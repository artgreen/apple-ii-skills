# Merlin32 Assembler Reference

A factual reference for **Merlin32** (Brutal Deluxe's cross-platform reimplementation
of Glen Bredon's Merlin 16+) for 6502 / 65C02 / 65816 targets.

Sources cited inline as `[BD]` (Brutal Deluxe Merlin 32 project page,
<https://brutaldeluxe.fr/products/crossdevtools/merlin/>), `[BD-IDX]` (the syntax
index page <http://www.brutaldeluxe.fr/products/crossdevtools/merlin/index.html>),
`[M16+]` (Merlin 16+ Supplementary Manual, archive.org), `[MPRO]` (Merlin Pro
Manual `MerlinManual.txt`), and `[GH]` (digarok/merlin32 GitHub mirror).

Where Merlin32 and Merlin 16+ disagree, the difference is called out. Where the
docs are silent, the doc says so — **do not invent behavior**.

---

## 1. Invocation

### 1.1 Command line  `[BD]` `[GH]`

```
merlin32 [-V] <macro_folder_path> <source_file_path | link_file_path>
```

- `-V` (optional): verbose. Emits a listing file (`<name>_Output.txt`) and a
  symbol file (`<name>_Symbols.txt`) alongside the binary. Without `-V` you
  only get the binary.
- `<macro_folder_path>`: directory containing macro library files (named
  `*.Macs.s` on macOS/Linux distributions, `*.Mac.s` in the GNUmakefile
  install layout — both conventions appear in the GitHub README).
  `[GH]` notes the path is **optional** on recent builds — the install step
  bakes a default (`/usr/local/share/merlin32/asminc` or
  `%LOCALAPPDATA%\merlin32\asminc`) into the binary. Older binaries require
  the path on every invocation.
- The final argument is **either** a single master source file **or** a
  Link file (which then pulls in source files via `ASM` directives).

Example  `[BD]`:

```
Merlin32.exe -V c:\AppleIIgs\Merlin\Library c:\AppleIIgs\Source\Cogito\Cogito_Link.s
```

```
merlin32 ~/git/merlin32/Library skynet.s
merlin32 skynet.s          # uses compiled-in default macro folder
```

### 1.2 The macro folder  `[BD]`

Holds reusable macro definition files referenced by `USE` directives in
source. Typical contents: `M16.Macs.s`, `Locator.Macs.s`, etc., for GS/OS,
ToolBox, and ProDOS 16 entry points. For pure 6502/65C02 Apple II work the
folder can be empty — pass any directory.

### 1.3 Outputs  `[BD]`

| File                                  | When     | Contents                              |
|---------------------------------------|----------|---------------------------------------|
| `<DSKNAME>`                           | always   | Binary object code (fixed addr or OMF v2.1) |
| `_FileInformation.txt`                | always   | One line per binary: `NAME=Type(NN),AuxType(NNNN),…` — feed to AppleCommander to set ProDOS metadata |
| `<DSKNAME>_S01_Segment1_Output.txt`   | with `-V` | Full listing: line#, file, type, MX, reloc, size, addr, bytes, source |
| `<DSKNAME>_Symbols.txt`               | with `-V` | Symbol table (CSV; consumed by the CYRENE debugger) |

The output binary's name comes from the **`DSK` directive**, not the source
file name. If no `DSK` is given, the binary is named after the source
basename. The verbose listing is per-segment (`_S01_Segment1_Output.txt`,
`_S02_Segment2_Output.txt`, …) for Link-file builds; flat-binary builds
emit just `_S01_Segment1_Output.txt`. Confirmed by test assemble on
Merlin32 v1.2 beta 2.

### 1.4 Single-source vs. Link-file builds  `[BD]`

- **Single-source**: produces a flat binary at the address set by `ORG`.
  This is the mode you want for an Apple II `SYS`/`BIN` file.
- **Link-file**: A `.s` file consisting only of ASM/linker directives.
  Pulls multiple segments via `ASM` and emits an OMF v2.1 relocatable —
  GS/OS-only territory. See §10.

---

## 2. Source line structure

### 2.1 Column layout  `[MPRO]` `[M16+]`

A line has up to four fields, separated by whitespace (any amount):

```
LABEL    OPCODE   OPERAND     ;COMMENT
```

Any field except OPCODE may be omitted. Labels must start in column 1
(any leading whitespace puts the assembler into "no label" mode). Comments
may stand alone on a line.

### 2.2 Comments  `[MPRO]`

- `*` in **column 1** — full-line comment.
- `;` anywhere after the operand — trailing comment to end of line.

```
* This whole line is a comment.
        LDA #$80   ;trailing comment
```

### 2.3 Labels  `[MPRO]` `[BD-IDX]`

| Kind            | Syntax           | Scope                                       |
|-----------------|------------------|---------------------------------------------|
| Global          | `NAME` or `Name` | Entire assembly; case-sensitive in Merlin32 |
| Local           | `:name`          | Between two surrounding global labels       |
| Variable        | `]name`          | Mutable; redefinable with `=`               |
| Macro parameter | `]1` … `]8`      | Inside macro body only; `]0` = arg count    |

Rules:

- Global labels must begin with a character whose ASCII value is at least
  that of `:` (colon = $3A). In practice: letters and a handful of
  punctuation. They must contain only characters >= `'0'` ($30) `[MPRO]`.
- Merlin Pro documented a 13-character label limit (8 recommended)
  `[MPRO]`. Merlin 16+ raised it to 26 chars. **Merlin32 removes the
  limit entirely** `[BD]`.
- Local labels attach to the most recent global label and reset at the
  next one. Restrictions `[MPRO]`: cannot be used in macros, cannot label
  `MAC`/`EOM`/`EXT`, cannot be the first label in the program.
- Variable labels (`]name`) can be reassigned freely with `=`. Inside
  macros, `]1`..`]8` are the positional parameters and `]0` is their
  count.
- `[BD-IDX]` notes Merlin32 treats `]`-prefixed labels as having
  *backward-only* visibility and `:`-prefixed labels as visible
  forward/backward within the embracing globals.

### 2.4 Number and literal forms  `[MPRO]` `[BD-IDX]`

| Form        | Meaning                                       |
|-------------|-----------------------------------------------|
| `123`       | Decimal                                       |
| `$7B`       | Hexadecimal                                   |
| `%01111011` | Binary                                        |
| `'A'`       | ASCII byte, **high bit clear** ($41)          |
| `"A"`       | ASCII byte, **high bit set**   ($C1)          |
| `*`         | Current program counter                       |

Leading zeros are ignored in all numeric formats `[MPRO]`. The
single-quote / double-quote distinction is **load-bearing**: it's how you
choose normal-video vs. high-ASCII for the Apple II text screen without
adding `|$80` everywhere.

### 2.5 Immediate prefix and byte selectors  `[MPRO]` `[BD-IDX]`

- `#expr` — immediate operand. On the 65816 the *size* of `#expr` depends
  on `MX` (see §6).
- `<expr` — low byte of expr
- `>expr` — high byte of expr (bits 8..15)
- `^expr` — bank byte of expr (bits 16..23, 65816)
- `|expr` — Merlin Pro/16+ also documented `|` as "force absolute"
  addressing in some contexts (e.g. `LDA |$10` forces 2-byte abs even if
  the value fits in zero page) `[MPRO]`. Merlin32's published syntax
  index uses an opcode `L` suffix (e.g. `LDAL`) or operand `>` prefix
  for the long form; the `|` operator appears in older docs only —
  treat as Merlin 16+ heritage, verify before relying on it in
  Merlin32  `[BD-IDX]`.
- The Merlin Pro manual also describes a trailing colon on the opcode
  (`LDA: $10`) as forcing non–zero-page absolute. This is documented
  for Merlin Pro `[MPRO]`; not explicitly restated in the Merlin32
  syntax page.

```
LDA #<TARGET     ; immediate low byte of TARGET
LDA #>TARGET     ; immediate high byte
LDA #^TARGET     ; immediate bank byte (65816)
LDA #'A'         ; #$41
LDA #"A"         ; #$C1
```

---

## 3. Expression evaluation

### 3.1 Operators  `[BD]` `[BD-IDX]` `[MPRO]`

Documented operator set, with `[BD-IDX]` listing them "lowest to highest
priority":

| Operator       | Meaning                                              |
|----------------|------------------------------------------------------|
| `<` `=` `>` `#`| Relational: less / equal / greater / not-equal (result 0 or 1) |
| `+` `-`        | Add / subtract                                       |
| `*` `/`        | Multiply / integer divide                            |
| `&` `.` `!`    | Bitwise AND / OR / XOR                               |
| `-` (unary)    | Negation                                             |

### 3.2 Evaluation order — the most important Merlin gotcha

**Strict left-to-right with no precedence.**  `[BD]` `[MPRO]`

```
1+2*3       evaluates to 9    (not 7) -- (1+2)*3
1+2*3 in {} evaluates to 7     -- algebraic precedence within braces
```

`[BD-IDX]` documents that braces `{...}` switch to algebraic precedence;
the priority table above only applies *inside* braces. Outside braces,
operators are applied strictly in source order regardless of the table.

This bites every newcomer. If you mean `(N>>1)+BASE`, write
`{N/2}+BASE`, not `N/2+BASE` (which would compute `(N/2)+BASE` — same
answer here, but only because `/` happens first textually). When in
doubt, brace it.

### 3.3 Parentheses

Parentheses `(...)` are **not** grouping operators in Merlin — they are
part of indirect addressing-mode syntax (see §4). Use `{ ... }` for
expression grouping.

---

## 4. Addressing modes

### 4.1 6502 / 65C02 modes  `[MPRO]` `[BD-IDX]`

| Mode               | Syntax              | Notes                |
|--------------------|---------------------|----------------------|
| Implied / Accum    | `OPC`               | `CLC`, `ROR`         |
| Immediate          | `OPC #expr`         | size: 1 byte (6502/65C02) |
| Zero page          | `OPC expr`          | assembler picks 1-byte if expr fits |
| Zero page,X        | `OPC expr,X`        |                      |
| Zero page,Y        | `OPC expr,Y`        | `LDX`/`STX` only     |
| Absolute           | `OPC expr`          | 2-byte address       |
| Absolute,X         | `OPC expr,X`        |                      |
| Absolute,Y         | `OPC expr,Y`        |                      |
| (Indirect)         | `JMP (expr)`        | 6502 JMP only        |
| (ZP,X)             | `OPC (expr,X)`      |                      |
| (ZP),Y             | `OPC (expr),Y`      |                      |
| (ZP)               | `OPC (expr)`        | 65C02 only           |
| (Abs,X)            | `JMP (expr,X)`      | 65C02 only           |

To **force absolute** when an expression would fit in zero page: see
the trailing-colon (`LDA:`) and `|` notes in §2.5 — Merlin Pro behavior;
Merlin32 syntax page does not restate them, verify before relying.

### 4.2 65C02-specific opcodes  `[BD]`

Merlin32's documented opcode list at `[BD]` does **not** mention
`RMB`/`SMB`/`BBR`/`BBS` (the Rockwell/WDC bit-manipulation extensions).
`[BD-IDX]` likewise omits them. If you need them on a 65C02 target,
verify on the version you have — the docs are silent. (`pippin` targets
the WDC65C02 in the Apple IIc/IIe-enh, where these *do* exist as native
opcodes.)

### 4.3 65816 modes  `[BD-IDX]`

| Mode                                  | Syntax              |
|---------------------------------------|---------------------|
| Absolute Indirect Long                | `LDA [$2000]`       |
| Absolute Long                         | `LDAL $E12000` or `LDA >$E12000` |
| Absolute Long,X                       | `LDAL $E12000,X`    |
| Direct Page Indirect                  | `LDA ($10)`         |
| Direct Page Indirect Long             | `LDA [$10]`         |
| Direct Page Indirect Long Indexed Y   | `LDA [$10],Y`       |
| Stack Relative                        | `LDA $10,S`         |
| Stack Relative Indirect Indexed Y     | `LDA ($10,S),Y`     |
| Program Counter Relative              | `BEQ LABEL`         |
| Program Counter Relative Long         | `BRL LABEL`         |
| Stack Immediate (PEA)                 | `PEA $1010`         |

**Long-form selection**:  `[BD-IDX]`

- Append `L` to the mnemonic: `LDAL`, `STAL`, `CMPL`, `ORAL`, …
- *or* prefix the operand with `>`: `LDA >$E12000`.

**Block move** (`MVN`, `MVP`): the docs at `[BD]` list `MVN` and `MVP` as
supported opcodes, but **neither the BD page nor the syntax index gives
an explicit operand example**. The conventional Merlin syntax (and the
one used in Brutal Deluxe sample code) is:

```
MVN srcbank,dstbank
MVP srcbank,dstbank
```

Cite the Merlin 16+/8-16 manual chapter on 65816 if you need a definitive
quote — the supplementary manual confirms support but the text excerpts
fetched here do not contain a worked example.

### 4.4 Byte selectors on 65816  `[BD-IDX]`

```
LDA #<LABEL    ; bits  0..7
LDA #>LABEL    ; bits  8..15
LDA #^LABEL    ; bits 16..23  (bank byte)
```

Note `[BD-IDX]` calls `#>` "middle byte" on the 65816 because `#^` is the
"high (bank)" byte. On pure 6502 work `#>` is just the high byte.

---

## 5. Pseudo-ops / directives

For each: documented syntax and effect. Quotes are from the listed source.

### 5.1 Origin and segments

#### ORG  `[BD-IDX]`
```
ORG $2000
ORG $038000     ; 24-bit address for 65816 bank-aware code
ORG             ; no operand: re-establish previous ORG
```
Sets the assembled-code origin. Default $8000 per `[MPRO]`.

#### REL  `[BD]` `[BD-IDX]`
```
REL
```
Declare the source as relocatable. Output is OMF v2.1. Mutually exclusive
with `CHK` — `[BD-IDX]`: "Cannot be used with relocatable code."

#### OBJ  `[MPRO]`
```
OBJ $8000
```
Sets the address at which assembled bytes are *stored* during assembly
(distinct from `ORG`, which is the address bytes will *run from*).
Rarely needed in cross-assembly; mostly a holdover from on-machine Merlin.

#### DSK  `[BD-IDX]`
```
DSK MYPROG
DSK /HD/Programs/MyProg
```
Output filename. In a single-source build it's also accepted at the top of
the source. In a Link file it's mandatory and names the linked output.

#### TYP  `[BD]`
```
TYP $FF          ; ProDOS SYS
TYP $B3          ; GS/OS S16
```
Sets the ProDOS/GS-OS file type metadata for the output. Common Apple II
ProDOS types: `$06` BIN, `$FC` BAS, `$FF` SYS. GS/OS OMF types `$B2`–`$BD`
per `[BD]`. Accepts ASCII forms like `EXE`, `SYS` per `[M16+]`.

**`TYP` is required**, not optional — Merlin32 v1.2 beta 2 errors out
with `Can't find output file Type in Source files (use TYP directive)`
if it's absent. Verified by test assemble.

### 5.2 Data definition

#### HEX  `[BD-IDX]`
```
HEX 00010203
HEX 00,01,02,03      ; commas optional
```
Raw hex bytes. No `$` prefix, no expressions.

#### DFB / DB  `[BD-IDX]`
```
DFB $0A,$0B,14,%0000_1111
DFB MyLabel-OtherLabel,>MyLabel
```
Define byte(s). Accepts all numeric formats and expressions.

#### DDB  `[BD-IDX]`
```
DDB $000A,14       ; emits high byte then low byte
```
Define double byte, **high byte first** (big-endian).

#### DA / DW  `[BD-IDX]`
```
DA $000A,14        ; emits low byte then high byte
```
Define word, little-endian. `DA` and `DW` are synonyms.

#### ADR  `[BD-IDX]`
```
ADR $0A            ; 3 bytes, low byte first
```
Define 3-byte (24-bit) address. 65816-flavored.

#### ADRL  `[BD-IDX]`
```
ADRL $0A           ; 4 bytes, low byte first
```
Define 4-byte (32-bit) address.

#### DS  `[BD-IDX]`
```
DS 8               ; 8 zero bytes
DS 8,$EE           ; 8 bytes of $EE
DS \,$A0           ; pad to next page boundary with $A0
DS \               ; pad to next page boundary with zeros
```
Define storage. The `\` operand means "to next page boundary."

#### DUM / DEND  `[BD-IDX]` `[M16+]`
```
DUM $0000
RXBUF   DS 256
RXHEAD  DS 1
        DEND
```
Dummy section. Labels inside take values from a phantom PC starting at
the DUM address, but **no code is emitted**. Used to lay out RAM
structures.

### 5.3 String pseudo-ops

All accept single quotes (`'…'`, high bit clear) or double quotes
(`"…"`, high bit set). Per `[M16+]`: "now can handle strings with hex
data interspersed, and not just at the end as was formerly the case."

**Hex interspersion convention** — inside these string pseudo-ops, byte
values written **without** a `$` prefix are still hex (not decimal). So
`ASC "HI",8D` emits `C8 C9 8D` and `ASC "HI",$8D` does the same.
Confirmed by test assemble. This is unique to the string directives; in
`DFB`/`DA`/etc. unprefixed numbers are decimal as usual.

#### ASC  `[BD-IDX]`
```
ASC 'Hello'        ; 48 65 6C 6C 6F
ASC "Hello"        ; C8 E5 EC EC EF  (high-ASCII)
ASC 'Hi',$0D,'There'
```

#### DCI  `[BD-IDX]` `[M16+]`
```
DCI 'Hello'        ; last char has OPPOSITE high bit from rest
```
"Dextral Character Inverted" — terminator-by-flipped-bit convention used
by Apple's monitor/Sweet-16.

#### INV  `[BD-IDX]` `[M16+]`
```
INV 'HELLO'        ; inverse-video mapping
```
Maps to inverse-video screen codes. Per `[M16+]`: previously mapped lower
case to `$20-3F`; now maps to `$60-7F` for "direct screen store with the
alternate, or 80-column, character set." Empty strings now accepted.

#### FLS  `[BD-IDX]`
```
FLS 'HELLO'        ; flashing-video mapping ($40-$7F range)
```

#### REV  `[BD-IDX]` `[MPRO]`
```
REV 'DISK VOLUME'  ; emits 'EMULOV KSID'
```
String, reversed.

#### STR  `[BD-IDX]`
```
STR 'Hello'        ; 05 48 65 6C 6C 6F   (leading length byte)
```

#### STRL  `[BD-IDX]` `[M16+]`
```
STRL 'Hello'       ; 05 00 48 65 6C 6C 6F  (leading 2-byte length)
```
For GS/OS Class 1 strings.

### 5.4 Symbol / variable

#### EQU and =  `[BD-IDX]` `[MPRO]`
```
HOME    EQU $FC58
BUFLEN  =   256
PTR     =   *
```
Define a constant. `EQU` and `=` are synonyms. **Forward references are
not allowed** for `EQU`/`=` `[BD-IDX]`.

#### VAR  `[MPRO]` `[M16+]`
```
VAR 3;$42;LABEL    ; ]1 = 3, ]2 = $42, ]3 = LABEL
```
Bulk-assigns the macro parameters `]1`..`]8` outside a macro context.
Note the **semicolon separator** between values — comma is *not* used
here. Useful immediately before a `PUT` to pass parameters to the
included file.

#### Variable labels  `[BD-IDX]` `[MPRO]`
```
]COUNT   =   0
         …
]COUNT   =   ]COUNT+1
```
Variable labels (any `]name`) can be reassigned freely with `=`. Useful
in `LUP` loops.

### 5.5 Include / file ops

#### PUT  `[BD-IDX]` `[MPRO]`
```
PUT FILENAME            ; .s extension is implicit
PUT Cogito.Main
```
Textually include another source file at this point. Re-read on every
pass.

#### USE  `[BD-IDX]`
```
USE 4/Int.Macs
```
Include a macro file from the macro folder. Subfolder paths are stripped
by Merlin32 (`[BD-IDX]`: "subfolder path ignored in Merlin 32"). `USE`
files are typically cached in memory; macro definitions only.

#### PUTBIN  `[BD-IDX]`
```
PUTBIN Cogito.Logo
LogoSize EQU #Sound-#Logo
```
Includes a binary file as raw bytes at this point in the output. The
size can be computed by bracketing with labels (the `#Label` form yields
the address; subtract to get the length).

