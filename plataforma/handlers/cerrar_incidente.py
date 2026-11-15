"""POST /incidentes/{id}/cerrar  body: {"intervencion": "...", "componentes": ["rodamientos"], "notas": "..."}
Cierra el incidente, escribe el historial (tiempo detenida, componentes, técnico y recurrencia a 14 días),
libera al técnico y devuelve la máquina a operación (dolor 10)."""
import json
from botocore.exceptions import ClientError
from common.dynamo import obtener, actualizar, query, tabla, to_dynamo, Key, ahora_ms, es_condicion_fallida
from common.http import respuesta, path_param, leer_body
from core.mensajes import recurrencia
from core.config import DIAS_RECURRENCIA


def lambda_handler(event, context):
    # Entrada (json)
    iid = path_param(event, "id")
    try:
        body = leer_body(event)
    except ValueError:
        return respuesta(400, {"error": "body JSON inválido"})
    inc = obtener("incidentes", {"incidente_id": iid})
    if not inc:
        return respuesta(404, {"error": f"incidente {iid} no existe"})
    componentes = body.get("componentes") or [c for c in [inc.get("componente_probable")] if c and c != "ninguno"]
    intervencion = (body.get("intervencion") or "Mantenimiento correctivo").strip()[:200]

    # Proceso
    ahora = ahora_ms()
    detenida_min = round((ahora - int(inc["creado_ts"])) / 60000, 1)
    previas = query("historial", Key("maquina_id").eq(inc["maquina_id"]) & Key("ts").gte(ahora - DIAS_RECURRENCIA * 86400000))
    previa = recurrencia(previas, inc["maquina_id"], componentes, ahora)
    try:
        # estado = "resuelto" y cerrado_ts son el contrato con el detector de A (cooldown)
        actualizar("incidentes", {"incidente_id": iid},
                   sets={"estado": "resuelto", "cerrado_ts": ahora, "tiempo_detenida_min": detenida_min,
                         "recurrencia": bool(previa)},
                   evento={"evento": "resuelto", "intervencion": intervencion, "componentes": componentes},
                   condicion="#estado <> :c0", valores_cond={":c0": "resuelto"})
    except ClientError as e:
        if es_condicion_fallida(e):
            return respuesta(409, {"error": "el incidente ya estaba resuelto"})
        raise

    registro = {"maquina_id": inc["maquina_id"], "ts": ahora, "incidente_id": iid, "zona": inc.get("zona"),
                "tipo": intervencion, "componentes": componentes, "tecnico_id": inc.get("tecnico_id"),
                "severidad": inc.get("severidad"), "componente_probable": inc.get("componente_probable"),
                "tiempo_detenida_min": detenida_min, "recurrencia": bool(previa),
                "recurrencia_de": previa.get("incidente_id") if previa else None, "notas": body.get("notas")}
    tabla("historial").put_item(Item=to_dynamo(registro))

    if inc.get("tecnico_id"):                         # el técnico queda libre para el siguiente incidente
        try:
            tabla("tecnicos").update_item(Key={"tecnico_id": inc["tecnico_id"]},
                                          UpdateExpression="SET estado = :d REMOVE incidente_actual",
                                          ConditionExpression="incidente_actual = :iid",
                                          ExpressionAttributeValues={":d": "disponible", ":iid": iid})
        except ClientError as e:
            if not es_condicion_fallida(e):
                raise
    # La máquina vuelve a operar: se quita la falla simulada y se reinicia el contador de mantenimiento
    actualizar("maquinas", {"maquina_id": inc["maquina_id"]},
               sets={"estado": "operativa", "horas_desde_mant": 0}, removes=["degradacion"])
    print(json.dumps({"cierre": iid, "tiempo_detenida_min": detenida_min, "recurrencia": bool(previa)}))
    # Salida (json)
    return respuesta(200, {"incidente_id": iid, "estado": "resuelto", "tiempo_detenida_min": detenida_min,
                           "recurrencia": bool(previa), "recurrencia_de": registro["recurrencia_de"]})
