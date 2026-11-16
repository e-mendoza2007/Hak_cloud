"""Consultas de lectura para el frontend:
GET /panel (máquinas + incidentes abiertos + técnicos en UNA invocación) | GET /flota?fecha= (productividad y
combustible en UNA invocación; por defecto el último día calculado) | GET /tecnicos | GET /repuestos/estado | GET /flota/productividad?fecha= | GET /flota/combustible?fecha=
GET /notificaciones?rol=supervisor"""
from datetime import datetime, timedelta, timezone
from common.dynamo import scan_all, query, obtener, Key, ahora_ms
from common.http import respuesta, query_param
from core.config import ROLES

CAMPOS_PROD = ["maquina_id", "modelo", "zona", "utilizacion", "horas_op", "prod_t_h", "costo", "costo_por_th",
               "clasificacion"]
CAMPOS_COMB = ["maquina_id", "modelo", "zona", "litros", "litros_por_th", "desv_combustible_pct",
               "tend_combustible_pct_dia", "alerta_combustible"]


def _hoy():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _resumen_reciente():
    """#RESUMEN que deja el batch de A: hoy o, si aún no corrió, ayer."""
    for d in (0, 1):
        f = (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%d")
        r = obtener("metricas", {"fecha": f, "maquina_id": "#RESUMEN"})
        if r:
            return r
    return {}


def tecnicos():
    ts = sorted(scan_all("tecnicos"), key=lambda t: t["tecnico_id"])
    return {"tecnicos": ts, "disponibles": sum(1 for t in ts if t.get("estado") == "disponible")}


def repuestos():
    almacenes = {}
    for r in scan_all("repuestos"):
        almacenes.setdefault(r["ubicacion_id"], []).append(
            {"componente": r["componente_id"], "stock": r.get("stock", 0), "minimo": r.get("minimo", 0),
             "bajo_minimo": r.get("stock", 0) < r.get("minimo", 0)})
    res = _resumen_reciente()
    return {"almacenes": almacenes, "demanda": res.get("alertas_repuestos", []),
            "consumo_irregular": res.get("consumo_irregular", []), "fecha_resumen": res.get("fecha")}


def _ultima_fecha_calculada():
    """Último día COMPLETO con #RESUMEN: se busca desde ayer (hoy todavía está en curso)."""
    for d in range(1, 9):
        f = (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%d")
        if obtener("metricas", {"fecha": f, "maquina_id": "#RESUMEN"}):
            return f
    return _hoy()


def flota(campos, fecha):
    filas = query("metricas", Key("fecha").eq(fecha))
    maquinas = [{k: f.get(k) for k in campos} for f in filas if not f["maquina_id"].startswith("#")]
    extra = {f["maquina_id"]: f for f in filas if f["maquina_id"].startswith("#")}
    return {"fecha": fecha, "maquinas": sorted(maquinas, key=lambda m: m["maquina_id"]),
            "resumen": extra.get("#RESUMEN", {}).get("clasificacion", {}), "plan": extra.get("#PLAN"),
            "calculado": any(m.get("utilizacion") is not None for m in maquinas),
            "patrones": obtener("metricas", {"fecha": "#PATRONES", "maquina_id": "actual"}).get("reglas", [])}


def panel():
    """Todo lo que la vista principal necesita, en una sola llamada (antes eran 3 Lambdas cada 8-15 s)."""
    from handlers.api_maquinas import CAMPOS_LISTA
    from handlers.api_incidentes import _prioridad
    maquinas = sorted(scan_all("maquinas", CAMPOS_LISTA), key=lambda m: m["maquina_id"])
    incs = sorted((i for i in scan_all("incidentes") if i.get("estado") != "resuelto"), key=_prioridad)
    for i in incs:
        i.pop("timeline", None)
    return {"maquinas": maquinas, "incidentes": incs, **tecnicos(), "ts": ahora_ms()}


def lambda_handler(event, context):
    # Entrada (json)
    recurso = event.get("resource")
    # Proceso
    if recurso == "/panel":
        return respuesta(200, panel())
    if recurso == "/tecnicos":
        return respuesta(200, tecnicos())
    if recurso == "/repuestos/estado":
        return respuesta(200, repuestos())
    if recurso == "/flota":
        return respuesta(200, flota(CAMPOS_PROD + CAMPOS_COMB[3:], query_param(event, "fecha") or _ultima_fecha_calculada()))
    if recurso == "/flota/productividad":
        return respuesta(200, flota(CAMPOS_PROD, query_param(event, "fecha") or _ultima_fecha_calculada()))
    if recurso == "/flota/combustible":
        return respuesta(200, flota(CAMPOS_COMB, query_param(event, "fecha") or _ultima_fecha_calculada()))
    if recurso == "/notificaciones":
        rol = query_param(event, "rol", "supervisor")
        if rol not in ROLES:
            return respuesta(400, {"error": f"rol válido: {ROLES}"})
        return respuesta(200, {"rol": rol, "notificaciones": query("notificaciones", Key("rol").eq(rol),
                                                                   limite=30, desc=True)})
    # Salida (json)
    return respuesta(404, {"error": f"ruta no soportada: {recurso}"})
