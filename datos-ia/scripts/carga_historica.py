"""Carga histórica desde esta PC (Python + boto3, sin Lambdas): una lectura por hora y máquina durante
los últimos 7 días (30 máquinas x 168 h = 5 040 lecturas) y sus contadores diarios en af_flota_metricas.

- Las lecturas llevan historico=true: el filtro de eventos del trigger del detector las descarta, así que
  no se invoca ninguna Lambda ni se crean incidentes con datos viejos.
- No toca af_maquinas (el estado actual de la flota no cambia).
- Se protege contra cargas dobles con el registro '#CARGA_HISTORICA' en af_flota_metricas.

Uso:  python scripts/carga_historica.py [horas=168] [--forzar]"""
import os
import random
import sys
import time
from collections import defaultdict
from decimal import Decimal

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")   # por si la terminal no tiene región configurada
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import boto3                                        # noqa: E402
from core.simulador import generar_lectura          # noqa: E402
from common.dynamo import tabla, scan_all, to_dynamo  # noqa: E402
from common.ingesta_core import _acumular_dia       # noqa: E402

HORA_MS = 3600 * 1000


def main(args):
    horas = int(next((a for a in args if a.isdigit()), 168))
    forzar = "--forzar" in args
    metricas = tabla("metricas")
    marca = metricas.get_item(Key={"fecha": "#CARGA_HISTORICA", "maquina_id": "#CARGA_HISTORICA"}).get("Item")
    if marca and not forzar:
        sys.exit(f"Ya hay una carga histórica ({marca.get('lecturas')} lecturas, {marca.get('cuando')}). "
                 "Usa --forzar si de verdad quieres sumar otra.")

    print(f"Cuenta AWS: {boto3.client('sts').get_caller_identity()['Account']}")
    maquinas = [m for m in scan_all(tabla("maquinas")) if m.get("modelo")]
    if not maquinas:
        sys.exit("af_maquinas está vacía: corre primero 'python scripts/demo.py correr 60' para crear la flota.")
    for m in maquinas:
        m.pop("degradacion", None)                     # el histórico es operación normal

    fin = (int(time.time() * 1000) // HORA_MS) * HORA_MS   # última hora completa
    rng = random.Random(2026)
    por_maquina_dia = defaultdict(list)
    n = 0
    t0 = time.time()
    with tabla("telemetria").batch_writer(overwrite_by_pkeys=["maquina_id", "ts"]) as bw:
        for h in range(horas, 0, -1):
            ts = fin - h * HORA_MS
            for m in maquinas:
                lect = generar_lectura(m, ts, rng)
                ttl = ts // 1000 + 7 * 86400               # vence a los 7 días de la lectura, como la ingesta real
                bw.put_item(Item=to_dynamo({**lect, "historico": True, "ttl": ttl}))
                por_maquina_dia[(m["maquina_id"], time.strftime("%Y-%m-%d", time.gmtime(ts / 1000)))].append(lect)
                n += 1
    print(f"Telemetría: {n} lecturas escritas en {time.time() - t0:.0f} s")

    for (mid, _dia), ls in sorted(por_maquina_dia.items()):
        _acumular_dia(mid, ls, dt_s=3600.0)          # mismas fórmulas que la ingesta real
    print(f"Métricas diarias: {len(por_maquina_dia)} filas (máquina x día) en af_flota_metricas")

    metricas.put_item(Item={"fecha": "#CARGA_HISTORICA", "maquina_id": "#CARGA_HISTORICA",
                            "lecturas": n, "horas": horas, "cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "desde_ts": Decimal(fin - horas * HORA_MS), "hasta_ts": Decimal(fin)})
    print("Listo. Ahora corre PreventivoDiario para recalcular productividad, combustible y preventivo.")


if __name__ == "__main__":
    main(sys.argv[1:])
