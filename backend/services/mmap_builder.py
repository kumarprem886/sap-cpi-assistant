"""
SAP CPI Graphical Message Mapping (.mmap) file builder.

Format reverse-engineered from real CPI mmap exports:
  - Namespace   : urn:sap-com:xi
  - Dst bricks  : <brick gid="0" path="..." type="Dst">
  - Src bricks  : <brick gid="0" path="..." type="Src">
  - Func bricks : <brick fname="..." fns="dflt" type="Func">
                    <arg>â€¦first argâ€¦</arg>
                    <arg pin="1">â€¦second argâ€¦</arg>
                    <bindings><param name="â€¦"><value>â€¦</value></param></bindings>
                  </brick>

Confirmed fname values (from real CPI exports):
  String  : toUpperCase, toLowerCase, trim, length, substring, concat, replaceString, equalsS, indexOf
  Date    : TransformDate   (user writes formatDate â€” translated here)
  Numeric : add, subtract, multiply, divide, abs, round, ceil, floor
  Boolean : if, Equals, notEquals, Not, And, Or
  Node    : useOneAsMany, SplitByValue, removeContexts, collapseContexts,
            createIf, exists, mapWithDefault, sort, sortByKey, replaceValue

ZIP bundle structure matches real CPI exports:
  xsd/<source_xsd_name>       â€” source XSD
  xsd/<target_xsd_name>       â€” target XSD
  mapping/<MappingName>.mmap  â€” the mapping XML
"""

import io
import time
import uuid
import zipfile
from xml.sax.saxutils import escape, quoteattr as _quoteattr


def _attr(value: str) -> str:
    """Safely escape a value for use inside an XML attribute (handles quotes)."""
    # quoteattr wraps in the appropriate quote char and escapes the other
    q = _quoteattr(value)
    # quoteattr adds surrounding quotes â€” strip them; we add our own in f-strings
    return q[1:-1].replace('"', '&quot;')


# â”€â”€ User-facing â†’ real SAP fname mapping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_FNAME_MAP: dict[str, str] = {
    # String
    "toUpperCase":   "toUpperCase",
    "toLowerCase":   "toLowerCase",
    "trim":          "trim",
    "length":        "length",
    "substring":     "substring",
    "concat":        "concat",
    "replaceAll":    "replaceString",   # user alias â†’ real name
    "replaceString": "replaceString",
    "indexOf":       "indexOf",
    "indexOf3":      "indexOf",
    "endsWith":      "endsWith",
    "startsWith":    "startsWith",
    "compare":       "compare",
    # Date
    "formatDate":    "TransformDate",   # user alias â†’ real name
    "TransformDate": "TransformDate",
    "DateTrans":     "TransformDate",
    "currentDate":   "currentDate",
    "DateBefore":    "DateBefore",
    "DateAfter":     "DateAfter",
    "CompareDates":  "CompareDates",
    # Numeric
    "add":           "add",
    "subtract":      "subtract",
    "multiply":      "multiply",
    "divide":        "divide",
    "abs":           "abs",
    "round":         "round",
    "ceil":          "ceil",
    "floor":         "floor",
    "FormatNum":     "FormatNum",
    # Boolean
    "if":            "if",
    "ifWithoutElse": "ifWithoutElse",
    "equals":        "Equals",          # user alias â†’ real name (capital E)
    "Equals":        "Equals",
    "equalsS":       "equalsS",
    "notEquals":     "notEquals",
    "Not":           "Not",
    "not":           "Not",
    "And":           "And",
    "and":           "And",
    "Or":            "Or",
    "or":            "Or",
    # Node
    "useOneAsMany":    "useOneAsMany",
    "splitByValue":    "SplitByValue",  # user alias â†’ real name (capital S)
    "SplitByValue":    "SplitByValue",
    "removeContexts":  "removeContexts",
    "collapseContexts":"collapseContexts",
    "createIf":        "createIf",
    "exists":          "exists",
    "mapWithDefault":  "mapWithDefault",
    "sort":            "sort",
    "sortByKey":       "sortByKey",
    "replaceValue":    "replaceValue",
    "formatByExample": "formatByExample",
    "UseOneAsMany":    "useOneAsMany",  # alternate capitalisation
}


def _resolve_fname(user_func: str) -> str:
    """Map user-facing function name to real SAP fname attribute value."""
    return _FNAME_MAP.get(user_func, user_func)


# â”€â”€ Low-level XML helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _uid() -> str:
    return uuid.uuid4().hex


