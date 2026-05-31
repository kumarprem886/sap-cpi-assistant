import json
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
from services.claude_service import generate
from services.mmap_builder import build_mmap_xml, build_mmap_zip
from services.xsd_parser import auto_map, smart_extract_paths
from services.sheet_mapper import sheet_to_field_mappings, _parse_sheet_rows
from services.prebuilt_mapper import (
    CATALOG_PAIRS as _CATALOG_PAIRS,
    prebuilt_status,
    generate_mapping_for_pair,
    save_prebuilt,
    build_mmap_from_prebuilt,
    load_prebuilt,
)

router = APIRouter(prefix="/api/mapping", tags=["mapping"])

# Path to bundled XSD schemas
# mapping.py is at: backend/routers/mapping.py
# resources is at:  sap-cpi-assistant/resources/  (3 levels up)
_RESOURCES = Path(__file__).parent.parent.parent / "resources"


# ── Schema Catalog ────────────────────────────────────────────────────────────

@router.get("/catalog")
def get_catalog():
    """Return list of all bundled XSD schemas + prebuilt mapping status."""
    schemas = []
    if _RESOURCES.exists():
        for f in sorted(_RESOURCES.glob("*.xsd")):
            stem = f.stem
            kind = "odata" if stem.startswith("A_") else "idoc"
            schemas.append({"filename": f.name, "stem": stem, "kind": kind})
    return {
        "schemas":  schemas,
        "prebuilt": prebuilt_status(),
    }


@router.get("/schema/{filename}")
def get_schema(filename: str):
    """Return the content of a bundled XSD schema by filename."""
    if not filename.endswith(".xsd") or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    fpath = _RESOURCES / filename
    if not fpath.exists():
        raise HTTPException(status_code=404, detail=f"Schema '{filename}' not found")
    return {"filename": filename, "content": fpath.read_text(encoding="utf-8")}


# ── Pre-built Mapping Endpoints ───────────────────────────────────────────────

@router.get("/prebuilt/status")
def get_prebuilt_status():
    """Return generation status for every catalog pair."""
    return {"prebuilt": prebuilt_status()}


@router.post("/prebuilt/generate/{pair_id}")
def generate_prebuilt(pair_id: str, background_tasks: BackgroundTasks):
    """
    Trigger Claude-powered generation for one catalog pair.
    Generation happens in the background; poll /prebuilt/status to check.
    """
    pair = next((p for p in _CATALOG_PAIRS if p["id"] == pair_id), None)
    if not pair:
        raise HTTPException(status_code=404, detail=f"Unknown pair id '{pair_id}'")

    def _run():
        mapping = generate_mapping_for_pair(pair, verbose=True)
        save_prebuilt(mapping)

    background_tasks.add_task(_run)
    return {"status": "generating", "pair_id": pair_id}


@router.post("/prebuilt/generate-all")
def generate_all_prebuilt(background_tasks: BackgroundTasks):
    """Trigger Claude-powered generation for ALL catalog pairs in sequence."""
    _PAIR_DELAY = 12  # seconds between pairs (Groq rate-limit buffer)

    def _run_all():
        for i, pair in enumerate(_CATALOG_PAIRS):
            # Skip already-generated pairs
            from services.prebuilt_mapper import load_prebuilt
            existing = load_prebuilt(pair["id"])
            if existing and existing.get("total_fields", 0) > 0:
                print(f"[prebuilt] {pair['id']} already ready ({existing['total_fields']} fields) — skipping")
                continue
            if i > 0:
                time.sleep(_PAIR_DELAY)
            try:
                print(f"[prebuilt] generating {pair['id']} ...")
                mapping = generate_mapping_for_pair(pair, verbose=True)
                save_prebuilt(mapping)
                print(f"[prebuilt] {pair['id']} done — {mapping['total_fields']} fields")
            except Exception as e:
                print(f"[prebuilt] ERROR {pair['id']}: {e}")

    background_tasks.add_task(_run_all)
    return {"status": "generating_all", "total": len(_CATALOG_PAIRS)}


