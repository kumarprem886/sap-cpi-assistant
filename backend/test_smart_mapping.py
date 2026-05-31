"""End-to-end test for smart mapping generation."""
import sys, json, zipfile, io, re, time
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Login
login = client.post('/api/auth/login', json={'email': 'admin@cpi.local', 'password': 'admin123'})
token = login.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

test_idea = (
    "Map SAP Purchase Order IDoc ORDERS05 to a REST target with: "
    "vendor number, total net value (sum of all item net values), "
    "item count, purchase order number, and delivery date"
)

print("=" * 70)
print("TEST: Smart Mapping Generation")
print(f"IDEA: {test_idea}")
print("=" * 70)

start = time.time()
r = client.post('/api/mapping/generate-from-idea',
    json={'idea': test_idea, 'mapping_name': 'MM_PO_to_REST'},
    headers=headers
)
elapsed = round(time.time() - start, 1)

print(f"Status: {r.status_code}  |  Time: {elapsed}s")
print(f"X-Mapping-Count: {r.headers.get('X-Mapping-Count', '?')}")
print(f"X-Source-XSD:    {r.headers.get('X-Source-XSD', '?')}")

if r.status_code != 200:
    print(f"ERROR: {r.text[:500]}")
    sys.exit(1)

# Inspect ZIP
with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
    print(f"\nZIP contents:")
    for name in zf.namelist():
        size = zf.getinfo(name).file_size
        print(f"  {name}  ({size:,} bytes)")

    mmap_file = [n for n in zf.namelist() if n.endswith('.mmap')][0]
    mmap_xml = zf.read(mmap_file).decode('utf-8')

# Extract all Dst bricks
print(f"\nAll mapping bricks (target paths):")
dst_paths = re.findall(r'path="([^"]+)" type="Dst"', mmap_xml)
for dst in dst_paths:
    seg = dst.split('/')[-1]
    # Find function or source for this target
    # Look for fname in the arg block of this Dst brick
    pattern = rf'path="{re.escape(dst)}" type="Dst">.*?</brick>'
    brick_match = re.search(pattern, mmap_xml, re.DOTALL)
    if brick_match:
        brick_content = brick_match.group(0)
        func_m = re.search(r'fname="([^"]+)"', brick_content)
        src_m  = re.search(r'path="([^"]+)" type="Src"', brick_content)
        if func_m:
            fn = func_m.group(1)
            src = src_m.group(1).split('/')[-1] if src_m else '?'
            print(f"  {dst:<55} <- [{fn}({src})]")
        elif src_m:
            src = src_m.group(1)
            print(f"  {dst:<55} <- {src.split('/')[-1]}")
        else:
            print(f"  {dst:<55} <- (auto parent)")

# Verification
print("\n--- VERIFICATION ---")
checks = [
    ("Catalog XSD used (not AI-hallucinated)", r.headers.get('X-Source-XSD','') != 'source.xsd'),
    ("sum() Statistics function for total",   'fname="sum"' in mmap_xml),
    ("count() Statistics function for items", 'fname="count"' in mmap_xml),
    ("No hallucinated Item/Quantity path",    "Item/Quantity" not in mmap_xml),
    ("Root parent auto-injected",             mmap_xml.count('type="Dst"') > 5),
    ("Vendor/Supplier field mapped",          any(
        "vendor" in p.lower() or "supplier" in p.lower() or "LIFNR" in mmap_xml
        for p in dst_paths)),
    ("PO number field mapped",                any(
        "order" in p.lower() or "po" in p.lower() for p in dst_paths)),
    ("sum uses repeating item field",         bool(re.search(r'fname="sum".*?path="[^"]*Item[^"]*"', mmap_xml, re.DOTALL)
                                                   or re.search(r'fname="sum".*?path="[^"]*Net[^"]*"', mmap_xml, re.DOTALL))),
]

all_ok = True
for label, ok in checks:
    status = "OK  " if ok else "FAIL"
    print(f"  {status} {label}")
    if not ok:
        all_ok = False

print()
print("RESULT:", "ALL CHECKS PASSED ✓" if all_ok else "SOME CHECKS FAILED ✗")

# Save for import
with open(r'C:\Users\prem.am.kumar\Downloads\MM_PO_to_REST_test.zip', 'wb') as f:
    f.write(r.content)
print("\nSaved to Downloads/MM_PO_to_REST_test.zip — ready to import into CPI")
