"""Simulador: EventBridge lo invoca cada minuto. Para la demo: {"lecturas": 6} = una lectura cada 10 s."""
import os
import random
import time
from botocore.exceptions import ClientError
from core.simulador import crear_flota, generar_lectura
from common.dynamo import tabla, scan_all, to_dynamo
from common.ingesta_core import procesar_lecturas


def _inicializar_flota():
    """Crea los datos maestros de las máquinas (solo si no existen)."""
    t = tabla("maquinas")
    for m in crear_flota():
        try:
            t.put_item(Item=to_dynamo(m), ConditionExpression="attribute_not_exists(maquina_id)")
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise


def handler(event, context):
    k = int((event or {}).get("lecturas") or os.environ.get("LECTURAS_POR_EJECUCION", 1))
    maquinas = scan_all(tabla("maquinas"))
    if not maquinas:
        _inicializar_flota()
        maquinas = scan_all(tabla("maquinas"))
    ahora = int(time.time() * 1000)
    paso = 60000 // k
    rng = random.Random()
    lecturas = []
    for maq in maquinas:
        if "modelo" not in maq:
            continue
        for i in range(k):
            lecturas.append(generar_lectura(maq, ahora - (k - 1 - i) * paso, rng))
    n = procesar_lecturas(lecturas, dt_s=60.0 / k)
    return {"maquinas": len(maquinas), "lecturas": n}
