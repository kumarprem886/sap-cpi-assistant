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
from services.sheet_mapper import sheet_to_field_mappings
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


