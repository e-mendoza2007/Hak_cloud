"""POST /incidentes/{id}/foto  body: {"imagen_base64": "...", "tipo": "image/jpeg"}
El técnico u operador sube una foto del componente: se guarda en S3 (bucket con versionado) y Amazon
Rekognition (detect-labels) devuelve qué ve en la imagen. Las etiquetas quedan en el incidente."""
import base64
import binascii
import json
import os
import boto3
from common.dynamo import obtener, actualizar, ahora_ms
from common.http import respuesta, path_param, leer_body

BUCKET = os.environ.get("BUCKET_ARCHIVO", "")
MAX_BYTES = 4 * 1024 * 1024                 # el frontend reduce la foto antes de enviarla
TIPOS = {"image/jpeg": "jpg", "image/png": "png"}
# Etiquetas de Rekognition que sugieren daño visible en una pieza
SENALES_DANO = {"Rust", "Corrosion", "Crack", "Leak", "Oil", "Smoke", "Fire", "Damage", "Broken", "Burn", "Stain"}
_s3 = _rek = None


def lambda_handler(event, context):
    global _s3, _rek
    # Entrada (json)
    iid = path_param(event, "id")
    try:
        body = leer_body(event)
        imagen = base64.b64decode(body.get("imagen_base64") or "", validate=True)
    except (ValueError, binascii.Error):
        return respuesta(400, {"error": "envía la foto como imagen_base64 (JPEG o PNG)"})
    tipo = body.get("tipo", "image/jpeg")
    if tipo not in TIPOS or not imagen or len(imagen) > MAX_BYTES:
        return respuesta(400, {"error": "la foto debe ser JPEG o PNG de hasta 4 MB"})
    inc = obtener("incidentes", {"incidente_id": iid})
    if not inc:
        return respuesta(404, {"error": f"incidente {iid} no existe"})

    # Proceso
    _s3 = _s3 or boto3.client("s3")
    _rek = _rek or boto3.client("rekognition")
    clave = f"fotos/{iid}/{ahora_ms()}.{TIPOS[tipo]}"
    put = _s3.put_object(Bucket=BUCKET, Key=clave, Body=imagen, ContentType=tipo)
    r = _rek.detect_labels(Image={"Bytes": imagen}, MaxLabels=8, MinConfidence=70)
    etiquetas = [{"nombre": l["Name"], "confianza": round(l["Confidence"], 1)} for l in r.get("Labels", [])]
    dano = sorted({e["nombre"] for e in etiquetas} & SENALES_DANO)
    foto = {"s3": f"s3://{BUCKET}/{clave}", "version": put.get("VersionId"), "etiquetas": etiquetas,
            "posible_dano": dano, "ts": ahora_ms()}
    actualizar("incidentes", {"incidente_id": iid}, sets={"foto": foto},
               evento={"evento": "foto_analizada", "etiquetas": [e["nombre"] for e in etiquetas[:4]]})
    print(json.dumps({"foto": iid, "etiquetas": [e["nombre"] for e in etiquetas], "posible_dano": dano}))
    # Salida (json)
    return respuesta(200, foto)
