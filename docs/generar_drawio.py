"""Genera docs/arquitectura.drawio (íconos oficiales AWS mxgraph.aws4 y GCP mxgraph.gcp2).
Uso:  python docs/generar_drawio.py
Exportar a PNG con draw.io de escritorio:  draw.io -x -f png -s 2 -o docs/arquitectura.png docs/arquitectura.drawio"""
import os
from xml.sax.saxutils import escape

celdas, n = [], [0]
COL = {"computo": "#ED7100", "datos": "#C925D1", "integracion": "#E7157B", "almacen": "#7AA116", "ia": "#01A88D",
       "seguridad": "#DD344C", "gestion": "#E7157B", "analitica": "#8C4FFF", "dev": "#4D72F3"}
C = [100, 320, 540, 760, 980, 1200, 1420]        # x del ícono por columna
R = [190, 420, 640, 860]                         # y del ícono por fila
T = 72                                           # tamaño del ícono


def nid():
    n[0] += 1
    return f"c{n[0]}"


def celda(valor, estilo, x, y, w, h, vertex=True, extra=""):
    i = nid()
    tipo = 'vertex="1"' if vertex else 'edge="1"'
    celdas.append(f'<mxCell id="{i}" value="{escape(valor)}" style="{estilo}" {tipo} parent="1"{extra}>'
                  f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    return i


def icono(col, fila, res, cat, texto, dx=0, dy=0):
    x, y = C[col] + dx, R[fila] + dy
    estilo = (f"sketch=0;outlineConnect=0;fontColor=#232F3E;fillColor={COL[cat]};strokeColor=#ffffff;dashed=0;"
              f"verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=13;"
              f"aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};")
    return celda(texto.replace("\n", "<br>"), estilo, x, y, T, T)


def icono_gcp(x, y, pr, texto):
    estilo = ("sketch=0;html=1;fillColor=#5184F3;strokeColor=none;verticalAlign=top;labelPosition=center;"
              f"verticalLabelPosition=bottom;align=center;fontSize=13;shape=mxgraph.gcp2.hexIcon;prIcon={pr};")
    return celda(texto.replace("\n", "<br>"), estilo, x, y, 76, 68)


def texto(t, x, y, w, h, tam=13, negrita=False, color="#232F3E", alin="center", borde=None, relleno="none"):
    estilo = (f"text;html=1;whiteSpace=wrap;align={alin};verticalAlign=middle;fontSize={tam};fontColor={color};"
              f"fontStyle={1 if negrita else 0};fillColor={relleno};" + (f"strokeColor={borde};rounded=1;" if borde else "strokeColor=none;"))
    return celda(t.replace("\n", "<br>"), estilo, x, y, w, h)


def numero(k, x, y):
    return celda(str(k), "ellipse;whiteSpace=wrap;html=1;fontSize=14;fontStyle=1;fillColor=#ffffff;strokeColor=#232F3E;", x, y, 28, 28)


def flecha(a, b, etiqueta="", puntos=(), salida=None, entrada=None, color="#232F3E", punteada=False):
    estilo = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;strokeWidth=2;strokeColor={color};"
              f"fontSize=13;fontColor=#232F3E;labelBackgroundColor=#ffffff;" + ("dashed=1;" if punteada else ""))
    if salida:
        estilo += f"exitX={salida[0]};exitY={salida[1]};exitDx=0;exitDy=0;"
    if entrada:
        estilo += f"entryX={entrada[0]};entryY={entrada[1]};entryDx=0;entryDy=0;"
    i = nid()
    pts = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in puntos)
    arr = f'<Array as="points">{pts}</Array>' if puntos else ""
    celdas.append(f'<mxCell id="{i}" value="{escape(etiqueta)}" style="{estilo}" edge="1" parent="1" source="{a}" target="{b}">'
                  f'<mxGeometry relative="1" as="geometry">{arr}</mxGeometry></mxCell>')
    return i


# ---------------- Título ----------------
texto("Diagrama de Arquitectura de Solución: ArquiFusion, mantenimiento inteligente de flota", 0, 8, 2000, 36, 26, True)
texto("100 % serverless en AWS + Google Cloud. Regla del lab: menos de 10 Lambdas a la vez (pico medido: 3 con 4 incidentes, 4 con 8).",
      0, 46, 2000, 26, 15, False, "#4A5960")

# ---------------- Grupos ----------------
celda("AWS Cloud", "points=[];outlineConnect=0;html=1;whiteSpace=wrap;fontSize=15;fontStyle=1;container=0;pointerEvents=0;"
      "collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;"
      "fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#232F3E;dashed=0;", 20, 90, 1570, 1090)
celda("Región us-east-1 (todas las Lambdas y Step Functions usan el rol LabRole)",
      "points=[];outlineConnect=0;html=1;whiteSpace=wrap;fontSize=14;fontStyle=0;container=0;pointerEvents=0;collapsible=0;"
      "recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_region;strokeColor=#00A4A6;fillColor=none;"
      "verticalAlign=top;align=left;spacingLeft=30;fontColor=#147EBA;dashed=1;", 40, 130, 1530, 1035)
