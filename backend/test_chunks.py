import sys
sys.path.insert(0, ".")
from services.prebuilt_mapper import _MAX_SRC_CHARS, _MAX_TGT_CHUNK_CHARS, _MAX_OUTPUT_TOKENS, _PREBUILT_MODEL, _trim_leaves, _chunk_target_leaves
from services.xsd_parser import smart_extract_paths, leaf_paths
import pathlib

r = pathlib.Path("../resources")

pairs = [
    ("DEBMAS06.xsd", "A_BusinessPartner.xsd"),
    ("CREMAS05.xsd", "A_Supplier.xsd"),
    ("ORDERS05.xsd", "A_PurchaseOrder.xsd"),
    ("INVOIC02.xsd", "A_SupplierInvoice.xsd"),
]

def _src_sort_key(path):
    seg = path.split("/")[3] if path.count("/") >= 3 else ""
    if seg.startswith("E1") or seg.startswith("Z1"): return 0
    if seg == "EDI_DC40": return 2
    return 1

for src_file, tgt_file in pairs:
    src_xsd = (r / src_file).read_text(encoding="utf-8")
    tgt_xsd = (r / tgt_file).read_text(encoding="utf-8")
    src_root, src_paths = smart_extract_paths(src_xsd)
    tgt_root, tgt_paths = smart_extract_paths(tgt_xsd)
    src_leaves = leaf_paths(src_paths)
    tgt_leaves = leaf_paths(tgt_paths)

    src_sorted = sorted(src_leaves, key=_src_sort_key)
    src_trimmed = _trim_leaves(src_sorted, _MAX_SRC_CHARS)
    tgt_chunks = _chunk_target_leaves(tgt_leaves)

    src_chars = sum(len(p)+2 for p in src_trimmed)
    api_calls = len(tgt_chunks)

    print(f"{src_file} -> {tgt_file}:")
    print(f"  src: {len(src_leaves)} leaves -> {len(src_trimmed)} trimmed ({src_chars} chars)")
    print(f"  tgt: {len(tgt_leaves)} leaves -> {api_calls} chunks")
    for i, c in enumerate(tgt_chunks):
        chars = sum(len(p)+2 for p in c)
        est_tokens = (src_chars + chars) // 4 + 320 + 250 + _MAX_OUTPUT_TOKENS
        print(f"    chunk {i}: {len(c)} leaves, {chars} chars, ~{est_tokens} total tokens")
    print()
