"""POST /asistente { "pregunta": "...", "rol": "supervisor" } -> respuesta con datos reales."""
import json
from common.dynamo import tabla, scan_all, from_dynamo
from common.ia_clients import generar
from core.ia_prompts import prompt_asistente

ORDEN = {"critica": 4, "alta": 3, "media": 2, "baja": 1, "normal": 0}


def _resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def _contexto():
    incs = [i for i in scan_all(tabla("incidentes")) if i.get("estado") != "resuelto"]
    incs.sort(key=lambda i: (ORDEN.get(i["severidad"], 0), i.get("score", 0)), reverse=True)
    lineas = ["INCIDENTES ABIERTOS:"]
    lineas += [f"- {i['maquina_id']} | zona {i['zona']} | {i['severidad']} (score {i['score']}) | "
               f"{i.get('componente_probable')} | estado {i['estado']} | técnico {i.get('tecnico_id', 'sin asignar')}"
               + (f" | grupo {i['grupo_id']}" if i.get("grupo_id") else "") for i in incs[:8]] or ["(ninguno)"]
    maqs = scan_all(tabla("maquinas"), ProjectionExpression="maquina_id, zona, estado, score_actual, preventivo")
    riesgo = sorted(maqs, key=lambda m: m.get("score_actual", 0), reverse=True)[:5]
    lineas += ["MAQUINAS CON MAYOR RIESGO:"] + [
        f"- {m['maquina_id']} | {m.get('zona')} | {m.get('estado')} | score {m.get('score_actual', 0)} | "
        f"mantenimiento {(m.get('preventivo') or {}).get('estado', 'n/d')}" for m in riesgo]
    disp = [t for t in scan_all(tabla("tecnicos")) if t.get("estado") == "disponible"]
    lineas.append(f"TECNICOS DISPONIBLES: {len(disp)}")
    return "\n".join(lineas), incs


def handler(event, context):
    d = json.loads(event.get("body") or "{}")
    pregunta = (d.get("pregunta") or "").strip()[:500]
    if not pregunta:
        return _resp(400, {"error": "falta la pregunta"})
    contexto, incs = _contexto()
    texto, fuente = generar(prompt_asistente(pregunta, contexto), max_tokens=300)
    if not texto:
        top = incs[0] if incs else None
        texto = (f"Atiende primero {top['maquina_id']} (zona {top['zona']}, severidad {top['severidad']}, "
                 f"componente {top.get('componente_probable')})." if top else "No hay incidentes abiertos ahora.")
        fuente = "plantilla"
    return _resp(200, {"respuesta": texto.strip(), "fuente": fuente})
