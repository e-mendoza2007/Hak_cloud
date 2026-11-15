# Pasos en orden (desde cero) — Parte A + infraestructura base

Tiempo estimado la primera vez: 1.5 a 2 horas. Usa `python` en Windows y `python3` en Mac/Linux.
Cada paso termina con una **comprobación**: si no pasa, no sigas.

## 0. Instalar herramientas (una vez)
Instala: Node.js 20 LTS, Python 3.12, AWS CLI v2 y Git. Luego:

    npm install -g serverless@3
    python -m pip install boto3

Comprobación: `node -v`, `aws --version`, `serverless --version` muestran versión.

## 1. Credenciales de la cuenta estudiantil
En AWS Academy: *Start Lab* → *AWS Details* → *Show* (AWS CLI). Copia los tres valores:

    aws configure set aws_access_key_id TU_ACCESS_KEY
    aws configure set aws_secret_access_key TU_SECRET
    aws configure set aws_session_token TU_TOKEN
    aws configure set region us-east-1
    aws sts get-caller-identity

Comprobación: el último comando devuelve tu cuenta. **Estos valores cambian en cada sesión del lab**: repite este paso
cada vez que inicies el lab.

## 2. Probar el código en local
    cd arquifusion/datos-ia
    python tests/test_core.py
    python tests/test_handlers_smoke.py

Comprobación: ambos terminan en `OK`.

## 3. Desplegar la infraestructura base
    cd ../infra-base
    serverless deploy --stage dev

Crea 8 tablas `af_*`, índices, streams, 3 tópicos SNS, parámetros SSM y el Step Functions `arquifusion-flujo-incidente`.
Comprobación: termina con "Service deployed". Si falla por permisos del rol del Step Functions o por
`PointInTimeRecovery`, avísame con el mensaje exacto.

## 4. Configurar la IA
**4a. Bedrock** (busca solo el modelo que funcione en tu cuenta):

    cd ../datos-ia
    python scripts/probar_bedrock.py

Si dice "FUNCIONA", ya quedó configurado. Si ninguno sirve, queda configurado solo Gemini (sigue con 4b igual).

**4b. Gemini (respaldo, gratis):** entra a aistudio.google.com → *Get API key* → crea una clave. Luego:

    aws ssm put-parameter --name /arquifusion/gemini_api_key --type SecureString --value "TU_CLAVE" --overwrite
    aws ssm put-parameter --name /arquifusion/gemini_model --type String --value "gemini-flash-latest" --overwrite

(Si ese nombre de modelo no existe en AI Studio, usa el que muestre allí.)

## 5. Segunda nube: Google (Firebase)
1. console.firebase.google.com → *Add project* (sin Analytics).
2. *Build → Firestore Database → Create database* → modo de prueba, cualquier ubicación.
3. ⚙ *Project settings → Service accounts → Generate new private key*. Guarda el archivo como `clave.json`
   dentro de la carpeta `datos-ia` (**nunca lo subas a GitHub**; ya está en `.gitignore`).
4. Guárdalo en SSM y construye el layer:

       aws ssm put-parameter --name /arquifusion/gcp_service_account --type SecureString --value file://clave.json --overwrite
       python -m pip install --target layer/gcp/python --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all: -r layer/requirements.txt

Comprobación: existe la carpeta `layer/gcp/python/google`.

## 6. Desplegar tu parte
    serverless deploy --stage dev

Comprobación: lista 7 funciones. Luego:

    python scripts/seed.py

## 7. Primera prueba end to end
Abre **dos terminales** en `datos-ia`.

Terminal 1 (simulador en bucle, 15 min):

    python scripts/demo.py correr 900

Terminal 2:

    python scripts/demo.py suscribir tu_correo@gmail.com     # confirma los 3 correos que llegan
    python scripts/demo.py falla M-017 rodamiento 4
    python scripts/demo.py estado                            # repite cada minuto

