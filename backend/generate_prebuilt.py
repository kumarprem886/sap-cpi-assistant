"""
Standalone script to generate prebuilt mappings with visible output.
Run from backend/ directory (set PYTHONIOENCODING=utf-8 env var first on Windows):
  set PYTHONIOENCODING=utf-8 && python generate_prebuilt.py
"""
import sys, time
sys.path.insert(0, ".")

from services.prebuilt_mapper import (
    CATALOG_PAIRS, generate_mapping_for_pair, save_prebuilt, load_prebuilt
)

PAIR_DELAY = 15  # seconds between pairs

def main():
    pending = []
    for pair in CATALOG_PAIRS:
        existing = load_prebuilt(pair["id"])
        if existing and existing.get("total_fields", 0) > 0:
            print(f"[SKIP]  {pair['id']} ({existing['total_fields']} fields already)")
        else:
            pending.append(pair)

    print(f"\n{len(pending)} pairs to generate out of {len(CATALOG_PAIRS)} total.\n")

    for i, pair in enumerate(pending):
        if i > 0:
            print(f"  ... waiting {PAIR_DELAY}s between pairs ...")
            time.sleep(PAIR_DELAY)

        print(f"\n[{i+1}/{len(pending)}] Generating: {pair['id']}")
        try:
            mapping = generate_mapping_for_pair(pair, verbose=True)
            save_prebuilt(mapping)
            print(f"  => DONE: {mapping['total_fields']} fields mapped")
        except Exception as e:
            print(f"  => ERROR: {e}")

    print("\n=== All done ===")

if __name__ == "__main__":
    main()
