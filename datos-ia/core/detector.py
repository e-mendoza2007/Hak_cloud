"""Detección de anomalías: EWMA + z-score propio + comparación con pares.
Puro Python: la función evaluar() recibe y devuelve dicts."""
import copy
import math
from .config import MODELOS, VARS, PESOS, COMPONENTE, UMBRALES_DEF

ALPHA = 0.01          # velocidad de aprendizaje del baseline (lento)
Z_APRENDER = 2.5      # no se aprende de lecturas anómalas
Z_MIN, Z_RANGO = 2.0, 6.0   # z=2 -> aporte 0; z=8 -> aporte 1
DIRECCIONAL = {"temperatura": True, "vibracion": True, "combustible_lh": True,
               "presion": False, "rpm": False}  # True: solo importa subir


def valores_norm(lectura, modelo):
    """Combustible se normaliza por carga: consumo alto con carga alta es normal."""
    m = MODELOS[modelo]
    ratio = lectura.get("carga_t", 0) / m["carga_nom"]
    ratio = min(max(ratio, 0.2), 1.6)
    return {"temperatura": lectura["temperatura"], "vibracion": lectura["vibracion"],
            "presion": lectura["presion"], "rpm": lectura["rpm"],
            "combustible_lh": lectura["combustible_lh"] / (0.6 + 0.5 * ratio)}


def estado_inicial(modelo):
    m = MODELOS[modelo]
    return {"stats": {v: {"mean": float(m[v][0]), "var": float(m[v][1]) ** 2} for v in VARS},
            "hist_score": []}


def severidad(score, um):
    if score >= um["critica"]:
        return "critica"
    if score >= um["alta"]:
        return "alta"
    if score >= um["media"]:
        return "media"
    return "baja" if score >= 0.2 else "normal"


def evaluar(lectura, estado, modelo, pares=None, umbrales=None):
    """Devuelve (nuevo_estado, resultado). resultado es None si la máquina no opera."""
    um = {**UMBRALES_DEF, **(umbrales or {})}
    if lectura.get("estado") != "operativa":
        return estado, None
    est = copy.deepcopy(estado) if estado and estado.get("stats") else estado_inicial(modelo)
    est.setdefault("hist_score", [])
    vals = valores_norm(lectura, modelo)
    aporte, zs = {}, {}
    for v in VARS:
        st = est["stats"][v]
        sd0 = MODELOS[modelo][v][1]
        sd = max(math.sqrt(st["var"]), 0.5 * sd0)
        z_prop = (vals[v] - st["mean"]) / sd
        z = z_prop
        if pares and v in pares:                      # comparación con máquinas del mismo modelo
            z_par = 0.7 * (vals[v] - pares[v]) / sd0
            z = max((z_prop, z_par), key=abs)
        dz = max(z, 0.0) if DIRECCIONAL[v] else abs(z)
        aporte[v] = min(max((dz - Z_MIN) / Z_RANGO, 0.0), 1.0)
        zs[v] = round(z, 2)
        if abs(z_prop) < Z_APRENDER:                  # actualizar baseline (EWMV)
            delta = vals[v] - st["mean"]
            st["mean"] += ALPHA * delta
            st["var"] = (1 - ALPHA) * (st["var"] + ALPHA * delta * delta)
    base = sum(PESOS[v] * aporte[v] for v in VARS)
    n_anom = sum(1 for v in VARS if aporte[v] > 0.25)
    mult = 1 + 0.25 * max(0, min(n_anom, 3) - 1)      # combinación de variables pesa más
    hist = est["hist_score"][-9:]
    bonus = 0.0
    if len(hist) >= 5 and all(hist[-i] >= hist[-i - 1] for i in range(1, 5)) and hist[-1] - hist[-5] >= 0.05:
        bonus = 0.08                                  # tendencia creciente sostenida
    score = round(min(1.0, base * mult + bonus), 3)
    est["hist_score"] = hist + [score]
    anomalas = [v for v in VARS if aporte[v] > 0.25]
    top = max(VARS, key=lambda v: (round(aporte[v], 3), PESOS[v]))  # la variable más desviada manda
    res = {"score": score, "severidad": severidad(score, um), "variables_anomalas": anomalas,
           "componente_probable": COMPONENTE[top] if score >= 0.2 else None,
           "z": zs, "n_anomalas": n_anom}
    return est, res
