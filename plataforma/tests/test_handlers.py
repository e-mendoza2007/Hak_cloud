"""Pruebas de los handlers contra AWS simulado en memoria (moto). No toca la cuenta real.
Requiere:  pip install "moto[dynamodb,sns,ssm]"      Uso:  python tests/test_handlers.py"""
import json
import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Credenciales falsas: aunque algo escapara de moto, no podría llegar a la cuenta real
for k, v in {"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing", "AWS_SESSION_TOKEN": "testing",
             "AWS_DEFAULT_REGION": "us-east-1", "AWS_REGION": "us-east-1"}.items():
    os.environ[k] = v
os.environ.pop("AWS_PROFILE", None)

import boto3                         # noqa: E402
from decimal import Decimal          # noqa: E402
from moto import mock_aws            # noqa: E402

D = lambda x: Decimal(str(x))        # noqa: E731
S, N = "S", "N"


def crear_tablas(db):
    def t(nombre, keys, gsis=None):
        attrs = {a: ty for a, ty, _ in keys}
        for g in gsis or []:
            attrs.update({a: ty for a, ty, _ in g[1]})
        kw = {"TableName": nombre, "BillingMode": "PAY_PER_REQUEST",
              "AttributeDefinitions": [{"AttributeName": a, "AttributeType": ty} for a, ty in attrs.items()],
              "KeySchema": [{"AttributeName": a, "KeyType": k} for a, _, k in keys]}
        if gsis:
            kw["GlobalSecondaryIndexes"] = [{"IndexName": n, "Projection": {"ProjectionType": "ALL"},
                                             "KeySchema": [{"AttributeName": a, "KeyType": k} for a, _, k in ks]}
                                            for n, ks in gsis]
        db.create_table(**kw)
    t("af_maquinas", [("maquina_id", S, "HASH")])
    t("af_telemetria", [("maquina_id", S, "HASH"), ("ts", N, "RANGE")])
    t("af_incidentes", [("incidente_id", S, "HASH")],
      [("maquina-creado-index", [("maquina_id", S, "HASH"), ("creado_ts", N, "RANGE")]),
       ("zona-creado-index", [("zona", S, "HASH"), ("creado_ts", N, "RANGE")])])
    t("af_historial", [("maquina_id", S, "HASH"), ("ts", N, "RANGE")])
    t("af_tecnicos", [("tecnico_id", S, "HASH")])
    t("af_repuestos", [("ubicacion_id", S, "HASH"), ("componente_id", S, "RANGE")])
    t("af_notificaciones", [("rol", S, "HASH"), ("ts", N, "RANGE")])
    t("af_flota_metricas", [("fecha", S, "HASH"), ("maquina_id", S, "RANGE")])


def sembrar(db):
    m = db.Table("af_maquinas")
    m.put_item(Item={"maquina_id": "M-017", "modelo": "CAM-770", "zona": "Z2", "lat": D(-12.060), "lon": D(-77.050),
                     "estado": "requiere_intervencion", "score_actual": D(0.7), "horas_desde_mant": D(310),
                     "degradacion": {"tipo": "rodamiento"}, "stats": {"x": 1},
                     "preventivo": {"estado": "vencido", "dias_restantes": 0, "fecha_sugerida": "2026-11-15"}})
    m.put_item(Item={"maquina_id": "M-002", "modelo": "EXC-320", "zona": "Z2", "lat": D(-12.061), "lon": D(-77.049),
                     "estado": "operativa", "score_actual": D(0.1), "preventivo": {"estado": "ok"}})
    t = db.Table("af_tecnicos")
    t.put_item(Item={"tecnico_id": "T-01", "nombre": "Ana", "lat": D(-12.0605), "lon": D(-77.0505),
                     "especialidades": ["inyectores"], "estado": "disponible"})
    t.put_item(Item={"tecnico_id": "T-02", "nombre": "Luis", "lat": D(-12.070), "lon": D(-77.040),
                     "especialidades": ["rodamientos"], "estado": "disponible"})
    r = db.Table("af_repuestos")
    r.put_item(Item={"ubicacion_id": "ALM-Z2", "componente_id": "rodamientos", "stock": 1, "minimo": 1})
    r.put_item(Item={"ubicacion_id": "ALM-Z1", "componente_id": "rodamientos", "stock": 3, "minimo": 1})
    db.Table("af_telemetria").put_item(Item={"maquina_id": "M-017", "ts": int(time.time() * 1000), "temperatura": D(95)})


