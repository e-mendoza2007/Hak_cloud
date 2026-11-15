"""Busca un modelo de Bedrock que SÍ funcione en tu cuenta y deja configurado SSM.
Uso:  python scripts/probar_bedrock.py"""
import boto3

REGION = "us-east-1"
CANDIDATOS = ["amazon.nova-micro-v1:0", "us.amazon.nova-micro-v1:0", "amazon.nova-lite-v1:0",
              "us.amazon.nova-lite-v1:0", "amazon.titan-text-lite-v1", "amazon.titan-text-express-v1",
              "anthropic.claude-3-haiku-20240307-v1:0", "us.anthropic.claude-3-haiku-20240307-v1:0"]

br = boto3.client("bedrock-runtime", region_name=REGION)
ssm = boto3.client("ssm", region_name=REGION)


def put(nombre, valor):
    ssm.put_parameter(Name=f"/arquifusion/{nombre}", Value=valor, Type="String", Overwrite=True)


elegido = None
for m in CANDIDATOS:
    try:
        r = br.converse(modelId=m, messages=[{"role": "user", "content": [{"text": "Responde solo: ok"}]}],
                        inferenceConfig={"maxTokens": 20})
        print(f"  FUNCIONA  {m}  -> {r['output']['message']['content'][0]['text'].strip()[:40]!r}")
        elegido = m
        break
    except Exception as e:
        codigo = getattr(e, "response", {}).get("Error", {}).get("Code", type(e).__name__)
        print(f"  no sirve  {m}  ({codigo})")
if elegido:
    put("bedrock_model_id", elegido); put("bedrock_region", REGION); put("ia_proveedores", "bedrock,gemini")
    print(f"\nListo: Bedrock con {elegido}. Gemini queda de respaldo.")
else:
    put("bedrock_region", REGION); put("ia_proveedores", "gemini")
    print("\nBedrock no está disponible en esta cuenta. Se configuró SOLO Gemini (necesitas gemini_api_key).")
