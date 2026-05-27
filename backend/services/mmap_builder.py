"""
SAP CPI Graphical Message Mapping (.mmap) file builder.

Format reverse-engineered from a real CPI export:
  - Namespace : urn:sap-com:xi
  - Mappings  : <brick type="Dst"> containing <arg><brick type="Src"/></arg>
  - Paths     : /RootElement/ParentElement/ChildElement  (bare names, no NS prefix)

ZIP bundle structure (matches real CPI exports exactly):
  wsdl/<source_xsd_name>          — source XSD schema
  wsdl/<target_xsd_name>          — target XSD (omitted when same name as source)
  mapping/<MappingName>.mmap      — mapping XML (urn:sap-com:xi format)
"""

import io
import time
import uuid
import zipfile
from xml.sax.saxutils import escape


# ─────────────────────────────────────────────────────────────────────────────
# Low-level XML helpers
# ─────────────────────────────────────────────────────────────────────────────

def _uid() -> str:
    """Random UUID without hyphens (used for textObj ids)."""
    return uuid.uuid4().hex


def _brick(src_path: str, dst_path: str) -> str:
    """One direct (1-to-1) field mapping: Dst brick wrapping a Src brick."""
    return (
        f'<brick gid="0" path="{escape(dst_path)}" type="Dst">'
        f'<viewData x="200" y="40"/>'
        f'<arg>'
        f'<brick gid="0" path="{escape(src_path)}" type="Src">'
        f'<viewData x="50" y="40"/>'
        f'</brick>'
        f'</arg>'
        f'<group/>'
        f'</brick>'
    )


