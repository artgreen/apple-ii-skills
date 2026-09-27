#!/usr/bin/env python3
"""
Self-test / regression suite for the 6502-codegen skill.

1. Confirms the simulator dependency (py65) is present.
2. Re-verifies every routine shipped in references/6502_reference.md by
   assembling it (Merlin syntax, exactly as printed) and checking results
   against ground truth across a sample + all edge cases.
3. Checks reference integrity: every section/technique ID that SKILL.md
   routes to actually exists in the reference file.

Run:  python scripts/selftest.py
Exit code 0 == all green.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import harness
    from harness import assemble, load, make_tables, run, s8, s16
except Exception as e:
    print("FAIL: %s" % e)
    sys.exit(2)

random.seed(1234)
ORG = 0x0300
FAILS = []


def report(name, n, bad, extra=""):
    tag = "PASS" if not bad else "FAIL"
    print("  [%s] %-26s %d checks%s" % (tag, name, n, (" — " + extra) if extra else ""))
    if bad:
        FAILS.append(name)


# ---- routines transcribed verbatim from references/6502_reference.md ----
MUL8 = [
 "MUL8     LDA   #$00", "         STA   ZP_PTR+1", "         LDX   #$08",
 ":ROT     LSR   ZP_TMP2", "         BCC   :NOADD", "         CLC",
 "         ADC   ZP_TMP", ":NOADD   ROR   A", "         ROR   ZP_PTR",
 "         DEX", "         BNE   :ROT", "         STA   ZP_PTR+1", "         RTS",
]
MUL_QS = [
 "MUL_QS   LDA   #>SQLO", "         STA   ZP_PTR+1", "         CLC",
 "         LDA   ZP_TMP", "         ADC   ZP_TMP2", "         STA   ZP_PTR",
 "         LDA   ZP_PTR+1", "         ADC   #$00", "         STA   ZP_PTR+1",
 "         LDY   #$00", "         LDA   (ZP_PTR),Y", "         STA   ZP_PTR2",
 "         LDA   ZP_PTR+1", "         CLC", "         ADC   #$02",
 "         STA   ZP_PTR+1", "         LDA   (ZP_PTR),Y", "         STA   ZP_STATE",
 "         SEC", "         LDA   ZP_TMP", "         SBC   ZP_TMP2",
 "         BCS   :DPOS", "         SEC", "         LDA   ZP_TMP2",
 "         SBC   ZP_TMP", ":DPOS    TAX", "         SEC", "         LDA   ZP_PTR2",
 "         SBC   SQLO,X", "         STA   ZP_PTR", "         LDA   ZP_STATE",
 "         SBC   SQHI,X", "         STA   ZP_PTR+1", "         RTS",
]
DIV8 = [
 "DIV8     LDA   #$00", "         LDX   #$08", ":LOOP    ASL   ZP_TMP",
 "         ROL   A", "         CMP   ZP_TMP2", "         BCC   :SKIP",
 "         SBC   ZP_TMP2", "         INC   ZP_TMP", ":SKIP    DEX",
 "         BNE   :LOOP", "         RTS",
]
BIN2BCD = [
 "BIN2BCD  SED", "         LDA   #$00", "         STA   ZP_PTR",
 "         STA   ZP_PTR+1", "         LDX   #$08", ":LOOP    ASL   ZP_TMP",
 "         LDA   ZP_PTR", "         ADC   ZP_PTR", "         STA   ZP_PTR",
 "         LDA   ZP_PTR+1", "         ADC   ZP_PTR+1", "         STA   ZP_PTR+1",
 "         DEX", "         BNE   :LOOP", "         CLD", "         RTS",
]
BCD2BIN = [
 "BCD2BIN  LDA   #$00", "         STA   ZP_PTR2", "         STA   ZP_PTR2+1",
 "         LDA   ZP_PTR+1", "         LSR", "         LSR", "         LSR",
 "         LSR", "         JSR   MUL10ADD", "         LDA   ZP_PTR+1",
 "         AND   #$0F", "         JSR   MUL10ADD", "         LDA   ZP_PTR",
 "         LSR", "         LSR", "         LSR", "         LSR",
 "         JSR   MUL10ADD", "         LDA   ZP_PTR", "         AND   #$0F",
 "         JSR   MUL10ADD", "         RTS",
 "MUL10ADD PHA", "         LDA   ZP_PTR2", "         STA   ZP_TMP",
 "         LDA   ZP_PTR2+1", "         STA   ZP_TMP2", "         ASL   ZP_PTR2",
 "         ROL   ZP_PTR2+1", "         ASL   ZP_PTR2", "         ROL   ZP_PTR2+1",
 "         CLC", "         LDA   ZP_PTR2", "         ADC   ZP_TMP",
 "         STA   ZP_PTR2", "         LDA   ZP_PTR2+1", "         ADC   ZP_TMP2",
 "         STA   ZP_PTR2+1", "         ASL   ZP_PTR2", "         ROL   ZP_PTR2+1",
 "         PLA", "         CLC", "         ADC   ZP_PTR2", "         STA   ZP_PTR2",
 "         LDA   ZP_PTR2+1", "         ADC   #$00", "         STA   ZP_PTR2+1",
 "         RTS",
]
SMUL8 = [
 "SMUL8    LDA   ZP_TMP", "         EOR   ZP_TMP2", "         STA   ZP_STATE",
 "         LDA   ZP_TMP", "         BPL   :AOK", "         EOR   #$FF",
 "         CLC", "         ADC   #$01", "         STA   ZP_TMP",
 ":AOK     LDA   ZP_TMP2", "         BPL   :BOK", "         EOR   #$FF",
 "         CLC", "         ADC   #$01", "         STA   ZP_TMP2",
 ":BOK     JSR   MUL8", "         LDA   ZP_STATE", "         BPL   :DONE",
 "         LDA   ZP_PTR", "         EOR   #$FF", "         CLC", "         ADC   #$01",
 "         STA   ZP_PTR", "         LDA   ZP_PTR+1", "         EOR   #$FF",
 "         ADC   #$00", "         STA   ZP_PTR+1", ":DONE    RTS",
] + MUL8
SDIV8 = [
 "SDIV8    LDA   ZP_TMP", "         EOR   ZP_TMP2", "         STA   ZP_STATE",
 "         LDA   ZP_TMP", "         STA   ZP_COUNT", "         LDA   ZP_TMP",
 "         BPL   :AOK", "         EOR   #$FF", "         CLC", "         ADC   #$01",
 "         STA   ZP_TMP", ":AOK     LDA   ZP_TMP2", "         BPL   :BOK",
 "         EOR   #$FF", "         CLC", "         ADC   #$01", "         STA   ZP_TMP2",
 ":BOK     JSR   DIV8", "         STA   ZP_PTR+1", "         LDA   ZP_TMP",
 "         STA   ZP_PTR", "         LDA   ZP_STATE", "         BPL   :QOK",
 "         LDA   ZP_PTR", "         EOR   #$FF", "         CLC", "         ADC   #$01",
 "         STA   ZP_PTR", ":QOK     LDA   ZP_COUNT", "         BPL   :ROK",
 "         LDA   ZP_PTR+1", "         EOR   #$FF", "         CLC", "         ADC   #$01",
 "         STA   ZP_PTR+1", ":ROK     RTS",
] + DIV8


def pairs(edges):
    pool = list(edges)
    for _ in range(300):
        pool.append((random.randint(0, 255), random.randint(0, 255)))
    return pool


print("6502-codegen self-test")
print("py65 present, harness imported OK\n")
print("Routine verification (sample + edges):")

# MUL8
code, _, _ = assemble(MUL8, ORG); n = bad = 0
for a, b in pairs([(0, 0), (0, 255), (255, 0), (255, 255), (1, 1), (16, 16),
                   (200, 200), (128, 2), (255, 1)]):
    m = harness.MPU(); load(m, code)
    m.memory[0x04] = a; m.memory[0x05] = b; m.memory[0x00] = 0xAA  # garbage prod-lo
    run(m, ORG, 200); n += 1
    if (m.memory[0x00] | (m.memory[0x01] << 8)) != a * b: bad += 1
report("MUL8 (unsigned mul)", n, bad)

# MUL_QS
code, _, _ = assemble(MUL_QS, ORG); n = bad = 0
for a, b in pairs([(0, 0), (255, 255), (256 and 255, 1), (1, 255), (200, 200),
                   (128, 128), (16, 16), (99, 99)]):
    m = harness.MPU(); load(m, code); make_tables(m)
    m.memory[0x04] = a; m.memory[0x05] = b
    run(m, ORG, 200); n += 1
    if (m.memory[0x00] | (m.memory[0x01] << 8)) != a * b: bad += 1
report("MUL_QS (quarter-square)", n, bad)

# DIV8
code, _, _ = assemble(DIV8, ORG); n = bad = 0
edges = [(0, 1), (255, 1), (255, 255), (254, 5), (100, 7), (255, 16), (1, 255)]
pool = edges + [(random.randint(0, 255), random.randint(1, 255)) for _ in range(300)]
for dv, ds in pool:
    m = harness.MPU(); load(m, code)
    m.memory[0x04] = dv; m.memory[0x05] = ds
    run(m, ORG, 200); n += 1
    if m.memory[0x04] != dv // ds or m.a != dv % ds: bad += 1
report("DIV8 (unsigned div)", n, bad)

# BIN2BCD (all 256)
code, _, _ = assemble(BIN2BCD, ORG); n = bad = 0
for v in range(256):
    m = harness.MPU(); load(m, code); m.memory[0x04] = v
    run(m, ORG, 200); n += 1
    lo = m.memory[0x00]; hi = m.memory[0x01]
    if (hi & 0x0F) * 100 + (lo >> 4) * 10 + (lo & 0x0F) != v: bad += 1
report("BIN2BCD (bin->decimal)", n, bad)

# BCD2BIN (edges + sample)
code, _, _ = assemble(BCD2BIN, ORG); n = bad = 0
vals = [0, 1, 9, 10, 99, 100, 101, 999, 1000, 5678, 9999] + \
       [random.randint(0, 9999) for _ in range(400)]
for v in vals:
    th = v // 1000; hu = (v // 100) % 10; te = (v // 10) % 10; un = v % 10
    m = harness.MPU(); load(m, code)
    m.memory[0x00] = (te << 4) | un; m.memory[0x01] = (th << 4) | hu
    run(m, ORG, 400); n += 1
    if (m.memory[0x02] | (m.memory[0x03] << 8)) != v: bad += 1
report("BCD2BIN (decimal->bin)", n, bad)

# SMUL8 (signed)
code, _, _ = assemble(SMUL8, ORG); n = bad = 0
sedges = [(-128, -128), (-128, 127), (127, 127), (-1, 1), (0, 5), (-7, 3), (100, -2)]
spool = sedges + [(random.randint(-128, 127), random.randint(-128, 127)) for _ in range(300)]
for a, b in spool:
    m = harness.MPU(); load(m, code)
    m.memory[0x04] = a & 0xFF; m.memory[0x05] = b & 0xFF
    run(m, ORG, 260); n += 1
    if s16(m.memory[0x00] | (m.memory[0x01] << 8)) != a * b: bad += 1
report("SMUL8 (signed mul)", n, bad)

# SDIV8 (signed, truncate toward zero)
def tdivmod(a, b):
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0): q = -q
    return q, a - q * b
code, _, _ = assemble(SDIV8, ORG); n = bad = 0
dedges = [(-7, 2), (7, -2), (-7, -2), (-128, 3), (127, -4), (0, 5), (-100, 7), (-128, -1)]
dpool = dedges + [(random.randint(-128, 127), random.choice([x for x in range(-128, 128) if x]))
                  for _ in range(300)]
for a, b in dpool:
    m = harness.MPU(); load(m, code)
    m.memory[0x04] = a & 0xFF; m.memory[0x05] = b & 0xFF
    run(m, ORG, 260); n += 1
    qw, rw = tdivmod(a, b)
    if s8(m.memory[0x01]) != rw: bad += 1
    elif -128 <= qw <= 127 and s8(m.memory[0x00]) != qw: bad += 1
    elif not (-128 <= qw <= 127) and m.memory[0x00] != (qw & 0xFF): bad += 1
report("SDIV8 (signed div)", n, bad)

# ---- 65C02 path: CMOS instructions assemble AND execute (cpu="65c02") ----
print("\n65C02 path (cpu='65c02'):")
c02_checks = [
    ("STZ clears mem, keeps A", ["T STZ $2000", "  RTS"],
     {"$2000": 0xAA, "A": 0x99}, {"$2000": 0, "A": 0x99}),
    ("PHX/PLX round-trip", ["T PHX", "  LDX #$00", "  PLX", "  RTS"],
     {"X": 0x11}, {"X": 0x11}),
    ("TSB sets bits (0x05|0x06)", ["T TSB $04", "  RTS"],
     {"$04": 0x05, "A": 0x06}, {"$04": 0x07}),
    ("TRB clears bits (0x07&~0x06)", ["T TRB $04", "  RTS"],
     {"$04": 0x07, "A": 0x06}, {"$04": 0x01}),
    ("BIT #imm sets Z, keeps A", ["T BIT #$F0", "  RTS"],
     {"A": 0x0F}, {"Z": 1, "A": 0x0F}),
    ("(zp) indirect load", ["T LDA ($10)", "  STA $04", "  RTS"],
     {"$10": 0x34, "$11": 0x12, "$1234": 0x5A}, {"$04": 0x5A}),
    ("INC A", ["T INC A", "  RTS"], {"A": 0x7F}, {"A": 0x80}),
]
for nm, prog, st, ex in c02_checks:
    ok, res = harness.run_cases(prog, ORG, [{"set": st, "expect": ex, "steps": 60}],
                                cpu="65c02")
    report(nm, 1, 0 if ok else 1, "" if ok else "; ".join(res[0]["failures"]))

# ---- verifier features: register/flag checks + assembler directives ----
print("\nVerifier features:")
# input in A, output in A (exercises register set + register expect)
NYB = ["NYBA AND #$0F", "     CMP #$0A", "     BCC :D", "     ADC #$06",
       ":D   ADC #$30", "     RTS"]
ok, res = harness.run_cases(NYB, ORG,
                            [{"set": {"A": 0x0B}, "expect": {"A": 0x42}, "steps": 40}])
report("register set/expect (A in -> A out)", 1, 0 if ok else 1,
       "" if ok else "; ".join(res[0]["failures"]))
# EQU / DFB / DA / %binary / < > expressions assemble to the right bytes
DIRP = ["VAL  EQU $1234", "TBL  DFB <VAL,>VAL", "MSK  DFB %00001111", "WRD  DA  VAL"]
code, syms, _ = harness.assemble(DIRP, ORG)
okd = (code[syms["TBL"]] == 0x34 and code[syms["TBL"] + 1] == 0x12
       and code[syms["MSK"]] == 0x0F
       and code[syms["WRD"]] == 0x34 and code[syms["WRD"] + 1] == 0x12
       and syms["VAL"] == 0x1234)
report("directives EQU/DFB/DA/%bin", 1, 0 if okd else 1)

# A CALL IS ONLY A RETURN IF THE STACK CAME BACK TOO.
#
# run()'s sentinel return address is $8000, which is "outside the program"
# only for routines as small as the ones above.  A real program can contain
# $8000, and then some JMP, branch or JSR target inside it IS the sentinel --
# at which point a PC-only test stops the run mid-call, frames still on the
# stack, and reports the half-finished machine as a completed one.
#
# The routine below is that situation in miniature: it JSRs to $8000, where a
# real subroutine lives, and only afterwards returns.  With run() testing the
# PC alone it stops at the JSR's target and A is never written; with the
# stack pointer tested too, the subroutine runs, returns, and the outer RTS
# lands on the sentinel with the stack back at its starting value.
#
# The failure this guards against cost one project three separate debugging
# sessions and, on the worst occasion, eighty-one phantom failures in code
# that was entirely correct.
m = harness.MPU()
outer, _, _ = harness.assemble(["      JSR $8000", "      RTS"], ORG)
harness.load(m, outer)
inner, _, _ = harness.assemble(["      LDA #$42", "      RTS"], 0x8000)
harness.load(m, inner)
returned = run(m, ORG, 40)
report("a call returns only with the stack back", 2,
       (0 if returned else 1) + (0 if m.a == 0x42 else 1),
       "" if returned and m.a == 0x42 else
       "stopped at the sentinel mid-call: A=$%02X, SP=$%02X" % (m.a, m.sp))

# ---- phase-error / directive guards (regressions for fixed bugs) ----
print("\nAssembler edge cases (phase-error guards):")
# a zero-page EQU declared AFTER its use must not shift later labels/branches
PH = ["T    LDA FOO", "     BNE NEXT", "NEXT RTS", "FOO  EQU $10"]
phc, phs, _ = harness.assemble(PH, ORG)
report("forward zp EQU keeps branch target", 1,
       0 if (phs["NEXT"] == ORG + 4 and phc.get(ORG) == 0xA5
             and phc.get(ORG + 2) == 0xD0 and phc.get(ORG + 3) == 0x00) else 1)
# odd-length HEX must be rejected, not silently desync sizing vs emission
try:
    harness.assemble(["X HEX F", "Y RTS"], ORG)
    odd_ok = False
except ValueError:
    odd_ok = True
report("odd-length HEX rejected", 1, 0 if odd_ok else 1)
# WAI must be reported as a wait-state, not a generic timeout
_, wres = harness.run_cases(["T WAI", "  RTS"], ORG, [{"steps": 40}], cpu="65c02")
wmsg = "; ".join(wres[0]["failures"])
report("WAI reported distinctly", 1,
       0 if ("WAI" in wmsg and "runaway" not in wmsg) else 1)

# ---- reference integrity: SKILL.md pointers must resolve ----
print("\nReference integrity (SKILL.md pointers exist in reference):")
ref_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "references", "6502_reference.md")
anchors = ["## SECTION 0", "## SECTION 1", "## SECTION 2", "## SECTION 3",
           "### T8:", "### T20:", "### T21:", "### T30:", "### T33:", "### T34:",
           "### T35:", "### T33S:", "### T35S:", "# PART IX", "# PART XI",
           "fully-formed target"]
try:
    ref = open(ref_path, encoding="utf-8").read()
    missing = [a for a in anchors if a not in ref]
    report("reference anchors", len(anchors), len(missing),
           "missing: " + ", ".join(missing) if missing else "")
except FileNotFoundError:
    print("  [FAIL] reference file not found at %s" % ref_path)
    FAILS.append("reference file")

print("\n" + ("ALL GREEN" if not FAILS else "FAILURES: " + ", ".join(FAILS)))
sys.exit(0 if not FAILS else 1)
