# Applesoft BASIC Reference

Verified reference for Applesoft BASIC (the floating-point Microsoft BASIC in
Apple II ROM, $D000–$F7FF). Provenance markers on claims:

- **[emu]** — behavior verified by running it in microM8 (Apple IIe, ProDOS
  BASIC.SYSTEM 1.5), 2026-06-11.
- **[rom]** — dumped or disassembled from the Applesoft ROM image in that
  same session (keyword table, error table, routine entry points).
- **[doc]** — documentary, with source: Applesoft II BASIC Programming
  Reference Manual (mirrors.apple2.org.za), calormen.com/jsbasic/reference.html
  (Joshua Bell's Applesoft reference), ProDOS 8 Technical Reference appendix
  (prodos8.com), Beneath Apple ProDOS, retrocomputing.stackexchange.com (RSE),
  and five Beagle Bros wall charts, 1982–84 (tags `doc:beagle*`; editions
  and their verified errata in §15).

Unmarked statements are uncontroversial Applesoft basics.

## 1. Program model

- Line numbers 0–63999. 64000+ is a `?SYNTAX ERROR` at entry. [emu]
- A statement without a line number executes immediately ("immediate mode");
  with one, it's stored ("deferred mode"). `INPUT`, `GET`, `DEF FN` only work
  in deferred mode (`?ILLEGAL DIRECT`, error code 149 [rom]).
- Multiple statements per line, separated by `:`.
- Entered lines are limited to 239 characters (GETLN buffer at $0200). [doc:manual]
- Spaces are insignificant outside quotes, `REM`, and `DATA`; the tokenizer
  strips them and `LIST` re-inserts its own. Keep code uppercase: lowercase
  keywords happen to tokenize on the IIe [emu], but II/II+ keyboards can't
  even type lowercase — reserve it for string contents.
- Entering an existing line number replaces that line; a line number alone
  deletes the line. `DEL first,last` deletes a range. `LIST n-m` lists a
  range (also `LIST -n`, `LIST n-`).
- Line editing at the keyboard [doc:beagle-cmds]: left-arrow (ctrl-H)
  backs up; right-arrow (ctrl-U) **copies** the character under the cursor
  into the input; ctrl-X cancels the line being typed — it echoes `\` and
  discards [emu]. ESC enters cursor moves: ESC A/B/C/D step
  right/left/down/up once; ESC I/J/K/M (arrows on a IIe) move repeatedly
  until a normal key; ESC @ clears the screen. The classic edit workflow:
  LIST the line, ESC-move onto its first character, trace along it with
  right-arrow to copy, typing replacements where needed (`POKE 33,33`
  first so LIST's wrap padding doesn't get copied — §11 tricks). ctrl-C
  stops a running program (code 255 under ONERR, §10).

### Line storage format [emu — hex dump of an entered program]

Program text starts at $0801 (TXTTAB $67/$68 points there), and the byte at
$0800 must be $00. Each line:

| bytes | meaning |
|---|---|
| 2 | link: address of the next line (lo,hi) |
| 2 | line number (lo,hi, unsigned) |
| n | tokenized text: keywords as single bytes ≥ $80, everything else literal ASCII |
| 1 | $00 end-of-line |

A link of $0000 ends the program. Verified dump of `10 PRINT "HI"`:

```
0800: 00 0B 08 0A 00 BA 22 48 49 22 00 00 00
      ^  ^link ^ln10 ^BA=PRINT "HI"  ^eol ^end
```

`REM` and `DATA` contents are stored literally (untokenized) to end of line /
statement. Numeric literals are stored as ASCII and re-parsed on every
execution (see §13 Performance).

### Token table [rom — decoded from the keyword table at $D0D0]

| | | | | |
|---|---|---|---|---|
| 80 END | 81 FOR | 82 NEXT | 83 DATA | 84 INPUT |
| 85 DEL | 86 DIM | 87 READ | 88 GR | 89 TEXT |
| 8A PR# | 8B IN# | 8C CALL | 8D PLOT | 8E HLIN |
| 8F VLIN | 90 HGR2 | 91 HGR | 92 HCOLOR= | 93 HPLOT |
| 94 DRAW | 95 XDRAW | 96 HTAB | 97 HOME | 98 ROT= |
| 99 SCALE= | 9A SHLOAD | 9B TRACE | 9C NOTRACE | 9D NORMAL |
| 9E INVERSE | 9F FLASH | A0 COLOR= | A1 POP | A2 VTAB |
| A3 HIMEM: | A4 LOMEM: | A5 ONERR | A6 RESUME | A7 RECALL |
| A8 STORE | A9 SPEED= | AA LET | AB GOTO | AC RUN |
| AD IF | AE RESTORE | AF & | B0 GOSUB | B1 RETURN |
| B2 REM | B3 STOP | B4 ON | B5 WAIT | B6 LOAD |
| B7 SAVE | B8 DEF | B9 POKE | BA PRINT | BB CONT |
| BC LIST | BD CLEAR | BE GET | BF NEW | C0 TAB( |
| C1 TO | C2 FN | C3 SPC( | C4 THEN | C5 AT |
| C6 NOT | C7 STEP | C8 + | C9 - | CA * |
| CB / | CC ^ | CD AND | CE OR | CF > |
| D0 = | D1 < | D2 SGN | D3 INT | D4 ABS |
| D5 USR | D6 FRE | D7 SCRN( | D8 PDL | D9 POS |
| DA SQR | DB RND | DC LOG | DD EXP | DE COS |
| DF SIN | E0 TAN | E1 ATN | E2 PEEK | E3 LEN |
| E4 STR$ | E5 VAL | E6 ASC | E7 CHR$ | E8 LEFT$ |
| E9 RIGHT$ | EA MID$ | | | |

$EA (MID$) is the last token; $EB–$FF are unused.

## 2. Variables and types

Naming rules:

- First character a letter; rest letters/digits; optional trailing `%`
  (integer) or `$` (string), which is part of the name (`A`, `A%`, `A$` are
  three different variables).
- Names may be long, but **only the first two characters plus the type suffix
  are significant**: `AB`, `ABC`, `ABLE` are the same variable. [emu]
- **A reserved word anywhere inside a name is a syntax error** — the
  tokenizer matches keywords greedily inside identifiers. `SCORE=5` →
  `?SYNTAX ERROR` because SCORE contains `OR` (it tokenizes as `SC OR E=5`).
  [emu] Common casualties (derived mechanically from the token table below):
  SCORE and COLOR (OR), TOTAL and TONE (TO), POINT (INT), SAND/BAND (AND),
  NOTE (NOT), ATOM (AT), GRADE (GR), FORMAT (FOR, AT, OR), ONE and FONT (ON),
  SENDER (END), LETTER (LET), LIFE (IF), COST (COS), FRED (FRE), CONTACT
  (CONT). To clear a name, scan it for every keyword in the token table as a
  substring — e.g. FLAG is legal (FLASH doesn't complete, and no AT/TO/OR/ON
  hides in it), but the only safe habit is short names (1–2 chars).
- The tokenizer special-cases the `AT`/`ATN`/`TO` ambiguity (e.g. `ATN(`
  parses as the function, `A TO Z` as `A TO Z`). [doc:manual]

Types:

| type | suffix | storage | range / limits |
|---|---|---|---|
| real | none | 5 bytes (excess-128 exponent + 4-byte mantissa) | ≈ ±1.7e38, ~9 significant digits |
| integer | `%` | 2 bytes in arrays/variables | −32767…32767; ±32768 is `?ILLEGAL QUANTITY` [emu] |
| string | `$` | 3-byte descriptor (len + pointer) | 0–255 chars; 256 is `?STRING TOO LONG` (code 176) [emu] |

**There is no integer arithmetic.** Every `%` value is converted to floating
point before any math and converted back (with range check) on store, so
integer variables are ~40% *slower* than reals [doc:RSE measurement]. Use `%`
only to halve array memory.

Assignment is `LET A=1` or just `A=1`. `CLEAR` wipes all variables, `NEW`
wipes program and variables.

### Arrays

- `DIM A(20)`, `DIM B%(5,5)`, `DIM N$(100)` — subscripts run 0…max, so
  `DIM A(20)` holds 21 elements.
- Undimensioned arrays auto-DIM to max subscript 10 on first use; index 11+
  then raises `?BAD SUBSCRIPT` (code 107). [emu]
- A second `DIM` of the same array raises `?REDIM'D ARRAY` (code 120) — guard
  re-runnable code with a flag, or `CLEAR` first.

### DEF FN

`DEF FN F(X) = X*X+1` — numeric single-argument functions only, deferred mode
only. Calling an undefined FN raises code 224. [rom]

## 3. Operators and precedence

Highest to lowest (order per calormen; the surprising rows verified [emu]):

1. `( )`
2. unary `+ - NOT`
3. `^`
4. `* /`
5. binary `+ -`
6. comparisons `= < > <= >= <>` (also accepted: `=<`, `=>`, `><`)
7. `AND`
8. `OR`

Two verified traps [emu]:

- `-2^2` is **4**, not −4 (unary minus binds tighter than `^`, unlike math
  convention and most other BASICs).
- `2^3^2` is **64** — `^` associates **left** (`(2^3)^2`), not right.
- `NOT` really is a tight unary operator here, unlike classic MS BASICs
  where it sits below the comparisons: `NOT 1 + 1` is 1 (= `(NOT 1)+1`)
  and `NOT 1 * 0` is 0 (= `(NOT 1)*0`). [emu]

Comparisons yield 1 (true) / 0 (false); `AND`/`OR`/`NOT` treat any nonzero as
true and return 1/0. Strings compare with the same operators
(character-by-character ASCII). `+` concatenates strings.

## 4. Flow control

| statement | semantics |
|---|---|
| `GOTO n` / `GOSUB n` / `RETURN` | target must be a literal line number (no computed GOTO — use ON) |
| `ON aexpr GOTO/GOSUB n1,n2,…` | value 1 picks n1, etc.; **0 or > list length falls through** to the next statement; negative or ≥256 is `?ILLEGAL QUANTITY` (both behaviors [emu]) |
| `POP` | discards one pending GOSUB return address without returning |
| `IF expr THEN …` | see below |
| `FOR V = a TO b [STEP s]` / `NEXT [V[,W]]` | see below |
| `END` | silent stop |
| `STOP` | stop with `BREAK IN line` message; `CONT` resumes |

### IF…THEN

- **No ELSE exists.** The entire rest of the line belongs to the THEN-branch:
  in `IF A=1 THEN B=2:C=3`, neither assignment runs when A≠1. [emu] This is
  the idiom for multi-statement conditionals; simulate ELSE with a second IF
  or a GOTO around the alternative.
- Forms: `IF A=1 THEN 100`, `IF A=1 THEN GOTO 100`, `IF A=1 GOTO 100` are
  equivalent; `THEN` followed by a statement runs it.
- `IF A THEN …` tests A≠0.

### FOR…NEXT

- **The body always executes at least once** — the limit is tested at `NEXT`,
  not at `FOR`. `FOR I=5 TO 1: PRINT I: NEXT` prints 5 once. [emu] Guard with
  an IF when the range can be empty.
- `STEP` may be negative or fractional; `STEP 0` loops forever.
- `NEXT` without a variable matches the innermost FOR and is faster;
  `NEXT J,I` closes two loops.
- Loop variable retains its overshot value after the loop ends.
- FOR frames live on the 6502 stack (18 bytes each); jumping out of a loop
  without finishing it leaks the frame. Re-`FOR`-ing the same variable reuses
  the slot, so the classic escape idiom is: set the loop variable to its
  limit, `NEXT`, then leave. Maximum nesting: **10 FOR loops — the 11th
  raises `?OUT OF MEMORY`** under ProDOS BASIC.SYSTEM [emu]; the constraint
  is the shared stack (see GOSUB).
- GOSUB nesting: the manual says ~25 levels; **24 measured** before
  `?OUT OF MEMORY` under ProDOS BASIC.SYSTEM (its hooks eat stack). [emu]
  Each GOSUB frame is 6 bytes of the same 256-byte 6502 stack used by FOR
  frames and expression evaluation — budget conservatively, and don't
  recurse: deep recursion that overflows the stack while ONERR is active can
  crash to the monitor instead of trapping. [emu]

## 5. Statements by area

### Text I/O

| statement | notes |
|---|---|
| `PRINT a;b,c` | `;` = no separation, `,` = tab to next 16-col field; trailing `;`/`,` suppresses the CR |
| `INPUT ["prompt";] var[,var…]` | prints `?` without a prompt string; commas/colons in typed input split fields (`?EXTRA IGNORED` / `??`); bad numeric input → `?REENTER`; under ONERR, code 254 |
| `GET C$` | one keystroke, no echo, no Return needed; control chars come through. **GETting into a numeric variable is a trap**: any non-digit keypress is a runtime `?SYNTAX ERROR` [emu] — GET a string, `VAL()` it |
| `HOME` | clear text window, cursor top-left |
| `HTAB n` / `VTAB n` | column 1–40 / row 1–24 (HTAB tracks 80-col when active) |
| `INVERSE` / `FLASH` / `NORMAL` | output modes (INVFLG at 50: 255 normal, 63 inverse, 127 flash) |
| `SPEED= n` | output delay, 0 slowest…255 full speed (default) |
| `TEXT` | text mode, full 24-row window |
| `PR# s` / `IN# s` | route output/input to slot s firmware; `PR# 0`/`IN# 0` restores; `PR# 3` activates 80-col firmware on a IIe/IIc |
| `TAB(n)` / `SPC(n)` | only inside PRINT; TAB( is absolute column, SPC( relative spaces |
| `POS(0)` | current cursor column (0-based) |

Text window: POKE 32 left edge, 33 width, 34 top, 35 bottom+1 (0-based);
`HOME` after changing. Cursor: PEEK(36) column, PEEK(37) row, both 0-based —
`VTAB 12:HTAB 10` leaves 37→11, 36→9. [emu]

INPUT that accepts commas and colons (they normally split fields): read a
raw line with the GETLN entry `CALL -657`, then harvest the $0200 buffer —
verified, returns the punctuation intact [emu]:

```basic
10 PRINT "TYPE:";: CALL -657
20 A$ = "": FOR X = 512 TO 767: IF PEEK(X) <> 141 THEN A$ = A$ + CHR$(PEEK(X) - 128): NEXT
30 REM the IF skipping the rest of the line (incl. NEXT) exits the loop at the CR
```

In 80-column mode, position the cursor horizontally with `POKE 1403,col`
(0-based) — HTAB alone misbehaves past column 40. [doc:beagle]

Text page 2 ($0800–$0BFF) is real, and the page-2 soft switch flips
*text* as well as graphics: `POKE -16299,0` displays it, `POKE -16300,0`
returns to page 1 [emu]. The catch: a default Applesoft program starts at
$0801 — *inside* text page 2; flip without preparing and you are looking
at your own tokenized program [emu]. To double-buffer text, relocate the
program clear of it first — `POKE 104,12: POKE 3072,0: NEW`, then LOAD
(TXTTAB→$0C01; same mechanism as the hi-res relocation below).
[doc:beagle-ttt]

Useful control characters in PRINT [doc:calormen]: CHR$(4) DOS/ProDOS command
prefix, CHR$(7) bell, CHR$(8) backspace, CHR$(13) return. With 80-col
firmware active also: CHR$(12) clear+home, CHR$(17)/CHR$(18) 40/80 columns,
CHR$(21) kill 80-col firmware, CHR$(27)/CHR$(24) mousetext on/off.

### Lo-res graphics (40×48, 16 colors)

| statement | notes |
|---|---|
| `GR` | lo-res mixed mode (40×40 + 4 text rows), clears to black, COLOR=0 |
| `COLOR= n` | 0 black, 1 magenta, 2 dark blue, 3 purple, 4 dark green, 5 grey, 6 medium blue, 7 light blue, 8 brown, 9 orange, 10 grey, 11 pink, 12 light green, 13 yellow, 14 aqua, 15 white |
| `PLOT x,y` | x 0–39, y 0–47 (0–39 visible in mixed mode) |
| `HLIN x1,x2 AT y` / `VLIN y1,y2 AT x` | horizontal / vertical line |
| `SCRN(x,y)` | color at x,y (function) |

Full-screen lo-res: `POKE -16302,0` after GR; back to mixed `POKE -16301,0`.

### Hi-res graphics (280×192, 6 colors)

| statement | notes |
|---|---|
| `HGR` | hi-res page 1 ($2000), mixed with 4 text rows, clears to black |
| `HGR2` | hi-res page 2 ($4000), full screen, clears to black |
| `HCOLOR= n` | 0 black1, 1 green, 2 purple, 3 white1, 4 black2, 5 orange, 6 blue, 7 white2 |
| `HPLOT x,y` | x 0–279, y 0–191 |
| `HPLOT x1,y1 TO x2,y2 [TO …]` | lines; `HPLOT TO x,y` continues from last point in the **last-used** color |
| `DRAW n [AT x,y]` / `XDRAW n [AT x,y]` | draw shape n from the shape table (XDRAW = XOR, draw twice to erase); set `ROT=` (0–63, 16 = 90°) and `SCALE=` (1–255) first |
| `SHLOAD` | loads a shape table from cassette — disk-era programs `BLOAD` instead and `POKE 232,lo: POKE 233,hi` the table address |

Hi-res helpers verified by ROM disassembly [rom]:

- `CALL -3100` ($F3E4): reveal hi-res **page 1** *without clearing it*
  (BITs the page-1/mixed switches, reads hires/graphics on). Caveat from the
  disassembly: the entry point lands just before a `STA $E6`, so it stomps
  HPAG with whatever is in A — `POKE 230,32` afterward before HPLOTting.
- `CALL -3086` ($F3F2): clear the current hi-res page to black.
- `CALL -3082` ($F3F6): clear it to the last-HPLOTted color.
- Current draw page is PEEK(230) (HPAG): 32 = page 1, 64 = page 2; POKE it to
  redirect HPLOT (e.g. for page-flip animation with `POKE -16299,0` /
  `POKE -16300,0` to display 2/1).
- **Off-screen rendering: `POKE 230,96`** points all hi-res drawing at
  $6000–$7FFF — a third, never-displayable "page" [doc:beagle82]. Verified:
  HPLOT lands at $6000 while pages 1/2 stay untouched [emu]. Build images
  there, then block-move to a visible page (§14). Protect the buffer from
  string growth with `HIMEM: 24576`.

NB color rules are NTSC-artifact based: even x = purple/blue pixels, odd x =
green/orange, white = adjacent pair. Vertical lines in color need x step 2.

Hi-res page 1 sits at $2000–$3FFF, directly above a default program at $0801:
a program plus variables larger than ~6K overwrites the picture (no error).
Either keep the program small, use HGR2/page 2, or relocate the program above
page 1 before loading it:
`POKE 103,1: POKE 104,64: POKE 16384,0: NEW` (TXTTAB→$4001), then LOAD/RUN.
[doc:widely-published idiom; remember $4000 must hold 0, like $0800]

### Data and misc

| statement | notes |
|---|---|
| `DATA v,v,…` / `READ var,…` / `RESTORE` | DATA is position-independent and read in line order from the program start; out of items → code 42. Strings in DATA need quotes only if they contain commas/colons/leading spaces. RESTORE rewinds to the first DATA (Applesoft has no `RESTORE n`) |
| `REM text` | comment to end of line (colons do NOT end a REM) |
| `WAIT addr,mask[,xor]` | spin until (PEEK(addr) XOR xor) AND mask ≠ 0 — un-interruptible; prefer a PEEK loop |
| `POKE a,v` / `PEEK(a)` | a may be negative (a−65536 convention: −16384 ≡ 49152) |
| `CALL a` | JSR to machine code at a (negative convention likewise: CALL −3288 = $F328 = 62248) |
| `USR(x)` | jumps via the JMP at $0A–$0C with x in the FAC ($9D); returns FAC |
| `& …` | jumps via the JMP at $3F5 — the hook for ML extensions |
| `TRACE` / `NOTRACE` | print `#line` as each statement runs |
| `HIMEM: a` / `LOMEM: a` | move the top of string space / bottom of variable space |
| `STORE A` / `RECALL A` / `LOAD` / `SAVE` | cassette-tape era; under DOS/ProDOS the same names are *disk commands* issued via CHR$(4) |
| `CONT` | resume after STOP/ctrl-C/END (not after program edits) — code 210 if impossible [rom] |

## 6. Functions

Numeric: `SGN INT ABS SQR LOG EXP COS SIN TAN ATN`. Notes:

- `INT` truncates toward −∞ (`INT(-2.5)` = −3); round with `INT(X+.5)`.
- `^` is computed via LOG/EXP: slow, and inexact for most operands —
  `3^2 - 9` is 3.7e−9, `10^4 - 10000` is 3.8e−6 [emu]. Use `X*X` instead of
  `X^2`, and round before comparing or PRINTing power results.
- Only natural LOG/EXP; log₁₀(x) = LOG(X)/LOG(10).
- `RND(n)`: n>0 → next pseudorandom 0 ≤ r < 1; n=0 → **repeat the last
  value** [emu]; n<0 → reseed deterministically from n. Seed at program start
  with the keyboard-wait counter: `X = RND(-PEEK(78)-256*PEEK(79))` — but
  under ProDOS, BASIC.SYSTEM stomps $4E/$4F (RNDL), so prompt for a keypress
  first or mix in another source. [doc:RSE]
- Die-roll idiom: `INT(RND(1)*N)` is 0…N−1 (add 1 for 1…N). There is no
  MOD operator in Applesoft (Integer BASIC's `MOD` doesn't exist here) —
  use `A - INT(A/B)*B`.
- `PDL(n)` paddle 0–3 → 0–255 (read two paddles with ≥ a few statements
  between reads — the timers interact). Buttons: `PEEK(-16287)`,
  `PEEK(-16286)`, `PEEK(-16285)` ≥ 128 = pressed (PB0/PB1 = Open/Closed
  Apple on IIe+).

String: `LEN(s$)`, `LEFT$(s$,n)`, `RIGHT$(s$,n)`, `MID$(s$,start[,len])`
(start is 1-based), `STR$(x)`, `VAL(s$)` (parses leading number, 0 if none),
`ASC(s$)` (first char; errors on empty string — guard with LEN),
`CHR$(n)`.

Substring edge semantics, measured [emu]: a count *larger* than the string
is fine (`LEFT$("X",2)` = "X", and they work on "" sources), and a MID$
start past the end returns "" — only a count/start of **0** raises
`?ILLEGAL QUANTITY`. So guard the zero cases (e.g. `LEFT$(A$,P-1)` when
P=1), not the overshoot.

System: `FRE(0)` free memory **and forces garbage collection** (see §9; a
result > 32767 comes back negative — add 65536), `PEEK`, `POS(0)`, `SCRN(`,
`USR(`.

## 7. Memory map and zero-page locations

Default layout under ProDOS BASIC.SYSTEM (HIMEM $9600 [emu], moves down 1K
per open file [doc:TechRef]); under DOS 3.3, HIMEM $9600 likewise on a 48K+
machine:

```
$0800            program text (TXTTAB→$0801)
  ↓ grows        simple variables (VARTAB), then arrays (ARYTAB→STREND)
  ↑ grows down   string data (FRETOP down from HIMEM)
HIMEM            DOS/ProDOS buffers above
$2000-$3FFF      hi-res page 1 (collides with big programs!)
$4000-$5FFF      hi-res page 2
$BE00-$BEFF      BASIC.SYSTEM global page (ProDOS)
```

Zero-page / low-memory addresses usable from BASIC (decimal, as PEEK/POKE
sees them):

| dec | hex | name | meaning |
|---|---|---|---|
| 32–35 | $20–$23 | WNDLFT/WNDWDTH/WNDTOP/WNDBTM | text window (see §5) |
| 36 / 37 | $24/$25 | CH / CV | cursor column / row, 0-based [emu] |
| 50 | $32 | INVFLG | 255 normal, 63 inverse, 127 flash |
| 78/79 | $4E/$4F | RND counter | keyboard-wait entropy (ProDOS stomps it) |
| 103/104 | $67/$68 | TXTTAB | program start, normally $0801 [emu] |
| 105/106 | $69/$6A | VARTAB | start of simple variables — first byte after the program (= PRGEND right after entry/LOAD [emu]) |
| 107/108 | $6B/$6C | ARYTAB | start of arrays |
| 109/110 | $6D/$6E | STREND | end of arrays / start of free space |
| 111/112 | $6F/$70 | FRETOP | bottom of string data |
| 115/116 | $73/$74 | HIMEM | top of BASIC memory [emu: $9600] |
| 117/118 | $75/$76 | CURLIN | current line number [rom] |
| 175/176 | $AF/$B0 | PRGEND | end of program |
| 184/185 | $B8/$B9 | TXTPTR | interpreter's read pointer (operand of CHRGOT's LDA) [rom] |
| 216 | $D8 | ERRFLG | ONERR active flag; `POKE 216,0` cancels ONERR [emu] |
| 218/219 | $DA/$DB | ERRLIN | line of last trapped error [emu] |
| 222 | $DE | ERRNUM | code of last trapped error [emu] |
| 224/225 | $E0/$E1 | — | X of last HPLOT (lo/hi) [emu] |
| 226 | $E2 | — | Y of last HPLOT [emu] |
| 228 | $E4 | — | HCOLOR bit pattern: 0,42,85,127,128,170,213,255 for HCOLOR=0–7 (127 spot-checked [emu], rest [doc:beagle]) |
| 230 | $E6 | HPAG | hi-res draw page ×$100: 32 or 64 |
| 231 | $E7 | — | SCALE value (0 means 256) [doc:beagle] |
| 232/233 | $E8/$E9 | SHAPEL | shape table address |
| 234 | $EA | — | XDRAW collision counter: 0 after XDRAWing onto all-black [doc:beagle] |
| 241 | $F1 | SPEEDZ | 256 − SPEED setting |
| 249 | $F9 | — | ROT value [doc:beagle] |

CHRGET lives at $B1–$C8 in zero page [rom]. Page 3: $3D0 DOS/BASIC warm
start, $3F2/$3F3 RESET vector, $3F5–$3F7 `&` JMP [emu — under BASIC.SYSTEM
1.5 it boots pointing at the global page, $BE03], $3F8–$3FA ctrl-Y JMP,
$3FE/$3FF IRQ. USR vector: JMP at $0A–$0C.

Soft switches / hardware from BASIC (read with PEEK unless noted):

| address | use |
|---|---|
| −16384 ($C000) | keyboard: ≥128 means a key waits; AND 127 for the char |
| −16368 ($C010) | POKE 0 to clear the keystrobe (also reset before polling) |
| −16336 ($C030) | speaker: one PEEK = one click; PEEK in a timed loop makes a tone |
| −16304/−16303 ($C050/51) | graphics / text |
| −16302/−16301 ($C052/53) | full screen / mixed |
| −16300/−16299 ($C054/55) | display page 1 / page 2 |
| −16298/−16297 ($C056/57) | lo-res / hi-res |
| −16287/−16286/−16285 ($C061–63) | buttons PB0/PB1/PB2 (≥128 = down) |

Which machine am I on: `PEEK(64435)` ($FBB3) — 56 = II, 234 = II+,
6 = IIe or later; if 6, `PEEK(64448)` ($FBC0) — 234 = IIe, 224 = enhanced
IIe, 0 = IIc. Measured 6 / 224 on the enhanced IIe [emu]. The 4/83 Beagle
chart's one-PEEK test (`PEEK(-637)`: 255 = IIe, 223 = II/II+, 234 =
Franklin Ace) is ROM-revision-fragile — an *enhanced* IIe returns 234,
which that table would call a Franklin [emu]; use the $FBB3/$FBC0 pair.

Slot probing: card ROM for slot n appears at $Cn00 — `PEEK(49152 + 256*n)`
(an empty slot reads floating garbage). The classic Disk II controller
signature is 162 at that byte [doc:beagle82], but firmware varies — a
non-stock controller shows other values (microM8's: 141 [emu]); robust
ProDOS-era detection checks the ID bytes $Cn01=32, $Cn03=0, $Cn05=3
for a block device instead.

Keyboard poll idiom (no INPUT/GET) — run-verified: pressing `A` yields
K=65 [emu]:

```basic
100 IF PEEK(-16384) < 128 THEN 100
110 K = PEEK(-16384) - 128 : POKE -16368,0
```

Monitor ROM helpers callable from BASIC [doc:calormen]: `CALL -868` clear to
end of line ($FC9C), `CALL -958` clear to end of window ($FC42), `CALL -922`
cursor down/line feed ($FC66), `CALL -756` wait for a key ($FD0C),
`CALL -1036` cursor right ($FBF4), `CALL -1008` cursor left ($FC10),
`CALL -998` cursor up ($FC1A), `CALL -678` wait for a Return keypress
($FD5A) [doc:beagle], `CALL -151` enter the monitor ($FF69).
(Negative CALL n = 65536+n.)

More from the 1982 chart [doc:beagle82]: `CALL -912` scroll the text window
up one line ($FC70), `CALL -1998` clear the full 48-row lo-res screen
($F832 — GR itself only clears the top 40), `CALL -1994` clear just the
top 40 lo-res rows ($F836), `CALL -2613` copy the hi-res pen position into
224–226 ($F5CB — i.e. where the next DRAW lands), `CALL -1321` print a
6502 register dump ($FAD7).

**1982-chart errata, verified on a IIe [emu]:** its HGR/HGR2 CALL addresses
are off by 4 — the true entries are `CALL -3102` (HGR, $F3E2) and
`CALL -3112` (HGR2, $F3D8). Its −3106 lands on HGR2's `LDA #$40`:
draw page→2, page 2 cleared, while page 1 stays displayed; −3116 starts
mid-instruction. And its `CALL -875` "clear entire text line" is a II/II+
monitor entry — on the IIe that address is mid-routine in the output path
and crashes to the monitor. Its keyboard column also lists a "PDL(3)
button" at $C064 — no fourth pushbutton exists: $C061–$C063 are PB0–PB2
and $C064 is paddle 0's analog *timer* (paddle 3's is $C067). Beagle
themselves cleaned house in the 4/83 edition: the bad HGR/HGR2 CALLs and
the $C064 row are gone from 4/83 onward, and the direct CALL −468 was
replaced with the LDY#0 shim (§14). On IIe-era machines stick to the
documented entries above (those are stable across ROMs).

## 8. Numbers in detail

5-byte Microsoft format: exponent byte (excess-128, 0 = value 0) + 4 mantissa
bytes (implicit leading 1, sign in mantissa high bit). ~9.6 significant
digits; PRINT shows up to 9, switching to scientific notation outside
0.01 ≤ |x| < 1e9. Integers up to ±2^31 are exact as reals — line numbers,
addresses, and money in cents are safe.

Comparison caution: accumulate floats and `IF X = 3` may miss;
compare with `IF ABS(X-3) < 1E-6`. `^` results are generally inexact
(`3^2 - 9` ≠ 0, via LOG/EXP — though powers of 2 happen to come out exact
[emu]); `X*X` is always exact for exact X.

The FAC (floating-point accumulator) is $9D–$A2; useful only to ML callers
(see §14).

## 9. Strings and garbage collection

String *data* lives in a heap growing down from HIMEM; variables hold 3-byte
descriptors. Every assignment/concatenation allocates a fresh copy on top of
the heap and abandons the old one; literals in program text are referenced
in place until modified.

When the heap meets the array space, Applesoft runs its garbage collector —
roughly O(n²) in live strings; with many strings (esp. arrays) **the machine
freezes for seconds to minutes**. [doc:RSE] Management:

- `X = FRE(0)` forces collection at a moment you control (between screens,
  during "PRESS ANY KEY"); cost is the same, but you choose when.
- Under ProDOS, `PRINT CHR$(4);"FRE"` invokes **BASIC.SYSTEM's much faster
  collector**. Plain `FRE(0)` always gets the slow ROM one (the ROM call is
  hardwired), but BASIC.SYSTEM watches free space at every statement (via
  always-on TRACE — the ~4% speed tax noted in Beneath Apple ProDOS) and
  preemptively runs its fast GC before Applesoft's would trigger, which is
  why string-heavy programs run *faster* under ProDOS. [doc:RSE #26157]
  The slow ROM collector can still fire under ProDOS: the preemptive check
  runs between statements, so a single statement that burns through the
  remaining free space (a big concatenation, many temporaries in one
  expression) trips Applesoft's own collector mid-statement — and an
  explicit `FRE(0)` always invokes it.
- Reduce garbage: fewer live string variables, reuse one scratch variable,
  avoid concatenation in hot loops (build with `MID$` reads instead of
  repeated `A$ = A$ + …` where possible).

## 10. Errors and ONERR

`ONERR GOTO n` installs a handler (deferred mode only; also disables ctrl-C,
which arrives as code 255). In the handler:

- `PEEK(222)` = error code, `PEEK(218) + 256*PEEK(219)` = offending line. [emu]
- `RESUME` re-executes the statement that failed (not the next one) —
  retry loops must fix the cause or they spin forever.
- `POKE 216,0` cancels trapping (otherwise a bug in the handler itself
  re-enters it endlessly). [emu]

Applesoft error codes [rom — offsets into the ROM message table; 254/255 doc]:

| code | error | code | error |
|---|---|---|---|
| 0 | NEXT WITHOUT FOR | 133 | DIVISION BY ZERO |
| 16 | SYNTAX | 149 | ILLEGAL DIRECT |
| 22 | RETURN WITHOUT GOSUB | 163 | TYPE MISMATCH |
| 42 | OUT OF DATA | 176 | STRING TOO LONG |
| 53 | ILLEGAL QUANTITY | 191 | FORMULA TOO COMPLEX |
| 69 | OVERFLOW | 210 | CAN'T CONTINUE |
| 77 | OUT OF MEMORY | 224 | UNDEF'D FUNCTION |
| 90 | UNDEF'D STATEMENT | 254 | bad response to INPUT |
| 107 | BAD SUBSCRIPT | 255 | ctrl-C interrupt |
| 120 | REDIM'D ARRAY | | |

DOS 3.3 / ProDOS errors arrive through the same mechanism with codes ≤ 21.
DOS 3.3 set [doc:calormen]: 1 LANGUAGE NOT AVAILABLE, 2 and 3 both RANGE
ERROR [doc:beagle82], 4 WRITE
PROTECTED, 5 END OF DATA, 6 FILE NOT FOUND [emu: a failed BLOAD under ProDOS
also yields 6, "PATH NOT FOUND"], 7 VOLUME MISMATCH, 8 I/O ERROR, 9 DISK
FULL, 10 FILE LOCKED, 11 INVALID OPTION, 12 NO BUFFERS AVAILABLE, 13 FILE
TYPE MISMATCH, 14 PROGRAM TOO LARGE, 15 NOT DIRECT COMMAND. BASIC.SYSTEM
extends the set: 17 DIRECTORY FULL, 18 FILE NOT OPEN, 19 DUPLICATE FILE
NAME, 20 FILE BUSY, 21 FILE(S) STILL OPEN. [doc:beagle] Meanings drift
between DOSes: 6 is FILE NOT FOUND under DOS 3.3 but PATH NOT FOUND under
ProDOS, and 11 is SYNTAX ERROR under DOS 3.3 but INVALID OPTION under
ProDOS. [doc:beagle]

### The ONERR stack bugs

1. **Dangling FOR/GOSUB frames.** An error inside a FOR loop or GOSUB leaves
   those frames on the stack; GOTO-ing out of the handler (instead of
   RESUME) accumulates them. Fix: `CALL -3288` in the handler — verified to
   be `LDX $DF : TXS` [rom], i.e. it restores the stack pointer saved at
   error time, flushing all pending FOR/GOSUB context. Consequence: after
   CALL −3288 you cannot RETURN to a GOSUB that was open when the error hit.
   (Heavier alternative: `CALL -10621` ($D683) resets the entire runtime
   stack — all FOR/GOSUB/ONERR state. [doc:calormen])
2. **The monitor-jump bug.** With TRACE on, or in some PRINT interactions,
   the ROM handler corrupts state and drops into the monitor after the 43rd
   error (87th for INPUT errors) when the handler exits with GOTO.
   [doc:manual] Using RESUME, or the CALL −3288 hygiene above, avoids it.
3. **No stack headroom.** If the stack is nearly full when the error fires
   (e.g. deep GOSUB recursion), error handling itself overflows and crashes
   to the monitor rather than trapping. [emu] Keep nesting shallow in code
   that relies on ONERR.

Canonical handler shape:

```basic
10 ONERR GOTO 1000
...
1000 E = PEEK(222): L = PEEK(218) + 256*PEEK(219)
1010 POKE 216,0 : CALL -3288
1020 IF E = 5 THEN 2000: REM end of data - normal path
1030 PRINT "ERROR ";E;" IN LINE ";L : END
```

## 11. DOS 3.3 and ProDOS from a program

Disk commands are issued by PRINTing CHR$(4) followed by the command text:

```basic
10 D$ = CHR$(4)
20 PRINT D$;"OPEN SCORES"
30 PRINT D$;"READ SCORES"
40 INPUT N$ : INPUT S
50 PRINT D$;"CLOSE"
```

- Under **DOS 3.3** the ctrl-D must follow a carriage return — i.e. begin the
  PRINT's output line (the old `CHR$(13)+CHR$(4)` trick exists because of
  this). Under **ProDOS**, BASIC.SYSTEM detects ctrl-D at the start of any
  *statement's* output (it watches execution via TRACE), so mid-line tricks
  are unnecessary — but keep the ctrl-D first in its PRINT. [doc:RSE #26157]
- While a file is OPEN for READ/WRITE, INPUT/PRINT are redirected to it;
  CLOSE (or an error) restores the screen. Always CLOSE — BASIC.SYSTEM
  lowers HIMEM 1K per open file. [doc:TechRef]
- In immediate mode just type commands (`CATALOG`, `SAVE X`); CHR$(4) is the
  in-program mechanism.

Create-or-replace a text file, ProDOS-safe [emu]:

```basic
100 PRINT D$;"OPEN ";F$: PRINT D$;"CLOSE ";F$: REM ENSURE IT EXISTS
110 PRINT D$;"DELETE ";F$: REM WRITES DON'T TRUNCATE - DROP OLD CONTENT
120 PRINT D$;"OPEN ";F$: PRINT D$;"WRITE ";F$
130 FOR I = 1 TO N: PRINT L$(I): NEXT
140 PRINT D$;"CLOSE ";F$
```

The DOS 3.3-era dance without the CLOSE (`OPEN: DELETE: OPEN: WRITE`)
fails under ProDOS with FILE BUSY, code 20 — BASIC.SYSTEM refuses to
DELETE an open file [emu]. The CLOSE-first form works on both DOSes.

Common commands: `CATALOG` (ProDOS also `CAT`), `RUN f`, `LOAD f`/`SAVE f`,
`BLOAD f[,Aaddr]` / `BSAVE f,Aaddr,Llen` / `BRUN f`, `OPEN/READ/WRITE/
APPEND/POSITION/CLOSE f`, `DELETE/RENAME/LOCK/UNLOCK`, `EXEC f` (run a text
file as typed input), `VERIFY`. ProDOS-only: `PREFIX path`, `CREATE`,
`FRE` (fast GC, §9), `CHAIN f` (run another program keeping variables —
DOS 3.3's own CHAIN works only from Integer BASIC; Applesoft chaining
under DOS 3.3 used the CHAIN binary utility on the System Master),
`STORE/RESTORE f` (save/load variables), `FLUSH`, `BYE`, `- f` (smart run).
DOS 3.3-only: `INIT`, `MON/NOMON`, `MAXFILES n`, `FP`/`INT`.

Record-oriented text files: `OPEN f,Llen` then `READ f,Rnum` /
`WRITE f,Rnum` for random access.

After a BLOAD, recover where it landed and how big it was [doc:beagle]:
ProDOS — start `PEEK(48825)+256*PEEK(48826)` ($BEB9), length
`PEEK(48840)+256*PEEK(48841)` ($BEC8); DOS 3.3 — start 43634/43635
($AA72), length 43616/43617 ($AA60).

### DOS 3.3 internals and patch POKEs [doc:beagle82]

Everything below assumes **unpatched DOS 3.3 on a 48K machine** (on 32K,
subtract 16384 from addresses over 40000 — the chart's own note). None of
it applies under ProDOS.

| dec | hex | meaning |
|---|---|---|
| 43624 / 43626 | $AA68/$AA6A | last-used drive / slot |
| 43607 / 43697 | $AA57/$AAB1 | MAXFILES current / default |
| 43698 | $AAB2 | the DOS command character (normally 4 = ctrl-D) |
| 43702 | $AAB6 | BASIC flag: 0 Integer, 64 Applesoft ROM, 128 Applesoft RAM |
| 44033 | $AC01 | catalog track number |
| 46064 | $B3F0 | sectors per track: 13 = a DOS 3.2 disk, 16 = DOS 3.3 |
| 42350 | $A56E | CATALOG routine — `CALL 42350` catalogs |

Catalog/DOS patch POKEs (each 234 = $EA = NOP over a JSR; re-boot undoes):
`POKE 42768,234: POKE 42769,234: POKE 42770,234` suppress all DOS error
messages; `POKE 44452,N+1: POKE 44605,N` N file names before the catalog
pauses [doc:beagle83];
`POKE 44505,234: POKE 44506,234` show deleted files in CATALOG;
`POKE 44578,234: POKE 44579,234: POKE 44580,234` no CR after each name;
`POKE 44596,234: POKE 44597,234: POKE 44598,234` no screen-full pause;
`POKE 44599,234: POKE 44600,234` pause at each name for a keypress;
`POKE 49107,234: POKE 49108,234: POKE 49109,234` skip language-card reload
on re-boot; `POKE 40514,52` / `POKE 40514,20` boot greeting may be
binary / text; `POKE 40193,PEEK(40193)-N: CALL 42964` move the DOS buffers
down N pages (frees HIMEM space) [doc:beagle83]; `POKE 1012,0` make RESET
boot the disk (`POKE 1012,56` restores DOS 3.3's normal $9DBF reset —
56 is that vector's EOR #$A5 checksum). The drive/slot bytes above are
POKEable too: `POKE 43624,d` / `POKE 43626,s` redirect the next disk I/O
[doc:beagle83]. `PRINT (PEEK(978)+35)/4;"K"` prints memory size — DOS 3.3
only ($3D2 points into DOS; under ProDOS it points at BASIC.SYSTEM and the
formula is meaningless).

Reading raw sectors from BASIC (RWTS) — DOS 3.3 only, run-verified [emu]:

```basic
10 REM READS TRACK TR, SECTOR SE INTO 38400-38655
20 POKE 768,32: POKE 769,227: POKE 770,3: POKE 771,76: POKE 772,217: POKE 773,3
30 POKE 47083,0: POKE 47088,0: POKE 47089,150: POKE 47090,0: POKE 47091,0: POKE 47092,1
40 POKE 47084,TR: POKE 47085,SE: CALL 768
```

Line 20 builds `JSR $03E3 : JMP $03D9` at $0300 — the page-3 vectors for
"locate IOB" and the RWTS entry. Line 30 fills DOS 3.3's standard IOB at
$B7E8+: 47083 volume (0 = any), 47088/47089 buffer lo/hi ($9600 = 38400),
47092 **command: 1 = read, 2 = write — a stray write trashes the disk**
(the chart: "if you ruin a disk, forget where you read this").
Verified by reading the System Master's VTOC (TR=17, SE=0):
`PEEK(38401…403)` = 17, 15, 3 — catalog track, catalog sector, DOS
release. [emu, doc:beagle83] Does not exist under ProDOS — use file
commands or the MLI there.

### Protection-era Applesoft tricks (DOS-agnostic)

Verified under ProDOS BASIC.SYSTEM [emu] except where tagged:

- `POKE 214,255` — the RUN flag: every subsequent command RUNs the program
  instead of executing (typing LIST ran it). The program itself must
  `POKE 214,0` to unlock the machine.
- `POKE 50,128` — output prints invisibly (listings show blank lines);
  `POKE 50,255` or NORMAL restores.
- `POKE 1014,165: POKE 1015,214` — point `&` at LIST ($D6A5): `&` then
  lists. `POKE 1014,18: POKE 1015,217` makes `&` RUN ($D912) [emu];
  `POKE 1014,110: POKE 1015,165` makes `&` CATALOG ($A56E) — **DOS 3.3
  only** (under ProDOS that address is inside BASIC.SYSTEM). Same pattern
  installs any handler (§14); under ProDOS restore with
  `POKE 1014,3: POKE 1015,190`.
- `POKE 1010,102: POKE 1011,213: POKE 1012,112` — RESET runs the program:
  $3F2/$3F3 → $D566, which is Applesoft's RUN (`JSR $D665` then
  `JMP $D7D2`/NEWSTT [rom]); 112 is the mandatory power-up checksum
  ($D5 EOR $A5).
- `POKE 2049,1` — corrupts the first line link so LIST repeats the first
  line forever; a listing-protection gag. [doc:beagle82]
- `POKE 33,33` — narrows the window so LIST output is compact and copy-
  editing over a listing doesn't inject padding spaces into quoted
  strings; `TEXT` restores. [doc:beagle82]
- `POKE 82,128` — cassette-era: a tape program auto-RUNs after LOAD.
  [doc:beagle82]

## 12. Tokenizer pitfalls recap

- Reserved word embedded in a variable name → `?SYNTAX ERROR` (§2). [emu]
- `?` is shorthand for PRINT at entry (tokenizes to the same byte). [emu]
- Keywords inside string literals and REM/DATA are safe (not tokenized).
- `XPLOT` has no token — it appears only in the manual's reserved-word
  list (and contains PLOT, so it's an illegal name regardless);
  `HPLOT TO` continues lines.
- A lone variable reference is not a statement: `X` alone is a syntax error
  (unlike some BASICs that print it).

## 13. Performance

What actually costs time, in rough order:

1. **Line lookup.** GOTO/GOSUB walk line links. Verified from the ROM's GOTO
   code [rom]: it compares only the **high bytes** of the target and current
   line numbers — search starts at the *current* line only if
   `INT(target/256) > INT(current/256)`; otherwise it starts at the
   **beginning of the program**. Practical rules: put hot subroutines at the
   lowest line numbers; a backward GOTO (loop) scans from the start every
   iteration, so keep hot loops early in the program and short.
2. **Variable lookup is a linear scan** of the variable table in creation
   order. Reference your hot variables once at program start (e.g.
   `I=0:X=0:Y=0:K=0`) so they're created early; every later use finds them
   fast. Fewer distinct variables = faster everything.
3. **Numeric literals are re-parsed every execution.** In a hot loop,
   `X = X + D1` (with `D1=1` set once) beats `X = X + 1`; this applies to
   PEEK/POKE addresses too: `KB = -16384` once, then `PEEK(KB)`.
4. **Integer variables are slower** (§2) — ~40% on arithmetic. [doc:RSE]
5. `NEXT` (bare) beats `NEXT I`. `IF…GOTO` ≈ `IF…THEN`.
6. Packing statements with `:` saves per-line overhead; deleting REMs from
   hot paths helps (they're still scanned); both matter only inside loops.
7. String concatenation in loops triggers GC pauses (§9) — restructure, or
   schedule `FRE(0)` / ProDOS `CHR$(4)"FRE"`.
8. `X*X` beats `X^2`; multiply beats divide (`X*.5` vs `X/2`).
9. When a loop is still too slow, that's the cue for a machine-language
   helper (§14), not more BASIC tricks. A 6502 routine is typically
   100–1000× faster than interpreted BASIC.

## 14. Machine-language interface

- **CALL addr** — JSR to your routine (RTS returns to BASIC). Pass data by
  POKEing agreed locations before the CALL (classic scratch: $0300–$03CF,
  free zero page $06–$09, $EB–$EF on a IIe — see the apple-assembly-programming
  skill's zero-page ownership tables before claiming more).
- **USR(x)** — JMP vector at $0A–$0C; x arrives in the FAC ($9D–$A2,
  exponent at $9D); whatever the routine leaves in the FAC is the function
  result. For integer exchange, ROM helpers: GETADR ($E752) FAC→16-bit in
  LINNUM ($50/$51), GIVAYF ($E2F2) A(hi)/Y(lo)→FAC. (Both entry points
  verified by disassembly. [rom])
- **`&`** — the ampersand statement JMPs through $3F5 with TXTPTR parked
  right after the `&`; your handler parses arguments with the ROM's CHRGET
  ($B1) / CHRGOT ($B7) and expression evaluator (FRMNUM $DD67 + GETADR, or
  CHKCOM $DEBE to eat commas; both verified by disassembly [rom]). This is
  the idiomatic way to add statements.
  Under BASIC.SYSTEM the vector boots pointing into the ProDOS global page
  [emu]; save and restore it if you hook it.
- **Block move from BASIC** — the monitor MOVE ($FE2C) copies A1→A2 to A4
  with pointers at 60/61 (source start), 62/63 (source end), 66/67 (dest).
  The classic published form `POKE`s the pointers then `CALL -468` — but
  **that failed in our tests** (under ProDOS BASIC.SYSTEM on a IIe): MOVE
  is Y-indexed (`LDA ($3C),Y : STA ($42),Y` [rom]) and assumes Y=0, while
  Applesoft's CALL arrives with Y depending on the address expression
  (Y=0 measured for `CALL 768`, Y=1 at $FE2C for `CALL -468`), shifting the
  whole copy. Beagle Bros evidently knew: their 4/83 chart replaces the
  direct call with "a Basic memory-move that does *not* use a direct
  CALL −468" — and its POKEs (160,0,76,44,254 at 768) are byte-for-byte
  the same `LDY #0 : JMP $FE2C` shim we derived from the failure
  [doc:beagle83]. Robust, verified form:

  ```basic
  10 POKE 768,160: POKE 769,0: POKE 770,76: POKE 771,44: POKE 772,254
  20 POKE 60,32: POKE 61,3: POKE 62,34: POKE 63,3: POKE 66,0: POKE 67,14
  30 CALL 768: REM COPIES $0320-$0322 TO $0E00 (VERIFIED [emu])
  ```

  (The 1982 chart additionally documents POKEing 64–65 as "new end" —
  MOVE never reads those locations; only 60/61, 62/63, 66/67 matter.)
- **Monitor commands from BASIC** (`CALL -144`, $FF70) — stuff a high-bit
  ASCII monitor command into the input buffer, then execute it [emu]:

  ```basic
  100 A$ = "300:51 52 53 54": L = LEN(A$)
  110 FOR X = 1 TO L: POKE 511+X, ASC(MID$(A$,X,1))+128: NEXT: POKE 512+L,141
  120 POKE 72,0: CALL -144
  ```

  Two requirements the published versions gloss over: terminate the buffer
  with a CR (the POKE …,141 — without it the last argument is dropped
  [emu]), and know that execution ends at the monitor prompt unless the
  command string itself ends with a `G` command that jumps back to BASIC
  (`3D0G` warm-starts DOS/ProDOS BASIC). Anything the monitor can do —
  moves, fills, compares — is one string away.
- **Mini-disassembler from BASIC**: `POKE 58,lo: POKE 59,hi: CALL -415`
  prints a 20-instruction monitor disassembly starting at hi·256+lo and
  returns to the prompt. [emu, doc:beagle83] It leaves 58/59 advanced past
  what it printed [emu], so calling it in a loop disassembles
  continuously. [doc:beagle-ttt]
- Protect ML from BASIC: lower `HIMEM:` (classic), park short routines at
  $0300, or under ProDOS request pages via GETBUFR ($BEF5). [doc:TechRef]
- Writing, assembling and verifying the 6502 side: use the
  apple-assembly-programming, merlin32, and 6502-codegen skills.

## 15. Sources

- Applesoft ROM (microM8-mounted IIe image): keyword table $D0D0, error
  message table $D260, GOTO $D93E, CHRGET image, $F328, hi-res entries
  $F3E4/F3F2/F3F6, FRMNUM $DD67, CHKCOM $DEBE, GIVAYF $E2F2, GETADR $E752 —
  dumped/disassembled 2026-06-11.
- microM8 emulator behavioral tests, ProDOS BASIC.SYSTEM 1.5, 2026-06-11.
- Applesoft II BASIC Programming Reference Manual (mirrors.apple2.org.za).
- Joshua Bell, *Applesoft BASIC Quick Reference* — calormen.com/jsbasic/reference.html.
- ProDOS 8 Technical Reference, appendix "The ProDOS BASIC System Program" — prodos8.com.
- *Beneath Apple ProDOS* (TRACE quote via RSE).
- Beagle Bros, *Tips, Tricks and Techniques* chart #1 (© 1983, the
  Double-Take pack-in) — [doc:beagle-ttt]. Seven type-in utilities; from
  it: CALL −415's pointer advance (continuous disassembly) and the
  text-page-2 double-buffer idiom (POKE 104,12) — both run-verified. The
  DATA-statement ML listings themselves were not transcribed.
- Beagle Bros, *Apple Commands* poster (10/84) — [doc:beagle-cmds].
  Alphabetical command set tagged Applesoft / Integer BASIC / DOS 3.3 /
  ProDOS, plus the control- and ESC-key tables. Supplied the line-editing
  workflow, the GET-numeric trap, and dialect boundaries (computed
  GOTO/GOSUB targets and MOD are Integer BASIC only — corroborating §4).
- Beagle Bros, *Peeks, Pokes and Pointers*, early edition (c. 1982, DOS 3.3
  and Integer BASIC era) — [doc:beagle82]. Supplied the off-screen hi-res
  page (POKE 230,96), the extra monitor CALLs, and BLOAD address/length
  locations. Three entries failed IIe verification: HGR/HGR2 CALLs off by
  4, and CALL -875 crashes (§7 errata).
- Beagle Bros, *Peeks, Pokes and Pointers*, 4/83 edition (© 1983; II, II+,
  IIe) — [doc:beagle83]. Independently corroborates the CALL −468 erratum:
  it replaces the direct call with the identical LDY#0/JMP$FE2C shim
  (§14). Supplied CALL −144 / −415, the `&`-vector examples, generalized
  catalog POKEs, and the PEEK(−637) machine test (itself ROM-fragile —
  see §7). Dropped the 1982 edition's bad HGR/HGR2 CALLs and $C064 row.
- Beagle Bros, *Peeks, Pokes and Pointers* poster (Bert Kersey, 1984) —
  [doc:beagle]. Cross-checked against this reference 2026-06-11: agrees on
  every overlapping table entry; supplied the HPLOT/HCOLOR/SCALE/ROT/
  collision locations, ProDOS error names 17–21, BLOAD-result peeks, and
  the CALL -657/-678 tricks. Its `CALL -468` memory move did NOT survive
  verification as printed — see §14 for why and the fixed form.
- retrocomputing.stackexchange.com #26157 (BASIC.SYSTEM TRACE/GC), and the
  measured integer-vs-float timing question.
