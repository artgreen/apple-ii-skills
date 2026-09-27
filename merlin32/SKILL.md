---
name: merlin32
description: "Use when reading, writing, editing, or assembling Merlin32 source for 6502, 65C02, or 65816 targets; when a task mentions Merlin32 directives, pseudo-ops, macros, the MX flag, linker behavior, or .s files in Merlin/Apple II/Apple IIgs context. Not for cc65/ca65, xa, dasm, or other 6502 assemblers."
license: MIT
---

# Merlin32

Merlin32 is a cross-platform 6502/65C02/65816 assembler with column-sensitive
syntax and quirky-but-stable semantics inherited from 1980s Apple II
toolchains. The full reference lives in [references/merlin32-reference.md](references/merlin32-reference.md);
this file covers the parts you need in working memory.

**The reference doc is authoritative for everything below.** When in doubt
(uncommon directive, edge-case syntax, linker behavior, 65816 modes), grep
or read it before guessing.

## Invocation

```
merlin32 [-V] <macro_folder> <source.s>
```

- `-V` adds a per-segment listing and CSV symbol file. Useful when debugging.
- `<macro_folder>` is required positionally even if you don't use macros —
  pass any directory. Set `MERLIN32_LIBRARY` to your installed Apple II macro library directory.
  See the repository README for configuration examples.
- Output binary is named by the `DSK` directive in the source (NOT the
  source filename). If `DSK` is absent, it falls back to the source basename.
- An adjacent `_FileInformation.txt` is always produced, encoding the
  ProDOS `TYP`/`AUX` so AppleCommander can apply the metadata to a disk image.

Example:
```
merlin32 "$MERLIN32_LIBRARY" src/main.s
```

## Source layout — read before writing a single line

Merlin is column-sensitive. **The label field starts at column 1.** Any
leading whitespace on a line means "no label." A line is:

```
LABEL   OPCODE   OPERAND     ;COMMENT
```

- Full-line comment: `*` in column 1
- Trailing comment: `;` after the operand (outside of strings)
- Indentation is whitespace, any amount — but mnemonics must NOT be in
  column 1 or they'll be parsed as labels

### Labels

| Kind     | Syntax  | Scope                                       |
|----------|---------|---------------------------------------------|
| Global   | `Name`  | Whole program                               |
| Local    | `:name` | Between adjacent globals; resets per global |
| Variable | `]name` | Reassignable with `=`; common in `LUP` loops |

Macro parameters use `]1` … `]8` (positional, textual substitution) and
`]0` (count).

### Numbers and literals

- `$7B` hex, `%01111011` binary, `123` decimal
- `'A'` = `$41` (high bit **clear**), `"A"` = `$C1` (high bit **set**)
- Apple II text screen displays high-ASCII as normal video, so output
  strings almost always want double-quotes
- `*` in an expression = current PC

### Byte selectors

- `<expr` low byte, `>expr` high byte, `^expr` bank byte (65816)
- `#expr` immediate

## The expression-evaluation footgun

**Merlin has NO operator precedence outside braces.** Expressions are
evaluated strictly left-to-right.

```
LDA #BASE+$10*4       ; this is (BASE+$10)*4 — left-to-right
LDA #BASE+{$10*4}     ; force algebraic precedence with braces
```

When in doubt: brace it. `(...)` is reserved for indirect addressing
modes; `{...}` is the grouping operator.

## CPU selection — `XC` directive

The Merlin docs describe `XC` as progressively enabling CPU levels:

- `XC` once → enable 65C02 opcodes (use for //e enh, //c, IIc+)
- `XC` twice (either two consecutive lines or `XC XC` on one line) →
  enable 65816 opcodes (use for IIgs)
- `XC OFF` → back to 6502

**Empirically, Merlin32 v1.2 beta 2 accepts all 65C02 and 65816 opcodes
regardless of `XC`** — it's effectively a no-op in this build (verified
by test assemble). Still put the right `XC` at the top of every source
file: it documents your target CPU for readers, and may be enforced in
future Merlin32 versions or other assemblers reading the same source.

