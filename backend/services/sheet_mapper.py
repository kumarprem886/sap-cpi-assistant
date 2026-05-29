"""
Mapping-sheet parser for SAP CPI .mmap generation.

Reads an Excel (.xlsx) or CSV (.csv) file whose rows describe how source
fields map to target fields, then resolves those short field names to full
XPath-style paths extracted from the uploaded XSDs.

Key behaviours
--------------
* Detects column layout automatically from header row keywords.
* For every target field that appears multiple times in the sheet, picks the
  Nth occurrence in the target XSD so "RunDate (row 1)" maps to the outer
  /Header/HeaderType/RunDate and "RunDate (row 4)" maps to the inner
  /Header/HeaderType/to_Stock/StockType/RunDate.
* Mapping rules like "(/msg/header/date)+T+(/msg/header/time)" are parsed
  into SAP CPI concat node-function bricks (type="Function" funcName="concat").
* After resolving all sheet rows, direct-parent container paths are
  auto-added for every simple 1-to-1 leaf mapping that lacks one.
"""

from __future__ import annotations

import io
import csv
import re
from pathlib import Path


# ── Excel / CSV readers ───────────────────────────────────────────────────────

def _rows_from_xlsx(data: bytes) -> list[list]:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        raise RuntimeError(
            "openpyxl is required for .xlsx support.  "
            "Run: pip install openpyxl"
        )
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = wb.active
    return [
        list(row)
        for row in ws.iter_rows(values_only=True)
        if any(c is not None for c in row)
    ]


def _rows_from_csv(data: bytes) -> list[list]:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader if any(c.strip() for c in row)]


def _rows_from_file(data: bytes, filename: str) -> list[list]:
    ext = Path(filename).suffix.lower()
    if ext in (".xlsx", ".xlsm", ".xlam"):
        return _rows_from_xlsx(data)
    if ext == ".xls":
        raise RuntimeError(
            ".xls is not supported — please save as .xlsx or .csv."
        )
    return _rows_from_csv(data)


# ── Column detection ──────────────────────────────────────────────────────────

def _detect_col(headers: list[str], keywords: list[str]) -> int:
    for i, h in enumerate(headers):
        if h and any(kw in h.lower() for kw in keywords):
            return i
    return -1


def _parse_sheet_rows(data: bytes, filename: str) -> list[dict]:
    rows = _rows_from_file(data, filename)
    if not rows:
        return []

    first = [str(c).strip() if c is not None else "" for c in rows[0]]
    has_header = (
        _detect_col(first, ["source"]) >= 0 or
        _detect_col(first, ["target"]) >= 0
    )

    if has_header:
        headers   = first
        data_rows = rows[1:]
        src_col   = _detect_col(headers, ["source field", "source"])
        tgt_col   = _detect_col(headers, ["target field", "target"])
        # Functional rule: plain-English description
        func_col  = _detect_col(headers, ["functional mapping", "functional rule",
                                           "functional", "business rule", "description"])
        # Technical rule: CPI expression (takes priority for actual mapping)
        tech_col  = _detect_col(headers, ["technical mapping", "technical rule",
                                           "technical", "cpi expression", "expression",
                                           "mapping rule", "rule", "formula",
                                           "function", "transform"])
    else:
        data_rows = rows
        src_col   = 0
        tgt_col   = len(rows[0]) - 1
        func_col  = -1
        tech_col  = 2 if len(rows[0]) > 2 else -1

    src_col  = max(src_col, 0)
    tgt_col  = tgt_col if tgt_col >= 0 else 1

    results = []
    for row in data_rows:
        def _cell(idx: int) -> str | None:
            if idx < 0 or idx >= len(row):
                return None
            v = row[idx]
            s = str(v).strip() if v is not None else ""
            return s or None

        src       = _cell(src_col)
        tgt       = _cell(tgt_col)
        func_rule = _cell(func_col) if func_col >= 0 else None
        tech_rule = _cell(tech_col) if tech_col >= 0 else None

        # Technical rule takes priority; fall back to functional rule as rule hint
        effective_rule = tech_rule or None

        if src or tgt:
            results.append({
                "source":          src,
                "target":          tgt,
                "rule":            effective_rule,
                "functional_rule": func_rule,
                "technical_rule":  tech_rule,
            })

    return results


# ── Path matching helpers ─────────────────────────────────────────────────────

def _last_seg(path: str) -> str:
    return path.rsplit("/", 1)[-1].lower()


def _match_field(field_name: str, paths: list[str]) -> str | None:
    """First (shallowest) path whose last segment equals field_name."""
    if not field_name:
        return None
    fn = field_name.strip().lower()
    for p in paths:
        if _last_seg(p) == fn:
            return p
    # Fallback: match any segment (structural nodes)
    for p in paths:
        for i, seg in enumerate(p.split("/")):
            if seg.lower() == fn:
                return "/".join(p.split("/")[: i + 1]) or p
    return None


