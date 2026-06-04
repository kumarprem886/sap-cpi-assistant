"""
update_td_with_iflow: Updates an existing TD document with iFlow ZIP data.
- Copies Appendix data to main body tables
- Overrides iFlow-specific fields from the actual ZIP
- Adds iFlow design steps section
- Adds message mapping field table
- Adds SAP-themed diagram
ZERO AI — 100% deterministic.
"""

import io, re, zipfile
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from services.flowchart_builder import generate_flowchart

# ── Colour helpers ────────────────────────────────────────────────────────────
SAP_BLUE = RGBColor(0x00, 0x6D, 0xB3)
SAP_DARK = RGBColor(0x1A, 0x1A, 0x2E)
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
AMBER    = RGBColor(0xCC, 0x77, 0x00)
MID_GREY = RGBColor(0x55, 0x60, 0x70)
GREEN    = RGBColor(0x1A, 0x8A, 0x5A)
RED_C    = RGBColor(0xC0, 0x2C, 0x2C)


def _shd(cell, hex_color):
    tc = cell._tc; p = tc.get_or_add_tcPr()
    s = OxmlElement("w:shd")
    s.set(qn("w:fill"), hex_color); s.set(qn("w:color"), "auto"); s.set(qn("w:val"), "clear")
    p.append(s)


def _set_cell(cell, text, bold=False, color=None):
    """Set cell text, preserve existing formatting where possible."""
    para = cell.paragraphs[0]
    for run in para.runs:
        run.text = ""
    if not para.runs:
        run = para.add_run()
    else:
        run = para.runs[0]
    run.text = str(text)
    run.font.size = Pt(9)
    run.font.bold = bold
    if color: run.font.color.rgb = color


def _norm(text):
    """Normalize label text for matching."""
    return re.sub(r'[^a-z0-9]', '', text.lower())[:30]


