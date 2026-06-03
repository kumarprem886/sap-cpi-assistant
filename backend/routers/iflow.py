import re
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
from typing import Optional, List
from services.claude_service import generate, analyze_flow_image, MAX_GENERATION_TOKENS
from services.iflow_packager import build_iflow_zip
from services.doc_parser import parse_docx_to_text, sections_to_summary, extract_images_from_docx

router = APIRouter(prefix="/api/iflow", tags=["iflow"])

# ─────────────────────────────────────────────────────────────────────────────
# Standard Groovy script templates (deterministic — no AI needed)
# ─────────────────────────────────────────────────────────────────────────────
SET_PROPERTIES_GROOVY = """\
import com.sap.gateway.ip.core.customdev.util.Message
import java.text.SimpleDateFormat

def Message processData(Message msg) {
    def props = msg.getProperties()

    // Set unique message ID
    def msgId = "FLOW-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12).toUpperCase()
    msg.setProperty("msgId", msgId)

    // Processing timestamp (UTC)
    def sdf = new SimpleDateFormat("yyyyMMddHHmmssSSS")
    sdf.setTimeZone(TimeZone.getTimeZone("UTC"))
    msg.setProperty("processingTimestamp", sdf.format(new Date()))

    // Optional payload logging
    def enableLog = props.get("ENABLE_PAYLOAD_LOGGING") ?: "FALSE"
    if (enableLog.toUpperCase() == "TRUE") {
        def body   = msg.getBody(String)
        def msgLog = messageLogFactory.getMessageLog(msg)
        if (msgLog != null) {
            msgLog.addAttachmentAsString("Payload", body, "application/xml")
        }
    }

    return msg
}
"""

HANDLE_ERROR_GROOVY = """\
import com.sap.gateway.ip.core.customdev.util.Message

def Message processData(Message msg) {
    def exception = msg.getProperty("CamelExceptionCaught")
    def errorMsg  = exception ? exception.getMessage() : "Unknown error"
    def msgId     = msg.getProperty("msgId") ?: "UNKNOWN"

    def msgLog = messageLogFactory.getMessageLog(msg)
    if (msgLog != null) {
        msgLog.addAttachmentAsString("ErrorDetails",
            "MessageId: ${msgId}\\nError: ${errorMsg}", "text/plain")
    }

    throw new Exception("Integration failed [${msgId}]: ${errorMsg}")
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Load condensed cheatsheet — only critical rules + confirmed versions.
# The FULL cheatsheet (62K) is kept on disk for reference but NOT injected
# into every prompt — it would exceed Groq's 12K TPM free-tier limit.
# ─────────────────────────────────────────────────────────────────────────────
def _load_iflow_cheatsheet() -> str:
    """Load full iFlow cheatsheet (used for detailed lookups, not injected into prompt)."""
    try:
        cs_path = Path(__file__).parent.parent / "resources" / "iflow_cheatsheet.md"
        return cs_path.read_text(encoding="utf-8")
    except Exception:
        return ""

def _condensed_cheatsheet() -> str:
    """
    Extract only the minimum-critical sections from the cheatsheet.
    Target: < 3,000 tokens so total IFLOW_SYSTEM fits within Groq free-tier 12K TPM.
    Includes: Critical Rules + Confirmed Versions table + ZIP structure + BPMN rules.
    Skips: Full adapter property sets, full palette step formats (too verbose).
    """
    full = _load_iflow_cheatsheet()
    if not full:
        return ""

    # ── Take only the CRITICAL RULES section (first big block) ──────────────
    # Stop before adapter details start
    stop_markers = [
        "## COMPLETE ADAPTER PROPERTY SETS",
        "## COMPLETE PALETTE STEP FORMATS",
        "### HTTPS Sender",
        "### HTTP Receiver",
        "### OData",
    ]
    top = full
    for marker in stop_markers:
        idx = top.find(marker)
        if idx > 0:
            top = top[:idx]
            break
    # Cap the top section so it doesn't include verbose tables
    top = top[:6000]

    # ── Extract just the versions table (condensed) ──────────────────────────
    ver_start = full.find("## CONFIRMED VERSIONS")
    ver_block = ""
    if ver_start > 0:
        ver_end = full.find("\n## ", ver_start + 50)
        ver_block = full[ver_start: ver_start + 2000] if ver_end < 0 else full[ver_start:min(ver_start+2000, ver_end)]

    # ── ZIP structure ─────────────────────────────────────────────────────────
    zip_start = full.find("## ZIP FILE STRUCTURE")
    zip_block = ""
    if zip_start > 0:
        zip_end = full.find("\n## ", zip_start + 50)
        zip_block = full[zip_start: zip_start + 600] if zip_end < 0 else full[zip_start:min(zip_start+600, zip_end)]

    # ── BPMN rules summary ────────────────────────────────────────────────────
    bpmn_start = full.find("## IFLW BPMN RULES")
    bpmn_block = ""
    if bpmn_start > 0:
        bpmn_block = full[bpmn_start: bpmn_start + 800]

    result = "\n\n".join(filter(None, [top.strip(), ver_block.strip(), zip_block.strip(), bpmn_block.strip()]))
    return result

_IFLOW_CHEATSHEET = _load_iflow_cheatsheet()      # full — for reference only

# ─────────────────────────────────────────────────────────────────────────────
# Tenant-specific system prompt.
# NOTE: We do NOT inject the full cheatsheet here — it pushes the prompt over
# Groq's 12K TPM free-tier limit.  The existing rules below are comprehensive
# and already include the confirmed version numbers.
# ─────────────────────────────────────────────────────────────────────────────
IFLOW_SYSTEM = """\
You are an SAP CPI iFlow generator. Generate complete, importable .iflw XML.