## Common directives — quick reference

For full syntax and edge cases, see [references/merlin32-reference.md](references/merlin32-reference.md).

| Need              | Directive                              |
|-------------------|----------------------------------------|
| Set load address  | `ORG $2000`                            |
| Name output file  | `DSK MYPROG`                           |
| ProDOS file type  | `TYP $FF`  (FF=SYS, 06=BIN, FC=BAS) — **required** |
| Constant          | `NAME EQU $C000`  or  `NAME = $C000`   |
| Reserve bytes     | `DS 256`  /  `DS 8,$00`  /  `DS \` (page-align) |
| Define byte data  | `DFB $0A,$0B,14`                       |
| Define word LE    | `DA $1234` / `DW $1234`                |
| Define word BE    | `DDB $1234`                            |
| 3-byte address    | `ADR $E12000` (65816)                  |
| Raw hex blob      | `HEX 0A0B0C0D`                         |
| ASCII string      | `ASC "TEXT"` (high), `ASC 'text'` (low) |
| Length-prefixed   | `STR "TEXT"`                           |
| Include source    | `PUT filename`                         |
| Include macro lib | `USE Filename.Macs`                    |
| Dummy section     | `DUM $0000` … `DEND`                   |
| Conditional       | `DO expr` / `ELSE` / `FIN`             |
| Mode-based cond   | `IF MX/2` / `ELSE` / `FIN`             |
| Loop              | `LUP n` … `--^`                        |
| End source        | `END`                                  |

**Hex interspersion in strings**: inside `ASC`/`DCI`/`STR`/etc., comma-
separated values after the quoted portion are hex by default — `ASC
"HI",8D` and `ASC "HI",$8D` are equivalent.

## Macros

```
INC2    MAC                  ; define
        INC  ]1
        BNE  :NC
        INC  ]1+1
:NC     <<<                  ; or EOM

        INC2 COUNTER         ; invoke — bare name in the opcode column
:LABEL  INC2 COUNTER         ; labels (including :local) may precede the macro
        INC2 SRC;DST         ; multiple args separated by ;
```

Critical rules:
- **Invoke macros by writing the macro name in the opcode column** —
  exactly like an instruction. Merlin32 v1.2 beta 2 does **NOT**
  accept `PMC NAME` or `>>> NAME` (the Merlin 16+ forms); they raise
  "Unknown line" errors. The Apple II Library at
  `$MERLIN32_LIBRARY/` uses the bare-name form throughout.
- **Arguments are separated by `;`, NOT `,`.** `FOO A,B` is one argument
  (`A,B`), not two.
- Parameters substitute **textually**, before evaluation. `]1+1` means
  "the text of arg 1 followed by `+1`".
- Conditional dispatch on argument form: `IF #=]1` (immediate-prefixed),
  `IF (=]1` (indirect-prefixed), `IF "=]1`, etc. Compares first character.
- Common idiom: macros that test `MX>1` to emit different code in 8-bit
  vs 16-bit accumulator modes.

The Apple II library at `$MERLIN32_LIBRARY/` has dozens of
worked examples (ProDOS, GS/OS, Toolbox). Read those first if you're
writing a non-trivial macro.

## 65816 essentials — the MX flag

`MX %ab` tracks 65816 processor state for the assembler:
- bit 1 (`M`): accumulator width — 0=16, 1=8
- bit 0 (`X`): index register width — 0=16, 1=8

| MX    | A   | X/Y |
|-------|-----|-----|
| `%00` | 16  | 16  |
| `%01` | 16  | 8   |
| `%10` | 8   | 16  |
| `%11` | 8   | 8 (default) |

This affects the **size of `#immediate` operands only** — the assembler
needs to know whether `LDA #$1234` is 1 or 2 bytes after the opcode.
`REP`/`SEP` update MX automatically; set explicitly only if you branch
into ambiguous state.

