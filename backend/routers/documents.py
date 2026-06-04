import json
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.claude_service import generate, analyze_flow_image
from services.doc_builder import build_fd, build_td
from services.doc_parser import parse_docx_to_text, sections_to_summary, extract_images_from_docx
from io import BytesIO

router = APIRouter(prefix="/api/docs", tags=["documents"])

# ── Shared AI helper ─────────────────────────────────────────────────────────

def _ask_for_json(prompt: str) -> dict:
    raw = generate("Return ONLY valid JSON with no markdown fences or extra text.", prompt)
    # Strip possible markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


def _docx_response(content: bytes, filename: str):
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── FD Generator ─────────────────────────────────────────────────────────────

class FDRequest(BaseModel):
    interface_id: str
    interface_name: str
    from_system: str
    to_system: str
    transformation_system: str = "SAP CPI"
    processing_type: str = "IDOC"
    idoc_message_type: str = ""
    idoc_basic_type: str = ""
    business_context: str = ""
    key_fields: str = ""
    author: str = ""


@router.post("/generate-fd")
def generate_fd(req: FDRequest):
    prompt = f"""Generate a complete SAP CPI Functional Design (FD) document for the following interface.
Return a JSON object that fills every field listed below.

Interface ID: {req.interface_id}
Interface Name: {req.interface_name}
From System: {req.from_system}
To System: {req.to_system}
Transformation System: {req.transformation_system}
Processing Type: {req.processing_type}
IDOC Message Type: {req.idoc_message_type or 'N/A'}
IDOC Basic Type: {req.idoc_basic_type or 'N/A'}
Business Context: {req.business_context}
Key Data Fields: {req.key_fields}

Return JSON with these exact keys (all strings unless noted):
interface_id, interface_name, author, overview, to_be_process, object_overview,
business_details, from_system, transformation_system, to_system, processing_type,
functional_description, assumptions, dependencies, security, fiori_impact,
functional_spec, process_flow, transfer_method, target_data_layout, source_data_layout,
field_mappings (list of [source_field, source_path, target_field, transformation]),
post_activities, monitoring, authorization, error_handling, performance,
business_test_conditions (list of strings), technical_test_conditions (list of strings),
issues (list of [issue, status, owner])
"""
    data = _ask_for_json(prompt)
    data["interface_id"] = req.interface_id
    data["interface_name"] = req.interface_name
    data["author"] = req.author or data.get("author", "")
    content = build_fd(data)
    filename = f"{req.interface_id}_FD.docx"
    return _docx_response(content, filename)


# ── FD to TD ─────────────────────────────────────────────────────────────────

