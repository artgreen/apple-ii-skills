---
name: apple-ii
description: Coordinate Apple II and IIgs programming work by selecting the relevant assembly, BASIC, interface, testing, and optimization skills. Use for projects spanning several of these areas or when the user wants guidance on which specialist to use.
license: MIT
---

# Apple II workflow coordinator

Select and read only the specialists needed for the user's task. They remain
independently usable; a narrow request can go directly to its specialist.
These skills are sibling directories in the `apple-ii-skills` repository.
Resolve this file's symlink to the repository before following the relative
links below; do not assume all specialists are installed in the same agent's
skill directory.

## Select the relevant skills

| Task | Read |
|---|---|
| Apple II memory, ROM, soft switches, graphics, I/O, ProDOS, or IIgs platform details | [apple-assembly-programming](../apple-assembly-programming/SKILL.md) |
| Write, fix, or explain CPU-level assembly routines | [6502-codegen](../6502-codegen/SKILL.md) |
| Merlin source syntax, macros, directives, assembly, or 65816 width tracking | [merlin32](../merlin32/SKILL.md) |
| Run or debug an assembled Apple II program | [6502-testing](../6502-testing/SKILL.md) |
| Audit assembly without execution | [6502-review](../6502-review/SKILL.md) |
| Improve the speed or size of working 6502/65C02 code | [6502-optimization](../6502-optimization/SKILL.md) |
| Build or debug 80-column MouseText widgets | [apple-ii-textui](../apple-ii-textui/SKILL.md), plus platform guidance for banking and screen access |
| Write, debug, test, or tune Applesoft BASIC | [applesoft-basic](../applesoft-basic/SKILL.md) |

Read dependencies required by the selected specialist, but do not load the
entire collection or every reference by default. If a specialist is missing,
identify the missing path and the affected portion of the task.

## Compose a workflow

- **New assembly program:** establish the machine, CPU, assembler, and launch
  environment from the project. Use platform guidance, codegen, and the
  matching assembler skill; then test routines and the built program at the
  appropriate levels. Merlin32 guidance applies only to Merlin source.
- **Runtime defect:** use the program testing skill to reproduce it, then the
  relevant platform or codegen skill to fix it and rerun the affected checks.
- **Static review:** use the review skill and its reference dependencies.
  Keep its findings distinct from execution evidence. A request for review
  alone does not call for applying fixes or starting an optimization project.
- **Optimization:** establish the working behavior and target constraint,
  then use the optimization skill's equivalence checks. Recheck machine
  interactions if the change affects them.
- **Text interface:** combine text UI recipes with platform mechanics and
  program testing; verify the actual screen bytes.
- **BASIC with machine-language routines:** use Applesoft for the BASIC side
  and codegen/platform guidance for the machine-language interface; test the
  combined behavior in the emulator.

## Scope and evidence

Honor the project's explicit CPU and machine target. If absent, use the
specialist's documented default and state the assumption; ask only when an
unresolved choice materially affects the task. Distinguish NMOS 6502,
65C02 variants, and 65816 emulation/native mode.

Keep opcode facts and cycle costs in the codegen reference, platform facts
in the platform reference, and assembler syntax in its own skill. Do not
duplicate their tables here. The CPU-generic skills remain usable for other
6502 machines; do not apply Apple II addresses or ROM conventions to them.

The bundled py65 harness does not execute native 65816 code. Merlin32's
65816 syntax support is not a substitute for native-mode runtime testing;
report what was assembled, executed, or checked only against references.
Likewise, simulator equivalence across a test corpus is not a hardware timing
measurement. Report verification and any remaining limits precisely.
