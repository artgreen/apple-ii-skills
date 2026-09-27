# Apple II Platform Reference

Deep reference for authoring assembly on the Apple II family. The SKILL.md
covers working-memory essentials; this file is the lookup table.

Scope: **platform** facts only — addresses, firmware contracts, hardware
behavior. CPU facts (opcodes, cycle counts, addressing-mode rules) live in
`6502-codegen`'s reference; cite that skill, don't recall. Assembler syntax
lives in `merlin32`.

Sourcing: entry points, soft switches, and calling conventions below were
cross-checked against Apple Assembly Line and standard Apple references;
these external source publications are not distributed with this collection. The
address-calculation routines and tables were verified by running them in
`6502-codegen`'s simulator. Section 8 lists the canonical books.

## 1. Hardware variants and CPUs

| Model | CPU | RAM | Notable additions |
|---|---|---|---|
| II | 6502 | 4–48K | Integer BASIC ROM, no autostart |
| II+ | 6502 | 16–48K | Applesoft ROM, Autostart monitor |
| IIe | 6502 | 64–128K | Aux memory, 80-col, self-test, internal `$C100–$CFFF` firmware |
| IIe enhanced | 65C02 | 64–128K | 65C02, MouseText, fixed monitor |
| IIc | 65C02 | 128K | Built-in 80-col/aux/serial/mouse/disk; IOU gating (`IOUDIS`) |
| IIgs | 65816 | 256K–8MB | SHR graphics, toolbox, banks `$E0/$E1`, 2.8 MHz |

Identifying the machine at runtime:

- `$FBB3` ROM ID byte: `$38` = II, `$EA` = II+ (Autostart), `$06` = IIe and
  everything after. (Corpus: AAL Mar 1983.)
- For IIe vs IIc vs enhanced, check `$FBC0` next (`$EA` IIe, `$E0` enhanced
  IIe, `$00` IIc) — full decision tree in Apple II Miscellaneous Tech Note #7.
- IIgs: `SEC` / `JSR $FE1F` / `BCC its_a_gs` — carry clear only on a IIgs
  (returns version info in A/X/Y).

CPU selection rule: target plain 6502 unless the request names a IIe-enhanced/
IIc/IIgs machine. `6502-codegen` hard-rules which instructions exist where.

## 2. Memory map

### 2.1 Main RAM/ROM layout

| Range | What | Notes |
|---|---|---|
| `$0000–$00FF` | Zero page | Contended — see 2.2 |
| `$0100–$01FF` | Hardware stack | Shared with everything |
| `$0200–$02FF` | GETLN input buffer | Reusable scratch *between* line inputs |
| `$0300–$03CF` | User scratch | Classic home for small resident helpers |
| `$03D0–$03FF` | DOS/ProDOS + monitor vectors | See 2.3 |
| `$0400–$07FF` | Text/lo-res page 1 | Contains screen holes — see 2.4 |
| `$0800–$0BFF` | Text/lo-res page 2 | Applesoft programs start at `$0801` |
| `$0C00–$1FFF` | Free RAM | |
| `$2000–$3FFF` | Hi-res page 1 | |
| `$4000–$5FFF` | Hi-res page 2 | |
| `$6000–$95FF` | Free RAM | Best load region for big programs |
| `$9600–$BFFF` | DOS 3.3 / ProDOS+BASIC.SYSTEM | HIMEM = `$9600` under both |
| `$BF00–$BFFF` | ProDOS global page | Persists across /RAM etc. — see 6.5 |
| `$C000–$C0FF` | Soft switches + slot device regs | Section 3 |
| `$C100–$C7FF` | Slot ROM `$Cs00` / IIe internal firmware | `INTCXROM` selects |
| `$C800–$CFFF` | Shared slot expansion ROM | Claimed per-slot; `$CFFF` releases |
| `$D000–$FFFF` | ROM: Applesoft `$D000–$F7FF`, monitor `$F800–$FFFF` | Language-card RAM underneath |

Language card (and the same region in IIe/IIc aux memory): 16K of RAM under
the ROM space, with **two 4K banks at `$D000–$DFFF`** and a single 8K
`$E000–$FFFF`. Switches at `$C080–$C08F`, section 3.4.

### 2.2 Zero page — who owns what

**Monitor block (`$20–$49`)** — live whenever monitor/firmware I/O runs:

| Addr | Name | Use |
|---|---|---|
| `$20–$23` | WNDLFT/WNDWDTH/WNDTOP/WNDBTM | Text window edges |
| `$24/$25` | CH/CV | Cursor column/row |
| `$26/$27` | GBASL/GBASH | Graphics line base (also Applesoft hi-res) |
| `$28/$29` | BASL/BASH | Text line base |
| `$2C/$2D` | H2/V2 | HLINE right end / VLINE bottom end |
| `$30` | COLOR | Lo-res color × `$11` |
| `$32` | INVFLG | `$FF` normal, `$3F` inverse |
| `$33` | PROMPT | GETLN prompt character |
| `$36/$37` | CSWL/CSWH | Output hook → COUT jumps here |
| `$38/$39` | KSWL/KSWH | Input hook → RDKEY jumps here |
| `$3A/$3B` | PCL/PCH | Saved PC (BRK, monitor commands) |
| `$3C–$43` | A1L…A4H | Monitor pointer args (MOVE, etc.) |
| `$45–$49` | ACC/XREG/YREG/STATUS/SPNT | Register save area |
| `$4E/$4F` | RNDL/RNDH | Churned by KEYIN/RDKEY while waiting — free entropy, unsafe storage |

