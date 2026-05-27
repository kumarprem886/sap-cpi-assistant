"""
Pre-built mapping generator for SAP IDoc ↔ OData catalog pairs.

Uses Claude AI to produce accurate, semantic field-level mappings for every
catalog pair, then stores them as JSON in resources/prebuilt/.

The generated JSON is used at download time to build the .mmap ZIP without
making any further API calls.
"""

import json
import re
import time
from pathlib import Path

from services.xsd_parser import smart_extract_paths, leaf_paths
from services.claude_service import generate
from services.mmap_builder import build_mmap_xml, build_mmap_zip

_RESOURCES   = Path(__file__).parent.parent.parent / "resources"
_PREBUILT    = _RESOURCES / "prebuilt"

# All catalog pairs — (src_file, tgt_file, mapping_name)
CATALOG_PAIRS: list[dict] = [
    # Material
    {"id": "MATMAS05_to_A_Product",         "src": "MATMAS05.xsd",         "tgt": "A_Product.xsd",          "name": "MM_MATMAS_to_Product"},
    {"id": "A_Product_to_MATMAS05",         "src": "A_Product.xsd",         "tgt": "MATMAS05.xsd",           "name": "MM_Product_to_MATMAS"},
    # Customer / Business Partner
    {"id": "DEBMAS06_to_A_BusinessPartner", "src": "DEBMAS06.xsd",          "tgt": "A_BusinessPartner.xsd",  "name": "MM_DEBMAS_to_BusinessPartner"},
    {"id": "A_BusinessPartner_to_DEBMAS06", "src": "A_BusinessPartner.xsd", "tgt": "DEBMAS06.xsd",           "name": "MM_BusinessPartner_to_DEBMAS"},
    # Vendor / Supplier
    {"id": "CREMAS05_to_A_Supplier",        "src": "CREMAS05.xsd",          "tgt": "A_Supplier.xsd",         "name": "MM_CREMAS_to_Supplier"},
    {"id": "A_Supplier_to_CREMAS05",        "src": "A_Supplier.xsd",        "tgt": "CREMAS05.xsd",           "name": "MM_Supplier_to_CREMAS"},
    {"id": "CREMAS05_to_A_BusinessPartner", "src": "CREMAS05.xsd",          "tgt": "A_BusinessPartner.xsd",  "name": "MM_CREMAS_to_BusinessPartner"},
    # Purchase Order
    {"id": "ORDERS05_to_A_PurchaseOrder",   "src": "ORDERS05.xsd",          "tgt": "A_PurchaseOrder.xsd",    "name": "MM_ORDERS_to_PurchaseOrder"},
    {"id": "A_PurchaseOrder_to_ORDERS05",   "src": "A_PurchaseOrder.xsd",   "tgt": "ORDERS05.xsd",           "name": "MM_PurchaseOrder_to_ORDERS"},
    # Sales Order
    {"id": "SALESORD05_to_A_SalesOrder",    "src": "SALESORD05.xsd",        "tgt": "A_SalesOrder.xsd",       "name": "MM_SALESORD_to_SalesOrder"},
    {"id": "A_SalesOrder_to_SALESORD05",    "src": "A_SalesOrder.xsd",      "tgt": "SALESORD05.xsd",         "name": "MM_SalesOrder_to_SALESORD"},
    # Invoice
    {"id": "INVOIC02_to_A_SupplierInvoice", "src": "INVOIC02.xsd",          "tgt": "A_SupplierInvoice.xsd",  "name": "MM_INVOIC_to_SupplierInvoice"},
    {"id": "A_SupplierInvoice_to_INVOIC02", "src": "A_SupplierInvoice.xsd", "tgt": "INVOIC02.xsd",           "name": "MM_SupplierInvoice_to_INVOIC"},
    {"id": "INVOIC02_to_A_BillingDocument", "src": "INVOIC02.xsd",          "tgt": "A_BillingDocument.xsd",  "name": "MM_INVOIC_to_BillingDocument"},
    {"id": "A_BillingDocument_to_INVOIC02", "src": "A_BillingDocument.xsd", "tgt": "INVOIC02.xsd",           "name": "MM_BillingDocument_to_INVOIC"},
    # Delivery
    {"id": "SALESORD05_to_A_OutboundDelivery","src": "SALESORD05.xsd",      "tgt": "A_OutboundDelivery.xsd", "name": "MM_DESADV_to_OutboundDelivery"},
    {"id": "A_OutboundDelivery_to_SALESORD05","src": "A_OutboundDelivery.xsd","tgt": "SALESORD05.xsd",        "name": "MM_OutboundDelivery_to_DESADV"},
    # Goods Movement
    {"id": "A_PurchaseOrder_to_A_MaterialDocument","src": "A_PurchaseOrder.xsd","tgt": "A_MaterialDocument.xsd","name": "MM_PO_to_MaterialDoc"},
]


