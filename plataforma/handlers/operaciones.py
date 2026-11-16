"""Una sola Lambda para las tareas de la Persona B dentro de FlujoIncidente, con tope de concurrencia 1
(regla de la hackathon: menos de 10 Lambdas a la vez). Step Functions sigue mostrando cada paso por
separado; aquí solo se elige el handler según 'accion'. Entrada: {"accion": "...", "incidente_id": "...", ...}"""
import json
from handlers import asignar_tecnico, reservar_repuesto, notificar_roles, escalar

ACCIONES = {
    "asignar": asignar_tecnico.lambda_handler,
    "reservar": reservar_repuesto.lambda_handler,
    "notificar": notificar_roles.lambda_handler,
    "escalar": escalar.lambda_handler,
}


def lambda_handler(event, context):
    accion = event.get("accion")
    if accion not in ACCIONES:
        raise ValueError(f"accion inválida: {accion}; válidas: {list(ACCIONES)}")
    print(json.dumps({"operacion": accion, "incidente_id": event.get("incidente_id")}))
    return ACCIONES[accion](event, context)
