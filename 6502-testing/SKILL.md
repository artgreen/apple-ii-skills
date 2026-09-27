---
name: 6502-testing
description: "Use when testing or debugging an Apple II assembly program by running the built binary, driving routines by symbol name, stubbing ROM or ProDOS MLI calls, loading a program into microM8, sending keyboard input, reading text screen bytes, installing to .dsk images with CiderPress2, or fuzzing whole-program behavior. Not for BASIC programs."
license: MIT
---

# 6502 / Apple II program testing

Verify an Apple II program by **running it**, at two tiers. Don't pick
one — they catch different failures, and using both is what makes
building a non-trivial program (a full editor, a game, a tool) tractable.

| Tier | Tool | Tests | Speed |
|---|---|---|---|
| **Unit** | py65 + `scripts/sim.py` | all logic, by symbol name | <1 s for hundreds of asserts |
| **Integration** | microM8 + `scripts/m8.py` | ROM, MLI, screen, keyboard, disk, feel | seconds per cycle |

Put **everything computational** in the unit tier (it's deterministic and
instant); use the emulator for what only a real machine has. The unit
suite is what lets you refactor and optimize without fear; the emulator
confirms the handful of things py65 can't model.

## Build first, with symbols

Assemble with `-V` so the symbol file exists — it is your test API:

```
merlin32 -V <macro-lib> src/prog.s      # -> PROG and PROG_Symbols.txt
```

Label every routine and state variable you want to drive or inspect.

## Tier 1 — unit-test the real binary in py65

Load the merlin32-built binary, then call its routines **by name**,
poking state in and asserting on memory out. This tests the bytes you
ship, not a re-creation. Full pattern and a worked test file:
**[references/sim-harness.md](references/sim-harness.md)**.

```python
import sim                                  # scripts/sim.py
p = sim.Program("build/PROG", "build/PROG_Symbols.txt", org=0x801)
p.stub_rom("BELL1")          # JSR ROM -> INC a counter / RTS (observable)
p.fake_mli()                 # ProDOS MLI at $BF00 logs calls, returns ok
p.poke16("GAPS", p.sym("TEXTBUF"))
p.call("DISPATCH", a=0xE9)   # seed A, run a routine to its RTS
assert p.peek("MODE") == 1
```

Run it with the repository environment configured in the README:

```
"$APPLE_II_SKILLS/.venv/bin/python" tests/run_tests.py
```

`stub_rom`/`fake_mli` let logic that calls ROM or the OS run in the
simulator, and make those calls assertable (beep counts, exact MLI call
sequences). Once routines are callable by name, **fuzz** them —
differential (vs a Python reference) and invariant (random commands,
structural checks) — see the reference's §6.

## Tier 2 — run it in microM8

This tier requires a microM8 build exposing the documented MCP extension.
Stock builds may not provide it. Configure `MICROM8_BIN`, `PRODOS_DISK`, and
`APPLE_II_SKILLS` as described in the repository README; the unit tier works
without an emulator or disk image. Launch the emulator in a separate terminal.

Launch, **wait for the `]` prompt (~7 s) before connecting** — connecting
mid-boot wedges the server — then load into RAM and `CALL` it. No disk
needed to iterate. Full control-plane reference, tool params, and disk
install: **[references/microm8-mcp.md](references/microm8-mcp.md)**.

```
"$MICROM8_BIN" -mcp -mcp-mode sse \
   -mcp-port 8080 -no-update -ssc-telnet-no-eof -drive1 "$PRODOS_DISK"
# after the ] prompt:
uv run --python 3.12 --with 'mcp>=1,<2' python "$APPLE_II_SKILLS/6502-testing/scripts/m8.py" load build/PROG 801 \
        call 2049 type 'iHELLO{e}' sleep 1 screen
```

Reach the control plane either through native `mcp__microm8__*` tools (if
the harness wired them up) or the `scripts/m8.py` driver CLI over SSE
(works regardless).

### The gotchas that will waste an hour if you don't know them

- **Read the screen with `get_text_screen_full` (`m8.py text`), not
  `get_text_screen`.** The legacy tool mis-orders the two memory banks in
  80-column mode (`ABCDEFGH`→`BADCFEHG`) and renders inverse/MouseText as
  plain ASCII; the graphical `screenshot` looks right but is pixels you
  can't assert on. `get_text_screen_full` reads main+aux directly, handles
  40/80 columns, decodes inverse and MouseText, and (with `attributes`)
  flags each cell `.`/`i`/`f`/`m`. See [references/microm8-mcp.md](references/microm8-mcp.md)
  §6–7 for the manual interleave fallback and the MouseText rules.
- **`type_text` is asynchronous** — sleep ≥1 s after typing before
  reading, or you race the keyboard queue. Submit with `\r` (not `\n`); a
  program polling `$C000` sees high-bit codes (`A`→`$C1`, RETURN→`$8D`,
  ESC→`$9B`).
- **`read_memory_range`'s length param is `count`, not `length`.**
- **Reload after every rebuild** — RAM holds the stale binary otherwise.

### Durable disk install (cp2, host-side)

In-emulator disk-write persistence to the host `.dsk` is
**build-dependent** — verify with `cp2 catalog` after exiting, don't
assume. For a reliable install: stop the emulator, back up the image,
then `cp2 add disk.dsk 'PROG#060801'` (NAPS suffix = type `06`/BIN, aux
`$0801`; `cd` to the file's dir first or the path becomes a subdirectory
on the volume). Never `cp2`-write a mounted image. Relaunch and `BRUN
PROG` to confirm the real load path. Details in the reference §7.

## Scripts

- `scripts/sim.py` — py65 `Program` harness: load by symbol, drive
  routines, stub ROM, fake the MLI, decode the text screen. Self-test:
  `"$APPLE_II_SKILLS/.venv/bin/python" "$APPLE_II_SKILLS/6502-testing/scripts/selftest.py"`.
- `scripts/m8.py` — microM8 driver CLI over MCP SSE: `load call type
  screen rows peek poke shot raw`. Run via `uv run --python 3.12 --with 'mcp>=1,<2' python`.

## Where this sits

Pairs with **merlin32** (assemble with `-V`), **6502-codegen** (owns the
py65 harness and the verified cycle/opcode reference; unit-checks single
routines from JSON), **apple-assembly-programming** (the platform facts —
screen layout, ROM entry points, MLI), and **applesoft-basic** (the same
emulator, oriented to testing BASIC rather than assembly).