def _extract_iflow_facts(zip_bytes: bytes) -> dict:
    """Extract all key facts from the iFlow ZIP."""
    facts = {
        'iflow_name': '',
        'iflow_symbolic': '',
        'iflow_version': '',
        'description': '',
        'package': '',
        'mmap_name': '',
        'mmap_dst_fields': [],
        'mmap_src_fields': [],
        'mmap_xml': '',
        'steps': [],
        'adapters': [],
        'participants': [],
        'scripts': {},
        'parameters': [],
        'xsd_files': [],
    }

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        files = z.namelist()

        # MANIFEST.MF
        for fn in files:
            if 'MANIFEST.MF' in fn:
                mf = z.read(fn).decode('utf-8', 'replace')
                bn = re.search(r'^Bundle-Name:\s*(.+)', mf, re.MULTILINE)
                bs = re.search(r'^Bundle-SymbolicName:\s*(.+)', mf, re.MULTILINE)
                bv = re.search(r'^Bundle-Version:\s*(.+)', mf, re.MULTILINE)
                facts['iflow_name']     = _join_wrapped(bn.group(1).strip() if bn else '')
                facts['iflow_symbolic'] = _join_wrapped(bs.group(1).strip() if bs else '')
                facts['iflow_version']  = bv.group(1).strip() if bv else ''
                break

        # metainfo.prop
        for fn in files:
            if 'metainfo.prop' in fn:
                mp = z.read(fn).decode('utf-8', 'replace')
                for line in mp.splitlines():
                    if line.startswith('description='):
                        facts['description'] = line[12:].strip()

        # parameters.propdef
        for fn in files:
            if fn.endswith('.propdef'):
                raw = z.read(fn).decode('utf-8', 'replace')
                for m in re.finditer(r'<parameter>(.*?)</parameter>', raw, re.DOTALL):
                    blk = m.group(1)
                    nm  = re.search(r'<name>([^<]+)</name>', blk)
                    dsc = re.search(r'<description>([^<]+)</description>', blk)
                    req = re.search(r'<isRequired>([^<]+)</isRequired>', blk)
                    if nm:
                        facts['parameters'].append({
                            'name': nm.group(1).strip(),
                            'description': dsc.group(1).strip() if dsc else '',
                            'required': req.group(1).strip().lower() == 'true' if req else False,
                        })

        # Groovy scripts
        for fn in files:
            if fn.endswith('.groovy'):
                facts['scripts'][fn.split('/')[-1]] = z.read(fn).decode('utf-8', 'replace')

        # XSD files
        for fn in files:
            if fn.endswith('.xsd'):
                facts['xsd_files'].append(fn.split('/')[-1])

        # .mmap files
        mmap_files = [n for n in files if n.endswith('.mmap')]
        if mmap_files:
            mf = mmap_files[0]
            facts['mmap_name'] = mf.split('/')[-1].replace('.mmap', '')
            mmap_xml = z.read(mf).decode('utf-8', 'replace')
            facts['mmap_xml'] = mmap_xml
            dst = re.findall(r'path="([^"]+)" type="Dst"', mmap_xml)
            src = re.findall(r'path="([^"]+)" type="Src"', mmap_xml)
            facts['mmap_dst_fields'] = [d.split('/')[-1] for d in dst]
            facts['mmap_src_fields'] = [s.split('/')[-1] for s in src]

        # iflw XML
        iflw_files = [n for n in files if n.endswith('.iflw')]
        if iflw_files:
            xml = z.read(iflw_files[0]).decode('utf-8', 'replace')
            
            # Participants
            for m in re.finditer(r'<bpmn2:participant\b([^>]*)>', xml):
                attrs = m.group(1)
                nm  = re.search(r'\bname="([^"]+)"', attrs)
                tp  = re.search(r'\bifl:type="([^"]+)"', attrs)
                if nm:
                    facts['participants'].append({'name': nm.group(1), 'type': tp.group(1) if tp else ''})

            # Steps (all element types)
            step_patterns = [
                ('startEvent',        r'<bpmn2:startEvent\b([^>]*)>(.*?)</bpmn2:startEvent>'),
                ('callActivity',      r'<bpmn2:callActivity\b([^>]*)>(.*?)</bpmn2:callActivity>'),
                ('serviceTask',       r'<bpmn2:serviceTask\b([^>]*)>(.*?)</bpmn2:serviceTask>'),
                ('exclusiveGateway',  r'<bpmn2:exclusiveGateway\b([^>]*)>(.*?)</bpmn2:exclusiveGateway>'),
                ('subProcess',        r'<bpmn2:subProcess\b([^>]*)>(.*?)</bpmn2:subProcess>'),
                ('endEvent',          r'<bpmn2:endEvent\b([^>]*)>(.*?)</bpmn2:endEvent>'),
            ]
            for etype, pat in step_patterns:
                for m in re.finditer(pat, xml, re.DOTALL):
                    attrs = m.group(1); body = m.group(2)
                    nm  = re.search(r'\bname="([^"]+)"', attrs)
                    at  = re.search(r'<key>activityType</key><value>([^<]+)</value>', body)
                    sc  = re.search(r'<key>script</key><value>([^<]+)</value>', body)
                    cmd = re.search(r'<key>cmdVariantUri</key><value>([^<]+)</value>', body)
                    facts['steps'].append({
                        'name': nm.group(1) if nm else '',
                        'element_type': etype,
                        'activity_type': at.group(1).strip() if at else '',
                        'script_file': sc.group(1).strip() if sc else '',
                        'cmd_uri': cmd.group(1).strip() if cmd else '',
                    })

            # Adapters from messageFlows
            for m in re.finditer(r'<bpmn2:messageFlow\b([^>]*)>(.*?)</bpmn2:messageFlow>', xml, re.DOTALL):
                attrs = m.group(1); body = m.group(2)
                nm   = re.search(r'\bname="([^"]+)"', attrs)
                src_ref = re.search(r'\bsourceRef="([^"]+)"', attrs)
                tgt_ref = re.search(r'\btargetRef="([^"]+)"', attrs)
                ct  = re.search(r'<key>ComponentType</key><value>([^<]+)</value>', body)
                dir_ = re.search(r'<key>direction</key><value>([^<]+)</value>', body)
                url = re.search(r'<key>(?:address|httpAddressWithoutQuery|urlPath)</key><value>([^<]+)</value>', body)
                cred= re.search(r'<key>(?:credentialName|credential_name|alias)</key><value>([^<]+)</value>', body)
                facts['adapters'].append({
                    'name': nm.group(1) if nm else '',
                    'component': ct.group(1).strip() if ct else '',
                    'direction': dir_.group(1).strip() if dir_ else '',
                    'url': url.group(1).strip() if url else '',
                    'credential': cred.group(1).strip() if cred else '',
                    'source_ref': src_ref.group(1) if src_ref else '',
                    'target_ref': tgt_ref.group(1) if tgt_ref else '',
                })

    return facts