For 65816 long addressing: use opcode `L` suffix (`LDAL $E12000`) or
operand `>` prefix (`LDA >$E12000`).

## Workflow: editing existing Merlin32 source

1. **Check the file's CPU level.** Look for `XC` near the top. No `XC`
   = 6502; one = 65C02; two = 65816.
2. **Check the MX state** if it's 65816 code. Track REP/SEP through to
   the edit point, or look for an explicit `MX %nn` above your insertion.
3. **Match the existing indentation.** Merlin sources typically use
   either tab or a consistent run of spaces between fields. Don't mix.
4. **Watch column 1.** Anything in column 1 is a label or comment. If you
   want to insert a new instruction, indent it.
5. **Macro args use `;`.** If you're invoking a macro inside the code
   you're editing, use semicolons between args.
6. **Re-assemble after every edit.** Merlin32 errors are usually clear,
   but two-pass forward-reference behavior means some mistakes only show
   up on pass 2.

## Workflow: writing new Merlin32 source

Minimal Apple II ProDOS SYS skeleton:

```
*  myprog.s
            xc                       ; 65C02
            org   $2000
            typ   $ff                ; ProDOS SYS
            dsk   MYPROG.SYSTEM

* ROM entry points
cout        equ   $fded
prbyte      equ   $fdda

start       ldx   #0
:loop       lda   banner,x
            beq   :done
            jsr   cout
            inx
            bra   :loop
:done       jmp   $be00              ; back to BASIC.SYSTEM

banner      asc   "HELLO, MERLIN32!",8d,00

            end
```

Assemble:
```
merlin32 "$MERLIN32_LIBRARY" myprog.s
```

Verify success:
1. No "ERROR" lines in stdout
2. Binary file matches the `DSK` name
3. `_FileInformation.txt` has the right TYP

To inspect generated machine code without re-running, use `xxd
<binary>` or rebuild with `-V` and read `<DSK>_S01_Segment1_Output.txt`.

## When to read the full reference

The reference doc covers every directive with citations to primary sources.
Read or grep [references/merlin32-reference.md](references/merlin32-reference.md) when:

- You hit a directive not in the table above (`CHK`, `ENT`/`EXT`,
  `ADRL`, `VAR`, `LST`, `EXP`, `CYC`, `DAT`, `ERR`, `PUTBIN`, `REL`, …)
- You need addressing-mode syntax for an unfamiliar form
- You're writing a Link file (multi-segment OMF output for GS/OS)
- You suspect a Merlin 16+ idiom from old source code that may not work
  in Merlin32 (the reference has a "Differences from Merlin 16+" section)
- You hit a case-sensitivity, forward-reference, or label-character issue

The reference cites every claim to a primary source (`[BD]`, `[BD-IDX]`,
`[M16+]`, `[MPRO]`, `[GH]`) — if a section is missing a citation, that's
a known-uncertain area and you should verify before committing to it.

## Gotchas summary

- No operator precedence outside `{...}` — strict left-to-right
- Macro args use `;` not `,`
- Macros are invoked by bare name in the opcode column — `PMC` / `>>>`
  don't work in Merlin32 v1.2 beta 2
- `:label` local labels can be used **before** a macro invocation, but
  **not inside** a macro definition (`Can't find format` error)
- `(...)` is for addressing modes, `{...}` is for expression grouping
- Column 1 = label position; mnemonics must be indented
- `'…'` = low ASCII; `"…"` = high ASCII (for Apple II text display)
- `EQU`/`=` cannot forward-reference
- `TYP` is mandatory — Merlin32 errors out without it
- 65C02 Rockwell ops (`RMB`/`SMB`/`BBR`/`BBS`) aren't documented for
  Merlin32 — test before relying on them
- `XC` is documentation-only in v1.2 beta 2 (no-op); set it correctly
  anyway so the source reads honestly
