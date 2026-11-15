"""FlujoIncidente -> ReservarRepuesto. Entrada: {"incidente_id": "..."}.
Descuenta 1 unidad del componente probable en el almacén con stock más cercano y alerta si queda bajo el mínimo."""
import json
from botocore.exceptions import ClientError
from common.dynamo import obtener, tabla, actualizar, from_dynamo, es_condicion_fallida
from core.asignacion import almacenes_por_cercania
from core.geo import haversine_km
from core.config import ALMACENES


def lambda_handler(event, context):
    # Entrada (json)
    iid = event["incidente_id"]
    inc = obtener("incidentes", {"incidente_id": iid})
    if not inc:
        raise ValueError(f"incidente {iid} no existe")
    if inc.get("repuesto"):                           # idempotente: un Retry no descuenta dos veces
        return inc["repuesto"]
    comp = inc.get("componente_probable")
    if not comp or comp == "ninguno":
        return {"reservado": False, "motivo": "sin componente identificado"}

    # Proceso
    maq = obtener("maquinas", {"maquina_id": inc["maquina_id"]})
    rep = {"reservado": False, "componente": comp, "motivo": "sin stock en ningún almacén"}
    for alm in almacenes_por_cercania(maq):
        try:
            r = tabla("repuestos").update_item(
                Key={"ubicacion_id": alm, "componente_id": comp},
                UpdateExpression="SET stock = stock - :uno",
                ConditionExpression="attribute_exists(stock) AND stock > :cero",
                ExpressionAttributeValues={":uno": 1, ":cero": 0}, ReturnValues="ALL_NEW")
        except ClientError as e:
            if es_condicion_fallida(e):
                continue                              # sin stock aquí: siguiente almacén
            raise
        nuevo = from_dynamo(r["Attributes"])
        rep = {"reservado": True, "componente": comp, "almacen": alm,
               "distancia_km": round(haversine_km(maq["lat"], maq["lon"], *ALMACENES[alm]), 2),
               "stock_restante": nuevo["stock"], "minimo": nuevo.get("minimo", 1),
               "bajo_minimo": nuevo["stock"] < nuevo.get("minimo", 1)}
        break
    actualizar("incidentes", {"incidente_id": iid}, sets={"repuesto": rep},
               evento={"evento": "repuesto_reservado" if rep["reservado"] else "repuesto_sin_stock",
                       "componente": comp, "almacen": rep.get("almacen")})
    print(json.dumps({"repuesto": rep, "incidente_id": iid}))
    # Salida (json)
    return rep
