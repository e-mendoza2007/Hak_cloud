"""GET /incidentes?estado=abiertos|todos (cola priorizada) | GET /incidentes/{id} (detalle)."""
from common.dynamo import scan_all, obtener
from common.http import respuesta, path_param, query_param
from core.config import ORDEN_SEVERIDAD


def _prioridad(i):
    # Más severo primero; a igual severidad, mayor score; a igual score, el más antiguo
    return (-ORDEN_SEVERIDAD.get(i.get("severidad"), 0), -float(i.get("score") or 0), int(i.get("creado_ts") or 0))


def lambda_handler(event, context):
    # Entrada (json)
    iid = path_param(event, "id")
    # Proceso
    if iid:
        inc = obtener("incidentes", {"incidente_id": iid})
        if not inc:
            return respuesta(404, {"error": f"incidente {iid} no existe"})
        maq = obtener("maquinas", {"maquina_id": inc["maquina_id"]})
        inc["maquina"] = {k: maq.get(k) for k in ("modelo", "lat", "lon", "estado", "score_actual", "horas_desde_mant")}
        return respuesta(200, inc)

    filtro = query_param(event, "estado", "abiertos")
    incs = scan_all("incidentes")
    if filtro == "abiertos":
        incs = [i for i in incs if i.get("estado") != "resuelto"]
    incs.sort(key=_prioridad)
    for i in incs:
        i.pop("timeline", None)                       # la lista va liviana; el detalle trae el timeline
    # Salida (json)
    return respuesta(200, {"incidentes": incs, "total": len(incs)})
