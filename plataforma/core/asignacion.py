"""Asignación de técnicos (dolor 5) y reserva de repuestos (dolor 3). Puro Python."""
from .config import (PESOS_ASIGNACION, CARGA_MAX, VEL_KMH, TIEMPO_REPARACION_MIN,
                     REPARACION_DEFAULT_MIN, EXTRA_SIN_ESPECIALIDAD_MIN, ALMACENES)
from .geo import haversine_km


def puntaje(tecnico, maquina, componente, severidad):
    """Puntaje = cercanía + especialidad - carga, con pesos según la severidad.
    Devuelve (puntaje, distancia_km, es_especialista)."""
    d = haversine_km(tecnico["lat"], tecnico["lon"], maquina["lat"], maquina["lon"])
    cercania = 1.0 / (1.0 + d)                       # 0 km -> 1.0 ; 4 km -> 0.2
    especialista = componente in (tecnico.get("especialidades") or [])
    carga = min(float(tecnico.get("carga", 0)), CARGA_MAX) / CARGA_MAX
    w = PESOS_ASIGNACION.get(severidad, PESOS_ASIGNACION["media"])
    p = w["cercania"] * cercania + w["especialidad"] * (1.0 if especialista else 0.0) - w["carga"] * carga
    return round(p, 4), round(d, 2), especialista


def rankear(tecnicos, maquina, componente, severidad):
    """Técnicos disponibles ordenados de mejor a peor candidato."""
    candidatos = []
    for t in tecnicos:
        if t.get("estado") != "disponible":
            continue
        p, d, esp = puntaje(t, maquina, componente, severidad)
        candidatos.append({"tecnico": t, "puntaje": p, "distancia_km": d, "especialista": esp})
    candidatos.sort(key=lambda c: (-c["puntaje"], c["distancia_km"]))
    return candidatos


def eta(distancia_km, componente, especialista):
    """Tiempo estimado: viaje (distancia / velocidad) + reparación (más lenta si no es especialista)."""
    viaje = distancia_km / VEL_KMH * 60
    rep = TIEMPO_REPARACION_MIN.get(componente, REPARACION_DEFAULT_MIN)
    if not especialista:
        rep += EXTRA_SIN_ESPECIALIDAD_MIN
    return {"viaje_min": round(viaje, 1), "reparacion_min": rep, "total_min": int(round(viaje + rep))}


def almacenes_por_cercania(maquina):
    """Almacenes ordenados del más cercano al más lejano a la máquina."""
    return sorted(ALMACENES, key=lambda a: haversine_km(maquina["lat"], maquina["lon"], *ALMACENES[a]))
