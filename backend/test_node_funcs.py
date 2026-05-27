"""Test the generic node function rule parser."""
import sys
sys.path.insert(0, ".")
from services.sheet_mapper import _parse_rule

# Fake src_paths — enough to resolve field names
SRC = [
    "/msg/header/sender",
    "/msg/header/date",
    "/msg/header/time",
    "/msg/body/stockreport/ln/mn",
    "/msg/body/stockreport/ln/sl",
]

cases = [
    # concat shorthand (existing)
    ("(/msg/header/date)+T+(/msg/header/time)",       "concat",         3),
    # explicit concat
    ("concat((/msg/header/date), T, (/msg/header/time))", "concat",    3),
    # single-arg functions
    ("toUpperCase((/msg/header/sender))",             "toUpperCase",    1),
    ("toLowerCase((/msg/header/sender))",             "toLowerCase",    1),
    ("trim((/msg/header/sender))",                    "trim",           1),
    ("length((/msg/header/sender))",                  "length",         1),
    # multi-arg functions
    ("substring((/msg/header/time), 0, 6)",           "substring",      3),
    ("formatDate((/msg/header/date), yyyyMMdd, yyyy-MM-dd)", "formatDate", 3),
    ("replaceAll((/msg/header/sender), [^A-Z], )",    "replaceAll",     3),
    ("mapWithDefault((/msg/body/stockreport/ln/mn), A, Alpha, B, Beta)", "mapWithDefault", 5),
    ("splitByValue((/msg/header/sender), -)",         "splitByValue",   2),
    ("UseOneAsMany((/msg/header/date))",              "UseOneAsMany",   1),
    # nested: if + equals
    ("if(equals((/msg/header/sender), SENDER), Y, N)", "if",           3),
    # unparseable → None
    ("just some free text",                           None,             0),
]

print(f"{'Rule':<55} {'Func':<18} {'Parts'} {'OK?'}")
print("-" * 90)
all_ok = True
for rule, exp_func, exp_parts in cases:
    result = _parse_rule(rule, SRC)
    if result is None:
        ok = (exp_func is None)
        print(f"{rule[:54]:<55} {'None':<18} {0:<6} {'OK' if ok else 'FAIL'}")
    else:
        func, parts = result
        ok = (func == exp_func) and (len(parts) == exp_parts)
        print(f"{rule[:54]:<55} {func:<18} {len(parts):<6} {'OK' if ok else f'FAIL (expected {exp_func}/{exp_parts})'}")
        if not ok:
            print(f"  parts: {parts}")
    if not ok:
        all_ok = False

print()
print("ALL PASS" if all_ok else "SOME FAILURES")