def _match_all_fields(field_name: str, paths: list[str]) -> list[str]:
    """ALL paths whose last segment equals field_name (in order of depth)."""
    if not field_name:
        return []
    fn = field_name.strip().lower()
    return [p for p in paths if _last_seg(p) == fn]


# ── Rule parser (concat shorthand + generic function calls) ───────────────────

def _split_func_args(args_str: str) -> list[str]:
    """
    Split a function argument list by comma, respecting nested parentheses.
    Empty arguments (e.g. trailing comma for empty-string replacement) are kept.
    """
    args: list[str] = []
    depth   = 0
    current = ""
    for ch in args_str:
        if ch == "(":
            depth += 1
            current += ch
        elif ch == ")":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            args.append(current)   # keep even if empty — valid empty-string constant
            current = ""
        else:
            current += ch
    args.append(current)           # always append the last segment
    return args


def _resolve_arg(token: str, src_paths: list[str]) -> dict:
    """Convert one rule argument token into a {"type", "path"/"value"} dict."""
    token = token.strip()
    # XPath reference: (/path/to/field)  or  /path/to/field
    m = re.match(r"^\(?(/[^)]*?)\)?$", token)
    if m:
        xpath      = m.group(1).strip().rstrip(")")
        field_name = xpath.rsplit("/", 1)[-1]
        resolved   = _match_field(field_name, src_paths) or xpath
        return {"type": "src", "path": resolved}
    # Everything else is a constant (string, number, date pattern…)
    return {"type": "const", "value": token}


def _parse_rule(rule: str, src_paths: list[str]) -> tuple[str, list[dict]] | None:
    """
    Parse a mapping rule into (func_name, parts).

    Two syntaxes are supported:

    1. **Concat shorthand** (backward-compatible)
       ``(/msg/header/date)+T+(/msg/header/time)``
       → ("concat", [src:date, const:"T", src:time])

    2. **Function call** — any SAP CPI standard node function
       ``toUpperCase((/msg/header/sender))``
       → ("toUpperCase", [src:sender])

       ``substring((/msg/header/time), 0, 6)``
       → ("substring", [src:time, const:"0", const:"6"])

       ``formatDate((/msg/header/date), yyyyMMdd, yyyy-MM-dd)``
       → ("formatDate", [src:date, const:"yyyyMMdd", const:"yyyy-MM-dd"])

       ``mapWithDefault((/field), Y, YES, N, NO)``
       → ("mapWithDefault", [...])

       ``concat((/field1), CONST, (/field2))``
       → ("concat", [src:field1, const:CONST, src:field2])

    Returns None when the rule cannot be parsed (treated as single-source or ignored).
    """
    if not rule:
        return None

    rule = rule.strip()

    # ── Syntax 2: funcName(arg1, arg2, ...) ─────────────────────────────
    func_m = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\s*\((.+)\)\s*$", rule, re.DOTALL)
    if func_m:
        func_name = func_m.group(1)
        args_str  = func_m.group(2)
        raw_args  = _split_func_args(args_str)
        parts     = [_resolve_arg(a, src_paths) for a in raw_args]
        # A function with a single source arg and no "Function" nature
        # is handled as a function brick (e.g. toUpperCase(src))
        return (func_name, parts)

    # ── Syntax 1: concat shorthand with + ───────────────────────────────
    if "+" in rule:
        parts = [_resolve_arg(tok, src_paths) for tok in rule.split("+")]
        if len(parts) >= 2:
            return ("concat", parts)

    return None


def _source_fields_from_rule(rule: str) -> list[str]:
    """Extract bare field names from a rule string (fallback for non-concat rules)."""
    refs: list[str] = []
    for m in re.findall(r"\((/[^)]+)\)", rule):
        refs.append(m.strip("/").rsplit("/", 1)[-1])
    if not refs:
        for token in re.split(r"[^a-zA-Z0-9_./]", rule):
            token = token.strip().strip("/")
            if token:
                refs.append(token.rsplit(".", 1)[-1].rsplit("/", 1)[-1])
    return [r for r in refs if r]


# ── Parent-mapping helper ─────────────────────────────────────────────────────

def _get_parent(path: str) -> str:
    """Return the direct parent path, or '' when already at root."""
    if path.count("/") <= 1:      # e.g. '' or '/Root'
        return ""
    return path.rsplit("/", 1)[0]


