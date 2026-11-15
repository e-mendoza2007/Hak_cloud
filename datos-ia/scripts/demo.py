"""Herramienta de demo (invoca las Lambdas directo; no necesita URLs).
  python scripts/demo.py correr [segundos=600] [intervalo=10]   # simulador en bucle (déjalo en otra terminal)
  python scripts/demo.py falla M-017 rodamiento 4               # falla en una máquina (rampa en minutos)
  python scripts/demo.py zona Z2 refrigeracion 4                # falla en toda una zona (causa común)
  python scripts/demo.py limpiar M-017                          # (o: limpiar zona Z2)
  python scripts/demo.py estado                                 # incidentes abiertos y máquinas con más riesgo
  python scripts/demo.py ia INC-...                             # explicación de IA de un incidente
  python scripts/demo.py preguntar "¿Qué máquinas atiendo primero?"
  python scripts/demo.py batch                                  # productividad, combustible, preventivo, repuestos
  python scripts/demo.py suscribir tu_correo@gmail.com          # recibir los emails por rol
Tipos de falla: rodamiento | refrigeracion | inyectores | hidraulica"""
import json
import sys
import time
from decimal import Decimal
import boto3

STAGE = "dev"
lam = boto3.client("lambda")
db = boto3.resource("dynamodb")


def nombre(fn):
    return f"arquifusion-datos-ia-{STAGE}-{fn}"


def invocar(fn, payload):
    r = lam.invoke(FunctionName=nombre(fn), Payload=json.dumps(payload).encode())
    out = json.loads(r["Payload"].read() or "null")
    if r.get("FunctionError"):
        raise SystemExit(f"Error en {fn}: {out}")
    return out


def http(fn, body):
    out = invocar(fn, {"body": json.dumps(body)})
    return json.loads(out["body"]) if isinstance(out, dict) and "body" in out else out


def num(x):
    return float(x) if isinstance(x, Decimal) else x


def scan(t):
    items, kw = [], {}
    while True:
        r = db.Table(t).scan(**kw)
        items += r["Items"]
        if "LastEvaluatedKey" not in r:
            return items
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def main(a):
    if not a:
        print(__doc__); return
    c = a[0]
    if c == "correr":
        total, paso = int(a[1]) if len(a) > 1 else 600, int(a[2]) if len(a) > 2 else 10
        fin = time.time() + total
        print(f"Simulador en bucle: {total}s, una ronda cada {paso}s (Ctrl+C para parar)")
        while time.time() < fin:
            t0 = time.time()
            print(" ", time.strftime("%H:%M:%S"), invocar("generarTelemetria", {"lecturas": 1}))
            time.sleep(max(0, paso - (time.time() - t0)))
    elif c == "falla":
        print(http("demoFalla", {"maquina_id": a[1], "tipo": a[2], "rampa_min": int(a[3]) if len(a) > 3 else 5}))
    elif c == "zona":
        print(http("demoFalla", {"zona": a[1], "tipo": a[2], "rampa_min": int(a[3]) if len(a) > 3 else 5}))
    elif c == "limpiar":
        key = {"zona": a[2]} if a[1] == "zona" else {"maquina_id": a[1]}
        print(http("demoFalla", {**key, "limpiar": True}))
    elif c == "estado":
        incs = [i for i in scan("af_incidentes") if i.get("estado") != "resuelto"]
        incs.sort(key=lambda i: i["creado_ts"], reverse=True)
        print(f"INCIDENTES ABIERTOS ({len(incs)})")
        for i in incs[:15]:
            print(f"  {i['incidente_id']} | {i['maquina_id']} {i['zona']} | {i['severidad']:8} score {num(i['score'])} | "
                  f"{i.get('componente_probable')} | IA: {(i.get('ia') or {}).get('fuente', '-')}"
                  + (f" | GRUPO {i['grupo_id']} ({num(i['grupo_info']['n_maquinas'])} máq.)" if i.get("grupo_id") else ""))
        maqs = sorted(scan("af_maquinas"), key=lambda m: num(m.get("score_actual", 0)), reverse=True)[:6]
        print("MAQUINAS CON MAS RIESGO")
        for m in maqs:
            print(f"  {m['maquina_id']} {m.get('zona')} | {m.get('estado')} | score {num(m.get('score_actual', 0))} | {m.get('componente_probable', '-')}")
    elif c == "ia":
        out = invocar("iaExplicar", {"incidente_id": a[1]})
        print(json.dumps(json.loads(json.dumps(out, default=num)), indent=2, ensure_ascii=False))
    elif c == "preguntar":
        r = http("asistente", {"pregunta": " ".join(a[1:])})
        print(f"[{r.get('fuente')}] {r.get('respuesta', r)}")
    elif c == "batch":
        print(invocar("batchFlota", {}))
    elif c == "suscribir":
        ssm, sns = boto3.client("ssm"), boto3.client("sns")
        for rol in ("tecnico", "supervisor", "gerente"):
            arn = ssm.get_parameter(Name=f"/arquifusion/sns_topic_{rol}")["Parameter"]["Value"]
            sns.subscribe(TopicArn=arn, Protocol="email", Endpoint=a[1])
        print("Revisa tu correo y confirma las 3 suscripciones.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
