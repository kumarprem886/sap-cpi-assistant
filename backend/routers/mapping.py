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

Convert any plain-English functional description into the correct SAP CPI Graphical Mapping expression.

== CONTEXT — MOST IMPORTANT ==
Context = how many times a value occurs at a given XML hierarchy level.
- N→1 (aggregate): sum(), average(), count() — Statistics functions collapse N values to 1
- 1→N (expand): useOneAsMany() — repeat one value for multiple targets
- N→N (same level): direct copy or transformation functions
- N→1 (collapse text): collapseContexts()

== STATISTICS FUNCTIONS (for aggregation — NO Groovy needed) ==
sum((/repeating/field))     → SUM of all occurrences (total quantity, total amount)
average((/f))               → average of all values
count((/f))                 → count of occurrences
first((/f))                 → first occurrence value
last((/f))                  → last occurrence value
index((/f))                 → sequential index 0, 1, 2, 3 ...

== FUNCTIONS ADDED TO COMPLETE THE OFFICIAL SAP CPI LIBRARY ==
inv((/f))                   → 1/x inverse (Arithmetic)
ifS((/f), val, y, n)        → if field string-equals val then y else n (Boolean)
ifSWithoutElse((/f), val, y) → ifS without else branch (Boolean)
isNil((/f))                 → true if value is xsi:nil (Boolean)
constant(VALUE)             → emit a fixed constant value with no source field (Constant)
xsi:nil                     → emit xsi:nil="true" for the target element (Constant)
getHeader(NAME)             → get message header value by name (Node)
getProperty(NAME)           → get integration property by name (Node)
fixValues((/f))             → fixed value lookup table key→value (Conversion)
valueMapping((/f))          → Value Mapping artifact table lookup (Conversion)

== ALL SAP CPI STANDARD FUNCTIONS ==

STRING:
  toUpperCase((/field))                            -> uppercase
  toLowerCase((/field))                            -> lowercase
  trim((/field))                                   -> remove whitespace
  length((/field))                                 -> character count
  substring((/field), startPos, length)            -> extract substring (0-based)
  (/field1)+SEPARATOR+(/field2)                    -> join with separator (concat)
  replaceAll((/field), searchText, replacement)    -> replace all occurrences
  SplitByValue((/field), delimiter)                -> split into multiple values
  indexOf((/field), searchText)                    -> position of first match
  lastIndexOf((/field), searchText)                -> position of last match
  endsWith((/field), suffix)                       -> boolean: ends with
  startsWith((/field), prefix)                     -> boolean: starts with
  compare((/field1), (/field2))                    -> lexicographic compare
  equalsS((/field), value)                         -> string equality boolean
  contains((/field), searchText)                   -> boolean: contains text

DATE:
  formatDate((/field), inputFormat, outputFormat)  -> reformat date/time (fname: TransformDate)
    Formats: yyyyMMdd, yyyy-MM-dd, HHmmss, HH:mm:ss, dd.MM.yyyy etc.
  currentDate()                                    -> today's date (no source field)
  DateBefore((/date1), (/date2))                   -> boolean: date1 before date2
  DateAfter((/date1), (/date2))                    -> boolean: date1 after date2
  CompareDates((/date1), (/date2))                 -> 1 if after, 0 if equal, -1 if before

ARITHMETIC:
  add((/field1), (/field2))                        -> numeric add
  subtract((/field1), (/field2))                   -> subtract
  multiply((/field1), (/field2))                   -> multiply
  divide((/field1), (/field2))                     -> divide
  abs((/field))                                    -> absolute value (fname: abs)
  neg((/field))                                    -> negate
  inv((/field))                                    -> inverse 1/x
  sqrt((/field))                                   -> square root
  square((/field))                                 -> square x^2 (fname: sqr)
  sign((/field))                                   -> sign: 1, 0, or -1
  round((/field))                                  -> round to integer
  ceil((/field))                                   -> round up
  floor((/field))                                  -> round down
  power((/base), (/exponent))                      -> base^exponent
  lesser((/field1), (/field2))                     -> true if field1 < field2 (fname: less)
  greater((/field1), (/field2))                    -> true if field1 > field2
  max((/field1), (/field2))                        -> maximum of two values
  min((/field1), (/field2))                        -> minimum of two values
  FormatNum((/field), pattern)                     -> format as number e.g. 0.00

