"""Fachadas de la API REST hacia Lambdas de A (datos-ia):
POST /asistente  {"pregunta": "..."}                      -> arquifusion-datos-ia-<stage>-asistente
POST /demo/falla {"maquina_id"|"zona", "tipo", "rampa_min"} o {"...", "limpiar": true} -> ...-demoFalla
Se invocan con boto3 (Lambda -> Lambda) y se responde con CORS y dentro del límite de 29 s de API Gateway."""
import json
import os
import boto3
from botocore.config import Config
from common.http import respuesta, leer_body

_lambda = boto3.client("lambda", config=Config(read_timeout=25, connect_timeout=3, retries={"max_attempts": 0}))
PREFIJO_A = os.environ.get("LAMBDA_A_PREFIX", "arquifusion-datos-ia-dev")
CAMPOS_FALLA = ("maquina_id", "zona", "tipo", "rampa_min", "limpiar")


def _invocar_a(funcion, body):
    r = _lambda.invoke(FunctionName=f"{PREFIJO_A}-{funcion}", Payload=json.dumps({"body": json.dumps(body)}).encode())
    out = json.loads(r["Payload"].read() or "{}")
    if r.get("FunctionError"):
        raise RuntimeError(str(out)[:300])
    return respuesta(out.get("statusCode", 200), json.loads(out.get("body") or "{}"))


def asistente(event, context):
    # Entrada (json)
    try:
        pregunta = (leer_body(event).get("pregunta") or "").strip()
    except ValueError:
        return respuesta(400, {"error": "body JSON inválido"})
    if not pregunta:
        return respuesta(400, {"error": "falta la pregunta"})
    # Proceso
    try:
        return _invocar_a("asistente", {"pregunta": pregunta[:500]})
    except Exception as e:
        print(f"[asistente] {type(e).__name__}: {str(e)[:300]}")
        # Salida (json)
        return respuesta(502, {"error": "El asistente no respondió a tiempo. Intenta de nuevo."})


def demo_falla(event, context):
    # Entrada (json)
    try:
        body = {k: v for k, v in leer_body(event).items() if k in CAMPOS_FALLA}
    except ValueError:
        return respuesta(400, {"error": "body JSON inválido"})
    # Proceso
    try:
        return _invocar_a("demoFalla", body)
    except Exception as e:
        print(f"[demo_falla] {type(e).__name__}: {str(e)[:300]}")
        # Salida (json)
        return respuesta(502, {"error": "no se pudo inyectar la falla"})