**Hazards (documented, will bite):**
- The ROM IRQ path saves A at **`$45`** before vectoring — if interrupts are
  enabled, treat `$45` as volatile at all times.
- Monitor **and** DOS 3.3 both use **`$48`** (status save) — a known conflict
  for interrupt handlers (corpus: AAL Jul 1982). Re-zero `$48` before `RTI`
  if you've been in the monitor's path.
- The **IIe monitor also uses `$1F`** (seen in CLREOL at `$FC9C`) — `$1F` is
  not free on a IIe even though older II+ maps imply it (corpus: AAL Mar 1983).

**Applesoft landmarks** — live whenever Applesoft (or a program loaded from
it) is in play:

| Addr | Name | Use |
|---|---|---|
| `$50/$51` | LINNUM | 16-bit line/value scratch |
| `$67/$68` | TXTTAB | Program start (`$0801` default) |
| `$69/$6A` | VARTAB | Simple variables (end of program) |
| `$6B/$6C` | ARYTAB | Arrays |
| `$6D/$6E` | STREND | End of variable space |
| `$6F/$70` | FRETOP | String space top (grows down) |
| `$73/$74` | HIMEM | Memory ceiling |
| `$75/$76` | CURLIN | Current line number |
| `$9D–$A2` | FAC | Float accumulator |
| `$A5–$AA` | ARG | Second float accumulator |
| `$B1–$C8` | **CHRGET routine** | Code in zero page; TXTPTR = `$B8/$B9` |
| `$D8` | ONERR flag | `POKE 216,0` clears |
| `$E0–$E2` | X0L/X0H/Y0 | Hi-res cursor (HPLOT position) |
| `$E6` | HPAG | Hi-res page high byte (`$20`/`$40`) |
| `$E7` | SCALE | Shape scale |
| `$E8/$E9` | SHAPTR | Shape table pointer (POKE 232/233) |

**What is actually free:** Apple's published maps leave exactly **`$06–$09`**
unclaimed by the monitor, Applesoft, DOS 3.3, and ProDOS. Everything else is
borrowed, not owned. To claim more:

1. Pick bytes from an owner whose feature you provably don't use (e.g.
   Applesoft FAC/ARG in a program that never returns to BASIC) — and document
   the claim in your zero-page block header.
2. Or save/restore around your routine (stack the bytes you need).
3. On IIe/IIc/IIgs, `ALTZP` gives a whole alternate zero page + stack
   (section 3.3) — but firmware I/O must run on the *main* one.

This is the platform face of `6502-codegen` hard rule "document your
zero-page contract": on an Apple II the contract names which owner you're
displacing.

### 2.3 Page-3 vectors (`$03D0–$03FF`)

| Addr | Vector | Notes |
|---|---|---|
| `$03D0` | DOS/BASIC.SYSTEM warmstart `JMP` | Re-enter BASIC keeping program |
| `$03D9` | DOS 3.3 RWTS entry | `JSR $03D9`, IOB ptr in A(hi)/Y(lo) |
| `$03E3` | DOS 3.3 "locate IOB" | Returns A(hi)/Y(lo) → IOB |
| `$03F0/$F1` | BRK handler address | Autostart/IIe monitors vector here |
| `$03F2/$F3` | RESET handler address | Autostart reset target |
| `$03F4` | Powerup byte | Must equal `$03F3 EOR #$A5` or reset reboots |
| `$03F5–$F7` | Applesoft `&` `JMP` | Ampersand hook |
| `$03F8–$FA` | Monitor Ctrl-Y `JMP` | User monitor command |
| `$03FB–$FD` | NMI `JMP` | |
| `$03FE/$FF` | IRQ handler address | Hardware IRQ (after ROM saves A→`$45`) |

To take over RESET: store handler address at `$3F2/$3F3`, then
`LDA $3F3 / EOR #$A5 / STA $3F4`.

### 2.4 Text-page screen holes

The text page leaves 8 bytes unused at the end of each 128-byte triplet;
firmware assigns them to **peripheral cards** (one byte per slot per hole,
base+slot): `$0478–$047F`, `$04F8–$04FF`, `$0578–$057F`, `$05F8–$05FF`,
`$0678–$067F`, `$06F8–$06FF`, `$0778–$077F`, `$07F8–$07FF`. Don't use them
as free RAM — the 80-col firmware and slot cards do.

### 2.5 Aux memory (IIe/IIc) — banking model

