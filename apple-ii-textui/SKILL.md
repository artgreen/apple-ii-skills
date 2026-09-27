---
name: apple-ii-textui
description: "Use when designing or debugging Apple II text-mode TUIs in 65C02 assembly with 80-column screen RAM, MouseText glyphs, dialog boxes, pull-down menus, buttons, scrollbars, list pickers, inverse text, ALTCHARSET, or byte-level screen verification. Not for low-level soft-switch or aux-bank mechanics."
license: MIT
---

# Apple II Text-Mode UI (MouseText)

How to compose a good-looking text-mode UI from the Apple II's stock 80-column
charset and MouseText glyphs — the design idioms layered *on top of* the hardware.
This skill carries the glyph map and the widget recipes; the mechanics it depends
on (the `$C0xx` soft switches, aux=even/main=odd column split, the char-encoding
bands) live in the **apple-assembly-programming** skill — read that for the
substrate, this for the look.

Targets the Enhanced IIe / IIc / IIc+ / IIgs (8-bit) — i.e. any machine with the
**65C02 + MouseText ROM**. The original IIe and II+ have no MouseText.

## The one rule that matters most

**Read the bytes; don't guess.** Every recipe in this skill was reverse-engineered
from a master program's live screen RAM (Block Warden, MouseWrite, ProTERM), then
re-verified in a working build. MouseText rendering is full of surprises — `$4C`
rules at the cell top not bottom, the "folder" glyphs don't render as folders,
`asc` strings won't invert. Documentation lies; screen RAM doesn't. When you draw
a widget, dump RAM and confirm the exact codes. When you admire a master's dialog,
boot it and read how it's built. See
[references/screen-ram-verification.md](references/screen-ram-verification.md)
and `scripts/decode_screen.py`.

## Prerequisites for any MouseText UI

- **ALTCHARSET on** (`STA $C00F`) — otherwise `$40–$5F` are flashing capitals,
  not MouseText.
- **Write screen codes directly to text RAM.** Do not print MouseText through
  COUT — it remaps bytes. A direct `PUTRAW` primitive (set row/col, write the raw
  byte, advance) is the foundation.
- **Know the char bands** (ALTCHARSET on): `$00–$3F` inverse, `$40–$5F` MouseText,
  `$60–$7F` inverse lowercase, `$80–$FF` normal. So inverse space = `$20` (solid
  block), normal space = `$A0`, normal `(`/`)` = `$A8`/`$A9`.

## Glyph quick reference

The codes you reach for constantly (full table + the don't-use list in
[references/glyph-map.md](references/glyph-map.md)):

| Code | Glyph | Code | Glyph | Code | Glyph |
|------|-------|------|-------|------|-------|
| `$41` | ⌘ open-apple | `$4C` | ─ hline (cell **top**) | `$5A` | │ vline **left** |
| `$40` | solid apple | `$4D` | ↵ return | `$5F` | │ vline **right** |
| `$44` | ✓ check | `$4E` | ▮ block (thumb) | `$5B` | ◆ diamond |
| `$48`/`$55` | ← / → | `$4A`/`$4B` | ↓ / ↑ | `$53` | ‑ mid-dash |
| `$56`/`$57` | ▦ checker pair | `$DF` | _ underscore (cell **bottom**, normal video) | | |

The two facts that drive every box: **`$4C` rules at the cell TOP** (use for box
bottoms), and there's **no clean bottom-of-cell horizontal in MouseText** — use
the **normal underscore `$DF`** for box tops.

## Widget recipes

Full column-by-column byte layouts with assembly snippets are in
[references/widget-recipes.md](references/widget-recipes.md). The essentials:

- **Dialog box (Bredon clean-corner):** top row = `$A0` + `$DF`×(W-2) + `$A0`;
  interior = `$5A` + content + `$5F`; bottom row = `$A0` + `$4C`×(W-2) + `$A0`.
  Blank corners; the two opposite-position rules land flush where the walls end.
- **Title bar:** fill the title row with the `$56`/`$57` checkerboard pair, then
  overprint the centered title (give it leading/trailing spaces), then a `$4C`
  separator below. Note: `$47` is stripes, not a checkerboard.
- **Button:** inverse-video band (`$20` padding + inverse label) capped by `$A8`
  `(` and `$A9` `)`. Focus/default = inverse; unfocused = the same shape in normal
  video (an attribute swap, not a different glyph).
- **Pull-down menu:** bar = inverse; items = **normal** (white-on-black, not
  inverse); open title = normal "pressed" block; highlighted item = inverse bar;
  walls `$5A`/`$5F`; separators `$53`; bottom `$4C`; **no top edge** (items flush
  under the bar). Shortcuts right-aligned: ` ⌘ K ` (modifier glyph + key, a space
  each side). Draw all items normal, then repaint the selected row inverse in one
  pass.
- **Scrollbar + picker:** right column = `$4B` up-cap / `$4A` down-cap / `$4E`
  proportional thumb / `$5F` track; selected row = `$55` pointer + inverse bar;
  directory marker = `$5B` diamond; adaptive box height = `min(count, MAX_VIS)`.

## Top gotchas

- **`asc` emits HIGH-BIT ASCII**, so a to-inverse routine that only folds the
  `$40–$5F` band leaves text ≥ `$60` rendering NORMAL. Fold `and #$7f` *first*,
  then map to the inverse band. (Symptom: inverse fill shows, low-bit shortcut key
  inverts, but the label stays normal.) Full fix in widget-recipes.md §6.
- **The `$4F`/`$50` folder pair does NOT render as a folder** on the IIe ROM — use
  the `$5B` diamond as a directory marker.
- **Box bottom floats detached** if you use plain `$4C` corners with no verticals
  — use the Bredon underscore-top / `$4C`-bottom / blank-corner recipe instead.
- **Glyphs render as flashing caps** → ALTCHARSET (`$C00F`) is off.

## Verifying

Draw it, then dump and decode screen RAM to confirm the exact codes — see
[references/screen-ram-verification.md](references/screen-ram-verification.md).
`scripts/decode_screen.py aux.bin main.bin --codes` reconstructs the 80×24 grid
from the two banks and names every MouseText code. This same step is how you read
the masters' UIs to copy a technique.
