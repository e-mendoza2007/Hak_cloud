"""Parámetros y secretos en SSM Parameter Store (/arquifusion/...). Con caché de 5 minutos."""
import json
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


def get_umbrales():
    from core.config import UMBRALES_DEF
    raw = get_param("umbrales")
    try:
        return {**UMBRALES_DEF, **(json.loads(raw) if raw else {})}
    except ValueError:
        return dict(UMBRALES_DEF)