def _lnk(role: str, xsd_filename: str, root_element: str) -> str:
    """<lnkRole> block for SOURCE_IFR_MESS or TARGET_IFR_MESS."""
    return (
        f'<lnkRole kpos="1" role="{role}">'
        f'<lnk rMode="R">'
        f'<key typeID="xsd" version="1.1">'
        f'<elem>{escape(xsd_filename)}</elem>'
        f'<elem>src/main/resources/wsdl</elem>'
        f'<elem>{escape(root_element)}</elem>'
        f'</key>'
        f'</lnk>'
        f'</lnkRole>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public: build .mmap XML string
# ─────────────────────────────────────────────────────────────────────────────

def build_mmap_xml(
    mapping_name: str,
    source_xsd_name: str,
    source_root: str,
    target_xsd_name: str,
    target_root: str,
    field_mappings: list,   # list of {"source_path": "...", "target_path": "..."}
    **_,                    # ignore unknown kwargs from old callers
) -> str:
    """
    Return the .mmap XML string exactly matching SAP CPI's urn:sap-com:xi format.
    Self-closing empty elements, no extra whitespace inside the XML (CPI stores it compact).
    """
    ts_ms  = int(time.time() * 1000)
    uid1   = _uid()
    uid2   = _uid()

    bricks = "".join(
        _brick(fm["source_path"].strip(), fm["target_path"].strip())
        for fm in field_mappings
        if fm.get("source_path", "").strip() and fm.get("target_path", "").strip()
    )

    src_lnk = _lnk("SOURCE_IFR_MESS", source_xsd_name, source_root)
    tgt_lnk = _lnk("TARGET_IFR_MESS", target_xsd_name, target_root)

    # NOTE: empty elements are self-closed (<modifBy/>) to match the real file exactly.
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<xiObj xmlns="urn:sap-com:xi">'

        '<idInfo VID="01">'
        '<vc caption="LOCAL" sp="-1" swcGuid="00000000000000000000000000000000" vcType="S">'
        '<clCxt consider="A"/>'
        '</vc>'
        '<key typeID="XI_TRAFO" version=""/>'
        '<version>1.0</version>'
        '</idInfo>'

        '<documentation><description/></documentation>'

        '<generic>'
        '<admInf>'
        '<modifBy/>'
        '<modifAt/>'
        f'<modifAtLong>{ts_ms}</modifAtLong>'
        '<owner/>'
        '</admInf>'
        # TARGET link comes first (matches real file order)
        f'<lnks>{tgt_lnk}{src_lnk}</lnks>'
        f'<textInfo loadedL="EN">'
        f'<textObj id="{uid1}" masterL="EN" type="0">'
        f'<texts lang="EN">'
        f'<text label=""/>'
        f'<text label="{uid2}"/>'
        f'</texts>'
        f'</textObj>'
        f'</textInfo>'
        '</generic>'

        '<AdditionalProperties>'
        '<Property Applicable="BOTH">'
        '<PropertyName>externalNameSpace</PropertyName>'
        '<PropertyValue>RESOLVED</PropertyValue>'
        '</Property>'
        '</AdditionalProperties>'

        '<content>'
        '<tr:XiTrafo xmlns:tr="urn:sap-com:xi:mapping:xitrafo">'
        '<tr:MetaData>'
        '<mappingtool version="XI7.1">'
        '<project version="XI7.1">'
        '<libstorage>'
        '<entry name="usernamespace">'
        '<functionstorage version="XI7.1">'
        '<key><key typeID=""><elem/><elem/></key></key>'
        '<classname/>'
        '<package/>'
        '<imports/>'
        '<globals><javaText/></globals>'
        '<init>'
        '<functionmodel>'
        '<signature cacheType="0"/>'
        '<name/><key/><tab/><title/><uiTitle/>'
        '<implementation type="udf"><javaText/></implementation>'
        '</functionmodel>'
        '</init>'
        '<cleanup><javaText/></cleanup>'
        '<usedjars/>'
        '</functionstorage>'
        '</entry>'
        '</libstorage>'
        f'<transformation>{bricks}</transformation>'
        '<testData><instances/></testData>'
        '<ViewState/>'
        '<pcont/>'
        '</project>'
        '</mappingtool>'
        '</tr:MetaData>'
        '<tr:ByteCodeJar/>'
        '<tr:SourceStructure/>'
        '<tr:TargetStructure/>'
        '<tr:Multiplicity>1:1</tr:Multiplicity>'
        '<tr:SourceParameters>'
        '<tr:Parameter>'
        '<tr:Position>1</tr:Position>'
        '<tr:Minoccurs>1</tr:Minoccurs>'
        '<tr:Maxoccurs>1</tr:Maxoccurs>'
        '</tr:Parameter>'
        '</tr:SourceParameters>'
        '<tr:TargetParameters>'
        '<tr:Parameter>'
        '<tr:Position>1</tr:Position>'
        '<tr:Minoccurs>1</tr:Minoccurs>'
        '<tr:Maxoccurs>1</tr:Maxoccurs>'
        '</tr:Parameter>'
        '</tr:TargetParameters>'
        '</tr:XiTrafo>'
        '</content>'

        '</xiObj>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public: build ZIP bundle
# ─────────────────────────────────────────────────────────────────────────────

def build_mmap_zip(
    mapping_name: str,
    mmap_xml: str,
    source_xsd: str = "",
    target_xsd: str = "",
    source_xsd_name: str = "source.xsd",
    target_xsd_name: str = "target.xsd",
) -> bytes:
    """
    Bundle exactly like a real CPI export:
      wsdl/<source_xsd_name>        — source XSD
      wsdl/<target_xsd_name>        — target XSD (omitted if same name as source)
      mapping/<mapping_name>.mmap   — the mapping XML

    No README, no extra files — matches the sample ZIP structure exactly.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Source XSD
        if source_xsd:
            zf.writestr(f"wsdl/{source_xsd_name}", source_xsd.encode("utf-8"))

        # Target XSD — only write if it has a different name from source
        if target_xsd and target_xsd_name != source_xsd_name:
            zf.writestr(f"wsdl/{target_xsd_name}", target_xsd.encode("utf-8"))

        # The .mmap — goes in mapping/ folder
        zf.writestr(f"mapping/{mapping_name}.mmap", mmap_xml.encode("utf-8"))

    buf.seek(0)
    return buf.read()
