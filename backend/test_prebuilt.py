"""
Quick diagnostic: test what the model returns for a small sample mapping.
Run from backend/ directory:
  python test_prebuilt.py
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from services.xsd_parser import smart_extract_paths, leaf_paths
from services.claude_service import generate

_SYSTEM = (
    "You are an SAP S/4HANA integration architect with deep expertise in "
    "IDoc structures (MATMAS, DEBMAS, CREMAS, ORDERS, INVOIC, SALESORD) and "
    "SAP OData APIs. Return ONLY valid JSON, no markdown, no explanation."
)
_MODEL = "llama-3.1-8b-instant"

def main():
    # Test with a small subset
    from pathlib import Path
    resources = Path(__file__).parent.parent / "resources"

    print("=== Testing llama-3.1-8b-instant for SAP field mapping ===\n")

    # Use CREMAS05 -> A_Supplier (small schemas)
    src_xsd = (resources / "CREMAS05.xsd").read_text(encoding="utf-8")
    tgt_xsd = (resources / "A_Supplier.xsd").read_text(encoding="utf-8")

    src_root, src_paths = smart_extract_paths(src_xsd)
    tgt_root, tgt_paths = smart_extract_paths(tgt_xsd)

    src_leaves = leaf_paths(src_paths)
    tgt_leaves = leaf_paths(tgt_paths)

    print(f"CREMAS05 src leaves: {len(src_leaves)}")
    print(f"A_Supplier tgt leaves: {len(tgt_leaves)}")
    print(f"\nFirst 5 src leaves:")
    for p in src_leaves[:5]: print(f"  {p}")
    print(f"\nFirst 5 tgt leaves:")
    for p in tgt_leaves[:5]: print(f"  {p}")

    # Send a SMALL test: first 20 src leaves, first 15 tgt leaves
    src_sample = src_leaves[:20]
    tgt_sample = tgt_leaves[:15]

    src_lines = "\n".join(f"  {p}" for p in src_sample)
    tgt_lines = "\n".join(f"  {p}" for p in tgt_sample)

    prompt = f"""Map the source schema fields to the target schema fields.

SOURCE schema: CREMAS05.xsd
SOURCE leaf fields (full XPath, use exactly as shown):
{src_lines}

TARGET schema: A_Supplier.xsd
TARGET leaf fields (full XPath, use exactly as shown):
{tgt_lines}

Rules:
1. Only include a mapping when there is a genuine semantic match.
2. Each source_path and target_path MUST be an EXACT copy of a path from the lists above.
3. Omit target fields with no real equivalent.

Return ONLY this JSON (no markdown fences):
{{
  "field_mappings": [
    {{"source_path": "...", "target_path": "...", "note": "brief reason"}}
  ]
}}"""

    print("\n=== Sending test prompt to llama-3.1-8b-instant ===")
    print(f"Prompt src size: {len(src_lines)} chars, tgt size: {len(tgt_lines)} chars")

    try:
        raw = generate(_SYSTEM, prompt, cache=False, max_tokens=2048, model=_MODEL)
        print(f"\n=== RAW RESPONSE ===\n{raw[:2000]}")

        # Try to parse
        clean = raw.strip()
        if clean.startswith("```"):
            import re
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean.rstrip())

        data = json.loads(clean)
        mappings = data.get("field_mappings", [])
        print(f"\n=== PARSED: {len(mappings)} mappings ===")

        src_set = set(src_leaves)
        tgt_set = set(tgt_leaves)
        valid = 0
        for m in mappings[:10]:
            sp = m.get("source_path", "")
            tp = m.get("target_path", "")
            sp_ok = sp in src_set
            tp_ok = tp in tgt_set
            print(f"  [src_valid={sp_ok} tgt_valid={tp_ok}] {sp} -> {tp}")
            if sp_ok and tp_ok:
                valid += 1
        print(f"\nValid mappings: {valid}/{len(mappings)}")

    except Exception as e:
        print(f"\n=== ERROR: {e}")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()
