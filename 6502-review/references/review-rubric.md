# 6502 / 65C02 Static Review Rubric

Four checklists, worked top to bottom. Each item says **what to look for** and **where the authority lives** — it does not restate the rule or the cycle count. Pull the exact rule text and verified numbers from `6502-codegen`'s `references/6502_reference.md`; pull optimization categories from `6502-optimization`'s `references/optimization-catalog.md`. **Cite, never recall** — there is no harness here to catch an invented number.

Severity bands: **Correctness** (High / Conditional) > **Best practice** > **Common practice**. **Optimization** is a separate axis (opportunity, ranked by how hot the path is). Label confidence on every finding: **Certain** (provable by inspection) / **Likely** (depends on unseen context) / **Possible — needs run** (recommend the harness).

---

## 1. Correctness scan (highest severity)

Hardware and semantic traps. Each cites a codegen rule or technique:

- [ ] **65C02-only instruction on an NMOS target** — `STZ`, `PHX`/`PHY`/`PLX`/`PLY`, `BRA`, `TRB`/`TSB`, `BIT #imm`, `INC A`/`DEC A`, `(zp)`, `JMP (abs,X)`, `RMB`/`SMB`/`BBR`/`BBS`, `WAI`/`STP`. → codegen Section 1 + hard rules. (Certain by inspection, given the target.)
- [ ] **NMOS `JMP ($xxFF)` page-wrap bug** — indirect vector whose low byte is `$FF`. → codegen `T8`. (Certain if the address is literal/derivable.)
- [ ] **Indexed-store dummy read** — `STA`/`STX`/`STY abs,X`/`abs,Y` aimed at an I/O address; the full address is formed and the location is touched even with no page cross. → codegen Section 2 ("fully-formed target").
- [ ] **Decimal-mode hygiene** — `SED` without a matching `CLD`; relying on N/V/Z after a decimal `ADC`/`SBC` on NMOS (only carry is valid there). → codegen `T30`.
- [ ] **Undocumented / unstable opcodes** — illegal NMOS opcodes, especially the unstable "magic constant" family. → codegen Part IX. (Correctness risk if the unstable ones are used; best-practice issue otherwise.)
- [ ] **Off-by-one / loop bounds** — does a `count = 0` loop wrongly run once (or 256 times)? is the terminal index right? are `BCC`/`BCS` vs `BEQ`/`BNE` correct for the comparison? → trace; confirm in harness if runnable. (Usually Possible — needs run.)
- [ ] **Branch out of range** — a relative branch target more than +127 / -128 away. → codegen `T9` (chaining). (Certain if addresses are known.)
- [ ] **Multi-byte carry handling** — carry propagated across bytes; `CLC`/`SEC` set correctly before `ADC`/`SBC`. → codegen `T26`/`T27`. (Likely / needs run.)
- [ ] **Signed vs unsigned comparison** — carry-only logic used where the N-xor-V signed idiom is required. → codegen `T28`/`T29`.
- [ ] **Register/flag clobber across a call** — a mid-routine `JSR` destroying a register the caller assumes is preserved. (Likely; depends on the callee's real contract.)
- [ ] **Stack balance** — pushes without matching pulls on some path; `RTS`/`RTI` mismatch; `PLP` restoring an unintended flag state. (Certain to Likely by tracing.)
- [ ] **Self-modifying code correctness** — the patched operand/address actually lands on the right byte, and the code runs from RAM not ROM. → codegen Part III.

## 2. Optimization-opportunity scan (separate axis — opportunities, not defects)

Each cites a `6502-optimization` catalog category and the codegen technique. Give the cycle/byte delta **from the table**, and mark any rewrite **unproven for equivalence** (defer the proof to `6502-optimization`'s `equiv`):

- [ ] **Computation that could be a table lookup** → opt A1 / codegen `T34`, `T32`.
- [ ] **Multiply/divide by a constant not reduced to shifts/adds** → opt A2 / codegen `T35`, `T33`.
- [ ] **Hot variables or pointers in absolute memory instead of zero page** → opt B1 / codegen `T1`.
- [ ] **Interleaved word table where split hi/lo would remove a shift** → opt B2 / codegen `T2`, `T34`.
- [ ] **Hot loop or indexed data not page-aligned** (cross-page penalty every iteration) → opt B3 / codegen `T12`.
- [ ] **Counted loop using `CMP` where count-down-to-zero is free** → opt C1.
- [ ] **Small fixed-count loop that could be unrolled** → opt C2 / codegen `T14`.
- [ ] **`JSR`+`RTS` tail that could be a `JMP`** → opt C4 / codegen `T15`.
- [ ] **`CMP`/branch ladder where a jump table fits** → opt C5 / codegen `T20`, `T21`.
- [ ] **NMOS sequence with a one-instruction 65C02 form** (only if the target is 65C02) → opt D1 / codegen Part VII.
- [ ] **Per-iteration pointer math that SMC could hoist** (hot loop, RAM, justified) → opt D2 / codegen Part III.
- [ ] **Identical instruction sequences repeated across routines** — shared *tails* / exit sequences, or a duplicated body — that could fold → opt C6. **Cross-routine scan:** read for repeated *trailing* sequences, not just the per-routine shapes above; when you find one duplication, sweep for the rest before moving on.

## 3. Best-practice rubric (works, but fragile/risky — "should fix")

Concrete criteria, not taste:

- [ ] **Documented entry/exit contract** — inputs (where/format), outputs (where/format), registers and flags clobbered vs preserved, zero page used, max stack depth. A routine without this is a landmine for callers. (Mirror codegen's output-contract format.)
- [ ] **Named constants, not magic numbers** — addresses, masks, counts as `EQU`s; not bare `$C030` / `#$07` scattered inline.
- [ ] **Zero-page discipline** — which ZP locations the routine uses, and whether they are free on the target. Undocumented ZP grabs collide, especially with the OS/ROM on a real machine (a platform fact — verify on the actual target).
- [ ] **Self-modifying code justified, documented, RAM-only** — flagged in the contract, with a comment on the patch; not silently scattered. → codegen Part III. SMC forecloses ROM and reentrancy.
- [ ] **Edge cases handled** — zero count/length, maximum values, empty input, wrap at boundaries.
- [ ] **Cycle-critical sections commented with their budget** — so a later edit cannot silently blow a raster or IRQ deadline.
- [ ] **No undocumented opcodes in portable code** — NMOS-only, and some are unstable. → codegen Part IX.
- [ ] **Interrupt safety / reentrancy** — an IRQ handler saves and restores everything it touches; a routine called from both main and an interrupt is reentrant (no SMC, no shared scratch). → codegen Part VIII.

## 4. Common-practice rubric (works and fine, but diverges from idiom — "consider/justify")

- [ ] **Standard idioms for common ops** — 16-bit increment/compare (`T6`/`T27`), multi-byte add (`T26`), clear/fill via count-down, nibble-to-ASCII (`T32`). A hand-rolled, longer/slower variant → suggest the idiom.
- [ ] **Consistent calling convention** — arguments passed in a regular register/ZP scheme, not a different ad-hoc one per routine.
- [ ] **Conventional table layout** — split hi/lo for word tables; page-aligned where indexed in a hot loop.
- [ ] **Count down to zero** when iteration order is free (the idiom) → opt C1.
- [ ] **Table-driven dispatch** over long `CMP` ladders → codegen `T20`/`T21`.
- [ ] **Flag-test idioms** — `BIT` to test bits without destroying A; the N-xor-V signed-compare idiom → codegen `T29`, `T40`.

---

Report **correctness first**, label **confidence** on every finding, **cite the source** for every rule and number, and end with **what you could not assess statically** — anything needing a run, or code using macros/segments/ROM calls you could not trace.
