#!/usr/bin/env python3
"""
Turnkey verifier for the 6502-codegen skill.

Reads a JSON test spec (file arg or stdin), assembles the routine for the
chosen CPU, runs each case in a simulator, and reports PASS/FAIL. Exit 0 iff
all cases pass. No Python to write -- just fill in the numbers.

JSON spec (this sample is valid JSON -- copy and edit; JSON has no comments):
{
  "program": ["DBL      ASL ZP_TMP", "         RTS"],
  "origin":  768,
  "cpu":     "nmos",
  "cases": [
    { "set":    {"ZP_TMP": 33, "C": 0},
      "tables": false,
      "steps":  50,
      "expect": {"ZP_TMP": 66, "C": 0, "Z": 0} }
  ]
}

A key in set/expect may be:
  - memory: an int, "0x04", "$04", a decimal string, or a workspace symbol
    name like "ZP_PTR" / "ZP_PTR+1";
  - a register: "A", "X", "Y", "SP", "P";
  - a flag: "C","Z","I","D","V","N" (or carry/zero/decimal/overflow/negative),
    value 0/1 or true/false.
PC/SP cannot be set as inputs (the runner seeds them). Values may be ints or
hex/binary strings. "cpu" is "nmos" (default) or "65c02".

CPU note: "nmos" and "65c02" execute. Some code must be paper-verified against
the reference instead: native-816 ops and BBR/BBS/STP won't assemble; WAI and
BRK assemble but never reach RTS (WAI waits for an interrupt; BRK needs a
handler/vector). The verifier flags a WAI wait-state distinctly, not as a
timeout.

Usage:
    python run.py spec.json
    cat spec.json | python run.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import harness  # noqa: E402
except RuntimeError as e:   # py65 missing -> actionable message, no traceback
    print(str(e))
    sys.exit(2)


def main():
    try:
        if len(sys.argv) > 1:
            with open(sys.argv[1]) as f:
                spec = json.load(f)
        else:
            spec = json.load(sys.stdin)
    except Exception as e:
        print("ERROR reading JSON spec: %s" % e)
        sys.exit(2)

    program = spec.get("program")
    origin = spec.get("origin", 0x0300)
    cpu = spec.get("cpu", "nmos")
    cases = spec.get("cases", [])
    if not program or not cases:
        print("ERROR: spec needs non-empty 'program' and 'cases'.")
        sys.exit(2)

    try:
        all_ok, results = harness.run_cases(program, origin, cases, cpu=cpu)
    except Exception as e:
        print("ASSEMBLY/RUN ERROR: %s" % e)
        sys.exit(2)

    for r in results:
        tag = "PASS" if r["passed"] else "FAIL"
        print("case %d: %s" % (r["index"], tag))
        for f in r["failures"]:
            print("    - %s" % f)
    print("-" * 40)
    print("%d/%d cases passed (cpu=%s)"
          % (sum(1 for r in results if r["passed"]), len(results), cpu))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