#### USR — historical  `[MPRO]`
```
USR OPERAND
```
On native Merlin, dispatched a `JSR $B6DA` to a user routine for custom
pseudo-ops. **Not documented at `[BD]` or `[BD-IDX]` for Merlin32** —
assume unsupported in cross-builds. If you find it in legacy source,
strip it.

### 5.6 Listing and trace control

All "off"/"on" tokens are case-insensitive per typical Merlin usage.

#### LST  `[BD-IDX]` `[M16+]`
```
LST OFF
LST ON
LST RTN          ; (M16+) only RTNs etc.
```
Toggle assembly listing. `[M16+]` documents `LST FILE,filename` to
redirect listing to a file.

#### EXP  `[M16+]`
```
EXP ON           ; show macro bodies in listing
EXP OFF
EXP ONLY         ; show only the expansion, not the source MAC line
```
Macro-expansion display in the listing.

#### PAG  `[MPRO]`
```
PAG
```
Page break in the listing (printer convention).

#### SKP  `[MPRO]`
```
SKP 5            ; skip 5 listing lines
```

#### TR  `[MPRO]`
```
TR ON
TR OFF
```
"Truncate" — limit object code display in the listing (3 bytes per line
when `ON`). Has nothing to do with execution tracing.

#### AST  `[MPRO]`
```
AST 10           ; print 10 asterisks
```
Prints asterisks in the listing for visual separation.

