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


def _inner_src(path: str, y: int = 40) -> str:
    """Source field brick for use as a function argument."""
    return (
        f'<brick gid="0" path="{escape(path)}" type="Src">'
        f'<viewData x="50" y="{y}"/>'
        f'</brick>'
    )


def _inner_const(value: str, y: int = 40) -> str:
    """Constant value brick for use as a function argument."""
    return (
        f'<brick gid="0" constValue="{escape(value)}" type="Const">'
        f'<viewData x="50" y="{y}"/>'
        f'</brick>'
    )


def _leaf_brick(p: dict, y: int = 40) -> str:
    """Render a single argument part as a src or const brick."""
    if p["type"] == "src":
        return _inner_src(p["path"], y)
    return _inner_const(p["value"], y)


def _build_func_node(func_name: str, parts: list, y: int = 30) -> str:
    """
    Build a function node brick for any SAP CPI standard node function.

    ``concat`` with more than 2 arguments is chained left-associatively
    (CPI's concat takes exactly 2 inputs).  All other functions receive
    all arguments as parallel <arg> elements.

    parts: list of {"type": "src"/"const", "path"/"value": "..."}
    """
    if not parts:
        return ""

    # ── Special case: concat needs chaining for N > 2 ──────────────────
    if func_name.lower() == "concat":
        if len(parts) == 1:
            return _leaf_brick(parts[0], y)
        if len(parts) == 2:
            a = _leaf_brick(parts[0], y)
            b = _leaf_brick(parts[1], y + 30)
            return (
                f'<brick gid="0" funcName="concat" type="Function">'
                f'<viewData x="125" y="{y}"/>'
                f'<arg>{a}</arg>'
                f'<arg>{b}</arg>'
                f'</brick>'
            )
        # N > 2: concat(chain(first N-1), last)
        inner = _build_func_node("concat", parts[:-1], y)
        last  = _leaf_brick(parts[-1], y + 30)
        return (
            f'<brick gid="0" funcName="concat" type="Function">'
            f'<viewData x="150" y="{y}"/>'
            f'<arg>{inner}</arg>'
            f'<arg>{last}</arg>'
            f'</brick>'
        )

    # ── General case: function with N parallel arguments ────────────────
    args_xml = "".join(
        f"<arg>{_leaf_brick(p, y + i * 30)}</arg>"
        for i, p in enumerate(parts)
    )
    return (
        f'<brick gid="0" funcName="{escape(func_name)}" type="Function">'
        f'<viewData x="125" y="{y}"/>'
        f'{args_xml}'
        f'</brick>'
    )


def _func_brick(dst_path: str, func_name: str, parts: list) -> str:
    """
    Complete Dst brick whose source is a node function (any funcName).
    Falls back to a direct source brick when only one part and no function needed.
    """
    if len(parts) == 1 and not func_name:
        # No function — plain source mapping
        p = parts[0]
        if p["type"] == "src":
            return _brick(p["path"], dst_path)
    inner = _build_func_node(func_name, parts)
    return (
        f'<brick gid="0" path="{escape(dst_path)}" type="Dst">'
        f'<viewData x="200" y="40"/>'
        f'<arg>{inner}</arg>'
        f'<group/>'
        f'</brick>'
    )


# Keep the old name as an alias so existing callers don't break
def _concat_brick(dst_path: str, parts: list) -> str:
    return _func_brick(dst_path, "concat", parts)


def _lnk(role: str, xsd_filename: str, root_element: str) -> str:
    """<lnkRole> block for SOURCE_IFR_MESS or TARGET_IFR_MESS."""
    return (
        f'<lnkRole kpos="1" role="{role}">'
        f'<lnk rMode="R">'
        f'<key typeID="xsd" version="1.1">'
        f'<elem>{escape(xsd_filename)}</elem>'
        f'<elem>src/main/resources/xsd</elem>'
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

    bricks_parts = []
    for fm in field_mappings:
        tgt   = fm.get("target_path", "").strip()
        if not tgt:
            continue
        parts = fm.get("parts")                       # function mapping
        func  = fm.get("func", "concat")              # function name
        src   = fm.get("source_path", "").strip()
        if parts:
            bricks_parts.append(_func_brick(tgt, func, parts))
        elif src:
            bricks_parts.append(_brick(src, tgt))
    bricks = "".join(bricks_parts)

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
            zf.writestr(f"xsd/{source_xsd_name}", source_xsd.encode("utf-8"))

        # Target XSD — only write if it has a different name from source
        if target_xsd and target_xsd_name != source_xsd_name:
            zf.writestr(f"xsd/{target_xsd_name}", target_xsd.encode("utf-8"))

        # The .mmap — goes in mapping/ folder
        zf.writestr(f"mapping/{mapping_name}.mmap", mmap_xml.encode("utf-8"))

    buf.seek(0)
    return buf.read()
