"""
Generates the SAP CPI Mapping Sheet Excel template using xlsxwriter.

The template has three worksheets:
  1. Mapping Sheet  — data-entry sheet with Source, Target, Functional Rule,
                      Technical Rule, and Notes columns.
  2. Function Ref   — full reference of every supported CPI node-function
                      expression with a plain-English description and example.
  3. Instructions   — step-by-step guide for functional and technical users.
"""

from __future__ import annotations

import io
import xlsxwriter


# ── Node-function reference rows ──────────────────────────────────────────────

FUNCTION_REFERENCE = [
    # (Category, Function, CPI Expression Syntax, Functional Description, Example)
    ("String", "Direct copy",
     "(leave Technical Rule blank)",
     "Copy value from source field directly to target — no transformation",
     "Source: MaterialNumber → Target: MATNR"),

    ("String", "toUpperCase",
     "toUpperCase((/path/to/SourceField))",
     "Convert text to ALL UPPER CASE",
     "toUpperCase((/Header/Sender)) → 'sap system' becomes 'SAP SYSTEM'"),

    ("String", "toLowerCase",
     "toLowerCase((/path/to/SourceField))",
     "Convert text to all lower case",
     "toLowerCase((/Header/SenderId)) → 'SAP' becomes 'sap'"),

    ("String", "trim",
     "trim((/path/to/SourceField))",
     "Remove leading and trailing whitespace from a text value",
     "trim((/Header/Name)) → '  John  ' becomes 'John'"),

    ("String", "concat (shorthand)",
     "(/path/Field1)+SEPARATOR+(/path/Field2)",
     "Join two or more fields with a constant separator",
     "(/Header/Date)+T+(/Header/Time) → '20240101T120000'"),

    ("String", "concat (explicit)",
     "concat((/path/Field1), SEPARATOR, (/path/Field2))",
     "Join fields/constants — more readable than shorthand for many args",
     "concat((/Header/CompCode), -, (/Header/Plant)) → '1000-PLT1'"),

    ("String", "substring",
     "substring((/path/to/SourceField), startIndex, length)",
     "Extract a portion of text — index starts at 0",
     "substring((/Header/DocNo), 0, 6) → first 6 characters"),

    ("String", "length",
     "length((/path/to/SourceField))",
     "Return the number of characters in a text value",
     "length((/Header/MaterialNo)) → '18' (the length)"),

    ("String", "replaceAll",
     "replaceAll((/path/to/SourceField), REGEX_PATTERN, REPLACEMENT)",
     "Replace all occurrences matching a regex pattern with a replacement text",
     "replaceAll((/Header/Phone), [^0-9], ) → removes non-digit chars"),

    ("String", "splitByValue",
     "splitByValue((/path/to/SourceField), DELIMITER)",
     "Split a field value by a delimiter into multiple output occurrences",
     "splitByValue((/Header/Tags), ,) → splits comma-separated list"),

    ("Date", "formatDate",
     "formatDate((/path/to/DateField), INPUT_FORMAT, OUTPUT_FORMAT)",
     "Reformat a date/time string from one pattern to another",
     "formatDate((/Header/DocDate), yyyyMMdd, yyyy-MM-dd) → '20240101' becomes '2024-01-01'"),

    ("Logic", "if + equals",
     "if(equals((/path/to/Field), COMPARE_VALUE), TRUE_VALUE, FALSE_VALUE)",
     "If field equals a value, output TRUE_VALUE; otherwise output FALSE_VALUE",
     "if(equals((/Header/Type), PO), Purchase Order, Sales Order)"),

    ("Logic", "if + contains",
     "if(contains((/path/to/Field), SEARCH_TEXT), TRUE_VALUE, FALSE_VALUE)",
     "If field contains a substring, output TRUE_VALUE; otherwise FALSE_VALUE",
     "if(contains((/Header/DocType), RE), Returns, Normal)"),

    ("Lookup", "mapWithDefault",
     "mapWithDefault((/path/to/Field), Key1, Value1, Key2, Value2, ..., DEFAULT)",
     "Map specific field values to new values, with a fallback default",
     "mapWithDefault((/Header/Status), A, Active, I, Inactive, Unknown)"),

    ("Occurrence", "UseOneAsMany",
     "UseOneAsMany((/path/to/SourceField))",
     "Repeat a single source value for each occurrence in the target structure",
     "UseOneAsMany((/Header/Currency)) → repeats currency for every line item"),

    ("Occurrence", "UseOneAsMany (constant)",
     "UseOneAsMany(CONSTANT_VALUE)",
     "Repeat a fixed constant for each occurrence in the target structure",
     "UseOneAsMany(EUR) → always outputs 'EUR' for every line item"),
]

