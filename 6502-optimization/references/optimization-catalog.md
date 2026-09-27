# 6502 / 65C02 Optimization Catalog

Judgment layer for the `6502-optimization` skill. Each entry is **what / when it pays / the tradeoff / what to watch**, plus a pointer to the `6502-codegen` technique (`T#`) or section where the actual code and the **verified cycle counts** live. This file intentionally contains **no cycle tables** — look the numbers up in `6502-codegen/references/6502_reference.md`.

Categories are grouped by the priority order in SKILL.md: structure first, layout second, flow third, instruction-level last. Apply in that order.

---

## A. Algorithm & data structure (do this first)

### A1 — Replace computation with a table
- **What:** precompute results into a table; index instead of calculate.
- **When it pays:** any repeated calculation with a bounded input domain — multiply, squares, sin/cos, gamma, character translation.
- **Tradeoff:** ROM/RAM for the table vs. CPU; table build cost (amortize it).
- **Watch:** table size vs. available memory; alignment for fast indexing (see B3).
- **Codegen:** quarter-square multiply `T34`; nibble→ASCII via table `T32`.

### A2 — Strength reduction
- **What:** replace expensive ops with cheap equivalents — `×2`→`ASL`, `×10`→`(x<<3)+(x<<1)`, `mod 2^n`→`AND #($2^n-1)`, `÷2^n`→`LSR`.
- **When it pays:** multiply/divide by constants, especially powers of two.
- **Tradeoff:** usually pure win; multi-shift sequences can grow for large constants.
- **Watch:** sign for arithmetic shifts; carry into/out of multi-byte shifts.
- **Codegen:** powers-of-two and 8/8 divide `T35`; shift-and-add multiply `T33`.

### A3 — Choose the right representation
- **What:** pick the data layout that makes the hot operation cheap (e.g. structure-of-arrays so a field is a flat indexable array; packed vs. unpacked).
- **When it pays:** loops that touch one field across many records.
- **Tradeoff:** memory layout vs. access pattern; can complicate unrelated code.
- **Watch:** 256-byte indexing limits with a single index register.
- **Codegen:** pointer pairs `T2`, streaming `T3`.

---

## B. Memory layout & zero page

### B1 — Zero page as a register file
- **What:** keep hot variables and all pointers in zero page.
- **When it pays:** any hot path — zero-page access is shorter and faster than absolute (look up the exact delta in codegen Section 2).
- **Tradeoff:** zero page is tiny and contended.
- **Watch:** on a real machine the ROM/OS reserves much of zero page — confirm what is actually free on the target before claiming a byte. (This is a platform fact, not a CPU fact.)
- **Codegen:** `T1`.

### B2 — Split hi/lo tables
- **What:** store a word table as two parallel byte arrays (all low bytes, all high bytes) instead of interleaved.
- **When it pays:** word lookups in a loop — indexing with one register and no shift.
- **Tradeoff:** two arrays instead of one; both must stay in sync.
- **Watch:** keep the two arrays' indexing identical.
- **Codegen:** see `T2`/`T34` (the squares tables use this layout).

### B3 — Page-boundary alignment
- **What:** align a hot loop's data (and the loop entry) so indexed reads and taken branches don't cross a page.
- **When it pays:** tight inner loops where the cross-page penalty repeats every iteration.
- **Tradeoff:** padding bytes; only worth it for genuinely hot code.
- **Watch:** indexed **stores** don't get the no-cross discount — they pay regardless (codegen Section 2's "fully-formed target" note); align for the loads and branches, not the stores.
- **Codegen:** `T12`.

---

## C. Loop & flow structure

