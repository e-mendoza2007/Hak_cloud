"""Causa común: varias máquinas de una misma zona con incidentes en una ventana corta."""
import time
from collections import Counter
from .dynamo import tabla, resource, Key, from_dynamo, IDX_INC_ZONA, set_attrs  # noqa: F401


def detectar(inc, um):
    """Si ya hay >= N máquinas con incidente en la zona, agrupa los incidentes y devuelve el grupo."""
    t0 = inc["creado_ts"] - um["ventana_min"] * 60000
    resp = tabla("incidentes").query(IndexName=IDX_INC_ZONA,
                                     KeyConditionExpression=Key("zona").eq(inc["zona"]) & Key("creado_ts").gte(t0))
    incs = [from_dynamo(i) for i in resp.get("Items", [])]
    if inc["incidente_id"] not in {i["incidente_id"] for i in incs}:
        incs.append(inc)
    maquinas = sorted({i["maquina_id"] for i in incs})
    if len(maquinas) < um["causa_comun_min_maquinas"]:
        return None
    grupo_id = next((i["grupo_id"] for i in incs if i.get("grupo_id")), None) or f"GRP-{inc['zona']}-{inc['creado_ts']}"
    cuenta = Counter(v for i in incs for v in i.get("variables_anomalas", [])[:2])
    var_comun = cuenta.most_common(1)[0][0] if cuenta else None
    info = {"grupo_id": grupo_id, "n_maquinas": len(maquinas), "maquinas": maquinas,
            "variable_comun": var_comun, "zona": inc["zona"]}
    for i in incs:
        set_attrs(tabla("incidentes"), {"incidente_id": i["incidente_id"]},
                  {"grupo_id": grupo_id, "grupo_info": info})
    return info
