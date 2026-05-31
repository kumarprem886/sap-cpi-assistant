"""
Mapping validation utilities.
Validates that AI-generated mapping rules reference real XSD paths,
function names are known, and the assembled mmap XML is well-formed.
"""
from __future__ import annotations
import re
from typing import NamedTuple

# ── Known valid SAP CPI function names (fname attribute values) ──────────────
_KNOWN_FNAMES = {
    # Arithmetic
    "add","subtract","multiply","divide","power","less","greater","max","min",
    "abs","neg","inv","sqrt","sqr","sign","round","ceil","floor","equalsA","FormatNum","counter",
    # Boolean
    "if","ifWithoutElse","ifS","ifSWithoutElse","Equals","notEquals","And","Or","Not","isNil",
    # Constant
    "constant","copyValue","currentDate",
    # Conversion
    "fixValues","valuemap",
    # Date
    "TransformDate","DateBefore","DateAfter","CompareDates",
    # Node
    "useOneAsMany","mapWithDefault","exists","getHeader","getProperty",
    "SplitByValue","removeContexts","collapseContexts","createIf","sort","sortByKey",
    "replaceValue","formatByExample",
    # Statistics
    "sum","average","count","index",
    # Text
    "toUpperCase","toLowerCase","trim","length","substring","concat",
    "replaceString","equalsS","indexOf","lastIndexOf","endsWith","startsWith",
    "compare","contains",
    # xsi:nil (special)
    "xsi:nil",
}

# Functions that don't exist in SAP CPI (commonly hallucinated)
_INVALID_FNAMES = {"first","last","max_value","min_value","getLast","getFirst",
                    "average_of","totalSum","concat2","join"}

# Known-valid date format tokens (case sensitive — SAP CPI uses Java SimpleDateFormat)
_DATE_FMT_WARN = re.compile(r'[YD]{2,}')   # YYYY or DD = wrong case (should be yyyy, dd)


class FieldIssue(NamedTuple):
    target:   str
    rule:     str
    issue:    str
    severity: str   # "error" | "warning" | "info"


def validate_rule_fields(rule: str, src_paths: list[str]) -> tuple[list[str], list[str]]:
    """
    Extract all (/path) references from a rule and classify each as:
      - exact match  → OK (not returned)
      - short-name match only → fuzzy (returned in fuzzy list, -10 score each)
      - no match at all → missing (returned in missing list, -30 score each)

    Returns (missing, fuzzy) — both empty means all field refs are confirmed OK.
    """
    if not rule or not src_paths:
        return [], []
    refs = re.findall(r'\((/[^)]+)\)', rule)
    src_set   = {p.lower() for p in src_paths}
    src_short = {p.rsplit("/", 1)[-1].lower() for p in src_paths}
    missing, fuzzy = [], []
    for ref in refs:
        ref_lower = ref.lower()
        ref_short = ref.rsplit("/", 1)[-1].lower()
        if ref_lower in src_set:
            pass                               # exact match ✓
        elif ref_short in src_short:
            fuzzy.append(ref)                  # short-name match — possibly right path, possibly not
        else:
            missing.append(ref)                # not found at all
    return missing, fuzzy


def validate_function_name(rule: str) -> tuple[str | None, bool]:
    """
    Extract the top-level function name from a rule and check it's known.
    Returns (fname, is_valid).
      True  = confirmed valid SAP CPI function or known user alias
      False = confirmed INVALID (function does not exist in SAP CPI)
      None  = uncertain / unrecognised (warn user)
    """
    if not rule:
        return None, True
    # Concat shorthand: (/f)+SEP+(/f)
    if re.match(r'\(/', rule) or re.search(r'\)+\S+\(', rule):
        return "concat", True
    m = re.match(r'^([A-Za-z][A-Za-z0-9_:]*)\s*\(', rule)
    if not m:
        return None, True   # direct copy or xsi:nil
    fname = m.group(1)

    # Confirmed bad — these do NOT exist in SAP CPI
    if fname.lower() in {f.lower() for f in _INVALID_FNAMES}:
        return fname, False

    # Check against real SAP fname values
    if fname in _KNOWN_FNAMES or fname.lower() in {f.lower() for f in _KNOWN_FNAMES}:
        return fname, True

    # Check against user aliases in _FNAME_MAP (formatDate, replaceAll, etc.)
    try:
        from services.mmap_builder import _FNAME_MAP
        if fname in _FNAME_MAP or fname.lower() in {k.lower() for k in _FNAME_MAP}:
            return fname, True
    except ImportError:
        pass

    # Unrecognised — might work, might not
    return fname, None


def validate_date_formats(rule: str) -> str | None:
    """Detect wrong-case date format strings (YYYY->yyyy, DD->dd)."""
    if "formatDate" not in rule and "TransformDate" not in rule:
        return None
    parts = re.findall(r',\s*([A-Za-z/:\-]+)', rule)
    for p in parts:
        if _DATE_FMT_WARN.search(p):
            return (f"Date format '{p}' may have wrong case — "
                    "SAP CPI uses Java SimpleDateFormat (yyyy not YYYY, dd not DD, MM not mm for months)")
    return None


