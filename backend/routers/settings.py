"""
AI Settings router — read and update AI provider configuration at runtime.
Saves changes to backend/.env and hot-reloads the AI service immediately.
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
    """Write key=value to os.environ and persist to .env file."""
    os.environ[key] = value
    if _DOTENV_AVAILABLE:
        _dotenv_set_key(_env_file_path(), key, value, quote_mode="never")


# ── GET /api/settings/ai ──────────────────────────────────────────────────────

@router.get("/ai")
def get_ai_settings():
    """Return current AI provider settings. API keys are masked."""
    return {
        "provider":          _cfg("AI_PROVIDER", "groq"),
        # Anthropic
        "anthropicKey":      _MASKED if _cfg("ANTHROPIC_API_KEY") else "",
        "anthropicModel":    _cfg("ANTHROPIC_MODEL",        "claude-opus-4-5"),
        # Groq
        "groqKey":           _MASKED if _cfg("GROQ_API_KEY") else "",
        "groqModel":         _cfg("GROQ_MODEL",             "llama-3.3-70b-versatile"),
        # Ollama
        "ollamaBaseUrl":     _cfg("OLLAMA_BASE_URL",        "http://localhost:11434"),
        "ollamaModel":       _cfg("OLLAMA_MODEL",           "qwen2.5-coder:14b"),
        "ollamaVisionModel": _cfg("OLLAMA_VISION_MODEL",    "llava:7b"),
    }


# ── PUT /api/settings/ai ──────────────────────────────────────────────────────

class AISettingsRequest(BaseModel):
    provider:          str = "groq"
    # Anthropic
    anthropicKey:      str = ""
    anthropicModel:    str = "claude-opus-4-5"
    # Groq
    groqKey:           str = ""
    groqModel:         str = "llama-3.3-70b-versatile"
    # Ollama
    ollamaBaseUrl:     str = "http://localhost:11434"
    ollamaModel:       str = "qwen2.5-coder:14b"
    ollamaVisionModel: str = "llava:7b"


@router.put("/ai")
def update_ai_settings(req: AISettingsRequest):
    """
    Persist AI settings to backend/.env and hot-reload the AI service so
    changes take effect immediately — no backend restart needed.
    Secrets left as '••••••••' are kept unchanged.
    """
    _set_env("AI_PROVIDER", req.provider.strip() or "groq")

    if req.provider == "anthropic":
        if req.anthropicKey and req.anthropicKey != _MASKED:
            _set_env("ANTHROPIC_API_KEY", req.anthropicKey.strip())
        _set_env("ANTHROPIC_MODEL", req.anthropicModel.strip() or "claude-opus-4-5")

    elif req.provider == "groq":
        if req.groqKey and req.groqKey != _MASKED:
            _set_env("GROQ_API_KEY", req.groqKey.strip())
        _set_env("GROQ_MODEL", req.groqModel.strip() or "llama-3.3-70b-versatile")

    else:  # ollama
        _set_env("OLLAMA_BASE_URL",     req.ollamaBaseUrl.strip()     or "http://localhost:11434")
        _set_env("OLLAMA_MODEL",        req.ollamaModel.strip()        or "qwen2.5-coder:14b")
        _set_env("OLLAMA_VISION_MODEL", req.ollamaVisionModel.strip() or "llava:7b")

    # Hot-reload the AI service (re-initializes provider/client/model globals)
    try:
        from services import claude_service
        claude_service.reload_from_env()
        return {
            "status":   "saved",
            "provider": claude_service.AI_PROVIDER,
            "model":    claude_service.MODEL,
        }
    except Exception as e:
        return {"status": "saved", "provider": req.provider, "model": "—", "warning": str(e)}
