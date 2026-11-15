"""Streams de af_incidentes y af_maquinas -> Firestore (segunda nube) por REST.
Necesita el layer con google-auth + requests y los parámetros /arquifusion/gcp_service_account."""
import json
import time
import traceback
from decimal import Decimal
from boto3.dynamodb.types import TypeDeserializer
from common.params import get_param

_deser = TypeDeserializer()
_creds = None
_info = None
COLECCION = {"af_incidentes": ("incidentes", "incidente_id"), "af_maquinas": ("maquinas", "maquina_id")}
CAMPOS_PESADOS = {"stats", "hist_score", "ultima"}   # no se replican (ruido y costo)


def _token():
    global _creds, _info
    from google.oauth2 import service_account
    import google.auth.transport.requests as gtr
    if _creds is None:
        _info = json.loads(get_param("gcp_service_account"))
        _creds = service_account.Credentials.from_service_account_info(
            _info, scopes=["https://www.googleapis.com/auth/datastore"])
    if not _creds.valid:
        _creds.refresh(gtr.Request())
    return _creds.token, _info["project_id"]


def _valor(v):
    """Python -> tipos de Firestore REST."""
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, Decimal):
        return {"integerValue": str(int(v))} if v == v.to_integral_value() else {"doubleValue": float(v)}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, (list, tuple, set)):
        return {"arrayValue": {"values": [_valor(x) for x in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: _valor(x) for k, x in v.items()}}}
    return {"stringValue": str(v)}


def handler(event, context):
    import requests
    ok = 0
    for rec in event.get("Records", []):
        try:
            if rec.get("eventName") not in ("INSERT", "MODIFY"):
                continue
            tabla = rec["eventSourceARN"].split("/")[1]
            if tabla not in COLECCION:
                continue
            col, pk = COLECCION[tabla]
            img = {k: _deser.deserialize(v) for k, v in rec["dynamodb"]["NewImage"].items()}
            campos = {k: _valor(v) for k, v in img.items() if k not in CAMPOS_PESADOS}
            tok, pid = _token()
            url = (f"https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/"
                   f"{col}/{img[pk]}")
            r = requests.patch(url, headers={"Authorization": f"Bearer {tok}"},
                               json={"fields": campos}, timeout=30)
            r.raise_for_status()
            ok += 1
        except Exception:
            print("[replicar_gcp] error:", traceback.format_exc()[-600:])
    return {"replicados": ok}