#### CYC  `[M16+]`
```
CYC ON
CYC AVE
CYC OFF
```
Per-instruction cycle counting in the listing.

#### DAT  `[BD-IDX]` `[M16+]`
```
DAT 1            ; "31-DEC-14" (high bit set)
DAT 2 .. DAT 8
```
Emit assembly date/time into the **object code**. `[M16+]` enumerates
formats 1–8 (date-only Merlin format, 9 bytes, through full date/time
control-panel format, 20 bytes). This is data, not metadata.

#### PAU  `[MPRO]`
```
PAU
```
Pause assembly (second pass) — interactive only; meaningless in
cross-assembly but accepted.

### 5.7 Conditional assembly

#### DO / ELSE / FIN  `[BD-IDX]` `[MPRO]`
```
DO    SYMBOL
        ; assembled when expression is non-zero
ELSE
        ; otherwise
FIN
```
Plain conditional. The expression is evaluated immediately. Merlin 16+
limited DO nesting to 8 deep; **Merlin32 removes that limit** `[BD]`.

#### IF / ELSE / FIN  `[BD-IDX]` `[M16+]`
```
IF MX/2          ; tests the M flag (accumulator size)
        ; …
FIN
```
`IF` is a variant that conditions on assembler state (notably the MX
flag for 65816). Also used inside macros to test the *form* of an
incoming argument (see §7.4).

