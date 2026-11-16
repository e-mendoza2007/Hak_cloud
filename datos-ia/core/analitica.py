"""Analítica de flota: productividad, combustible, preventivo y repuestos. Puro Python."""
import statistics
from datetime import date, timedelta
from .config import (MODELOS, PRECIO_LITRO, UMBRAL_UTIL_BAJA, UMBRAL_UTIL_ALTA, COMPONENTE)


def _mediana(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def metricas_dia(item, modelo):
    """item = contadores acumulados del día (seg_op, seg_tot, litros, prod, temp_s)."""
    seg_op, seg_tot = float(item.get("seg_op", 0)), float(item.get("seg_tot", 0))
    litros, prod = float(item.get("litros", 0)), float(item.get("prod", 0))
    horas_op = seg_op / 3600
    util = seg_op / seg_tot if seg_tot > 0 else 0.0
    costo = litros * PRECIO_LITRO + horas_op * MODELOS[modelo]["costo_hora_mant"]
    return {"horas_op": round(horas_op, 2), "utilizacion": round(util, 3),
            "litros": round(litros, 1), "prod_t_h": round(prod, 2),
            "litros_por_th": round(litros / prod, 3) if prod > 0 else None,
            "costo": round(costo, 2),
            "costo_por_th": round(costo / prod, 3) if prod > 0 else None,
            "temp_prom": round(float(item.get("temp_s", 0)) / seg_op, 1) if seg_op > 0 else None}


def clasificar_flota(filas):
    """filas = [{maquina_id, modelo, utilizacion, costo_por_th, litros_por_th, ...}].
    Agrega: clasificacion (lista), desv_combustible_pct (vs mediana del modelo)."""
    por_modelo = {}
    for f in filas:
        por_modelo.setdefault(f["modelo"], []).append(f)
    for modelo, grupo in por_modelo.items():
        med_costo = _mediana([g.get("costo_por_th") for g in grupo])
        med_comb = _mediana([g.get("litros_por_th") for g in grupo])
        for g in grupo:
            etiquetas = []
            u = g.get("utilizacion", 0)
            if u < UMBRAL_UTIL_BAJA:
                etiquetas.append("baja_utilizacion")
            if u > UMBRAL_UTIL_ALTA:
                etiquetas.append("uso_excesivo")
            c = g.get("costo_por_th")
            if u < 0.5 and c and med_costo and c > 1.3 * med_costo:
                etiquetas.append("baja_productividad_alto_costo")
            g["clasificacion"] = etiquetas
            l = g.get("litros_por_th")
            g["desv_combustible_pct"] = round((l / med_comb - 1) * 100, 1) if l and med_comb else None
    return filas


def tendencia_pct_dia(valores):
    """Pendiente de regresión lineal relativa a la media, en %/día. None si hay < 4 puntos."""
    ys = [v for v in valores if v is not None]
    if len(ys) < 4:
        return None
    n = len(ys)
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0 or my == 0:
        return None
    pend = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return round(pend / my * 100, 2)


def preventivo(maq, modelo, horas_op_dia, temp_prom=None, hoy=None):
    """Intervalo de mantenimiento ajustado por uso severo (temperatura sobre lo normal)."""
    m = MODELOS[modelo]
    hoy = hoy or date.today()
    sev = 0.0
    if temp_prom:
        sev = min(max((temp_prom - m["temperatura"][0]) / (3 * m["temperatura"][1]), 0), 1)
    intervalo = m["intervalo_mant_h"] * (1 - 0.3 * sev)
    restantes = intervalo - float(maq.get("horas_desde_mant", 0))
    ritmo = horas_op_dia if horas_op_dia and horas_op_dia > 0.5 else 12.0
    dias = restantes / ritmo
    estado = "vencido" if restantes <= 0 else ("proximo" if dias <= 5 else "ok")
    fecha = hoy + timedelta(days=max(0, int(dias)))
    return {"intervalo_h": round(intervalo, 1), "horas_restantes": round(restantes, 1),
            "dias_restantes": round(dias, 1), "fecha_sugerida": fecha.isoformat(),
            "estado": estado, "factor_uso_severo": round(sev, 2)}


def demanda_repuestos(maquinas, stock, umbral_score=0.4):
    """maquinas: [{maquina_id, zona, score_actual, componente_probable, preventivo:{estado}}]
    stock: {(ubicacion_id, componente_id): {"stock": n, "minimo": m}}  (ubicacion = ALM-<zona>)
    Devuelve alertas de faltante por zona/componente."""
    demanda = {}
    for m in maquinas:
        riesgo = float(m.get("score_actual", 0)) >= umbral_score
        prev = (m.get("preventivo") or {}).get("estado") in ("vencido", "proximo")
        comp = m.get("componente_probable")
        if (riesgo or prev) and comp and comp != "ninguno":   # sin componente identificado no hay repuesto que pedir
            demanda.setdefault((m["zona"], comp), []).append(m["maquina_id"])
    alertas = []
    for (zona, comp), ids in sorted(demanda.items()):
        s = stock.get((f"ALM-{zona}", comp), {"stock": 0, "minimo": 0})
        faltan = len(ids) - int(s["stock"])
        if faltan > 0:
            alertas.append({"zona": zona, "componente": comp, "demanda": len(ids),
                            "stock": int(s["stock"]), "faltan": faltan, "maquinas": ids})
    return alertas


def consumo_irregular(historial, z_umbral=2.5):
    """historial: consumos diarios de un componente. Marca el último valor si se sale del patrón."""
    xs = [float(x) for x in historial]
    if len(xs) < 5:
        return None
    previos, ultimo = xs[:-1], xs[-1]
    mu, sd = statistics.mean(previos), statistics.pstdev(previos)
    if sd == 0:
        return None
    z = (ultimo - mu) / sd
    return {"z": round(z, 2), "irregular": abs(z) >= z_umbral}