@router.get("/prebuilt/download/{pair_id}")
def download_prebuilt(pair_id: str):
    """Return the pre-built .mmap ZIP for a catalog pair (must be generated first)."""
    zip_bytes = build_mmap_from_prebuilt(pair_id)
    if zip_bytes is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pre-built mapping '{pair_id}' not generated yet. "
                   f"Call POST /prebuilt/generate/{pair_id} first.",
        )
    mapping = load_prebuilt(pair_id)
    filename = f"{mapping['mapping_name']}.zip"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/prebuilt/preview/{pair_id}")
def preview_prebuilt(pair_id: str):
    """Return the raw field_mappings JSON for inspection."""
    mapping = load_prebuilt(pair_id)
    if not mapping:
        raise HTTPException(status_code=404, detail=f"Not generated yet: {pair_id}")
    return mapping


class MappingRequest(BaseModel):
    source_schema: str
    target_schema: str
    mapping_hints: str = ""
    output_format: str = "groovy"


MAPPING_SYSTEM = """Generate SAP CPI message mappings.
For Groovy output: use com.sap.gateway.ip.core.customdev.util.Message and proper SAP CPI imports.
For XSLT output: generate valid XSLT 2.0 that works in SAP CPI.
For graphical mapping description: describe each field mapping with source path, target path, and any function/conversion needed.
Output ONLY the code — no explanation outside of comments."""


@router.post("/generate")
def generate_mapping(req: MappingRequest):
    prompt = f"""Generate a SAP CPI message mapping from source to target schema.

Source Schema / Structure:
{req.source_schema}

Target Schema / Structure:
{req.target_schema}

Mapping Hints / Business Rules:
{req.mapping_hints or "Map fields with matching names directly. For non-matching fields, use best-guess mapping based on field names and types."}

Output Format: {req.output_format}

{"Generate a Groovy script that reads the source message and produces the target message with all field mappings applied." if req.output_format == "groovy" else ""}
{"Generate XSLT 2.0 that transforms the source XML to target XML with all field mappings applied." if req.output_format == "xslt" else ""}
{"Describe each field mapping: source XPath -> target XPath, with any transformation function needed." if req.output_format == "description" else ""}
"""
    result = generate(MAPPING_SYSTEM, prompt)
    return {"result": result, "type": req.output_format}


# ── .mmap Generator ──────────────────────────────────────────────────────────

class MmapRequest(BaseModel):
    source_xsd: str
    target_xsd: str
    source_xsd_name: str = "source.xsd"   # original uploaded filename
    target_xsd_name: str = "target.xsd"   # original uploaded filename
    mapping_name: str = "MM_Mapping"
    hints: str = ""


def _ask_json(prompt: str) -> dict:
    raw = generate("Return ONLY valid JSON with no markdown fences or extra text.", prompt)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(raw)