#### Terminator note

Both `DO` and `IF` close with `FIN`. There's no `ENDIF` keyword.

### 5.8 Loops

#### LUP / `--^`  `[BD-IDX]` `[MPRO]`
```
        LUP 4
        ASL
        --^
```
Repeat the bracketed block N times. Maximum iterations: `$8000` (32768).

**Dynamic labels in loops** `[BD]`: use `@` in label names; the assembler
substitutes uppercase letters Z, Y, X, …, B, A on each iteration:

```
        LUP 4
@LOOP   NOP
        BRA @LOOP
        --^
```

Maximum iteration count for `@`-labels is 26 (one letter each) `[BD]`.

### 5.9 65816 processor mode

#### MX  `[BD-IDX]`
```
MX %00     ; A = 16-bit,  X/Y = 16-bit
MX %01     ; A = 16-bit,  X/Y = 8-bit
MX %10     ; A = 8-bit,   X/Y = 16-bit
MX %11     ; A = 8-bit,   X/Y = 8-bit    (native-startup default)
```

The MX flag tracks the 65816's `m` (bit 1) and `x` (bit 0) status bits
**for the assembler's benefit only** — it does *not* emit `REP`/`SEP`
opcodes. Its job: tell the assembler whether `#imm` is 1 or 2 bytes for
A-class and X/Y-class loads, since the 65816 immediate operand width
depends on processor state.

