"""Lo invoca Step Functions: { incidente_id, ... } -> guarda y devuelve la explicación por rol."""
import time
from common.dynamo import tabla, from_dynamo, set_attrs, Key
from common.ia_clients import generar
from core.ia_prompts import prompt_incidente, plantilla_incidente, parse_json_flexible, validar_ia


def handler(event, context):
    iid = event["incidente_id"]
    ti = tabla("incidentes")
    inc = from_dynamo(ti.get_item(Key={"incidente_id": iid}).get("Item") or {})
    if not inc:
        raise ValueError(f"incidente {iid} no existe")
    if (inc.get("ia") or {}).get("fuente") in ("bedrock", "gemini"):       # caché
        return {"incidente_id": iid, "ia": inc["ia"]}
    maq = from_dynamo(tabla("maquinas").get_item(Key={"maquina_id": inc["maquina_id"]}).get("Item") or {})
    hist = from_dynamo(tabla("historial").query(KeyConditionExpression=Key("maquina_id").eq(inc["maquina_id"]),
                                                ScanIndexForward=False, Limit=3).get("Items", []))
    texto, fuente = generar(prompt_incidente(inc, maq, hist), max_tokens=400,
                            validar=lambda t: validar_ia(parse_json_flexible(t)))
    ia = parse_json_flexible(texto) if texto else None
    if not ia:
        ia, fuente = plantilla_incidente(inc, maq), "plantilla"
    ia = {**ia, "fuente": fuente, "ts": int(time.time() * 1000)}
    set_attrs(ti, {"incidente_id": iid}, {"ia": ia})
    return {"incidente_id": iid, "ia": ia}
