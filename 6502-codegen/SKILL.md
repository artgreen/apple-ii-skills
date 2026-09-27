---
name: 6502-codegen
description: "Use when generating, fixing, debugging, or explaining portable 6502, 65C02, or W65C816 8-bit assembly; when a task mentions MOS-family CPUs such as 6502, 65C02, 6510, Apple II, Commodore, NES, Atari, or BBC Micro; or when it involves opcodes, cycle counts, zero page, addressing modes, BCD/decimal mode, self-modifying code, interrupts, or undocumented opcodes."
license: MIT
---

# 6502 / 65C02 / 65C816 Code Generation

You are generating assembly for the 8-bit MOS 6502 family. Follow the procedure below **in order, every time**. Do not rely on memorized cycle counts or opcode behavior — they are a known source of error. Look them up in the bundled reference.

## Scope

This skill is **CPU-generic**. It does **not** cover platform memory maps, ROM/firmware calls, fixed I/O addresses, interrupt vectors, or display/timer races for any specific machine (Apple II, C64, NES, etc.). RAM addresses in examples are generic placeholders. If a request needs platform specifics, say so and ask the user (or defer to a machine-specific skill) rather than inventing addresses.

## Operating procedure

1. **Determine the CPU target.** If the user did not state one, default to **documented NMOS 6502** (most portable). Targets: NMOS 6502, W65C02S, Rockwell 65C02, W65C816 8-bit (see reference Section 1).
2. **Obey the Hard Rules** (below) without exception.
3. **Do the mandatory lookups** (below) before emitting any instruction in the listed categories. Reading is not optional and not discretionary.
4. **Reuse a pre-verified routine** from the reference when one fits (multiply, divide, BCD conversion, dispatch, etc.) instead of writing your own.
5. **Verify before returning** (see "Verify"). Only return code that assembles and passes its test. For code that can't be executed here (the paper-verify cases listed under Verify), confirm it against the reference instead and say so in the output contract.
6. **Emit the output contract** (below) alongside the code.

## Hard rules (never violate)

1. `CLC` before a standalone `ADC`; `SEC` before a standalone `SBC`.
2. Carry is an **inverted borrow**: after `SBC`/`CMP`, carry set means A >= operand, carry clear means A < operand.
3. No `(zp)` non-indexed indirect on plain NMOS — use `LDY #0 / LDA (zp),Y`.
4. No `STZ`, `PHX/PHY/PLX/PLY`, `BRA`, `TRB/TSB`, `INC A`/`DEC A`, `BIT #imm`, `JMP (abs,X)`, `RMB/SMB`, `BBR/BBS`, `WAI`, `STP` on plain NMOS — these are 65C02/816 (some WDC/Rockwell-only). Use the fallback.
5. No undocumented/illegal opcodes unless the target is explicitly NMOS-only AND the user enabled them (Part IX gate). Never emit `JAM`/`KIL`.
6. On NMOS, never place an indirect-`JMP` vector with its low byte at `$xxFF` (the page-wrap bug; reference T8).
7. `CLD` early in NMOS interrupt handlers that do binary `ADC`/`SBC` (NMOS does not clear D on interrupt).
8. `SED` is for `ADC`/`SBC` only and must be followed by `CLD`. On NMOS, only carry is valid after a decimal op — do not branch on N/V/Z.
9. No self-modifying code in ROM, and it is not re-entrant.
10. State your assumptions: CPU target, register/flag clobbers, and cycle behavior if timing matters.

## Mandatory lookups (read the named slice of references/6502_reference.md BEFORE emitting)

| If you are about to emit / claim | Read first |
|---|---|
| any cycle count or timing claim | Section 2B, 2C, 2D |
| a decimal-mode `ADC`/`SBC` | T30 + Section 2B (decimal rows) |
| a store with `,X` or `,Y` indexing | Section 2B row on the "fully-formed target" dummy-read trap |
| an indirect `JMP` | T8 + Section 2B |
| a 65C02/816-only instruction | Section 2C + the matching technique |
| an undocumented opcode | Part IX policy gate (all 5 conditions) before anything else |
| signed multiply or divide | T33S / T35S |
| an interrupt handler | Part VIII |

If you cannot find the relevant slice, say so rather than guessing.

## Reference map — references/6502_reference.md (grep by the IDs)

- **Section 0** — Hard Rules (same list, full text).
- **Section 1** — CPU compatibility frame + default policy.
- **Section 2A–2D** — flag effects; NMOS-vs-65C02 differences; 65C02 opcode/cycle table; cycle rules. *Your lookup tables — prefer these over recall.*
- **Section 3** — workspace symbols (ZP_PTR, ZP_TMP, WORKBUF, ...).
- **Parts I–IX** — techniques T1–T58 plus T33S/T35S, each as: What / Code / Compat / Use when / Watch out / Agent rules + fallback. (I addressing/ZP, II flow/cycles, III SMC, IV stack, V arithmetic/flags/BCD, VI math routines, VII 65C02 power tools, VIII interrupts, IX undocumented opcodes.)
- **Part X** — runnable verification/feature-probe snippets.
- **Part XI** — output templates (register contract, timing, SMC, undocumented).

