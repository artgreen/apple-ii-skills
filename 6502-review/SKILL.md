---
name: 6502-review
description: "Use when statically reviewing, auditing, or critiquing existing 6502 or 65C02 assembly without running it, especially for correctness, edge cases, hardware hazards, contracts, zero-page discipline, self-modifying code, portability, idioms, or optimization opportunities. Not for 65816 native mode or non-6502 architectures."
license: MIT
---

# 6502 / 65C02 Static Code Review

You are auditing **existing** 6502-family assembly **by reading it**, not by running it, and producing a prioritized findings report. This skill is methodology plus a rubric; it owns no cycle tables and no rule definitions. Those live in `6502-codegen`'s reference; optimization categories live in `6502-optimization`'s catalog. Your value here is **systematic coverage** (a checklist so nothing is missed) and **grounded findings** (every claim tied to a cited rule, technique, or idiom — never to a recalled number).

## What this skill is, and is not

- **Is:** a static review — read the code, judge it against rules / idioms / practice, report findings with severity, confidence, location, citation, and a suggested fix.
- **Is not:** an execution. You do not assemble or run anything. Findings are reasoned arguments, not test results — never fabricate a run or claim "I tested this."
- **Hands off:** anything runnable and uncertain belongs in `6502-codegen`'s harness. Static review is the fast, total-coverage first pass; the bench test confirms the runnable suspects.

## Dependency (documentation, not code)

This skill cites two others; install them alongside it so you can quote the authoritative text and the **verified** numbers:
- **`6502-codegen`'s `references/6502_reference.md`** — every hard rule, cycle count, opcode encoding, gotcha, and technique ID you cite. **Look numbers up there; never recall a cycle count.** With no harness to catch an invented figure, citation is the only thing keeping this review honest.
- **`6502-optimization`'s `references/optimization-catalog.md`** — the optimization-opportunity categories you cite.

If the codegen reference is not reachable, do not assert specific cycle counts from memory — say "verify against the reference" and lower your confidence accordingly.

## Review procedure (in order — severity descending)

1. **Establish context.** Target CPU (NMOS 6502, 65C02, Rockwell/WDC, or 816 in 8-bit mode), the routine's claimed contract (what it should do; inputs/outputs), and whether the source is full Merlin (macros/segments) or the runnable subset. You cannot review without the target: `STZ` is a bug on NMOS and correct on 65C02. If the target is unstated, ask or state your assumption explicitly.
2. **Correctness pass (highest severity).** Walk the correctness checklist in the rubric. Each hit cites the codegen rule/technique and traces the semantics. Label confidence; flag runnable-and-uncertain items for harness confirmation.
3. **Optimization-opportunity pass.** Walk the optimization catalog's categories. Each opportunity cites the catalog category + the codegen technique + the cycle/byte delta (looked up, not recalled). These are opportunities, not defects — and any suggested rewrite is **unproven for equivalence** here; defer the proof to `6502-optimization`'s `equiv` before applying.
4. **Best-practice pass.** Walk the best-practice rubric (contract, named constants, ZP discipline, justified SMC, portability, edge handling, timing comments, reentrancy).
5. **Common-practice pass.** Walk the idiom rubric — is it hand-rolling something with a standard idiom, or using an unusual convention? Diverging is not wrong, but it should be justified.
6. **Synthesize.** Emit one prioritized findings list, correctness first. If you found no correctness issues, **say so plainly** before listing lesser findings — don't let practice or optimization notes imply the code is broken.

## Hard rules of reviewing (never violate)

1. **Cite, don't recall.** Every cycle count, rule, and opcode fact comes from `6502-codegen`'s verified reference. Never state a number from memory.
2. **Don't run, don't claim to.** This is static review. Findings are arguments, not executions; never invent a test result.
3. **Label confidence; defer runnable suspects.** Mark each finding Certain / Likely / Possible. Anything runnable and uncertain gets "confirm in `6502-codegen`'s harness," not a confident assertion.
4. **Severity ordering is sacred.** Lead with correctness. Never let a style, idiom, or optimization note bury a real bug. "No correctness issues found" is itself a headline finding — state it.
5. **Be target-aware.** Judge against the stated CPU. A 65C02 instruction is not a defect on a 65C02.
6. **Practice findings need a concrete criterion, not taste.** Cite the specific rule or idiom and why it matters. Do not invent rules or review by aesthetic preference.
7. **Optimization suggestions are unproven here.** Give the cycle/byte delta from the table and defer the equivalence proof to `6502-optimization`. A "faster" suggestion you cannot prove equivalent is a hypothesis, labeled as one.

## Reference map — `references/review-rubric.md`

The rubric holds the four checklists: the correctness scan (each item pointing to a codegen rule/technique), the optimization-opportunity scan (pointing to the optimization catalog), and the new best-practice and common-practice rubrics. Work through it top to bottom; that is how you get complete, consistent coverage instead of an ad-hoc glance.

## Severity and confidence

**Severity** (what a finding costs):
- **Correctness — High:** will produce wrong output or crash on the stated target (e.g. `STZ` on NMOS; literal `JMP ($xxFF)`; `SED` with no `CLD`).
- **Correctness — Conditional:** wrong only under certain inputs or a different target (an off-by-one that bites at count=0; a page-cross assumption).
- **Best practice:** works, but fragile or unmaintainable (undocumented clobbers, magic numbers, undocumented SMC, unhandled edges).
- **Common practice:** works and is fine, but diverges from idiom — "consider/justify," not "fix."
- **Optimization:** works and is fine, but leaves cycles or bytes on the table; rank by how hot the path is.

**Confidence** (how sure, given you did not run it):
- **Certain:** provably violates a named rule by inspection. Cite it.
- **Likely:** strong pattern, but depends on context not fully visible.
- **Possible / needs-run:** suspicious; recommend confirming in the harness.

## Output contract (the findings report)

Lead with a one-line verdict (e.g. "No correctness defects found; 2 best-practice and 3 optimization notes"). Then list findings, correctness first:

```
[#] SEVERITY / CONFIDENCE   line or label
    Finding:  what is wrong or suboptimal
    Why:      the cited rule / technique / idiom + the reasoning (semantic trace)
    Fix:      suggested change; for optimization, the cycle/byte delta (cited) and
              "prove equivalent with 6502-optimization before applying"
```

Close with **what you could not assess statically** — anything that needs a run, and any code using macros / segments / ROM calls you could not trace — so the reader knows the review's blind spots.
