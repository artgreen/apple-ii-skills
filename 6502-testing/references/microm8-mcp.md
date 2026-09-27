# microM8 integration testing — control plane reference

How to drive the microM8 Apple II emulator over its MCP control plane to
run a program on a (virtual) real machine. Table of contents:

1. Launching and connecting
2. Control paths: native MCP tools vs the driver CLI
3. The MCP tools you actually use (with exact params)
4. The fast iteration loop (no disk)
5. Keyboard input and its quirks
6. Reading the screen correctly (40- and 80-column)
7. MouseText and the alternate character set
8. Installing on a disk image with CiderPress2 (cp2)
9. Local configuration

---

## 1. Launching and connecting

```
"$MICROM8_BIN" -mcp -mcp-mode sse -mcp-port 8080 -no-update \
          -ssc-telnet-no-eof -drive1 "$PRODOS_DISK"
```

- The MCP server is **SSE at `http://localhost:8080/mcp/sse`**; health at
  `http://localhost:8080/mcp/health` (returns `{"status":"healthy",...}`).
- **Wait for ProDOS to reach the `]` prompt — ~7 s after the port opens —
  before connecting. Connecting mid-boot wedges the MCP server.** Poll the
  health endpoint, then `state` and confirm you see `]`, before doing
  anything else.
- Start it in the background; you can stop and restart it freely. A fresh
  launch is the reliable way to recover a wedged server.

## 2. Control paths: native MCP tools vs the driver CLI

Two ways to talk to the same control plane — use whichever is wired up:

- **Native MCP tools** (`mcp__microm8__*`) if the agent harness has the
  server connected. Call them directly (`write_memory_range`,
  `type_text`, `read_memory_range`, `emulator_state`, `screenshot`, …).
- **The driver CLI** `scripts/m8.py` over SSE, which works regardless of
  whether the harness mounted the MCP server. Run it through uv:

  ```
  uv run --python 3.12 --with 'mcp>=1,<2' python scripts/m8.py load build/PROG 801 call 2049 \
                                          sleep 1 screen
  ```

  Commands chain left to right: `state text screen rows load call type
  peek poke shot sleep reboot raw`. See the script's docstring for the
  full list. `raw <tool> <json>` reaches any tool the CLI doesn't wrap.

## 3. The MCP tools you actually use (with exact params)

| Tool | Params | Use |
|---|---|---|
| `emulator_state` | `{}` | CPU regs, mode, mounted disks, text screen |
| `get_text_screen_full` | `{"attributes":bool}` | **correct** text screen (40/80-col, inverse, MouseText) — see §6 |
| `write_memory_range` | `{"address":N,"values":[..]}` | load a binary; chunk ≤1024 bytes |
| `read_memory_range` | `{"address":N,"count":N}` | dump memory; **param is `count`, not `length`** |
| `read_ram_range` | `{"region":"aux.all","offset":N,"count":N}` | read a specific bank (e.g. aux text page) |
| `type_text` | `{"text":"..","delay":ms}` | feed the keyboard; `delay` optional |
| `screenshot` | `{"path":"x.jpg"}` | JPEG to host disk (for a human to look at) |
| `reboot` | `{}` | cold reboot |

`read_memory_range` returns lines like `0400: A0 A0 C8 ... |..H..|`; parse
the hex, stop at the `|` ASCII gutter.

## 4. The fast iteration loop (no disk)

Don't reinstall to disk every rebuild. Load the binary straight into RAM
at its ORG and `CALL` it from BASIC:

1. `write_memory_range` the binary to its ORG (e.g. `$801`).
2. `type_text` `CALL <decimal ORG>` + RETURN (`$801` → `CALL 2049`).
3. Drive it, read the screen, assert.
4. Rebuild, repeat. Seconds per cycle.

`CALL` enters with a JSR, so the program returns to BASIC with `RTS`.
Reload after every `merlin32` build; the binary in RAM is stale otherwise.

## 5. Keyboard input and its quirks