def _src(path: str, x: int = 50, y: int = 40, context: str = "") -> str:
    ctx_attr = f' context="{escape(context)}"' if context else ""
    return (
        f'<brick{ctx_attr} gid="0" path="{_attr(path)}" type="Src">'
        f'<viewData x="{x}" y="{y}"/>'
        f'</brick>'
    )


def _const_as_binding_value(value: str) -> str:
    """An empty <value/> for empty strings, otherwise <value>text</value>."""
    return f'<value>{escape(value)}</value>' if value else '<value/>'


def _brick_direct(src_path: str, dst_path: str) -> str:
    """Direct 1-to-1 field mapping."""
    return (
        f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
        f'<viewData x="200" y="40"/>'
        f'<arg>{_src(src_path)}</arg>'
        f'<group/>'
        f'</brick>'
    )


def _arg(content: str, pin: int | None = None) -> str:
    pin_attr = f' pin="{pin}"' if pin is not None else ""
    return f'<arg{pin_attr}>{content}</arg>'


def _binding(name: str, value: str) -> str:
    return f'<param name="{_attr(name)}">{_const_as_binding_value(value)}</param>'


def _bindings(*params: tuple[str, str]) -> str:
    if not params:
        return ""
    inner = "".join(_binding(n, v) for n, v in params)
    return f'<bindings>{inner}</bindings>'


def _func_open(fname: str, x: int = 125, y: int = 30) -> str:
    return f'<brick fname="{_attr(fname)}" fns="dflt" type="Func"><viewData x="{x}" y="{y}"/>'


# â”€â”€ Function brick builders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _build_brick_for_part(p: dict, y: int = 40) -> str:
    """Render one argument part as a Src brick (or nested Func brick when needed)."""
    if p["type"] == "src":
        return _src(p["path"], y=y)
    # Constant â€” wrap as a no-arg concat with empty second arg as a workaround,
    # because SAP's graphical mapping has no standalone "Const" brick.
    # In practice, constants appear as <bindings> values, not separate bricks.
    # Return empty so callers can move the value to a binding.
    return ""


