"""Batch de flota (diario o bajo demanda). Evento opcional: {"fecha": "YYYY-MM-DD"}.
Calcula: utilización/productividad, combustible (vs pares y tendencia 7 días), preventivo y repuestos."""
import time
from datetime import date, datetime, timedelta, timezone
from common.dynamo import tabla, scan_all, query_all, set_attrs, Key
from core.analitica import (metricas_dia, clasificar_flota, tendencia_pct_dia, preventivo,
                            demanda_repuestos, consumo_irregular)


def _dia(fecha):
    return query_all(tabla("metricas"), KeyConditionExpression=Key("fecha").eq(fecha))


def handler(event, context):
    fecha = (event or {}).get("fecha") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    maquinas = {m["maquina_id"]: m for m in scan_all(tabla("maquinas"))}
    hoy = [i for i in _dia(fecha) if i["maquina_id"] in maquinas]

    # 1) Utilización, productividad y costo
    filas = []
    for it in hoy:
        modelo = maquinas[it["maquina_id"]].get("modelo")
        if modelo:
            f = metricas_dia(it, modelo)
            f.update({"maquina_id": it["maquina_id"], "modelo": modelo, "zona": maquinas[it["maquina_id"]].get("zona")})
            filas.append(f)
    clasificar_flota(filas)

    # 2) Combustible: tendencia de los últimos 7 días (litros por t·h)
    d0 = date.fromisoformat(fecha)
    previos = {}
    for k in range(7, 0, -1):
        for it in _dia((d0 - timedelta(days=k)).isoformat()):
            mod = maquinas.get(it["maquina_id"], {}).get("modelo")
            if mod:
                previos.setdefault(it["maquina_id"], []).append(metricas_dia(it, mod)["litros_por_th"])
    for f in filas:
        serie = previos.get(f["maquina_id"], []) + [f.get("litros_por_th")]
        f["tend_combustible_pct_dia"] = tendencia_pct_dia(serie)
        f["alerta_combustible"] = bool((f.get("desv_combustible_pct") or 0) > 15 or (f["tend_combustible_pct_dia"] or 0) > 2)
        set_attrs(tabla("metricas"), {"fecha": fecha, "maquina_id": f["maquina_id"]},
                  {k: v for k, v in f.items() if k not in ("maquina_id",)})

    # 3) Preventivo por máquina (ritmo = horas de operación promedio de los días con datos)
    horas_dia = {f["maquina_id"]: f["horas_op"] for f in filas}
    temp = {f["maquina_id"]: f.get("temp_prom") for f in filas}
    for mid, m in maquinas.items():
        if m.get("modelo"):
            p = preventivo(m, m["modelo"], horas_dia.get(mid), temp.get(mid), d0)
            m["preventivo"] = p
            set_attrs(tabla("maquinas"), {"maquina_id": mid}, {"preventivo": p})

    # 4) Repuestos: demanda proyectada vs stock por almacén (ALM-<zona>) y consumo irregular
    reps = scan_all(tabla("repuestos"))
    stock = {(r["ubicacion_id"], r["componente_id"]): r for r in reps}
    alertas = demanda_repuestos(list(maquinas.values()), stock)
    irregulares = []
    for r in reps:
        ci = consumo_irregular(r.get("consumo_historial", []))
        if ci and ci["irregular"]:
            irregulares.append({"ubicacion": r["ubicacion_id"], "componente": r["componente_id"], **ci})

    resumen = {"clasificacion": {}, "alertas_repuestos": alertas, "consumo_irregular": irregulares,
               "preventivo_vencido": [m for m, v in maquinas.items() if (v.get("preventivo") or {}).get("estado") == "vencido"],
               "alerta_combustible": [f["maquina_id"] for f in filas if f.get("alerta_combustible")],
               "generado_ts": int(time.time() * 1000)}
    for f in filas:
        for c in f["clasificacion"]:
            resumen["clasificacion"].setdefault(c, []).append(f["maquina_id"])
    set_attrs(tabla("metricas"), {"fecha": fecha, "maquina_id": "#RESUMEN"}, resumen)
    return {"fecha": fecha, "maquinas": len(filas), "alertas_repuestos": len(alertas),
            "clasificacion": {k: len(v) for k, v in resumen["clasificacion"].items()}}
