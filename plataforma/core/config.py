"""Constantes de la plataforma (Persona B). Puro Python: sin AWS, se prueba en local."""

# Mismos componentes que usa A (core/config.py -> COMPONENTE) y el seed (af_repuestos)
COMPONENTES = ["rodamientos", "refrigeracion", "bomba_hidraulica", "inyectores", "motor_transmision"]

# Un almacén por zona (ALM-<zona>), ubicado en el centro de la zona (mismas coordenadas que el simulador de A)
ALMACENES = {
    "ALM-Z1": (-12.040, -77.030),
    "ALM-Z2": (-12.060, -77.050),
    "ALM-Z3": (-12.080, -77.020),
    "ALM-Z4": (-12.050, -77.000),
}

ROLES = ["operador", "tecnico", "supervisor", "gerente"]
ORDEN_SEVERIDAD = {"critica": 4, "alta": 3, "media": 2, "baja": 1, "normal": 0}

# Asignación de técnicos: el peso de cada criterio depende de la severidad.
# Crítica: manda la cercanía (llegar rápido). Media: manda la especialidad (resolver bien a la primera).
PESOS_ASIGNACION = {
    "critica": {"cercania": 0.70, "especialidad": 0.20, "carga": 0.10},
    "alta":    {"cercania": 0.45, "especialidad": 0.45, "carga": 0.10},
    "media":   {"cercania": 0.30, "especialidad": 0.55, "carga": 0.15},
}
CARGA_MAX = 5                 # incidentes atendidos que ya cuentan como "carga completa"

# ETA = viaje + reparación
VEL_KMH = 30                  # velocidad media de una camioneta dentro de la operación
TIEMPO_REPARACION_MIN = {"rodamientos": 120, "refrigeracion": 90, "bomba_hidraulica": 150,
                         "inyectores": 60, "motor_transmision": 180}
REPARACION_DEFAULT_MIN = 120
EXTRA_SIN_ESPECIALIDAD_MIN = 45

# Historial: una falla del mismo componente en la misma máquina dentro de esta ventana es "recurrente"
DIAS_RECURRENCIA = 14