CONDITIONAL / BOOLEAN:
  if((/condition), valueIfTrue, valueIfFalse)      -> conditional (3 args)
  ifS((/field), compareVal, valueIfTrue, valueIfFalse) -> if string-equals compareVal
  ifWithoutElse((/condition), valueIfTrue)         -> if without else
  ifSWithoutElse((/field), compareVal, valueIfTrue) -> ifS without else
  Equals((/field), VALUE)                          -> equality check (fname: Equals)
  notEquals((/field), VALUE)                       -> inequality check
  And((/bool1), (/bool2))                          -> logical AND
  Or((/bool1), (/bool2))                           -> logical OR
  Not((/bool))                                     -> logical NOT
  isNil((/field))                                  -> true if field is xsi:nil

CONSTANT:
  constant(VALUE)                                  -> fixed constant with no source input
  copyValue((/field))                              -> copy value as-is
  xsi:nil                                          -> set target element to xsi:nil="true"

CONVERSION:
  fixValues((/field))                              -> fixed value lookup table
  valueMapping((/field))                           -> CPI Value Mapping table lookup

STATISTICS (aggregate — NO Groovy needed!):
  sum((/field))                                    -> SUM of all occurrences
  average((/field))                                -> average of all values
  count((/field))                                  -> count of occurrences
  index((/field))                                  -> 0-based index of current
  first((/field))                                  -> first value in queue
  last((/field))                                   -> last value in queue

NODE:
  useOneAsMany((/field))                           -> repeat value for each occurrence
  mapWithDefault((/field), defaultValue)           -> pass value or default if empty
  exists((/field))                                 -> boolean: field has value
  getHeader(NAME)                                  -> get named message header
  getProperty(NAME)                                -> get named integration property
  SplitByValue((/field), delimiter)                -> split into multiple contexts
  removeContexts((/field))                         -> flatten multi-value to list
  collapseContexts((/field))                       -> merge multiple into one
  createIf((/condition))                           -> create element if true
  sort((/field))                                   -> sort values ascending
  sort((/field), descending)                       -> sort values descending
  copyValue((/field))                              -> copy value through

== INTENT RECOGNITION EXAMPLES ==

"uppercase" / "to upper" / "make uppercase"       -> toUpperCase((/fieldName))
"lowercase"                                        -> toLowerCase((/fieldName))
"trim" / "remove whitespace"                       -> trim((/fieldName))
"length" / "character count"                       -> length((/fieldName))
"first N characters"                               -> substring((/fieldName), 0, N)
"extract chars from X to Y"                        -> substring((/fieldName), X, Y)
"combine X and Y with hyphen"                      -> (/X)+- +(/Y)
"join date and time with T"                        -> (/date)+T+(/time)
"replace X with Y"                                 -> replaceAll((/field), X, Y)
"remove dashes / hyphens"                          -> replaceAll((/field), -, )
"split by comma"                                   -> SplitByValue((/field), ,)
"format date YYYYMMDD to YYYY-MM-DD"               -> formatDate((/field), yyyyMMdd, yyyy-MM-dd)
"today's date"                                    -> currentDate()
"add two fields"                                   -> add((/field1), (/field2))
"multiply"                                         -> multiply((/field1), (/field2))
"format as 2 decimal places"                       -> FormatNum((/field), 0.00)
"if field exists"                                  -> exists((/field))
"default value if empty"                           -> mapWithDefault((/field), DEFAULT)
"repeat for each line"                             -> useOneAsMany((/field))
"sort ascending"                                   -> sort((/field))
"direct copy" / "same value"                      -> ""
"sum all quantities"                               -> sum((/path/to/Quantity))
"count items"                                      -> count((/path/to/Item))
"if equals some value"                             -> ifS((/field), someValue, resultIfTrue, resultIfFalse)
"get header"                                       -> getHeader(HEADER_NAME)
"get property"                                     -> getProperty(PROPERTY_NAME)
"1 divided by field" / "inverse"                   -> inv((/field))
"set to nil"                                       -> xsi:nil

== RULES ==