# ── Example rows for the Mapping Sheet ────────────────────────────────────────

EXAMPLE_ROWS = [
    # (Source Field, Target Field, Functional Rule, Technical Rule, Notes)
    ("MaterialNumber", "MATNR",
     "Direct copy — material number maps 1-to-1",
     "",
     "Leave Technical Rule blank for direct copy"),

    ("BaseUnit", "MEINS",
     "Convert UoM code to uppercase",
     "toUpperCase((/MaterialNumber/BaseUnit))",
     ""),

    ("CreationDate", "ERSDA",
     "Reformat date from YYYY-MM-DD to YYYYMMDD",
     "formatDate((/MaterialNumber/CreationDate), yyyy-MM-dd, yyyyMMdd)",
     ""),

    ("Plant + StorageLocation", "LGORT",
     "Concatenate Plant and StorageLocation with underscore separator",
     "(/Stock/Plant)+_+(/Stock/StorageLocation)",
     ""),

    ("MaterialGroup", "MATKL",
     "Map: 'ROH' → 'Raw', 'HALB' → 'Semi', default 'Finished'",
     "mapWithDefault((/MaterialNumber/MaterialGroup), ROH, Raw, HALB, Semi, Finished)",
     ""),

    ("Description", "MAKTX",
     "Trim whitespace from description text",
     "trim((/MaterialNumber/Description))",
     ""),

    ("", "", "", "", ""),  # blank row for visual separation
    ("YourSourceField", "YourTargetField",
     "Write your functional rule here in plain English",
     "",
     "Leave Technical Rule blank — AI will derive it on upload"),
]


# ── Workbook builder ──────────────────────────────────────────────────────────

def build_template_bytes() -> bytes:
    """Build the Excel template and return the raw bytes."""

    buf = io.BytesIO()
    wb  = xlsxwriter.Workbook(buf, {"in_memory": True})

    _build_mapping_sheet(wb)
    _build_function_ref_sheet(wb)
    _build_instructions_sheet(wb)

    wb.close()
    return buf.getvalue()


# ── Sheet 1: Mapping Sheet ────────────────────────────────────────────────────

_COL_HEADERS = [
    "#",
    "Source Field",
    "Target Field",
    "Functional Mapping Rule",
    "Technical Mapping Rule",
    "Notes",
]
_COL_WIDTHS = [4, 22, 22, 45, 52, 30]

