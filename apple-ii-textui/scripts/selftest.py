#!/usr/bin/env python3
"""Self-test for the apple-ii-textui helper scripts."""
import os
import subprocess
import sys
import tempfile


SCRIPT = os.path.join(os.path.dirname(__file__), "decode_screen.py")


def run_decode(aux_text, main_text):
    with tempfile.TemporaryDirectory() as d:
        aux = os.path.join(d, "aux.txt")
        main = os.path.join(d, "main.txt")
        with open(aux, "w") as f:
            f.write(aux_text)
        with open(main, "w") as f:
            f.write(main_text)
        return subprocess.run(
            [sys.executable, SCRIPT, aux, main, "--row", "0", "--codes"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


def report(name, ok, detail=""):
    print(("PASS" if ok else "FAIL") + f": {name}" + (f"  {detail}" if detail else ""))
    return ok


def main():
    simple = ("A0 " * 1024).strip()
    mcp_line = "0400: " + " ".join(["A0"] * 16) + " |                |\n"
    mcp_dump = mcp_line * 64

    ok = True

    p = run_decode(simple, simple)
    ok &= report("plain hex text decodes as screen bytes", p.returncode == 0 and "A0 A0 A0" in p.stdout,
                 p.stderr.strip())

    p = run_decode(mcp_dump, mcp_dump)
    ok &= report("MCP address/gutter hex dump decodes as screen bytes",
                 p.returncode == 0 and "r 0: A0 A0 A0" in p.stdout,
                 (p.stdout.splitlines()[0] if p.stdout else p.stderr.strip()))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
