"""Pruebas de la lógica pura (sin AWS):  python tests/test_core.py"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.geo import haversine_km
from core.asignacion import puntaje, rankear, eta, almacenes_por_cercania
from core.mensajes import canal, asunto, mensaje, recurrencia, a_ascii
from core.preventivo import planificar, texto_plan

MAQ = {"maquina_id": "M-017", "lat": -12.060, "lon": -77.050}
CERCA = {"tecnico_id": "T-01", "lat": -12.061, "lon": -77.051, "especialidades": ["inyectores"], "estado": "disponible"}
ESPEC = {"tecnico_id": "T-02", "lat": -12.075, "lon": -77.030, "especialidades": ["rodamientos"], "estado": "disponible"}
OCUP = {"tecnico_id": "T-03", "lat": -12.060, "lon": -77.050, "especialidades": ["rodamientos"], "estado": "ocupado"}


def test_haversine():
    assert haversine_km(0, 0, 0, 0) == 0
    d = haversine_km(-12.04, -77.03, -12.08, -77.02)          # Z1 -> Z3: ~4.6 km
    assert 4.0 < d < 5.2, d


def test_rankeo_depende_de_la_severidad():
    # Crítica: gana el que está al lado aunque no sea especialista. Media: gana el especialista.
    assert rankear([CERCA, ESPEC, OCUP], MAQ, "rodamientos", "critica")[0]["tecnico"]["tecnico_id"] == "T-01"
    assert rankear([CERCA, ESPEC, OCUP], MAQ, "rodamientos", "media")[0]["tecnico"]["tecnico_id"] == "T-02"
    assert all(c["tecnico"]["estado"] == "disponible" for c in rankear([CERCA, ESPEC, OCUP], MAQ, "x", "alta"))


def test_carga_resta_puntaje():
    p0, _, _ = puntaje(ESPEC, MAQ, "rodamientos", "alta")
    p1, _, _ = puntaje({**ESPEC, "carga": 5}, MAQ, "rodamientos", "alta")
    assert p1 < p0


def test_eta():
    e = eta(3.0, "rodamientos", True)
    assert e["viaje_min"] == 6.0 and e["reparacion_min"] == 120 and e["total_min"] == 126
    assert eta(3.0, "rodamientos", False)["total_min"] == 171       # +45 min si no es especialista


def test_almacen_mas_cercano():
    assert almacenes_por_cercania(MAQ)[0] == "ALM-Z2"


def test_canales_por_rol():
    assert canal("operador", "critica") == "bandeja"
    assert canal("tecnico", "media") == "email" and canal("supervisor", "media") == "email"
    assert canal("gerente", "critica") == "email" and canal("gerente", "alta") == "bandeja"


def test_asunto_ascii_y_corto():
    s = asunto({"severidad": "crítica", "maquina_id": "M-017", "zona": "Z2"}, prefijo="Incidente " + "ñ" * 200)
    assert len(s) <= 100 and s == a_ascii(s)


def test_mensaje_por_rol():
    inc = {"incidente_id": "INC-1", "maquina_id": "M-017", "zona": "Z2", "severidad": "alta", "score": 0.7,
           "componente_probable": "rodamientos", "variables_anomalas": ["vibracion"], "tecnico_id": "T-02",
           "asignacion": {"distancia_km": 2.1, "eta": {"total_min": 124}},
           "repuesto": {"reservado": True, "componente": "rodamientos", "almacen": "ALM-Z2", "stock_restante": 0,
                        "bajo_minimo": True},
           "grupo_info": {"n_maquinas": 3, "zona": "Z2", "variable_comun": "temperatura"},
           "ia": {"resumen_por_rol": {"tecnico": "Revisar rodamiento delantero."}}}
    tec, sup, ger, ope = (mensaje(r, inc) for r in ("tecnico", "supervisor", "gerente", "operador"))
    assert "Revisar rodamiento delantero." in tec and "ETA 124" in tec
    assert "bajo el mínimo" in sup and "causa común" in sup
    assert "causa común" in ger and "ETA" not in ger
    assert "M-017" in ope and "ETA" not in ope                       # plantilla: el operador no ve logística


def test_recurrencia_14_dias():
    ahora = 1_800_000_000_000
    dia = 86_400_000
    hist = [{"maquina_id": "M-017", "ts": ahora - 3 * dia, "componentes": ["rodamientos"], "incidente_id": "INC-A"},
            {"maquina_id": "M-017", "ts": ahora - 20 * dia, "componentes": ["inyectores"], "incidente_id": "INC-B"}]
    assert recurrencia(hist, "M-017", ["rodamientos"], ahora)["incidente_id"] == "INC-A"
    assert recurrencia(hist, "M-017", ["inyectores"], ahora) is None   # fue hace 20 días
    assert recurrencia(hist, "M-001", ["rodamientos"], ahora) is None


def test_plan_preventivo():
    maqs = [{"maquina_id": "M-1", "zona": "Z1", "score_actual": 0.1,
             "preventivo": {"estado": "proximo", "dias_restantes": 3, "fecha_sugerida": "2026-11-18"}},
            {"maquina_id": "M-2", "zona": "Z2", "score_actual": 0.5,
             "preventivo": {"estado": "vencido", "dias_restantes": 0, "fecha_sugerida": "2026-11-15"}},
            {"maquina_id": "M-3", "zona": "Z3", "preventivo": {"estado": "ok", "dias_restantes": 40}}]
    plan = planificar(maqs, {"alertas_repuestos": [{"zona": "Z2", "componente": "rodamientos", "faltan": 1}]})
    assert [m["maquina_id"] for m in plan["mantener"]] == ["M-2", "M-1"]
    assert plan["posponer"] == 1 and plan["novedades"] == 3
    assert "Se posponen 1" in texto_plan(plan, "2026-11-15")


if __name__ == "__main__":
    pruebas = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in pruebas:
        t()
        print("  ok ", t.__name__)
    print(f"OK ({len(pruebas)} pruebas)")