### C1 — Count down to zero
- **What:** loop on a decrementing index so `DEX`/`DEY` sets Z and you branch with no separate compare.
- **When it pays:** almost every counted loop where iteration order is free.
- **Tradeoff:** reverses traversal order — fine for clears/fills, not for order-dependent work.
- **Watch:** off-by-one at the boundary; whether index 0 must be processed.
- **Codegen:** unsigned compare `T28` (and why you often don't need it).

### C2 — Loop unrolling
- **What:** emit the body N times to delete the per-iteration `DEX`+branch overhead.
- **When it pays:** small fixed counts on a hot path.
- **Tradeoff:** code size grows linearly; pure speed-for-size.
- **Watch:** instruction-fetch cost; partial counts (use a computed entry).
- **Codegen:** Duff-style entry into unrolled code `T14`.

### C3 — Fall-through on the common path
- **What:** arrange branches so the frequent case is not-taken (cheapest), the rare case branches away.
- **When it pays:** hot conditionals with a skewed distribution.
- **Tradeoff:** can read slightly less naturally; document intent.
- **Watch:** keep loop-back branch targets on the same page (see B3).
- **Codegen:** branch timing equalization `T11`, long-branch chaining `T9`.

### C4 — Tail-call with JMP; inline tiny leaves
- **What:** `JSR sub`/`RTS` at a routine's end becomes `JMP sub`; inline very small leaf routines on hot paths.
- **When it pays:** call-heavy hot code; leaves called from one or two hot sites.
- **Tradeoff:** inlining trades size for call overhead; over-inlining bloats.
- **Watch:** inlined code must not assume it was entered via JSR (no caller return on stack).
- **Codegen:** tail calls `T15`.

### C5 — Table-driven dispatch
- **What:** replace a `CMP`/branch ladder with an index into a jump table.
- **When it pays:** 3+ way dispatch on a small integer (state machines, opcode handlers).
- **Tradeoff:** table space; indirection setup.
- **Watch:** NMOS `RTS`-trick pushes (handler-1); 65C02 `JMP (abs,X)` is cleaner where available.
- **Codegen:** `RTS` computed jump `T20`; 65C02 `JMP (abs,X)` table `T21`.

### C6 — Fold duplicated code (shared tails)
- **What:** when routines end in — or contain — the same instruction sequence, keep one copy: fall into or `JMP` to a shared tail, or extract the duplicate body and `JSR` it.
- **When it pays:** size-driven work; multiple exit paths doing the same cleanup-then-`RTS`; copy-pasted routine variants. Scan *across* routines, not just within one.
- **Tradeoff:** fall-through/`JMP` folding is a near-pure size win; folding via `JSR`/`RTS` buys size at call-overhead cycles (delta from codegen Section 2) — don't fold a hot path that way.
- **Watch:** every entry into the shared tail must arrive with the same register/flag/zero-page expectations — fold code, not coincidence; folding moves code and can push relative branches out of range (re-chain per `T9`).
- **Codegen:** tail-call `JMP` `T15`; long-branch chaining `T9`.

---

## D. Instruction-level & 65C02 (last)

### D1 — 65C02 instruction upgrades
- **What:** collapse common NMOS sequences into single 65C02 ops — `CLC`/`ADC #1`→`INC A`, `SEC`/`SBC #1`→`DEC A` (Merlin spells these `INA`/`DEA`, but the verifier and codegen reference use `INC A`/`DEC A`), `LDA #0`/`STA`→`STZ`, `TXA`/`PHA`→`PHX` (also preserves A), `PLA`/`TAX`→`PLX`.
- **When it pays:** 65C02 target, after structural work is done.
- **Tradeoff:** breaks NMOS portability.
- **Watch:** only on a 65C02; look up each replacement's real size/cycle delta in codegen Section 2 / Part VII rather than trusting a remembered figure.
- **Codegen:** Part VII (`T38`–`T44`).

### D2 — Self-modifying code
- **What:** patch an inline operand or address in a hot loop instead of recomputing or using indirection (e.g. self-modify an absolute address rather than `(zp),Y` per iteration).
- **When it pays:** very hot loops where the patched value is stable across many iterations.
- **Tradeoff:** unreadable if undocumented; forecloses ROM and reentrancy.
- **Watch:** **RAM only, not re-entrant, document it** (codegen hard rule 9).
- **Codegen:** Part III (`T16`–`T19`).

### D3 — Stack and register-pressure tricks
- **What:** keep loop variables in X/Y; avoid `PHA`/`PLA` churn in inner loops; use the stack as scratch where it genuinely helps.
- **When it pays:** register-starved inner loops.
- **Tradeoff:** fragile; easy to clobber something a caller depends on.
- **Watch:** the routine's documented register contract (SKILL.md hard rule 4).
- **Codegen:** stack scratch `T22`, caller args via `TSX` `T23`.

### D4 — `BIT` skip-over (converging entry points)
- **What:** a lone `$2C` (`BIT abs`) opcode byte absorbs the next 2-byte instruction as its operand, so two entry points converge without a jump — 1 byte where a `JMP` over them costs 3, a **2-byte** saving. A lone `$24` (`BIT zp`) skips 1 byte the same way.
- **When it pays:** size-critical code where two entry points differ by one leading 2-byte instruction (e.g. `LDA #1` vs `LDA #0` into a shared tail).
- **Tradeoff:** pure size play — the skipping path still executes the `BIT` (slower than the `JMP` it replaces; deltas in codegen Section 2), and `BIT` clobbers N, V, Z, so flags set before the skip don't survive into the tail.
- **Watch:** the swallowed bytes are **read as an address** — on memory-mapped I/O that read can fire a side effect (an Apple II `$C030`-shaped operand toggles the speaker). Confirm they decode into plain RAM/ROM. `BIT #imm` is no escape: it can't encode an absolute skip.
- **Codegen:** `BIT` encodings and flags — Section 2, Part VII; opcode-as-data toggle `T18`.

---

## Correctness gotchas that optimization tends to reintroduce

Reordering, stripping, or "tightening" code is exactly when these bite. An optimizer must re-check them, and `equiv.py` is what catches a miss:

- **Indexed-store dummy read.** `STA abs,X`/`STA abs,Y` always forms the full address first; this is destructive on I/O addresses and is why stores don't get the page-cross discount. Codegen Section 2 ("fully-formed target").
- **Decimal-mode hygiene.** `SED` must be paired with `CLD`; on NMOS only carry is valid after a decimal op. Codegen `T30`.
- **`JMP ($xxFF)` page-wrap bug** on NMOS. Codegen `T8`.
- **`BIT`-skip operand must be readable.** Using `BIT abs` to swallow the next two bytes still *reads* that address. (See codegen Section 2 / Part VII for `BIT`.)
- **Clobbering a preserved register.** The fastest variant is wrong if the original promised to preserve A/X/Y/a flag and a caller relied on it. This is what `observe` (full image + A/X/Y by default) is for.
