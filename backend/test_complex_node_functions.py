"""
Complex node function test — exercises 10+ different functions.

Scenario: Map MATMAS05 (Material Master IDoc) to a REST target with:
1. sum()          - total storage quantity across all plant records
2. count()        - count of plant records
3. index()        - generate line numbers for each plant
4. useOneAsMany() - repeat material number for each plant
5. SplitByValue() - split comma-separated units of measure
6. collapseContexts() - merge multiple description lines
7. mapWithDefault()   - default plant if missing
8. toUpperCase()      - uppercase material type
9. formatDate()       - reformat creation date
10. concat (+)        - combine plant + storage location code
11. replaceAll()      - remove special chars from material number
"""
import sys, json, zipfile, io, re, time
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
login = client.post('/api/auth/login', json={'email': 'admin@cpi.local', 'password': 'admin123'})
token = login.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# ── Minimal source XSD (MATMAS05-like, simplified) ──────────────────────────
SOURCE_XSD = '''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="MaterialMaster">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Header">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="MaterialNumber" type="xs:string"/>
              <xs:element name="MaterialType"   type="xs:string"/>
              <xs:element name="CreationDate"   type="xs:string"/>
              <xs:element name="BaseUnit"        type="xs:string"/>
              <xs:element name="AlternativeUnits" type="xs:string" minOccurs="0"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
        <xs:element name="Descriptions" minOccurs="0">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="Description" type="xs:string"
                          minOccurs="0" maxOccurs="unbounded"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
        <xs:element name="PlantData" minOccurs="0">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="Plant" minOccurs="0" maxOccurs="unbounded">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element name="PlantCode"         type="xs:string"/>
                    <xs:element name="StorageLocation"   type="xs:string" minOccurs="0"/>
                    <xs:element name="UnrestrictedStock" type="xs:decimal"/>
                    <xs:element name="SpecialStock"      type="xs:decimal" minOccurs="0"/>
                  </xs:sequence>
                </xs:complexType>
              </xs:element>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>'''

# ── Target XSD ──────────────────────────────────────────────────────────────
TARGET_XSD = '''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="ProductOutput">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="MaterialId"        type="xs:string"/>
        <xs:element name="MaterialTypeCode"  type="xs:string"/>
        <xs:element name="FormattedDate"     type="xs:string"/>
        <xs:element name="CombinedDescription" type="xs:string"/>
        <xs:element name="AlternativeUomList" minOccurs="0">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="UomEntry" type="xs:string"
                          minOccurs="0" maxOccurs="unbounded"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
        <xs:element name="TotalStock"    type="xs:decimal"/>
        <xs:element name="PlantCount"    type="xs:integer"/>
        <xs:element name="PlantLines" minOccurs="0">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="PlantLine" minOccurs="0" maxOccurs="unbounded">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element name="LineNumber"       type="xs:integer"/>
                    <xs:element name="MaterialRef"      type="xs:string"/>
                    <xs:element name="PlantLocation"    type="xs:string"/>
                    <xs:element name="EffectivePlant"   type="xs:string"/>
                    <xs:element name="StockQuantity"    type="xs:decimal"/>
                  </xs:sequence>
                </xs:complexType>
              </xs:element>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>'''