Per `[BD-IDX]`: "Automatically updated by `REP`/`SEP` opcodes during
assembly." So if you write `REP #$30` the assembler tracks the
implied `MX %00` until you write `SEP #$30` (or change MX manually).

On pure 6502/65C02 work you can ignore MX — but note `XC` (§5.10) below.

#### LONGA / LONGI  `[M16+]`
```
LONGA ON     ; equivalent to setting A to 16-bit
LONGA OFF
LONGI ON
LONGI OFF
```
APW-syntax aliases for the MX flag's two bits. `LONGA` ON = M=16; `LONGI`
ON = X/Y=16. Provided for portability with code written in APW format.

#### XC  `[M16+]`
```
XC           ; enable next CPU level: 6502 -> 65C02 -> 65816
XC           ; (called again) enable next level
XC OFF       ; back to 6502-only
```
Each `XC` directive expands the recognized opcode set by one level. From
a clean start (6502 only), one `XC` enables 65C02 opcodes; two `XC`s
enable 65816. `XC OFF` restores 6502-only. `[M16+]`: "XC OFF restores
Merlin's extended code to OFF, i.e., 6502 codes accepted only."

**Practically**: for the pippin project (Apple //e enh / //c WDC65C02),
you want **one** `XC` at the top of every source file that uses 65C02
opcodes. For IIgs/65816 code use `XC` twice (either two consecutive
lines or `XC XC` on a single line — both forms verified to assemble
identically).

**Empirical override**: in Merlin32 v1.2 beta 2, `XC` is effectively a
no-op — the assembler accepts **all** 65C02 and 65816 opcodes (STZ,
BRA, REP, PHB, PHK, MVN, etc.) regardless of XC level, even with zero
XC directives in the source. Verified by test assemble. Set `XC`
anyway: it documents your target CPU honestly and may be enforced in
future builds.

### 5.10 Macros

#### MAC / EOM / `<<<`  `[BD-IDX]` `[MPRO]`
```
WaitForKey  MAC
            LDA $C000
            BPL *-3
            STA $C010
            <<<                 ; or  EOM
```
`<<<` and `EOM` are synonyms ending a macro definition. The macro name
is the label in column 1 of the `MAC` line.

#### Macro invocation — bare name only in Merlin32  (empirically verified)
```
            WaitForKey               ; invoke: macro name in opcode column
:label      WaitForKey               ; labels (including :local) may precede
            Move      $300;$400      ; ]1=$300, ]2=$400 — args sep'd by ;
```
**Empirically confirmed against Merlin32 v1.2 beta 2**: macros are
invoked by writing the macro name in the opcode column, exactly like an
instruction. `PMC NAME` and `>>> NAME` (the Merlin 16+ forms documented
at `[MPRO]` and `[BD-IDX]`) raise "Unknown line" errors and are **not
accepted** in this Merlin32 build, despite being listed in the syntax
docs.

The Apple II Library shipped with Merlin32 (e.g.
`/Library/Dos.8.Macs.s`, `Mem.Macs.s`) uses only the bare-name form,
confirming this is the canonical convention.

Arguments are separated by **semicolons** (not commas), as `[MPRO]`
specifies.

#### Macro parameters  `[MPRO]` `[BD]`

| Symbol     | Meaning                                                     |
|------------|-------------------------------------------------------------|
| `]1`..`]8` | The 1st through 8th argument as a substitution string       |
| `]0`       | Number of arguments actually passed                         |

Arguments are **substituted textually** — they are not evaluated before
substitution. So `]1+1` inside a macro means "the text of arg 1, followed
by `+1`" which is then assembled as an expression.

```
INC4    MAC
        LDA ]1
        CLC
        ADC #4
        STA ]1
        <<<

        INC4 TIMER           ; expands to LDA TIMER / CLC / ADC #4 / STA TIMER
```

Merlin 16+ limited macro nesting to 15 deep; **Merlin32 removes that
limit** `[BD]`.

#### Local labels inside macros  `[MPRO]`  (empirically verified)

Per `[MPRO]`, traditional `:label` local labels are **not** allowed
inside macros — and **Merlin32 v1.2 beta 2 enforces this**. A `BPL
:check` or `BEQ :loop` inside a `MAC`/`<<<` body raises
`Can't find format for element ':check' in Operand ':check'` at
assembly time. Verified by test assemble.

Workaround: name labels via macro parameters (label `]2` and pass an
instance suffix as a separate argument so each invocation gets a
unique label), or do the branch arithmetically with `BEQ *+N`.

Note: `:label` *before* a macro invocation (in the outer scope) works
fine — e.g. `:loop  WAITKEY` is valid. The restriction is only inside
the macro body itself.

#### Conditional parameter tests  `[MPRO]`

Inside a macro, `IF` can test the **first character** of an argument:

```
        IF "=]1           ; true if first char of ]1 is "
        IF #=]1           ; true if first char of ]1 is # (immediate)
        IF (=]1           ; true if first char of ]1 is (  (indirect)
        IF )=]1           ; true if first char of ]1 is )
        IF /=]1
        ;  ...etc
```

This lets a macro choose between forms (e.g. "if my caller wrote
`#value`, use immediate mode; else use absolute"). The form is `IF
<char>=]<n>`. `[MPRO]` documents it; the Merlin32 syntax index doesn't
contradict it. The Merlin32 `[BD-IDX]` page says only "IF checks register
sizes" for the addressing-mode case — both uses coexist.

You can also do arithmetic on parameters: `]1+1`, `]1/$100`, etc., since
parameters substitute as expressions.

### 5.11 Linker / output

#### END  `[BD-IDX]` `[MPRO]`
```
END
```
Stops the assembler from reading further source. Optional but
recommended for cleanliness.

#### ERR  `[BD-IDX]` `[MPRO]`
```
ERR *-1/$9600     ; force an assembly error if PC > $9600
ERR MX-3          ; error if MX isn't %11 here
```
Forces an error (and aborts) when the expression is non-zero. Use to
bake assertions into the source.

#### CHK  `[BD-IDX]`
```
CHK
```
Emits a single checksum byte at this point — XOR of all preceding
emitted bytes. Cannot be combined with `REL` per `[BD-IDX]`.

#### ENT / EXT  `[BD-IDX]`
```
WaitForKey  ENT       ; export this label to the linker
WaitForKey  EXT       ; declare label as defined in another segment
```
Entry / external for the relocatable linker. Only meaningful with
`REL` / Link-file builds.

#### KBD — historical  `[MPRO]`

`LABEL KBD` accepted operator input at assembly time. **Not relevant to
Merlin32** (no interactive input in batch cross-assembly). Ignore.

---

## 6. The MX flag in depth (65816)

### 6.1 Bit definitions  `[BD-IDX]`

```
MX %ab
   ││
   │└── X bit (0):  X/Y register width.  1 = 8-bit, 0 = 16-bit
   └─── M bit (1):  Accumulator width.   1 = 8-bit, 0 = 16-bit