def score_row(target: str, rule: str, src_paths: list[str]) -> dict:
    """
    Compute a trust score for one mapping row.
    Returns:
      tier: "green" | "yellow" | "red"
      score: 0-100
      issues: list of issue strings
    """
    issues = []
    score = 100

    if not rule:
        # Direct copy — always green
        return {"tier": "green", "score": 100, "issues": []}

    # 1. Function name check
    fname, fname_ok = validate_function_name(rule)
    if fname_ok is False:
        issues.append(f"Function '{fname}' does not exist in SAP CPI — will fail in CPI")
        score -= 65      # definitely broken → push to red
    elif fname_ok is None:
        issues.append(f"Function '{fname}' is not a recognised SAP CPI standard name — verify it")
        score -= 25      # unknown → yellow

    # 2. Field path check — separate exact-miss from short-name-only match
    missing, fuzzy = validate_rule_fields(rule, src_paths)
    for m in missing:
        issues.append(f"Field '{m}' NOT found in source XSD — CPI will show an empty input slot")
        score -= 55      # definitely wrong path → red
    for f in fuzzy:
        issues.append(f"Field '{f}' matched by short name only — confirm the full XPath is correct")
        score -= 20      # possibly wrong path → yellow

    # 3. Date format check
    date_warn = validate_date_formats(rule)
    if date_warn:
        issues.append(date_warn)
        score -= 20      # wrong case in date format → silently wrong at runtime → yellow

    # 4. useOneAsMany arg count
    if fname == "useOneAsMany":
        args = re.findall(r'\(/', rule)
        if len(args) < 3:
            issues.append(
                "useOneAsMany needs 3 arguments: (value), (contextParent), (contextField). "
                f"Only {len(args)} found — context will not work correctly in CPI"
            )
            score -= 25

    score = max(0, score)
    if score >= 85:
        tier = "green"     # all field refs confirmed in XSD, function known, no format warnings
    elif score >= 50:
        tier = "yellow"    # minor issues — fuzzy path, unknown alias, date case, uOAM arg count
    else:
        tier = "red"       # critical — invalid function, field path not in XSD at all

    return {"tier": tier, "score": score, "issues": issues}


def validate_mmap_xml(mmap_xml: str) -> dict:
    """
    Parse the assembled mmap XML and return a quality report.
    Catches malformed XML and counts structural elements.
    """
    import re
    report = {
        "xml_valid": False,
        "dst_count": 0,
        "func_count": 0,
        "src_count": 0,
        "warnings": [],
    }
    try:
        from lxml import etree
        etree.fromstring(mmap_xml.encode("utf-8"))
        report["xml_valid"] = True
    except Exception as e:
        report["warnings"].append(f"XML parse error: {e}")
        return report

    report["dst_count"]  = len(re.findall(r'type="Dst"', mmap_xml))
    report["func_count"] = len(re.findall(r'type="Func"', mmap_xml))
    report["src_count"]  = len(re.findall(r'type="Src"', mmap_xml))

    if report["dst_count"] == 0:
        report["warnings"].append("No Dst bricks found — mapping is empty")
    if report["dst_count"] > 0 and report["src_count"] == 0:
        report["warnings"].append("Dst bricks present but no Src bricks — all mappings are constants or broken")

    return report


def quality_report(rows: list[dict], src_paths: list[str]) -> dict:
    """
    Compute a quality report for a full set of mapping rows.
    Returns summary + per-row tier.
    """
    green = yellow = red = 0
    field_issues = []

    for row in rows:
        rule   = (row.get("technical_rule") or row.get("rule") or "").strip()
        target = (row.get("target_path") or row.get("target") or "").split("/")[-1]
        result = score_row(target, rule, src_paths)
        row["_tier"]   = result["tier"]
        row["_score"]  = result["score"]
        row["_issues"] = result["issues"]
        if result["tier"] == "green":  green  += 1
        elif result["tier"] == "yellow": yellow += 1
        else:                            red    += 1
        for iss in result["issues"]:
            field_issues.append({"target": target, "rule": rule, "issue": iss,
                                  "severity": "error" if result["tier"] == "red" else "warning"})

    total = green + yellow + red or 1
    overall_score = round((green * 100 + yellow * 60 + red * 20) / total)
    if overall_score >= 80: overall_tier = "green"
    elif overall_score >= 55: overall_tier = "yellow"
    else: overall_tier = "red"

    return {
        "overall_tier":  overall_tier,
        "overall_score": overall_score,
        "total":  total,
        "green":  green,
        "yellow": yellow,
        "red":    red,
        "field_issues": field_issues,
    }