- **`type_text` is asynchronous** — it queues into the emulated keyboard
  hardware. **Sleep ≥1 s after typing before reading memory or the
  screen**, or you race the queue and read a half-typed state. The CLI's
  `{sN}` marker (sleep N/10 s) lets you pace a single paste.
- **Submit lines with `\r` (carriage return), not `\n`.** The CLI maps
  `{r}`→`\r`, `{e}`→ESC (`\x1b`), `{t}`→TAB.
- A program polling `$C000` directly sees the **high-bit-set** code: send
  `A` and it reads `$C1`; `{r}` → `$8D`; `{e}` → `$9B`. This is real
  keyboard-hardware behavior, so it exercises your input path faithfully.
- `delay` (ms between keystrokes) matters when you're testing whether the
  program keeps up with fast input — a slow per-key handler drops
  characters at low delay. Vary it to probe that.

## 6. Reading the screen correctly (40- and 80-column)

**Use `get_text_screen_full` — it is the only screen source that is
correct in 80-column mode and decodes inverse and MouseText.** Driver CLI:
`m8.py text` (add `attrs` for the per-cell attribute grid). It reads the
main and auxiliary text pages directly, so it sidesteps the traps below.

```
$ m8.py text
[80 columns x 24 rows, alt charset: on]
... 24 rows, one character per cell, MouseText decoded ...
```

Why the other sources mislead, and must not be trusted for exact content:

- **`get_text_screen` mis-orders the two memory banks in 80-column mode.**
  In 80 columns each row is split — auxiliary memory holds the **even**
  display columns (0,2,4,…), main memory the **odd** (1,3,5,…) — and the
  legacy tool pairs them backwards, so `ABCDEFGH` comes back `BADCFEHG`.
  It also renders inverse/flash as normal ASCII, hiding attributes.
- The **graphical `screenshot`** renders 80-column text and MouseText
  *correctly* (verified), but it returns a JPEG — you cannot grep or
  diff pixels. Use it for a human/visual check, not for assertions.
- The **disk-LED overlay** transiently writes a byte (often `$FF`) into
  the top-left of the legacy text dump — a stray `.` at row 0 col 1.
  `get_text_screen_full` reads raw bank memory and is free of it.