# ── Expected mappings with rules ─────────────────────────────────────────────
MAPPINGS = [
    # Root
    {"source_path": "/MaterialMaster",          "target_path": "/ProductOutput",                    "rule": ""},
    # Header
    {"source_path": "/MaterialMaster/Header",   "target_path": "/ProductOutput",                    "rule": ""},

    # 1. replaceAll — clean special chars from material number
    {"source_path": "/MaterialMaster/Header/MaterialNumber",
     "target_path": "/ProductOutput/MaterialId",
     "rule": "replaceAll((/MaterialMaster/Header/MaterialNumber), [^A-Z0-9], )",
     "note": "replaceAll: remove non-alphanumeric"},

    # 2. toUpperCase — standardize material type
    {"source_path": "/MaterialMaster/Header/MaterialType",
     "target_path": "/ProductOutput/MaterialTypeCode",
     "rule": "toUpperCase((/MaterialMaster/Header/MaterialType))",
     "note": "toUpperCase"},

    # 3. formatDate — reformat creation date YYYYMMDD → YYYY-MM-DD
    {"source_path": "/MaterialMaster/Header/CreationDate",
     "target_path": "/ProductOutput/FormattedDate",
     "rule": "formatDate((/MaterialMaster/Header/CreationDate), yyyyMMdd, yyyy-MM-dd)",
     "note": "TransformDate"},

    # 4. collapseContexts — merge repeating description lines into one
    {"source_path": "/MaterialMaster/Descriptions/Description",
     "target_path": "/ProductOutput/CombinedDescription",
     "rule": "collapseContexts((/MaterialMaster/Descriptions/Description))",
     "note": "collapseContexts: merge N descriptions → 1"},

    # 5. SplitByValue — split comma-delimited alternative UoMs
    {"source_path": "/MaterialMaster/Header/AlternativeUnits",
     "target_path": "/ProductOutput/AlternativeUomList/UomEntry",
     "rule": "SplitByValue((/MaterialMaster/Header/AlternativeUnits), ,)",
     "note": "SplitByValue: 1 → N on comma"},

    # 6. sum — total unrestricted stock across all plants
    {"source_path": "/MaterialMaster/PlantData/Plant/UnrestrictedStock",
     "target_path": "/ProductOutput/TotalStock",
     "rule": "sum((/MaterialMaster/PlantData/Plant/UnrestrictedStock))",
     "note": "sum: N plant stocks → 1 total"},

    # 7. count — number of plants
    {"source_path": "/MaterialMaster/PlantData/Plant",
     "target_path": "/ProductOutput/PlantCount",
     "rule": "count((/MaterialMaster/PlantData/Plant))",
     "note": "count: how many plants"},

    # PlantLines parent
    {"source_path": "/MaterialMaster/PlantData/Plant",
     "target_path": "/ProductOutput/PlantLines",
     "rule": ""},
    {"source_path": "/MaterialMaster/PlantData/Plant",
     "target_path": "/ProductOutput/PlantLines/PlantLine",
     "rule": ""},

    # 8. index — line number for each plant
    {"source_path": "/MaterialMaster/PlantData/Plant/PlantCode",
     "target_path": "/ProductOutput/PlantLines/PlantLine/LineNumber",
     "rule": "index((/MaterialMaster/PlantData/Plant/PlantCode))",
     "note": "index: 0-based sequential"},

    # 9. useOneAsMany — repeat material number for each plant line
    {"source_path": "/MaterialMaster/Header/MaterialNumber",
     "target_path": "/ProductOutput/PlantLines/PlantLine/MaterialRef",
     "rule": "useOneAsMany((/MaterialMaster/Header/MaterialNumber))",
     "note": "useOneAsMany: 1 material → N plant lines"},

    # 10. concat — combine PlantCode + StorageLocation
    {"source_path": "/MaterialMaster/PlantData/Plant/PlantCode",
     "target_path": "/ProductOutput/PlantLines/PlantLine/PlantLocation",
     "rule": "(/MaterialMaster/PlantData/Plant/PlantCode)+_+(/MaterialMaster/PlantData/Plant/StorageLocation)",
     "note": "concat: plant_storageloc"},

    # 11. mapWithDefault — use DEFAULT if plant code missing
    {"source_path": "/MaterialMaster/PlantData/Plant/PlantCode",
     "target_path": "/ProductOutput/PlantLines/PlantLine/EffectivePlant",
     "rule": "mapWithDefault((/MaterialMaster/PlantData/Plant/PlantCode), DEFAULT)",
     "note": "mapWithDefault"},

    # 12. Direct copy — stock quantity
    {"source_path": "/MaterialMaster/PlantData/Plant/UnrestrictedStock",
     "target_path": "/ProductOutput/PlantLines/PlantLine/StockQuantity",
     "rule": "",
     "note": "direct copy"},
]

# ── Build mmap directly via builder ─────────────────────────────────────────
from services.mmap_builder import build_mmap_xml, build_mmap_zip
from services.sheet_mapper import _parse_rule
from services.xsd_parser import smart_extract_paths

src_root, src_paths = smart_extract_paths(SOURCE_XSD)
tgt_root, tgt_paths = smart_extract_paths(TARGET_XSD)

print("=" * 70)
print("COMPLEX NODE FUNCTION TEST — 12 different functions")
print("=" * 70)
print(f"\nSource root: {src_root}  |  Source paths: {len(src_paths)}")
print(f"Target root: {tgt_root}  |  Target paths: {len(tgt_paths)}\n")

# Parse rules
matched = []
for m in MAPPINGS:
    src_p  = m.get("source_path", "")
    tgt_p  = m.get("target_path", "")
    rule   = m.get("rule", "")
    note   = m.get("note", "")
    if rule:
        parsed = _parse_rule(rule, src_paths)
        if parsed:
            func_name, parts = parsed
            matched.append({"target_path": tgt_p, "func": func_name, "parts": parts, "note": note})
        else:
            print(f"  WARN: Could not parse rule '{rule}' for {tgt_p.split('/')[-1]}")
    elif src_p:
        matched.append({"source_path": src_p, "target_path": tgt_p, "note": note or "direct"})

