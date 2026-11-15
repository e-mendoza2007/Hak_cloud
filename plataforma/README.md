# plataforma (Persona B)

Orquestación, API y acciones automáticas. Todo con el rol `LabRole` y Serverless Framework v3 (fijado en `package.json`).

## Estructura
- `statemachines/`: definiciones ASL en YAML de `FlujoIncidente` y `PreventivoDiario` (se incluyen en `serverless.yml` con `${file()}`).
- `core/`: lógica pura y testeable (asignación por puntaje y ETA, mensajes por rol, recurrencia y plan preventivo).
- `common/`: acceso a DynamoDB, SSM con caché, respuestas HTTP con CORS y entrega de notificaciones (bandeja + SNS).
- `handlers/`: una Lambda por archivo (`lambda_handler`).
- `tests/`: `python tests/test_core.py` (sin dependencias) y `python tests/test_handlers.py` (AWS simulado con `moto`).

## Contrato con datos-ia
- El detector de A inicia `FlujoIncidente` con el ARN de `/arquifusion/sfn_incidente_arn`, que crea este stack.
- El flujo invoca `arquifusion-datos-ia-<stage>-iaExplicar` y el preventivo `...-batchFlota` (nombres fijos, sin exports).
- Al cerrar se escribe `estado = "resuelto"` y `cerrado_ts`, que es lo que usa el cooldown del detector.
- Estados del incidente: `abierto` → `asignado` → `en_atencion` → `resuelto`, con `escalado` si vence el SLA.

## Endpoints (API REST)
`GET /maquinas`, `/maquinas/{id}`, `/maquinas/{id}/telemetria?desde=` · `GET /incidentes?estado=abiertos|todos`, `/incidentes/{id}` ·
`POST /incidentes/{id}/atender`, `/incidentes/{id}/cerrar` · `GET /tecnicos`, `/repuestos/estado`, `/flota/productividad`, `/flota/combustible`, `/notificaciones?rol=` ·
`POST /asistente`, `/demo/falla` (fachadas hacia las Lambdas de A)

## Ajustes
En `serverless.yml`, `custom.slaSeg` define el SLA por severidad (60/120/180 s para la demo), `custom.preventivoEstado` enciende la regla diaria y `custom.corsOrigin` restringe CORS al dominio de Firebase.
