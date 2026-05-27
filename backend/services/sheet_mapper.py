"""
Mapping-sheet parser for SAP CPI .mmap generation.

Reads an Excel (.xlsx) or CSV (.csv) file whose rows describe how source
fields map to target fields, then resolves those short field names to full
XPath-style paths extracted from the uploaded XSDs.

Supported sheet column layouts (auto-detected by header keywords):
  • Source Field | [Description] | [Entity Set] | [Property] | Target Field | [Mapping Rule] | [Comment]
  • Any layout where at least one header contains "source" and one contains "target"
  • Fallback: column 0 = source, last column = target

Returns a list of {"source_path", "target_path", "note"} dicts ready for
build_mmap_xml().
"""

from __future__ import annotations

import io
import csv
import re
from pathlib import Path
from typing import Optional


# ── Excel / CSV readers ───────────────────────────────────────────────────────

def _rows_from_xlsx(data: bytes) -> list[list]:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        raise RuntimeError(
            "openpyxl is required for .xlsx support. "
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
    if ext in (".xls",):
        raise RuntimeError(
            ".xls format is not supported. Please save the file as .xlsx or .csv."
        )
    return _rows_from_csv(data)


# ── Column detection ──────────────────────────────────────────────────────────

def _detect_col(headers: list[str], keywords: list[str]) -> int:
    """Return index of first header that contains any keyword (case-insensitive)."""
    for i, h in enumerate(headers):
        if h and any(kw in h.lower() for kw in keywords):
            return i
    return -1


def _parse_sheet_rows(data: bytes, filename: str) -> list[dict]:
    """
    Parse a mapping sheet file and return a list of row dicts:
    {"source": str|None, "target": str|None, "rule": str|None}
    """
    rows = _rows_from_file(data, filename)
    if not rows:
        return []

    # --- Detect header row ---
    # Check if first row looks like a header (contains keyword "source" or "target")
    first_row_str = [str(c).strip() if c is not None else "" for c in rows[0]]
    has_header = _detect_col(first_row_str, ["source"]) >= 0 or \
                 _detect_col(first_row_str, ["target"]) >= 0

    if has_header:
        headers = first_row_str
        data_rows = rows[1:]
    else:
        # No header — assume col 0 = source, last col = target
        headers = []
        data_rows = rows

    if has_header:
        src_col  = _detect_col(headers, ["source field", "source"])
        tgt_col  = _detect_col(headers, ["target field", "target"])
        rule_col = _detect_col(headers, ["mapping rule", "rule", "formula", "function", "transform"])
    else:
        src_col  = 0
        tgt_col  = len(rows[0]) - 1
        rule_col = 2 if len(rows[0]) > 2 else -1

    # Default fallback if we somehow still have -1
    if src_col < 0:
        src_col = 0
    if tgt_col < 0:
        tgt_col = 1 if len(rows[0]) > 1 else 0

    results = []
    for row in data_rows:
        def _cell(idx: int) -> str | None:
            if idx < 0 or idx >= len(row):
                return None
            v = row[idx]
            if v is None:
                return None
            s = str(v).strip()
            return s or None

        src  = _cell(src_col)
        tgt  = _cell(tgt_col)
        rule = _cell(rule_col) if rule_col >= 0 else None

        if src or tgt:
            results.append({"source": src, "target": tgt, "rule": rule})

    return results


# ── Path matching ─────────────────────────────────────────────────────────────

def _last_seg(path: str) -> str:
    return path.rsplit("/", 1)[-1].lower()


def _match_field(field_name: str, paths: list[str]) -> str | None:
    """
    Find the best matching XPath-style path for a short field name.

    Priority:
    1. Exact case-insensitive match on the last path segment
    2. Exact match on any segment (for structural/container nodes —
       returns the path truncated up to that segment)
    """
    if not field_name:
        return None

    fn = field_name.strip().lower()

    # 1. Exact last-segment match
    for p in paths:
        if _last_seg(p) == fn:
            return p

    # 2. Match any segment (structural path)
    for p in paths:
        segs = p.split("/")  # e.g. ['', 'msg', 'body', 'stockreport']
        for i, s in enumerate(segs):
            if s.lower() == fn:
                # Truncate path to this segment
                return "/".join(segs[: i + 1]) or p

    return None


def _source_fields_from_rule(rule: str) -> list[str]:
    """
    Extract field/path references from a mapping rule expression.
    Example: "(/msg/header/date)+T+(/msg/header/time)" -> ["date", "time"]
             "header.date"                              -> ["date"]
    """
    refs: list[str] = []
    # Bracketed XPath-like references: (/msg/header/date)
    for m in re.findall(r'\((/[^)]+)\)', rule):
        refs.append(m.strip("/").rsplit("/", 1)[-1])
    if not refs:
        # Dot-notation: header.date -> date
        for token in re.split(r'[^a-zA-Z0-9_./]', rule):
            token = token.strip().strip("/")
            if token:
                refs.append(token.rsplit(".", 1)[-1].rsplit("/", 1)[-1])
    return [r for r in refs if r]


# ── Public entry point ────────────────────────────────────────────────────────

def parse_sheet(data: bytes, filename: str) -> list[dict]:
    """Public alias for _parse_sheet_rows — parse a sheet and return row dicts."""
    return _parse_sheet_rows(data, filename)


def sheet_to_field_mappings(
    sheet_data: bytes,
    filename: str,
    src_paths: list[str],
    tgt_paths: list[str],
) -> tuple[list[dict], list[dict]]:
    """
    Parse the mapping sheet and resolve field names to real XSD paths.

    Args:
        sheet_data:  raw bytes of the uploaded .xlsx / .csv file
        filename:    original filename (used to detect format)
        src_paths:   all paths from the source XSD (smart_extract_paths result)
        tgt_paths:   all paths from the target XSD

    Returns:
        (matched, unmatched)
        matched   — list of {"source_path", "target_path", "note"}
        unmatched — list of {"source", "target", "rule", "reason"}
    """
    sheet_rows = _parse_sheet_rows(sheet_data, filename)

    matched: list[dict] = []
    unmatched: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for row in sheet_rows:
        src_field = row["source"]
        tgt_field = row["target"]
        rule      = row["rule"]

        # Every row must have a target
        if not tgt_field:
            continue

        # --- Resolve target path ---
        tgt_path = _match_field(tgt_field, tgt_paths)
        if not tgt_path:
            # Can't map without a real target path — record and skip
            unmatched.append({
                "source": src_field, "target": tgt_field,
                "rule": rule, "reason": "target not found in XSD",
            })
            continue

        # --- Resolve source path ---
        src_path: str | None = None
        note_parts: list[str] = []

        if src_field:
            src_path = _match_field(src_field, src_paths)

        # If rule present and source wasn't directly found, mine the rule
        if not src_path and rule:
            for fn in _source_fields_from_rule(rule):
                candidate = _match_field(fn, src_paths)
                if candidate:
                    src_path = candidate
                    note_parts.append(f"derived from rule: {rule}")
                    break

        if rule:
            note_parts.append(f"Rule: {rule}")

        # --- Decide outcome ---
        if src_path:
            key = (src_path, tgt_path)
            if key not in seen:
                seen.add(key)
                matched.append({
                    "source_path": src_path,
                    "target_path": tgt_path,
                    "note":        "; ".join(note_parts),
                })
        else:
            # No source path resolvable
            reason = (
                f"source '{src_field}' not found in XSD"
                if src_field
                else "no source field"
            )
            unmatched.append({
                "source": src_field, "target": tgt_field,
                "rule": rule, "reason": reason,
            })

    return matched, unmatched