print(f"Rules parsed: {len(matched)} / {len(MAPPINGS)}")

# Build mmap
mmap_xml = build_mmap_xml(
    "MM_ComplexNodeFunctions",
    "source.xsd", src_root,
    "target.xsd", tgt_root,
    matched
)

zip_bytes = build_mmap_zip("MM_ComplexNodeFunctions", mmap_xml, SOURCE_XSD, TARGET_XSD)

# ── Inspect result ────────────────────────────────────────────────────────────
dst_bricks = re.findall(r'path="([^"]+)" type="Dst"', mmap_xml)
func_bricks = re.findall(r'fname="([^"]+)"', mmap_xml)

print(f"\nDst bricks total:  {len(dst_bricks)}")
print(f"Function bricks:   {len(func_bricks)}  {sorted(set(func_bricks))}")

print("\n--- MAPPING RESULT ---")
for dst in dst_bricks:
    seg = dst.split('/')[-1]
    # Find function for this Dst
    pat = rf'path="{re.escape(dst)}" type="Dst">.*?(?=<brick gid="0" path=|</transformation>)'
    m2 = re.search(pat, mmap_xml, re.DOTALL)
    if m2:
        block = m2.group(0)
        fn = re.search(r'fname="([^"]+)"', block)
        src = re.search(r'path="([^"]+)" type="Src"', block)
        delim = re.search(r'name="delimeter"><value>([^<]*)</value>', block)
        iform = re.search(r'name="iform"><value>([^<]*)</value>', block)
        oform = re.search(r'name="oform"><value>([^<]*)</value>', block)
        srch  = re.search(r'name="search"><value>([^<]*)</value>', block)
        repl  = re.search(r'name="replace"><value>([^<]*)</value>', block)
        defv  = re.search(r'name="default_value"><value>([^<]*)</value>', block)

        details = []
        if fn: details.append(fn.group(1))
        if src and not fn: details.append(f"← {src.group(1).split('/')[-1]}")
        if delim: details.append(f'delimeter="{delim.group(1)}"')
        if iform:  details.append(f'iform={iform.group(1)}')
        if oform:  details.append(f'oform={oform.group(1)}')
        if srch:   details.append(f'search="{srch.group(1)}"')
        if repl:   details.append(f'replace="{repl.group(1)}"')
        if defv:   details.append(f'default="{defv.group(1)}"')

        tag = f"[{' | '.join(details)}]" if details else "(parent)"
        print(f"  {dst.split('/ProductOutput/')[-1] if 'ProductOutput' in dst else seg:<45} {tag}")

# ── Verification ─────────────────────────────────────────────────────────────
print("\n--- FUNCTION VERIFICATION ---")
checks = [
    ("replaceString (replaceAll)",  "replaceString"      in func_bricks),
    ("toUpperCase",                  "toUpperCase"        in func_bricks),
    ("TransformDate (formatDate)",   "TransformDate"      in func_bricks),
    ("collapseContexts",             "collapseContexts"   in func_bricks),
    ("SplitByValue",                 "SplitByValue"       in func_bricks),
    ("sum (Statistics)",             "sum"                in func_bricks),
    ("count (Statistics)",           "count"              in func_bricks),
    ("index (Statistics)",           "index"              in func_bricks),
    ("useOneAsMany",                 "useOneAsMany"       in func_bricks),
    ("concat (+ shorthand)",         "concat"             in func_bricks),
    ("mapWithDefault",               "mapWithDefault"     in func_bricks),
    ("No first()/last() used",       "first" not in func_bricks and "last" not in func_bricks),
    ("Correct brick count (16)",     len(dst_bricks) == 16),
    ("delimeter binding in concat",  'name="delimeter"'  in mmap_xml),
    ("iform/oform in TransformDate", 'name="iform"'      in mmap_xml),
    ("default_value in mapWithDef",  'name="default_value"' in mmap_xml),
]

all_ok = True
for label, ok in checks:
    status = "OK  " if ok else "FAIL"
    print(f"  {status} {label}")
    if not ok: all_ok = False

print(f"\nRESULT: {'ALL {0} CHECKS PASSED ✓'.format(len(checks)) if all_ok else 'SOME CHECKS FAILED ✗'}")

# Save
with open(r'C:\Users\prem.am.kumar\Downloads\MM_ComplexNodeFunctions.zip', 'wb') as f:
    f.write(zip_bytes)
print(f"\nSaved to Downloads/MM_ComplexNodeFunctions.zip  ({len(zip_bytes):,} bytes)")
print("Ready to import into SAP CPI!")
