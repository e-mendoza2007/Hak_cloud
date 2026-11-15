# datos-ia (Persona A)

Simulador, ingesta, detector de anomalías, IA (Bedrock → Gemini → plantilla), asistente,
analítica de flota y réplica en Google (Firestore). Todo serverless.

## Estructura
- `core/`: lógica pura (sin AWS): simulador, detector, analítica, prompts. Se prueba en local.
- `common/`: acceso a DynamoDB, SSM, ingesta, causa común, clientes de IA.
- `handlers/`: una Lambda por archivo (ver `serverless.yml`).
- `scripts/`: `probar_bedrock.py`, `seed.py` y `demo.py` (herramienta de demo).
- `tests/`: `python3 tests/test_core.py` y `python3 tests/test_handlers_smoke.py`.

## Pruebas locales (sin credenciales)
    python3 tests/test_core.py            # simulador + detector + analítica + utilidades de IA
    python3 tests/test_handlers_smoke.py  # handlers con AWS simulado

## Infraestructura previa
Va en la carpeta hermana `infra-base/` (tablas `af_*` con sus índices, streams, SNS, parámetros SSM y un Step Functions mínimo).
Se despliega primero. Convenciones: almacenes `ALM-<zona>` y componentes `rodamientos`, `refrigeracion`,
`bomba_hidraulica`, `inyectores`, `motor_transmision`. El simulador crea las 30 máquinas; `scripts/seed.py` carga técnicos y repuestos.

## Parámetros SSM que pone A (`/arquifusion/...`)
| Parámetro | Tipo | Valor |
|---|---|---|
| `bedrock_model_id` | String (lo pone `probar_bedrock.py`) | ID del modelo barato que sí funcione en tu cuenta (ej. `amazon.nova-micro-v1:0` o `us.amazon.nova-micro-v1:0`) |
| `bedrock_region` | String | `us-east-1` |
| `gemini_api_key` | SecureString | clave de Google AI Studio |
| `gemini_model` | String | `gemini-flash-latest` (confirma el nombre vigente en AI Studio) |
| `ia_proveedores` | String | `bedrock,gemini` (usa `gemini` si Bedrock da AccessDenied) |
| `gcp_service_account` | SecureString | JSON completo de la cuenta de servicio de Firebase |
| `umbrales` | String | `{"media":0.4,"alta":0.6,"critica":0.8,"cooldown_min":30,"causa_comun_min_maquinas":3,"ventana_min":60}` |

`sfn_incidente_arn` lo crea B. Si aún no existe, el detector igual crea el incidente (solo no inicia el flujo).

## Despliegue
    npm i -g serverless@3
    ./build_layer.sh                      # una vez (necesita pip y red)
    serverless deploy --stage dev
    # encender el simulador: cambia custom.simuladorActivo a true y vuelve a desplegar,
    # o invócalo a mano:
    serverless invoke -f generarTelemetria --data '{"lecturas": 6}'

Si todavía no tienes streams/SSM de B, comenta los bloques `stream:` y el layer para probar la ingesta y el simulador.

## Demo (orden recomendado)
1. `serverless invoke -f generarTelemetria` una o dos veces: se crean las 30 máquinas y llegan lecturas.
2. `POST /demo/falla` con `{"maquina_id":"M-017","tipo":"rodamiento","rampa_min":5}`.
3. Deja corriendo el simulador (`LECTURAS_POR_EJECUCION=6` acelera). En ~3 min el score pasa por media → alta → crítica,
   se crea el incidente y se inicia Step Functions.
4. Falla de zona: `{"zona":"Z2","tipo":"refrigeracion","rampa_min":5}` → 3+ incidentes en la zona → `grupo_id` (causa común).
5. `POST /asistente` con `{"pregunta":"¿Qué máquinas atiendo primero y por qué?"}`.
6. Limpiar: `{"maquina_id":"M-017","limpiar":true}`.

## Notas de diseño
- El baseline de cada máquina (EWMA) no aprende de lecturas anómalas (|z| ≥ 2.5), así una falla lenta no se "normaliza".
- El combustible se normaliza por carga antes de compararlo (consumo alto con carga alta no es anomalía).
- El score combina variables con un multiplicador por co-ocurrencia y un bono por tendencia creciente.
- Umbrales calibrados con el simulador: 0 falsos positivos en 8 600 lecturas normales; las 4 fallas llegan a `media` en 7–11 min de una rampa de 15.
- BigQuery sandbox no admite inserciones en streaming ni DML: aquí no se usa. Firestore guarda la réplica; si queda tiempo,
  se puede cargar un CSV diario a BigQuery con un load job.
- Rekognition (`analizar-foto`) quedó fuera de esta entrega; es opcional.