@router.post("/generate-mmap")
def generate_mmap(req: MmapRequest):
    """
    Analyse source and target XSD schemas with AI, generate brick-based field mappings,
    and return a ZIP in SAP CPI's real urn:sap-com:xi .mmap format.
    ZIP: wsdl/*.xsd  +  mapping/<name>.mmap  (matches CPI iFlow artifact structure).
    """
    prompt = f"""You are an SAP CPI integration expert. Analyse these two XSD schemas and produce
a complete field-level mapping for a SAP CPI Graphical Message Mapping artifact.

SOURCE XSD:
{req.source_xsd[:3000]}

TARGET XSD:
{req.target_xsd[:3000]}

Additional hints / business rules:
{req.hints or "Map fields with matching or similar names directly. For non-matching fields, use best-guess mapping based on semantics and data types."}

Return ONLY a valid JSON object (no markdown, no extra text) with this exact structure:

{{
  "source_root": "RootElementName",
  "target_root": "RootElementName",
  "field_mappings": [
    {{
      "source_path": "/SourceRoot/ParentElement/FieldA",
      "target_path": "/TargetRoot/ParentElement/FieldB"
    }}
  ]
}}

Rules:
- source_root / target_root: the top-level XML element name (from <xs:element name="..."> at root).
- Paths MUST start with /RootElement/ and use bare element names exactly as in the XSD.
- Include container (parent) elements as their own entries (e.g. /Order/Header -> /PO/Header).
- Include ALL mappable field pairs — be thorough. Omit fields with no match.
- No namespace prefixes in paths.
"""
    data = _ask_json(prompt)

    source_root  = data.get("source_root", "SourceMessage")
    target_root  = data.get("target_root", "TargetMessage")
    mappings     = [
        {"source_path": fm["source_path"], "target_path": fm["target_path"]}
        for fm in data.get("field_mappings", [])
        if fm.get("source_path") and fm.get("target_path")
    ]

    # Use the real uploaded filenames (ensures wsdl/ entry matches .mmap reference)
    src_xsd_name = req.source_xsd_name or "source.xsd"
    tgt_xsd_name = req.target_xsd_name or "target.xsd"

    mmap_xml = build_mmap_xml(
        mapping_name=req.mapping_name,
        source_xsd_name=src_xsd_name,
        source_root=source_root,
        target_xsd_name=tgt_xsd_name,
        target_root=target_root,
        field_mappings=mappings,
    )

    zip_bytes = build_mmap_zip(
        mapping_name=req.mapping_name,
        mmap_xml=mmap_xml,
        source_xsd=req.source_xsd,
        target_xsd=req.target_xsd,
        source_xsd_name=src_xsd_name,
        target_xsd_name=tgt_xsd_name,
    )

    filename = f"{req.mapping_name}.zip"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Template Download ─────────────────────────────────────────────────────────

@router.get("/template")
def download_template():
    """Return the Excel mapping template (.xlsx) for download."""
    from services.template_service import build_template_bytes
    xlsx_bytes = build_template_bytes()
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="CPI_Mapping_Template.xlsx"'},
    )


# ── Sheet Preview (parse + XSD resolve, no .mmap) ────────────────────────────