def _join_wrapped(text):
    """Join MANIFEST continuation lines (lines starting with space)."""
    return re.sub(r'\s+', ' ', text.replace('\n ', '')).strip()


def _extract_appendix_data(doc: Document) -> dict:
    """
    Extract data from appendix tables (last ~14 tables in the document).
    Returns dict: {normalized_label: value}
    """
    data = {}
    n = len(doc.tables)
    # Appendix tables are typically the last 14 (43-56 of 56)
    appendix_start = max(0, n - 15)
    
    for table in doc.tables[appendix_start:]:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            # Deduplicate merged
            seen = []
            for c in cells:
                if c not in seen: seen.append(c)
            if len(seen) >= 2 and seen[0] and seen[1]:
                label = seen[0]
                value = seen[1]
                if label and value and value not in ('', 'N/A', '[TBD]', '[TBD Date]', '[TBD Name]'):
                    data[_norm(label)] = value
    return data


# Labels where we ALWAYS replace the current value (even if not empty)
# because the TD may have wrong placeholder names from the FD
_ALWAYS_REPLACE_LABELS = {
    'iflow',           # IFlow name
    'artifact',        # Artifact (CPI)
    'package',         # Package / Folder name
    'folder',          # Folder name (PO)
    'mappingname',     # Mapping name row
    'mmapping',        # Mapping name
    'description',     # iFlow description
    'mode',            # Asynchronous/Synchronous
    'bundlename',      # Bundle name
    'artifactname',    # Artifact name
}

def _should_always_replace(norm_label: str) -> bool:
    """Return True if this label's value should always be replaced from iFlow ZIP."""
    return any(k in norm_label for k in _ALWAYS_REPLACE_LABELS)


def _fill_table_from_appendix(table, appendix_data: dict, overrides: dict = None):
    """
    For each row in a main-body table:
    - If label is in ALWAYS_REPLACE list → replace regardless of current value
    - If cell is empty or has a placeholder → fill from appendix / overrides
    overrides: {normalized_label: value} that takes priority over appendix.
    """
    for row in table.rows:
        cells = row.cells
        if len(cells) < 2:
            continue
        label_text = cells[0].text.strip()
        if not label_text:
            continue
        norm_label = _norm(label_text)
        
        # Find the VALUE cell (skip merged cells, find first non-label empty-ish cell)
        value_cell = None
        for c in cells[1:]:
            if c != cells[0]:  # skip merged
                value_cell = c
                break
        if not value_cell:
            continue

        current_val = value_cell.text.strip()
        norm_label  = _norm(label_text)

        # Always replace for iFlow-critical fields (iFlow name, package, mmap name, description)
        force_replace = _should_always_replace(norm_label) and bool(overrides)

        # For other fields: only fill if empty or placeholder
        is_empty = (not current_val or
                    current_val.startswith('[TBD') or
                    current_val.startswith('Example:') or
                    current_val.startswith('Type TBU') or
                    current_val.startswith('Make a summary') or
                    current_val.startswith('Place a BPMN') or
                    current_val.startswith('TBF') or
                    current_val.startswith('upon receiving'))

        if not is_empty and not force_replace:
            continue

        # Check overrides first (iFlow ZIP data), then appendix
        new_val = None
        if overrides:
            for ok, ov in overrides.items():
                if ok in norm_label or norm_label in ok:
                    new_val = ov
                    break
        if not new_val:
            for ak, av in appendix_data.items():
                if ak in norm_label or norm_label in ak:
                    new_val = av
                    break

        if new_val:
            _set_cell(value_cell, new_val)


