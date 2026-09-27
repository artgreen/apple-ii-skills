---
name: 6502-optimization
description: "Use when optimizing or tuning existing working 6502 or 65C02 assembly for speed or size, cycle budgets, zero-page allocation, loop unrolling, strength reduction, table dispatch, self-modifying code, page-boundary alignment, or 65C02 instruction upgrades. Not for 65816 native mode or non-6502 architectures."
license: MIT
---

# 6502 / 65C02 Optimization

You are making **existing, working** 6502-family assembly faster or smaller. This skill is the optimization layer; it deliberately owns no cycle counts and no opcode encodings. Those live in the `6502-codegen` skill's verified reference, and you look them up there. Your job here is judgment — what to change, in what order, and proving the change didn't break anything.

## Dependency (read this first)

This skill is a companion to **`6502-codegen`** and assumes it is installed alongside it. You need it for two things:
1. **Every number.** Cycle counts, opcode sizes, page-cross penalties, and the 65C02 instruction set come from `6502-codegen`'s `references/6502_reference.md` (Section 2 and the technique entries). Never quote a cycle count from memory — look it up there. This skill will not repeat those tables, on purpose: one source of truth, and it's the verified one.
2. **The proof.** `scripts/equiv.py` rides on `6502-codegen`'s simulator harness to prove an optimized routine behaves identically to the original. It finds the codegen skill as a sibling directory or via `CODEGEN_DIR`.

If `6502-codegen` is not reachable, say so and stop — without it you would be guessing at numbers and unable to prove equivalence, which is exactly what this skill exists to prevent.

## Operating procedure (in order, every time)

1. **State the goal and target.** Speed, size, or an explicit cycle budget (raster line, IRQ latency)? Which CPU — NMOS 6502 or 65C02? Optimization is a tradeoff; you cannot pick well without knowing which axis matters.
2. **Find the hot path.** Optimize what dominates runtime or size — an inner loop, a per-frame routine, a large table. Leave cold code alone. A change to code that runs once is almost never worth the risk.
3. **Look up real costs** in `6502-codegen`'s reference before claiming any number. (Mandatory; see Dependency.)
4. **Apply optimizations in priority order** (below). Algorithm and data layout first; instruction-level tricks last.
5. **Prove non-regression (REQUIRED).** The optimized routine must produce identical observable output to the original across a test corpus. Use `scripts/equiv.py`. A change that alters behavior is a bug, not an optimization — see "Verify".
6. **Quantify from the table.** State the cycle and byte delta, computed from `6502-codegen`'s verified Section 2 numbers, and cite the rows. Do **not** measure cycles by running (the simulator is functional, not cycle-accurate) and do **not** estimate from memory.
7. **Emit the output contract** (below): the change, the proven delta, and what got worse.

## Priority order (where the real gains are)

1. **Algorithm and data structure.** 99 times out of 100 the biggest win is structural — a lookup table replacing a computed loop, a better memory layout, precomputation. A table can save hundreds of cycles; `INA` saves two. Do this first or you are polishing the wrong thing.
2. **Memory layout / zero page.** Hot variables and pointers in zero page; split hi/lo tables; align hot data. (Zero page is scarce and, on a real machine, partly reserved by the ROM/OS — confirm what is actually free on the target.)
3. **Loop and flow structure.** Count down to zero so the flag is free; unroll small fixed loops; arrange the common path to fall through; replace `JSR`+`RTS` tails with `JMP`.
4. **Instruction-level / 65C02 upgrades — last.** `INA`/`DEA`, `STZ`, `PHX`/`PHY`, `TRB`/`TSB`, `BIT #imm`, `JMP (abs,X)`, `BRA`. Small, safe, and only worth doing after the above.

## Hard rules (never violate)

1. **Correctness outranks speed.** Never present an optimization you have not proven equivalent to the original (step 5). This is the whole point of the skill.
2. **Numbers come from `6502-codegen`'s verified reference, never from recall.**
3. **The simulator is functional, not cycle-accurate.** Cycle claims are computed from the table and labeled as computed, not measured.
4. **Preserve the routine's documented contract.** A faster routine that clobbers a register or flag the original preserved is a regression unless every caller is updated too. State any contract change loudly.
5. **Self-modifying code: RAM only, documented, not re-entrant** (see `6502-codegen` Part III and its hard rule 9). It is a real optimization on the cacheless 6502 but it is not free of hazards.
6. **65C02 instructions only if the target is a 65C02**; `RMBx`/`SMBx`/`BBRx`/`BBSx` only on Rockwell/WDC parts, not all CMOS brands.
7. **Do not optimize cold paths, and do not trade correctness or clarity for cycles that do not matter.** "Fast enough, correct, and readable" beats "fastest and fragile."

## Reference map — `references/optimization-catalog.md`

The catalog holds the optimization categories as judgment (what / when it pays / the tradeoff / what to watch), each pointing to the `6502-codegen` technique ID where the actual code and verified numbers live. Read it for the menu; read `6502-codegen` for the implementation and the cycle counts.

## Verify before returning (REQUIRED)

An optimization is valid only if it is **behaviorally identical** to the original. Prove it with `scripts/equiv.py`, which assembles both routines, runs each on the same test cases through `6502-codegen`'s simulator, and reports any divergence.

```python
import sys; sys.path.insert(0, "scripts"); import equiv
# original and optimized: Merlin-style source line lists
# cases: same shape 6502-codegen's harness uses -- {"set": {...}, "steps": N}
# observe: the routine's actual contract (output bytes + result registers).
#          Omit to compare the entire memory image + A/X/Y (conservative;
#          will flag scratch differences too, which is often what you want).
ok, results = equiv.compare(original, optimized, cases,
                            origin=0x0300, cpu="nmos",
                            observe=["$2000", "$2001", "A", "C"])
```

Rules for the proof:
- **Cover the corpus that exercises the change**: edge values (0, max, signed extremes), every branch, and any data shape the optimization special-cases (runs, boundaries, empty input).
- **`equiv` decides equivalence; you decide the contract.** If the optimized version legitimately leaves different scratch (e.g. ends with `X=0` instead of `X=8`), scope `observe` to the real outputs — but do that deliberately, not to silence a failure you do not understand.
- **The cycle/byte delta is computed from `6502-codegen`'s Section 2 table, not measured.** py65 is not cycle-accurate; never report a measured cycle count.
- If a change cannot be proven equivalent, it does not ship.

**Self-check:** `python scripts/selftest.py` confirms `equiv` catches a broken "optimization" and passes a real one, and that the catalog's pointers into `6502-codegen` resolve. Run it if the environment looks wrong.

## Output contract (emit with every optimization)

```
Goal:     speed | size | cycle budget (which)   CPU: NMOS 6502 | 65C02
Change:   what was changed + catalog category
Before:   N cycles / M bytes   (per 6502-codegen Section 2, cite rows)
After:    N' cycles / M' bytes  (same source)
Delta:    -X cycles / -Y bytes  (computed, not measured)
Tradeoff: what got worse (size, clarity, reentrancy, ZP pressure, alignment padding)
Proof:    equiv.compare cases run + result (all equivalent); observe scope used
Contract: registers/flags/memory preserved | changed (state exactly what)
```