_SYSTEM = (
    "You are an SAP S/4HANA integration architect with deep expertise in "
    "IDoc structures (MATMAS, DEBMAS, CREMAS, ORDERS, INVOIC, SALESORD) and "
    "SAP OData APIs (API_PRODUCT_SRV, API_BUSINESS_PARTNER, "
    "API_PURCHASEORDER_PROCESS_SRV, API_SALES_ORDER_SRV, "
    "API_SUPPLIERINVOICE_PROCESS_SRV, API_BILLING_DOCUMENT_SRV, "
    "API_OUTBOUND_DELIVERY_SRV, API_MATERIAL_DOCUMENT_SRV). "
    "Return ONLY valid JSON, no markdown, no explanation."
)


def _build_prompt(src_file: str, tgt_file: str,
                  src_leaves: list[str], tgt_leaves: list[str]) -> str:
    src_lines = "\n".join(f"  {p}" for p in src_leaves)
    tgt_lines = "\n".join(f"  {p}" for p in tgt_leaves)
    return f"""Map the source schema fields to the target schema fields.

SOURCE schema: {src_file}
SOURCE leaf fields (full XPath, use exactly as shown):
{src_lines}

TARGET schema: {tgt_file}
TARGET leaf fields (full XPath, use exactly as shown):
{tgt_lines}

Rules:
1. Only include a mapping when there is a genuine semantic match between source and target.
2. Do NOT map structural/container paths (they have children — ignore if you see them).
3. Do NOT force every target field to have a mapping — omit fields with no real equivalent.
4. Each source_path and target_path MUST be an EXACT copy of a path from the lists above.
5. One source field may map to multiple target fields if semantically correct.
6. Prefer the most-specific match (e.g. prefer segment/FIELD over a sibling segment match).

Return ONLY this JSON (no markdown fences):
{{
  "field_mappings": [
    {{"source_path": "...", "target_path": "...", "note": "brief reason"}}
  ]
}}"""


def _read_xsd(filename: str) -> str:
    return (_RESOURCES / filename).read_text(encoding="utf-8")


# Groq free-tier hard limit: 6,000 tokens per request (all models).
# Budget per call: ~320 system + ~250 wrapper + src + tgt + max_output <= 6,000
# With 1,500 max_output: field budget = 3,930 tokens ≈ 15,720 chars
# Split: 5,000 src chars + 3,000 tgt chars = 8,000 chars ≈ 2,000 tokens -> safe headroom.
_MAX_SRC_CHARS      = 5000  # trim source leaves to this many chars per call
_MAX_TGT_CHUNK_CHARS= 3000  # chunk target leaves at this size
_MAX_OUTPUT_TOKENS  = 1500  # per-call output cap (keeps total request < 6k tokens)
_CALL_DELAY         = 4.0   # seconds between API calls (Groq 30 RPM limit)
_RETRY_DELAYS       = [5, 15, 30]  # retry back-off on 413/429 errors
_PREBUILT_MODEL     = "llama-3.1-8b-instant"  # any Groq model; free tier = 6k TPM