64K auxiliary RAM mirrors the main map. Three independent gates:

- **`RAMRD`** (`$C002` off / `$C003` on, write) — reads of `$0200–$BFFF`
  come from aux.
- **`RAMWRT`** (`$C004` off / `$C005` on, write) — writes of `$0200–$BFFF`
  go to aux.
- **`ALTZP`** (`$C008` off / `$C009` on, write) — zero page, stack, **and
  the aux language-card region** switch together (corpus: AAL Dec 1984 —
  save the stack pointer first; you're swapping stacks).

Display-page carve-out: when **`80STORE`** (`$C001`) is on, `PAGE2`
(`$C054/$C055`) stops selecting the displayed page and instead banks
`$0400–$07FF` main/aux (and `$2000–$3FFF` too when `HIRES` is on). That's how
80-column text and double hi-res interleave their aux halves.

Firmware movers (IIe/IIc, `$C300` firmware present):

- **`AUXMOVE` `$C311`** — copy main↔aux. A1 (`$3C/$3D`)=source start,
  A2 (`$3E/$3F`)=source end, A4 (`$42/$43`)=dest; carry set = main→aux,
  clear = aux→main. It moves data via RAMRD/RAMWRT, which 80STORE
  *overrides* for the display windows — turn 80STORE off first or those
  ranges silently won't transfer (Apple IIe TN #3).
- **`XFER` `$C314`** — jump across banks. Target address in `$03ED/$03EE`;
  carry set = execute in aux; overflow set = use aux zero page/stack.
  Save your stack pointer before crossing.

### 2.6 IIgs banks (survey)

Bank `$00`/`$01`: fast RAM (the 8-bit world lives in `$00`). Banks
`$E0`/`$E1`: 1 MHz "slow side" holding real display memory and I/O —
softswitches and legacy video are mirrored there. Shadowing (`$C035`) copies
writes from bank `$00/$01` display pages to `$E0/$E1`. ROM at `$FC–$FF`
(ROM 3: `$F0–$FF`). Super hi-res lives in bank `$E1` (section 5.6).

## 3. Soft switches — complete table

Conventions: **R** = read, **W** = write, **R/W** = any access triggers.
Status switches read state in **bit 7**. Two hard rules:

- A *read* of a switch address is a real bus access — `LDA`/`BIT` toggles
  things. Never let an indexed store's dummy read land on `$C0xx`
  (`6502-codegen` Section 2, "fully-formed target"; same trap as the
  `BIT`-skip gotcha in `6502-optimization` D4).
- Prefer `LDA`/`BIT` (or `STA` where listed W) — never read-modify-write ops
  on `$C0xx`.

### 3.1 Display modes (R/W — any access)

| Off | On | Switch |
|---|---|---|
| `$C050` | `$C051` | TEXT (off = graphics) |
| `$C052` | `$C053` | MIXED (4 text lines under graphics) |
| `$C054` | `$C055` | PAGE2 (display page 1/2 — or aux bank when 80STORE) |
| `$C056` | `$C057` | HIRES (hi-res vs lo-res for the graphics area) |

### 3.2 Annunciators and DHR gate (R/W)

| Off | On | Switch |
|---|---|---|
| `$C058` | `$C059` | AN0 |
| `$C05A` | `$C05B` | AN1 |
| `$C05C` | `$C05D` | AN2 |
| `$C05E` | `$C05F` | AN3 — on IIe rev B+/IIc, `$C05E` = **DHIRES on** |

IOU gating (IIe and IIc): write `$C07E` = IOUDIS on / `$C07F` = IOUDIS off;
read bit 7 of `$C07E` = IOUDIS status, of `$C07F` = **DHIRES status**. With
IOUDIS on, `$C058–$C05F` become IIc mouse/VBL interrupt controls instead of
annunciators — check the IIc Tech Ref when targeting it.

### 3.3 IIe/IIc memory & video switches (W to set, R `$C01x` for status)

| Off (W) | On (W) | Status (R, bit 7) | Switch |
|---|---|---|---|
| `$C000` | `$C001` | `$C018` | 80STORE (PAGE2 banks display memory) |
| `$C002` | `$C003` | `$C013` | RAMRD (aux reads `$0200–$BFFF`) |
| `$C004` | `$C005` | `$C014` | RAMWRT (aux writes `$0200–$BFFF`) |
| `$C006` | `$C007` | `$C015` | INTCXROM (internal vs slot `$C100–$CFFF`) |
| `$C008` | `$C009` | `$C016` | ALTZP (aux zp + stack + aux LC) |
| `$C00A` | `$C00B` | `$C017` | SLOTC3ROM (slot 3 vs internal `$C300`) |
| `$C00C` | `$C00D` | `$C01F` | 80COL (80-column display) |
| `$C00E` | `$C00F` | `$C01E` | ALTCHARSET (MouseText/inverse set) |

More status reads (R, bit 7): `$C010` AKD (any key down — reading also
clears the keyboard strobe), `$C011` BSRBANK2, `$C012` BSRREADRAM,
`$C019` VBL (IIe: **0 during VBL**, 1 while the beam draws — the signal is
VBL-bar; IIgs: inverted, 1 during VBL; IIc: VBL is interrupt-based and
`$C019` resets the interrupt instead), `$C01A` TEXT, `$C01B` MIXED,
`$C01C` PAGE2, `$C01D` HIRES.

### 3.4 Language card (R — read the switch, twice for write-enable)

`$C080–$C087` select **bank 2**, `$C088–$C08F` the same pattern for
**bank 1** (the two banks differ only at `$D000–$DFFF`):

| Addr (bank2 / bank1) | Read from | Write to RAM? |
|---|---|---|
| `$C080` / `$C088` | RAM | no |
| `$C081` / `$C089` | ROM | yes — needs 2 reads |
| `$C082` / `$C08A` | ROM | no |
| `$C083` / `$C08B` | RAM | yes — needs 2 reads |

`$C084–$C087`/`$C08C–$C08F` mirror the four above. Write-enable requires
**two consecutive reads** of an odd switch (`LDA $C083 / LDA $C083`): an odd
*read* sets the PRE-WRITE flip-flop, a second odd read with PRE-WRITE set
enables writing. A *write* to an odd switch doesn't count (it resets
PRE-WRITE), and any even access write-protects again (Sather, *Understanding
the Apple II*). Status: `$C011` (bank 2 selected), `$C012` (reading RAM).