@router.post("/fd-to-td")
async def fd_to_td(
    file:         UploadFile = File(...),
    author:       str = Form(""),
    project_team: str = Form(""),
    developer:    str = Form(""),
):
    file_bytes = await file.read()

    # ── Step 1: Extract ALL text from FD (sections + tables) ─────────────────
    sections   = parse_docx_to_text(file_bytes)
    fd_summary = sections_to_summary(sections)
    # Use up to 12 000 chars — enough for most FDs without hitting token limits
    fd_text = fd_summary[:12000]

    # ── Step 2: Try image analysis (vision AI) — silently skip if not supported
    image_context = ""
    flow_analysis: dict = {}
    images = extract_images_from_docx(file_bytes)
    for img in images:
        try:
            result = analyze_flow_image(img["bytes"], img["content_type"])
            if result.get("is_flow_diagram"):
                flow_analysis = result
                chain    = result.get("chain", "")
                steps    = result.get("cpi_steps", [])
                targets  = result.get("multiple_targets", [])
                protocols = result.get("protocols", {})
                image_context = f"""
FLOW DIAGRAM IMAGE FOUND IN THE FD:
- System chain: {chain}
- CPI processing steps: {", ".join(steps) if steps else "not detected"}
- Multiple targets: {", ".join(targets) if targets else "none"}
- Protocols: {protocols}
Use this as the PRIMARY source for source_app_name, target_app_name,
source_protocol, target_protocol, integration_logic.
"""
                break
        except Exception:
            pass   # vision not supported by current AI provider — skip silently

    # ── Step 3: AI extracts structured facts from the FD text ─────────────────
    prompt = f"""You are an SAP CPI Technical Design document generator.
Read this Functional Design (FD) document carefully and extract ONLY information
that is explicitly stated. Do NOT invent or hallucinate values — use "" for anything
not mentioned in the document.
{image_context}
FD DOCUMENT TEXT:
{fd_text}

Return ONLY a valid JSON object with these keys (use "" or [] for unknowns):
{{
  "interface_id": "short ID e.g. I_001_MaterialOut",
  "interface_name": "full interface name",
  "author": "",
  "project_team": "",
  "process_owner": "",
  "organisation": "",
  "middleware": "CPI",
  "business_owner": "",
  "business_criticality": "Critical",
  "source_system": "source system name from FD",
  "target_system": "target system name from FD",
  "data_flow": "Unidirectional",
  "data_objects": ["list of data objects"],
  "planned_test_date": "TBD",
  "planned_golive_date": "TBD",
  "business_process_description": "description from FD",
  "assumptions": ["list of assumptions from FD"],
  "source_app_name": "sender system name",
  "source_use": "how source is used",
  "source_type": "SAP System",
  "source_protocol": "HTTPS or IDoc or RFC etc",
  "target_app_name": "receiver system name(s) — comma-separated if multiple",
  "target_use": "how target is used",
  "target_type": "Third-Party System",
  "target_protocol": "HTTP or SFTP or SOAP etc",
  "message_content": "what data fields are transferred",
  "message_sample": "sample file / payload description",
  "message_frequency": "how often messages are sent",
  "message_size": "estimated payload size",
  "has_dependencies": false,
  "dependencies_detail": "N/A",
  "sensitive_data": false,
  "transport_encryption": "TLS 1.2 or higher",
  "message_encryption": "N/A",
  "auth_receiving": "auth details for receiving backend",
  "auth_integration": "CPI auth details",
  "complexity": "Medium",
  "developer": "",
  "integration_logic": "step-by-step description of what happens in CPI: e.g. 1.Receive IDoc via HTTPS 2.Transform with Groovy 3.Route to REST API",
  "flowchart": "one-line caption for the diagram",
  "package_name": "CPI package name from FD",
  "artifact_name": "iFlow artifact name from FD",
  "mode": "Asynchronous",
  "iflow_description": "what the iFlow does",
  "mapping_name": "",
  "mapping_namespace": "",
  "mapping_type": "Message Mapping",
  "mapping_spec": "mapping specification details",
  "mapping_objects": [],
  "sender_monitoring": "SAP Application Interface Framework or similar",
  "sender_contact": "sender team contact",
  "cpi_monitoring": "SAP Integration Suite Message Monitoring",
  "cpi_alert": "alert configuration details",
  "cloud_alm": "Cloud ALM integration property",
  "cpi_contact": "CPI team contact",
  "receiver_monitoring": "receiver monitoring solution",
  "receiver_contact": "receiver team contact",
  "processing_description": ["step 1 description", "step 2 description"],
  "processing_type_detail": ["Groovy Script", "Message Mapping"],
  "error_handling": "exception subprocess description",
  "master_data": "N/A",
  "security_considerations": "TLS, role-based auth",
  "dev_considerations": [["area", "detail"]],
  "test_system": "test system name",
  "test_client": "DEV / QA",
  "test_tool": "Postman / SOAP UI",
  "technical_test_conditions": ["condition 1", "condition 2"],
  "unit_test_description": "how to unit test",
  "unit_test_materials": "test payload files",
  "unit_test_scenarios": ["scenario 1 — expected result"],
  "enhanced_fields": [],
  "issues": []
}}"""

    data = _ask_for_json(prompt)

    # ── Step 4: Fill diagram fields from image analysis if available ──────────
    if flow_analysis.get("is_flow_diagram"):
        if flow_analysis.get("chain") and not data.get("source_app_name"):
            data["process_flow"] = flow_analysis["chain"]
        if flow_analysis.get("cpi_steps"):
            logic = ", ".join(flow_analysis["cpi_steps"])
            existing = data.get("integration_logic", "")
            data["integration_logic"] = f"{logic}. {existing}".strip(". ")
        if flow_analysis.get("multiple_targets") and not data.get("target_app_name"):
            data["target_app_name"] = ", ".join(flow_analysis["multiple_targets"])

    # ── Step 5: Apply user-supplied overrides ─────────────────────────────────
    data["author"]       = author       or data.get("author", "")
    data["project_team"] = project_team or data.get("project_team", "")
    data["developer"]    = developer    or data.get("developer", "")

    content  = build_td(data)
    iface_id = data.get("interface_id", "TD")
    filename = f"{iface_id}_TD.docx"
    return _docx_response(content, filename)


