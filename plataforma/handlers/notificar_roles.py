"""FlujoIncidente -> PrepararNotificaciones (vía la Lambda operaciones). Entrada: {"incidente_id": "..."}.
Una sola invocación para los 4 roles: arma el mensaje de cada uno, lo deja en su bandeja y devuelve los
correos que Step Functions publica directamente en SNS (Parallel de sns:publish, sin más Lambdas)."""
import json
from common.dynamo import obtener
from common.notificar import guardar_bandeja
from core.mensajes import canal, mensaje, asunto
from core.config import ROLES


def lambda_handler(event, context):
    # Entrada (json)
    iid = event["incidente_id"]
    inc = obtener("incidentes", {"incidente_id": iid})    # ya trae IA, técnico y repuesto
    if not inc:
        raise ValueError(f"incidente {iid} no existe")
    # Proceso
    correos, canales = {}, {}
    for rol in ROLES:
        via = canal(rol, inc.get("severidad"))
        texto = mensaje(rol, inc)
        guardar_bandeja(rol, inc, texto, via, "incidente")
        canales[rol] = via
        if rol != "operador":                                 # el operador no tiene tópico: solo bandeja
            correos[rol] = {"enviar": via == "email", "asunto": asunto(inc), "mensaje": texto}
    print(json.dumps({"notificaciones": iid, "canales": canales}))
    # Salida (json): lo que necesita el Parallel de SNS
    return {"correos": correos, "zona": inc.get("zona") or "-", "severidad": inc.get("severidad") or "-"}