### 3.5 Input/output addresses (not toggles)

| Addr | R/W | What |
|---|---|---|
| `$C000` | R | Keyboard: bit 7 = key waiting, bits 6-0 = char |
| `$C010` | R/W | Clear keyboard strobe (IIe: read = AKD status too) |
| `$C020` | R | Cassette out toggle (historical) |
| `$C030` | R | Speaker toggle — **read it, don't write** |
| `$C060` | R | Cassette in (bit 7) |
| `$C061/$C062` | R | Button 0 / 1 (bit 7) = Open/Closed Apple keys |
| `$C063` | R | Button 2 (bit 7; the Shift key on shift-key-modded machines) |
| `$C064–$C067` | R | Paddle 0–3 timer (bit 7) |
| `$C070` | R/W | Paddle trigger (start the timers) |

### 3.6 Slot space control

| Addr | What |
|---|---|
| `$C080+s*$10` | Slot *s* device registers (16 bytes each) |
| `$Cs00–$CsFF` | Slot *s* 256-byte ROM |
| `$C800–$CFFE` | 2K expansion ROM, claimed by the last slot accessed |
| `$CFFF` | R — release expansion ROM (every card must do this first) |

### 3.7 IIgs extras (survey)

| Addr | What |
|---|---|
| `$C029` | NEWVIDEO — write `$81` for super hi-res (bit 7 = SHR, bit 6 = linear, bit 5 = B/W) |
| `$C034` | Border color (low nibble); also RTC control |
| `$C035` | SHADOW — set a bit to *inhibit* copying to `$E0/$E1`: b0 text, b1 hires1, b2 hires2, b3 SHR, b4 aux-hires, b6 I/O |
| `$C036` | SPEED/CYAREG — bit 7: 2.8 MHz (set) / 1 MHz |
| `$C068` | STATEREG — b7 ALTZP, b6 PAGE2, b5 RAMRD, b4 RAMWRT, b3 RDROM, b2 LCBNK2, b1 ROMBANK, b0 INTCXROM |

## 4. ROM entry points

All addresses are the Autostart/IIe monitor and Applesoft ROMs. General
contract notes: **register preservation is not guaranteed** across COUT/RDKEY
because they vector through `$36`/`$38` and DOS/ProDOS/80-col hooks differ —
save what you need. Characters use high-bit ASCII (`"A"` = `$C1`).

### 4.1 Character output

| Addr | Name | Contract |
|---|---|---|
| `$FDED` | COUT | Print A via CSW hook (the normal path) |
| `$FDF0` | COUT1 | Print A to the 40-col screen directly, bypassing hooks |
| `$FD8E` | CROUT | Print a CR |
| `$FDDA` | PRBYTE | Print A as two hex digits (destroys A) |
| `$FDE3` | PRHEX | Print low nibble of A as one hex digit |
| `$F941` | PRNTAX | Print A then X as four hex digits |

### 4.2 Keyboard input

| Addr | Name | Contract |
|---|---|---|
| `$FD0C` | RDKEY | Blink cursor, wait for key via KSW hook → A |
| `$FD1B` | KEYIN | Poll `$C000` directly (no hook) → A; clears strobe; churns RNDL/RNDH (`$4E/$4F`) while waiting |
| `$FD35` | RDCHAR | RDKEY + interprets ESC cursor sequences |
| `$FD6A` | GETLN | Read line w/ prompt from `$33` → buffer `$0200`, X = length |
| `$FD67` | GETLNZ | GETLN after printing a CR first |
| `$FD6F` | GETLN1 | GETLN without printing a prompt |