== CONFIRMED VERSIONS (from 4 live tenant iFlows — use exactly) ==
IFlowConfig:         ctype::IFlowVariant/cname::IFlowConfiguration/version::1.2.4
IntegrationProcess:  ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.1
httpSessionHandling: onExchange  (NOT None)

Steps (all bpmn2:callActivity except ExternalCall and Router):
  Groovy Script:     Script / GroovyScript/version::1.1.2   (needs subActivityType+scriptBundleId)
  Content Modifier:  Enricher / Enricher/version::1.5.3
  Request Reply:     ExternalCall / ExternalCall/version::1.0.4  (bpmn2:serviceTask NOT callActivity)
  Message Mapping:   Mapping / MessageMapping/version::1.3.1
  Router:            ExclusiveGateway  (bpmn2:exclusiveGateway, cmdVariantUri=ExclusiveGateway no version)
  Splitter:          Splitter / GeneralSplitter/version::1.6.0
  DataStore Write:   DBstorage / put/version::1.7.1
  Timer Start:       StartTimerEvent / intermediatetimer/version::1.3.0
  Error SubProcess:  ErrorEventSubProcessTemplate/version::1.1.0
  MessageEndEvent:   cmdVariantUri=MessageEndEvent/version::1.1.0  (bpmn2:endEvent, needs messageEventDefinition)
  MessageStartEvent: cmdVariantUri=MessageStartEvent  (no version, needs messageEventDefinition)
  ErrorStartEvent:   cmdVariantUri=ErrorStartEvent  (no version)
  ErrorEndEvent:     cmdVariantUri=ErrorEndEvent  (no version)

Adapters:
  HTTPS Sender:  sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.0
  HTTP Receiver: sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.15.0
  OData Recv:    sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.24.0
  SOAP Recv:     sap:SOAP/tp::HTTP/mp::SOAP 1.x/direction::Receiver/version::1.12.3
  SFTP Recv:     sap:SFTP/tp::SFTP/mp::File/direction::Receiver/version::1.13.3