def _ensure_parent_mappings(
    matched: list[dict],
    src_path_set: set[str],
    tgt_path_set: set[str],
) -> list[dict]:
    """
    For every simple 1-to-1 mapping whose DIRECT parent pair
    (src_parent, tgt_parent) is not already present, add it —
    provided both parent paths exist in the respective XSDs.

    Only one level up is added per mapping entry; the recursion
    terminates naturally because parent entries are themselves added
    to `matched` (and therefore to `seen`) during the same pass.
    """
    seen: set[tuple[str, str]] = set()
    for m in matched:
        sp = m.get("source_path", "")
        tp = m.get("target_path", "")
        if sp and tp:
            seen.add((sp, tp))

    to_add: list[dict] = []

    for m in list(matched):
        sp = m.get("source_path", "")
        tp = m.get("target_path", "")
        if not sp or not tp:
            continue                # skip concat / func entries

        sp_par = _get_parent(sp)
        tp_par = _get_parent(tp)

        if (
            sp_par and tp_par
            and sp_par in src_path_set
            and tp_par in tgt_path_set
        ):
            key = (sp_par, tp_par)
            if key not in seen:
                seen.add(key)
                to_add.append({
                    "source_path": sp_par,
                    "target_path": tp_par,
                    "note": "auto parent",
                })

    return matched + to_add


# ── Public API ────────────────────────────────────────────────────────────────

def parse_sheet(data: bytes, filename: str) -> list[dict]:
    """Public alias — parse a sheet file and return row dicts."""
    return _parse_sheet_rows(data, filename)


def sheet_to_field_mappings(
    sheet_data: bytes,
    filename: str,
    src_paths: list[str],
    tgt_paths: list[str],
) -> tuple[list[dict], list[dict]]:
    """
    Parse the mapping sheet and resolve field names to real XSD paths.

    Returns
    -------
    matched   list of field-mapping dicts ready for build_mmap_xml():
              • Simple:  {"source_path": "...", "target_path": "...", "note": ""}
              • Concat:  {"target_path": "...", "parts": [...], "note": "..."}
    unmatched list of rows that could not be resolved, with a reason.
    """
    sheet_rows  = _parse_sheet_rows(sheet_data, filename)
    src_path_set = set(src_paths)
    tgt_path_set = set(tgt_paths)

    matched:   list[dict] = []
    unmatched: list[dict] = []
    seen:      set[tuple] = set()

    # Track how many times each target field name has been used,
    # so successive occurrences in the sheet map to successive XSD paths.
    tgt_occ: dict[str, int] = {}

    for row in sheet_rows:
        src_field = row["source"]
        tgt_field = row["target"]
        rule      = row["rule"]

        if not tgt_field:
            continue

        # ── Resolve target path (Nth occurrence) ─────────────────────────────
        all_tgt = _match_all_fields(tgt_field, tgt_paths)
        occ     = tgt_occ.get(tgt_field, 0)
        tgt_path = all_tgt[occ] if occ < len(all_tgt) else (all_tgt[-1] if all_tgt else None)
        tgt_occ[tgt_field] = occ + 1

        if not tgt_path:
            unmatched.append({
                "source": src_field, "target": tgt_field,
                "rule": rule, "reason": "target not found in XSD",
            })
            continue

        # ── Try to parse a function rule ──────────────────────────────────────
        parsed_rule = _parse_rule(rule, src_paths) if rule else None

        if parsed_rule:
            func_name, func_parts = parsed_rule
            key = ("__func__", tgt_path, func_name)
            if key not in seen:
                seen.add(key)
                matched.append({
                    "target_path": tgt_path,
                    "func":        func_name,
                    "parts":       func_parts,
                    "note":        f"Rule: {rule}",
                })
            continue

        # ── Simple 1-to-1 ─────────────────────────────────────────────────────
        src_path:   str | None = None
        note_parts: list[str]  = []

        if src_field:
            src_path = _match_field(src_field, src_paths)

        # Fall back: mine a single source field from the rule
        if not src_path and rule:
            for fn in _source_fields_from_rule(rule):
                candidate = _match_field(fn, src_paths)
                if candidate:
                    src_path = candidate
                    note_parts.append(f"derived from rule: {rule}")
                    break

        if rule:
            note_parts.append(f"Rule: {rule}")

        if src_path:
            key = (src_path, tgt_path)
            if key not in seen:
                seen.add(key)
                matched.append({
                    "source_path": src_path,
                    "target_path": tgt_path,
                    "note": "; ".join(note_parts),
                })
        else:
            reason = (
                f"source '{src_field}' not found in XSD"
                if src_field
                else "no source field"
            )
            unmatched.append({
                "source": src_field, "target": tgt_field,
                "rule": rule, "reason": reason,
            })

    # ── Auto-add missing direct parent mappings ───────────────────────────────
    matched = _ensure_parent_mappings(matched, src_path_set, tgt_path_set)

    return matched, unmatched
