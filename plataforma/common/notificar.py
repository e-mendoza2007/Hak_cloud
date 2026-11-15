"""Entrega de mensajes: bandeja en DynamoDB (af_notificaciones) + email por SNS (tópico del rol en SSM)."""
import json
import boto3
from botocore.exceptions import ClientError
from .dynamo import tabla, ahora_ms, to_dynamo, es_condicion_fallida
from .params import get_param
from core.mensajes import a_ascii

_sns = None


def guardar_bandeja(rol, inc, texto, canal, tipo):
    """Registra la notificación en la bandeja del rol (PK rol, SK ts). Si dos llegan en el mismo ms, corre 1 ms."""
    ts = ahora_ms()
    item = {"rol": rol, "incidente_id": inc.get("incidente_id"), "maquina_id": inc.get("maquina_id"),
            "zona": inc.get("zona"), "severidad": inc.get("severidad"), "tipo": tipo,
            "mensaje": texto, "canal": canal, "leida": False}
    for _ in range(5):
        try:
            tabla("notificaciones").put_item(Item=to_dynamo({**item, "ts": ts}),
                                             ConditionExpression="attribute_not_exists(ts)")
            return ts
        except ClientError as e:
            if not es_condicion_fallida(e):
                raise
            ts += 1
    raise RuntimeError("no se pudo registrar la notificación")


def enviar_email(rol, asunto, texto, inc):
    """Publica en el tópico SNS del rol. MessageAttributes permite filtrar suscripciones por zona o severidad."""
    global _sns
    topic = get_param(f"sns_topic_{rol}")
    if not topic:
        print(f"[notificar] sin tópico para {rol}: solo bandeja")
        return None
    _sns = _sns or boto3.client("sns")
    r = _sns.publish(TopicArn=topic, Subject=a_ascii(asunto)[:100], Message=texto,
                     MessageAttributes={
                         "zona": {"DataType": "String", "StringValue": str(inc.get("zona") or "-")},
                         "severidad": {"DataType": "String", "StringValue": str(inc.get("severidad") or "-")}})
    return r.get("MessageId")


def entregar(rol, inc, texto, canal, asunto, tipo="incidente"):
    ts = guardar_bandeja(rol, inc, texto, canal, tipo)
    msg_id = enviar_email(rol, asunto, texto, inc) if canal == "email" else None
    print(json.dumps({"notificacion": tipo, "rol": rol, "canal": canal, "incidente_id": inc.get("incidente_id"),
                      "sns_message_id": msg_id}))
    return {"rol": rol, "canal": canal, "ts": ts, "email_enviado": bool(msg_id)}