### 4.3 Text screen control

| Addr | Name | Contract |
|---|---|---|
| `$FC58` | HOME | Clear window, cursor to top-left |
| `$FC22` | VTAB | Move to row in CV (`$25`) |
| `$FB5B` | TABV | A = row → CV, then VTAB |
| `$FC42` | CLREOP | Clear to end of window |
| `$FC9C` | CLREOL | Clear to end of line (IIe: uses `$1F`) |
| `$FB39` | SETTXT | Text mode, full window |
| `$FB40` | SETGR | Lo-res mixed mode, clear top |
| `$FBC1` | BASCALC | A = row → BASL/BASH (`$28/$29`) |

### 4.4 Lo-res graphics

| Addr | Name | Contract |
|---|---|---|
| `$F800` | PLOT | Plot block: A = row (0–47), Y = col (0–39), color `$30` |
| `$F819` | HLINE | A = row, Y = left col, `$2C` = right col |
| `$F828` | VLINE | A = top row, Y = col, `$2D` = bottom row |
| `$F832` | CLRSCR | Clear all 48 lo-res rows |
| `$F836` | CLRTOP | Clear top 40 rows (mixed mode) |
| `$F847` | GBASCALC | A = row pair (0–23) → GBASL/H (`$26/$27`) |
| `$F864` | SETCOL | A = color → `$30` |
| `$F85F` | NEXTCOL | COLOR += 3 |
| `$F871` | SCRN | A = row, Y = col → A = color at that block |

### 4.5 Applesoft hi-res (need Applesoft zp context sane)

| Addr | Name | Contract |
|---|---|---|
| `$F3E2` | HGR | Hi-res page 1, mixed, clear |
| `$F3D8` | HGR2 | Hi-res page 2, full screen, clear |
| `$F411` | HPOSN | Position: X-coord in (Y=hi, X=lo), Y-coord in A |
| `$F457` | HPLOT | Plot at (Y,X),(A) with current hi-res color |
| `$F53A` | HLIN internal | Line from last position (used by HPLOT TO) |

These trash Applesoft scratch (`$26/$27`, `$E0–$E2`, etc.) and assume `$E6`
(HPAG) is set. From pure assembly, prefer your own plot core (section 5.4).

### 4.6 Utility / system

| Addr | Name | Contract |
|---|---|---|
| `$FCA8` | WAIT | Delay = 2.5·A² + 13.5·A + 7 cycles in-routine (+6 for the `JSR`; the classic ½(5A²+27A+26) figure includes it). A=0 behaves like A=256 minus 10 cycles. Destroys A |
| `$FE2C` | MOVE | Copy (A1)..(A2) → (A4); **Y must be 0**; monitor `<`-move |
| `$FB1E` | PREAD | X = paddle # → Y = 0–255 (let timer settle between reads) |
| `$FF4A` | SAVE | A,X,Y,P,S → `$45–$49` |
| `$FF3F` | RESTORE | `$45–$49` → registers |
| `$FBDD` | BELL1 | Beep the speaker directly (~1 kHz, 0.1 s) |
| `$FF3A` | BELL | Output a ctrl-G through COUT |
| `$FF65` | MON | Enter monitor with bell |
| `$FF69` | MONZ | Enter monitor quietly (`CALL -151`) |
| `$FBB3` | — | ROM ID byte (section 1) |
| `$FA62` | RESET | Autostart reset handler |

## 5. Graphics

### 5.1 Text screen (40-col)

`$0400` (page 1) / `$0800` (page 2, rarely used). 24 rows × 40 cols, but rows
are **not** contiguous: rows are interleaved in thirds.

    base(row) = $0400 + (row mod 8)*$80 + (row div 8)*$28

| Row | Base | Row | Base | Row | Base |
|---|---|---|---|---|---|
| 0 | `$0400` | 8 | `$0428` | 16 | `$0450` |
| 1 | `$0480` | 9 | `$04A8` | 17 | `$04D0` |
| 2 | `$0500` | 10 | `$0528` | 18 | `$0550` |
| 3 | `$0580` | 11 | `$05A8` | 19 | `$05D0` |
| 4 | `$0600` | 12 | `$0628` | 20 | `$0650` |
| 5 | `$0680` | 13 | `$06A8` | 21 | `$06D0` |
| 6 | `$0700` | 14 | `$0728` | 22 | `$0750` |
| 7 | `$0780` | 15 | `$07A8` | 23 | `$07D0` |

(Table verified against the formula in the `6502-codegen` simulator.)

Character encoding: `$00–$3F` inverse, `$40–$7F` flash (or MouseText with
ALTCHARSET on a IIe), `$80–$FF` normal — i.e. normal text = ASCII with the
high bit set. To write a char without COUT: compute base, `STA (BASL),Y`
with Y = column.

80-col: turn on 80STORE + 80COL; even columns live in **aux** memory, odd in
main, same row bases. Use PAGE2 on/off (`$C055/$C054`) to reach the aux half
while 80STORE is on. Or just print through COUT with the 80-col firmware on
(`PR#3` equivalent: `JSR $C300`).

