import sys, re
sys.path.insert(0, ".")
from services.sheet_mapper import sheet_to_field_mappings
from services.xsd_parser import smart_extract_paths
from services.mmap_builder import build_mmap_xml, build_mmap_zip

SHEET = r"C:\Users\prem.am.kumar\Downloads\stocksnapshot mapping.xlsx"
SRC   = r"C:\Users\prem.am.kumar\Downloads\source.xsd"
TGT   = r"C:\Users\prem.am.kumar\Downloads\Target.xsd"

sheet = open(SHEET, "rb").read()
src   = open(SRC, encoding="utf-8").read()
tgt   = open(TGT, encoding="utf-8").read()

_, sp = smart_extract_paths(src)
_, tp = smart_extract_paths(tgt)
matched, unmatched = sheet_to_field_mappings(sheet, "mapping.xlsx", sp, tp)

xml = build_mmap_xml("MM_StockSheet", "source.xsd", "msg",
                     "Target.xsd", "Header", matched)

# Show bricks for RunDate (they should contain concat)
print("=== RunDate bricks ===")
# Regex to find Dst bricks for RunDate paths
for m in re.finditer(r'<brick gid="0" path="[^"]*RunDate[^"]*" type="Dst">.*?</brick>', xml, re.DOTALL):
    snippet = m.group(0)
    print(snippet[:700])
    print()

# Confirm concat funcName appears
concat_count = xml.count('funcName="concat"')
const_t_count = xml.count('constValue="T"')
print(f"funcName=\"concat\" occurrences: {concat_count}")
print(f'constValue="T" occurrences:    {const_t_count}')

# Save the zip for manual import test
zip_bytes = build_mmap_zip("MM_StockSheet", xml, src, tgt, "source.xsd", "Target.xsd")
out = r"C:\Users\prem.am.kumar\Downloads\MM_StockSheet.zip"
open(out, "wb").write(zip_bytes)
print(f"\nZIP written: {out}  ({len(zip_bytes)} bytes)")
