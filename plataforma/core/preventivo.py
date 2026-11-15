"""Plan preventivo diario (dolor 2): qué máquinas mantener ya y cuáles pueden esperar. Puro Python."""


def planificar(maquinas, resumen=None):
    """maquinas: [{maquina_id, zona, modelo, score_actual, preventivo:{estado, dias_restantes, fecha_sugerida}}]
    resumen: #RESUMEN del batch de A (alertas_repuestos, alerta_combustible, clasificacion)."""
    resumen = resumen or {}
    mantener, posponer = [], 0
    for m in maquinas:
        p = m.get("preventivo") or {}
        if p.get("estado") in ("vencido", "proximo"):
            mantener.append({"maquina_id": m["maquina_id"], "zona": m.get("zona"), "estado": p["estado"],
                             "dias_restantes": p.get("dias_restantes"), "fecha_sugerida": p.get("fecha_sugerida"),
                             "score": m.get("score_actual", 0)})
        elif p.get("estado") == "ok":
            posponer += 1
    # Primero las vencidas, luego las más urgentes y, a igualdad, las de mayor riesgo actual
    mantener.sort(key=lambda x: (x["estado"] != "vencido", x.get("dias_restantes") or 0, -float(x["score"] or 0)))
    alertas_rep = resumen.get("alertas_repuestos") or []
    combustible = resumen.get("alerta_combustible") or []
    return {"mantener": mantener, "posponer": posponer, "alertas_repuestos": alertas_rep,
            "alerta_combustible": combustible, "clasificacion": resumen.get("clasificacion") or {},
            "novedades": len(mantener) + len(alertas_rep)}


def texto_plan(plan, fecha):
    lineas = [f"Plan preventivo del {fecha}"]
    if plan["mantener"]:
        lineas.append("Mantener (en este orden):")
        lineas += [f"- {m['maquina_id']} ({m['zona']}): {m['estado']}, fecha sugerida {m['fecha_sugerida']}"
                   for m in plan["mantener"][:10]]
    lineas.append(f"Se posponen {plan['posponer']} mantenimientos que todavía no hacen falta.")
    for a in plan["alertas_repuestos"][:5]:
        lineas.append(f"Repuestos: faltan {a['faltan']} de {a['componente']} en zona {a['zona']}.")
    if plan["alerta_combustible"]:
        lineas.append(f"Consumo de combustible fuera de lo esperado: {', '.join(plan['alerta_combustible'][:8])}.")
    for etiqueta, ids in (plan["clasificacion"] or {}).items():
        lineas.append(f"{etiqueta}: {len(ids)} máquinas")
    return "\n".join(lineas)