== CRITICAL RULES (each violation causes import failure) ==
1. ifl namespace: xmlns:ifl="http:///com.sap.ifl.model/Ifl.xsd"  (triple slash)
2. bpmn2:definitions has NO targetNamespace attribute
3. Collaboration name = "Default Collaboration" always
4. Participant ifl:type="EndpointRecevier" (SAP typo — single i in Recevier)
5. IntegrationProcess participant has EMPTY <bpmn2:extensionElements/>
6. Receiver messageFlow sourceRef = ServiceTask ID (NEVER EndEvent ID)
7. Exception Subprocess: NO triggeredByEvent attribute on bpmn2:subProcess
8. BPMNDiagram name="Default Collaboration Diagram" — required or iFlow won't open
9. Every di:waypoint needs xsi:type="dc:Point"
10. Every BPMNEdge needs sourceElement and targetElement (Shape ID refs)
11. Groovy Script callActivity must have subActivityType=GroovyScript + scriptBundleId (empty)
12. Router = bpmn2:exclusiveGateway (NOT callActivity). Conditions on sequenceFlow via bpmn2:conditionExpression
13. SFTP ServiceTask uses activityType=Send (NOT ExternalCall)
14. Timer startEvent: MUST have timerEventDefinition, scheduleKey={{Scheduler}}, NO intervalInMinutes

== ZIP FILE STRUCTURE (files at root — NO wrapper folder) ==
.project | metainfo.prop | META-INF/MANIFEST.MF
src/main/resources/scenarioflows/integrationflow/<Name>.iflw
src/main/resources/script/<Script>.groovy
src/main/resources/parameters.prop | parameters.propdef

