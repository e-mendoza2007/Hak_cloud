"""Patrones previos a fallas (dolor 12): qué variables se desviaron antes de cada incidente pasado y con cuánta
anticipación, agregados por componente como reglas de alerta temprana. Puro Python."""
import statistics
from collections import Counter

VARS = ["temperatura", "vibracion", "presion", "combustible_lh", "rpm"]
NOMBRE = {"temperatura": "temperatura", "vibracion": "vibración", "presion": "presión",
          "combustible_lh": "combustible", "rpm": "revoluciones"}


def senales_previas(lecturas, creado_ts, ventana_min=5, z_umbral=2.0):
    """lecturas: telemetría de la máquina en las horas previas al incidente (incluye el histórico).
    Base = lecturas operativas antes de la ventana; señal = lecturas operativas de los últimos `ventana_min`.
    Devuelve {variables, z, anticipacion_min} o None si no hay datos suficientes."""
    corte = creado_ts - ventana_min * 60000
    ops = sorted((l for l in lecturas if l.get("estado") == "operativa" and int(l["ts"]) <= creado_ts),
                 key=lambda l: int(l["ts"]))
    base = [l for l in ops if int(l["ts"]) < corte]
    senal = [l for l in ops if int(l["ts"]) >= corte]
    if len(base) < 5 or len(senal) < 3:
        return None
    z, umbral = {}, {}
    for v in VARS:
        xs = [float(l[v]) for l in base if v in l]
        ys = [float(l[v]) for l in senal if v in l]
        if len(xs) < 5 or not ys:
            continue
        media = statistics.mean(xs)
        sd = max(statistics.pstdev(xs), abs(media) * 0.02, 1e-6)
        z[v] = round((statistics.mean(ys) - media) / sd, 2)
        umbral[v] = (media, sd)
    variables = sorted((v for v in z if abs(z[v]) >= z_umbral), key=lambda v: -abs(z[v]))
    if not variables:
        return None
    # Anticipación: desde qué lectura la variable principal quedó fuera de lo normal hasta el incidente
    v = variables[0]
    media, sd = umbral[v]
    signo = 1 if z[v] > 0 else -1
    inicio = None
    for l in senal:
        fuera = signo * (float(l[v]) - media) >= z_umbral * sd
        if fuera and inicio is None:
            inicio = int(l["ts"])
        elif not fuera:
            inicio = None                     # tiene que mantenerse fuera hasta el incidente
    anticipacion = round((creado_ts - inicio) / 60000, 1) if inicio else 0.0
    return {"variables": variables, "z": {k: z[k] for k in variables}, "anticipacion_min": anticipacion}


def reglas(registros, min_casos=2):
    """registros: [{componente, variables, anticipacion_min}] -> reglas de alerta temprana por componente."""
    por_comp = {}
    for r in registros:
        por_comp.setdefault(r["componente"], []).append(r)
    salida = []
    for comp, rs in sorted(por_comp.items(), key=lambda kv: -len(kv[1])):
        combos = Counter(tuple(sorted(r["variables"][:2])) for r in rs)
        (combo, veces), = combos.most_common(1)
        if veces < min_casos:
            continue
        ant = statistics.median(r["anticipacion_min"] for r in rs if tuple(sorted(r["variables"][:2])) == combo)
        vars_txt = " y ".join(NOMBRE.get(v, v) for v in combo)
        verbo = "se desvían juntas" if len(combo) > 1 else "se desvía"
        salida.append({"componente": comp, "variables": list(combo), "casos": veces, "total": len(rs),
                       "anticipacion_min": round(ant, 1),
                       "texto": f"Si {vars_txt} {verbo}, preparar {comp.replace('_', ' ')}: pasó en {veces} de "
                                f"{len(rs)} fallas, unos {round(ant, 1)} min antes del incidente."})
    return salida