### 5.2 Lo-res

Same memory as text. Each byte = two stacked pixels: **low nibble = top**,
high nibble = bottom. 40×48 in 16 colors:

| # | Color | # | Color | # | Color | # | Color |
|---|---|---|---|---|---|---|---|
| 0 | black | 4 | dark green | 8 | brown | 12 | green |
| 1 | magenta | 5 | grey 1 | 9 | orange | 13 | yellow |
| 2 | dark blue | 6 | medium blue | 10 | grey 2 | 14 | aqua |
| 3 | purple | 7 | light blue | 11 | pink | 15 | white |

Monitor helpers in 4.4 handle plotting; `COLOR = n*$11` fills both nibbles.

### 5.3 Hi-res layout

280×192, pages at `$2000` and `$4000`, 40 bytes per line, **bit 0 is the
leftmost pixel** of each byte (LSB-first), bit 7 selects the color phase for
the whole byte. Lines are interleaved:

    base(line) = $2000 + (line mod 8)*$400
                       + ((line div 8) mod 8)*$80
                       + (line div 64)*$28

Anchors: line 0 → `$2000`, line 1 → `$2400`, line 8 → `$2080`,
line 64 → `$2028`, line 191 → `$3FD0`.

### 5.4 Hi-res line-base routine (verified in the codegen simulator)

```asm
GBASL    EQU   $26          ; monitor's graphics base pair — or move
GBASH    EQU   $27          ;   to your own zp if monitor I/O interleaves

* HBASE: A = line (0-191) -> GBASL/GBASH = line base on hi-res page 1.
* Preserves A. Trashes X,Y. For page 2, change the ORA #$20 to ORA #$40.
HBASE    PHA                ; save the line number
         AND   #$07
         ASL
         ASL
         ORA   #$20         ; high byte = $20 + (line mod 8)*4
         STA   GBASH
         PLA
         PHA
         LSR
         LSR
         LSR                ; A = line/8: bits 2-0 = $80-row, 4-3 = third
         TAX
         AND   #$07
         LSR                ; A = $100s to add, C = odd $80 row
         TAY                ; (transfers don't touch carry)
         LDA   #$00
         ROR                ; A = C * $80
         STA   GBASL
         TYA
         CLC
         ADC   GBASH
         STA   GBASH        ; high byte += the $100s
         TXA
         LSR
         LSR
         LSR                ; A = screen third (0-2)
         TAY
         BEQ   HBDONE
HBLOOP   LDA   GBASL
         CLC
         ADC   #$28         ; each third starts $28 further in
         STA   GBASL
         DEY
         BNE   HBLOOP
HBDONE   PLA                ; restore the line number
         RTS
```

To plot pixel (X 0–279, line): byte = X div 7 (`STA (GBASL),Y` with Y =
byte), bit = X mod 7 → `ORA` a mask `1<<bit`. Division by 7 is the expensive
part — use a 280-entry div/mod table pair (`6502-optimization` A1) for
anything hot.

### 5.5 Hi-res color (the weirdness)

- A byte's 7 pixels render in **two colors max**, picked by bit 7:
  bit7=0 → violet/green, bit7=1 → blue/orange.
- Which of the pair a lone bit shows depends on **even/odd screen position**
  (NTSC phase). Adjacent on-bits merge to white; isolated off-bits between
  on-bits show fringe colors.
- Monochrome thinking: treat it as 280×192 B/W and it behaves; color
  thinking: treat it as 140×192 with 2-bit pixels per phase pair.
- Crossing a byte boundary mid-shape with mixed bit-7 values causes the
  classic color clash — keep sprites byte-aligned (or pre-shift 7 copies,
  `6502-optimization` A1/A3).

### 5.6 Double hi-res and IIgs super hi-res (survey)

**DHR** (IIe rev-B motherboard w/ jumpered 64K aux card, IIc): 560×192 mono
/ 140×192 in 16 lo-res colors. Enable: graphics+HIRES on (`$C050`/`$C057`),
80COL on (`$C00D`), AN3 off = DHR on (`$C05E`), 80STORE on — then PAGE2
banks `$2000–$3FFF` main/aux. Pixels interleave **aux byte, then main
byte**, 7 bits each; 4 adjacent bits = one color pixel. Two gotchas from
the tech note: **Ctrl-Reset turns AN3 back on** (re-hit `$C05E` after any
reset), and check `$C07F` bit 7 for current DHR state (3.2).

**SHR** (IIgs): lives in bank `$E1`: `$2000–$9CFF` pixels (320 mode: 160
bytes/line, 2 px/byte high nibble first; 640 mode: 4 px/byte),
`$9D00–$9DC7` per-line scan-control bytes (320/640 mode and palette select,
per scanline), `$9DC8–$9DFF` reserved, `$9E00–$9FFF` sixteen 16-entry
palettes — each entry a little-endian `$0RGB` word (4 bits per gun).
Enable via NEWVIDEO `$C029` (write `$81`). Usually driven via QuickDraw II —
see section 7.