1. Use ACTUAL field names from source fields list -- never write (/field) literally
2. Field references: (/FieldName) -- short name, NOT full XPath
3. Constants go WITHOUT parentheses: T, -, _, EUR, yyyyMMdd, DEFAULT
4. Direct copy -> return exactly: ""
5. If description mentions multiple fields, look them up from available source fields
6. Return ONLY the expression on one line -- no explanation, no markdown
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

# -- Cheat sheet loader -------------------------------------------------------

def _load_cheatsheet() -> str:
    """Load the CPI mapping cheat sheet — used in all AI generation prompts."""
    try:
        cs_path = Path(__file__).parent.parent.parent / "resources" / "cpi_mapping_cheatsheet.md"
        return cs_path.read_text(encoding="utf-8")
    except Exception:
        return ""

_CHEATSHEET = _load_cheatsheet()

# Enhance _DERIVE_SYSTEM with cheat sheet node function reference now that cheatsheet is loaded
if _CHEATSHEET:
    _sec5_start = _CHEATSHEET.find("## 5. ALL NODE FUNCTIONS")
    _sec5_end   = _CHEATSHEET.find("## 6. PATH FORMAT")
    if _sec5_start >= 0 and _sec5_end > _sec5_start:
        _DERIVE_SYSTEM = (
            "You are an SAP CPI Graphical Message Mapping expert.\n\n"
            "REFERENCE — correct fname values (MUST use these exactly):\n"
            + _CHEATSHEET[_sec5_start:_sec5_end]
            + "\nConvert any plain-English functional description into the correct SAP CPI expression."
        )

_XSD_GEN_RULES = """
CRITICAL XSD RULES for SAP CPI compatibility:
1. DO NOT add targetNamespace attribute — causes CPI path resolution errors
2. DO NOT add xmlns:tns or elementFormDefault="qualified" with namespace
3. Root xs:element name must be a simple CamelCase noun (e.g. Order, Product, Material)
4. Use minOccurs="0" on most elements for flexibility
5. Keep nesting max 4 levels deep
6. No type references outside the schema (keep self-contained)
7. Example valid root: <xs:element name="StockReport"><xs:complexType><xs:sequence>...
"""

# -- Generate from Source XSD + Description ----------------------------------

class GenerateFromSourceRequest(BaseModel):
    source_xsd: str
    source_xsd_name: str = "source.xsd"
    description: str
    mapping_name: str = "MM_Mapping"


