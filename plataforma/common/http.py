"""Utilidades para la API REST (integración lambda-proxy): respuesta con CORS y lectura del request."""
import json
import os
from decimal import Decimal


def _json_default(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    if isinstance(o, set):
        return list(o)
    raise TypeError(f"no serializable: {type(o).__name__}")


def respuesta(codigo, cuerpo):
    return {"statusCode": codigo,
            "headers": {"Content-Type": "application/json",
                        "Access-Control-Allow-Origin": os.environ.get("CORS_ORIGIN", "*")},
            "body": json.dumps(cuerpo, default=_json_default, ensure_ascii=False)}


def leer_body(event):
    """Body JSON del request; lanza ValueError si no es JSON válido."""
    body = event.get("body") or "{}"
    if isinstance(body, dict):
        return body
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("el body debe ser un objeto JSON")
    return data


def path_param(event, nombre):
    return (event.get("pathParameters") or {}).get(nombre)


def query_param(event, nombre, default=None):
    return (event.get("queryStringParameters") or {}).get(nombre) or default
