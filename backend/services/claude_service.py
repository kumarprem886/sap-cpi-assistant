"""
AI service — three providers, auto-detected from backend/.env

Priority (first match wins):
  1. AI_PROVIDER=anthropic  OR  ANTHROPIC_API_KEY set  → Claude claude-opus-4-5  (best quality)
  2. AI_PROVIDER=groq       OR  GROQ_API_KEY set       → Groq / Llama            (free cloud, 12K token limit)
  3. AI_PROVIDER=ollama     OR  neither key set        → Ollama local LLM        (free, no key, runs on your machine)

backend/.env quick-start (pick one block):

  # ── Option A: Claude (best quality) ──────────────────────────────────────
  ANTHROPIC_API_KEY=sk-ant-...
  # ANTHROPIC_MODEL=claude-opus-4-5        # default
  # ANTHROPIC_VISION_MODEL=claude-opus-4-5

  # ── Option B: Groq (free cloud, weaker quality) ───────────────────────────
  GROQ_API_KEY=gsk_...
  # GROQ_MODEL=llama-3.3-70b-versatile

  # ── Option C: Ollama local (no key needed) ────────────────────────────────
  AI_PROVIDER=ollama
  # OLLAMA_BASE_URL=http://localhost:11434  # default
  # OLLAMA_MODEL=qwen2.5-coder:14b         # default for 16 GB RAM
  # OLLAMA_VISION_MODEL=llava:7b           # for FD image analysis (optional)
"""

import os, base64, json
import httpx as _httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

# ── Detect provider ───────────────────────────────────────────────────────────
_ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
_GROQ_KEY      = os.getenv("GROQ_API_KEY",      "").strip()
_FORCED        = os.getenv("AI_PROVIDER",        "").strip().lower()

if   _FORCED == "anthropic" or (_ANTHROPIC_KEY and _FORCED != "groq" and _FORCED != "ollama"):
    AI_PROVIDER = "anthropic"
elif _FORCED == "groq"      or (_GROQ_KEY and _FORCED != "ollama"):
    AI_PROVIDER = "groq"
else:
    AI_PROVIDER = "ollama"

# Max output tokens exposed to callers (e.g. iflow.py)
# Anthropic / Ollama: generous; Groq free: 12K TPM → 6K leaves room for system prompt
MAX_GENERATION_TOKENS = 6000 if AI_PROVIDER == "groq" else 8000

# ── Shared system prompt ──────────────────────────────────────────────────────
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

# ── Provider-specific setup ───────────────────────────────────────────────────
if AI_PROVIDER == "anthropic":
    from anthropic import Anthropic
    _client      = Anthropic(api_key=_ANTHROPIC_KEY)
    MODEL        = os.getenv("ANTHROPIC_MODEL",        "claude-opus-4-5")
    VISION_MODEL = os.getenv("ANTHROPIC_VISION_MODEL", "claude-opus-4-5")

elif AI_PROVIDER == "groq":
    from groq import Groq
    _client      = Groq(api_key=_GROQ_KEY)
    MODEL        = os.getenv("GROQ_MODEL",        "llama-3.3-70b-versatile")
    VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

else:  # ollama
    _client      = None   # we call Ollama via httpx directly
    OLLAMA_BASE  = os.getenv("OLLAMA_BASE_URL",    "http://localhost:11434").rstrip("/")
    MODEL        = os.getenv("OLLAMA_MODEL",        "qwen2.5-coder:14b")
    VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava:7b")


def reload_from_env() -> None:
    """
    Re-read all AI-related env vars and re-initialize globals in-place.
    Called by the settings router after writing new values to .env.
    """
    from dotenv import load_dotenv as _load
    _load(override=True)   # re-read .env file into os.environ

    global AI_PROVIDER, _client, MODEL, VISION_MODEL, MAX_GENERATION_TOKENS
    global _ANTHROPIC_KEY, _GROQ_KEY, _FORCED

    _ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
    _GROQ_KEY      = os.getenv("GROQ_API_KEY",      "").strip()
    _FORCED        = os.getenv("AI_PROVIDER",        "").strip().lower()

    if   _FORCED == "anthropic" or (_ANTHROPIC_KEY and _FORCED not in ("groq", "ollama")):
        AI_PROVIDER = "anthropic"
    elif _FORCED == "groq"      or (_GROQ_KEY      and _FORCED != "ollama"):
        AI_PROVIDER = "groq"
    else:
        AI_PROVIDER = "ollama"

    MAX_GENERATION_TOKENS = 6000 if AI_PROVIDER == "groq" else 8000

    if AI_PROVIDER == "anthropic":
        from anthropic import Anthropic
        _client      = Anthropic(api_key=_ANTHROPIC_KEY)
        MODEL        = os.getenv("ANTHROPIC_MODEL",        "claude-opus-4-5")
        VISION_MODEL = os.getenv("ANTHROPIC_VISION_MODEL", "claude-opus-4-5")

    elif AI_PROVIDER == "groq":
        from groq import Groq
        _client      = Groq(api_key=_GROQ_KEY)
        MODEL        = os.getenv("GROQ_MODEL",        "llama-3.3-70b-versatile")
        VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    else:  # ollama — update OLLAMA_BASE global used by _ollama_chat / stream_generate
        global OLLAMA_BASE
        _client      = None
        OLLAMA_BASE  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        MODEL        = os.getenv("OLLAMA_MODEL",        "qwen2.5-coder:14b")
        VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava:7b")


def _build_system(extra: str) -> str:
    return SAP_SYSTEM_PROMPT + "\n\n" + extra if extra else SAP_SYSTEM_PROMPT


