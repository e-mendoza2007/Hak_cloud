"""POST /ingesta  ->  { ...lectura } o { "lecturas": [ ... ] }"""
import json
from common.ingesta_core import procesar_lecturas


def _resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def handler(event, context):
    try:
        data = json.loads(event.get("body") or "{}")
        lecturas = data["lecturas"] if isinstance(data.get("lecturas"), list) else [data]
        return _resp(200, {"recibidas": procesar_lecturas(lecturas)})
    except (ValueError, KeyError) as e:
        return _resp(400, {"error": str(e)})
