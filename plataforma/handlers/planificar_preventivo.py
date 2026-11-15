"""PreventivoDiario -> PlanificarPreventivo. Entrada: salida de CalcularFlota (batchFlota de A) en $.flota.
Arma el plan del día (qué mantener ya y qué posponer) y lo deja en la bandeja del supervisor.
El email lo envía Step Functions directamente con SNS (integración nativa)."""
import json
from datetime import datetime, timezone
from common.dynamo import obtener, scan_all, actualizar
from common.notificar import guardar_bandeja
from core.preventivo import planificar, texto_plan


def lambda_handler(event, context):
    # Entrada (json)
    fecha = (event.get("flota") or {}).get("fecha") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resumen = obtener("metricas", {"fecha": fecha, "maquina_id": "#RESUMEN"})
    maquinas = scan_all("maquinas", ["maquina_id", "zona", "modelo", "score_actual", "preventivo"])

    # Proceso
    plan = planificar(maquinas, resumen)
    texto = texto_plan(plan, fecha)
    actualizar("metricas", {"fecha": fecha, "maquina_id": "#PLAN"},
               sets={"mantener": plan["mantener"], "posponer": plan["posponer"], "novedades": plan["novedades"]})
    if plan["novedades"]:
        guardar_bandeja("supervisor", {"incidente_id": f"PLAN-{fecha}"}, texto, "email", "preventivo")
    print(json.dumps({"plan_preventivo": fecha, "mantener": len(plan["mantener"]), "posponer": plan["posponer"],
                      "alertas_repuestos": len(plan["alertas_repuestos"])}))
    # Salida (json)
    return {"fecha": fecha, "novedades": plan["novedades"], "asunto": f"[ArquiFusion] Plan preventivo {fecha}",
            "mensaje": texto}
