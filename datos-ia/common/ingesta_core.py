"""Camino único de ingesta: lo usan la API (POST /ingesta) y el simulador."""
import time
from decimal import Decimal
from botocore.exceptions import ClientError
from core.config import VARS
from .dynamo import tabla, to_dynamo

REQUERIDOS = ["maquina_id", "ts", "temperatura", "vibracion", "presion", "combustible_lh",
              "carga_t", "velocidad", "rpm", "estado"]
ESTADOS = ("operativa", "detenida", "requiere_intervencion", "mantenimiento")
D = lambda x: Decimal(str(round(float(x), 6)))  # noqa: E731


def validar(l):
    faltan = [k for k in REQUERIDOS if k not in l]
    if faltan:
        raise ValueError(f"faltan campos: {faltan}")
    if l["estado"] not in ESTADOS:
        raise ValueError("estado inválido")
    return l


def procesar_lecturas(lecturas, dt_s=60.0):
    """Guarda telemetría, actualiza la máquina y acumula los contadores del día."""
    lecturas = [validar(l) for l in lecturas]
    ttl = int(time.time()) + 7 * 86400
    with tabla("telemetria").batch_writer(overwrite_by_pkeys=["maquina_id", "ts"]) as bw:
        for l in lecturas:
            bw.put_item(Item=to_dynamo({**l, "ttl": ttl}))
    por_maq = {}
    for l in lecturas:
        por_maq.setdefault(l["maquina_id"], []).append(l)
    for mid, ls in por_maq.items():
        _actualizar_maquina(mid, ls, dt_s)
        _acumular_dia(mid, ls, dt_s)
    return len(lecturas)


def _actualizar_maquina(mid, ls, dt_s):
    ult = ls[-1]
    horas_op = sum(dt_s for l in ls if l["estado"] == "operativa") / 3600
    ultima = {k: ult[k] for k in VARS + ["carga_t", "velocidad", "estado"]}
    t = tabla("maquinas")
    t.update_item(
        Key={"maquina_id": mid},
        UpdateExpression=("SET ultima = :u, ultima_lectura_ts = :ts, estado_lectura = :e, "
                          "zona = if_not_exists(zona, :z), lat = if_not_exists(lat, :la), "
                          "lon = if_not_exists(lon, :lo) ADD horas_totales :h, horas_desde_mant :h"),
        ExpressionAttributeValues={":u": to_dynamo(ultima), ":ts": ult["ts"], ":e": ult["estado"],
                                   ":z": ult.get("zona", "Z1"), ":la": D(ult.get("lat", 0)),
                                   ":lo": D(ult.get("lon", 0)), ":h": D(horas_op)})
    # El estado visible solo cambia si no hay una intervención en curso.
    try:
        t.update_item(Key={"maquina_id": mid}, UpdateExpression="SET estado = :e",
                      ConditionExpression="attribute_not_exists(estado) OR NOT (estado IN (:ri, :mt))",
                      ExpressionAttributeValues={":e": ult["estado"], ":ri": "requiere_intervencion",
                                                 ":mt": "mantenimiento"})
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise


def _acumular_dia(mid, ls, dt_s):
    fecha = time.strftime("%Y-%m-%d", time.gmtime(ls[-1]["ts"] / 1000))
    op = [l for l in ls if l["estado"] == "operativa"]
    tabla("metricas").update_item(
        Key={"fecha": fecha, "maquina_id": mid},
        UpdateExpression="ADD seg_op :so, seg_tot :st, litros :li, prod :pr, temp_s :ts",
        ExpressionAttributeValues={
            ":so": D(len(op) * dt_s), ":st": D(len(ls) * dt_s),
            ":li": D(sum(l["combustible_lh"] for l in ls) * dt_s / 3600),
            ":pr": D(sum(l["carga_t"] for l in op) * dt_s / 3600),
            ":ts": D(sum(l["temperatura"] for l in op) * dt_s)})