```

| MX    | A   | X/Y |
|-------|-----|-----|
| `%00` | 16  | 16  |
| `%01` | 16  | 8   |
| `%10` | 8   | 16  |
| `%11` | 8   | 8   |

After a hardware/native-mode reset the 65816 starts with both flags set
(MX = `%11`), so Merlin32 starts the same way.

### 6.2 Why it matters

It only changes the assembled size of `#`-immediate operands:

```
MX %11
        LDA #$00      ; 1-byte immediate -> A9 00
MX %00
        LDA #$1234    ; 2-byte immediate -> A9 34 12
```

For separate A and X/Y widths:

```
MX %10               ; A=8, X/Y=16
        LDA #$80     ; 1 byte after opcode
        LDX #$1234   ; 2 bytes after opcode
```

### 6.3 Automatic tracking  `[BD-IDX]`

When you write `REP #$30` or `SEP #$30`, Merlin32 updates the MX flag
automatically based on which bits are being cleared/set. This means you
usually don't need to set MX manually if you bracket transitions
correctly with REP/SEP.

For branches into code whose MX state is ambiguous, set MX explicitly:

```
        REP #$20
TARGET  MX %01        ; A=16, X/Y=8 at this label, regardless of fall-through
        LDA #$BEEF
```

### 6.4 LONGA / LONGI

Aliases that adjust the two MX bits independently. APW-portability only.

---

## 7. Macros — full picture

(Synthesizing §5.10 with examples.)

### 7.1 Definition  `[BD-IDX]`
```
NAME    MAC
        ;  body, using ]1..]8 for parameters
        <<<           ; or EOM
```

### 7.2 Invocation  (verified)
```
        NAME                       ; macro name in the opcode column
:label  NAME                       ; preceding label OK
        NAME arg1;arg2;arg3        ; args separated by ;
```
Arguments separated by `;`. There's no quoting of arguments — whatever
you write up to the next `;` or end-of-operand is the substitution text.

`PMC` and `>>>` are documented in older Merlin manuals but **do not
work** in Merlin32 v1.2 beta 2 — verified by test assemble. Use only
the bare-name form.

### 7.3 Parameters
- `]1` … `]8` — positional substitution strings (textual).
- `]0` — count of arguments actually passed.
- Inside-macro arithmetic uses normal expression evaluation:
  `LDA ]1+1`, `LDA ]1/$100`, etc.

### 7.4 Conditional dispatch on argument form

Per `[MPRO]`:

```
COPY    MAC
        IF #=]1                 ; immediate?
          LDA ]1
        ELSE
          IF (=]1               ; indirect?
            LDA ]1
          ELSE
            LDA ]1              ; absolute
          FIN
        FIN
        STA ]2
        <<<
```

The `<char>=]<n>` test compares the first character of `]n` to
`<char>`. Useful for macros that should accept multiple addressing
forms transparently.

### 7.5 Macro library convention