def incidente(db, iid, mid="M-017", sev="alta", score=0.7):
    db.Table("af_incidentes").put_item(Item={
        "incidente_id": iid, "maquina_id": mid, "zona": "Z2", "creado_ts": int(time.time() * 1000) - 600000,
        "severidad": sev, "score": D(score), "variables_anomalas": ["vibracion", "temperatura"],
        "componente_probable": "rodamientos", "estado": "abierto", "timeline": []})


def http(fn, metodo_recurso, path=None, body=None, query=None):
    ev = {"resource": metodo_recurso, "pathParameters": path, "queryStringParameters": query,
          "body": json.dumps(body) if body is not None else None}
    r = fn(ev, None)
    assert r["headers"]["Access-Control-Allow-Origin"]
    return r["statusCode"], json.loads(r["body"])


@mock_aws
def prueba_completa():
    db = boto3.resource("dynamodb")
    crear_tablas(db)
    sembrar(db)
    sns, ssm = boto3.client("sns"), boto3.client("ssm")
    for rol in ("tecnico", "supervisor", "gerente"):
        arn = sns.create_topic(Name=f"af-notif-{rol}")["TopicArn"]
        ssm.put_parameter(Name=f"/arquifusion/sns_topic_{rol}", Value=arn, Type="String")

    from handlers import (asignar_tecnico, reservar_repuesto, escalar, atender_incidente, operaciones,
                          cerrar_incidente, api_incidentes, api_maquinas, api_consultas, planificar_preventivo,
                          analizar_foto)
    inc = lambda iid: json.loads(json.dumps(db.Table("af_incidentes").get_item(Key={"incidente_id": iid})["Item"],
                                            default=float))  # noqa: E731

    # 1) Asignación: severidad alta -> especialista; idempotente; un segundo incidente toma a otro técnico
    incidente(db, "INC-1")
    a = operaciones.lambda_handler({"accion": "asignar", "incidente_id": "INC-1"}, None)   # vía el despachador
    assert a["tecnico_id"] == "T-02" and a["especialista"] and a["eta"]["total_min"] > 120, a
    assert inc("INC-1")["estado"] == "asignado"
    assert asignar_tecnico.lambda_handler({"incidente_id": "INC-1"}, None)["reutilizado"]
    incidente(db, "INC-2", mid="M-002", sev="critica", score=0.9)
    assert asignar_tecnico.lambda_handler({"incidente_id": "INC-2"}, None)["tecnico_id"] == "T-01"
    incidente(db, "INC-X", mid="M-002")
    assert asignar_tecnico.lambda_handler({"incidente_id": "INC-X"}, None)["tecnico_id"] is None   # nadie libre
    print("  ok  asignar técnico (puntaje, idempotencia, concurrencia, sin técnicos)")

    # 2) Repuestos: ALM-Z2 queda en 0 (bajo mínimo); el siguiente incidente usa el almacén siguiente
    r1 = reservar_repuesto.lambda_handler({"incidente_id": "INC-1"}, None)
    assert r1["almacen"] == "ALM-Z2" and r1["stock_restante"] == 0 and r1["bajo_minimo"], r1
    assert reservar_repuesto.lambda_handler({"incidente_id": "INC-1"}, None) == r1                 # idempotente
    r2 = reservar_repuesto.lambda_handler({"incidente_id": "INC-2"}, None)
    assert r2["reservado"] and r2["almacen"] != "ALM-Z2", r2
    from datetime import datetime, timezone
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cz2 = db.Table("af_repuestos").get_item(Key={"ubicacion_id": "ALM-Z2", "componente_id": "rodamientos"})["Item"]
    cz1 = db.Table("af_repuestos").get_item(Key={"ubicacion_id": "ALM-Z1", "componente_id": "rodamientos"})["Item"]
    assert cz2["consumo_por_dia"][hoy] == 1 and cz1["consumo_por_dia"][hoy] == 1, (cz2, cz1)   # idempotente: no suma 2
    print("  ok  reservar repuesto (cercanía, stock condicional, alerta de mínimo, consumo del día)")

    # 3) Notificación: UNA invocación llena las 4 bandejas y devuelve los correos para el Parallel de SNS
    n = operaciones.lambda_handler({"accion": "notificar", "incidente_id": "INC-1"}, None)
    assert {r: c["enviar"] for r, c in n["correos"].items()} == {"tecnico": True, "supervisor": True, "gerente": False}, n
    assert "operador" not in n["correos"] and n["zona"] == "Z2" and n["severidad"] == "alta"
    assert all(len(c["asunto"]) <= 100 and c["asunto"].isascii() for c in n["correos"].values())
    for rol in ("operador", "tecnico", "supervisor", "gerente"):
        st, b = http(api_consultas.lambda_handler, "/notificaciones", query={"rol": rol})
        assert st == 200 and len(b["notificaciones"]) == 1, (rol, b)
    st, bandeja = http(api_consultas.lambda_handler, "/notificaciones", query={"rol": "supervisor"})
    assert "bajo el mínimo" in bandeja["notificaciones"][0]["mensaje"]
    try:
        operaciones.lambda_handler({"accion": "borrar_todo", "incidente_id": "INC-1"}, None)
        raise AssertionError("aceptó una acción inválida")
    except ValueError:
        pass
    print("  ok  notificar a los 4 roles en una invocación (correos para SNS directo, bandejas, acción inválida)")

    # 4) Escalamiento: nivel 1 -> supervisor; si la severidad sube a crítica, el SLA se acorta
    db.Table("af_incidentes").update_item(Key={"incidente_id": "INC-1"}, UpdateExpression="SET severidad = :c",
                                          ExpressionAttributeValues={":c": "critica"})
    e = escalar.lambda_handler({"incidente_id": "INC-1", "control": {"nivel": 0, "sla_seg": 120}}, None)
    assert e == {"nivel": 1, "sla_seg": 60, "ruta": "critica"}, e
    assert inc("INC-1")["estado"] == "escalado"
    print("  ok  escalar (nivel, reclasificación por severidad)")

    # 5) Atender detiene el escalamiento; atender dos veces da 409
    assert http(atender_incidente.lambda_handler, "/incidentes/{id}/atender", {"id": "INC-1"}, {})[0] == 200
    assert http(atender_incidente.lambda_handler, "/incidentes/{id}/atender", {"id": "INC-1"}, {})[0] == 409
    assert escalar.lambda_handler({"incidente_id": "INC-1", "control": {"nivel": 1, "sla_seg": 60}}, None)["nivel"] == 2
    assert inc("INC-1")["estado"] == "en_atencion"                                       # no se pisó
    print("  ok  atender (en_atencion frena el escalamiento)")

    # 6) Cerrar: contrato con el detector de A + historial + técnico libre + máquina operativa
    st, c = http(cerrar_incidente.lambda_handler, "/incidentes/{id}/cerrar", {"id": "INC-1"},
                 {"intervencion": "Cambio de rodamiento", "componentes": ["rodamientos"]})
    assert st == 200 and c["recurrencia"] is False and c["tiempo_detenida_min"] >= 10, c
    i1 = inc("INC-1")
    assert i1["estado"] == "resuelto" and i1["cerrado_ts"] > 0
    tec = db.Table("af_tecnicos").get_item(Key={"tecnico_id": "T-02"})["Item"]
    assert tec["estado"] == "disponible" and "incidente_actual" not in tec
    maq = db.Table("af_maquinas").get_item(Key={"maquina_id": "M-017"})["Item"]
    assert maq["estado"] == "operativa" and "degradacion" not in maq and maq["horas_desde_mant"] == 0
    assert http(cerrar_incidente.lambda_handler, "/incidentes/{id}/cerrar", {"id": "INC-1"}, {})[0] == 409
    # La misma falla vuelve dentro de 14 días -> recurrencia
    incidente(db, "INC-3")
    st, c3 = http(cerrar_incidente.lambda_handler, "/incidentes/{id}/cerrar", {"id": "INC-3"}, {})
    assert c3["recurrencia"] is True and c3["recurrencia_de"] == "INC-1", c3
    print("  ok  cerrar incidente (historial, recurrencia a 14 días, liberar técnico)")

    # 7) API de consulta
    st, lst = http(api_incidentes.lambda_handler, "/incidentes")
    assert st == 200 and [i["incidente_id"] for i in lst["incidentes"]][0] == "INC-2"         # crítica primero
    assert all(i["estado"] != "resuelto" for i in lst["incidentes"]) and "timeline" not in lst["incidentes"][0]
    st, det = http(api_incidentes.lambda_handler, "/incidentes/{id}", {"id": "INC-1"})
    assert st == 200 and len(det["timeline"]) >= 4 and det["maquina"]["modelo"] == "CAM-770"
    assert http(api_incidentes.lambda_handler, "/incidentes/{id}", {"id": "NOPE"})[0] == 404
    st, ms = http(api_maquinas.lambda_handler, "/maquinas")
    assert st == 200 and len(ms["maquinas"]) == 2 and "stats" not in ms["maquinas"][0]
    st, m = http(api_maquinas.lambda_handler, "/maquinas/{id}", {"id": "M-017"})
    assert st == 200 and "stats" not in m["maquina"] and len(m["historial"]) == 2 and m["incidentes"]
    st, tel = http(api_maquinas.lambda_handler, "/maquinas/{id}/telemetria", {"id": "M-017"})
    assert st == 200 and len(tel["lecturas"]) == 1
    st, pnl = http(api_consultas.lambda_handler, "/panel")
    assert st == 200 and len(pnl["maquinas"]) == 2 and len(pnl["tecnicos"]) == 2 and "disponibles" in pnl
    assert [i["incidente_id"] for i in pnl["incidentes"]][0] == "INC-2" and "timeline" not in pnl["incidentes"][0]
    st, fl = http(api_consultas.lambda_handler, "/flota", query={"fecha": "2026-11-15"})
    assert st == 200 and fl["fecha"] == "2026-11-15" and "maquinas" in fl
    for ruta in ("/tecnicos", "/repuestos/estado", "/flota", "/flota/productividad", "/flota/combustible"):
        assert http(api_consultas.lambda_handler, ruta)[0] == 200, ruta
    assert http(api_consultas.lambda_handler, "/notificaciones", query={"rol": "hacker"})[0] == 400
    print("  ok  API de consulta (cola priorizada, detalle, máquinas, telemetría, consultas)")

    # 8) Plan preventivo
    p = planificar_preventivo.lambda_handler({"flota": {"fecha": "2026-11-15"}}, None)
    assert p["novedades"] == 1 and "M-017" in p["mensaje"] and "Se posponen 1" in p["mensaje"], p
    print("  ok  planificar preventivo")

    # 9) Foto del componente: S3 (moto) + Rekognition (doble de prueba)
    import base64
    boto3.client("s3").create_bucket(Bucket="bucket-prueba")
    analizar_foto.BUCKET = "bucket-prueba"
    class RekFalso:
        def detect_labels(self, **kw):
            assert kw["Image"]["Bytes"] == b"JPEGfoto" and kw["MaxLabels"] == 8
            return {"Labels": [{"Name": "Machine", "Confidence": 98.1}, {"Name": "Rust", "Confidence": 88.0}]}
    analizar_foto._rek = RekFalso()
    st, f = http(analizar_foto.lambda_handler, "/incidentes/{id}/foto", {"id": "INC-2"},
                 {"imagen_base64": base64.b64encode(b"JPEGfoto").decode(), "tipo": "image/jpeg"})
    assert st == 200 and f["posible_dano"] == ["Rust"] and f["s3"].startswith("s3://bucket-prueba/fotos/INC-2/"), f
    assert inc("INC-2")["foto"]["etiquetas"][0]["nombre"] == "Machine"
    assert http(analizar_foto.lambda_handler, "/incidentes/{id}/foto", {"id": "INC-2"}, {"imagen_base64": "no-es-base64!!"})[0] == 400
    assert http(analizar_foto.lambda_handler, "/incidentes/{id}/foto", {"id": "NOPE"},
                {"imagen_base64": base64.b64encode(b"x").decode()})[0] == 404
    print("  ok  foto del componente (S3, etiquetas, posible daño, validaciones)")


if __name__ == "__main__":
    prueba_completa()
    print("OK")
