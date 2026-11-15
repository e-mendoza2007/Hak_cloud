"""FlujoIncidente -> AsignarTecnico. Entrada: {"incidente_id": "..."}.
Elige al mejor técnico disponible (cercanía + especialidad - carga, según severidad) y calcula la ETA."""
import json
from botocore.exceptions import ClientError
from common.dynamo import obtener, scan_all, tabla, actualizar, es_condicion_fallida
from core.asignacion import rankear, eta


def lambda_handler(event, context):
    # Entrada (json)
    iid = event["incidente_id"]
    inc = obtener("incidentes", {"incidente_id": iid})
    if not inc:
        raise ValueError(f"incidente {iid} no existe")
    if inc.get("tecnico_id"):                         # idempotente: un Retry no reasigna
        return {"tecnico_id": inc["tecnico_id"], "reutilizado": True, **(inc.get("asignacion") or {})}

    # Proceso
    maq = obtener("maquinas", {"maquina_id": inc["maquina_id"]})
    comp, sev = inc.get("componente_probable"), inc.get("severidad", "media")
    candidatos = rankear(scan_all("tecnicos"), maq, comp, sev)
    for c in candidatos:
        t = c["tecnico"]
        try:                                          # reserva atómica: dos incidentes no toman al mismo técnico
            tabla("tecnicos").update_item(
                Key={"tecnico_id": t["tecnico_id"]},
                UpdateExpression="SET estado = :ocupado, incidente_actual = :iid ADD carga :uno",
                ConditionExpression="estado = :disp",
                ExpressionAttributeValues={":ocupado": "ocupado", ":iid": iid, ":uno": 1, ":disp": "disponible"})
        except ClientError as e:
            if es_condicion_fallida(e):
                continue                              # otro flujo lo tomó primero: siguiente candidato
            raise
        asignacion = {"tecnico_id": t["tecnico_id"], "nombre": t.get("nombre"), "puntaje": c["puntaje"],
                      "distancia_km": c["distancia_km"], "especialista": c["especialista"],
                      "eta": eta(c["distancia_km"], comp, c["especialista"])}
        try:
            actualizar("incidentes", {"incidente_id": iid},
                       sets={"tecnico_id": t["tecnico_id"], "estado": "asignado", "asignacion": asignacion},
                       evento={"evento": "tecnico_asignado", "tecnico_id": t["tecnico_id"],
                               "eta_min": asignacion["eta"]["total_min"]},
                       condicion="#estado IN (:c0, :c1)", valores_cond={":c0": "abierto", ":c1": "escalado"})
        except ClientError as e:
            if not es_condicion_fallida(e):
                raise
            # El incidente ya fue atendido o cerrado mientras tanto: se libera al técnico
            tabla("tecnicos").update_item(Key={"tecnico_id": t["tecnico_id"]},
                                          UpdateExpression="SET estado = :d REMOVE incidente_actual",
                                          ExpressionAttributeValues={":d": "disponible"})
            return {"tecnico_id": None, "motivo": "el incidente ya no está abierto"}
        print(json.dumps({"asignacion": asignacion, "incidente_id": iid, "candidatos": len(candidatos)}))
        # Salida (json)
        return asignacion

    actualizar("incidentes", {"incidente_id": iid}, evento={"evento": "sin_tecnico_disponible"})
    print(json.dumps({"asignacion": None, "incidente_id": iid}))
    return {"tecnico_id": None, "motivo": "sin técnicos disponibles"}