Place commonly used macros in `*.Macs.s` (or `*.Mac.s`) in the macro
folder and pull them in with `USE`:

```
        USE Common.Macs
```

---

## 8. Linker (Merlin32-specific)

### 8.1 When you need a Link file

Only for OMF v2.1 multi-segment GS/OS programs. A flat ProDOS 8 SYS/BIN
binary uses a single source file + `ORG` + (optionally) `DSK`. **The
pippin project does not need a Link file.**

### 8.2 Link file format  `[BD]` `[BD-IDX]`

A `.s` file that consists only of linker directives. No 6502 opcodes.

**Program-level (once at the top):**

| Directive | Effect                                                       |
|-----------|--------------------------------------------------------------|
| `DSK <name>`  | Output filename                                          |
| `TYP <val>`   | GS/OS file type: `$B2`..`$BD` OMF, others fixed-address  |
| `AUX <val>`   | Auxiliary type. Default `$0000`                          |
| `XPL`         | Append an ExpressLoad segment (faster GS/OS load)        |

**Per-segment block (repeat for each):**

| Directive | Effect                                                                |
|-----------|-----------------------------------------------------------------------|
| `ASM <file>`  | Master source file for this segment                               |
| `DS <n>`      | Append N zero bytes after the segment (default 0)                 |
| `KND <val>`   | Segment kind/attributes (default `#$1100`)                        |
| `ALI <kw>`    | Alignment: `BANK` ($10000) / `PAGE` ($100) / `NONE` (default)     |
| `BSZ <val>`   | Bank size, default `$10000`                                       |
| `ORG <addr>`  | Absolute load address; `0` = relocatable                          |
| `LNA <name>`  | Load segment name (max 10 bytes)                                  |
| `SNA <name>`  | Segment name                                                      |

`KND` low byte: `$00` Code, `$01` Data, `$02` Jump-Table, `$04`
Pathname, `$08` Library, `$10` Init, `$12` Direct-page. High byte: flag
bits — see `[BD-IDX]` for the table.

### 8.3 PUT vs. USE

- `PUT` — full source file, re-read every pass; lives in the segment
  it's `PUT` into. Use for ordinary modules of your program.
- `USE` — macro library file, typically cached. Use for shared macro
  definitions only.

Mechanically the assembler reads them at the same point in the source,
but the convention separates concerns.

---

## 9. Differences from Merlin 16+  `[BD]`

Per the Brutal Deluxe page, Merlin32 **removes** the following Merlin16+
limits:

| Limit                       | Merlin 16+        | Merlin32 |
|-----------------------------|-------------------|----------|
| Source file size            | 64 KB             | unlimited |
| Source line length          | 255 chars         | unlimited |
| Label length                | 26 chars          | unlimited |
| Operand section             | 80 chars          | unlimited |
| External references         | 255               | unlimited |
| Macro nesting               | 15                | unlimited |
| Conditional nesting         | 8                 | unlimited |
| Symbol table                | 4096 short / 2048 long | unlimited |

**Link file format is incompatible**: Merlin 16+ link files cannot be
used directly with Merlin32.

Some directives present in Merlin 16+/Pro are not (re-)documented for
Merlin32 — `USR`, `KBD`, `PAU`, `CAS`, `XREF`/`XREFA`, `FLO`. These
were either interactive-only or rarely useful in cross-assembly. If
your source uses them, expect either silent acceptance or an error;
test on your specific build.

### 65C02 bit-manipulation opcodes

`RMB`/`SMB`/`BBR`/`BBS` are **not in the documented opcode list** at
`[BD]`. The Merlin32 source supports the WDC W65C02 standard set, but
whether these Rockwell extensions assemble depends on the build. If
your target is the //c/llcplus's WDC chip and you need them, write a
short test source and check the output before committing to that path.

---

## 10. Common gotchas and conventions

### 10.1 No operator precedence outside braces

```
LDA #BASE+$10*4       ; this is (BASE+$10)*4, NOT BASE + ($10*4)
LDA #BASE+{$10*4}     ; force algebraic precedence
```
This is the single most common source of bugs. When in doubt, brace.

### 10.2 `;` vs `,`

- Addressing-mode operand lists use `,` — `LDA $2000,X`, `DFB 1,2,3`.
- Macro invocation argument lists use `;` — `COPY SRC;DST` (recall:
  macro invocation is by bare name in the opcode column; `PMC` and
  `>>>` do not work in Merlin32 v1.2 beta 2 — see §5.10).
- `VAR` uses `;` — `VAR 3;$42;LABEL`.
- Comments are introduced by `;` (when in the comment field, not the
  operand field).

If you accidentally write `COPY SRC,DST` (with comma) the assembler
sees one argument, the string `SRC,DST`. Conversely `LDA $2000;X` will
swallow `;X` as a comment.

### 10.3 High-bit strings on text screen

Apple II text display puts the inverse/flashing video range at low ASCII
and normal video at high ASCII. So output strings want `"…"` (high bit
set), not `'…'`. Tedious but normal.

```
BANNER  ASC "PIPPIN v0.1",$8D,$00
```

(`$8D` = CR with bit 7 set; `$00` here is the writer's terminator
convention, not Merlin syntax — the byte is just appended via the
expression.)

### 10.4 Forward references

Merlin is **two-pass**. Forward label references work in most contexts
— branches, JSR, JMP, data definitions (`DFB`, `DA`, `DW`, `ADR`, …).

`EQU`/`=` cannot forward-reference per `[BD-IDX]`. So this fails:

```
SIZE    EQU END-START      ; END not yet defined -> error
START   …
END
```

Workaround: put `EQU`s after the labels they depend on, or compute the
length at use-sites with `*` arithmetic.

The size of forward-referenced operands is also resolved on pass 2. On
the 65816 the assembler may need a hint (long form `LDAL` or `>` prefix)
to know up front whether to reserve 2 or 3 operand bytes.

