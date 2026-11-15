"""Comunicación por rol (dolor 9) e historial con recurrencia (dolor 10). Puro Python."""
import unicodedata
from .config import DIAS_RECURRENCIA


def canal(rol, severidad):
    """Mismo incidente, distinta urgencia: quién recibe email (push) y quién solo bandeja (pull)."""
    if rol == "operador":
        return "bandeja"
    if rol == "gerente":
        return "email" if severidad == "critica" else "bandeja"
    return "email"                                   # técnico y supervisor


def a_ascii(texto):
    """SNS solo acepta ASCII en el Subject."""
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()


def asunto(inc, prefijo="Incidente"):
    s = f"[ArquiFusion] {prefijo} {inc.get('severidad', '')} - {inc.get('maquina_id', '')} zona {inc.get('zona', '')}"
    return a_ascii(s)[:100]


def _plantilla(rol, inc):
    comp = inc.get("componente_probable") or "componente no identificado"
    mid, sev, zona = inc.get("maquina_id"), inc.get("severidad"), inc.get("zona")
    return {
        "operador": f"La máquina {mid} tiene una alerta {sev}. Reduzca la carga y espere al técnico.",
        "tecnico": f"{mid}: revisar {comp}. Variables anómalas: {', '.join(inc.get('variables_anomalas', []))}.",
        "supervisor": f"Incidente {sev} en {mid}, zona {zona}. Componente probable: {comp}.",
        "gerente": f"Alerta {sev} en la zona {zona}: riesgo de detención de {mid}.",
    }[rol]


def mensaje(rol, inc):
    """Texto para cada rol: resumen de la IA (si existe) + datos operativos que ese rol necesita."""
    resumen = ((inc.get("ia") or {}).get("resumen_por_rol") or {}).get(rol) or _plantilla(rol, inc)
    lineas = [resumen]
    asig, rep, grupo = inc.get("asignacion") or {}, inc.get("repuesto") or {}, inc.get("grupo_info")
    if rol in ("tecnico", "supervisor"):
        if inc.get("tecnico_id"):
            lineas.append(f"Técnico asignado: {inc['tecnico_id']} a {asig.get('distancia_km', '?')} km, "
                          f"ETA {(asig.get('eta') or {}).get('total_min', '?')} min.")
        else:
            lineas.append("Sin técnico disponible: requiere decisión del supervisor.")
        if rep.get("reservado"):
            lineas.append(f"Repuesto reservado: {rep['componente']} en {rep['almacen']} (quedan {rep['stock_restante']}).")
        elif rep:
            lineas.append(f"Repuesto NO reservado: {rep.get('motivo', 'sin stock')}.")
    if rol == "supervisor" and rep.get("bajo_minimo"):
        lineas.append(f"ALERTA: el stock de {rep['componente']} en {rep['almacen']} quedó bajo el mínimo.")
    if rol in ("supervisor", "gerente") and grupo:
        lineas.append(f"Posible causa común: {grupo.get('n_maquinas')} máquinas de la zona {grupo.get('zona')} "
                      f"con incidentes a la vez (variable común: {grupo.get('variable_comun')}).")
    lineas.append(f"Incidente {inc.get('incidente_id')} | score {inc.get('score')}")
    return "\n".join(lineas)


def mensaje_escalamiento(destino, inc, nivel, sla_seg):
    base = (f"SLA vencido (nivel {nivel}): el incidente {inc.get('incidente_id')} de {inc.get('maquina_id')} "
            f"(zona {inc.get('zona')}, severidad {inc.get('severidad')}) sigue sin atención tras {sla_seg} s.")
    if destino == "supervisor":
        accion = (f"Técnico asignado: {inc['tecnico_id']}. Confírmelo o reasigne." if inc.get("tecnico_id")
                  else "No hay técnico asignado: asigne uno manualmente.")
    else:
        accion = "El supervisor no logró resolverlo a tiempo: evalúe detener la máquina o traer apoyo externo."
    return f"{base}\n{accion}"


def recurrencia(historial, maquina_id, componentes, ahora_ms, dias=DIAS_RECURRENCIA):
    """Devuelve la intervención previa (misma máquina, mismo componente, dentro de la ventana) o None."""
    limite = ahora_ms - dias * 86400000
    comps = set(componentes or [])
    previas = sorted((h for h in historial if h.get("maquina_id") == maquina_id and int(h.get("ts", 0)) >= limite),
                     key=lambda h: -int(h["ts"]))
    for h in previas:
        if comps & set(h.get("componentes") or []):
            return h
    return None