def _build_mapping_sheet(wb: xlsxwriter.Workbook) -> None:
    ws = wb.add_worksheet("Mapping Sheet")
    ws.set_zoom(100)
    ws.freeze_panes(5, 0)          # freeze above header row

    # ── Formats ───────────────────────────────────────────────────────────────
    title_fmt = wb.add_format({
        "bold": True, "font_size": 14, "font_color": "#FFFFFF",
        "bg_color": "#1B4F72", "border": 0, "valign": "vcenter",
    })
    subtitle_fmt = wb.add_format({
        "italic": True, "font_size": 9, "font_color": "#7F8C8D",
        "bg_color": "#FAFAFA",
    })
    hdr_base = {"bold": True, "font_color": "#FFFFFF", "border": 1,
                 "border_color": "#AAAAAA", "valign": "vcenter", "align": "center",
                 "font_size": 9}
    hdr_num  = wb.add_format({**hdr_base, "bg_color": "#5D6D7E"})
    hdr_src  = wb.add_format({**hdr_base, "bg_color": "#1A5276"})   # dark blue
    hdr_tgt  = wb.add_format({**hdr_base, "bg_color": "#145A32"})   # dark green
    hdr_func = wb.add_format({**hdr_base, "bg_color": "#7D3C98"})   # purple
    hdr_tech = wb.add_format({**hdr_base, "bg_color": "#1A5276"})   # blue
    hdr_note = wb.add_format({**hdr_base, "bg_color": "#5D6D7E"})   # gray

    num_fmt  = wb.add_format({"align": "center", "font_color": "#999999",
                               "border": 1, "border_color": "#DDDDDD", "font_size": 9})
    src_fmt  = wb.add_format({"bg_color": "#EBF5FB", "border": 1,
                               "border_color": "#AED6F1", "font_size": 9,
                               "font_name": "Courier New"})
    tgt_fmt  = wb.add_format({"bg_color": "#EAFAF1", "border": 1,
                               "border_color": "#A9DFBF", "font_size": 9,
                               "font_name": "Courier New"})
    func_fmt = wb.add_format({"bg_color": "#F5EEF8", "border": 1,
                               "border_color": "#D7BDE2", "font_size": 9,
                               "italic": True, "text_wrap": True})
    tech_fmt = wb.add_format({"bg_color": "#EBF5FB", "border": 1,
                               "border_color": "#AED6F1", "font_size": 9,
                               "font_name": "Courier New", "font_color": "#154360"})
    note_fmt = wb.add_format({"bg_color": "#FDFEFE", "border": 1,
                               "border_color": "#DDDDDD", "font_size": 9,
                               "font_color": "#7F8C8D", "italic": True})
    blank_src  = wb.add_format({"bg_color": "#EBF5FB", "border": 1,
                                 "border_color": "#AED6F1", "font_name": "Courier New",
                                 "font_size": 9})
    blank_tgt  = wb.add_format({"bg_color": "#EAFAF1", "border": 1,
                                 "border_color": "#A9DFBF", "font_name": "Courier New",
                                 "font_size": 9})
    blank_func = wb.add_format({"bg_color": "#F5EEF8", "border": 1,
                                 "border_color": "#D7BDE2", "font_size": 9})
    blank_tech = wb.add_format({"bg_color": "#EBF5FB", "border": 1,
                                 "border_color": "#AED6F1", "font_name": "Courier New",
                                 "font_size": 9})
    blank_note = wb.add_format({"bg_color": "#FDFEFE", "border": 1,
                                 "border_color": "#DDDDDD", "font_size": 9})
    label_fmt  = wb.add_format({"bold": True, "font_size": 8,
                                 "font_color": "#FFFFFF", "bg_color": "#1B4F72",
                                 "border": 1, "border_color": "#AAAAAA"})

    # ── Column widths ─────────────────────────────────────────────────────────
    for i, w in enumerate(_COL_WIDTHS):
        ws.set_column(i, i, w)
    ws.set_row(0, 28)   # title row
    ws.set_row(1, 16)   # subtitle
    ws.set_row(2, 6)    # spacer
    ws.set_row(3, 22)   # legend / sub-headers
    ws.set_row(4, 20)   # column headers

    # ── Row 0: Title ──────────────────────────────────────────────────────────
    ws.merge_range("A1:F1", "SAP CPI Message Mapping Template", title_fmt)

    # ── Row 1: Subtitle ───────────────────────────────────────────────────────
    ws.merge_range("A2:F2",
        "Fill in Source Field, Target Field and Functional Rule. "
        "Upload to SAP CPI Assistant → the AI will derive Technical Rules automatically.",
        subtitle_fmt)

    # ── Row 2: Spacer (empty) ─────────────────────────────────────────────────
    ws.merge_range("A3:F3", "", wb.add_format({"bg_color": "#FAFAFA"}))

    # ── Row 3: Column colour legend ───────────────────────────────────────────
    ws.write(3, 0, "",      label_fmt)
    ws.write(3, 1, "REQUIRED — fill source field name or XPath", wb.add_format({
        "bold": True, "font_size": 8, "font_color": "#154360",
        "bg_color": "#D6EAF8", "border": 1, "border_color": "#AED6F1"}))
    ws.write(3, 2, "REQUIRED — fill target field name or XPath", wb.add_format({
        "bold": True, "font_size": 8, "font_color": "#1D6A39",
        "bg_color": "#D5F5E3", "border": 1, "border_color": "#A9DFBF"}))
    ws.write(3, 3, "RECOMMENDED — describe the mapping in plain English (functional person fills this)", wb.add_format({
        "bold": True, "font_size": 8, "font_color": "#5B2C6F",
        "bg_color": "#EBD7F5", "border": 1, "border_color": "#D7BDE2"}))
    ws.write(3, 4, "OPTIONAL — CPI node function expression (AI derives from Functional Rule if blank)", wb.add_format({
        "bold": True, "font_size": 8, "font_color": "#154360",
        "bg_color": "#D6EAF8", "border": 1, "border_color": "#AED6F1"}))
    ws.write(3, 5, "Optional notes", wb.add_format({
        "bold": True, "font_size": 8, "font_color": "#5D6D7E",
        "bg_color": "#F2F3F4", "border": 1, "border_color": "#DDDDDD"}))

    # ── Row 4: Column headers ─────────────────────────────────────────────────
    hdr_fmts = [hdr_num, hdr_src, hdr_tgt, hdr_func, hdr_tech, hdr_note]
    for col, (label, fmt) in enumerate(zip(_COL_HEADERS, hdr_fmts)):
        ws.write(4, col, label, fmt)

    # ── Data rows: examples ───────────────────────────────────────────────────
    for row_i, (src, tgt, func, tech, note) in enumerate(EXAMPLE_ROWS):
        row = 5 + row_i
        ws.set_row(row, 18)
        if not any([src, tgt, func, tech, note]):
            # blank separator row
            for c, f in enumerate([num_fmt, blank_src, blank_tgt, blank_func, blank_tech, blank_note]):
                ws.write(row, c, "", f)
            continue
        ws.write(row, 0, row_i + 1, num_fmt)
        ws.write(row, 1, src,  src_fmt)
        ws.write(row, 2, tgt,  tgt_fmt)
        ws.write(row, 3, func, func_fmt)
        ws.write(row, 4, tech, tech_fmt)
        ws.write(row, 5, note, note_fmt)

    # ── 50 blank user rows ────────────────────────────────────────────────────
    user_start = 5 + len(EXAMPLE_ROWS)
    for i in range(50):
        row = user_start + i
        ws.set_row(row, 18)
        ws.write(row, 0, i + 1, num_fmt)
        ws.write(row, 1, "", blank_src)
        ws.write(row, 2, "", blank_tgt)
        ws.write(row, 3, "", blank_func)
        ws.write(row, 4, "", blank_tech)
        ws.write(row, 5, "", blank_note)

    # ── Tab colour ────────────────────────────────────────────────────────────
    ws.set_tab_color("#1B4F72")