== OUTPUT FORMAT ==
Return ONLY the raw .iflw XML — no JSON, no markdown fences, no explanation.
Start directly with: <?xml version="1.0" encoding="UTF-8"?><bpmn2:definitions
End with: </bpmn2:definitions>
"""

# ─────────────────────────────────────────────────────────────────────────────
# XML post-processor — fix common AI namespace and structural mistakes
# ─────────────────────────────────────────────────────────────────────────────

# Required extensionElements for <bpmn2:process> — CPI won't open without these
_PROCESS_EXT = (
    '\n    <bpmn2:extensionElements>\n'
    '        <ifl:property><key>transactionTimeout</key><value>30</value></ifl:property>\n'
    '        <ifl:property><key>componentVersion</key><value>1.2</value></ifl:property>\n'
    '        <ifl:property><key>cmdVariantUri</key>'
    '<value>ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.0</value></ifl:property>\n'
    '        <ifl:property><key>transactionalHandling</key><value>Not Required</value></ifl:property>\n'
    '    </bpmn2:extensionElements>'
)


def _extract_xml_block(xml: str, open_prefix: str, close_tag: str) -> str:
    """Return the first complete XML block that starts with open_prefix and ends with close_tag."""
    start = xml.find(open_prefix)
    if start == -1:
        return ''
    end = xml.find(close_tag, start)
    if end == -1:
        return ''
    return xml[start : end + len(close_tag)].strip()


def _parse_attrs(tag: str) -> dict:
    """Extract attribute name → value pairs from a single XML opening tag string."""
    return dict(re.findall(r'\b([\w:]+)\s*=\s*"([^"]*)"', tag))


def _fix_bpmn_edges(xml: str) -> str:
    """Add missing sourceElement / targetElement attributes to every BPMNEdge."""
    # Build flowId → (sourceRef, targetRef) from sequenceFlow and messageFlow elements
    flow_map: dict = {}
    for m in re.finditer(r'<bpmn2:(?:sequenceFlow|messageFlow)\b[^>]*>', xml):
        attrs = _parse_attrs(m.group(0))
        fid, src, tgt = attrs.get('id'), attrs.get('sourceRef'), attrs.get('targetRef')
        if fid and src and tgt:
            flow_map[fid] = (src, tgt)

    if not flow_map:
        return xml

    def _patch_edge(m: re.Match) -> str:
        tag = m.group(0)
        flow_id = _parse_attrs(tag).get('bpmnElement', '')
        refs = flow_map.get(flow_id)
        if not refs:
            return tag
        src_id, tgt_id = refs
        # Strip the trailing > so we can append attributes
        core = tag[:-1].rstrip()
        if 'sourceElement=' not in tag:
            core += f' sourceElement="BPMNShape_{src_id}"'
        if 'targetElement=' not in tag:
            core += f' targetElement="BPMNShape_{tgt_id}"'
        return core + '>'

    return re.sub(r'<bpmndi:BPMNEdge\b[^>]*>', _patch_edge, xml)


def _fix_iflw_xml(xml: str) -> str:
    """
    Repair common AI-generated iflw mistakes so SAP CPI can open the artifact.

    Fixes applied (in order):
      1  Strip markdown fences / leading text before <?xml
      2  Fix wrong ifl namespace (triple-slash URI)
      3  Add any missing required namespaces
      4  Fix ifl:type="System" → EndpointRecevier
      5  Add xsi:type="dc:Point" to di:waypoints
      6  Remove triggeredByEvent from subProcess
      7  Fix process name → "Integration Process"; remove isExecutable
      8  Add processRef="Process_1" to IntegrationProcess participant
      9  Ensure process has correct extensionElements (cmdVariantUri etc.)
     10  Enforce element order: collaboration → process → BPMNDiagram
     11  Add missing sourceElement / targetElement to BPMNEdge elements
    """
    # ── 0. Fix namespace prefix typos (e.g. bpm2: → bpmn2:) ──────────────────────
    xml = _fix_namespace_typos(xml)

    # ── 1. Strip markdown fences / leading whitespace ──────────────────────────
    xml = xml.strip()
    if xml.startswith("```"):
        xml = xml.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    # Skip any preamble text before the XML declaration
    start = xml.find("<?xml")
    if start == -1:
        start = xml.find("<bpmn2:definitions")
    if start > 0:
        xml = xml[start:]

    # ── 2. Fix wrong ifl namespace ─────────────────────────────────────────────
    xml = re.sub(r'xmlns:ifl="[^"]*"',
                 'xmlns:ifl="http:///com.sap.ifl.model/Ifl.xsd"', xml)

    # ── 3. Add missing required namespaces ────────────────────────────────────
    for ns, uri in [
        ('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance'),
        ('xmlns:dc',  'http://www.omg.org/spec/DD/20100524/DC'),
        ('xmlns:di',  'http://www.omg.org/spec/DD/20100524/DI'),
    ]:
        if f'{ns}=' not in xml:
            xml = re.sub(r'(<bpmn2:definitions\b)', rf'\1 {ns}="{uri}"', xml, count=1)

    # ── 4. Fix ifl:type="System" → EndpointRecevier ───────────────────────────
    xml = xml.replace('ifl:type="System"', 'ifl:type="EndpointRecevier"')
    xml = xml.replace('<value>System</value>', '<value>EndpointRecevier</value>')

    # ── 5. Add xsi:type="dc:Point" to waypoints that are missing it ───────────
    xml = re.sub(
        r'(<di:waypoint\b(?![^>]*xsi:type)[^>]*?)/>',
        lambda m: m.group(1).rstrip() + ' xsi:type="dc:Point"/>',
        xml,
    )

    # ── 6. Remove triggeredByEvent from subProcess ─────────────────────────────
    xml = re.sub(
        r'(<bpmn2:subProcess\b[^>]*?)\s+triggeredByEvent="[^"]*"',
        r'\1', xml,
    )

    # ── 7. Fix process element: name must be "Integration Process", no isExecutable
    xml = re.sub(
        r'(<bpmn2:process\b[^>]*)name="[^"]*"',
        r'\1name="Integration Process"', xml,
    )
    xml = re.sub(r'\s+isExecutable="[^"]*"', '', xml)

    # ── 8. Ensure IntegrationProcess participant has processRef="Process_1" ────
    def _add_process_ref(m: re.Match) -> str:
        tag = m.group(0)
        if 'processRef=' not in tag:
            tag = tag[:-1].rstrip() + ' processRef="Process_1">'
        return tag

    xml = re.sub(
        r'<bpmn2:participant\b[^>]*ifl:type="IntegrationProcess"[^>]*>',
        _add_process_ref, xml,
    )

    # ── 9. Ensure <bpmn2:process> has the required extensionElements ───────────
    if 'IntegrationProcess/version::1.2.0' not in xml:
        # Does the process element already have an extensionElements child?
        has_proc_ext = re.search(
            r'<bpmn2:process\b[^>]*>\s*<bpmn2:extensionElements>',
            xml,
        )
        if has_proc_ext:
            # Replace the whole existing extensionElements block (it lacks cmdVariantUri)
            xml = re.sub(
                r'(<bpmn2:process\b[^>]*>)\s*<bpmn2:extensionElements>.*?</bpmn2:extensionElements>',
                r'\1' + _PROCESS_EXT,
                xml, count=1, flags=re.DOTALL,
            )
        else:
            # No extensionElements at all — inject right after the process opening tag
            xml = re.sub(
                r'(<bpmn2:process\b[^>]*>)',
                r'\1' + _PROCESS_EXT,
                xml, count=1,
            )

    # ── 10. Enforce element order: collaboration → process → BPMNDiagram ──────
    #  (AI often emits process before collaboration, which causes CPI load errors)
    def_open_m = re.match(r'(.*?<bpmn2:definitions\b[^>]*>)', xml, re.DOTALL)
    if def_open_m:
        def_open = def_open_m.group(1)
        inner    = xml[len(def_open):]
        if inner.rstrip().endswith('</bpmn2:definitions>'):
            inner = inner.rstrip()[: -len('</bpmn2:definitions>')].rstrip()

        collab  = _extract_xml_block(inner, '<bpmn2:collaboration', '</bpmn2:collaboration>')
        process = _extract_xml_block(inner, '<bpmn2:process',       '</bpmn2:process>')
        diagram = _extract_xml_block(inner, '<bpmndi:BPMNDiagram',  '</bpmndi:BPMNDiagram>')

        if collab and process and diagram:
            # Strip the three known blocks to preserve any other declarations
            remaining = inner
            for blk in (collab, process, diagram):
                remaining = remaining.replace(blk, '', 1).strip()

            xml = (
                def_open + '\n\n'
                + (remaining + '\n\n' if remaining else '')
                + collab  + '\n\n'
                + process + '\n\n'
                + diagram + '\n\n'
                + '</bpmn2:definitions>'
            )

    # ── 11. Add missing sourceElement / targetElement to BPMNEdge elements ─────
    xml = _fix_bpmn_edges(xml)

    # ── 12. Convert serviceTask → callActivity for non-ExternalCall steps ────────
    #  (Script, Enricher, Mapping, Router, etc. must all be callActivity in CPI)
    xml = _fix_element_types(xml)

    # ── 13. Fix outdated cmdVariantUri version strings ────────────────────────────
    xml = _fix_version_strings(xml)

    # ── 14. Add cmdVariantUri extensionElements to MessageStartEvent/EndEvent ─────
    xml = _fix_event_extensions(xml)

    return xml


def _fix_namespace_typos(xml: str) -> str:
    """Fix common namespace prefix typos (e.g. bpm2: → bpmn2:)."""
    return xml.replace('<bpm2:', '<bpmn2:').replace('</bpm2:', '</bpmn2:')


def _fix_element_types(xml: str) -> str:
    """
    Convert bpmn2:serviceTask → bpmn2:callActivity for all non-ExternalCall steps.
    SAP CPI rule: serviceTask = ONLY activityType=ExternalCall (outbound adapter step).
                  callActivity = Groovy Script, Enricher, Mapping, Router, Splitter, etc.
    Also injects subActivityType=GroovyScript + scriptBundleId into Script callActivities.
    """
    def _swap(m: re.Match) -> str:
        block = m.group(0)
        if 'ExternalCall' in block:
            return block  # Keep ExternalCall as serviceTask
        block = re.sub(r'<bpmn2:serviceTask(\b|\s)', r'<bpmn2:callActivity\1', block, count=1)
        block = block.replace('</bpmn2:serviceTask>', '</bpmn2:callActivity>')
        return block

    xml = re.sub(
        r'<bpmn2:serviceTask\b.*?</bpmn2:serviceTask>',
        _swap, xml, flags=re.DOTALL,
    )

    def _add_groovy_props(m: re.Match) -> str:
        block = m.group(0)
        if 'subActivityType' in block or '<value>Script</value>' not in block:
            return block
        return re.sub(
            r'(<key>activityType</key>\s*<value>Script</value>\s*</ifl:property>)',
            (r'\1\n        <ifl:property><key>subActivityType</key>'
             r'<value>GroovyScript</value></ifl:property>'
             r'\n        <ifl:property><key>scriptBundleId</key><value/></ifl:property>'),
            block,
        )

    xml = re.sub(
        r'<bpmn2:callActivity\b.*?</bpmn2:callActivity>',
        _add_groovy_props, xml, flags=re.DOTALL,
    )
    return xml


def _fix_version_strings(xml: str) -> str:
    """Fix outdated cmdVariantUri version strings to match the live SAP Integration Suite tenant."""
    for old, new in (
        ('cname::IFlowConfiguration/version::1.2.3',          'cname::IFlowConfiguration/version::1.2.4'),
        ('cname::IntegrationProcess/version::1.2.0',           'cname::IntegrationProcess/version::1.2.1'),
        ('cname::ErrorEventSubProcessTemplate/version::1.0.2', 'cname::ErrorEventSubProcessTemplate/version::1.1.0'),
    ):
        xml = xml.replace(old, new)
    return xml


def _fix_event_extensions(xml: str) -> str:
    """
    Add missing cmdVariantUri extensionElements to MessageStartEvent and MessageEndEvent.
    Real CPI iFlows require these on every start/end event.
    """
    def _patch_start(m: re.Match) -> str:
        block = m.group(0)
        # Skip if already has cmdVariantUri, or is a Timer/Error start
        if ('cmdVariantUri' in block
                or 'timerEventDefinition' in block
                or 'errorEventDefinition' in block):
            return block
        if '<bpmn2:extensionElements>' not in block:
            block = re.sub(
                r'(<bpmn2:startEvent\b[^>]*>)',
                (r'\1\n    <bpmn2:extensionElements>\n'
                 r'        <ifl:property><key>cmdVariantUri</key>'
                 r'<value>ctype::FlowstepVariant/cname::MessageStartEvent</value></ifl:property>\n'
                 r'    </bpmn2:extensionElements>'),
                block, count=1,
            )
        return block

    xml = re.sub(
        r'<bpmn2:startEvent\b.*?</bpmn2:startEvent>',
        _patch_start, xml, flags=re.DOTALL,
    )

    def _patch_end(m: re.Match) -> str:
        block = m.group(0)
        if 'cmdVariantUri' in block or 'errorEventDefinition' in block:
            return block
        if '<bpmn2:extensionElements>' not in block:
            block = re.sub(
                r'(<bpmn2:endEvent\b[^>]*>)',
                (r'\1\n    <bpmn2:extensionElements>\n'
                 r'        <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>\n'
                 r'        <ifl:property><key>cmdVariantUri</key>'
                 r'<value>ctype::FlowstepVariant/cname::MessageEndEvent/version::1.1.0</value></ifl:property>\n'
                 r'    </bpmn2:extensionElements>'),
                block, count=1,
            )
        return block

    xml = re.sub(
        r'<bpmn2:endEvent\b.*?</bpmn2:endEvent>',
        _patch_end, xml, flags=re.DOTALL,
    )
    return xml


def _default_scripts(include_error_handling: bool) -> dict[str, str]:
    scripts = {"SetProperties.groovy": SET_PROPERTIES_GROOVY}
    if include_error_handling:
        scripts["HandleError.groovy"] = HANDLE_ERROR_GROOVY
    return scripts


# ─────────────────────────────────────────────────────────────────────────────
# Generate iFlow from form
# ─────────────────────────────────────────────────────────────────────────────
class IFlowRequest(BaseModel):
    name: str
    description: str
    sender_adapter: str = "HTTPS"
    receiver_adapter: str = "HTTP"
    transformation_type: str = "None"
    include_error_handling: bool = True
    extra_steps: str = ""
    version: str = "1.0.0"
    package_id: str = ""
    package_name: str = ""


@router.post("/generate")
def generate_iflow(req: IFlowRequest):
    is_timer = req.sender_adapter.upper() == "TIMER"
    trigger  = "Timer trigger (no sender participant — use startEvent with timerEventDefinition)" \
               if is_timer else f"Sender adapter: {req.sender_adapter}"

    prompt = f"""Generate the complete .iflw XML for this SAP CPI iFlow.
