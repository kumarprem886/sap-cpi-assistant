"""Parse a SAP CPI iFlow ZIP into structured data for TD generation."""
import re, zipfile, io
from xml.etree import ElementTree as ET

def parse_iflow_zip(zip_bytes: bytes) -> dict:
    """
    Parse a CPI iFlow ZIP and return structured dict with:
    - name: iFlow name
    - description: from metainfo.prop
    - steps: list of steps in sequence order
    - adapters: sender + receiver adapter configs
    - scripts: {filename: code_string}
    - parameters: list of {name, default, description, required}
    - participants: {id: {name, type}}
    - sequence_flows: list of {source, target, condition}
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        files = z.namelist()

        # Find the .iflw file
        iflw_files = [n for n in files if n.endswith('.iflw')]
        if not iflw_files:
            return {}
        xml_text = z.read(iflw_files[0]).decode('utf-8', errors='replace')

        # metainfo.prop → description
        description = ''
        for pf in files:
            if 'metainfo.prop' in pf:
                raw = z.read(pf).decode('utf-8', errors='replace')
                for line in raw.splitlines():
                    if line.startswith('description='):
                        description = line[12:].strip()

        # Groovy scripts
        scripts = {}
        for f in files:
            if f.endswith('.groovy'):
                name = f.split('/')[-1]
                scripts[name] = z.read(f).decode('utf-8', errors='replace')

        # parameters.prop default values
        param_defaults = {}
        for f in files:
            if f.endswith('parameters.prop') and not f.endswith('.propdef'):
                for line in z.read(f).decode('utf-8', errors='replace').splitlines():
                    if '=' in line and not line.startswith('#'):
                        k, _, v = line.partition('=')
                        param_defaults[k.strip()] = v.strip()

        # parameters.propdef
        parameters = []
        for f in files:
            if f.endswith('.propdef'):
                raw = z.read(f).decode('utf-8', errors='replace')
                for m in re.finditer(r'<parameter>(.*?)</parameter>', raw, re.DOTALL):
                    block = m.group(1)
                    name = re.search(r'<name>([^<]+)</name>', block)
                    desc = re.search(r'<description>([^<]+)</description>', block)
                    req  = re.search(r'<isRequired>([^<]+)</isRequired>', block)
                    if name:
                        n = name.group(1).strip()
                        parameters.append({
                            'name':        n,
                            'default':     param_defaults.get(n, ''),
                            'description': desc.group(1).strip() if desc else '',
                            'required':    (req.group(1).strip().lower() == 'true') if req else False,
                        })

        # Parse the iflw XML
        result = _parse_iflw_xml(xml_text, scripts, parameters, description)
        return result


def _get_prop(block: str, key: str) -> str:
    """Extract <key>KEY</key><value>VAL</value> from an XML block."""
    m = re.search(rf'<key>{re.escape(key)}</key>\s*<value>([^<]*)</value>', block)
    return m.group(1).strip() if m else ''


def _get_all_props(block: str) -> dict:
    """Extract all key/value properties from an XML block."""
    props = {}
    for m in re.finditer(r'<key>([^<]+)</key>\s*<value>([^<]*)</value>', block):
        props[m.group(1).strip()] = m.group(2).strip()
    return props


def _parse_iflw_xml(xml: str, scripts: dict, parameters: list, description: str) -> dict:
    """Parse the .iflw XML and return structured step/adapter data."""

    # ── iFlow name from process name ────────────────────────────────────────
    name_m = re.search(r'<bpmn2:process[^>]+\bname="([^"]+)"', xml)
    iflow_name = name_m.group(1) if name_m else 'Unknown'

    # ── Participants ─────────────────────────────────────────────────────────
    participants = {}
    for m in re.finditer(r'<bpmn2:participant\b([^>]*)>', xml):
        attrs = m.group(1)
        pid   = re.search(r'\bid="([^"]+)"', attrs)
        pname = re.search(r'\bname="([^"]+)"', attrs)
        ptype = re.search(r'\bifl:type="([^"]+)"', attrs)
        if pid:
            participants[pid.group(1)] = {
                'name': pname.group(1) if pname else '',
                'type': ptype.group(1) if ptype else '',
            }

    # ── Adapter configs from messageFlows ────────────────────────────────────
    adapters = []
    for m in re.finditer(r'<bpmn2:messageFlow\b([^>]*)>(.*?)</bpmn2:messageFlow>', xml, re.DOTALL):
        attrs    = m.group(1)
        body     = m.group(2)
        mf_id    = re.search(r'\bid="([^"]+)"', attrs)
        mf_name  = re.search(r'\bname="([^"]+)"', attrs)
        src_ref  = re.search(r'\bsourceRef="([^"]+)"', attrs)
        tgt_ref  = re.search(r'\btargetRef="([^"]+)"', attrs)
        props    = _get_all_props(body)
        direction = props.get('direction', 'Sender' if src_ref and src_ref.group(1) in participants else 'Receiver')
        comp_type = props.get('ComponentType') or props.get('Name') or mf_name.group(1) if mf_name else 'Unknown'

        src_name = participants.get(src_ref.group(1), {}).get('name', '') if src_ref else ''
        tgt_name = participants.get(tgt_ref.group(1), {}).get('name', '') if tgt_ref else ''

        adapters.append({
            'id':          mf_id.group(1) if mf_id else '',
            'name':        mf_name.group(1) if mf_name else '',
            'direction':   direction,
            'component':   comp_type,
            'source_name': src_name,
            'target_name': tgt_name,
            'properties':  props,
        })

    # ── Steps: extract all elements in the process ───────────────────────────
    raw_steps = []

    patterns = [
        ('startEvent',       r'<bpmn2:startEvent\b([^>]*)>(.*?)</bpmn2:startEvent>'),
        ('callActivity',     r'<bpmn2:callActivity\b([^>]*)>(.*?)</bpmn2:callActivity>'),
        ('serviceTask',      r'<bpmn2:serviceTask\b([^>]*)>(.*?)</bpmn2:serviceTask>'),
        ('exclusiveGateway', r'<bpmn2:exclusiveGateway\b([^>]*)>(.*?)</bpmn2:exclusiveGateway>'),
        ('subProcess',       r'<bpmn2:subProcess\b([^>]*)>(.*?)</bpmn2:subProcess>'),
        ('endEvent',         r'<bpmn2:endEvent\b([^>]*)>(.*?)</bpmn2:endEvent>'),
    ]

    for elem_type, pattern in patterns:
        for m in re.finditer(pattern, xml, re.DOTALL):
            attrs = m.group(1)
            body  = m.group(2)
            sid   = re.search(r'\bid="([^"]+)"', attrs)
            sname = re.search(r'\bname="([^"]+)"', attrs)
            props = _get_all_props(body)

            # For exception subprocess, extract inner steps too
            inner = []
            if elem_type == 'subProcess':
                for ip, ipat in patterns[:-1]:
                    for im in re.finditer(ipat, body, re.DOTALL):
                        ia = im.group(1); ib = im.group(2)
                        iid = re.search(r'\bid="([^"]+)"', ia)
                        ina = re.search(r'\bname="([^"]+)"', ia)
                        inner.append({
                            'id':            iid.group(1) if iid else '',
                            'name':          ina.group(1) if ina else '',
                            'element_type':  ip,
                            'activity_type': _get_prop(ib, 'activityType'),
                            'cmd_uri':       _get_prop(ib, 'cmdVariantUri'),
                            'properties':    _get_all_props(ib),
                        })

            activity_type = props.get('activityType', '')
            script_file   = props.get('script', '')

            raw_steps.append({
                'id':            sid.group(1) if sid else '',
                'name':          sname.group(1) if sname else '',
                'element_type':  elem_type,
                'activity_type': activity_type,
                'cmd_uri':       props.get('cmdVariantUri', ''),
                'script_file':   script_file,
                'script_code':   scripts.get(script_file, ''),
                'script_fn':     props.get('scriptFunction', ''),
                'properties':    props,
                'inner_steps':   inner,
            })

    # ── Sequence flows ───────────────────────────────────────────────────────
    sequence_flows = []
    for m in re.finditer(r'<bpmn2:sequenceFlow\b([^>]*)>(.*?)</bpmn2:sequenceFlow>', xml, re.DOTALL):
        attrs = m.group(1); body = m.group(2)
        sf_id    = re.search(r'\bid="([^"]+)"', attrs)
        sf_name  = re.search(r'\bname="([^"]+)"', attrs)
        sf_src   = re.search(r'\bsourceRef="([^"]+)"', attrs)
        sf_tgt   = re.search(r'\btargetRef="([^"]+)"', attrs)
        cond_m   = re.search(r'<bpmn2:conditionExpression[^>]*>([^<]+)</bpmn2:conditionExpression>', body)
        sequence_flows.append({
            'id':        sf_id.group(1) if sf_id else '',
            'name':      sf_name.group(1) if sf_name else '',
            'source':    sf_src.group(1) if sf_src else '',
            'target':    sf_tgt.group(1) if sf_tgt else '',
            'condition': cond_m.group(1).strip() if cond_m else '',
        })

    # ── Sort steps by sequence flow order ────────────────────────────────────
    ordered = _order_steps(raw_steps, sequence_flows)

    return {
        'name':            iflow_name,
        'description':     description,
        'participants':    participants,
        'adapters':        adapters,
        'steps':           ordered,
        'sequence_flows':  sequence_flows,
        'scripts':         scripts,
        'parameters':      parameters,
    }


def _order_steps(steps: list, flows: list) -> list:
    """Sort steps in execution order using sequence flows."""
    # Build adjacency: step_id → next step_id
    step_by_id = {s['id']: s for s in steps}
    next_map   = {}
    for f in flows:
        if f['source'] in step_by_id and f['target'] in step_by_id:
            if f['source'] not in next_map:
                next_map[f['source']] = []
            next_map[f['source']].append(f['target'])

    # Find start event
    ordered = []
    visited = set()

    # Start from startEvents
    starts = [s for s in steps if s['element_type'] == 'startEvent' and 'Error' not in s['id']]
    queue = [s['id'] for s in starts]

    while queue:
        sid = queue.pop(0)
        if sid in visited: continue
        visited.add(sid)
        if sid in step_by_id:
            ordered.append(step_by_id[sid])
        for nxt in next_map.get(sid, []):
            if nxt not in visited:
                queue.append(nxt)

    # Add any unvisited steps (subProcesses, error handlers, etc.)
    for s in steps:
        if s['id'] not in visited:
            ordered.append(s)

    return ordered