# ── Sheet 2: Function Reference ───────────────────────────────────────────────

def _build_function_ref_sheet(wb: xlsxwriter.Workbook) -> None:
    ws = wb.add_worksheet("Function Reference")
    ws.set_zoom(95)

    title_fmt = wb.add_format({
        "bold": True, "font_size": 13, "font_color": "#FFFFFF",
        "bg_color": "#512E5F", "border": 0,
    })
    cat_fmt = wb.add_format({
        "bold": True, "font_size": 9, "font_color": "#FFFFFF",
        "bg_color": "#7D3C98", "border": 1, "border_color": "#AAAAAA",
    })
    func_fmt = wb.add_format({
        "bold": True, "font_size": 9, "font_color": "#154360",
        "bg_color": "#D6EAF8", "border": 1, "border_color": "#AED6F1",
    })
    syntax_fmt = wb.add_format({
        "font_size": 9, "font_color": "#154360",
        "bg_color": "#EBF5FB", "border": 1, "border_color": "#AED6F1",
        "font_name": "Courier New", "text_wrap": True,
    })
    plain_fmt = wb.add_format({
        "font_size": 9, "bg_color": "#F5EEF8", "border": 1,
        "border_color": "#D7BDE2", "text_wrap": True, "italic": True,
    })
    ex_fmt = wb.add_format({
        "font_size": 8, "font_color": "#145A32", "bg_color": "#EAFAF1",
        "border": 1, "border_color": "#A9DFBF",
        "font_name": "Courier New", "text_wrap": True,
    })

    ws.set_column(0, 0, 12)   # Category
    ws.set_column(1, 1, 20)   # Function
    ws.set_column(2, 2, 50)   # CPI Expression Syntax
    ws.set_column(3, 3, 40)   # Functional Description
    ws.set_column(4, 4, 55)   # Example
    ws.set_row(0, 26)
    ws.set_row(1, 18)

    ws.merge_range("A1:E1", "SAP CPI Node Function Reference", title_fmt)

    # Headers
    for col, hdr in enumerate(["Category", "Function Name",
                                "CPI Expression Syntax",
                                "Functional Description (plain English)",
                                "Example"]):
        ws.write(1, col, hdr, wb.add_format({
            "bold": True, "font_color": "#FFFFFF", "bg_color": "#2C3E50",
            "border": 1, "border_color": "#AAAAAA", "font_size": 9,
        }))

    for row_i, (cat, func, syntax, plain, ex) in enumerate(FUNCTION_REFERENCE):
        row = 2 + row_i
        ws.set_row(row, 36)
        ws.write(row, 0, cat,    cat_fmt)
        ws.write(row, 1, func,   func_fmt)
        ws.write(row, 2, syntax, syntax_fmt)
        ws.write(row, 3, plain,  plain_fmt)
        ws.write(row, 4, ex,     ex_fmt)

    ws.set_tab_color("#512E5F")