# ── iFlow to TD ───────────────────────────────────────────────────────────────

class IFlowTDRequest(BaseModel):
    iflow_xml: str
    author: str = ""
    project_team: str = ""
    developer: str = ""
    extra_context: str = ""


@router.post("/iflow-to-td")
def iflow_to_td(req: IFlowTDRequest):
    import re as _re

    # ── Step 1: Extract key facts from iFlow XML to help the AI ─────────────
    xml = req.iflow_xml

    # Pull participant names (sender + receivers)
    participants = _re.findall(r'<bpmn2:participant\b[^>]*\bname="([^"]+)"', xml)
    adapter_components = _re.findall(r'<key>ComponentType</key><value>([^<]+)</value>', xml)
    activity_types = _re.findall(r'<key>activityType</key><value>([^<]+)</value>', xml)
    step_names = _re.findall(r'<bpmn2:callActivity\b[^>]*\bname="([^"]+)"', xml)
    svc_names  = _re.findall(r'<bpmn2:serviceTask\b[^>]*\bname="([^"]+)"', xml)
    gw_names   = _re.findall(r'<bpmn2:exclusiveGateway\b[^>]*\bname="([^"]+)"', xml)
    # Message flows direction
    msg_flows = _re.findall(r'<bpmn2:messageFlow\b[^>]*\bname="([^"]+)"', xml)
    # iFlow name
    iflow_name_m = _re.search(r'<bpmn2:process\b[^>]*\bname="([^"]+)"', xml)
    iflow_name = iflow_name_m.group(1) if iflow_name_m else "Unknown"
    # Documentation block
    doc_m = _re.search(r'<bpmn2:documentation[^>]*>([^<]+)</bpmn2:documentation>', xml)
    iflow_desc = doc_m.group(1).strip() if doc_m else ""

    # URL / credential references
    urls = _re.findall(r'<key>(?:address|httpAddressWithoutQuery|urlPath)</key><value>([^<]+)</value>', xml)
    cred_aliases = _re.findall(r'<key>(?:credentialName|credential_name|alias)</key><value>([^<]+)</value>', xml)

    extracted = f"""
iFlow Name: {iflow_name}
Description: {iflow_desc}
Participants: {', '.join(participants)}
Adapter types used: {', '.join(sorted(set(adapter_components)))}
Processing steps: {', '.join(step_names + svc_names + gw_names)}
Message flows: {', '.join(msg_flows)}
Endpoint URLs/paths ({{}} = externalized): {', '.join(urls[:5])}
Credential aliases: {', '.join(cred_aliases[:5])}
Extra context: {req.extra_context or 'None'}
""".strip()

    # Send first 3000 chars of raw XML for structure details
    xml_sample = xml[:3000]

    prompt = f"""You are an SAP CPI Technical Design document generator.
Analyse this SAP CPI iFlow and generate a complete TD document.

KEY FACTS EXTRACTED FROM IFLOW:
{extracted}

RAW XML SAMPLE (first 3000 chars for structure reference):
{xml_sample}

Return ONLY valid JSON (no markdown) with these exact keys (use "" for unknowns):
interface_id, interface_name, author, project_team, process_owner, organisation,
middleware, business_owner, business_criticality, source_system, target_system,
data_flow, data_objects (list), planned_test_date, planned_golive_date,
business_process_description, assumptions (list),
source_app_name, source_use, source_type, source_protocol,
target_app_name, target_use, target_type, target_protocol,
message_content, message_sample, message_frequency, message_size,
has_dependencies (bool), dependencies_detail, sensitive_data (bool),
transport_encryption, message_encryption, auth_receiving, auth_integration,
complexity, developer, integration_logic, flowchart,
package_name, artifact_name, mode, iflow_description,
mapping_name, mapping_namespace, mapping_type, mapping_spec,
mapping_objects (list), sender_monitoring, sender_contact,
cpi_monitoring, cpi_alert, cloud_alm, cpi_contact,
receiver_monitoring, receiver_contact,
processing_description (list), processing_type_detail (list),
error_handling, master_data, security_considerations,
dev_considerations (list of [area, details]),
test_system, test_client, test_tool,
technical_test_conditions (list), unit_test_description, unit_test_materials,
unit_test_scenarios (list),
enhanced_fields (list of objects with segment/field/description/qualifier/logic),
issues (list of objects with issue/resolution)

IMPORTANT for diagram fields:
- source_app_name: the SENDER system name (e.g. "S4 HANA", "S/4HANA")
- target_app_name: ALL receiver system names comma-separated (e.g. "Manogna SFTP, Mrudula HTTP")
- source_protocol: protocol from sender (HTTPS, IDoc, RFC, etc.)
- target_protocol: primary receiver protocol (SFTP, HTTP, SOAP, etc.)
- integration_logic: describe the steps in order (Content Modifier, Groovy Script, Router, etc.)
"""
    data = _ask_for_json(prompt)
    data["author"] = req.author or data.get("author", "")
    data["project_team"] = req.project_team or data.get("project_team", "")
    data["developer"] = req.developer or data.get("developer", "")

    # ── Ensure diagram fields are populated even if AI missed them ───────────
    if not data.get("source_app_name") and participants:
        data["source_app_name"] = participants[0]
    if not data.get("target_app_name") and len(participants) > 2:
        data["target_app_name"] = ", ".join(participants[1:-1])  # skip Integration Process
    if not data.get("interface_name"):
        data["interface_name"] = iflow_name
    if not data.get("integration_logic") and (step_names or activity_types):
        data["integration_logic"] = "Steps: " + ", ".join(
            ([s for s in step_names[:6]] + [a for a in activity_types[:4]])
        )

    content = build_td(data)
    iface_id = data.get("interface_id", "TD")
    filename = f"{iface_id}_TD.docx"
    return _docx_response(content, filename)


