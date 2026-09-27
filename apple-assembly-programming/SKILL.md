---
name: apple-assembly-programming
description: "Use when writing Apple II family assembly from scratch or working with Apple II platform details: memory map, ROM monitor, ProDOS, Applesoft entry points, soft switches, text/lo-res/hi-res/double-hi-res graphics, keyboard, speaker I/O, IIgs hardware, program structure, zero-page conventions, or platform routines."
license: MIT
---

# Apple II Assembly Programming

How to *author* assembly for the Apple II family. This skill carries the
platform knowledge — memory map, ROM routines, soft switches, I/O — that the
sibling skills deliberately don't. Pair it with `merlin32` (to drive the
assembler), `6502-codegen` (to write and verify CPU-generic routines), and
`6502-optimization` (to tune what you've written).

Full platform reference: [references/apple2-platform-reference.md](references/apple2-platform-reference.md).

## Scope and targets

The Apple II line spans three CPUs. Know which one you're targeting before you
write a single opcode, because the instruction set and addressing modes differ:

- **6502** — II, II+, original IIe. Base instruction set only.
- **65C02** — Enhanced IIe, IIc. Adds `PHX/PLX`, `PHY/PLY`, `STZ`, `BRA`,
  `(zp)` indirect, `INC A`, and fixes the indirect-`JMP` page-boundary bug.
- **65816** — IIgs. 16-bit registers, 24-bit addressing, native vs. emulation
  mode. Boots in 6502-emulation mode; you opt into native mode explicitly.

When in doubt, target the 6502 for portability across the whole family.

## Memory map (the parts you need in working memory)

Full map, zero-page ownership tables, page-3 vectors, language card, and aux
memory: reference §2.

- `$0000–$00FF` — zero page. Fast/small addressing, but heavily used by the
  monitor, Applesoft, and DOS/ProDOS. Only `$06–$09` are free on every setup;
  carve out anything more deliberately (reference §2.2) and document it.
- `$0100–$01FF` — hardware stack.
- `$0200–$02FF` — input buffer (GETLN).
- `$0300–$03FF` — free-ish scratch; also holds vectors at the top.
- `$0400–$07FF` — text/lo-res page 1.
- `$2000–$3FFF` — hi-res page 1. `$4000–$5FFF` — hi-res page 2.
- `$C000–$CFFF` — soft switches and slot I/O.
- `$D000–$FFFF` — ROM (monitor, Applesoft). Bank-switched RAM underneath.

## Soft switches

Apple II hardware is controlled by reading or writing magic addresses in the
`$C0xx` range. A few you'll reach for constantly:

| Switch    | Address | Effect                          |
|-----------|---------|---------------------------------|
| TXTCLR    | `$C050` | Graphics mode                   |
| TXTSET    | `$C051` | Text mode                       |
| MIXCLR    | `$C052` | Full screen                     |
| MIXSET    | `$C053` | Mixed text/graphics             |
| LOWSCR    | `$C054` | Display page 1                  |
| HISCR     | `$C055` | Display page 2                  |
| LORES     | `$C056` | Lo-res graphics                 |
| HIRES     | `$C057` | Hi-res graphics                 |
| KBD       | `$C000` | Read keyboard (bit 7 = ready)   |
| KBDSTRB   | `$C010` | Clear keyboard strobe           |
| SPKR      | `$C030` | Toggle speaker (read it)        |

Complete tables — IIe/IIc aux-memory and 80-col switches, language card,
annunciators/DHR, IIgs extras, status reads: reference §3. Two rules always:
a read is a real access (so `LDA`/`BIT` toggle things), and never let an
indexed store's dummy read land on `$C0xx`.

## Common ROM entry points

Lean on the monitor ROM instead of reinventing it:

- `COUT` (`$FDED`) — output char in A (high-bit ASCII) to current device.
- `HOME` (`$FC58`) — clear text screen, cursor home.
- `RDKEY` (`$FD0C`) — wait for and read a keypress.
- `GETLN` (`$FD6A`) — read a line into `$0200`, X = length.
- `BELL1` (`$FBDD`) — beep the speaker. (`BELL` `$FF3A` prints ctrl-G instead.)
- `WAIT` (`$FCA8`) — delay = 2.5·A²+13.5·A+7 cycles (+6 for the JSR);
  A=0 acts like A=256. Destroys A.

Full table with register contracts, lo-res plotting, and the Applesoft
hi-res entries: reference §4. Don't assume registers survive `COUT`/`RDKEY` —
they vector through the `$36`/`$38` hooks, and DOS/ProDOS/80-col hooks differ.

## Program structure starter

A minimal Apple II program in Merlin32 syntax (assembles as-is:
`merlin32 -V . HELLO.S` → BRUNable binary `HELLO`): set the org, document
your zero-page claims, init the screen, do work, exit cleanly. A ProDOS SYS
program would exit via MLI QUIT (reference §6.5) instead of `RTS`.

```asm
* HELLO -- minimal Apple II skeleton.
* Zero page claimed: none (the $06-$09 free bytes are where yours go).

KBD      EQU   $C000        ; equates up top, hardware then ROM
KBDSTRB  EQU   $C010
HOME     EQU   $FC58
COUT     EQU   $FDED
RDKEY    EQU   $FD0C

         TYP   $06          ; ProDOS file type BIN
         DSK   HELLO        ; merlin32: write the object to ./HELLO
         ORG   $2000        ; fine unless you need hi-res page 1

MAIN     JSR   HOME         ; clear text screen, cursor home
         LDY   #0
PRINT    LDA   MSG,Y
         BEQ   GETKEY
         JSR   COUT         ; COUT wants high-bit ASCII
         INY
         BNE   PRINT
GETKEY   JSR   RDKEY        ; wait for a key
         RTS                ; back to the BASIC/monitor caller

MSG      ASC   "HELLO, APPLE II!" ; double quotes = high bit set
         DFB   $8D          ; carriage return
         DFB   $00          ; terminator
```

Conventions worth copying: equates before code; a zero-page manifest comment
even when empty; high-bit ASCII for anything COUT sees; `RTS` only if you
were called — a program that takes over RESET or quits to ProDOS exits
differently (reference §2.3, §6.5).

## What goes where

- Authoring questions (this skill): "how do I draw to hi-res?", "which ROM call
  reads the keyboard?", "what's the IIgs memory map?"
- Syntax/assembling questions → `merlin32`.
- CPU-generic routines, opcode semantics, "debug this routine" → `6502-codegen`.
- "make this loop faster / smaller" → `6502-optimization`.
- "audit this code without running it" → `6502-review`.
