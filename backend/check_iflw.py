"""Check generated iFlw structure vs reference iFlw."""
import sys, re, urllib.request, json
sys.path.insert(0, '.')

# Generate a sample iFlw
body = json.dumps({
    "name": "Test_Flow", "description": "HTTPS receives XML sends via HTTP",
    "sender_adapter": "HTTPS", "receiver_adapter": "HTTP",
    "transformation_type": "None", "include_error_handling": True,
    "extra_steps": "", "version": "1.0.0", "package_id": "", "package_name": ""
}).encode()

req = urllib.request.Request("http://localhost:8080/api/iflow/generate",
    data=body, method="POST", headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as r:
    data = json.loads(r.read())
iflw = data["result"]

print("=== STRUCTURE CHECKS ===")
# Order check
collab_pos  = iflw.find('<bpmn2:collaboration')
process_pos = iflw.find('<bpmn2:process')
diagram_pos = iflw.find('<bpmndi:BPMNDiagram')
print(f"collaboration at char {collab_pos}")
print(f"process       at char {process_pos}")
print(f"BPMNDiagram   at char {diagram_pos}")
print(f"Order OK (collab < process < diagram): {collab_pos < process_pos < diagram_pos}")
print()

# Process name check
pm = re.search(r'<bpmn2:process\b[^>]*>', iflw)
print(f"process opening tag: {pm.group() if pm else 'NOT FOUND'}")
print()

# processRef check
pref = re.search(r'processRef="([^"]+)"', iflw)
pid  = re.search(r'<bpmn2:process\b[^>]*\bid="([^"]+)"', iflw)
print(f"processRef value: {pref.group(1) if pref else 'NOT FOUND'}")
print(f"process id:       {pid.group(1) if pid else 'NOT FOUND'}")
print(f"processRef matches process id: {pref and pid and pref.group(1)==pid.group(1)}")
print()

# Integration Process cmdVariantUri check
print(f"IntegrationProcess/version present: {'IntegrationProcess/version' in iflw}")
print(f"transactionTimeout present: {'transactionTimeout' in iflw}")
print()

# Participant types
for m in re.finditer(r'ifl:type="([^"]+)"', iflw):
    print(f"  ifl:type found: {m.group(1)}")
print()

# BPMNEdge sourceElement check
edges = re.findall(r'<bpmndi:BPMNEdge\b[^>]*>', iflw)
for e in edges[:3]:
    has_src = 'sourceElement=' in e
    has_tgt = 'targetElement=' in e
    print(f"  Edge sourceElement={has_src} targetElement={has_tgt}: {e[:80]}")
print()

# Waypoint xsi:type check
wps = re.findall(r'<di:waypoint\b[^/]*/>', iflw)
for wp in wps[:3]:
    print(f"  waypoint has xsi:type: {'xsi:type' in wp} → {wp}")