En 3 a 4 minutos debe aparecer un incidente (severidad media → alta → crítica). Cuando aparezca:

    python scripts/demo.py ia INC-xxxxxxxx                   # explicación con IA (el ID sale en "estado")
    python scripts/demo.py preguntar "¿Qué máquinas atiendo primero y por qué?"

Comprobaciones: (1) hay una ejecución en la consola de Step Functions, (2) llegan correos por rol,
(3) aparece el incidente en Firestore (Firebase console → Firestore → colección `incidentes`).

Causa común: `python scripts/demo.py zona Z2 refrigeracion 4` → en pocos minutos 3+ incidentes de Z2 con el mismo `GRUPO`.
Batch de flota: `python scripts/demo.py batch`.
Limpiar: `python scripts/demo.py limpiar M-017` y `python scripts/demo.py limpiar zona Z2`.

## 8. Ensayo de la demo (haz esto antes de grabar)
1. Terminal 1: `python scripts/demo.py correr 900`. Espera 2 minutos para que haya datos.
2. Terminal 2: `python scripts/demo.py falla M-017 rodamiento 3`, después `python scripts/demo.py zona Z3 refrigeracion 3`.
3. Prepara estas pestañas: DynamoDB (`af_maquinas`, `af_incidentes`), Step Functions (ejecuciones), tu correo, Firestore.

## 9. Grabar el video (tu parte ≈ 1:45 dentro de los 5:00)
Graba la pantalla en tramos cortos (OBS o Win+G) y la voz aparte; une todo en CapCut o DaVinci. Máximo 5:00 en total.

| Tramo | Qué mostrar en pantalla | Qué decir (idea) |
|---|---|---|
| 0:00–0:20 | Terminal con `correr` y la tabla `af_maquinas` llenándose | «30 máquinas envían telemetría cada pocos segundos; todo serverless, sin servidores encendidos.» |
| 0:20–0:50 | `falla M-017 rodamiento 3`, luego `estado` mostrando subir el score | «No miramos una variable sola: combinamos temperatura, vibración y combustible, y su evolución en el tiempo.» |
| 0:50–1:15 | Ejecución en Step Functions y los 3 correos distintos | «Se dispara el flujo automático y cada rol recibe el mensaje que necesita.» |
| 1:15–1:35 | `ia INC-...` y `preguntar "¿Qué atiendo primero?"` | «La IA de Bedrock explica la causa y responde con datos reales; si falla, hay respaldo.» |
| 1:35–1:50 | `zona Z3 refrigeracion 3` y el `GRUPO` en `estado`; Firestore con el incidente | «Detectamos causa común por zona y replicamos en Google Cloud: dos nubes.» |

Después de grabar: apaga el simulador (Ctrl+C en la terminal 1).

## 10. Subir a GitHub y entregar
    cd ..
    git init
    git add .
    git commit -m "ArquiFusion: infra-base + parte A"
    git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
    git branch -M main
    git push -u origin main

Antes del `git add`, confirma que `clave.json` NO aparece en `git status`. Entrega por Canvas: video + link del repo + imagen de arquitectura.

## Si algo falla
| Síntoma | Qué hacer |
|---|---|
| `ExpiredToken` / `InvalidClientTokenId` | Reinicia el lab y repite el paso 1 |
| `serverless deploy` pide login | Usa `serverless@3` (paso 0) |
| `AccessDenied` al crear algo | Cópiame el mensaje completo |
| `estado` no muestra incidentes | Verifica que `correr` siga activo y espera 4 min; revisa logs: `serverless logs -f detectorAnomalias --stage dev` |
| IA siempre dice `plantilla` | Revisa 4a/4b; mira `serverless logs -f iaExplicar --stage dev` |
| No hay colección `incidentes` en Firestore | `serverless logs -f replicarGcp --stage dev` |
| Sale un gasto raro en el lab | Detén `correr` y no dejes simuladores activos |