`get_text_screen_full` reports the column count and ALTCHARSET state in
its header line, and with `attributes=true` returns a second grid where
each cell is `.`=normal `i`=inverse `f`=flash `m`=mousetext — that grid
is how you verify a UI precisely (e.g. "this border cell is `.` normal
ASCII, not `m` — so it is not real MouseText").

**Manual reconstruction (fallback for a microM8 build without the tool).**
Read both banks and interleave; row bases are interleaved, not linear:

```
base(row) = $0400 + (row mod 8)*$80 + (row div 8)*$28
main = read_memory_range   {address: $0400, count: $400}     # odd cols
aux  = read_ram_range      {region:"aux.all", offset:$0400, count:$400}  # even
# 80-col row r: col[2k] = aux[base+k], col[2k+1] = main[base+k]
# 40-col row r: col[k]  = main[base+k]
```

Decode each byte by its band (with ALTCHARSET on): `$A0–$FF` normal video
(mask `$7F`), `$00–$1F` inverse uppercase (`| $40`), `$20–$3F` inverse
symbols, `$40–$5F` **MouseText**, `$60–$7F` inverse lowercase. With
ALTCHARSET off, `$40–$7F` is flashing text instead of MouseText/inverse-
lowercase. `scripts/m8.py screen`/`rows` do this for the **main** page
only (40-column case); for 80-column always prefer `text`.

## 7. MouseText and the alternate character set

MouseText is the set of 32 desktop-UI glyphs (apples, arrows, checkmark,
folder, title-bar hatch, border lines, diamond) that occupy screen codes
**`$40–$5F` when the alternate character set is on** (`ALTCHARSET`,
status `$C01E` bit 7; turned on by the 80-column firmware / `PR#3`, or
directly by writing `$C00F`). With ALTCHARSET **off**, those same codes
are flashing uppercase. So MouseText only appears when both the codes and
the soft switch agree — a program that pokes `$40–$5F` without ALTCHARSET
on shows flashing letters, not icons.

Encoding facts for verifying a program's UI:

- Inverse uppercase lives at **`$00–$1F`**, MouseText at **`$40–$5F`** —
  a program that wants inverse capitals but has ALTCHARSET on and uses
  `$40–$5F` gets icons instead (the classic MouseText bug). To get inverse
  capitals with ALTCHARSET on, use `$00–$1F`.
- Proper display (Apple Tech Note Mouse #6): `PR#3`, then print
  `CHR$(27)`/`$1B` to enable MouseText, `CHR$(15)`/`$0F` for inverse,
  then the letters `@ A–Z [ \ ] ^ _`; `CHR$(24)`/`$18` disables. From
  assembly: enable the firmware, set ALTCHARSET, send `$40–$5F` through
  `COUT`. Directly poking `$40–$5F` works when ALTCHARSET is on but is
  "unsupported" (could break under a future glyph remap).
- The `F`/`G` glyphs (`$46`/`$47`) were a two-cell "running man" in early
  ROMs, replaced in current production by a return-arrow and a title-bar
  hatch; don't rely on the running man.

**Verifying MouseText when testing:** microM8 renders MouseText faithfully
(verified), so the **graphical `screenshot`** is ground truth for the
*picture*. For *data* assertions, `get_text_screen_full attributes=true`
tells you which cells are MouseText (`m`) versus inverse (`i`) versus
plain ASCII (`.`) — that distinction is how you confirm a border or icon
is "proper MouseText" and not ASCII line-drawing characters.

## 8. Installing on a disk image with CiderPress2 (cp2)

For a durable install (so `BRUN PROG` works after a reboot), put the file
on the `.dsk` from the host with `cp2` — **not** from inside the emulator:

- **In-emulator disk-write persistence to the host `.dsk` is
  build-dependent.** It has been observed both ways on different microM8
  builds. Don't rely on it: after exiting, check the host image with
  `cp2 catalog`.
- **Stop the emulator and back up the image first.** Never `cp2`-write an
  image a running emulator has mounted — you'll corrupt it.

```
pkill -f "microM8 -mcp"        # stop the emulator
cp disk.dsk disk.dsk.backup    # back up
cd build && cp2 add ../disk.dsk 'PROG#060801'   # BIN, aux $0801
cp2 catalog ../disk.dsk        # verify
```

- The **NAPS suffix `NAME#TTAAAA`** sets the ProDOS type/aux: `TT` = hex
  file type (`06` BIN, `04` TXT, `FF` SYS, `FC` BAS), `AAAA` = hex aux
  (load address for BIN). `PROG#060801` = BIN loading at `$0801`.
- **`cd` into the file's directory before `cp2 add`**, or the parent path
  becomes a subdirectory on the volume (`cp2 add disk /tmp/PROG#060801`
  creates a `tmp/` dir on the disk).
- Other commands: `cp2 catalog disk`, `cp2 rm disk NAME`,
  `cp2 export disk text NAME -` (read a TXT file back to verify a save).
- This workflow uses CiderPress2 (`cp2`), installed separately.

Then relaunch the emulator and `BRUN PROG` from the `]` prompt to confirm
the real load-from-disk path, not just the RAM iteration loop.

## 9. Local configuration

Set the paths described in the repository README: `MICROM8_BIN`, `PRODOS_DISK`,
and (when needed) `DOS33_DISK`. Set `MICROM8_MCP_URL` to override the driver's
default SSE endpoint, `http://localhost:8080/mcp/sse`.

The MCP tools documented here are an emulator extension, not a guarantee of
stock microM8 support. Use a build exposing these tools, or adapt the integration
workflow to your emulator. No emulator, ROM, or disk image is included here.

The `applesoft-basic` skill describes BASIC-specific testing; this skill covers
assembly and whole-program testing.
