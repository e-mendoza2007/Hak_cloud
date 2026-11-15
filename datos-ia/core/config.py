"""Constantes del dominio. Sin dependencias de AWS (se puede probar en local)."""

VARS = ["temperatura", "vibracion", "presion", "combustible_lh", "rpm"]

# Peso de cada variable en el score de riesgo (suman 1.0)
PESOS = {"temperatura": 0.25, "vibracion": 0.30, "presion": 0.20,
         "combustible_lh": 0.15, "rpm": 0.10}

# Variable que más aporta -> componente probable (ids que B debe usar en af_repuestos)
COMPONENTE = {"vibracion": "rodamientos", "temperatura": "refrigeracion",
              "presion": "bomba_hidraulica", "combustible_lh": "inyectores",
              "rpm": "motor_transmision"}

# Comportamiento normal por modelo: (media, desviación). carga_nom en toneladas.
MODELOS = {
    "EXC-320": {"tipo": "excavadora", "temperatura": (86, 3.0), "vibracion": (3.0, 0.45),
                "presion": (300, 10), "combustible_lh": (32, 2.5), "rpm": (1800, 60),
                "carga_nom": 18, "vel": 6, "intervalo_mant_h": 500, "costo_hora_mant": 14},
    "CAM-770": {"tipo": "camion", "temperatura": (90, 3.0), "vibracion": (2.5, 0.4),
                "presion": (280, 9), "combustible_lh": (55, 4.0), "rpm": (1900, 70),
                "carga_nom": 90, "vel": 28, "intervalo_mant_h": 600, "costo_hora_mant": 22},
    "CAR-950": {"tipo": "cargador", "temperatura": (84, 3.0), "vibracion": (3.5, 0.5),
                "presion": (320, 10), "combustible_lh": (28, 2.2), "rpm": (1750, 60),
                "carga_nom": 12, "vel": 10, "intervalo_mant_h": 450, "costo_hora_mant": 12},
}

UMBRALES_DEF = {"media": 0.4, "alta": 0.6, "critica": 0.8, "cooldown_min": 30,
                "causa_comun_min_maquinas": 3, "ventana_min": 60}

PRECIO_LITRO = 1.1          # USD ficticio por litro
UMBRAL_UTIL_BAJA = 0.35
UMBRAL_UTIL_ALTA = 0.90