def _trim_leaves(leaves: list[str], max_chars: int) -> list[str]:
    """Return a prefix of `leaves` whose total length (with newlines) fits in max_chars."""
    out, size = [], 0
    for leaf in leaves:
        cost = len(leaf) + 2
        if size + cost > max_chars:
            break
        out.append(leaf)
        size += cost
    return out


def _call_with_retry(prompt: str, verbose: bool = False) -> str | None:
    """Call the LLM with retry/back-off on 413/429 rate-limit errors.
    Uses _PREBUILT_MODEL and _MAX_OUTPUT_TOKENS calibrated to stay under the 6k TPM free limit.
    """
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            if verbose:
                print(f"    [retry {attempt}] waiting {delay}s ...")
            time.sleep(delay)
        try:
            raw = generate(_SYSTEM, prompt, cache=False, max_tokens=_MAX_OUTPUT_TOKENS, model=_PREBUILT_MODEL)
            return raw
        except Exception as exc:
            msg = str(exc).lower()
            if "413" in msg or "429" in msg or "rate" in msg or "limit" in msg or "quota" in msg or "too large" in msg:
                if verbose:
                    print(f"    [rate-limit/413] {str(exc)[:120]}")
                continue  # retry
            # Other errors — give up immediately
            if verbose:
                print(f"    [api-error] {exc}")
            return None
    return None  # all retries exhausted


def _chunk_target_leaves(tgt_leaves: list[str], max_chars: int = _MAX_TGT_CHUNK_CHARS) -> list[list[str]]:
    """Split target leaves into chunks that fit under the per-call token budget."""
    chunks, current, size = [], [], 0
    for leaf in tgt_leaves:
        cost = len(leaf) + 2
        if size + cost > max_chars and current:
            chunks.append(current)
            current, size = [], 0
        current.append(leaf)
        size += cost
    if current:
        chunks.append(current)
    return chunks


def generate_mapping_for_pair(pair: dict, verbose: bool = False) -> dict:
    """
    Use Claude to generate an accurate field mapping for one catalog pair.

    Strategy (minimises API calls to respect Groq rate limits):
    - Always send ALL source leaves in every call (trimmed at _MAX_LEAF_CHARS if huge).
    - Chunk only the TARGET leaves so we iterate over O(T) calls, not O(S×T).
    - Retry on 429 / rate-limit errors with exponential back-off.
    - Sleep _CALL_DELAY seconds between successive API calls.
    """
    src_xsd = _read_xsd(pair["src"])
    tgt_xsd = _read_xsd(pair["tgt"])

    src_root, src_paths = smart_extract_paths(src_xsd)
    tgt_root, tgt_paths = smart_extract_paths(tgt_xsd)

    src_leaves = leaf_paths(src_paths)
    tgt_leaves = leaf_paths(tgt_paths)

    if verbose:
        print(f"  src leaves: {len(src_leaves)}  tgt leaves: {len(tgt_leaves)}")

    # Sort src leaves: IDoc data segments (E1/Z1/Z2) first, EDI_DC40 control last
    # This ensures the most business-relevant fields are included when trimming.
    def _src_sort_key(path: str) -> int:
        seg = path.split("/")[3] if path.count("/") >= 3 else ""
        if seg.startswith("E1") or seg.startswith("Z1") or seg.startswith("Z2"):
            return 0   # business data first
        if seg == "EDI_DC40":
            return 2   # control record last
        return 1

    src_leaves_sorted = sorted(src_leaves, key=_src_sort_key)

    # Trim source to fit within the per-call token budget
    src_for_prompt = _trim_leaves(src_leaves_sorted, _MAX_SRC_CHARS)
    if verbose and len(src_for_prompt) < len(src_leaves):
        print(f"  [trim] src trimmed {len(src_leaves)} -> {len(src_for_prompt)} leaves for prompt")

    # Chunk target leaves (1 API call per chunk, target budget = _MAX_TGT_CHUNK_CHARS)
    tgt_chunks = _chunk_target_leaves(tgt_leaves)
    if verbose:
        print(f"  [chunks] {len(tgt_chunks)} target chunk(s) -> {len(tgt_chunks)} API call(s)")

    all_mappings: list[dict] = []
    seen_pairs: set[tuple] = set()
    src_set = set(src_leaves)
    tgt_set = set(tgt_leaves)

    for ti, tgt_chunk in enumerate(tgt_chunks):
        prompt = _build_prompt(pair["src"], pair["tgt"], src_for_prompt, tgt_chunk)

        if ti > 0:
            time.sleep(_CALL_DELAY)

        raw = _call_with_retry(prompt, verbose=verbose)
        if raw is None:
            if verbose:
                print(f"    [chunk {ti}] skipped after retries")
            continue

        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw.rstrip())

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            if verbose:
                print(f"    [chunk {ti}] JSON parse error — skipping")
            continue

        for fm in data.get("field_mappings", []):
            sp = fm.get("source_path", "").strip()
            tp = fm.get("target_path", "").strip()
            if not sp or not tp:
                continue
            # Validate paths exist in the actual leaf lists
            if sp not in src_set or tp not in tgt_set:
                continue
            key = (sp, tp)
            if key not in seen_pairs:
                seen_pairs.add(key)
                all_mappings.append({
                    "source_path": sp,
                    "target_path": tp,
                    "note": fm.get("note", ""),
                })

    return {
        "id":            pair["id"],
        "mapping_name":  pair["name"],
        "source_schema": pair["src"],
        "target_schema": pair["tgt"],
        "source_root":   src_root or "Source",
        "target_root":   tgt_root or "Target",
        "field_mappings": all_mappings,
        "total_fields":  len(all_mappings),
    }