@router.post("/generate-from-source")
def generate_from_source(req: GenerateFromSourceRequest):
    """
    Given a source XSD and a description of what the target system expects,
    generate: (1) a target XSD, (2) field mappings, (3) an mmap ZIP.
    """
    from services.xsd_parser import smart_extract_paths, leaf_paths
    import json as _json

    src_root, src_paths = smart_extract_paths(req.source_xsd)
    src_leaves = leaf_paths(src_paths)[:40]

    # Step 1: Generate target XSD
    tgt_xsd_prompt = (
        "You are an SAP CPI integration expert. Generate a valid XSD schema for the target system.\n\n"
        f"{_XSD_GEN_RULES}\n\n"
        "CHEAT SHEET REFERENCE:\n" + _CHEATSHEET[:3000] + "\n\n"
        "Source system XSD leaf fields:\n" + "\n".join(src_leaves) + "\n\n"
        "Target system requirement:\n" + req.description + "\n\n"
        "Generate a complete, valid XSD schema for the target system. Rules:\n"
        "- Use xs: namespace prefix\n"
        "- Create a clean, flat structure appropriate for the target\n"
        "- Field names should be clear and descriptive\n"
        "- Include xs:element with appropriate types (xs:string, xs:decimal, xs:dateTime, etc.)\n"
        "- Return ONLY the XSD XML, no explanation, no markdown fences\n"
    )

    tgt_xsd_text = generate("Return only valid XSD XML.", tgt_xsd_prompt, max_tokens=3000)
    if "```" in tgt_xsd_text:
        tgt_xsd_text = tgt_xsd_text.split("```", 1)[-1]
        tgt_xsd_text = tgt_xsd_text.rsplit("```", 1)[0]
        if tgt_xsd_text.startswith("xml\n"):
            tgt_xsd_text = tgt_xsd_text[4:]
    tgt_xsd_text = tgt_xsd_text.strip()

    # Step 2: Parse target XSD
    try:
        tgt_root, tgt_paths = smart_extract_paths(tgt_xsd_text)
    except Exception:
        tgt_root = "Root"
        tgt_paths = []

    # Step 3: Generate mappings
    mapping_prompt = (
        "Generate SAP CPI Graphical Message Mapping field mappings.\n\n"
        "SOURCE XSD fields:\n" + "\n".join(src_paths[:60]) + "\n\n"
        "TARGET XSD fields:\n" + "\n".join(tgt_paths[:60]) + "\n\n"
        "Mapping goal: " + req.description + "\n\n"
        "Use SAP CPI node function expressions where transformation is needed:\n"
        "- toUpperCase((/field)), toLowerCase((/field)), trim((/field))\n"
        "- formatDate((/field), inputFmt, outputFmt)\n"
        "- (/field1)+SEPARATOR+(/field2) for concatenation\n"
        "- replaceAll((/field), search, replacement)\n"
        "- mapWithDefault((/field), defaultValue)\n\n"
        'Return ONLY valid JSON (no markdown):\n'
        '{"field_mappings": [{"source_path": "/S/F", "target_path": "/T/F", "rule": "", "note": ""}]}'
    )

    try:
        raw = generate("Return ONLY valid JSON, no markdown.", mapping_prompt, max_tokens=4000)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = _json.loads(raw)
        fm_list = data.get("field_mappings", [])
    except Exception:
        fm_list = []

    # Convert to mmap format
    from services.sheet_mapper import _parse_rule
    matched = []
    for fm in fm_list:
        src_p = fm.get("source_path", "")
        tgt_p = fm.get("target_path", "")
        rule  = fm.get("rule", "")
        if not tgt_p:
            continue
        if rule:
            try:
                parsed = _parse_rule(rule, src_paths)
                if parsed:
                    func_name, parts = parsed
                    matched.append({"target_path": tgt_p, "func": func_name, "parts": parts, "note": fm.get("note", "")})
                    continue
            except Exception:
                pass
        if src_p:
            matched.append({"source_path": src_p, "target_path": tgt_p, "note": fm.get("note", "")})

    safe_name    = req.mapping_name.replace(" ", "_") or "MM_Mapping"
    tgt_xsd_name = "target.xsd"

    mmap_xml  = build_mmap_xml(safe_name, req.source_xsd_name, src_root or "Source",
                                tgt_xsd_name, tgt_root or "Target", matched)
    zip_bytes = build_mmap_zip(safe_name, mmap_xml, req.source_xsd, tgt_xsd_text,
                                req.source_xsd_name, tgt_xsd_name)

    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.zip"',
            "X-Generated-Target-XSD": tgt_xsd_text[:500],
            "X-Mapping-Count": str(len(matched)),
            "Access-Control-Expose-Headers": "X-Generated-Target-XSD,X-Mapping-Count",
        },
    )


# -- Generate from Idea Only -------------------------------------------------

class GenerateFromIdeaRequest(BaseModel):
    idea: str
    mapping_name: str = "MM_Mapping"


