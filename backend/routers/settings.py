"""
AI Settings router — read and update AI provider configuration at runtime.
Supports: anthropic, groq, openai, gemini, openrouter, mistral, nvidia, ollama
"""
from __future__ import annotations

import os
from fastapi import APIRouter
from pydantic import BaseModel

try:
    from dotenv import set_key as _dotenv_set_key, find_dotenv as _dotenv_find
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

router = APIRouter(prefix="/api/settings", tags=["settings"])

_MASKED = "••••••••"


def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_file_path() -> str:
    import os.path as osp
    candidate = osp.normpath(osp.join(osp.dirname(__file__), "..", ".env"))
    if osp.exists(candidate):
        return candidate
    if _DOTENV_AVAILABLE:
        found = _dotenv_find(usecwd=False, raise_error_if_not_found=False)
        if found:
            return found
    return candidate


def _set_env(key: str, value: str) -> None:
    os.environ[key] = value
    if _DOTENV_AVAILABLE:
        _dotenv_set_key(_env_file_path(), key, value, quote_mode="never")


def _mask(key: str) -> str:
    return _MASKED if _cfg(key) else ""


# ── GET /api/settings/ai ──────────────────────────────────────────────────────

@router.get("/ai")
def get_ai_settings():
    return {
        "provider":           _cfg("AI_PROVIDER", "groq"),
        # Anthropic
        "anthropicKey":       _mask("ANTHROPIC_API_KEY"),
        "anthropicModel":     _cfg("ANTHROPIC_MODEL",        "claude-opus-4-5"),
        # Groq
        "groqKey":            _mask("GROQ_API_KEY"),
        "groqModel":          _cfg("GROQ_MODEL",             "llama-3.3-70b-versatile"),
        # OpenAI
        "openaiKey":          _mask("OPENAI_API_KEY"),
        "openaiModel":        _cfg("OPENAI_MODEL",           "gpt-4o"),
        # Gemini
        "geminiKey":          _mask("GOOGLE_API_KEY"),
        "geminiModel":        _cfg("GEMINI_MODEL",           "gemini-2.0-flash"),
        # OpenRouter
        "openrouterKey":      _mask("OPENROUTER_API_KEY"),
        "openrouterModel":    _cfg("OPENROUTER_MODEL",       "meta-llama/llama-3.3-70b-instruct:free"),
        # Mistral
        "mistralKey":         _mask("MISTRAL_API_KEY"),
        "mistralModel":       _cfg("MISTRAL_MODEL",          "mistral-small-latest"),
        # NVIDIA NIM
        "nvidiaKey":          _mask("NVIDIA_API_KEY"),
        "nvidiaModel":        _cfg("NVIDIA_MODEL",           "meta/llama-3.3-70b-instruct"),
        # Ollama
        "ollamaBaseUrl":      _cfg("OLLAMA_BASE_URL",        "http://localhost:11434"),
        "ollamaModel":        _cfg("OLLAMA_MODEL",           "qwen2.5-coder:14b"),
        "ollamaVisionModel":  _cfg("OLLAMA_VISION_MODEL",    "llava:7b"),
    }


# ── PUT /api/settings/ai ──────────────────────────────────────────────────────

class AISettingsRequest(BaseModel):
    provider:          str = "groq"
    # Anthropic
    anthropicKey:      str = ""; anthropicModel:   str = "claude-opus-4-5"
    # Groq
    groqKey:           str = ""; groqModel:        str = "llama-3.3-70b-versatile"
    # OpenAI
    openaiKey:         str = ""; openaiModel:      str = "gpt-4o"
    # Gemini
    geminiKey:         str = ""; geminiModel:      str = "gemini-2.0-flash"
    # OpenRouter
    openrouterKey:     str = ""; openrouterModel:  str = "meta-llama/llama-3.3-70b-instruct:free"
    # Mistral
    mistralKey:        str = ""; mistralModel:     str = "mistral-small-latest"
    # NVIDIA NIM
    nvidiaKey:         str = ""; nvidiaModel:      str = "meta/llama-3.3-70b-instruct"
    # Ollama
    ollamaBaseUrl:     str = "http://localhost:11434"
    ollamaModel:       str = "qwen2.5-coder:14b"
    ollamaVisionModel: str = "llava:7b"


@router.put("/ai")
def update_ai_settings(req: AISettingsRequest):
    _set_env("AI_PROVIDER", req.provider.strip() or "groq")

    def _save_key_model(key_field: str, env_key: str, model_val: str, env_model: str, default: str):
        if key_field and key_field != _MASKED:
            _set_env(env_key, key_field.strip())
        _set_env(env_model, model_val.strip() or default)

    if req.provider == "anthropic":
        _save_key_model(req.anthropicKey,   "ANTHROPIC_API_KEY", req.anthropicModel,  "ANTHROPIC_MODEL",  "claude-opus-4-5")
    elif req.provider == "groq":
        _save_key_model(req.groqKey,        "GROQ_API_KEY",      req.groqModel,       "GROQ_MODEL",       "llama-3.3-70b-versatile")
    elif req.provider == "openai":
        _save_key_model(req.openaiKey,      "OPENAI_API_KEY",    req.openaiModel,     "OPENAI_MODEL",     "gpt-4o")
    elif req.provider == "gemini":
        _save_key_model(req.geminiKey,      "GOOGLE_API_KEY",    req.geminiModel,     "GEMINI_MODEL",     "gemini-2.0-flash")
    elif req.provider == "openrouter":
        _save_key_model(req.openrouterKey,  "OPENROUTER_API_KEY", req.openrouterModel, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    elif req.provider == "mistral":
        _save_key_model(req.mistralKey,     "MISTRAL_API_KEY",   req.mistralModel,    "MISTRAL_MODEL",    "mistral-small-latest")
    elif req.provider == "nvidia":
        _save_key_model(req.nvidiaKey,      "NVIDIA_API_KEY",    req.nvidiaModel,     "NVIDIA_MODEL",     "meta/llama-3.3-70b-instruct")
    else:  # ollama
        _set_env("OLLAMA_BASE_URL",     req.ollamaBaseUrl.strip()     or "http://localhost:11434")
        _set_env("OLLAMA_MODEL",        req.ollamaModel.strip()        or "qwen2.5-coder:14b")
        _set_env("OLLAMA_VISION_MODEL", req.ollamaVisionModel.strip() or "llava:7b")

    try:
        from services import claude_service
        claude_service.reload_from_env()
        return {"status": "saved", "provider": claude_service.AI_PROVIDER, "model": claude_service.MODEL}
    except Exception as e:
        return {"status": "saved", "provider": req.provider, "model": "—", "warning": str(e)}
