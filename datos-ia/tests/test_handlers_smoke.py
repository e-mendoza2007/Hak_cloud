"""Humo de handlers con AWS simulado (sin boto3 real):  python3 tests/test_handlers_smoke.py"""
import os, sys, types, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from unittest import mock

# --- boto3 / botocore falsos para poder importar los módulos ---
b3 = types.ModuleType("boto3"); b3.resource = mock.MagicMock(); b3.client = mock.MagicMock()
dyn = types.ModuleType("boto3.dynamodb"); cond = types.ModuleType("boto3.dynamodb.conditions")
class Key:
    def __init__(self, n): self.n = n
    def eq(self, v): return self
    def gte(self, v): return self
    def __and__(self, o): return self
cond.Key = Key
typ = types.ModuleType("boto3.dynamodb.types"); typ.TypeDeserializer = mock.MagicMock
bc = types.ModuleType("botocore"); bce = types.ModuleType("botocore.exceptions")
class ClientError(Exception):
    pass
bce.ClientError = ClientError
for n, m in {"boto3": b3, "boto3.dynamodb": dyn, "boto3.dynamodb.conditions": cond,
             "boto3.dynamodb.types": typ, "botocore": bc, "botocore.exceptions": bce}.items():
    sys.modules[n] = m

from core.simulador import crear_flota, generar_lectura
from handlers import batch_flota, detector_anomalias, asistente, ia_explicar, generar_telemetria, ingesta, demo_falla  # noqa
import handlers.replicar_gcp as rg

T0 = 1_763_100_000_000


def test_batch_flota():
    flota = {m["maquina_id"]: dict(m, score_actual=0.7 if i < 3 else 0.1,
                                   componente_probable="rodamientos" if i < 3 else "ninguno")
             for i, m in enumerate(crear_flota())}
    for m in flota.values():
        m["zona"] = "Z2" if m["maquina_id"] in ("M-001", "M-002", "M-003") else m["zona"]
    metricas = [{"maquina_id": mid, "seg_op": 40000 + 1000 * i, "seg_tot": 86400, "litros": 300 + i,
                 "prod": 100 + i, "temp_s": 86 * (40000 + 1000 * i)} for i, mid in enumerate(flota)]
    guardado = {}
    with mock.patch.object(batch_flota, "tabla", lambda n: n), \
         mock.patch.object(batch_flota, "scan_all", lambda t: list(flota.values()) if t == "maquinas" else
                           [{"ubicacion_id": "ALM-Z2", "componente_id": "rodamientos", "stock": 1, "consumo_historial": [2, 3, 2, 3, 2, 9]}]), \
         mock.patch.object(batch_flota, "query_all", lambda t, **kw: metricas if True else []), \
         mock.patch.object(batch_flota, "set_attrs", lambda t, k, a: guardado.__setitem__((t, tuple(k.values())), a)):
        out = batch_flota.handler({"fecha": "2026-11-15"}, None)
    print("  batch:", out)
    resumen = guardado[("metricas", ("2026-11-15", "#RESUMEN"))]
    assert resumen["alertas_repuestos"] and resumen["consumo_irregular"]
    assert out["maquinas"] == 30


def test_detector_crea_incidente():
    maq = dict(crear_flota()[0])
    creados, attrs = [], {}
    ti = mock.MagicMock(); ti.query.return_value = {"Items": []}
    ti.put_item.side_effect = lambda **kw: creados.append(kw["Item"])
    tm = mock.MagicMock(); tm.get_item.return_value = {"Item": maq}
    tabs = {"maquinas": tm, "incidentes": ti}
    maq["degradacion"] = {"tipo": "rodamiento", "inicio_ts": T0, "rampa_min": 10}
    rng = random.Random(3)
    with mock.patch.object(detector_anomalias, "tabla", lambda n: tabs[n]), \
         mock.patch.object(detector_anomalias, "get_umbrales", lambda: {"media": .4, "alta": .6, "critica": .8, "cooldown_min": 30,
                                                                      "causa_comun_min_maquinas": 3, "ventana_min": 60}), \
         mock.patch.object(detector_anomalias, "_pares", lambda m: None), \
         mock.patch.object(detector_anomalias, "set_attrs", lambda t, k, a: (maq.update(a) if "stats" in a else None)), \
         mock.patch.object(detector_anomalias.causa_comun, "detectar", lambda inc, um: None), \
         mock.patch.object(detector_anomalias, "_iniciar_flujo", lambda inc: creados.append(("SFN", inc["incidente_id"]))), \
         mock.patch.object(detector_anomalias, "to_dynamo", lambda x: x):
        for i in range(12):
            l = generar_lectura(maq, T0 + i * 60000, rng)
            detector_anomalias.procesar(l)
    print("  incidentes creados:", [c if isinstance(c, tuple) else (c["incidente_id"], c["severidad"], c["componente_probable"]) for c in creados])
    assert any(isinstance(c, dict) for c in creados) and any(isinstance(c, tuple) for c in creados)


def test_firestore_valor():
    from decimal import Decimal
    assert rg._valor(Decimal("3")) == {"integerValue": "3"}
    assert rg._valor(Decimal("3.5")) == {"doubleValue": 3.5}
    assert rg._valor({"a": [1, "x", None]})["mapValue"]["fields"]["a"]["arrayValue"]["values"][1] == {"stringValue": "x"}


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            print(nombre); fn()
    print("OK")