# ── Sheet 3: Instructions ─────────────────────────────────────────────────────

def _build_instructions_sheet(wb: xlsxwriter.Workbook) -> None:
    ws = wb.add_worksheet("Instructions")
    ws.set_column(0, 0, 5)
    ws.set_column(1, 1, 100)

    title_fmt = wb.add_format({
        "bold": True, "font_size": 13, "font_color": "#FFFFFF",
        "bg_color": "#1B4F72",
    })
    h1_fmt = wb.add_format({
        "bold": True, "font_size": 11, "font_color": "#FFFFFF",
        "bg_color": "#1A5276",
    })
    h2_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_color": "#154360",
        "bg_color": "#D6EAF8",
    })
    body_fmt = wb.add_format({"font_size": 9, "text_wrap": True})
    bullet_fmt = wb.add_format({"font_size": 9, "text_wrap": True, "indent": 2})
    code_fmt = wb.add_format({
        "font_size": 9, "font_name": "Courier New",
        "bg_color": "#F2F3F4", "text_wrap": True,
    })
    tip_fmt = wb.add_format({
        "font_size": 9, "italic": True, "font_color": "#1D6A39",
        "bg_color": "#D5F5E3", "text_wrap": True,
    })

    lines = [
        ("title", "SAP CPI Message Mapping — Template Guide"),
        ("", ""),
        ("h1", "FOR FUNCTIONAL CONSULTANTS"),
        ("h2", "What you need to fill:"),
        ("body", "Column B — Source Field: The source field name (e.g. MaterialNumber, CreationDate). Use the exact field name as it appears in the source system XML/XSD."),
        ("body", "Column C — Target Field: The target field name (e.g. MATNR, ERSDA). Use the exact field name as it appears in the target XSD."),
        ("body", "Column D — Functional Mapping Rule: Describe HOW the mapping works in plain English. Examples:"),
        ("bullet", '"Direct copy — no transformation needed"'),
        ("bullet", '"Convert date from YYYYMMDD to YYYY-MM-DD format"'),
        ("bullet", '"Concatenate Sender ID and Company Code separated by a hyphen"'),
        ("bullet", '"Map values: A=Active, I=Inactive, anything else=Unknown"'),
        ("bullet", '"Convert the amount to uppercase text"'),
        ("body", "Column E — Technical Mapping Rule: Leave blank. The SAP CPI Assistant AI will auto-derive this from your Functional Rule description when you upload the sheet."),
        ("body", "Column F — Notes: Any additional context, edge cases, or comments for the technical team."),
        ("tip", "TIP: You do NOT need to know CPI expressions. Just describe the business logic clearly in Column D."),
        ("", ""),
        ("h1", "FOR TECHNICAL DEVELOPERS"),
        ("h2", "Technical Rule column syntax:"),
        ("body", "You can fill Column E directly with CPI node function expressions if you prefer. Supported syntax:"),
        ("code", "Direct copy:          (leave blank — no expression needed)"),
        ("code", "Concat shorthand:     (/path/Field1)+SEPARATOR+(/path/Field2)"),
        ("code", "Concat explicit:      concat((/Field1), SEP, (/Field2))"),
        ("code", "Uppercase:            toUpperCase((/path/to/Field))"),
        ("code", "Date reformat:        formatDate((/DateField), yyyyMMdd, yyyy-MM-dd)"),
        ("code", "Value lookup:         mapWithDefault((/Field), A, Active, I, Inactive, Unknown)"),
        ("code", "Conditional:          if(equals((/Type), PO), Purchase, Sales)"),
        ("code", "Regex replace:        replaceAll((/Field), [^0-9], )"),
        ("code", "Substring:            substring((/Field), 0, 6)"),
        ("body", "See the 'Function Reference' sheet for the full list of supported functions."),
        ("", ""),
        ("h1", "UPLOAD STEPS"),
        ("body", "1. Fill in your mapping rows (Source Field, Target Field, Functional Rule at minimum)."),
        ("body", "2. Go to SAP CPI Assistant → Message Mapping → Sheet Mapping tab."),
        ("body", "3. Upload your Source XSD, Target XSD, and this mapping sheet."),
        ("body", "4. Click 'Preview' to see how fields are matched to XSD paths."),
        ("body", "5. Click 'AI Derive Rules' — the AI will fill Technical Rules from your Functional descriptions."),
        ("body", "6. Review the preview table. Fix any unmatched fields by adjusting field names."),
        ("body", "7. Click 'Generate .mmap' to download the ready-to-import CPI mapping file."),
        ("tip", "TIP: Field names are matched case-insensitively and partially. 'MatNum' will match 'MaterialNumber' if it's the closest fit."),
        ("", ""),
        ("h1", "TIPS FOR BETTER MATCHING"),
        ("bullet", "Use the exact last segment of the XPath — e.g. 'MaterialNumber' not '/root/header/MaterialNumber'"),
        ("bullet", "For ambiguous names, paste the full XPath — e.g. /MaterialMaster/Header/MaterialNumber"),
        ("bullet", "If a target field appears multiple times in the XSD, list it on separate rows in the order you want them mapped"),
        ("bullet", "Constants in rules do NOT use parentheses — e.g. write EUR not (/EUR)"),
    ]

    row = 0
    for (kind, text) in lines:
        ws.set_row(row, 20 if kind in ("h1", "h2", "title") else 16 if kind == "" else None)
        if kind == "title":
            ws.merge_range(row, 0, row, 1, text, title_fmt)
        elif kind == "h1":
            ws.merge_range(row, 0, row, 1, text, h1_fmt)
        elif kind == "h2":
            ws.merge_range(row, 0, row, 1, text, h2_fmt)
        elif kind == "body":
            ws.merge_range(row, 0, row, 1, text, body_fmt)
        elif kind == "bullet":
            ws.write(row, 0, "•", bullet_fmt)
            ws.write(row, 1, text, bullet_fmt)
        elif kind == "code":
            ws.merge_range(row, 0, row, 1, text, code_fmt)
        elif kind == "tip":
            ws.merge_range(row, 0, row, 1, text, tip_fmt)
        else:
            ws.merge_range(row, 0, row, 1, "", body_fmt)
        row += 1

    ws.set_tab_color("#1D6A39")
