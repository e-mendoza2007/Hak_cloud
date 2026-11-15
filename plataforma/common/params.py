"""Variables globales en SSM Parameter Store (/arquifusion/...), con caché de 5 minutos por contenedor."""
import os
import time
import boto3

PREFIJO = os.environ.get("SSM_PREFIX", "/arquifusion")
_cache = {}
_ssm = None


def get_param(nombre, default=None):
    global _ssm
    ahora = time.time()
    hit = _cache.get(nombre)
    if hit and hit[1] > ahora:
        return hit[0]
    try:
        _ssm = _ssm or boto3.client("ssm")
        val = _ssm.get_parameter(Name=f"{PREFIJO}/{nombre}", WithDecryption=True)["Parameter"]["Value"]
    except Exception as e:  # parámetro inexistente o sin permiso
        print(f"[params] {nombre}: {type(e).__name__}")
        val = default
    _cache[nombre] = (val, ahora + 300)
    return val