def _build_func_brick(dst_path: str, func_name: str, parts: list) -> str:
    """
    Build the complete Dst brick for a mapped function field.
    Handles each function's specific parameter structure based on real SAP mmap format.
    """
    fname = _resolve_fname(func_name)
    src_parts   = [p for p in parts if p["type"] == "src"]
    const_parts = [p for p in parts if p["type"] == "const"]

    # â”€â”€ concat â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # SAP concat takes exactly 2 inputs and a separator in bindings.
    # User syntax: (/src1)+SEP+(/src2) â†’ parts=[src1, const:SEP, src2]
    if fname == "concat":
        sources   = src_parts
        separator = const_parts[0]["value"] if const_parts else ""
        if not sources:
            return ""
        if len(sources) == 1:
            # Only one source â†’ direct mapping with separator irrelevant
            inner = _build_func_brick(dst_path, "toUpperCase", sources)  # fallback
            return _brick_direct(sources[0]["path"], dst_path)
        # Build left-associative chain for more than 2 sources
        def _chain(srcs: list) -> str:
            if len(srcs) == 2:
                return (
                    _func_open("concat")
                    + _arg(_src(srcs[0]["path"]))
                    + _arg(_src(srcs[1]["path"]), pin=1)
                    + _bindings(("delimeter", separator))
                    + "</brick>"
                )
            # 3+: concat(chain(first N-1), last)
            inner_chain = _chain(srcs[:-1])
            return (
                _func_open("concat", x=150)
                + _arg(inner_chain)
                + _arg(_src(srcs[-1]["path"]), pin=1)
                + _bindings(("delimeter", separator))
                + "</brick>"
            )
        func_xml = _chain(sources)
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ TransformDate (formatDate) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Parts: [src, const:iform, const:oform]
    if fname == "TransformDate":
        src_path = src_parts[0]["path"] if src_parts else ""
        iform    = const_parts[0]["value"] if len(const_parts) > 0 else "yyyyMMdd"
        oform    = const_parts[1]["value"] if len(const_parts) > 1 else "yyyy-MM-dd"
        func_xml = (
            _func_open("TransformDate")
            + _arg(_src(src_path))
            + _bindings(
                ("iform",  iform),
                ("oform",  oform),
                ("calend", "<calend_props><fd>1</fd><md>1</md><le>true</le></calend_props>"),
            )
            + "</brick>"
        )
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ mapWithDefault â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Parts: [src, const:default]  (key-value pairs not supported in XML â€” use Value Mapping)
    if fname == "mapWithDefault":
        src_path = src_parts[0]["path"] if src_parts else ""
        default  = const_parts[-1]["value"] if const_parts else ""
        func_xml = (
            _func_open("mapWithDefault")
            + _arg(_src(src_path))
            + _bindings(("default_value", default))
            + "</brick>"
        )
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ SplitByValue â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Parts: [src, const:delimiter]
    if fname == "SplitByValue":
        src_path  = src_parts[0]["path"] if src_parts else ""
        delimiter = const_parts[0]["value"] if const_parts else ","
        func_xml = (
            _func_open("SplitByValue")
            + _arg(_src(src_path))
            + _bindings(("delimeter", delimiter))
            + "</brick>"
        )
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ replaceString (replaceAll) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Parts: [src, const:search, const:replacement]
    if fname == "replaceString":
        src_path    = src_parts[0]["path"] if src_parts else ""
        search      = const_parts[0]["value"] if len(const_parts) > 0 else ""
        replacement = const_parts[1]["value"] if len(const_parts) > 1 else ""
        func_xml = (
            _func_open("replaceString")
            + _arg(_src(src_path))
            + _bindings(("search", search), ("replace", replacement))
            + "</brick>"
        )
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ substring â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Parts: [src, const:start, const:length]
    if fname == "substring":
        src_path = src_parts[0]["path"] if src_parts else ""
        start    = const_parts[0]["value"] if len(const_parts) > 0 else "0"
        length   = const_parts[1]["value"] if len(const_parts) > 1 else "10"
        func_xml = (
            _func_open("substring")
            + _arg(_src(src_path))
            + _bindings(("from", start), ("to", str(int(start) + int(length))
                         if start.isdigit() and length.isdigit() else length))
            + "</brick>"
        )
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ useOneAsMany â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Parts: [src]  (context args added automatically)
    if fname == "useOneAsMany":
        src_path = src_parts[0]["path"] if src_parts else ""
        func_xml = _func_open("useOneAsMany") + _arg(_src(src_path)) + "</brick>"
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ Simple single-arg functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # toUpperCase, toLowerCase, trim, length, abs, round, ceil, floor,
    # exists, removeContexts, collapseContexts, replaceValue, not, etc.
    _SIMPLE_ONE_ARG = {
        "toUpperCase", "toLowerCase", "trim", "length", "abs", "round",
        "ceil", "floor", "exists", "removeContexts", "collapseContexts",
        "replaceValue", "Not", "createIf",
    }
    if fname in _SIMPLE_ONE_ARG:
        src_path = src_parts[0]["path"] if src_parts else dst_path
        func_xml = _func_open(fname) + _arg(_src(src_path)) + "</brick>"
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ Two-arg functions with optional bindings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Equals, notEquals, equalsS, And, Or, compare, endsWith, startsWith, indexOf
    _TWO_ARG = {"Equals", "notEquals", "equalsS", "And", "Or", "compare",
                "endsWith", "startsWith", "indexOf", "add", "subtract",
                "multiply", "divide", "DateBefore", "DateAfter", "CompareDates"}
    if fname in _TWO_ARG:
        args_xml = ""
        for pin_idx, p in enumerate(src_parts[:2]):
            args_xml += _arg(_src(p["path"]), pin=pin_idx if pin_idx > 0 else None)
        # any const parts become bindings
        bindings_xml = ""
        if const_parts:
            bindings_xml = _bindings(*[(f"value{i}", cp["value"]) for i, cp in enumerate(const_parts)])
        func_xml = _func_open(fname) + args_xml + bindings_xml + "</brick>"
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ if / ifWithoutElse â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if fname in ("if", "ifWithoutElse"):
        args_xml = ""
        for pin_idx, p in enumerate(src_parts[:3]):
            args_xml += _arg(_src(p["path"]), pin=pin_idx if pin_idx > 0 else None)
        func_xml = _func_open(fname) + args_xml + "</brick>"
        return (
            f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
            f'<viewData x="200" y="40"/>'
            f'<arg>{func_xml}</arg>'
            f'<group/>'
            f'</brick>'
        )

    # â”€â”€ Fallback: generic function with all src args â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    args_xml = ""
    for pin_idx, p in enumerate(src_parts):
        args_xml += _arg(_src(p["path"]), pin=pin_idx if pin_idx > 0 else None)
    bindings_xml = ""
    if const_parts:
        bindings_xml = _bindings(*[(f"param{i}", cp["value"]) for i, cp in enumerate(const_parts)])
    func_xml = _func_open(fname) + args_xml + bindings_xml + "</brick>"
    return (
        f'<brick gid="0" path="{_attr(dst_path)}" type="Dst">'
        f'<viewData x="200" y="40"/>'
        f'<arg>{func_xml}</arg>'
        f'<group/>'
        f'</brick>'
    )


