# Screen-RAM verification workflow

The single most valuable technique in this skill: **don't guess how a glyph
renders or how a master program drew its UI — read the bytes.** Every recipe here
was won by dumping live screen RAM, not from documentation. Two uses:

1. **Verify your own output** — draw a widget, dump RAM, confirm the exact codes.
2. **Reverse-engineer the masters** — boot Block Warden / MouseWrite / ProTERM,
   open the dialog or menu you admire, and read how it's actually built.

This assumes the **microM8** emulator with its MCP server. Adapt the dump step to
any emulator that can read memory.

## The 80-column memory layout

The 80-col text screen is split across two banks:

- **EVEN columns (0,2,4,…) live in AUX** `$0400–$07FF`
- **ODD columns (1,3,5,…) live in MAIN** `$0400–$07FF`
- Row base = `$0400 + (row%8)*$80 + (row/8)*$28`
- Byte offset within a row = `col / 2`

So to reconstruct a row you interleave: `aux[base+0], main[base+0], aux[base+1],
main[base+1], …`. The `scripts/decode_screen.py` helper does this for you.

## Dumping in microM8 (MCP)

```
read_ram_range region="aux.all"  offset=0x400 count=0x400   # even columns
read_ram_range region="main.all" offset=0x400 count=0x400   # odd  columns
```

Save each to a file (binary or hex text), then decode:

```bash
# rendered 80x24 grid (ASCII stand-ins; MouseText shown as '.')
uv run python3 scripts/decode_screen.py aux.bin main.bin

# raw screen codes + MouseText glyph names, one row
uv run python3 scripts/decode_screen.py aux.bin main.bin --row 8 --codes
```

`--codes` is what you want when reverse-engineering: it prints every byte as hex
and names the MouseText codes, so you can read a dialog's frame straight off the
dump (e.g. `r8: ... 5A A0 DF DF ... A0 5F` = a Bredon box top edge).

## Driving the emulator to the screen you want

To open a master program's menu/dialog before dumping, send keystrokes. microM8's
`key_event` uses **internal vduconst codes, NOT GLFW**:

| Key   | Code     |
|-------|----------|
| left  | `0xe000` |
| right | `0xe001` |
| up    | `0xe002` |
| down  | `0xe003` |

Return and Escape go through `type_text("\r")` / `type_text("\x1b")`. The `m8.py`
helper's `type` command supports the escapes `{r}` (Return), `{e}` (Escape),
`{t}` (Tab) only.

## microM8 launch / relaunch hygiene

Launch headless with the MCP server:

```bash
cd /path/to/microm8 && nohup ./microM8 -mcp -mcp-mode sse -mcp-port 8080 \
  -no-update -ssc-telnet-no-eof -drive1 <disk.po> &
# then health-poll the MCP port and sleep ~7s for boot
```

**Before any relaunch, free the ports or the next boot crashes** (the telnet port
1977 conflict is fatal):

```bash
pkill -9 -f microM8
lsof -ti :1977 | xargs -r kill -9
lsof -ti :8080 | xargs -r kill -9
```

If a debugger/breakpoint left the CPU paused, a fresh reboot clears it.

## Confirming MouseText is actually on

If glyphs render as flashing capitals instead of MouseText, ALTCHARSET is off.
The UI must `STA $C00F` (SETALTCHAR) during screen init, alongside 80-col setup
(`SET80COL $C00D`, `SET80STORE $C001`). A dump will show your intended `$40–$5F`
bytes in RAM regardless — the bytes are right, only the display interpretation
changed — so check the soft switch, not the data.