# ── TD + iFlow → Enhanced TD ──────────────────────────────────────────────────

@router.post("/update-td")
async def update_td(
    td_file:   UploadFile = File(...),
    iflow_zip: UploadFile = File(...),
    author:    str = Form(""),
):
    """
    Update an existing TD document with iFlow ZIP data — ZERO AI.
    - Copies Appendix data to main body sections
    - Fills iFlow name, mmap name, description from actual ZIP
    - Adds iFlow design steps, diagram
    """
    from services.td_updater import update_td_with_iflow
    td_bytes    = await td_file.read()
    iflow_bytes = await iflow_zip.read()
    result   = update_td_with_iflow(td_bytes, iflow_bytes, author=author)
    base     = (td_file.filename or "TD").replace(".docx", "")
    filename = f"{base}_Updated.docx"
    return _docx_response(result, filename)


@router.post("/mapping-excel")
async def mapping_excel(
    iflow_zip: UploadFile = File(...),
):
    """Generate a mapping specification Excel file from an iFlow ZIP."""
    from services.mapping_excel import generate_mapping_excel
    iflow_bytes = await iflow_zip.read()
    result = generate_mapping_excel(iflow_bytes)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="No message mapping (.mmap) found in iFlow ZIP")
    xlsx_bytes, filename = result
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/iflow-to-td-noai")
async def iflow_to_td_noai(
    iflow_zip:    UploadFile = File(...),
    author:       str = Form(""),
    project_team: str = Form(""),
):
    """
    Generate a complete TD document from an iFlow ZIP — ZERO AI.
    Technical sections are 100% accurate (from iFlow XML).
    Business sections have TBD placeholders for manual completion.
    """
    from services.td_enhancer import build_td_from_iflow
    iflow_bytes = await iflow_zip.read()
    content  = build_td_from_iflow(iflow_bytes, author=author, project_team=project_team)
    filename = (iflow_zip.filename or "iFlow").replace(".zip", "") + "_TD.docx"
    return _docx_response(content, filename)


@router.post("/enhance-td")
async def enhance_td(
    td_file:   UploadFile = File(...),
    iflow_zip: UploadFile = File(...),
):
    """
    Append a Developer Implementation Guide section to an existing TD document.
    Does NOT modify existing content — only appends a new section.
    """
    from services.td_enhancer import enhance_td_with_iflow

    td_bytes    = await td_file.read()
    iflow_bytes = await iflow_zip.read()

    enhanced = enhance_td_with_iflow(td_bytes, iflow_bytes)

    # Derive output filename from TD file
    base = td_file.filename.replace('.docx', '') if td_file.filename else 'TD'
    filename = f"{base}_with_DevGuide.docx"

    return _docx_response(enhanced, filename)
