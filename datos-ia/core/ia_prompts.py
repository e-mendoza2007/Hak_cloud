"""Prompts y utilidades de IA. Puro Python."""
import json
import re

ROLES = ["operador", "tecnico", "supervisor", "gerente"]


def prompt_incidente(inc, maq, historial):
    hist = "; ".join(f"{h.get('tipo', 'intervención')} ({', '.join(h.get('componentes', []) or [])})"
                     for h in (historial or [])[:3]) or "sin intervenciones previas"
    grupo = inc.get("grupo_info")
    extra = (f"\nOjo: {grupo['n_maquinas']} máquinas de la zona {inc['zona']} fallan a la vez; "
             f"variable común: {grupo.get('variable_comun')}.") if grupo else ""
    return f"""Eres el asistente de mantenimiento de ArquiFusion Corp (maquinaria pesada).
Incidente: máquina {inc['maquina_id']} (modelo {maq.get('modelo')}, zona {inc['zona']}).
Severidad {inc['severidad']} (score {inc['score']}). Variables anómalas: {', '.join(inc.get('variables_anomalas', []))}.
Componente probable: {inc.get('componente_probable')}. Horas desde último mantenimiento: {maq.get('horas_desde_mant')}.
Historial reciente: {hist}.{extra}
Responde SOLO con un JSON válido, sin texto adicional ni markdown, con esta forma:
{{"causa_probable": "...", "acciones": ["...", "..."], "resumen_por_rol": {{"operador": "...", "tecnico": "...", "supervisor": "...", "gerente": "..."}}}}
Reglas: español, frases cortas. operador: qué hacer ahora con la máquina. tecnico: diagnóstico y repuestos a llevar.
supervisor: prioridad, impacto y asignación. gerente: una frase de impacto en la operación. No inventes datos que no estén arriba."""


def plantilla_incidente(inc, maq):
    comp = inc.get("componente_probable") or "componente no identificado"
    vars_ = ", ".join(inc.get("variables_anomalas", [])) or "varias variables"
    mid, sev = inc["maquina_id"], inc["severidad"]
    return {
        "causa_probable": f"Posible falla en {comp} (variables fuera de lo normal: {vars_}).",
        "acciones": [f"Inspeccionar {comp}", "Reducir la carga hasta revisar", "Confirmar con una segunda lectura"],
        "resumen_por_rol": {
            "operador": f"La máquina {mid} tiene una alerta {sev}. Reduzca la carga y espere al técnico.",
            "tecnico": f"{mid} ({maq.get('modelo')}): revisar {comp}. Variables: {vars_}. Lleve el repuesto correspondiente.",
            "supervisor": f"Incidente {sev} en {mid}, zona {inc['zona']}. Asignar técnico con especialidad en {comp}.",
            "gerente": f"Alerta {sev} en la zona {inc['zona']}; riesgo de detención de {mid}.",
        },
    }


def parse_json_flexible(texto):
    """Extrae el primer objeto JSON de la respuesta de un modelo (tolera ``` y texto extra)."""
    if not texto:
        return None
    t = re.sub(r"```(?:json)?", "", texto).strip()
    ini, fin = t.find("{"), t.rfind("}")
    if ini < 0 or fin <= ini:
        return None
    try:
        return json.loads(t[ini:fin + 1])
    except ValueError:
        return None


def validar_ia(d):
    """True si el JSON tiene la forma esperada."""
    if not isinstance(d, dict) or not d.get("causa_probable"):
        return False
    r = d.get("resumen_por_rol")
    return isinstance(r, dict) and all(isinstance(r.get(k), str) and r.get(k) for k in ROLES)


def prompt_asistente(pregunta, contexto):
    return f"""Eres el asistente de mantenimiento de ArquiFusion Corp. Responde en español, en máximo 6 líneas,
usando SOLO los datos de abajo. Si el dato no está, dilo. Prioriza por severidad y cercanía al técnico.

DATOS ACTUALES:
{contexto}

PREGUNTA: {pregunta}"""