celda("Google Cloud / Firebase (capa gratuita)", "rounded=1;arcSize=3;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#4285F4;"
      "strokeWidth=2;dashed=1;verticalAlign=top;align=left;spacingLeft=44;spacingTop=6;fontSize=15;fontStyle=1;fontColor=#4285F4;",
      1615, 90, 365, 710)
celda("", "sketch=0;html=1;shape=mxgraph.gcp2.hexIcon;prIcon=google_cloud_platform;fillColor=none;strokeColor=none;", 1620, 92, 36, 32)

# ---------------- Fila 1: ingesta, detección e IA ----------------
vm = icono(0, 0, "cloudshell", "dev", "AWS CloudShell (VM)\ndemo.py y carga_historica.py\nPython + boto3, sin Lambda")
ddb = icono(1, 0, "dynamodb", "datos", "DynamoDB af_*\non-demand, PITR, TTL 7 días\nalta disponibilidad multi-AZ")
st = icono(2, 0, "dynamodb_stream", "datos", "Stream de af_telemetria\nfiltro de eventos: solo\nINSERT sin historico")
det = icono(3, 0, "lambda", "computo", "detectorAnomalias (tope 1)\nEWMA + z-score propio y\npor pares, causa común")
ia = icono(4, 0, "lambda", "computo", "iaExplicar (tope 1)\ncausa y texto por rol\nGemini o plantilla")
rek = icono(5, 0, "rekognition", "ia", "Amazon Rekognition\ndetect-labels sobre la\nfoto del componente")
foto = icono(6, 0, "lambda", "computo", "analizarFoto (tope 1)\nguarda la foto en S3\ny pide etiquetas")

# ---------------- Filas 2 y 3 ----------------
ssm = icono(0, 1, "parameter_store", "gestion", "SSM Parameter Store\nSecureString: claves de\nGemini y GCP, ARN, umbrales")
kms = icono(1, 1, "key_management_service", "seguridad", "AWS KMS\ncifra los SecureString")
cw = icono(0, 2, "cloudwatch_2", "gestion", "CloudWatch\nlogs JSON y métricas\nde concurrencia")
texto("Menos de 10 Lambdas a la vez\n- tope (reservedConcurrency) en cada función\n- ingesta y carga histórica sin Lambdas\n"
      "- sin Parallel de Lambdas en Step Functions\n- frontend: 1 consulta a /panel cada 15 s",
      250, 600, 215, 150, 12, False, "#1F3FBF", "left", "#1F3FBF", "#F4F7FF")

# FlujoIncidente: recuadro con sus pasos
caja_flujo = celda("", "rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor=#FDF2F8;strokeColor=#E7157B;strokeWidth=2;", 490, 380, 620, 380)
sfn = icono(2, 1, "step_functions", "integracion", "", dx=-30, dy=-20)
texto("Step Functions: FlujoIncidente", 600, 395, 380, 30, 16, True, "#B0105B", "left")
pasos = ("1. Leer incidente (DynamoDB directo, sin Lambda)\n2. Choice por severidad: define el SLA\n3. Explicar con IA: iaExplicar\n"
         "4. Asignar técnico: cercanía, especialidad, ETA\n5. Reservar repuesto: almacén más cercano\n"
         "6. Preparar avisos: 4 bandejas en 1 Lambda\n7. Parallel: sns:publish directo a 3 roles\n"
         "8. Wait SLA y luego: ¿lo atendieron?\n9. Si no: escalar a supervisor y luego gerente\nCatch: aviso por SNS si algo falla")
texto(pasos, 510, 440, 580, 310, 14, False, "#232F3E", "left")

ops = icono(5, 1, "lambda", "computo", "operaciones (tope 1)\nasignar, reservar,\nnotificar, escalar")
sns = icono(5, 2, "sns", "integracion", "SNS: 3 tópicos\nuno por rol")
api = icono(6, 1, "api_gateway", "integracion", "API Gateway REST\nuna sola API\n(CORS solo web)")
lapi = icono(6, 2, "lambda", "computo", "Lambdas de consulta\n/panel, /flota, cerrar")

# ---------------- Fila 4: preventivo diario y persistencia ----------------
eb = icono(0, 3, "eventbridge", "integracion", "EventBridge\nregla diaria\n(06:00 Lima)")
prev = icono(1, 3, "step_functions", "integracion", "Step Functions\nPreventivoDiario")
batch = icono(2, 3, "lambda", "computo", "batchFlota (tope 1)\nproductividad, combustible,\npreventivo y repuestos")
plan = icono(3, 3, "lambda", "computo", "planificarPreventivo\nqué mantener y qué posponer\n+ patrones previos a fallas\n(reglas de alerta temprana)")
s3 = icono(4, 3, "s3", "almacen", "S3 con versionado\npreventivo/día.json\ny fotos de componentes")
st2 = icono(5, 3, "dynamodb_stream", "datos", "Stream de\naf_incidentes")
rep = icono(6, 3, "lambda", "computo", "replicarGcp (tope 1)\nréplica en otra nube")