def _add_para(doc, text, bold=False, size=10, color=None, indent=0):
    p = doc.add_paragraph()
    if indent: p.paragraph_format.left_indent = Cm(indent)
    r = p.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    if color: r.font.color.rgb = color
    return p


def _add_table(doc, headers, rows, col_widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = 'Table Grid'
    for j, h in enumerate(headers):
        c = t.rows[0].cells[j]; c.text = h
        r = c.paragraphs[0].runs[0]; r.font.bold = True
        r.font.size = Pt(9); r.font.color.rgb = WHITE
        _shd(c, '1A1A2E')
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.rows[i+1].cells[j]; c.text = str(val) if val else ''
            c.paragraphs[0].runs[0].font.size = Pt(9)
            if i % 2 == 0: _shd(c, 'F2F4F7')
    if col_widths:
        for j, w in enumerate(col_widths):
            for row in t.rows: row.cells[j].width = Cm(w)
    doc.add_paragraph()


def _add_code(doc, text):
    for line in text.strip().split('\n'):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(0)
        r = p.add_run(line or ' ')
        r.font.name = 'Courier New'; r.font.size = Pt(8); r.font.color.rgb = SAP_DARK


STEP_LABELS = {
    'Script':                      'Groovy Script',
    'GroovyScript':                'Groovy Script',
    'Enricher':                    'Content Modifier',
    'ExternalCall':                'Request Reply',
    'Mapping':                     'Message Mapping',
    'ExclusiveGateway':            'Router (CBR)',
    'Splitter':                    'Splitter',
    'DBstorage':                   'DataStore',
    'StartTimerEvent':             'Timer Start',
    'ErrorEventSubProcessTemplate':'Exception Subprocess',
    'Send':                        'Send Step',
    'ProcessCallElement':          'Process Call',
}


def _replace_text_in_cell(cell, old_text: str, new_text: str):
    """Replace text in all runs of all paragraphs in a cell."""
    for para in cell.paragraphs:
        full = ''.join(r.text for r in para.runs)
        if old_text in full:
            new_full = full.replace(old_text, new_text)
            if para.runs:
                para.runs[0].text = new_full
                for r in para.runs[1:]:
                    r.text = ''
            else:
                para.add_run(new_full)


def _replace_all_occurrences(doc: Document, replacements: list[tuple[str, str]]):
    """
    Replace ALL occurrences of old→new text across EVERY run in EVERY paragraph
    in EVERY table cell and regular paragraph in the document.
    replacements: list of (old_text, new_text)
    """
    def _fix_para(para):
        for old, new in replacements:
            full = ''.join(r.text for r in para.runs)
            if old in full:
                new_full = full.replace(old, new)
                if para.runs:
                    para.runs[0].text = new_full
                    for r in para.runs[1:]:
                        r.text = ''
                else:
                    para.add_run(new_full)

    # Regular paragraphs
    for para in doc.paragraphs:
        _fix_para(para)

    # Table cells
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _fix_para(para)


def _replace_artifact_names_everywhere(doc: Document, facts: dict, appendix_data: dict):
    """
    Scan every cell in every table in the document.
    Replace wrong/placeholder artifact names with correct names from iFlow ZIP.

    Targets:
    - Any cell whose label-row says 'IFlow', 'Artifact', 'Package', 'Folder name',
      'Name:' (in mapping context), 'Description'
    - The value cell in that row gets the correct name
    """
    iflow_name  = facts.get('iflow_name', '')
    mmap_name   = facts.get('mmap_name', '')
    pkg_name    = appendix_data.get(_norm('Folder name (PO) or Package (CPI)'), '')
    description = facts.get('description', '')

    for table in doc.tables:
        for row in table.rows:
            cells = row.cells
            if not cells:
                continue

            # Get first cell as the label, subsequent non-merged cells as values
            label = cells[0].text.strip()
            if not label:
                continue
            nf = _norm(label)

            # Collect unique value cells
            value_cells = []
            seen_texts = {cells[0].text}
            for c in cells[1:]:
                if c.text not in seen_texts:
                    seen_texts.add(c.text)
                    value_cells.append(c)

            if not value_cells:
                continue
            val_cell = value_cells[0]
            curr = val_cell.text.strip()

            # ── iFlow name rows ───────────────────────────────────────────────
            if iflow_name and ('iflow' in nf or ('artifact' in nf and 'cpi' in nf)):
                if curr and curr != iflow_name:
                    _set_cell(val_cell, iflow_name)

            # ── Package / Folder name rows ────────────────────────────────────
            elif pkg_name and ('folder' in nf or 'package' in nf):
                if curr and curr != pkg_name:
                    _set_cell(val_cell, pkg_name)

            # ── Description rows (iFlow description) ─────────────────────────
            elif description and nf == _norm('Description:'):
                if not curr or curr.startswith('[') or len(curr) < 20:
                    _set_cell(val_cell, description)

            # ── Mapping name rows ─────────────────────────────────────────────
            # Replace if cell looks like an old wrong mapping/artifact name
            elif mmap_name:
                is_name_row = 'name' in nf and len(nf) <= len(_norm('Name:') + 'softwarecomponentversion')
                if is_name_row and curr:
                    looks_like_wrong_name = (
                        curr.startswith('MM_') or
                        curr.startswith('GLO') or
                        (len(curr) > 5 and not curr.startswith('[') and
                         not curr.startswith('http') and
                         not curr.startswith('This') and
                         any(sep in curr for sep in ('_', '-')) and
                         curr != mmap_name)
                    )
                    if looks_like_wrong_name:
                        _set_cell(val_cell, mmap_name)

            # ── Artifact: <name> (CPI) rows ───────────────────────────────────
            elif mmap_name and 'artifactnamespace' in nf or ('artifact' in nf and 'cpi' in nf and 'namespace' not in nf):
                if curr and curr != f'Artifact: {mmap_name} (CPI)' and 'Artifact:' in curr:
                    _set_cell(val_cell, f'Artifact: {mmap_name} (CPI)')


def update_td_with_iflow(td_bytes: bytes, iflow_zip_bytes: bytes) -> bytes:
    """
    Update an existing TD document with iFlow ZIP data.
    - Fills main body tables from Appendix data
    - Overrides iFlow artifact fields from ZIP MANIFEST
    - Adds iFlow Design Steps section
    - Adds Message Mapping field table
    - Adds SAP-themed flow diagram
    ZERO AI — 100% deterministic.
    """
    doc   = Document(io.BytesIO(td_bytes))
    facts = _extract_iflow_facts(iflow_zip_bytes)
    appendix_data = _extract_appendix_data(doc)

    # ── Step 0: Extract what the TD currently has (to know what to replace) ──
    # Collect all "wrong" artifact names already in the document that need replacing.
    # We collect every cell value in the iFlow artifact and mapping tables
    # and replace any that differ from the correct ZIP names.
    existing_iflow_names = set()
    existing_mmap_names  = set()

    for table in doc.tables:
        for row in table.rows:
            cells = row.cells
            if not cells: continue
            for cell in cells:
                t = cell.text.strip()
                # Looks like an iFlow artifact name (CamelCase, no spaces, starts with Send/Receive/Map etc.)
                if (len(t) > 8 and ' ' not in t and
                    any(t.startswith(p) for p in ('Send','Receive','Get','Post','Map','I_','GLO','MM_',
                                                    'FDMAP','TDMAP','Inbound','Outbound'))):
                    # It's a candidate wrong name if it's NOT the correct names
                    if t != facts['iflow_name'] and t != facts['mmap_name']:
                        if any(kw in cell.text for kw in ['Batch','Stock','MBGMCR','ITALTRANS','Italtrans',
                                                            'BatchStatus','StockStatus']):
                            if t.startswith('MM_'):
                                existing_mmap_names.add(t)
                            else:
                                existing_iflow_names.add(t)

    # ── Step 0b: Build replacement list and do a full document text replacement
    replacements = []
    iflow_name = facts.get('iflow_name', '')
    mmap_name  = facts.get('mmap_name', '')

    # Replace wrong iFlow names with correct one
    if iflow_name:
        for wrong in existing_iflow_names:
            if wrong and wrong != iflow_name:
                replacements.append((wrong, iflow_name))
        # Also replace "Artifact: {wrong} (CPI)" → "Artifact: {iflow_name} (CPI)"
        for wrong in existing_iflow_names:
            replacements.append((f'Artifact: {wrong} (CPI)', f'Artifact: {iflow_name} (CPI)'))

    # Replace wrong mmap names with correct one
    if mmap_name:
        for wrong in existing_mmap_names:
            if wrong and wrong != mmap_name:
                replacements.append((wrong, mmap_name))

    if replacements:
        _replace_all_occurrences(doc, replacements)

    # ── Build override dict from actual iFlow ZIP facts ───────────────────────
    overrides = {}
    if facts['iflow_name']:
        overrides[_norm('IFlow (PO) or Artifact')] = facts['iflow_name']
        overrides[_norm('Artifact (CPI)')] = facts['iflow_name']
    if facts['description']:
        overrides[_norm('Description')] = facts['description']
    if facts['mmap_name']:
        overrides[_norm('Name:')] = facts['mmap_name']
    if facts['iflow_version']:
        overrides[_norm('Version')] = facts['iflow_version']

    # ── Full-document name replacement ────────────────────────────────────────
    # BEFORE filling tables, do a direct find-and-replace of wrong names
    # across ALL cells in ALL tables. This catches names that were copied
    # from the FD into the TD and are now incorrect.
    _replace_artifact_names_everywhere(doc, facts, appendix_data)

    # ── Fill each main body table from appendix data + overrides ─────────────
    # Appendix tables are the last ~14 tables; main body is everything before
    n_tables = len(doc.tables)
    main_body_limit = max(0, n_tables - 14)

    for i, table in enumerate(doc.tables[:main_body_limit]):
        _fill_table_from_appendix(table, appendix_data, overrides)

    # ── Special: fill Integration Logic table (Table 14 ~) with step summary ─
    step_summary = ' → '.join(
        s['name'] for s in facts['steps']
        if s['element_type'] not in ('endEvent', 'startEvent')
        and 'Error' not in s.get('name', '')
        and s.get('name')
    )
    if step_summary:
        for table in doc.tables[:main_body_limit]:
            for row in table.rows:
                if any('Integration flow' in c.text for c in row.cells):
                    for c in row.cells:
                        if 'Integration flow' not in c.text and (not c.text.strip() or c.text.strip().startswith('Example')):
                            _set_cell(c, step_summary)
                    break

    # ── Hard replace: iFlow name, package, mapping name in ALL tables ────────
    # These must be replaced regardless of current cell content because
    # the TD may have wrong names from FD (e.g. SendBatchAndStockStatusToItaltrans
    # instead of the real iFlow Bundle-Name from the ZIP).
    iflow_name_from_zip = facts['iflow_name']
    mmap_name_from_zip  = facts['mmap_name']
    pkg_from_appendix   = appendix_data.get(_norm('Folder name (PO) or Package (CPI)'), '')

    for table in doc.tables[:main_body_limit]:
        for row in table.rows:
            cells = row.cells
            if not cells: continue
            first = cells[0].text.strip()
            if not first: continue
            nf = _norm(first)

            # Get the value cell (first non-merged cell after label)
            val_cell = None
            for c in cells[1:]:
                if c.text.strip() != cells[0].text.strip():
                    val_cell = c
                    break
            if not val_cell:
                continue

            # Package / Folder name → ALWAYS replace with appendix value
            if ('folder' in nf or 'package' in nf) and pkg_from_appendix:
                _set_cell(val_cell, pkg_from_appendix)

            # iFlow / Artifact name → ALWAYS replace with ZIP Bundle-Name
            elif ('iflow' in nf or ('artifact' in nf and 'cpi' in nf)) and iflow_name_from_zip:
                _set_cell(val_cell, iflow_name_from_zip)

            # iFlow Description → ALWAYS replace with metainfo.prop description
            elif nf == _norm('Description:') and facts['description']:
                _set_cell(val_cell, facts['description'])

            # Mapping Name rows → ALWAYS replace with actual mmap name from ZIP
            elif mmap_name_from_zip and val_cell.text.strip():
                # If the cell looks like an old mapping name (starts with MM_ or SendBatch...)
                curr = val_cell.text.strip()
                is_old_mapping_name = (
                    (curr.startswith('MM_') or curr.startswith('Send') or
                     curr.startswith('FDMAP') or curr.startswith('TDMAP'))
                    and 'Artifact:' not in curr
                    and any(k in nf for k in ('name', 'artifact', 'mapping'))
                )
                if is_old_mapping_name:
                    # Only replace if the label suggests it's a mapping name field
                    if 'name' in nf and len(nf) < 15:
                        _set_cell(val_cell, mmap_name_from_zip)

    # ── Add new page with iFlow Design Steps ─────────────────────────────────
    doc.add_page_break()

    h = doc.add_heading('iFlow Design – Technical Steps', level=1)
    for r in h.runs: r.font.color.rgb = SAP_BLUE

    _add_para(doc,
        f'iFlow: {facts["iflow_name"]} | Version: {facts["iflow_version"]} | '
        f'Package: {appendix_data.get(_norm("Folder name (PO) or Package (CPI)"), "TBD")}',
        size=9, color=MID_GREY)
    _add_para(doc, facts['description'], size=10)
    doc.add_paragraph()

    # ── Flow diagram ─────────────────────────────────────────────────────────
    h2 = doc.add_heading('Integration Flow Diagram', level=2)
    for r in h2.runs: r.font.color.rgb = SAP_BLUE

    senders   = [a for a in facts['adapters'] if a['direction'] == 'Sender']
    receivers = [a for a in facts['adapters'] if a['direction'] == 'Receiver']
    main_steps= [s for s in facts['steps']
                 if s['element_type'] not in ('endEvent',)
                 and 'Error' not in s.get('name','')
                 and 'Error' not in s.get('element_type','')]

    step_desc = ', '.join(f"{s['name']} [{STEP_LABELS.get(s['activity_type'], s['element_type'])}]"
                          for s in main_steps if s.get('name'))
    act_types = [s['activity_type'] for s in main_steps]
    mapping_type = ('Groovy' if any(a in ('Script','GroovyScript') for a in act_types)
                    else 'Message Mapping' if 'Mapping' in act_types else '')

    src_name = senders[0]['source_ref']   if senders   else 'SAP_AEM'
    # Get participant name for sender
    sender_participant = next((p['name'] for p in facts['participants']
                               if p['type'] == 'EndpointSender'), src_name)

    tgt_names = ', '.join(
        f"{r['target_ref']} {r['component']}" for r in receivers
        if r['component'] not in ('ProcessDirect',)
    ) if receivers else 'Target'

    # Map participant refs to actual names
    part_names = {p['name']: p['name'] for p in facts['participants']}
    # Use component name for target classification
    tgt_display = ', '.join(
        f"{next((p['name'] for p in facts['participants'] if p['name'] == r['target_ref']), r['target_ref'])} {r['component']}"
        for r in receivers if r['component'] not in ('ProcessDirect',)
    ) if receivers else 'Target'

    try:
        png = generate_flowchart({
            'interface_name':  facts['iflow_name'],
            'source_app_name': sender_participant,
            'source_protocol': senders[0]['component'] if senders else 'HTTPS',
            'target_app_name': tgt_display or tgt_names,
            'target_protocol': receivers[0]['component'] if receivers else 'AS2',
            'integration_logic': step_desc,
            'mapping_type':    mapping_type,
        })
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(io.BytesIO(png), width=Inches(6.2))
    except Exception as e:
        _add_para(doc, f'[Diagram error: {e}]', size=9, color=RED_C)

    doc.add_paragraph()

    # ── Step-by-step table ────────────────────────────────────────────────────
    h3 = doc.add_heading('Step-by-Step Configuration', level=2)
    for r in h3.runs: r.font.color.rgb = SAP_BLUE

    step_rows = []
    step_num = 1
    for s in facts['steps']:
        if s['element_type'] in ('endEvent',): continue
        if 'Error' in s.get('name','') and s['element_type'] == 'startEvent': continue
        label = STEP_LABELS.get(s['activity_type'], s['element_type'].replace('Event','').title())
        step_rows.append((
            str(step_num),
            s['name'],
            label,
            s.get('script_file', '') or '',
            s.get('cmd_uri', '').split('/')[-1] if s.get('cmd_uri') else '',
        ))
        step_num += 1

    _add_table(doc,
        ['#', 'Step Name', 'Type', 'Script / Artifact', 'Version'],
        step_rows, col_widths=[1, 6, 3, 4.5, 3])

    # ── Adapters ──────────────────────────────────────────────────────────────
    h4 = doc.add_heading('Adapters', level=2)
    for r in h4.runs: r.font.color.rgb = SAP_BLUE

    adapter_rows = []
    for a in facts['adapters']:
        direction = a['direction']
        sys_ref   = a['source_ref'] if direction == 'Sender' else a['target_ref']
        adapter_rows.append((direction, sys_ref, a['component'],
                             a['url'][:50] if a['url'] else '', a['credential']))
    _add_table(doc,
        ['Direction', 'System', 'Adapter', 'URL / Endpoint', 'Credential Alias'],
        adapter_rows, col_widths=[2.5, 3.5, 2.5, 5.5, 3.5])

    # ── Parameters ───────────────────────────────────────────────────────────
    if facts['parameters']:
        h5 = doc.add_heading('Externalized Parameters', level=2)
        for r in h5.runs: r.font.color.rgb = SAP_BLUE
        _add_table(doc,
            ['Parameter Name', 'Required', 'Description'],
            [(p['name'], 'Yes' if p['required'] else 'No', p['description'])
             for p in facts['parameters'][:30]],
            col_widths=[6, 2, 9.5])

    # ── Message Mapping ───────────────────────────────────────────────────────
    if facts['mmap_name']:
        doc.add_page_break()
        h6 = doc.add_heading('Message Mapping', level=2)
        for r in h6.runs: r.font.color.rgb = SAP_BLUE

        _add_para(doc, f'Mapping Artifact: {facts["mmap_name"]}.mmap', bold=True, size=10)
        _add_para(doc,
            f'Source fields: {len(facts["mmap_src_fields"])} | '
            f'Target fields: {len(facts["mmap_dst_fields"])}',
            size=9, color=MID_GREY)
        doc.add_paragraph()

        # Show source → target field mapping table
        # Match src to dst by position (both lists are ordered by occurrence in XML)
        n = max(len(facts['mmap_src_fields']), len(facts['mmap_dst_fields']))
        rows = []
        for i in range(min(n, 60)):
            src_f = facts['mmap_src_fields'][i] if i < len(facts['mmap_src_fields']) else ''
            dst_f = facts['mmap_dst_fields'][i] if i < len(facts['mmap_dst_fields']) else ''
            if src_f != dst_f or src_f:
                rows.append((src_f, '→', dst_f))
        if rows:
            _add_table(doc,
                ['Source Field (IDoc)', '', 'Target Field (IDoc-XML)'],
                rows, col_widths=[6, 1, 10.5])
        if n > 60:
            _add_para(doc, f'... {n - 60} more fields (see mmap artifact in CPI)', size=9, color=MID_GREY)

    # ── Groovy Scripts ────────────────────────────────────────────────────────
    if facts['scripts']:
        h7 = doc.add_heading('Groovy Scripts', level=2)
        for r in h7.runs: r.font.color.rgb = SAP_BLUE
        for fname, code in facts['scripts'].items():
            t = doc.add_table(rows=1, cols=1); t.style = 'Table Grid'
            c = t.rows[0].cells[0]; c.text = fname
            _shd(c, '1A1A2E')
            c.paragraphs[0].runs[0].font.bold = True
            c.paragraphs[0].runs[0].font.color.rgb = WHITE
            c.paragraphs[0].runs[0].font.size = Pt(10)
            _add_code(doc, code[:3000])
            doc.add_paragraph()

    # ── XSD / Schema references ───────────────────────────────────────────────
    if facts['xsd_files']:
        h8 = doc.add_heading('XSD Schema Files', level=2)
        for r in h8.runs: r.font.color.rgb = SAP_BLUE
        for xf in facts['xsd_files']:
            _add_para(doc, f'• {xf}', size=10)
        doc.add_paragraph()

    # ── Save ─────────────────────────────────────────────────────────────────
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()
