"""PreventivoDiario -> PlanificarPreventivo. Entrada: salida de CalcularFlota (batchFlota de A) en $.flota.
Arma el plan del día (qué mantener ya y qué posponer) y lo deja en la bandeja del supervisor.
El email lo envía Step Functions directamente con SNS (integración nativa)."""
import json
from datetime import datetime, timezone
from common.dynamo import obtener, scan_all, actualizar, query, Key
from common.notificar import guardar_bandeja
from core.preventivo import planificar, texto_plan
from core.patrones import senales_previas, reglas, VARS


def patrones_previos():
    """Dolor 12: para cada incidente pasado, qué variables se desviaron antes y con cuánta anticipación."""
    registros, analizados = [], 0
    for i in scan_all("incidentes", ["maquina_id", "componente_probable", "creado_ts"]):
        comp = i.get("componente_probable")
        if not comp or comp == "ninguno":
            continue
        c = int(i["creado_ts"])
        lect = query("telemetria", Key("maquina_id").eq(i["maquina_id"]) & Key("ts").between(c - 24 * 3600000, c),
                     campos=["ts", "estado"] + VARS)
        analizados += 1
        s = senales_previas(lect, c)
        if s:
            registros.append({"componente": comp, **s})
    return reglas(registros), analizados, len(registros)


def lambda_handler(event, context):
    # Entrada (json)
    fecha = (event.get("flota") or {}).get("fecha") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resumen = obtener("metricas", {"fecha": fecha, "maquina_id": "#RESUMEN"})
    maquinas = scan_all("maquinas", ["maquina_id", "zona", "modelo", "score_actual", "preventivo"])

    # Proceso
    plan = planificar(maquinas, resumen)
    texto = texto_plan(plan, fecha)
    reglas_tempranas, analizados, con_senal = patrones_previos()
    actualizar("metricas", {"fecha": "#PATRONES", "maquina_id": "actual"},
               sets={"reglas": reglas_tempranas, "incidentes_analizados": analizados, "con_senal": con_senal,
                     "calculado_para": fecha})
    if reglas_tempranas:
        lineas = [f"- {r['texto']}" for r in reglas_tempranas]
        texto += "\nAlertas tempranas aprendidas de fallas pasadas:\n" + "\n".join(lineas)
    actualizar("metricas", {"fecha": fecha, "maquina_id": "#PLAN"},
               sets={"mantener": plan["mantener"], "posponer": plan["posponer"], "novedades": plan["novedades"]})
    if plan["novedades"]:
        guardar_bandeja("supervisor", {"incidente_id": f"PLAN-{fecha}"}, texto, "email", "preventivo")
    print(json.dumps({"plan_preventivo": fecha, "mantener": len(plan["mantener"]), "posponer": plan["posponer"],
                      "alertas_repuestos": len(plan["alertas_repuestos"]), "incidentes_analizados": analizados,
                      "reglas_tempranas": len(reglas_tempranas)}))
    # Salida (json)
    return {"fecha": fecha, "novedades": plan["novedades"], "asunto": f"[ArquiFusion] Plan preventivo {fecha}",
            "mensaje": texto}
