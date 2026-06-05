"""
Mapping feedback loop — stores user corrections to AI-derived rules.
When a user edits an AI-derived rule, the correction is stored and
injected into future AI prompts as few-shot examples.
"""
import json, os
from pathlib import Path

_FEEDBACK_FILE = Path(__file__).parent.parent / "data" / "mapping_feedback.json"

def save_correction(
    functional_rule: str,
    wrong_ai_rule: str,
    correct_rule: str,
    source_field: str = "",
    target_field: str = "",
) -> None:
    """Store a user correction: AI was wrong, user provided the right rule."""
    _FEEDBACK_FILE.parent.mkdir(exist_ok=True)
    data = _load()
    entry = {
        "functional": functional_rule.strip(),
        "wrong":      wrong_ai_rule.strip(),
        "correct":    correct_rule.strip(),
        "source":     source_field.strip(),
        "target":     target_field.strip(),
    }
    # Avoid duplicate entries (same functional rule -> same correction)
    key = functional_rule.strip().lower()
    data[key] = entry
    with open(_FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_examples(limit: int = 10) -> list[dict]:
    """Return the most recent user corrections as few-shot examples."""
    data = _load()
    return list(data.values())[-limit:]


def build_feedback_prompt_section(limit: int = 8) -> str:
    """Build a prompt section from stored corrections for injection into AI prompts."""
    examples = get_examples(limit)
    if not examples:
        return ""
    lines = ["== USER-CORRECTED EXAMPLES FROM YOUR MAPPINGS (highest priority) =="]
    for ex in examples:
        src = f" [source: {ex['source']}]" if ex.get("source") else ""
        lines.append(f'"{ex["functional"]}"{src}  ->  {ex["correct"]}')
    return "\n".join(lines)


def _load() -> dict:
    if not _FEEDBACK_FILE.exists():
        return {}
    try:
        with open(_FEEDBACK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
