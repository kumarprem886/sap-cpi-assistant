"""Quick test of the sheet_mapper service."""
import sys
sys.path.insert(0, ".")

from services.sheet_mapper import parse_sheet, sheet_to_field_mappings
from services.xsd_parser import smart_extract_paths

SHEET = r"C:\Users\prem.am.kumar\Downloads\stocksnapshot mapping.xlsx"
SRC   = r"C:\Users\prem.am.kumar\Downloads\source.xsd"
TGT   = r"C:\Users\prem.am.kumar\Downloads\Target.xsd"

sheet_bytes = open(SHEET, "rb").read()
src_xsd     = open(SRC, encoding="utf-8").read()
tgt_xsd     = open(TGT, encoding="utf-8").read()

# 1. Parse sheet
rows = parse_sheet(sheet_bytes, "mapping.xlsx")
print(f"Sheet rows parsed: {len(rows)}")
for r in rows:
    print(f"  {r}")

# 2. Extract XSD paths
src_root, src_paths = smart_extract_paths(src_xsd)
tgt_root, tgt_paths = smart_extract_paths(tgt_xsd)
print(f"\nSource: root={src_root!r}  paths={len(src_paths)}")
print(f"Target: root={tgt_root!r}  paths={len(tgt_paths)}")

print("\nSource paths:")
for p in src_paths:
    print(f"  {p}")
print("\nTarget paths:")
for p in tgt_paths:
    print(f"  {p}")

# 3. Resolve mappings
matched, unmatched = sheet_to_field_mappings(sheet_bytes, "mapping.xlsx", src_paths, tgt_paths)
print(f"\n=== MATCHED ({len(matched)}) ===")
for m in matched:
    note = f"  [{m['note']}]" if m.get("note") else ""
    print(f"  {m['source_path']}  ->  {m['target_path']}{note}")

print(f"\n=== UNMATCHED ({len(unmatched)}) ===")
for u in unmatched:
    print(f"  {u}")