### 10.5 Reserved characters and label-content rules

Per `[MPRO]`, label characters must be `>= '0'` ($30). That excludes
space, `!`, `"`, `#`, `$`, `%`, `&`, `'`, `(`, `)`, `*`, `+`, `,`, `-`,
`.`, `/`. The first character additionally must be `>=':'` ($3A) — so
digits as first character are out (which would otherwise be parsed as
numeric literals anyway).

Practically: stick to letters, digits (not first), and `_`. Merlin32
removes the *length* limit, not the *character* rules.

### 10.6 Case sensitivity

Merlin Pro/16+ defaulted to case-insensitive labels with a `CAS SE/IN`
toggle `[M16+]`. The Merlin32 `[BD-IDX]` page describes globals as
"case-sensitive" by default. If you mix `Foo` and `foo` and they're
treated as the same on your Merlin32 build, that's the 16+ heritage
asserting itself — write a one-line test and pin down behavior before
relying.

### 10.7 Mixing comments and operands

A `;` in the operand field of a non-string pseudo-op begins a comment.
Inside an `ASC`/`STR`/`DCI`/etc. delimited by quotes, `;` is just a
character. Inside `VAR` and macro-invocation argument lists, `;` is a
separator. Mind which context you're in.

### 10.8 The `*` overload

`*` means three different things depending on column:

- In **column 1**: start of a full-line comment.
- In an **expression**: current program counter.
- In the operator position **within an expression**: multiply.

```
* This is a comment.
LOOP    LDA #0
        BRA *           ; jump to self (PC reference)
SIZE    EQU *-LOOP      ; PC minus start  (PC reference)
COUNT   EQU 10*4        ; multiplication
```

---

## 11. Quick example — minimal Apple II ProDOS SYS source

```
*  HELLO.SYSTEM -- minimal ProDOS SYS file

        XC                    ; enable 65C02 opcodes
        ORG  $2000            ; ProDOS SYS load address
        TYP  $FF              ; ProDOS SYS file type
        DSK  HELLO.SYSTEM

COUT    EQU  $FDED            ; ROM character-out

START   LDX  #0
:LOOP   LDA  BANNER,X
        BEQ  :DONE
        JSR  COUT
        INX
        BRA  :LOOP
:DONE   JMP  $BE00            ; back to BASIC.SYSTEM

BANNER  ASC  "HELLO, WORLD",$8D
        DFB  $00

        END
```

Assemble:

```
merlin32 . HELLO.S
```

This produces a flat binary `HELLO` of the assembled size. Put it on a
ProDOS disk as type `$FF`, aux `$0000`, named `HELLO.SYSTEM`.

---

## 12. Sources

- `[BD]`   Brutal Deluxe Merlin 32 project page —
  <https://brutaldeluxe.fr/products/crossdevtools/merlin/>
- `[BD-IDX]` Merlin 32 Syntax index —
  <http://www.brutaldeluxe.fr/products/crossdevtools/merlin/index.html>
- `[GH]`   digarok/merlin32 README — <https://github.com/digarok/merlin32>
- `[M16+]` Merlin 16+ Supplementary Manual (Archive.org) —
  <https://archive.org/details/Merlin_16_Supplementary_Manual>
- `[MPRO]` Merlin Pro Macro Assembler manual —
  <https://gswv.apple2.org.za/a2zine/Docs/MerlinManual.txt>
- Merlin 8/16 Macro Assembler manual (Archive.org) —
  <https://archive.org/details/Merlin_816_Macro_Assembler_Manual>
  (general reference; specific syntax sections were not fetchable from
  the OCR'd djvu text and are noted as "verify" above where relied on.)

### Empirical findings (Merlin32 v1.2 beta 2)

These were verified by test assemble and override the documented
behavior where they conflict:

- **`PMC` and `>>>` macro invocations are not accepted.** Use bare
  macro name in the opcode column. See §5.10, §7.2.
- **`TYP` is mandatory**, not optional. See §5.1.
- **`XC` is effectively a no-op.** All 65C02 and 65816 opcodes (STZ,
  BRA, REP, PHB, PHK, MVN, …) assemble cleanly regardless of XC level,
  even with zero `XC` directives. See §5.9.
- **`:label` local labels are forbidden inside macro definitions** —
  produces `Can't find format` at assembly time. They're fine in the
  outer scope, including immediately before a macro invocation. See
  §5.10.
- **Hex interspersion in string pseudo-ops works without `$` prefix**:
  `ASC "HI",8D` and `ASC "HI",$8D` are equivalent. See §5.3.
- Output binary is named by the `DSK` directive (uppercased as written),
  not the source filename. The verbose listing is
  `<DSK>_S01_Segment1_Output.txt`. A `_FileInformation.txt` is always
  produced beside the binary. See §1.3.
- `XC XC` on a single line and two consecutive `XC` lines produce
  identical effect (both verified). See §5.9.

### Conflict notes

- `[MPRO]` and `[BD-IDX]` disagree on case-sensitivity defaults
  (insensitive-with-toggle vs. sensitive). §10.6.
- `[MPRO]` documents `:label` locals as forbidden inside macros;
  `[BD-IDX]` is silent. §5.10.
- The `|` byte-selector / force-absolute operator from `[MPRO]` is not
  restated in `[BD-IDX]`. §2.5.
- `RMB`/`SMB`/`BBR`/`BBS` (65C02 Rockwell) are not in the Merlin32
  documented opcode list. §4.2.
- `USR`, `KBD`, `PAU`, `CAS`, `XREF`/`XREFA`, `FLO` from `[M16+]`/`[MPRO]`
  are not (re-)documented for Merlin32 — verify on your build. §9.
- `MVN`/`MVP` operand syntax is not given an explicit example in the
  fetched Merlin32 docs. §4.3.
