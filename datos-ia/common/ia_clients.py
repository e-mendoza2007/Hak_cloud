"""Cadena de IA: Bedrock -> Gemini -> (el que llama usa su plantilla)."""
import json
import os
import urllib.request
import boto3
from .params import get_param

_bedrock = None


def llamar_bedrock(prompt, max_tokens=350):
    global _bedrock
    modelo = get_param("bedrock_model_id")
    if not modelo:
        raise RuntimeError("falta /arquifusion/bedrock_model_id")
    _bedrock = _bedrock or boto3.client(
        "bedrock-runtime", region_name=get_param("bedrock_region", os.environ.get("AWS_REGION", "us-east-1")))
    r = _bedrock.converse(modelId=modelo, messages=[{"role": "user", "content": [{"text": prompt}]}],
                          inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2})
    return r["output"]["message"]["content"][0]["text"]


def llamar_gemini(prompt, max_tokens=350):
    key = get_param("gemini_api_key")
    if not key:
        raise RuntimeError("falta /arquifusion/gemini_api_key")
    modelo = get_param("gemini_model", "gemini-flash-latest")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def generar(prompt, max_tokens=350, validar=None):
    """Devuelve (texto, fuente). fuente = bedrock | gemini | None (usar plantilla).
    /arquifusion/ia_proveedores permite forzar el orden, p. ej. 'gemini' o 'bedrock,gemini'."""
    orden = [p.strip() for p in (get_param("ia_proveedores", "bedrock,gemini") or "").split(",") if p.strip()]
    fn = {"bedrock": llamar_bedrock, "gemini": llamar_gemini}
    for nombre in orden:
        try:
            texto = fn[nombre](prompt, max_tokens)
            if validar is None or validar(texto):
                return texto, nombre
            print(f"[ia] {nombre}: respuesta con formato inválido")
        except Exception as e:
            print(f"[ia] {nombre} falló: {type(e).__name__}: {str(e)[:200]}")
    return None, None
