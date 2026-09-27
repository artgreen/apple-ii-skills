---
name: applesoft-basic
description: "Use when reading, writing, debugging, testing, or speed-tuning Applesoft BASIC programs for Apple II, including syntax, tokenization, variable-name rules, PEEK/POKE/CALL, text/lo-res/hi-res statements, ONERR, DOS 3.3/ProDOS commands through CHR$(4), string garbage collection, performance idioms, or machine-language hooks. Not for Integer BASIC."
license: MIT
---

# Applesoft BASIC Programming

How to write Applesoft BASIC that actually runs on an Apple II — the ROM
dialect's real rules, not generic-BASIC folklore. Numbers and behaviors here
come from a verified reference: token and error tables dumped from the
Applesoft ROM, quirks tested in the microM8 emulator, the rest cited to
primary documentation.

Full reference: [references/applesoft-reference.md](references/applesoft-reference.md).

## The traps that bite first

Every one of these is verified; details and workarounds in the reference (§ noted):

- **Variable names**: only the first 2 characters (+ type suffix) are
  significant, and a reserved word *anywhere* in a name is a syntax error —
  `SCORE` dies because it contains `OR`. Use short names. (§2)
- **No ELSE**, and a false `IF` skips the *whole rest of the line*:
  `IF A=1 THEN B=2:C=3` runs neither assignment when A≠1. (§4)
- **FOR bodies always run at least once** — the limit check happens at NEXT.
  `FOR I=5 TO 1` executes the body with I=5. (§4)
- **Integer variables (`X%`) are ~40% slower**, not faster — there is no
  integer arithmetic; everything converts to float. Use `%` only to shrink
  arrays. (§2)
- **`-2^2` is 4 and `2^3^2` is 64** — unary minus outranks `^`, and `^`
  associates left. Also `^` is inexact: `3^2-9` ≠ 0. (§3, §6)
- **String churn freezes the machine**: concatenation garbage accumulates
  until a multi-second garbage collection fires. Manage it with `FRE(0)` —
  or under ProDOS, `PRINT CHR$(4)"FRE"` (much faster collector). (§9)
- **A growing program silently overwrites hi-res page 1** ($2000–$3FFF).
  Use page 2, keep the program small, or relocate it. (§5)

## Skeleton with the standard idioms

```basic
10 REM *** SETUP: HOT VARS FIRST, CONSTANTS IN VARS (SPEED, REF 13)
20 D$ = CHR$(4): KB = -16384: KS = -16368: I = 0: K = 0
30 ONERR GOTO 9000
100 REM *** HOT SUBROUTINES LIVE AT LOW LINE NUMBERS (REF 13)
110 GOTO 1000
120 K = PEEK(KB): IF K < 128 THEN 120
130 POKE KS,0: K = K - 128: RETURN
1000 REM *** MAIN
1010 PRINT D$;"BLOAD TITLE,A$2000"
1020 GOSUB 120: REM WAIT FOR KEY
1030 END
9000 E = PEEK(222): L = PEEK(218) + 256*PEEK(219)
9010 POKE 216,0: CALL -3288: REM CANCEL TRAP + FLUSH STACK (REF 10)
9020 PRINT "ERROR ";E;" IN ";L: END
```

Why it looks like this: GOTO/GOSUB searches restart from the program start
unless the target's line÷256 exceeds the current line÷256 (verified in ROM),
so hot subroutines go first; literals are re-parsed on every execution, so
addresses live in variables; the ONERR handler captures the error code and
line first, then clears the trap flag (216) and repairs the stack
(`CALL -3288`) before branching anywhere.

## Quick lookups (all in the reference)

- §1 line/tokenization format, full **token table** ($80–$EA, ROM-dumped)
- §5 statements by area — text I/O, lo-res, hi-res, DATA, cassette leftovers
- §7 **memory map, zero-page table, soft switches** as PEEK/POKE numbers
- §10 **error codes** (ROM-dumped, incl. DOS/ProDOS codes ≤21) and the three
  ONERR bugs
- §11 disk I/O via `PRINT CHR$(4)…` — DOS 3.3 vs ProDOS differences
- §13 performance idioms, ranked by payoff
- §14 CALL/USR/ampersand machine-language interface

## Testing programs (microM8)

Integration tests use a microM8 build with the documented MCP extension
(`applesoft_write`, `type_text`, `get_text_screen_full`, `read_memory_range`, …).
This extension may not exist in stock builds. Set `MICROM8_BIN`, `PRODOS_DISK`,
and `APPLE_II_SKILLS` using the repository README. Launch in a separate terminal:

```sh
"$MICROM8_BIN" -mcp -mcp-mode sse -mcp-port 8080 -no-update \
  -ssc-telnet-no-eof -drive1 "$PRODOS_DISK"
```

- **Wait for ProDOS to reach the `]` prompt** (~7 s after the port opens)
  before connecting — connecting mid-boot wedges the MCP server.
- If the session's MCP client won't connect, use the driver CLI:
  `uv run --python 3.12 --with 'mcp>=1,<2' python "$APPLE_II_SKILLS/6502-testing/scripts/m8.py" state`.
  Use its `text`, `type`, `load`, `peek`, and `raw` commands as needed.
- `type_text` needs `\r` (the driver maps `{r}`) to submit; typing is
  asynchronous — **sleep ≥1 s after typing before reading memory or the
  screen**, or you'll race the keyboard queue.
- Prefer `type_text` over `applesoft_write` when ROM-tokenizer behavior
  matters (applesoft_write uses microM8's own tokenizer).
- The stray `.` at screen row 0 col 1 is microM8's disk-LED overlay.
- Run, then `get_text_screen_full` to check output; `applesoft_read` detokenizes
  the program in memory. **In-emulator disk write persistence is
  build-dependent** — different tested builds have behaved differently.
  After exiting, check the host image with `cp2 catalog`. For durable installs
  prefer CiderPress2 on the host (emulator stopped, image backed up):
  `cp2 import disk.dsk bas PROG.bas` tokenizes Applesoft source
  (byte-identical to microM8's tokenizer), `cp2 add disk.dsk 'NAME#TTAAAA'`
  adds a binary with ProDOS type/aux via NAPS suffix (e.g. `VI#060801` =
  BIN at $0801; cd to the file's dir first or the parent dir becomes a
  subdirectory on the volume), `cp2 export … text NAME` pulls files out.
  Never cp2-write an image a running emulator has mounted.
- When exact screen content matters, byte-verify with `read_memory_range`
  at $0400+ instead of trusting `get_text_screen`: the dump renders
  inverse characters as their normal glyphs, and the disk-LED overlay
  transiently writes bytes (e.g. $FF) straight into text page 1 near the
  top-left — both look like phantom corruption.
- For DOS 3.3-specific behavior, provide your own System Master image
  (set `DOS33_DISK` to its path) and swap it in with the
  `insert_disk` tool (`{"drive":0,"filename":…}`) and `reboot`.

## What goes where

- This skill: BASIC language, interpreter behavior, BASIC-visible addresses.
- Platform deep-dive (soft-switch semantics, ROM entry contracts, aux
  memory): `apple-assembly-programming`.
- Writing the fast 6502 routine your BASIC program CALLs: `6502-codegen`
  (+ `merlin32` for assembler syntax, `6502-optimization` to tune it).
- Integer BASIC: not covered — different language, different tokenizer.
