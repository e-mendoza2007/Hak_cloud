"""Carga técnicos y repuestos de ejemplo. Uso:  python scripts/seed.py
(Las máquinas las crea el simulador la primera vez que corre.)"""
import random
from decimal import Decimal
import boto3

db = boto3.resource("dynamodb")
COMPONENTES = ["rodamientos", "refrigeracion", "bomba_hidraulica", "inyectores", "motor_transmision"]
ZONAS = {"Z1": (-12.040, -77.030), "Z2": (-12.060, -77.050), "Z3": (-12.080, -77.020), "Z4": (-12.050, -77.000)}
D = lambda x: Decimal(str(x))  # noqa: E731

tec = db.Table("af_tecnicos")
rnd = random.Random(5)
for i in range(8):
    zona = f"Z{(i % 4) + 1}"
    lat, lon = ZONAS[zona]
    esp = [COMPONENTES[i % 5], COMPONENTES[(i + 2) % 5]]
    tec.put_item(Item={"tecnico_id": f"T-{i + 1:02d}", "nombre": f"Técnico {i + 1}", "zona_base": zona,
                       "especialidades": esp, "lat": D(round(lat + rnd.uniform(-.005, .005), 5)),
                       "lon": D(round(lon + rnd.uniform(-.005, .005), 5)), "estado": "disponible"})
rep = db.Table("af_repuestos")
for zona in ZONAS:
    for c in COMPONENTES:
        stock = 1 if (zona == "Z2" and c in ("rodamientos", "refrigeracion")) else 3   # Z2 con poco stock (demo)
        rep.put_item(Item={"ubicacion_id": f"ALM-{zona}", "componente_id": c, "stock": stock, "minimo": 1,
                           "consumo_historial": [D(x) for x in (2, 3, 2, 3, 2, 3)]})
print("Cargados 8 técnicos y 20 registros de repuestos.")
