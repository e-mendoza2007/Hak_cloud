"""FlujoIncidente -> Escalar. Entrada: {"incidente_id", "control": {"nivel", "sla_seg", "ruta"}}.
Nivel 1 avisa al supervisor y nivel 2 al gerente. Si la severidad subió mientras se esperaba, acorta el SLA."""
import json
import os
from botocore.exceptions import ClientError
from common.dynamo import obtener, actualizar, es_condicion_fallida
from common.notificar import entregar
from core.mensajes import mensaje_escalamiento, asunto

SLA_SEG = json.loads(os.environ.get("SLA_SEG", '{"critica": 60, "alta": 120, "media": 180}'))


def lambda_handler(event, context):
    # Entrada (json)
    iid = event["incidente_id"]
    control = event.get("control") or {}
    nivel = int(control.get("nivel", 0)) + 1
    sla_actual = int(control.get("sla_seg", SLA_SEG["media"]))
    inc = obtener("incidentes", {"incidente_id": iid})
    if not inc:
        raise ValueError(f"incidente {iid} no existe")

    # Proceso
    sev = inc.get("severidad", "media")              # severidad ACTUAL (el detector de A la sube en DynamoDB)
    nuevo_sla = min(sla_actual, int(SLA_SEG.get(sev, sla_actual)))
    salida = {"nivel": nivel, "sla_seg": nuevo_sla, "ruta": sev}
    destino = "supervisor" if nivel == 1 else "gerente"
    try:
        actualizar("incidentes", {"incidente_id": iid},
                   sets={"estado": "escalado", "nivel_escalamiento": nivel},
                   evento={"evento": "escalado", "nivel": nivel, "destino": destino, "severidad": sev},
                   condicion="#estado IN (:c0, :c1, :c2)",
                   valores_cond={":c0": "abierto", ":c1": "asignado", ":c2": "escalado"})
    except ClientError as e:
        if es_condicion_fallida(e):                   # lo atendieron justo ahora: no se escala
            return salida
        raise
    inc["severidad"] = sev
    entregar(destino, inc, mensaje_escalamiento(destino, inc, nivel, sla_actual), "email",
             asunto(inc, prefijo=f"ESCALADO nivel {nivel}"), tipo="escalamiento")
    # Salida (json)
    return salida