@router.post("/preview-sheet")
async def preview_sheet(
    source_xsd:    UploadFile = File(...),
    target_xsd:    UploadFile = File(...),
    mapping_sheet: UploadFile = File(...),
):
    """
    Parse the mapping sheet, resolve fields against uploaded XSDs,
    and return matched + unmatched rows for the frontend preview table.
    Does NOT generate a .mmap.
    """
    src_bytes   = await source_xsd.read()
    tgt_bytes   = await target_xsd.read()
    sheet_bytes = await mapping_sheet.read()

    src_xsd_text = src_bytes.decode("utf-8", errors="replace")
    tgt_xsd_text = tgt_bytes.decode("utf-8", errors="replace")

    try:
        src_root, src_paths = smart_extract_paths(src_xsd_text)
        tgt_root, tgt_paths = smart_extract_paths(tgt_xsd_text)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse XSD: {exc}")

    # Get the raw sheet rows first (with functional/technical columns)
    raw_rows = _parse_sheet_rows(sheet_bytes, mapping_sheet.filename or "mapping.xlsx")

    # Resolve paths
    try:
        matched, unmatched = sheet_to_field_mappings(
            sheet_bytes,
            mapping_sheet.filename or "mapping.xlsx",
            src_paths,
            tgt_paths,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse mapping sheet: {exc}")

    # Index unmatched rows by (source, target) for quick lookup of reason
    unmatched_index: dict[tuple, str] = {
        (str(u.get("source") or "").lower(), str(u.get("target") or "").lower()): u.get("reason", "")
        for u in unmatched
    }

    # Index matched rows by target last-segment for resolved path lookup
    matched_by_tgt: dict[str, dict] = {}
    for m in matched:
        tgt_seg = m.get("target_path", "").rsplit("/", 1)[-1].lower()
        if tgt_seg and tgt_seg not in matched_by_tgt:
            matched_by_tgt[tgt_seg] = m

    # Build enriched row list with per-cell match status + resolved full paths
    enriched_rows = []
    for raw in raw_rows:
        src_f   = raw.get("source") or ""
        tgt_f   = raw.get("target") or ""
        func_r  = raw.get("functional_rule") or raw.get("rule") or ""
        tech_r  = raw.get("technical_rule") or ""

        # Find match entry for this target field
        match_entry = matched_by_tgt.get(tgt_f.lower()) if tgt_f else None
        is_matched  = match_entry is not None or any(
            (m.get("source_path", "").rsplit("/", 1)[-1].lower() == src_f.lower() or not src_f)
            and (m.get("target_path", "").rsplit("/", 1)[-1].lower() == tgt_f.lower())
            for m in matched
        )
        status = "matched" if is_matched else "unmatched" if (src_f or tgt_f) else "empty"

        # Determine which specific cell is unmatched
        reason = unmatched_index.get((src_f.lower(), tgt_f.lower()), "")
        src_matched = is_matched or not src_f or ("source" not in reason and "no source" not in reason)
        tgt_matched = is_matched or not tgt_f or ("target" not in reason)

        # Resolved full XSD paths (for display in UI)
        resolved_src_path = match_entry.get("source_path", "") if match_entry else ""
        resolved_tgt_path = match_entry.get("target_path", "") if match_entry else ""

        enriched_rows.append({
            "source":          src_f,
            "target":          tgt_f,
            "functional_rule": func_r,
            "technical_rule":  tech_r,
            "status":          status,
            "source_matched":  src_matched,
            "target_matched":  tgt_matched,
            "source_path":     resolved_src_path,
            "target_path":     resolved_tgt_path,
        })

    return {
        "rows":        enriched_rows,
        "matched":     len(matched),
        "unmatched":   len(unmatched),
        "unmatched_detail": unmatched,
        "src_root":    src_root,
        "tgt_root":    tgt_root,
        "src_paths":   src_paths[:200],   # cap for payload size
        "tgt_paths":   tgt_paths[:200],
    }


# ── AI Rule Derivation ────────────────────────────────────────────────────────

_DERIVE_SYSTEM = """You are an SAP CPI Graphical Message Mapping expert.

Your job: read a functional description (written in plain English by a business analyst) and
produce the correct SAP CPI Graphical Mapping expression. The user may write anything from a
single word to a full sentence — understand their INTENT and produce the right expression.

━━ AVAILABLE SAP CPI STANDARD FUNCTIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STRING:
  toUpperCase((/field))                         → uppercase text
  toLowerCase((/field))                         → lowercase text
  trim((/field))                                → remove leading/trailing spaces
  length((/field))                              → character count
  substring((/field), startIndex, length)       → extract part of string (0-based)
  (/field1)+SEPARATOR+(/field2)                 → join two fields with a separator
  replaceAll((/field), searchText, replacement) → replace text in field
  SplitByValue((/field), delimiter)             → split into multiple values

DATE:
  formatDate((/field), inputFormat, outputFormat)
    — reformats date/time strings. Common formats: yyyyMMdd, yyyy-MM-dd, HHmmss, HH:mm:ss
    — e.g. formatDate((/date), yyyyMMdd, yyyy-MM-dd)

NUMERIC:
  add((/field1), (/field2))       → add two field values
  subtract((/field1), (/field2))  → subtract
  multiply((/field1), (/field2))  → multiply
  divide((/field1), (/field2))    → divide

CONDITIONAL:
  if((/boolField), valueIfTrue, valueIfFalse)
  equals((/field), CONSTANT)      → returns true/false
  exists((/field))                → true if field has a value
  mapWithDefault((/field), defaultValue) → value or default if empty

NODE FUNCTIONS:
  useOneAsMany((/field))          → repeat single value for each occurrence of target
  removeContexts((/field))        → flatten multi-value into single context
  collapseContexts((/field))      → merge multiple values into one

━━ INTENT RECOGNITION EXAMPLES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Description → Expression (source field: "date", available fields: date, time, plant, qty)

"direct copy"                        → ""
"copy as-is"                         → ""
"same value"                         → ""
"uppercase"                          → toUpperCase((/date))
"make upper case"                    → toUpperCase((/date))
"convert to uppercase"               → toUpperCase((/date))
"lowercase"                          → toLowerCase((/date))
"trim spaces"                        → trim((/date))
"remove whitespace"                  → trim((/date))
"format date yyyyMMdd to yyyy-MM-dd" → formatDate((/date), yyyyMMdd, yyyy-MM-dd)
"reformat date from YYYYMMDD to ISO" → formatDate((/date), yyyyMMdd, yyyy-MM-dd)
"combine date and time with T"       → (/date)+T+(/time)
"join date and time using T between" → (/date)+T+(/time)
"concatenate plant and date with -"  → (/plant)+- +(/date)
"first 6 characters"                 → substring((/date), 0, 6)
"extract first 4 chars"              → substring((/date), 0, 4)
"remove dashes"                      → replaceAll((/date), -, )
"replace space with underscore"      → replaceAll((/date), , _)
"repeat for each line"               → useOneAsMany((/date))
"use one value for all"              → useOneAsMany((/date))
"default to N/A if empty"            → mapWithDefault((/date), N/A)
"split by comma"                     → SplitByValue((/date), ,)
"add qty to itself"                  → add((/qty), (/qty))

━━ RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ALWAYS use the actual source field names provided — never write (/field) as a literal
2. Field names go in parentheses: (/fieldName) — use short name, not full XPath
3. Separators and constants go WITHOUT parentheses: T, -, _, EUR, yyyyMMdd
4. For direct copy (no transformation), return exactly: ""
5. If description mentions multiple fields, look them up in the available source fields list
6. If the operation genuinely cannot be done with standard functions (e.g. complex arithmetic
   with hardcoded numbers like "divide by 2"), use the closest standard function and note it
   OR return GROOVY: followed by a one-liner Groovy expression
7. Return ONLY the expression string on one line — no explanation, no markdown, no quotes
"""


class DeriveRuleRequest(BaseModel):
    rows: list[dict]


@router.post("/derive-rules")
def derive_rules(req: DeriveRuleRequest):
    """
    For each row with a functional_rule but no technical_rule,
    use AI to understand the user's intent and derive the correct
    SAP CPI Graphical Mapping expression. Works with any free-form
    English description — not just formal syntax.
    """
    results = []
    for row in req.rows:
        src       = (row.get("source") or "").strip()
        tgt       = (row.get("target") or "").strip()
        func_rule = (row.get("functional_rule") or "").strip()
        tech_rule = (row.get("technical_rule") or "").strip()

        if func_rule and not tech_rule:
            all_src = (row.get("available_source_fields") or "").strip()

            prompt = f"""MAPPING ROW:
Source field: {src or "(not specified — infer from description)"}
Target field: {tgt or "(not specified)"}
All available source fields: {all_src or "(unknown)"}

WHAT THE USER WROTE (functional description):
"{func_rule}"

Understand what the user wants to do and produce the correct SAP CPI Graphical Mapping expression.
Use the actual source field name(s) — not generic placeholders.
Return ONLY the expression on one line."""

            try:
                derived = generate(_DERIVE_SYSTEM, prompt, max_tokens=300).strip()
                if derived.startswith("```"):
                    derived = derived.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                results.append({**row, "technical_rule": derived, "ai_derived": True})
            except Exception as e:
                results.append({**row, "ai_derived": False, "derive_error": str(e)})
        else:
            results.append({**row, "ai_derived": False})

    return {"rows": results}


# ── ZIP preview — returns file list + mmap XML without downloading ────────────

@router.post("/from-sheet-preview")
async def preview_mmap_from_sheet(
    source_xsd:    UploadFile = File(...),
    target_xsd:    UploadFile = File(...),
    mapping_sheet: UploadFile = File(...),
    mapping_name:  str        = Form("MM_Mapping"),
):
    """
    Same processing as /from-sheet but returns the mmap XML and file list
    as JSON instead of streaming a ZIP download. Used by the frontend to
    show a ZIP contents preview before the user downloads.
    """
    src_bytes   = await source_xsd.read()
    tgt_bytes   = await target_xsd.read()
    sheet_bytes = await mapping_sheet.read()

    src_xsd_text = src_bytes.decode("utf-8", errors="replace")
    tgt_xsd_text = tgt_bytes.decode("utf-8", errors="replace")

    try:
        src_root, src_paths = smart_extract_paths(src_xsd_text)
        tgt_root, tgt_paths = smart_extract_paths(tgt_xsd_text)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse XSD: {exc}")

    try:
        matched, unmatched = sheet_to_field_mappings(
            sheet_bytes, mapping_sheet.filename or "mapping.xlsx",
            src_paths, tgt_paths,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse mapping sheet: {exc}")

    safe_name    = mapping_name.replace(" ", "_") or "MM_Mapping"
    src_xsd_name = source_xsd.filename or "source.xsd"
    tgt_xsd_name = target_xsd.filename or "target.xsd"

    mmap_xml = build_mmap_xml(
        mapping_name    = safe_name,
        source_xsd_name = src_xsd_name,
        source_root     = src_root or "Source",
        target_xsd_name = tgt_xsd_name,
        target_root     = tgt_root or "Target",
        field_mappings  = matched,
    )

    files = [f"mapping/{safe_name}.mmap"]
    if src_xsd_name:
        files.append(f"wsdl/{src_xsd_name}")
    if tgt_xsd_name and tgt_xsd_name != src_xsd_name:
        files.append(f"wsdl/{tgt_xsd_name}")

    return {
        "mmap_xml":  mmap_xml,
        "files":     files,
        "matched":   len(matched),
        "unmatched": len(unmatched),
        "mapping_name": safe_name,
    }


# ── Sheet-driven .mmap ────────────────────────────────────────────────────────

@router.post("/from-sheet")
async def generate_mmap_from_sheet(
    source_xsd:    UploadFile = File(...),
    target_xsd:    UploadFile = File(...),
    mapping_sheet: UploadFile = File(...),
    mapping_name:  str        = Form("MM_Mapping"),
):
    """
    Build a SAP CPI .mmap from three uploaded files:
      - source_xsd    : source XSD schema
      - target_xsd    : target XSD schema
      - mapping_sheet : Excel (.xlsx) or CSV mapping table with source->target columns

    The mapping sheet is parsed to extract field pairs, which are then resolved
    to full XPath paths in the uploaded XSDs. Returns a .mmap ZIP bundle.
    """
    src_bytes   = await source_xsd.read()
    tgt_bytes   = await target_xsd.read()
    sheet_bytes = await mapping_sheet.read()

    src_xsd_text = src_bytes.decode("utf-8", errors="replace")
    tgt_xsd_text = tgt_bytes.decode("utf-8", errors="replace")

    # Extract all paths from both XSDs
    try:
        src_root, src_paths = smart_extract_paths(src_xsd_text)
        tgt_root, tgt_paths = smart_extract_paths(tgt_xsd_text)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse XSD: {exc}")

    # Parse the mapping sheet and resolve paths
    try:
        matched, unmatched = sheet_to_field_mappings(
            sheet_bytes,
            mapping_sheet.filename or "mapping.xlsx",
            src_paths,
            tgt_paths,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse mapping sheet: {exc}")

    if not matched:
        detail = "No field pairs could be resolved. "
        if unmatched:
            detail += f"{len(unmatched)} unmatched rows: " + \
                      "; ".join(f"{r['source']}->{r['target']} ({r['reason']})" for r in unmatched[:5])
        raise HTTPException(status_code=422, detail=detail)

    src_xsd_name = source_xsd.filename or "source.xsd"
    tgt_xsd_name = target_xsd.filename or "target.xsd"
    safe_name    = mapping_name.replace(" ", "_") or "MM_Mapping"

    mmap_xml = build_mmap_xml(
        mapping_name    = safe_name,
        source_xsd_name = src_xsd_name,
        source_root     = src_root or "Source",
        target_xsd_name = tgt_xsd_name,
        target_root     = tgt_root or "Target",
        field_mappings  = matched,
    )
    zip_bytes = build_mmap_zip(
        mapping_name    = safe_name,
        mmap_xml        = mmap_xml,
        source_xsd      = src_xsd_text,
        target_xsd      = tgt_xsd_text,
        source_xsd_name = src_xsd_name,
        target_xsd_name = tgt_xsd_name,
    )

    summary = f"mapped={len(matched)},unmatched={len(unmatched)}"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.zip"',
            "X-Mapping-Summary": summary,
            "Access-Control-Expose-Headers": "X-Mapping-Summary",
        },
    )


# ── AutoMap ───────────────────────────────────────────────────────────────────

class AutoMapRequest(BaseModel):
    source_fields: str
    target_fields: str


@router.post("/automap")
def auto_map_fields(req: AutoMapRequest):
    prompt = f"""Perform intelligent field mapping between source and target fields for SAP CPI.

Source Fields (one per line, format: fieldName: dataType):
{req.source_fields}

Target Fields (one per line, format: fieldName: dataType):
{req.target_fields}

Create a mapping table showing:
1. Source Field -> Target Field
2. Confidence (High/Medium/Low)
3. Transformation needed (if any)
4. Reasoning

Then generate the corresponding Groovy script for SAP CPI to implement these mappings.
"""
    result = generate(MAPPING_SYSTEM, prompt)
    return {"result": result, "type": "automap"}


# ── Local XSD Auto-Map (no AI API call) ──────────────────────────────────────

class MmapAutoRequest(BaseModel):
    source_xsd: str
    target_xsd: str
    source_xsd_name: str = "source.xsd"
    target_xsd_name: str = "target.xsd"
    mapping_name: str = "MM_Mapping"


@router.post("/generate-mmap-auto")
def generate_mmap_auto(req: MmapAutoRequest):
    """
    Parse source and target XSD locally (no AI call), extract ALL element paths,
    match every target field to the best source field using name-similarity scoring,
    and return a ZIP bundle in SAP CPI's urn:sap-com:xi .mmap format.

    Every single target path is guaranteed to appear in the output — nothing is skipped.
    """
    src_root, tgt_root, mappings = auto_map(req.source_xsd, req.target_xsd)

    src_xsd_name = req.source_xsd_name or "source.xsd"
    tgt_xsd_name = req.target_xsd_name or "target.xsd"

    mmap_xml = build_mmap_xml(
        mapping_name=req.mapping_name,
        source_xsd_name=src_xsd_name,
        source_root=src_root or "Source",
        target_xsd_name=tgt_xsd_name,
        target_root=tgt_root or "Target",
        field_mappings=mappings,
    )

    zip_bytes = build_mmap_zip(
        mapping_name=req.mapping_name,
        mmap_xml=mmap_xml,
        source_xsd=req.source_xsd,
        target_xsd=req.target_xsd,
        source_xsd_name=src_xsd_name,
        target_xsd_name=tgt_xsd_name,
    )

    filename = f"{req.mapping_name}.zip"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