## 6. I/O

### 6.1 Keyboard

```asm
KEYWAIT  LDA   $C000        ; bit 7 set when a key is waiting
         BPL   KEYWAIT
         STA   KEYCODE      ; high-bit ASCII
         BIT   $C010        ; clear the strobe (read or write)
```

Open-Apple/Closed-Apple read as buttons 0/1 (`$C061/$C062` bit 7) — note
they're the same lines as joystick buttons. IIe any-key-down: `$C010` bit 7.

### 6.2 Speaker

`$C030` toggles the cone; **read it** (`LDA`/`BIT`), don't write — and never
let an indexed addressing mode near it (dummy-read double-click). Square
wave: toggle, delay, repeat — pitch = half-period in cycles. The monitor's
`WAIT` (`$FCA8`) burns ≈ (26+27A+5A²)/2 cycles for quick-and-dirty delays;
for real tone generation count cycles with `6502-codegen`'s tables.

```asm
* Click + crude tone: Y half-periods of pitch A (delay loop units)
TONE     BIT   $C030        ; toggle speaker
         TAX
T1       DEX                ; 5-cycle/iteration delay (DEX+BNE)
         BNE   T1
         DEY
         BNE   TONE
         RTS
```

### 6.3 Paddles / joystick

Trigger `$C070` (any access) starts all four one-shot timers; bit 7 of
`$C064–$C067` stays set for a time ∝ resistance. `PREAD` (`$FB1E`, X=paddle)
returns Y=0–255. Reading two paddles back-to-back skews the second — let the
timers settle (~3 ms) or re-trigger between reads. Buttons: `$C061–$C063`.

### 6.4 Slots and expansion ROM

A card's firmware is at `$Cs00`; its device registers at `$C080+s*$10`; its
screen-hole bytes at hole-base+s (2.4). The shared 2K `$C800–$CFFE` belongs
to whichever card was addressed last — read `$CFFF` to release it before
claiming. Boot follows `$Cs00` signature bytes; disk boot = slot 6 ROM
(`PR#6` ≡ `JSR $C600`).

### 6.5 ProDOS MLI

One call gate, parameter block follows the JSR inline:

```asm
MLI      EQU   $BF00

         JSR   MLI
         DFB   $C8          ; the call number (OPEN)
         DA    OPARMS       ; parameter block address
         BCS   ERROR        ; carry set: A = MLI error code

OPARMS   DFB   3            ; parameter count for OPEN
         DA    PATHNAME     ; ptr: len-prefixed path
         DA    IOBUF        ; 1K buffer, page-aligned
         DFB   0            ; -> ref num returned here
```

Call numbers (housekeeping `$C0–$C7`, files `$C8–$D3`, system):

| # | Call | # | Call | # | Call |
|---|---|---|---|---|---|
| `$C0` | CREATE | `$C8` | OPEN | `$D0` | SET_EOF |
| `$C1` | DESTROY | `$C9` | NEWLINE | `$D1` | GET_EOF |
| `$C2` | RENAME | `$CA` | READ | `$D2` | SET_BUF |
| `$C3` | SET_FILE_INFO | `$CB` | WRITE | `$D3` | GET_BUF |
| `$C4` | GET_FILE_INFO | `$CC` | CLOSE | `$80` | READ_BLOCK |
| `$C5` | ONLINE | `$CD` | FLUSH | `$81` | WRITE_BLOCK |
| `$C6` | SET_PREFIX | `$CE` | SET_MARK | `$82` | GET_TIME |
| `$C7` | GET_PREFIX | `$CF` | GET_MARK | `$65` | QUIT |

(`$40/$41` ALLOC/DEALLOC_INTERRUPT round out the set.) Global page
essentials: `$BF30` DEVNUM (last device), `$BF58–$BF6F` BITMAP (mark every
page your program occupies, one bit per page of the lower 48K), `$BF90/$BF91`
DATE (`MMMDDDDD`,`YYYYYYYM`), `$BF92/$BF93` TIME, `$BF98` MACHID. A system
program exits with the `$65` QUIT call, params `DFB 4,0 / DA 0 / DFB 0 / DA 0`.

### 6.6 DOS 3.3 (brief)

Warmstart `JMP $03D0`. Direct disk access via RWTS: `JSR $03E3` → A(hi)/Y(lo)
point at the IOB; fill in track/sector/buffer/command; `JSR $03D9`. Details
and the IOB layout: *Beneath Apple DOS*.

### 6.7 Interrupts on this platform

- Hardware IRQ: ROM saves A at `$45`, decides BRK vs IRQ, then jumps via
  `($03FE)`. Consequences: `$45` is volatile under interrupts, your handler
  gets A *already trashed* (original A is at `$45`), and BRK handling costs
  extra cycles before your code runs.