# ── Ollama helper (OpenAI-compatible endpoint, uses httpx already in deps) ───

def _ollama_chat(system: str, user_prompt: str, max_tokens: int,
                 model: str, image_b64: str = "", content_type: str = "") -> str:
    """Call Ollama's OpenAI-compatible /v1/chat/completions endpoint."""
    messages: list = [{"role": "system", "content": system}]

    if image_b64:
        # Multimodal message for vision models
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:{content_type};base64,{image_b64}"}},
                {"type": "text", "text": user_prompt},
            ],
        })
    else:
        messages.append({"role": "user", "content": user_prompt})

    try:
        resp = _httpx.post(
            f"{OLLAMA_BASE}/v1/chat/completions",
            headers={"Authorization": "Bearer ollama"},   # value ignored, header required
            json={
                "model":      model,
                "messages":   messages,
                "max_tokens": max_tokens,
                "stream":     False,
            },
            timeout=600,   # local inference can take a while for large outputs
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except _httpx.ConnectError:
        raise HTTPException(503,
            "Ollama is not running. Start it with: ollama serve  "
            "(install from https://ollama.ai)")
    except _httpx.HTTPStatusError as e:
        body = e.response.text[:300]
        if "model" in body and ("not found" in body or "pull" in body):
            raise HTTPException(503,
                f"Ollama model '{model}' not downloaded yet. "
                f"Run:  ollama pull {model}")
        raise HTTPException(502, f"Ollama error: {body}")


# ── generate ──────────────────────────────────────────────────────────────────

def generate(system_extra: str, user_prompt: str, cache: bool = True,
             max_tokens: int = 4096, model: str | None = None) -> str:
    """Generate a response from the configured AI provider."""
    system = _build_system(system_extra)
    chosen = model or MODEL

    # ── Anthropic ─────────────────────────────────────────────────────────────
    if AI_PROVIDER == "anthropic":
        try:
            resp = _client.messages.create(
                model=chosen,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return resp.content[0].text
        except Exception as e:
            status = getattr(e, "status_code", None)
            msg    = str(e)
            if status in (429, 529):
                raise HTTPException(429, f"Claude rate limit: {msg[:300]}. Try again shortly.")
            raise HTTPException(502, f"Claude error ({status}): {msg[:300]}")

    # ── Groq ──────────────────────────────────────────────────────────────────
    elif AI_PROVIDER == "groq":
        from groq import APIStatusError
        try:
            resp = _client.chat.completions.create(
                model=chosen,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except APIStatusError as e:
            status = e.status_code
            msg    = str(e)
            if status in (413, 429):
                raise HTTPException(429,
                    f"Groq limit reached: {msg[:300]}. "
                    "Shorten your description or try again in a few seconds.")
            raise HTTPException(502, f"Groq error ({status}): {msg[:300]}")

    # ── Ollama ────────────────────────────────────────────────────────────────
    else:
        return _ollama_chat(system, user_prompt, max_tokens, chosen)


# ── analyze_flow_image ────────────────────────────────────────────────────────

_VISION_PROMPT = """You are an SAP integration architect. Analyse this integration flow diagram carefully.

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
- Include ALL visible systems
- If multiple targets/receivers exist, list them in multiple_targets array
- cpi_steps: list the processing steps shown inside the CPI/middleware box
- If this is not a flow diagram, set is_flow_diagram to false and leave other fields empty"""


def analyze_flow_image(image_bytes: bytes, content_type: str = "image/png") -> dict:
    """Send an image to the vision model to extract the SAP integration flow."""
    b64 = base64.b64encode(image_bytes).decode()

    try:
        if AI_PROVIDER == "anthropic":
            resp = _client.messages.create(
                model=VISION_MODEL,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image",
                         "source": {"type": "base64", "media_type": content_type, "data": b64}},
                        {"type": "text", "text": _VISION_PROMPT},
                    ],
                }],
            )
            raw = resp.content[0].text.strip()

        elif AI_PROVIDER == "groq":
            resp = _client.chat.completions.create(
                model=VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url",
                         "image_url": {"url": f"data:{content_type};base64,{b64}"}},
                        {"type": "text", "text": _VISION_PROMPT},
                    ],
                }],
                max_tokens=1024,
            )
            raw = resp.choices[0].message.content.strip()

        else:  # ollama — needs a vision model (llava:7b etc.)
            raw = _ollama_chat(
                system="",
                user_prompt=_VISION_PROMPT,
                max_tokens=1024,
                model=VISION_MODEL,
                image_b64=b64,
                content_type=content_type,
            )
            raw = raw.strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(raw)

    except Exception as e:
        return {"is_flow_diagram": False, "error": str(e)}


# ── stream_generate ───────────────────────────────────────────────────────────

def stream_generate(system_extra: str, user_prompt: str):
    """Stream a response token-by-token."""
    system = _build_system(system_extra)

    if AI_PROVIDER == "anthropic":
        with _client.messages.stream(
            model=MODEL, max_tokens=4096, system=system,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    elif AI_PROVIDER == "groq":
        stream = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=4096,
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    else:  # ollama — streaming via httpx
        try:
            with _httpx.stream(
                "POST",
                f"{OLLAMA_BASE}/v1/chat/completions",
                headers={"Authorization": "Bearer ollama"},
                json={
                    "model":    MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user_prompt},
                    ],
                    "stream": True,
                },
                timeout=600,
            ) as resp:
                for line in resp.iter_lines():
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    try:
                        chunk = json.loads(line)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        pass
        except _httpx.ConnectError:
            yield "\n\n[Error: Ollama is not running — start it with: ollama serve]"
