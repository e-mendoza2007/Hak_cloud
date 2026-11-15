"""Acceso a DynamoDB (boto3). Tablas del contrato común (af_*), creadas por infra-base."""
import time
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key  # noqa: F401  (se re-exporta)

TABLAS = {"maquinas": "af_maquinas", "telemetria": "af_telemetria", "incidentes": "af_incidentes",
          "historial": "af_historial", "tecnicos": "af_tecnicos", "repuestos": "af_repuestos",
          "notificaciones": "af_notificaciones", "metricas": "af_flota_metricas"}
IDX_INC_MAQUINA = "maquina-creado-index"     # GSI de af_incidentes (maquina_id + creado_ts)

_res = None


def tabla(clave):
    global _res
    _res = _res or boto3.resource("dynamodb")
    return _res.Table(TABLAS[clave])


def ahora_ms():
    return int(time.time() * 1000)


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
    if isinstance(o, (list, tuple, set)):
        return [from_dynamo(v) for v in o]
    return o


def obtener(clave_tabla, key):
    return from_dynamo(tabla(clave_tabla).get_item(Key=key).get("Item") or {})


def _proyeccion(campos):
    """ProjectionExpression con alias (#p0, #p1...) para no chocar con palabras reservadas de DynamoDB."""
    if not campos:
        return {}
    nombres = {f"#p{i}": c for i, c in enumerate(campos)}
    return {"ProjectionExpression": ", ".join(nombres), "ExpressionAttributeNames": nombres}


def scan_all(clave_tabla, campos=None):
    t, kw, items = tabla(clave_tabla), _proyeccion(campos), []
    while True:
        resp = t.scan(**kw)
        items += resp.get("Items", [])
        if "LastEvaluatedKey" not in resp:
            return [from_dynamo(i) for i in items]
        kw["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def query(clave_tabla, condicion, limite=None, desc=False, indice=None, campos=None):
    kw = {"KeyConditionExpression": condicion, "ScanIndexForward": not desc, **_proyeccion(campos)}
    if limite:
        kw["Limit"] = limite
    if indice:
        kw["IndexName"] = indice
    return [from_dynamo(i) for i in tabla(clave_tabla).query(**kw).get("Items", [])]


def actualizar(clave_tabla, key, sets=None, evento=None, removes=None, condicion=None, valores_cond=None):
    """UPDATE ... SET a=:a ... [timeline = timeline + evento] [REMOVE x] [IF condicion].
    `condicion` usa los nombres tal cual (ej. "estado IN (:c0, :c1)") y `valores_cond` sus valores."""
    names, vals, partes = {}, {}, []
    for i, (k, v) in enumerate((sets or {}).items()):
        names[f"#s{i}"], vals[f":s{i}"] = k, to_dynamo(v)
        partes.append(f"#s{i} = :s{i}")
    if evento:
        names["#tl"] = "timeline"
        vals[":ev"], vals[":vacia"] = [to_dynamo({"ts": ahora_ms(), **evento})], []
        partes.append("#tl = list_append(if_not_exists(#tl, :vacia), :ev)")
    expr = "SET " + ", ".join(partes) if partes else ""
    if removes:
        for i, k in enumerate(removes):
            names[f"#r{i}"] = k
        expr += " REMOVE " + ", ".join(f"#r{i}" for i in range(len(removes)))
    kw = {"Key": key, "UpdateExpression": expr.strip(), "ExpressionAttributeNames": names}
    if condicion:
        kw["ConditionExpression"] = condicion
        vals.update({k: to_dynamo(v) for k, v in (valores_cond or {}).items()})
        if "#estado" in condicion:                   # alias para las condiciones sobre el estado
            names["#estado"] = "estado"
    if vals:
        kw["ExpressionAttributeValues"] = vals
    tabla(clave_tabla).update_item(**kw)


def es_condicion_fallida(error):
    return getattr(error, "response", {}).get("Error", {}).get("Code") == "ConditionalCheckFailedException"
