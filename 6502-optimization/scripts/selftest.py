#!/usr/bin/env python3
"""
Self-test for the 6502-optimization skill.

1. Confirms equiv.py can reach the 6502-codegen harness (imports it).
2. Proves the equivalence spine works in BOTH directions:
   - a genuine optimization (same output, fewer cycles) is reported EQUIVALENT;
   - equiv detects a register-clobber difference under the default (full) compare;
   - a broken "optimization" (off-by-one) is reported as DIFFERING.
3. Checks every 6502-codegen pointer cited in references/optimization-catalog.md
   actually resolves in that skill's reference file.

Run:  python scripts/selftest.py
Exit 0 == all green. Exits 2 if 6502-codegen / py65 are not reachable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import equiv   # locates 6502-codegen and imports its harness (may sys.exit 2)
except Exception as e:
    print("FAIL: %s" % e)
    sys.exit(2)

ORG = 0x0300
FAILS = []


def report(name, ok, extra=""):
    print("  [%s] %-42s%s" % ("PASS" if ok else "FAIL", name,
                              ("  -- " + extra) if extra and not ok else ""))
    if not ok:
        FAILS.append(name)


# Three routines that all "clear 8 bytes at $0400", with known differences.
# NAIVE: count up with CPX; ends X=8.
NAIVE = ["NAIVE LDX #$00", "      LDA #$00",
         ":L   STA $0400,X", "      INX", "      CPX #$08", "      BNE :L",
         "      RTS"]
# OPT: count down (no CPX); same memory result, but ends X=0.
OPT = ["OPT   LDX #$08", "      LDA #$00",
       ":L   STA $03FF,X", "      DEX", "      BNE :L",
       "      RTS"]
# BROKEN: off-by-one, only clears $0400..$0406 (misses $0407).
BROKEN = ["BAD   LDX #$07", "      LDA #$00",
          ":L   STA $03FF,X", "      DEX", "      BNE :L",
          "      RTS"]

OUTBYTES = ["$0400", "$0401", "$0402", "$0403", "$0404", "$0405", "$0406", "$0407"]
# prefill the last byte so a missed clear is detectable
CASE = [{"set": {"$0407": 0xFF}, "steps": 100}]

print("6502-optimization self-test")
print("equiv.py reached 6502-codegen at:", equiv.CODEGEN_DIR, "\n")
print("Equivalence spine:")

# 1) genuine optimization, scoped to the real contract (the 8 output bytes)
ok, res = equiv.compare(NAIVE, OPT, CASE, origin=ORG, observe=OUTBYTES)
report("true optimization -> EQUIVALENT (observe outputs)", ok,
       "" if ok else "; ".join(res[0]["diffs"]))

# 2) default (full) compare must NOTICE the X-register difference (8 vs 0)
ok2, res2 = equiv.compare(NAIVE, OPT, CASE, origin=ORG)   # no observe
saw_x = (not ok2) and any("X:" in d for d in res2[0]["diffs"])
report("default compare flags X clobber (8 vs 0)", saw_x,
       "expected an X difference; got: " + "; ".join(res2[0]["diffs"]))

# 3) broken optimization must be caught at the missed byte
ok3, res3 = equiv.compare(NAIVE, BROKEN, CASE, origin=ORG, observe=OUTBYTES)
saw_0407 = (not ok3) and any("$0407" in d for d in res3[0]["diffs"])
report("broken optimization -> DIFFERS at $0407", saw_0407,
       "expected a $0407 difference; got: " + "; ".join(res3[0]["diffs"]))

# ---- catalog pointers must resolve in the 6502-codegen reference ----
print("\nCatalog integrity (pointers into 6502-codegen resolve):")
ref_path = os.path.join(equiv.CODEGEN_DIR, "references", "6502_reference.md")
cited = ["### T1:", "### T2:", "### T3:", "### T8:", "### T9:", "### T11:",
         "### T12:", "### T14:", "### T15:", "### T18:", "### T20:", "### T21:",
         "### T22:", "### T23:",
         "### T28:", "### T30:", "### T32:", "### T33:", "### T34:", "### T35:",
         "# PART III", "# PART VII", "## SECTION 2", "fully-formed target"]
try:
    ref = open(ref_path, encoding="utf-8").read()
    missing = [c for c in cited if c not in ref]
    report("cited codegen anchors exist (%d)" % len(cited), not missing,
           "missing: " + ", ".join(missing))
except FileNotFoundError:
    report("codegen reference file present", False, "not found at %s" % ref_path)

print("\n" + ("ALL GREEN" if not FAILS else "FAILURES: " + ", ".join(FAILS)))
sys.exit(0 if not FAILS else 1)
