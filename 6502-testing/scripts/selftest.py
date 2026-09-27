#!/usr/bin/env python3
"""Self-test for the 6502-testing helper scripts."""
import os
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))


def report(name, ok, detail=""):
    print(("PASS" if ok else "FAIL") + f": {name}" + (f"  {detail}" if detail else ""))
    return ok


def main():
    ok = True

    env = os.environ.copy()
    env.pop("CODEGEN_DIR", None)
    with tempfile.TemporaryDirectory() as home:
        env["HOME"] = home
        env["PYTHONPATH"] = HERE
        code = (
            "import os, sim; "
            "h = sim._load_harness(); "
            "print(os.path.realpath(h.__file__))"
        )
        p = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    ok &= report(
        "sim.py finds sibling 6502-codegen without ~/.claude default",
        p.returncode == 0 and "/6502-codegen/scripts/harness.py" in p.stdout,
        p.stderr.strip() or p.stdout.strip(),
    )

    smoke = subprocess.run(
        [sys.executable, os.path.join(HERE, "sim.py")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    ok &= report("sim.py smoke test", smoke.returncode == 0,
                 smoke.stderr.strip() or smoke.stdout.strip())

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
