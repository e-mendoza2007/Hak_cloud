"""POST /incidentes/{id}/atender  body opcional: {"tecnico_id": "T-03"}
El técnico confirma que está atendiendo: el incidente pasa a en_atencion y Step Functions deja de escalar."""
import json
from botocore.exceptions import ClientError
from common.dynamo import obtener, actualizar, es_condicion_fallida
from common.http import respuesta, path_param, leer_body


def lambda_handler(event, context):
    # Entrada (json)
    iid = path_param(event, "id")
    try:
        body = leer_body(event)
    except ValueError:
        return respuesta(400, {"error": "body JSON inválido"})
    inc = obtener("incidentes", {"incidente_id": iid})
    if not inc:
        return respuesta(404, {"error": f"incidente {iid} no existe"})
    # Proceso
    try:
        actualizar("incidentes", {"incidente_id": iid}, sets={"estado": "en_atencion"},
                   evento={"evento": "en_atencion", "tecnico_id": body.get("tecnico_id") or inc.get("tecnico_id")},
                   condicion="#estado IN (:c0, :c1, :c2)",
                   valores_cond={":c0": "abierto", ":c1": "asignado", ":c2": "escalado"})
    except ClientError as e:
        if es_condicion_fallida(e):
            return respuesta(409, {"error": f"el incidente está {inc.get('estado')}"})
        raise
    print(json.dumps({"atender": iid}))
    # Salida (json)
    return respuesta(200, {"incidente_id": iid, "estado": "en_atencion"})