- BRK lands at `($03F0)` (Autostart/IIe) with PC saved at `$3A/$3B`.
- DOS 3.3 + monitor both touch `$48` — repair STATUS expectations before
  `RTI` if anything monitor-ish ran (corpus: AAL Jul 1982).
- The language card complicates everything: if your handler can run while
  RAM is banked in, it must live in *both* banks or re-bank ROM first
  (classic crash source).
- VBL: IIe can poll `$C019`; the II/II+ has no VBL status at all. The
  classic workaround is the **"vapor lock"** (floating-bus read): seed
  marker bytes into display memory, then poll any *unconnected* `$C0xx`
  address — the read returns whatever byte the video scanner last fetched,
  so spotting your marker locates the beam (Bob Bishop's technique; Sather
  has the bus-level story). Trap from the field: the AppleMouse II card
  firmware uses exactly this on a II+, **clearing `$2000–$3FFF` during
  init** to find VBL — keep code and data out of hi-res page 1 while
  initializing a mouse card there (undocumented; 6502.org forum).

## 7. 65816 / IIgs specifics (survey)

The 8-bit skills (`6502-codegen` etc.) cover the 65816 **in 8-bit emulation
mode only**. Native-mode IIgs work:

- Boot state: 6502-emulation mode, 1 MHz. `CLC / XCE` enters native;
  `SEP`/`REP` size A (`m` bit) and X/Y (`x` bit) — keep the assembler's
  MX state in sync (see `merlin32` on `MX`/`LONGA`/`LONGX`).
- Set SPEED (`$C036` bit 7) for 2.8 MHz; I/O and bank `$E0/$E1` accesses
  stay slow.
- Direct page and stack are relocatable in native mode (`TCD`, 16-bit S) —
  "zero page" becomes wherever D points.
- Toolbox: push result space, push params, `LDX #func*256+toolnum`,
  `JSL $E10000`; error in A + carry on return. Tool sets: Tool Locator,
  Memory Manager, QuickDraw II, Event Manager, Sound — *Apple IIgs Toolbox
  Reference* vols 1–3.
- GS/OS: `JSL $E100A8` followed by `DA callnum` + `ADRL parmblock`
  (class-1 calls); carry/A error convention like the MLI.
- Memory: allocate via the Memory Manager (handles, purge levels), don't
  assume fixed banks; only `$E0/$E1` and the shadowed windows are special.
- Interrupts: many more sources (scanline, timer, ADB, serial); manage via
  the Misc Tools / firmware vectors, not raw `$FFFE`.

When a request is genuinely native-mode 16-bit, this skill's role is the
platform map above; for instruction semantics defer to *Programming the
65816* (Eyes & Lichty) rather than guessing.

## 8. Sources and further reading

External sources (not bundled or required for installing the skills):

- [Apple Assembly Line archive](https://alfter.us/computers/apple-ii/publications/apple-assembly-line/)
  — Bob Sander-Cederlof, 1980–86. Worked disassemblies, RWTS/DOS internals,
  IIe auxiliary-memory techniques, and monitor patches.
- [6502.org Source Code Library](https://6502.org/source/) — arithmetic,
  floating point, and monitor examples. Follow the authors' terms for any reuse.

Canonical paper references (the facts above follow these):

- *Apple II Reference Manual* ("Red Book") — II/II+ hardware, monitor listing.
- *Apple IIe / IIc Technical Reference* — aux memory, soft switches, firmware
  contracts.
- *Apple IIgs Hardware Reference* + *Firmware Reference* + *Toolbox Reference*
  vols 1–3.
- *ProDOS 8 Technical Reference* — MLI calls, global page, interrupt protocol.
- *Beneath Apple DOS* / *Beneath Apple ProDOS* — disk formats, RWTS, MLI
  internals.
- *Understanding the Apple II / IIe* (Jim Sather) — bus-level truth: video
  timing, vapor lock, soft-switch electrical behavior.
- *Programming the 65816* (Eyes & Lichty) — the 65816 itself.
- Apple II Technical Notes (Misc #2/#7 machine ID, IIe #3 DHR, etc.).

Useful online mirrors (used to verify this file, 2026-06): Jon Relay's Apple
II Info Archives (kreativekorp.com — the complete `$C0xx` and MLI tables),
the Apple II Tech Notes mirrors (prodos8.com, mirrors.apple2.org.za),
6502disassembly.com (commented ROM listings, incl. the corrected WAIT
timing), and ciderpress2.com format notes (SHR).

Verification status of this file: ROM entry addresses, soft-switch addresses,
MLI numbers, and global-page locations were grep-confirmed against the AAL
corpus EQ tables and articles where present (most are), then re-checked
against the online references above (machine ID table, IOU/DHR switches,
language-card pre-write rule, XFER/AUXMOVE carry conventions, RWTS Y/A
convention, QUIT parameter shape, WAIT cycle derivation, SHR layout); the
text-row table and HBASE routine were executed against their formulas in
the `6502-codegen` simulator. When something here disagrees with observed
hardware, trust the hardware, fix the file.
