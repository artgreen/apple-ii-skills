#!/usr/bin/env python3
"""
Equivalence prover for the 6502-optimization skill.

An optimization is valid only if the optimized routine produces identical
observable results to the original across a test corpus. This module does NOT
re-implement assembly or simulation -- it rides on the 6502-codegen skill's
verified harness (one engine, one source of truth) and adds only the
two-routine comparison.

Dependency: the 6502-codegen skill must be installed. It is located, in order:
  1. $CODEGEN_DIR                              (path to the codegen skill root)
  2. ../../6502-codegen   relative to this file (sibling skill, the usual case)
  3. ../6502-codegen      relative to this file
("relative to this file" resolves symlinks first, so a symlink in
~/.claude/skills still finds the real sibling in the repo checkout)
Then py65 must be importable (see codegen's dependency note for the venv hint).

Public API:
    compare(original, optimized, cases, origin=0x0300, cpu="nmos",
            entry=None, observe=None) -> (all_equivalent, results)

`original` / `optimized` are Merlin-style source line lists (the same form the
codegen harness assembles). `cases` use the harness shape: each a dict with
optional "set" (initial memory/registers/flags), "tables" (bool), "steps" (int).
No "expect" is needed -- the ORIGINAL routine defines the truth.

`observe` selects what counts as observable output: a list of memory addresses
("$2000", "0x04", "WORKBUF+1", int) and/or registers ("A","X","Y","SP","P") and
/or flags ("C","Z","I","D","V","N"). If omitted, the entire 64K memory image
plus A/X/Y is compared (conservative: surfaces unintended scratch/clobber
differences too). Status flags are NOT compared unless named in `observe`,
because equivalent routines often leave harmless flag residue.
"""
import os
import sys


def _find_codegen():
    cands = []
    env = os.environ.get("CODEGEN_DIR")
    if env:
        cands.append(env)
    here = os.path.dirname(os.path.realpath(__file__))  # realpath: survive ~/.claude/skills symlinks
    cands.append(os.path.normpath(os.path.join(here, "..", "..", "6502-codegen")))
    cands.append(os.path.normpath(os.path.join(here, "..", "6502-codegen")))
    for c in cands:
        if os.path.isfile(os.path.join(c, "scripts", "harness.py")):
            return c
    raise RuntimeError(
        "Cannot find the 6502-codegen skill (needed for the simulator harness).\n"
        "Install it alongside this skill, or set CODEGEN_DIR to its root.\n"
        "Looked in:\n  " + "\n  ".join(cands))


CODEGEN_DIR = _find_codegen()   # raises RuntimeError (with guidance) if missing
sys.path.insert(0, os.path.join(CODEGEN_DIR, "scripts"))
import harness  # noqa: E402  -- raises RuntimeError (venv hint) if py65 is absent


def _exec(code, start, cpu, case):
    """Fresh MPU (right core via codegen), load, apply inputs, run from `start`."""
    mpu, _ = harness._make(cpu)
    harness.load(mpu, code)
    if case.get("tables"):
        harness.make_tables(mpu)
    for k, v in case.get("set", {}).items():
        harness._apply_set(mpu, k, v)
    returned = harness.run(mpu, start, case.get("steps", 100000))
    return mpu, returned


def _reg(mpu, name):
    return {'A': mpu.a, 'X': mpu.x, 'Y': mpu.y,
            'SP': mpu.sp, 'P': mpu.p, 'PC': mpu.pc}[name]


def _diff(m0, m1, observe):
    """Return a list of human-readable difference strings (m0=original)."""
    out = []
    if observe:
        for k in observe:
            kind, info = harness._key_kind(k)
            if kind == 'reg':
                a, b = _reg(m0, info), _reg(m1, info)
                if a != b:
                    out.append("%s: original=$%02X optimized=$%02X" % (info, a, b))
            elif kind == 'flag':
                a = 1 if (m0.p & info) else 0
                b = 1 if (m1.p & info) else 0
                if a != b:
                    out.append("flag %s: original=%d optimized=%d" % (k, a, b))
            else:
                a, b = m0.memory[info], m1.memory[info]
                if a != b:
                    out.append("mem[%s]: original=$%02X optimized=$%02X" % (k, a, b))
        return out
    # default: full 64K image + A/X/Y (not flags)
    for addr in range(0x10000):
        if m0.memory[addr] != m1.memory[addr]:
            out.append("mem[$%04X]: original=$%02X optimized=$%02X"
                       % (addr, m0.memory[addr], m1.memory[addr]))
            if len(out) >= 16:
                out.append("... (more memory differences suppressed)")
                break
    for name in ('A', 'X', 'Y'):
        a, b = _reg(m0, name), _reg(m1, name)
        if a != b:
            out.append("%s: original=$%02X optimized=$%02X" % (name, a, b))
    return out


def compare(original, optimized, cases, origin=0x0300, cpu="nmos",
            entry=None, observe=None):
    """Prove `optimized` matches `original` on every case. See module docstring.

    Returns (all_equivalent, results), results a list of
      {"index", "equivalent", "diffs": [...]}.
    """
    code0, syms0, _ = harness.assemble(original, origin, cpu)
    code1, syms1, _ = harness.assemble(optimized, origin, cpu)

    def _start(syms):
        if entry is None:
            return origin
        return syms[entry] if isinstance(entry, str) else entry

    s0, s1 = _start(syms0), _start(syms1)
    results = []
    all_ok = True
    for i, case in enumerate(cases):
        m0, ret0 = _exec(code0, s0, cpu, case)
        m1, ret1 = _exec(code1, s1, cpu, case)
        diffs = []
        if ret0 != ret1:
            diffs.append("return/halt differs: original returned=%s optimized returned=%s "
                         "(one may have run away, jammed, or hit WAI)" % (ret0, ret1))
        diffs += _diff(m0, m1, observe)
        ok = not diffs
        all_ok = all_ok and ok
        results.append({"index": i, "equivalent": ok, "diffs": diffs})
    return all_ok, results


def report(original, optimized, cases, **kw):
    """Convenience: run compare and print a PASS/FAIL summary. Returns bool."""
    all_ok, results = compare(original, optimized, cases, **kw)
    for r in results:
        tag = "EQUIVALENT" if r["equivalent"] else "DIFFERS"
        print("case %d: %s" % (r["index"], tag))
        for d in r["diffs"]:
            print("    - %s" % d)
    print("-" * 50)
    print("%d/%d cases equivalent"
          % (sum(1 for r in results if r["equivalent"]), len(results)))
    return all_ok


if __name__ == "__main__":
    print("equiv.py is a library. Import it:")
    print('    import sys; sys.path.insert(0, "scripts"); import equiv')
    print("    ok, results = equiv.compare(original, optimized, cases, cpu=...)")
    print("Using 6502-codegen at:", CODEGEN_DIR)