# ---------------- Google ----------------
fh = icono_gcp(1757, 160, "firebase", "Firebase Hosting\nReact + Leaflet\ncloud-c2933.web.app")
gem = icono_gcp(1757, 380, "cloud_natural_language_api", "Gemini API\ngemini-3.5-flash-lite\n(IA generativa)")
fs = icono_gcp(1757, 600, "cloud_firestore", "Cloud Firestore\nréplica de incidentes")
usr = celda("Operador, técnico,<br>supervisor y gerente",
            "sketch=0;outlineConnect=0;fontColor=#232F3E;fillColor=#232F3E;strokeColor=none;verticalLabelPosition=bottom;"
            "verticalAlign=top;align=center;html=1;fontSize=13;aspect=fixed;shape=mxgraph.aws4.users;", 1760, 900, 70, 70)

# ---------------- Ruta de escala (no implementado) ----------------
celda("", "rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#8C8C8C;dashed=1;strokeWidth=2;", 60, 1040, 1490, 110)
texto("Ruta de escala a miles de máquinas (NO implementado):", 75, 1046, 600, 24, 14, True, "#5A5A5A", "left")
texto("máquinas → API Gateway → SQS (amortigua picos) → Lambda por lotes → DynamoDB on-demand + TTL → Firehose → S3 en Parquet → Athena / BigQuery",
      75, 1072, 1080, 60, 14, False, "#5A5A5A", "left")
for k, (res, cat) in enumerate((("sqs", "integracion"), ("kinesis_data_firehose", "analitica"), ("athena", "analitica"))):
    celda("", f"sketch=0;outlineConnect=0;fillColor={COL[cat]};strokeColor=#ffffff;html=1;aspect=fixed;"
              f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};opacity=60;", 1220 + k * 100, 1065, 64, 64)

# ---------------- Flechas del flujo principal ----------------
flecha(vm, ddb, "PutItem (boto3)")
flecha(ddb, st, "")
flecha(st, det, "eventos")
flecha(det, caja_flujo, "", puntos=[(690, 251), (690, 330)], salida=(0, 0.85), entrada=(0.3226, 0))
flecha(caja_flujo, ia, "", puntos=[(910, 226)], salida=(0.6774, 0), entrada=(0, 0.5))
texto("StartExecution", 698, 335, 120, 22, 13, False, "#232F3E", "left")
flecha(ia, gem, "HTTPS (clave en SSM)", puntos=[(1016, 150), (1606, 150), (1606, 416)], salida=(0.5, 0), entrada=(0, 0.5))
flecha(caja_flujo, ops, "invoca", salida=(1, 0.2), entrada=(0, 0.5))
flecha(caja_flujo, sns, "sns:publish", salida=(1, 0.7789), entrada=(0, 0.5))
flecha(sns, usr, "correo por rol", puntos=[(1345, 676), (1345, 805), (1795, 805)], salida=(1, 0.5), entrada=(0.5, 0))
flecha(usr, fh, "navegador", puntos=[(1900, 935), (1900, 194)], salida=(1, 0.5), entrada=(1, 0.5))
flecha(fh, api, "", puntos=[(1580, 194), (1580, 456)], salida=(0, 0.5), entrada=(1, 0.5))
texto("HTTPS: /panel<br>cada 15 s", 1622, 288, 110, 40, 12, False, "#232F3E", "left")
flecha(api, foto, "", puntos=[(1545, 438), (1545, 226)], salida=(1, 0.25), entrada=(1, 0.5))
flecha(api, lapi, "", puntos=[(1545, 474), (1545, 676)], salida=(1, 0.75), entrada=(1, 0.5))
flecha(foto, rek, "", salida=(0, 0.5), entrada=(1, 0.5))
flecha(eb, prev, "")
flecha(prev, batch, "")
flecha(batch, plan, "")
flecha(plan, s3, "s3:putObject")
flecha(st2, rep, "")
flecha(rep, fs, "REST", puntos=[(1600, 896), (1600, 634)], salida=(1, 0.5), entrada=(0, 0.5))
flecha(ssm, kms, "", salida=(1, 0.5), entrada=(0, 0.5))

# Números del recorrido de un incidente (estilo de los diagramas de clase)
for k, (x, y) in enumerate([(232, 196), (444, 196), (664, 196), (650, 300), (880, 300), (1140, 412), (1140, 632), (1500, 770)], 1):
    numero(k, x, y)

xml = ('<mxfile host="drawio"><diagram id="arquitectura" name="Arquitectura"><mxGraphModel dx="2000" dy="1200" grid="1" '
       'gridSize="10" guides="1" page="1" pageScale="1" pageWidth="2000" pageHeight="1200" background="#FFFFFF" math="0" shadow="0">'
       '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(celdas) + "</root></mxGraphModel></diagram></mxfile>")
destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arquitectura.drawio")
open(destino, "w", encoding="utf-8").write(xml)
print("ok", destino, len(celdas), "elementos")
