#!/usr/bin/env python3
"""
Citation-integrity self-test for the 6502-review skill.

This skill's entire value is *grounded* findings -- every rule and number cited,
never recalled. So the one thing worth checking automatically is that the
anchors it cites actually resolve. This does NOT run py65 or any harness (static
review needs neither); it only reads the two sibling reference files and confirms
every cited technique/part/section/category is present.

Locates the sibling skills via, in order:
  - $CODEGEN_DIR / $OPT_DIR
  - ../../6502-codegen and ../../6502-optimization (the usual sibling layout)
  - ../6502-codegen and ../6502-optimization

Run:  python scripts/selftest.py
Exit 0 == all citations resolve. Exit 2 if a sibling skill cannot be found.
"""
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))  # realpath: survive ~/.claude/skills symlinks


def _find(name, env):
    cands = []
    if os.environ.get(env):
        cands.append(os.environ[env])
    cands.append(os.path.normpath(os.path.join(HERE, "..", "..", name)))
    cands.append(os.path.normpath(os.path.join(HERE, "..", name)))
    for c in cands:
        if os.path.isdir(c):
            return c
    print("FAIL: cannot find the %s skill (needed to verify citations).\n"
          "Install it alongside this skill, or set %s.\nLooked in:\n  %s"
          % (name, env, "\n  ".join(cands)))
    sys.exit(2)


CODEGEN = _find("6502-codegen", "CODEGEN_DIR")
OPT = _find("6502-optimization", "OPT_DIR")

# Anchors cited by SKILL.md / references/review-rubric.md.
CODEGEN_ANCHORS = (
    ["### T%d:" % n for n in (1, 2, 6, 8, 9, 12, 14, 15, 20, 21,
                              26, 27, 28, 29, 30, 32, 33, 34, 35, 40)]
    + ["# PART III", "# PART VII", "# PART VIII", "# PART IX",
       "## SECTION 1", "## SECTION 2", "fully-formed target"]
)
OPT_ANCHORS = ["### %s" % c for c in
               ("A1", "A2", "B1", "B2", "B3", "C1", "C2", "C4", "C5", "C6", "D1", "D2")]

FAILS = []


def check(label, path, anchors):
    try:
        text = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        print("  [FAIL] %s -- file not found: %s" % (label, path))
        FAILS.append(label)
        return
    missing = [a for a in anchors if a not in text]
    ok = not missing
    print("  [%s] %-46s (%d anchors)%s"
          % ("PASS" if ok else "FAIL", label, len(anchors),
             "" if ok else "  missing: " + ", ".join(missing)))
    if not ok:
        FAILS.append(label)


print("6502-review citation-integrity self-test")
print("  codegen:      ", CODEGEN)
print("  optimization: ", OPT, "\n")
print("Cited anchors resolve in the sibling references:")
check("codegen reference", os.path.join(CODEGEN, "references", "6502_reference.md"),
      CODEGEN_ANCHORS)
check("optimization catalog", os.path.join(OPT, "references", "optimization-catalog.md"),
      OPT_ANCHORS)

print("\n" + ("ALL GREEN" if not FAILS else "FAILURES: " + ", ".join(FAILS)))
sys.exit(0 if not FAILS else 1)