def save_prebuilt(mapping: dict) -> Path:
    """Save a generated mapping dict to resources/prebuilt/<id>.json."""
    _PREBUILT.mkdir(parents=True, exist_ok=True)
    path = _PREBUILT / f"{mapping['id']}.json"
    path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    return path


def load_prebuilt(pair_id: str) -> dict | None:
    """Load a pre-built mapping JSON by pair ID. Returns None if not generated yet."""
    path = _PREBUILT / f"{pair_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def prebuilt_status() -> list[dict]:
    """Return status of all catalog pairs (generated / pending)."""
    result = []
    for pair in CATALOG_PAIRS:
        path = _PREBUILT / f"{pair['id']}.json"
        status = "ready"
        count  = 0
        if path.exists():
            try:
                data  = json.loads(path.read_text(encoding="utf-8"))
                count = data.get("total_fields", 0)
            except Exception:
                status = "error"
        else:
            status = "pending"
        result.append({
            "id":     pair["id"],
            "name":   pair["name"],
            "src":    pair["src"],
            "tgt":    pair["tgt"],
            "status": status,
            "fields": count,
        })
    return result


def build_mmap_from_prebuilt(pair_id: str) -> bytes | None:
    """Load a pre-built mapping and return the .mmap ZIP bytes. None if not ready."""
    mapping = load_prebuilt(pair_id)
    if not mapping:
        return None

    src_xsd = _read_xsd(mapping["source_schema"])
    tgt_xsd = _read_xsd(mapping["target_schema"])

    mmap_xml = build_mmap_xml(
        mapping_name   = mapping["mapping_name"],
        source_xsd_name= mapping["source_schema"],
        source_root    = mapping["source_root"],
        target_xsd_name= mapping["target_schema"],
        target_root    = mapping["target_root"],
        field_mappings = mapping["field_mappings"],
    )
    return build_mmap_zip(
        mapping_name   = mapping["mapping_name"],
        mmap_xml       = mmap_xml,
        source_xsd     = src_xsd,
        target_xsd     = tgt_xsd,
        source_xsd_name= mapping["source_schema"],
        target_xsd_name= mapping["target_schema"],
    )
