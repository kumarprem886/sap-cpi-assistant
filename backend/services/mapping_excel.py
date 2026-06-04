"""
Generate a mapping specification Excel (.xlsx) from a CPI iFlow ZIP.
Format mirrors the sample: Overview header + Definition (Target | Source | Type).
"""
import io, re, zipfile


def _parse_mmap_xml(mmap_xml: str) -> list[tuple[str, str]]:
    """
    Extract (target_path, source_path) pairs from an SAP .mmap XML.
    Each <brick type="Dst"> that contains a direct <brick type="Src"> child
    represents a 1-to-1 field mapping.
    """
    pairs: list[tuple[str, str]] = []

    # Match every <brick ... type="Dst" ...> block (non-greedy, handles nesting)
    # The mmap XML is flat enough for regex extraction on the brick elements.
    dst_pattern = re.compile(
        r'<brick\b[^>]*\bpath="([^"]+)"[^>]*\btype="Dst"[^>]*>(.*?)</brick>',
        re.DOTALL,
    )
    src_pattern = re.compile(r'<brick\b[^>]*\bpath="([^"]+)"[^>]*\btype="Src"')

    for m in dst_pattern.finditer(mmap_xml):
        dst_path = m.group(1)
        body     = m.group(2)
        # Find the FIRST <arg> child's <brick type="Src">
        arg_m = re.search(r'<arg>(.*?)</arg>', body, re.DOTALL)
        if not arg_m:
            continue
        src_m = src_pattern.search(arg_m.group(1))
        src_path = src_m.group(1) if src_m else ''
        pairs.append((dst_path, src_path))

    return pairs


def generate_mapping_excel(iflow_zip_bytes: bytes) -> tuple[bytes, str] | None:
    """
    Parse the iFlow ZIP, find the .mmap file, and generate an Excel mapping spec.
    Returns (xlsx_bytes, filename) or None if no .mmap found.
    """
    try:
        import openpyxl
        from openpyxl.styles import (Font, PatternFill, Alignment,
                                      Border, Side)
    except ImportError:
        return None

    with zipfile.ZipFile(io.BytesIO(iflow_zip_bytes)) as z:
        files = z.namelist()
        mmap_files = [f for f in files if f.endswith('.mmap')]
        if not mmap_files:
            return None

        mmap_path  = mmap_files[0]
        mmap_name  = mmap_path.split('/')[-1].replace('.mmap', '')
        mmap_xml   = z.read(mmap_path).decode('utf-8', 'replace')

        # Try to get XSD names
        xsd_files = [f.split('/')[-1] for f in files if f.endswith('.xsd')]

    # Parse mapping pairs
    pairs = _parse_mmap_xml(mmap_xml)

    # ── Build workbook ──────────────────────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Overview"

    # ── Styles ──────────────────────────────────────────────────────────────
    SAP_BLUE  = "006DB3"
    SAP_DARK  = "1A1A2E"
    HDR_FILL  = PatternFill("solid", fgColor=SAP_DARK)
    SECT_FILL = PatternFill("solid", fgColor=SAP_BLUE)
    COL_FILL  = PatternFill("solid", fgColor="2C3E6B")
    EVEN_FILL = PatternFill("solid", fgColor="EEF2F7")
    ODD_FILL  = PatternFill("solid", fgColor="FFFFFF")
    WHITE_FT  = Font(color="FFFFFF", bold=True, name="Calibri", size=10)
    BOLD_FT   = Font(bold=True, name="Calibri", size=10)
    NORM_FT   = Font(name="Calibri", size=9)
    CENTER    = Alignment(horizontal="center", vertical="center", wrap_text=True)
    LEFT      = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    thin      = Side(style="thin", color="CCCCCC")
    BORDER    = Border(left=thin, right=thin, top=thin, bottom=thin)

    def _hdr(row, col, val, fill=HDR_FILL, ft=WHITE_FT, al=LEFT):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = fill; c.font = ft; c.alignment = al; c.border = BORDER

    def _cell(row, col, val, fill=ODD_FILL, ft=NORM_FT, al=LEFT):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = fill; c.font = ft; c.alignment = al; c.border = BORDER

    # ── Row 1: Title ────────────────────────────────────────────────────────
    ws.merge_cells("A1:C1")
    c = ws.cell(row=1, column=1, value="OVERVIEW")
    c.fill = HDR_FILL; c.font = Font(color="FFFFFF", bold=True, size=13, name="Calibri")
    c.alignment = CENTER; c.border = BORDER

    # ── Row 2: Column headers ───────────────────────────────────────────────
    _hdr(2, 1, "PARAMETER", COL_FILL); _hdr(2, 2, "VALUE", COL_FILL); _hdr(2, 3, "", COL_FILL)

    # ── Rows 3-8: Metadata ──────────────────────────────────────────────────
    meta = [
        ("Name of Mapping",           f"{mmap_name}.mmap"),
        ("Description",               ""),
        ("Name of the Source Messages", ""),
        ("Name of the Source Files",   ", ".join(xsd_files) if xsd_files else ""),
        ("Name of the Target Messages", ""),
        ("Name of the Target Files",   ", ".join(xsd_files) if xsd_files else ""),
    ]
    for i, (label, value) in enumerate(meta):
        row = 3 + i
        fill = EVEN_FILL if i % 2 == 0 else ODD_FILL
        _cell(row, 1, label, fill=fill, ft=BOLD_FT)
        _cell(row, 2, value, fill=fill)
        _cell(row, 3, "",    fill=fill)

    # ── Row 9: blank separator ──────────────────────────────────────────────
    ws.row_dimensions[9].height = 6

    # ── Row 10: DEFINITION heading ──────────────────────────────────────────
    ws.merge_cells("A10:C10")
    c = ws.cell(row=10, column=1, value="DEFINITION")
    c.fill = SECT_FILL; c.font = WHITE_FT; c.alignment = CENTER; c.border = BORDER

    # ── Row 11: Column headers ──────────────────────────────────────────────
    _hdr(11, 1, "TARGET",  COL_FILL, al=CENTER)
    _hdr(11, 2, "MAPPING (SOURCE)", COL_FILL, al=CENTER)
    _hdr(11, 3, "TYPE",    COL_FILL, al=CENTER)

    # ── Rows 12+: Mapping pairs ─────────────────────────────────────────────
    for i, (dst, src) in enumerate(pairs):
        row  = 12 + i
        fill = EVEN_FILL if i % 2 == 0 else ODD_FILL
        _cell(row, 1, dst, fill=fill)
        _cell(row, 2, src, fill=fill)
        _cell(row, 3, "",  fill=fill)

    # ── Column widths ────────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 55
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 12

    # ── Row heights ──────────────────────────────────────────────────────────
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 16
    ws.row_dimensions[10].height = 18
    ws.row_dimensions[11].height = 16

    # Freeze header rows
    ws.freeze_panes = "A12"

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    return xlsx_bytes, f"{mmap_name}_MappingSpec.xlsx"
