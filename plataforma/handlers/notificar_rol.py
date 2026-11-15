"""FlujoIncidente -> NotificarPorRol (una rama del Parallel por rol). Entrada: {"incidente_id", "rol"}.
Cada rol recibe un texto distinto y por un canal distinto (email o solo bandeja) según la severidad."""
from common.dynamo import obtener
from common.notificar import entregar
from core.mensajes import canal, mensaje, asunto
from core.config import ROLES


def lambda_handler(event, context):
    # Entrada (json)
    iid, rol = event["incidente_id"], event["rol"]
    if rol not in ROLES:
        raise ValueError(f"rol inválido: {rol}")
    inc = obtener("incidentes", {"incidente_id": iid})   # se lee de DynamoDB: ya trae IA, técnico y repuesto
    if not inc:
        raise ValueError(f"incidente {iid} no existe")
    # Proceso
    via = canal(rol, inc.get("severidad"))
    resultado = entregar(rol, inc, mensaje(rol, inc), via, asunto(inc))
    # Salida (json)
    return resultado