@router.post("/generate-from-idea")
def generate_from_idea(req: GenerateFromIdeaRequest):
    """
    Given only an idea/description, intelligently generate source XSD, target XSD,
    field mappings (with UDFs for aggregations) and mmap ZIP.

    Smart features:
    - Detects SAP standard entities (SalesOrder, Material, PurchaseOrder…) and uses
      the bundled catalog XSDs instead of generating new ones
    - Detects aggregate operations (sum, total, count) and generates proper Groovy UDFs
    """
    import json as _json
    from services.xsd_parser import smart_extract_paths

    idea_lower = req.idea.lower()

    # ── 1. Detect catalog XSD matches ─────────────────────────────────────────
    _ENTITY_MAP = {
        ("sales order", "salesorder", "vbak", "salesdocument", "a_salesorder"):
            ("A_SalesOrder.xsd", "SalesOrder"),
        ("purchase order", "purchaseorder", "ekko", "purchdoc", "a_purchaseorder"):
            ("A_PurchaseOrder.xsd", "PurchaseOrder"),
        ("material", "product", "matnr", "matmas", "a_product"):
            ("A_Product.xsd", "Product"),
        ("business partner", "customer", "debmas", "a_businesspartner"):
            ("A_BusinessPartner.xsd", "BusinessPartner"),
        ("supplier", "vendor", "cremas", "a_supplier"):
            ("A_Supplier.xsd", "Supplier"),
        ("invoice", "billing", "invoic", "a_supplierinvoice"):
            ("A_SupplierInvoice.xsd", "SupplierInvoice"),
        ("delivery", "desadv", "a_outbounddelivery"):
            ("A_OutboundDelivery.xsd", "OutboundDelivery"),
        ("goods movement", "wmmbxy", "material document", "a_materialdocument"):
            ("A_MaterialDocument.xsd", "MaterialDocument"),
        ("production order", "loipro"):
            ("A_ProductionOrder.xsd", "ProductionOrder"),
        ("cost center", "a_costcenter"):
            ("A_CostCenter.xsd", "CostCenter"),
    }

    def _detect_xsd(text: str) -> tuple[str, str] | None:
        for keywords, (filename, root) in _ENTITY_MAP.items():
            if any(k in text for k in keywords):
                xsd_path = _RESOURCES / filename
                if xsd_path.exists():
                    return xsd_path.read_text(encoding="utf-8"), filename
        return None

    src_detected = _detect_xsd(idea_lower)
    src_xsd_text = src_detected[0] if src_detected else ""
    src_xsd_name = src_detected[1] if src_detected else "source.xsd"

    # ── 2. Detect aggregate operations ────────────────────────────────────────
    _AGGREGATE_KEYWORDS = {"sum", "total", "aggregate", "count", "average", "summ", "add all",
                           "accumulate", "sumof", "sum of", "total of"}
    needs_aggregate = any(kw in idea_lower for kw in _AGGREGATE_KEYWORDS)

    # ── 3. Generate XSDs (only those not found in catalog) ────────────────────
    if src_xsd_text:
        # Source found in catalog — only need to generate target
        src_root, src_paths = smart_extract_paths(src_xsd_text)
        src_leaves = [p for p in src_paths if not any(p.rsplit("/", 1)[-1] == seg
                      for seg in [q.split("/")[-1] for q in src_paths if q != p and p in q])][:50]

        tgt_prompt = (
            "Generate a target XSD for this integration goal:\n\n"
            f'"{req.idea}"\n\n'
            f"{_XSD_GEN_RULES}\n\n"
            "Source system fields (for reference):\n" + "\n".join(src_leaves[:30]) + "\n\n"
            "Return ONLY valid XML (the complete XSD, no markdown, no targetNamespace)."
        )
        tgt_xsd_text = generate("Return ONLY valid XSD XML.", tgt_prompt, max_tokens=3000).strip()
        if tgt_xsd_text.startswith("```"):
            tgt_xsd_text = tgt_xsd_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    else:
        # Neither found — generate both
        both_prompt = (
            "You are an SAP CPI integration architect. Integration requirement:\n\n"
            f'"{req.idea}"\n\n'
            f"{_XSD_GEN_RULES}\n\n"
            "Return ONLY valid JSON (no markdown):\n"
            '{"source_xsd": "<?xml version=\\"1.0\\"?>...", "target_xsd": "<?xml version=\\"1.0\\"?>...", '
            '"source_root": "Name", "target_root": "Name"}\n\n'
            "CRITICAL: No targetNamespace. Simple xs:element root.\n"
            + _CHEATSHEET[_CHEATSHEET.find("## 2. XSD FORMAT"):_CHEATSHEET.find("## 3.")]
        )
        raw = generate("Return ONLY valid JSON.", both_prompt, max_tokens=6000).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = _json.loads(raw)
        src_xsd_text = data.get("source_xsd", "")
        tgt_xsd_text = data.get("target_xsd", "")

    try:
        src_root, src_paths = smart_extract_paths(src_xsd_text)
    except Exception:
        src_root, src_paths = "Source", []
    try:
        tgt_root, tgt_paths = smart_extract_paths(tgt_xsd_text)
    except Exception:
        tgt_root, tgt_paths = "Target", []

    # ── 4. Generate field mappings (with aggregate awareness) ─────────────────
    aggregate_note = ""
    if needs_aggregate:
        aggregate_note = """
AGGREGATION DETECTED: The user wants SUM/TOTAL/COUNT of repeating values.
SAP CPI has BUILT-IN Statistics functions for this — NO Groovy UDF needed!

For sum of a repeating field (e.g. TotalQuantity = sum of all Item/Quantity):
  - rule: "sum((/SalesOrder/Items/Item/Quantity))"  ← use the repeating source path
  - The sum() function takes ALL occurrences and returns one total value
  - NEVER use GROOVY: for sum/average/count — use the Statistics functions

Other Statistics functions:
  - sum((/field))     → total of all values
  - average((/field)) → average
  - count((/field))   → how many occurrences
  - first((/field))   → first value only
  - last((/field))    → last value only
"""

    map_prompt = (
        "Generate SAP CPI field mappings for: " + req.idea + "\n\n"
        + aggregate_note
        + "SOURCE fields available:\n" + "\n".join(src_paths[:60]) + "\n\n"
        "TARGET fields to map:\n" + "\n".join(tgt_paths[:60]) + "\n\n"
        "Rules:\n"
        "1. Map EVERY target field to the best source field\n"
        "2. For direct copy: rule = \"\"\n"
        "3. For transformations: use SAP CPI expressions (toUpperCase, formatDate, etc.)\n"
        "4. For SUM/AGGREGATE: rule = \"GROOVY:sumAll\", source_path = repeating field path\n"
        "5. Map container/parent elements too (e.g. /SalesOrder → /OrderSummary)\n"
        + _CHEATSHEET[_CHEATSHEET.find("## 7. COMMON"):_CHEATSHEET.find("## 8.")] + "\n"
        'Return ONLY JSON: {"field_mappings": [{"source_path": "...", "target_path": "...", "rule": "", "note": "..."}]}'
    )

    raw2 = generate("Return ONLY valid JSON.", map_prompt, max_tokens=4000).strip()
    if raw2.startswith("```"):
        raw2 = raw2.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        fm_list = _json.loads(raw2).get("field_mappings", [])
    except Exception:
        fm_list = []

    # ── 5. Build matched list and UDF registry ────────────────────────────────
    from services.sheet_mapper import _parse_rule

    udfs: list[dict] = []  # collect UDFs to inject into mmap

    matched = []
    udf_needed: set[str] = set()

    for fm in fm_list:
        src_p = fm.get("source_path", "")
        tgt_p = fm.get("target_path", "")
        rule  = fm.get("rule", "")
        if not tgt_p:
            continue

        # Handle Groovy UDF rules (aggregate/sum)
        if rule and rule.startswith("GROOVY:"):
            udf_name = rule[7:].strip()
            udf_needed.add(udf_name)
            matched.append({
                "target_path": tgt_p,
                "func": udf_name,
                "fns": "usernamespace",        # UDF namespace
                "parts": [{"type": "src", "path": src_p}] if src_p else [],
                "note": fm.get("note", f"Groovy UDF: {udf_name}"),
            })
            continue

        if rule:
            try:
                parsed = _parse_rule(rule, src_paths)
                if parsed:
                    func_name, parts = parsed
                    matched.append({"target_path": tgt_p, "func": func_name, "parts": parts,
                                    "note": fm.get("note", "")})
                    continue
            except Exception:
                pass
        if src_p:
            matched.append({"source_path": src_p, "target_path": tgt_p, "note": fm.get("note", "")})

    # Collect UDF definitions to embed in the mmap
    udfs_to_embed = []
    if "sumAll" in udf_needed:
        udfs_to_embed.append(_GROOVY_SUM_UDF)

    safe_name = req.mapping_name.replace(" ", "_") or "MM_Mapping"
    mmap_xml  = build_mmap_xml(safe_name, src_xsd_name, src_root or "Source",
                                "target.xsd", tgt_root or "Target", matched,
                                udfs=udfs_to_embed)
    zip_bytes = build_mmap_zip(safe_name, mmap_xml, src_xsd_text, tgt_xsd_text,
                                src_xsd_name, "target.xsd")

    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.zip"',
            "X-Mapping-Count": str(len(matched)),
            "X-Source-XSD": src_xsd_name,
            "Access-Control-Expose-Headers": "X-Mapping-Count,X-Source-XSD",
        },
    )
