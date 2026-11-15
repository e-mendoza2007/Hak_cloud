"""POST /demo/falla  { "maquina_id": "M-017" | "zona": "Z2", "tipo": "rodamiento", "rampa_min": 5 }
Con { "limpiar": true } se quita la degradación."""
import json
import time
from core.simulador import EFECTOS
from common.dynamo import tabla, scan_all


def _resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def handler(event, context):
    d = json.loads(event.get("body") or "{}")
    t = tabla("maquinas")
    if d.get("maquina_id"):
        ids = [d["maquina_id"]]
    elif d.get("zona"):
        ids = [m["maquina_id"] for m in scan_all(t) if m.get("zona") == d["zona"]]
    else:
        return _resp(400, {"error": "indica maquina_id o zona"})
    if d.get("limpiar"):
        for mid in ids:
            t.update_item(Key={"maquina_id": mid}, UpdateExpression="REMOVE degradacion")
        return _resp(200, {"limpiadas": ids})
    tipo = d.get("tipo", "rodamiento")
    if tipo not in EFECTOS:
        return _resp(400, {"error": f"tipo válido: {list(EFECTOS)}"})
    deg = {"tipo": tipo, "inicio_ts": int(time.time() * 1000), "rampa_min": int(d.get("rampa_min", 10))}
    from common.dynamo import to_dynamo
    for mid in ids:
        t.update_item(Key={"maquina_id": mid}, UpdateExpression="SET degradacion = :d",
                      ExpressionAttributeValues={":d": to_dynamo(deg)})
    return _resp(200, {"degradando": ids, **deg})
