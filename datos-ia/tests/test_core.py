"""Pruebas locales (sin AWS):  python3 tests/test_core.py"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.config import MODELOS, UMBRALES_DEF
from core.simulador import crear_flota, generar_lectura, EFECTOS
from core.detector import evaluar

T0 = 1_763_100_000_000
ORDEN = ["normal", "baja", "media", "alta", "critica"]


def correr(maq, minutos, dt_ms=60000, inicio=T0, rng=None):
    rng = rng or random.Random(1)
    est, out = None, []
    for i in range(minutos):
        ts = inicio + i * dt_ms
        l = generar_lectura(maq, ts, rng)
        est, res = evaluar(l, est, maq["modelo"])
        if res:
            out.append((i, res))
    return out


def test_sin_falsos_positivos():
    for modelo in MODELOS:
        maq = next(m for m in crear_flota() if m["modelo"] == modelo)
        maq = {**maq, "perfil": "sobrecargado"}
        res = correr(maq, 3000)
        mx = max(r["score"] for _, r in res)
        n_media = sum(1 for _, r in res if r["score"] >= UMBRALES_DEF["media"])
        print(f"  {modelo}: lecturas operativas={len(res)} score máx={mx} lecturas>=media={n_media}")
        assert n_media == 0, "falso positivo"


def test_deteccion_por_tipo():
    maq0 = {**crear_flota()[0], "perfil": "sobrecargado"}
    for tipo in EFECTOS:
        maq = {**maq0, "degradacion": {"tipo": tipo, "inicio_ts": T0 + 200 * 60000, "rampa_min": 15}}
        res = correr(maq, 260)
        hitos = {}
        for i, r in res:
            if i < 200:
                assert r["severidad"] in ("normal", "baja"), (tipo, i, r)
                continue
            for sev in ("media", "alta", "critica"):
                if ORDEN.index(r["severidad"]) >= ORDEN.index(sev) and sev not in hitos:
                    hitos[sev] = (i - 200, r["componente_probable"])
        print(f"  {tipo}: {hitos}")
        assert "media" in hitos and hitos["media"][0] <= 13, tipo
        assert "critica" in hitos or "alta" in hitos, tipo
        esperado = {"rodamiento": "rodamientos", "refrigeracion": "refrigeracion",
                    "inyectores": "inyectores", "hidraulica": "bomba_hidraulica"}[tipo]
        assert res[-1][1]["componente_probable"] == esperado, (tipo, res[-1][1])


def test_analitica():
    from core.analitica import (metricas_dia, clasificar_flota, preventivo, demanda_repuestos,
                                tendencia_pct_dia, consumo_irregular)
    filas = []
    casos = {"M-1": (0.20, 40), "M-2": (0.65, 40), "M-3": (0.95, 40), "M-4": (0.30, 80), "M-5": (0.6, 41)}
    for mid, (util, prod_h) in casos.items():
        seg_tot = 86400
        c = {"seg_op": util * seg_tot, "seg_tot": seg_tot, "litros": 30 * util * 24, "prod": prod_h * util * 24 / 4,
             "temp_s": 86 * util * seg_tot}
        f = metricas_dia(c, "EXC-320"); f.update({"maquina_id": mid, "modelo": "EXC-320"})
        filas.append(f)
    clasificar_flota(filas)
    cl = {f["maquina_id"]: f["clasificacion"] for f in filas}
    print("  clasificación:", cl)
    assert "baja_utilizacion" in cl["M-1"] and "uso_excesivo" in cl["M-3"] and cl["M-2"] == []
    assert tendencia_pct_dia([10, 10.5, 11, 11.6, 12.1]) > 3
    assert tendencia_pct_dia([10, 10, 10, 10]) == 0
    p = preventivo({"horas_desde_mant": 480}, "EXC-320", 12, temp_prom=95)
    print("  preventivo:", p)
    assert p["estado"] in ("proximo", "vencido")
    maqs = [{"maquina_id": f"M-{i}", "zona": "Z2", "score_actual": 0.7, "componente_probable": "rodamientos"} for i in range(3)]
    al = demanda_repuestos(maqs, {("ALM-Z2", "rodamientos"): {"stock": 1, "minimo": 1}})
    print("  alertas repuestos:", al)
    assert al and al[0]["faltan"] == 2
    assert consumo_irregular([2, 3, 2, 3, 2, 9])["irregular"]


def test_ia_utils():
    from core.ia_prompts import parse_json_flexible, validar_ia, plantilla_incidente, prompt_incidente
    inc = {"maquina_id": "M-017", "zona": "Z2", "severidad": "alta", "score": 0.7,
           "variables_anomalas": ["vibracion", "temperatura"], "componente_probable": "rodamientos"}
    maq = {"modelo": "EXC-320", "horas_desde_mant": 410}
    pl = plantilla_incidente(inc, maq)
    assert validar_ia(pl)
    import json
    ruido = "Claro, aquí va:\n```json\n" + json.dumps(pl) + "\n```\nSaludos"
    assert validar_ia(parse_json_flexible(ruido))
    assert parse_json_flexible("sin json") is None
    assert "M-017" in prompt_incidente(inc, maq, [])


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            print(nombre)
            fn()
    print("OK")