The technique IDs are stable handles — to use "the RTS dispatch trick" read `T20`; for the cycle table read `Section 2B`.

## Verify before returning (REQUIRED)

Generated 6502 is not trustworthy until it runs. Assemble and test it in the bundled simulator before you hand it back.

**Dependency:** `py65`, in an isolated env (avoid a system-wide install — on managed/Homebrew Python it's blocked by PEP 668):

    python3 -m venv .venv && . .venv/bin/activate && pip install py65

Or user-site without a venv: `python3 -m pip install --user py65`. The scripts print this same hint if `py65` is missing, and exit non-zero rather than throwing a traceback.

**Turnkey path — JSON spec, no Python to write.** Put the routine and test cases in a JSON file and run `python scripts/run.py spec.json`. Exit 0 means all cases passed. Schema and a worked example (testing the multiply routine on 3 * 5 = 15):

```json
{
  "program": [
    "MUL8     LDA   #$00",
    "         STA   ZP_PTR+1",
    "         LDX   #$08",
    ":ROT     LSR   ZP_TMP2",
    "         BCC   :NOADD",
    "         CLC",
    "         ADC   ZP_TMP",
    ":NOADD   ROR   A",
    "         ROR   ZP_PTR",
    "         DEX",
    "         BNE   :ROT",
    "         STA   ZP_PTR+1",
    "         RTS"
  ],
  "origin": 768,
  "cpu": "nmos",
  "cases": [
    { "set": {"ZP_TMP": 3, "ZP_TMP2": 5}, "steps": 200,
      "expect": {"ZP_PTR": 15, "ZP_PTR+1": 0} }
  ]
}
```

**Keys in `set`/`expect`** may be a memory location (int, `"0x04"`, `"$04"`, a decimal string, or a symbol like `"ZP_PTR"` / `"ZP_PTR+1"`), a **register** (`"A"`, `"X"`, `"Y"`, `"SP"`, `"P"`), or a **flag** (`"C"`, `"Z"`, `"I"`, `"D"`, `"V"`, `"N"`; value `0`/`1`). So a routine that returns its result in `A` or signals via carry is checkable directly — e.g. `"expect": {"A": 2, "C": 1}`. `PC`/`SP` can't be set as inputs (the runner seeds them). Values may be ints or hex/binary strings. Set `"tables": true` to preload the quarter-square tables for T34.

**`"cpu"`** selects the core: `"nmos"` (default) or `"65c02"`. Both assemble **and execute**. Two kinds of code can't be run here and must be **paper-verified** against the reference instead: (1) *won't assemble* — native-816 instructions (no 65816 core) and `BBR`/`BBS`/`STP`; (2) *assembles but never reaches `RTS`* — `WAI` (parks the CPU waiting for an interrupt the harness can't inject; the verifier flags this distinctly rather than as a timeout) and `BRK` (needs an installed handler/vector). Test the surrounding logic with the `WAI`/`BRK` removed, and note in the output contract that the instruction itself was checked on paper.

**Assembler scope.** It accepts instructions for the selected CPU plus: column-1 labels (`FOO` / `FOO:`), `:local` labels, a label sharing a line with an instruction; the directives `EQU`/`=`, `DFB`/`DB`, `DA`/`DW`, `DDB`, `DS`, `HEX`; `$hex` / `%binary` / decimal literals; and `+ - < > ( )` in expressions (e.g. `DFB <(HAND0-1)`). It does **not** handle macros, conditional assembly, `ORG`/`PUT`/`SAV`, or string directives — keep a test harness to a single routine plus its data.

**Power path — Python.** Add the scripts dir to the path and import the module: `import sys; sys.path.insert(0, "scripts"); import harness` (or just run your script from inside `scripts/`). Then use `harness.assemble`, `load`, `run`, `run_cases` (each takes `cpu="nmos"|"65c02"`), `s8`, `s16`, `make_tables`. Use this when expected values are computed rather than fixed.

**Rules:**
- Test edge cases, not just the happy path: 0, max (255 / signed -128, 127), carry/borrow boundaries, page crossings, and (for division) divisor extremes.
- If a case fails, fix the code and re-run. **Only return code that passes.**
- Do not promise exact cycle counts for `BBR`/`BBS` — the reference documents that their taken/page-cross timing is unresolved.

**Sanity check the skill itself:** `python scripts/selftest.py` re-verifies all bundled reference routines against ground truth and confirms the reference file is intact. Run it if you suspect the environment is broken.

## Output contract (emit with every routine)

```
CPU:     NMOS 6502 / 65C02 / W65C816 8-bit
Input:   A/X/Y = ...   ZP_xxx = ...   carry/decimal = ...
Output:  A/X/Y = preserved | clobbered   Flags = meaningful (which) | clobbered
         Zero page used: ...   Memory touched: ...   Max stack depth: ...
Timing:  setup / loop-per-iter / page-cross behavior  (if timing matters)
Verified: how it was tested (cases run, or "scripts/selftest.py")
```
