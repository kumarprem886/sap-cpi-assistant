from groq import Groq
import os, base64, json
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL        = os.getenv("GROQ_MODEL",        "llama-3.3-70b-versatile")
VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

SAP_SYSTEM_PROMPT = """You are an expert SAP Cloud Platform Integration (CPI) developer assistant.
You have deep knowledge of:
- SAP CPI iFlow design and XML structure
- Message mapping (graphical and XSLT-based)
- Groovy scripting for SAP CPI (using com.sap.gateway.ip.core.customdev.util.Message)
- XSLT transformations for SAP integrations
- SAP CPI adapters: HTTP, SFTP, SOAP, REST, OData, JDBC, Mail, etc.
- Content modifier, router, splitter, aggregator, and other CPI steps
- Exception handling and error handling patterns in CPI
- SAP Integration Suite best practices

Always generate production-ready, well-structured code. For XML/iFlow output, use proper SAP CPI namespace prefixes.
For Groovy scripts, always import the required SAP CPI classes.
"""


def generate(system_extra: str, user_prompt: str, cache: bool = True, max_tokens: int = 4096,
             model: str | None = None) -> str:
    """
    Generate a response from the AI model.
    max_tokens: Groq free tier cap is ~12 000 TPM total (prompt + output).
      Use 4096 for most calls, 8192 only for large structured outputs (iFlow XML).
    model: optional override (e.g. 'llama-3.1-8b-instant' for higher-TPM prebuilt generation).
    """
    system = SAP_SYSTEM_PROMPT + "\n\n" + system_extra if system_extra else SAP_SYSTEM_PROMPT
    chosen_model = model or MODEL

    response = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def analyze_flow_image(image_bytes: bytes, content_type: str = "image/png") -> dict:
    """
    Send an image to Groq vision model to extract the SAP integration flow.
    Returns a dict with keys: chain, protocols, cpi_steps, multiple_targets, description.
    Falls back to empty dict on any error.
    """
    b64 = base64.b64encode(image_bytes).decode()
    prompt = """You are an SAP integration architect. Analyse this integration flow diagram carefully.

Identify every system/component visible left-to-right and describe the full flow.

Return ONLY a valid JSON object (no markdown, no extra text):
{
  "is_flow_diagram": true,
  "chain": "SystemA->SystemB->SAP CPI->SystemC->SystemD",
  "protocols": {"SystemA->SystemB": "HTTPS", "SAP CPI->SystemC": "AS2"},
  "cpi_steps": ["Content Modifier", "Message Mapping", "Router", "Exception Subprocess"],
  "multiple_targets": [],
  "description": "One sentence describing what this integration does"
}

Rules:
- chain must use -> as separator between system names exactly as shown in the diagram
- Include ALL visible systems (e.g. AEM, Event Mesh, PIGMA, relay nodes)
- If multiple targets/receivers exist, list them in multiple_targets array
- cpi_steps: list the processing steps shown inside the CPI/middleware box
- If this is not a flow diagram, set is_flow_diagram to false and leave other fields empty"""

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:{content_type};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception as e:
        return {"is_flow_diagram": False, "error": str(e)}


def stream_generate(system_extra: str, user_prompt: str):
    system = SAP_SYSTEM_PROMPT + "\n\n" + system_extra if system_extra else SAP_SYSTEM_PROMPT

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4096,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
