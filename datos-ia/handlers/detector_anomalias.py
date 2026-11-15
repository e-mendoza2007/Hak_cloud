"""Stream de af_telemetria -> score de riesgo -> incidente -> causa común -> Step Functions."""
import json
import secrets
import time
import traceback
import boto3
from boto3.dynamodb.types import TypeDeserializer
from core.config import MODELOS
from core.detector import evaluar, valores_norm, VARS
from common.dynamo import (tabla, from_dynamo, scan_all, set_attrs, to_dynamo, Key, IDX_INC_MAQUINA)
from common.params import get_param, get_umbrales
from common import causa_comun

_deser = TypeDeserializer()
_pares_cache = {}
_sfn = None
ORDEN = ["normal", "baja", "media", "alta", "critica"]


def _pares(modelo):
    """Mediana actual de cada variable entre las máquinas del mismo modelo (caché 2 min)."""
    hit = _pares_cache.get(modelo)
    if hit and hit[1] > time.time():
        return hit[0]
    filas = [m for m in scan_all(tabla("maquinas"), ProjectionExpression="maquina_id, modelo, ultima")
             if m.get("modelo") == modelo and (m.get("ultima") or {}).get("estado") == "operativa"]
    pares = None
    if len(filas) >= 3:
        vals = [valores_norm(m["ultima"], modelo) for m in filas]
        pares = {v: sorted(x[v] for x in vals)[len(vals) // 2] for v in VARS}
    _pares_cache[modelo] = (pares, time.time() + 120)
    return pares


def handler(event, context):
    for rec in event.get("Records", []):
        if rec.get("eventName") != "INSERT":
            continue
        try:
            img = {k: _deser.deserialize(v) for k, v in rec["dynamodb"]["NewImage"].items()}
            procesar(from_dynamo(img))
        except Exception:
            print("[detector] error:", traceback.format_exc())   # no se relanza: no bloquear el stream


def procesar(lect):
    t = tabla("maquinas")
    maq = from_dynamo(t.get_item(Key={"maquina_id": lect["maquina_id"]}).get("Item") or {})
    if maq.get("modelo") not in MODELOS:
        return
    um = get_umbrales()
    estado = {"stats": maq.get("stats"), "hist_score": maq.get("hist_score", [])} if maq.get("stats") else None
    nuevo, res = evaluar(lect, estado, maq["modelo"], _pares(maq["modelo"]), um)
    if res is None:
        return
    attrs = {"stats": nuevo["stats"], "hist_score": nuevo["hist_score"], "score_actual": res["score"],
             "severidad_actual": res["severidad"], "componente_probable": res["componente_probable"] or "ninguno"}
    set_attrs(t, {"maquina_id": maq["maquina_id"]}, attrs)
    if res["severidad"] == "critica":
        try:
            t.update_item(Key={"maquina_id": maq["maquina_id"]}, UpdateExpression="SET estado = :e",
                          ConditionExpression="estado <> :mt",
                          ExpressionAttributeValues={":e": "requiere_intervencion", ":mt": "mantenimiento"})
        except Exception:
            pass
    if ORDEN.index(res["severidad"]) >= ORDEN.index("media"):
        gestionar_incidente(maq, lect, res, um)


def gestionar_incidente(maq, lect, res, um):
    ti = tabla("incidentes")
    ultimos = from_dynamo(ti.query(IndexName=IDX_INC_MAQUINA, KeyConditionExpression=Key("maquina_id").eq(maq["maquina_id"]),
                                   ScanIndexForward=False, Limit=1).get("Items", []))
    ahora = int(time.time() * 1000)
    if ultimos:
        u = ultimos[0]
        if u.get("estado") != "resuelto":                      # ya hay uno abierto: solo se escala
            if res["score"] > float(u.get("score", 0)):
                set_attrs(ti, {"incidente_id": u["incidente_id"]},
                          {"score": res["score"], "severidad": res["severidad"],
                           "variables_anomalas": res["variables_anomalas"],
                           "componente_probable": res["componente_probable"]})
            return
        if ahora - int(u.get("cerrado_ts") or u["creado_ts"]) < um["cooldown_min"] * 60000:
            return                                              # cooldown tras resolver
    inc = {"incidente_id": f"INC-{ahora}-{secrets.token_hex(2)}", "maquina_id": maq["maquina_id"],
           "zona": maq["zona"], "creado_ts": ahora, "severidad": res["severidad"], "score": res["score"],
           "variables_anomalas": res["variables_anomalas"], "componente_probable": res["componente_probable"],
           "estado": "abierto", "timeline": [{"ts": ahora, "evento": "detectado", "score": res["score"]}]}
    ti.put_item(Item=to_dynamo(inc), ConditionExpression="attribute_not_exists(incidente_id)")
    try:
        info = causa_comun.detectar(inc, um)
        if info:
            inc["grupo_id"], inc["grupo_info"] = info["grupo_id"], info
    except Exception:
        print("[causa_comun] error:", traceback.format_exc())
    _iniciar_flujo(inc)


def _iniciar_flujo(inc):
    global _sfn
    arn = get_param("sfn_incidente_arn")
    if not arn:
        print("[detector] sin sfn_incidente_arn: incidente creado, flujo no iniciado")
        return
    _sfn = _sfn or boto3.client("stepfunctions")
    _sfn.start_execution(stateMachineArn=arn, name=inc["incidente_id"],
                         input=json.dumps({"incidente_id": inc["incidente_id"], "maquina_id": inc["maquina_id"],
                                           "zona": inc["zona"], "severidad": inc["severidad"], "score": inc["score"]}))
