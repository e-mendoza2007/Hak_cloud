"""GET /maquinas | GET /maquinas/{id} | GET /maquinas/{id}/telemetria?desde=<ms>  (dolores 4 y 8)."""
from common.dynamo import scan_all, obtener, query, Key, ahora_ms, IDX_INC_MAQUINA
from common.http import respuesta, path_param, query_param

CAMPOS_LISTA = ["maquina_id", "modelo", "zona", "lat", "lon", "estado", "score_actual", "severidad_actual",
                "componente_probable", "horas_totales", "horas_desde_mant", "preventivo", "ultima",
                "ultima_lectura_ts", "degradacion"]
CAMPOS_TELEMETRIA = ["ts", "temperatura", "vibracion", "presion", "combustible_lh", "carga_t", "rpm", "estado"]
OCULTOS = {"stats", "hist_score"}                    # estado interno del detector de A


def lambda_handler(event, context):
    # Entrada (json)
    recurso = event.get("resource")
    try:
        # Proceso
        if recurso == "/maquinas":
            maquinas = sorted(scan_all("maquinas", CAMPOS_LISTA), key=lambda m: m["maquina_id"])
            resumen = {}
            for m in maquinas:
                resumen[m.get("estado", "sin_datos")] = resumen.get(m.get("estado", "sin_datos"), 0) + 1
            return respuesta(200, {"maquinas": maquinas, "resumen": resumen})

        mid = path_param(event, "id")
        if recurso == "/maquinas/{id}":
            maq = obtener("maquinas", {"maquina_id": mid})
            if not maq:
                return respuesta(404, {"error": f"máquina {mid} no existe"})
            incidentes = query("incidentes", Key("maquina_id").eq(mid), limite=10, desc=True, indice=IDX_INC_MAQUINA)
            historial = query("historial", Key("maquina_id").eq(mid), limite=10, desc=True)
            return respuesta(200, {"maquina": {k: v for k, v in maq.items() if k not in OCULTOS},
                                   "incidentes": incidentes, "historial": historial})

        if recurso == "/maquinas/{id}/telemetria":
            desde = int(query_param(event, "desde", ahora_ms() - 30 * 60 * 1000))
            lecturas = query("telemetria", Key("maquina_id").eq(mid) & Key("ts").gte(desde),
                             limite=500, campos=CAMPOS_TELEMETRIA)
            return respuesta(200, {"maquina_id": mid, "desde": desde, "lecturas": lecturas})
    except ValueError as e:
        return respuesta(400, {"error": str(e)})
    # Salida (json)
    return respuesta(404, {"error": f"ruta no soportada: {recurso}"})
