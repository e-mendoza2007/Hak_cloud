"""Acceso a DynamoDB (boto3). Los nombres de tabla salen del contrato (af_*)."""
import os
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key  # noqa: F401  (se re-exporta)

TABLAS = {"maquinas": "af_maquinas", "telemetria": "af_telemetria", "incidentes": "af_incidentes",
          "historial": "af_historial", "tecnicos": "af_tecnicos", "repuestos": "af_repuestos",
          "notificaciones": "af_notificaciones", "metricas": "af_flota_metricas"}
IDX_INC_MAQUINA = "maquina-creado-index"   # GSI de af_incidentes: maquina_id + creado_ts
IDX_INC_ZONA = "zona-creado-index"         # GSI de af_incidentes: zona + creado_ts

_res = None


def resource():
    global _res
    if _res is None:
        _res = boto3.resource("dynamodb")
    return _res


def tabla(clave):
    return resource().Table(os.environ.get("T_" + clave.upper(), TABLAS[clave]))


def to_dynamo(o):
    """DynamoDB no acepta float: se convierte a Decimal (recursivo)."""
    if isinstance(o, float):
        return Decimal(str(round(o, 6)))
    if isinstance(o, dict):
        return {k: to_dynamo(v) for k, v in o.items() if v is not None}
    if isinstance(o, (list, tuple)):
        return [to_dynamo(v) for v in o]
    return o


def from_dynamo(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    if isinstance(o, dict):
        return {k: from_dynamo(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [from_dynamo(v) for v in o]
    return o


def scan_all(t, **kw):
    items, resp = [], t.scan(**kw)
    items += resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **kw)
        items += resp.get("Items", [])
    return [from_dynamo(i) for i in items]


def query_all(t, **kw):
    items, resp = [], t.query(**kw)
    items += resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = t.query(ExclusiveStartKey=resp["LastEvaluatedKey"], **kw)
        items += resp.get("Items", [])
    return [from_dynamo(i) for i in items]


def set_attrs(t, key, attrs):
    """UPDATE ... SET a=:a, b=:b (crea el ítem si no existe)."""
    names, vals, parts = {}, {}, []
    for i, (k, v) in enumerate(attrs.items()):
        names[f"#a{i}"], vals[f":v{i}"] = k, to_dynamo(v)
        parts.append(f"#a{i} = :v{i}")
    t.update_item(Key=key, UpdateExpression="SET " + ", ".join(parts),
                  ExpressionAttributeNames=names, ExpressionAttributeValues=vals)