Return ONLY the raw XML — start with <?xml and end with </bpmn2:definitions>.

iFlow Name   : {req.name}
Description  : {req.description}
Trigger      : {trigger}
Receiver     : {req.receiver_adapter}
Transformation: {req.transformation_type}
Error Handling: {"Yes — include Exception Subprocess with ErrorStartEvent→ErrorEndEvent" if req.include_error_handling else "No"}
Extra Steps  : {req.extra_steps or "None"}

Requirements:
- The iflw references SetProperties.groovy (script file, key=script, value=SetProperties.groovy)
{"- The iflw references HandleError.groovy in the Exception Subprocess" if req.include_error_handling else ""}
- Externalize all URLs, credentials, endpoint paths as {{PARAM_NAME}}
- Use exact cmdVariantUri versions and adapter properties from the system instructions
- Include complete bpmndi:BPMNDiagram section with all shapes and edges
"""

    raw  = generate(IFLOW_SYSTEM, prompt, max_tokens=MAX_GENERATION_TOKENS)
    iflw = _fix_iflw_xml(raw)
    scripts = _default_scripts(req.include_error_handling)

    return {
        "result":      iflw,
        "scripts":     scripts,
        "description": req.description,
        "name":        req.name,
        "type":        "xml",
    }


# ─────────────────────────────────────────────────────────────────────────────
# ZIP Download
# ─────────────────────────────────────────────────────────────────────────────
class IFlowZipRequest(BaseModel):
    xml:         str
    name:        str
    description: str = ""
    version:     str = "1.0.0"
    scripts:     Optional[dict[str, str]] = None
    xsds:        Optional[dict[str, str]] = None
    mmaps:       Optional[dict[str, str]] = None


@router.post("/download-zip")
def download_iflow_zip(req: IFlowZipRequest):
    """Package the iFlow XML + scripts + schemas into a SAP CPI-importable ZIP."""
    zip_bytes = build_iflow_zip(
        iflow_xml   = req.xml,
        name        = req.name,
        description = req.description,
        version     = req.version,
        scripts     = req.scripts or {},
        xsds        = req.xsds   or {},
        mmaps       = req.mmaps  or {},
    )
    safe_name = req.name.replace(" ", "_") or "iflow"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={safe_name}.zip"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# FD → iFlow
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/fd-to-iflow")
async def fd_to_iflow(
    file:        UploadFile        = File(...),
    attachments: List[UploadFile]  = File([]),
    name:        str               = Form(""),
    version:     str               = Form("1.0.0"),
):
    file_bytes = await file.read()

    # Step 1: parse FD text
    sections   = parse_docx_to_text(file_bytes)
    fd_summary = sections_to_summary(sections)

    # Step 2: analyse embedded flow diagram image
    images        = extract_images_from_docx(file_bytes)
    image_context = ""
    for img in images:
        result = analyze_flow_image(img["bytes"], img["content_type"])
        if result.get("is_flow_diagram"):
            image_context = (
                "\nFLOW DIAGRAM EXTRACTED FROM FD IMAGE:\n"
                f"  System chain : {result.get('chain', '')}\n"
                f"  CPI steps    : {', '.join(result.get('cpi_steps', [])) or 'not visible'}\n"
                f"  Extra targets: {', '.join(result.get('multiple_targets', [])) or 'none'}\n"
                f"  Protocols    : {result.get('protocols', {})}\n"
                "Use this as the primary source for adapter types and the process chain.\n"
            )
            break

    # Step 3: read optional attachments
    attachment_context = ""
    extra_xsds:    dict[str, str] = {}
    extra_mmaps:   dict[str, str] = {}
    extra_scripts: dict[str, str] = {}

    for att in attachments:
        att_bytes = await att.read()
        fname = att.filename or "unknown"
        ext   = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        content = att_bytes.decode("utf-8", errors="replace")
        if ext in ("xsd", "wsdl"):
            extra_xsds[fname] = content
            attachment_context += f"\n--- Schema: {fname} ---\n{content[:1500]}\n"
        elif ext == "mmap":
            extra_mmaps[fname] = content
            attachment_context += f"\n--- Mapping: {fname} ---\n{content[:1000]}\n"
        elif ext == "groovy":
            extra_scripts[fname] = content
        else:
            attachment_context += f"\n--- File: {fname} ---\n{content[:1000]}\n"

    # Step 4: extract iFlow name from FD (quick call)
    iflow_name = name
    if not iflow_name:
        meta_raw = generate(
            "Return ONLY valid JSON with no markdown. Extract interface metadata from this FD.",
            f'Extract from this FD: {{"interface_id": "...", "description": "one sentence"}}\n\n{fd_summary[:1500]}'
        )
        try:
            meta_raw = meta_raw.strip()
            if meta_raw.startswith("```"):
                meta_raw = meta_raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            import json
            meta = json.loads(meta_raw)
            raw_id = meta.get("interface_id", "GeneratedIFlow")
            iflow_name   = re.sub(r"[^A-Za-z0-9_\-]", "_", raw_id.strip()) or "GeneratedIFlow"
        except Exception:
            iflow_name = "GeneratedIFlow"

    # Step 5: generate iflw XML
    has_xsds  = bool(extra_xsds)
    has_mmaps = bool(extra_mmaps)

    prompt = f"""Generate the complete .iflw XML for a SAP CPI iFlow based on the FD below.