# â”€â”€ lnkRole helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _lnk(role: str, xsd_filename: str, root_element: str) -> str:
    return (
        f'<lnkRole kpos="1" role="{role}">'
        f'<lnk rMode="R">'
        f'<key typeID="xsd" version="1.1">'
        f'<elem>{_attr(xsd_filename)}</elem>'
        f'<elem>src/main/resources/wsdl</elem>'
        f'<elem>{_attr(root_element)}</elem>'
        f'</key>'
        f'</lnk>'
        f'</lnkRole>'
    )


# Keep old alias for callers that still use _concat_brick
def _concat_brick(dst_path: str, parts: list) -> str:
    return _build_func_brick(dst_path, "concat", parts)


# â”€â”€ Public: build .mmap XML string â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_mmap_xml(
    mapping_name: str,
    source_xsd_name: str,
    source_root: str,
    target_xsd_name: str,
    target_root: str,
    field_mappings: list,
    **_,
) -> str:
    ts_ms = int(time.time() * 1000)
    uid1  = _uid()
    uid2  = _uid()

    bricks_parts: list[str] = []
    for fm in field_mappings:
        tgt   = fm.get("target_path", "").strip()
        if not tgt:
            continue
        parts = fm.get("parts")
        func  = fm.get("func", "")
        src   = fm.get("source_path", "").strip()

        if parts and func:
            bricks_parts.append(_build_func_brick(tgt, func, parts))
        elif src:
            bricks_parts.append(_brick_direct(src, tgt))

    bricks   = "".join(bricks_parts)
    src_lnk  = _lnk("SOURCE_IFR_MESS", source_xsd_name, source_root)
    tgt_lnk  = _lnk("TARGET_IFR_MESS", target_xsd_name, target_root)

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
        '<modifBy></modifBy>'
        '<modifAt></modifAt>'
        f'<modifAtLong>{ts_ms}</modifAtLong>'
        '<owner/>'
        '</admInf>'
        f'<lnks>{tgt_lnk}{src_lnk}</lnks>'
        f'<textInfo loadedL="EN">'
        f'<textObj id="{uid1}" masterL="EN" type="0">'
        f'<texts lang="EN">'
        f'<text label=""/>'
        f'<text label="{uid2}"></text>'
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
        '<key><key typeID=""><elem></elem><elem></elem></key></key>'
        '<classname></classname>'
        '<package></package>'
        '<imports/>'
        '<globals><javaText/></globals>'
        '<init>'
        '<functionmodel>'
        '<signature cacheType="0"/>'
        '<name></name><key></key><tab></tab><title></title><uiTitle></uiTitle>'
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


# â”€â”€ Public: build ZIP bundle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_mmap_zip(
    mapping_name: str,
    mmap_xml: str,
    source_xsd: str = "",
    target_xsd: str = "",
    source_xsd_name: str = "source.xsd",
    target_xsd_name: str = "target.xsd",
    version: str = "1.0.0",
    include_manifest: bool = False,
) -> bytes:
    """
    Build a CPI Message Mapping ZIP.

    Standard export format (no manifest):
      mapping/<name>.mmap  |  xsd/<source>.xsd  |  xsd/<target>.xsd

    API import format (with manifest=True — required by MessageMappingDesigntimeArtifacts POST):
      META-INF/MANIFEST.MF  |  .project  |  mapping/<name>.mmap  |  xsd/...

    SAP's API import requires the manifest even though its own export does not include it.
    Set include_manifest=False only when you want a "download" ZIP matching CPI's export format.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if include_manifest:
            manifest = (
                "Manifest-Version: 1.0\r\n"
                f"Bundle-SymbolicName: {mapping_name}\r\n"
                f"Bundle-Name: {mapping_name}\r\n"
                f"Bundle-Version: {version}\r\n"
                "\r\n"
            )
            project = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<projectDescription>\n'
                f'  <name>{mapping_name}</name>\n'
                '  <comment></comment>\n'
                '  <buildSpec></buildSpec>\n'
                '  <natures></natures>\n'
                '</projectDescription>\n'
            )
            zf.writestr("META-INF/MANIFEST.MF", manifest.encode("utf-8"))
            zf.writestr(".project",             project.encode("utf-8"))

        zf.writestr(f"mapping/{mapping_name}.mmap", mmap_xml.encode("utf-8"))
        if source_xsd:
            zf.writestr(f"wsdl/{source_xsd_name}", source_xsd.encode("utf-8"))
        if target_xsd and target_xsd_name != source_xsd_name:
            zf.writestr(f"wsdl/{target_xsd_name}", target_xsd.encode("utf-8"))
    buf.seek(0)
    return buf.read()

