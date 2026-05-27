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
    file: UploadFile = File(...),
    author: str = Form(""),
    project_team: str = Form(""),
    developer: str = Form(""),
):
    file_bytes = await file.read()

    # ── Step 1: extract text ────────────────────────────────────────────────
    sections  = parse_docx_to_text(file_bytes)
    fd_summary = sections_to_summary(sections)

    # ── Step 2: analyse any flow diagram images inside the FD ──────────────
    images      = extract_images_from_docx(file_bytes)
    image_context = ""
    flow_analysis: dict = {}

    for img in images:                         # largest image first
        result = analyze_flow_image(img["bytes"], img["content_type"])
        if result.get("is_flow_diagram"):
            flow_analysis = result
            chain       = result.get("chain", "")
            steps       = result.get("cpi_steps", [])
            targets     = result.get("multiple_targets", [])
            description = result.get("description", "")
            protocols   = result.get("protocols", {})

            image_context = f"""
FLOW DIAGRAM ANALYSIS (extracted from the embedded image in the FD):
- System chain: {chain}
- CPI processing steps: {", ".join(steps) if steps else "not visible"}
- Multiple targets: {", ".join(targets) if targets else "none"}
- Protocol details: {protocols}
- Description: {description}

Use this flow analysis as the PRIMARY source for:
  process_flow, integration_logic, source_app_name, target_app_name,
  source_protocol, target_protocol, cpi_steps.
Do NOT override this with guesses — trust the image analysis.
"""
            break   # stop after the first valid flow diagram

    # ── Step 3: generate TD JSON via AI ────────────────────────────────────
    prompt = f"""You are an SAP CPI Technical Design (TD) document generator.
Analyse the document below and extract every detail needed to fill a complete TD.
{image_context}
DOCUMENT CONTENT:
{fd_summary[:5000]}

Return ONLY a valid JSON object (no markdown, no extra text) with these exact keys.
Use empty string "" for unknown values — never omit a key.

Keys and expected format:
  interface_id          — short ID like "I_001_MaterialMasterOut"
  interface_name        — full interface name
  author                — author name
  project_team          — project team name
  process_owner         — process owner name
  organisation          — organisation name
  middleware            — "CPI" or "PO"
  business_owner        — business owner
  business_criticality  — "Highly critical" | "Critical" | "Non-critical"
  source_system         — source system name
  target_system         — target system name(s)
  data_flow             — "Unidirectional" | "Bidirectional" | "Multiple"
  data_objects          — list of strings (data objects being transferred)
  planned_test_date     — planned test start date or "TBD"
  planned_golive_date   — planned go-live date or "TBD"
  business_process_description — description of the business process
  assumptions           — list of strings (one assumption per item)
  source_app_name       — source application name
  source_use            — how the source system is used
  source_type           — "SAP System" | "Third-Party System" | "Other"
  source_protocol       — communication protocol (HTTPS, IDoc, RFC, AS2, SFTP, etc.)
  target_app_name       — target application name
  target_use            — how the target system is used
  target_type           — "SAP System" | "Third-Party System" | "Other"
  target_protocol       — communication protocol
  message_content       — what data is in the message
  message_sample        — sample file description
  message_frequency     — how often messages are sent
  message_size          — estimated message size
  has_dependencies      — true | false (boolean)
  dependencies_detail   — dependency details or "N/A"
  sensitive_data        — true | false (boolean)
  transport_encryption  — "TLS 1.2 or higher" | "N/A"
  message_encryption    — "PGP" | "N/A"
  auth_receiving        — authorisation for receiving backend
  auth_integration      — authorisation for integration solution
  complexity            — "High" | "Medium" | "Low"
  developer             — integration developer name
  integration_logic     — describe the integration flow step by step
  flowchart             — short description for flowchart caption
  package_name          — CPI package name
  artifact_name         — iFlow artifact name
  mode                  — "Asynchronous" | "Synchronous" | "Asynchronous via Event Mesh"
  iflow_description     — description of what the iFlow does
  mapping_name          — mapping artifact name
  mapping_namespace     — mapping namespace / artifact ID
  mapping_type          — "Message Mapping" | "Groovy" | "XSLT" | "None"
  mapping_spec          — mapping specification details
  mapping_objects       — list of [name, type, namespace, specification] (can be empty list)
  sender_monitoring     — sender monitoring solution
  sender_contact        — sender contact information
  cpi_monitoring        — CPI monitoring solution
  cpi_alert             — CPI alert / additional monitoring info
  cloud_alm             — Cloud ALM property info
  cpi_contact           — CPI contact information
  receiver_monitoring   — receiver monitoring solution
  receiver_contact      — receiver contact information
  processing_description — list of strings describing processing steps
  processing_type_detail — list of strings describing processing type
  error_handling        — error handling description
  master_data           — master data entries description
  security_considerations — security considerations
  dev_considerations    — list of [area, details] pairs or leave as []
  test_system           — test system name
  test_client           — test client/environment
  test_tool             — test tool used
  technical_test_conditions — list of strings (test conditions)
  unit_test_description — how to perform a unit test
  unit_test_materials   — test materials/files
  unit_test_scenarios   — list of strings (test scenarios and results)
  enhanced_fields       — list of {{segment, field, description, qualifier, logic}} dicts
  issues                — list of {{issue, resolution}} dicts
"""
    data = _ask_for_json(prompt)

    # ── Step 4: override flowchart fields with image analysis if available ──
    if flow_analysis.get("is_flow_diagram"):
        if flow_analysis.get("chain"):
            data["process_flow"] = flow_analysis["chain"]
        if flow_analysis.get("cpi_steps"):
            # Inject into integration_logic so flowchart_builder detects them
            steps_str = ", ".join(flow_analysis["cpi_steps"])
            data["integration_logic"] = (
                f"{steps_str}. " + data.get("integration_logic", "")
            )
        if flow_analysis.get("multiple_targets"):
            data["target_app_name"] = ", ".join(flow_analysis["multiple_targets"])

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
    prompt = f"""You are an SAP CPI Technical Design document generator.
Analyse the following SAP CPI iFlow XML and generate a complete TD document.
Extract adapter types, message mappings, routing logic, error handling, monitoring, etc.

iFlow XML:
{req.iflow_xml[:5000]}

Additional Context: {req.extra_context or "None"}

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
mapping_objects (list of [name, type, namespace, spec]),
sender_monitoring, sender_contact, cpi_monitoring, cpi_alert, cloud_alm, cpi_contact,
receiver_monitoring, receiver_contact,
processing_description (list), processing_type_detail (list),
error_handling, master_data, security_considerations,
dev_considerations (list of [area, details]),
test_system, test_client, test_tool,
technical_test_conditions (list), unit_test_description, unit_test_materials,
unit_test_scenarios (list), enhanced_fields (list of objects with segment/field/description/qualifier/logic),
issues (list of objects with issue/resolution)
"""
    data = _ask_for_json(prompt)
    data["author"] = req.author or data.get("author", "")
    data["project_team"] = req.project_team or data.get("project_team", "")
    data["developer"] = req.developer or data.get("developer", "")
    content = build_td(data)
    iface_id = data.get("interface_id", "TD")
    filename = f"{iface_id}_TD.docx"
    return _docx_response(content, filename)