Return ONLY the raw XML — start with <?xml and end with </bpmn2:definitions>.

iFlow Name: {iflow_name}
Version: {version}
{image_context}
{"Attached XSD schemas provided — reference them in the Message Mapping step." if has_xsds else ""}
{"Attached .mmap mapping file provided — reference it in the Message Mapping step." if has_mmaps else ""}

FD CONTENT:
{fd_summary[:3500]}
{attachment_context[:1000]}

Instructions:
1. Identify sender adapter/trigger from FD (HTTPS or Timer).
2. Identify receiver adapter(s) from FD.
3. Add transformation steps as described in the FD (mapping, Groovy, XSLT).
4. Externalize all configurable values as {{PARAM_NAME}}.
5. Reference SetProperties.groovy in a Groovy Script step near the start.
6. Include Exception Subprocess with HandleError.groovy reference.
7. Use exact versions and properties from the system instructions.
8. Include complete bpmndi:BPMNDiagram section.
"""

    raw  = generate(IFLOW_SYSTEM, prompt, max_tokens=MAX_GENERATION_TOKENS)
    iflw = _fix_iflw_xml(raw)

    # Merge: user-supplied scripts take priority over defaults
    merged_scripts = {**_default_scripts(True), **extra_scripts}

    return {
        "result":      iflw,
        "scripts":     merged_scripts,
        "description": fd_summary[:200].replace("\n", " "),
        "name":        iflow_name,
        "xsds":        extra_xsds,
        "mmaps":        extra_mmaps,
        "type":        "xml",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Explain
# ─────────────────────────────────────────────────────────────────────────────
class IFlowExplainRequest(BaseModel):
    xml: str


@router.post("/explain")
def explain_iflow(req: IFlowExplainRequest):
    prompt = f"""Analyze and explain this SAP CPI iFlow XML:

