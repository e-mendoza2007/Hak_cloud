"""Simulador de telemetría. Puro Python: sin AWS."""
import math
import random
from .config import MODELOS, VARS

ZONAS = {"Z1": (-12.040, -77.030), "Z2": (-12.060, -77.050),
         "Z3": (-12.080, -77.020), "Z4": (-12.050, -77.000)}
UTIL = {"ocioso": 0.20, "normal": 0.65, "sobrecargado": 0.95}

# Efecto de cada falla a progreso 1.0, en desviaciones estándar de la variable.
EFECTOS = {
    "rodamiento":    {"vibracion": 12, "temperatura": 8, "combustible_lh": 4, "rpm": -2},
    "refrigeracion": {"temperatura": 14, "vibracion": 6, "combustible_lh": 5},
    "inyectores":    {"combustible_lh": 12, "rpm": -6, "temperatura": 5},
    "hidraulica":    {"presion": -12, "vibracion": 5, "temperatura": 4},
}


def crear_flota(n=30):
    """Datos maestros de las máquinas (30 máquinas, 4 zonas, 3 modelos)."""
    modelos = list(MODELOS)
    flota = []
    for i in range(n):
        rnd = random.Random(i)
        zona = f"Z{(i % 4) + 1}"
        modelo = modelos[i % 3]
        perfil = "ocioso" if i % 10 == 3 else ("sobrecargado" if i % 10 == 7 else "normal")
        lat0, lon0 = ZONAS[zona]
        flota.append({
            "maquina_id": f"M-{i + 1:03d}", "modelo": modelo, "zona": zona,
            "lat": round(lat0 + rnd.uniform(-0.004, 0.004), 5),
            "lon": round(lon0 + rnd.uniform(-0.004, 0.004), 5),
            "perfil": perfil, "estado": "operativa",
            "horas_totales": round(rnd.uniform(500, 6000), 1),
            "horas_desde_mant": round(rnd.uniform(0, MODELOS[modelo]["intervalo_mant_h"] * 0.9), 1),
        })
    return flota


def esta_trabajando(maq, ts_ms):
    """Bloques de 30 min deterministas por máquina: trabaja o está parada."""
    bloque = ts_ms // (30 * 60 * 1000)
    r = random.Random(f"{maq['maquina_id']}-{bloque}").random()
    return r < UTIL.get(maq.get("perfil", "normal"), 0.65)


def progreso(deg, ts_ms):
    """0..1 según el avance de la degradación inyectada."""
    if not deg:
        return 0.0
    rampa = max(float(deg.get("rampa_min", 10)), 0.1) * 60000
    return min(max((ts_ms - float(deg["inicio_ts"])) / rampa, 0.0), 1.0)


def generar_lectura(maq, ts_ms, rng):
    m = MODELOS[maq["modelo"]]
    deg = maq.get("degradacion")
    r = progreso(deg, ts_ms)
    trabaja = esta_trabajando(maq, ts_ms) or r > 0
    base = {"maquina_id": maq["maquina_id"], "ts": int(ts_ms), "zona": maq["zona"],
            "lat": float(maq["lat"]), "lon": float(maq["lon"]),
            "horas_totales": float(maq.get("horas_totales", 0))}
    if not trabaja:
        base.update({"temperatura": rng.gauss(50, 4), "vibracion": abs(rng.gauss(0.3, 0.05)),
                     "presion": rng.gauss(40, 5), "combustible_lh": abs(rng.gauss(4, 0.5)),
                     "carga_t": 0.0, "velocidad": 0.0, "rpm": rng.gauss(700, 30),
                     "estado": "detenida"})
    else:
        ratio = max(0.2, rng.gauss(1.0, 0.15))
        ciclo = math.sin((ts_ms / 3600000.0 % 24) / 24 * 2 * math.pi)
        v = {}
        for var in VARS:
            mu, sd = m[var]
            v[var] = rng.gauss(mu, sd)
        v["temperatura"] += 0.3 * m["temperatura"][1] * ciclo
        if deg and deg.get("tipo") in EFECTOS and r > 0:
            for var, shift in EFECTOS[deg["tipo"]].items():
                v[var] += shift * m[var][1] * r
        v["combustible_lh"] *= (0.6 + 0.5 * ratio)   # el consumo real depende de la carga
        base.update({k: v[k] for k in VARS})
        base.update({"carga_t": m["carga_nom"] * ratio,
                     "velocidad": max(0.0, rng.gauss(m["vel"], m["vel"] * 0.1)),
                     "estado": "operativa"})
    for k in ("temperatura", "vibracion", "presion", "combustible_lh", "carga_t", "velocidad", "rpm"):
        base[k] = round(base[k], 2)
    return base