{req.xml[:5000]}

Provide:
1. Overview of what this iFlow does
2. Step-by-step flow description
3. Adapters/channels used and their versions
4. Externalized parameters ({{...}}) and what they configure
5. Potential issues or improvements
"""
    result = generate("", prompt)
    return {"result": result, "type": "markdown"}


# ─────────────────────────────────────────────────────────────────────────────
# Extract .iflw XML from a SAP CPI iFlow ZIP
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/extract-xml")
async def extract_iflow_xml(file: UploadFile = File(...)):
    """Extract the .iflw XML from a SAP CPI iFlow ZIP file."""
    import zipfile
    from fastapi import HTTPException as _HTTPException

    zip_bytes = await file.read()
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            iflw_files = [n for n in zf.namelist() if n.endswith(".iflw")]
            if not iflw_files:
                raise _HTTPException(
                    status_code=400,
                    detail="No .iflw file found in the ZIP. "
                           "Make sure this is a valid SAP CPI iFlow export.",
                )
            xml_content = zf.read(iflw_files[0]).decode("utf-8")
            name = iflw_files[0].split("/")[-1].replace(".iflw", "")
    except zipfile.BadZipFile:
        from fastapi import HTTPException as _HTTPException2
        raise _HTTPException2(
            status_code=400,
            detail="Invalid ZIP file. Please upload a valid SAP CPI iFlow ZIP.",
        )
    return {"xml": xml_content, "name": name}
