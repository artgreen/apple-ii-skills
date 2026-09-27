# Widget recipes

Column-by-column byte layouts for the five core widgets, each reverse-engineered
from a master program's live screen RAM (Block Warden, MouseWrite, ProTERM) and
re-verified in a working build. Codes assume ALTCHARSET on. See
[glyph-map.md](glyph-map.md) for the glyph table and the geometry gotchas.

Contents:
1. Dialog box frame (Bredon clean-corner)
2. Checkerboard title bar
3. Buttons (inverse-bar + paren caps)
4. Pull-down menus (MouseWrite recipe)
5. Scrollbar + list picker
6. The `asc` high-bit / invert gotcha

---

## 1. Dialog box frame — Glen Bredon's clean-corner trick

Read from Block Warden 2.5's screen RAM. The insight: there are **no corner
glyphs**, and you get flush corners by using two *different* horizontal rules at
opposite cell positions, with **blank spaces in the corners**.

For a box spanning columns `L..R`, width `W = R-L+1`:

| Row        | Col L   | Cols L+1 .. R-1        | Col R   |
|------------|---------|------------------------|---------|
| **top**    | `$A0`   | `$DF` (underscore) ×(W-2) | `$A0` |
| interior   | `$5A`   | content (spaces `$A0`) | `$5F`   |
| **bottom** | `$A0`   | `$4C` (hline) ×(W-2)   | `$A0`   |

Why it works: the underscore `$DF` rules at the cell **bottom**, so the top edge
sits flush *above* the first interior row, landing exactly where the `$5A`/`$5F`
walls begin. `$4C` rules at the cell **top**, so the bottom edge sits flush
*below* the last interior row, where the walls end. Corners are blank — the rules
meet the wall ends with no corner glyph, no float, no feet. Symmetric and clean.

```
GAP filled with $A0 in corners:        _________________
                                      | Save changes?   |     <- $5A walls, $A0 fill
                                      |_________________|     <- $4C bottom, $A0 corners
top row underscores ($DF), bottom row hlines ($4C)
```

**Alternative (all-MouseText, no underscore):** top AND bottom rows both
`$5A` + `$4C`×(W-2) + `$5F` (corner verticals on *both* rows). The bottom corner
verticals give the `$4C` rule something reaching down to meet, reading as a small
corner foot. Looks slightly heavier than the Bredon trick; use it only if you
want a pure-MouseText frame. Do **not** put plain `$4C` corners on the bottom with
no verticals — the rule floats detached. Bredon's underscore-top is the clean one.

---

## 2. Checkerboard title bar

Block Warden's titled dialogs put a 50%-grey hatch band on the title row, with
the title centered in normal video on top. The texture is the **`$56`/`$57`
alternating pair** (NOT `$47`, which is horizontal stripes).

Title row, interior columns: alternate `$56, $57, $56, $57, …` across the band,
then overprint the centered title string in normal video, then rule a `$4C`
separator on the row below the title.

```asm
; CHECKER_FILL -- write X cells of $56/$57 alternating from CURROW,CURCOL.
CHECKER_FILL    txa
                and   #1
                bne   :odd
                lda   #$56
                bra   :put
:odd            lda   #$57
:put            jsr   PUTRAW          ; preserves A/X/Y, advances CURCOL
                dex
                bne   CHECKER_FILL
                rts
```

Give the title string leading/trailing spaces (`asc " Word II "`) so the hatch
doesn't crowd the text.

---

## 3. Buttons — inverse bar + paren caps (ShrinkIt / ProTERM / WeeGUI)

No custom font. A button is a one-row **inverse-video band** flanked by high-bit
ASCII parens as pseudo-rounded caps:

| Piece        | Bytes                                              |
|--------------|----------------------------------------------------|
| left cap     | `$A8`  (normal `(`)                                |
| band + label | inverse space `$20` padding + the label in inverse |
| right cap    | `$A9`  (normal `)`)                                |

**Focus / default = inverse band; unfocused = the exact same shape in NORMAL
video.** Focus is an attribute swap, not a different glyph — so a button toggles
between focused/unfocused by re-drawing the band with TOINV vs TONORM. An inline
`$41` (open-apple) inside the label reads as `⌘-S`.

```
focused:   (^^Yes^^)   <- inverse band, black-on-white
unfocused: ( No )      <- normal band, white-on-black, same footprint
```

---

## 4. Pull-down menus — the MouseWrite recipe

Read from MouseWrite's live screen RAM. The non-obvious part is the **video
polarity**, which is easy to misjudge on a mono screen:

| Element                    | Video                                        |
|----------------------------|----------------------------------------------|
| menu **bar** (titles row)  | **inverse** (black-on-white)                 |
| open menu **title**        | **normal** — a dark "pressed" block in the bar |
| pulldown **items**         | **normal** (white-on-black) — NOT inverse    |
| **highlighted** item       | **inverse** full-width bar                    |
| left / right walls         | `$5A` / `$5F`                                 |
| group separators           | `$53` (mid-dash) across the interior          |
| bottom edge                | `$4C`                                         |
| **top edge of pulldown**   | **none** — items start flush under the bar (no gap) |

**Shortcut rendering:** right-aligned before the right wall, a MouseText modifier
glyph + the key letter, **with a space on each side**:

```
| Copy          [sp] $41 C [sp] |        <- ⌘ C
  ^item label             ^key   ^right wall $5F
```

Modifier glyph by key type: `$41` open-apple (⌘), `$40` solid-apple, `$5B`
diamond (Control). Place the glyph at `MBCOL + MBWIDTH - 4`, the key at `-3`,
fill spaces at `-5` and `-2`.

**Two-pass draw** (simplest correct structure): draw every item NORMAL in a loop,
then repaint just the selected row INVERSE in one unconditional post-pass
(`HILITE_SEL`). No per-item "is this selected?" branch in the loop. Widen each
menu's box so the longest `label␣␣␣⌘K␣` fits.

---

## 5. Scrollbar + list picker

A file/list picker that scrolls needs a right-hand scrollbar column and per-row
affordances:

**Scrollbar column** (one cell per visible row, right edge of the box):
- top cell: `$4B` (up arrow) cap
- bottom cell: `$4A` (down arrow) cap
- thumb cell(s): `$4E` (solid block), positioned proportionally
- track (everything else): `$5F` (vertical rule) — reads as a thin groove

Proportional thumb position = `top + (scrolltop * (track_h - thumb_h)) / (total - visible)`.
Do the multiply-then-divide in 16-bit (`MUL_AY` / `DIV16_8`) to avoid overflow.

**Selected row:** a `$55` (right arrow) pointer in the left margin + an inverse
bar across the row, stopping a couple cells short of the scrollbar so the bar
doesn't collide with the groove.

**Directory marker:** `$5B` diamond (the folder pair does not render — see
glyph-map.md). **Legend row** at the box bottom uses literal glyphs:
`$4D`=Return to open, `$4B`/`$4A`=scroll.

**Adaptive height:** `VISROWS = min(item_count, MAX_VIS)` so a short list draws a
short box instead of a half-empty frame.

---

## 6. The `asc` high-bit / invert gotcha (cost a long debugging detour)

Merlin's **`asc` directive emits HIGH-BIT ASCII**: `asc "Copy"` → `$C3 $EF $F0 $F9`.
A naive "to inverse" routine that only folds the `$40–$5F` MouseText band leaves
anything ≥ `$60` (i.e. all high-bit text) unchanged — so an inverse-printed label
renders as NORMAL video even though the invert routine was called. The symptom is
maddening: the inverse *fill* shows, a low-bit shortcut *key* (stored `dfb 'C'` =
`$43`) inverts fine, but the high-bit *label* stays normal.

Fix: fold to 7 bits **first**, then map into the inverse band:

```asm
TOINV           and   #$7f            ; fold high-bit (asc) text to 7-bit FIRST
                cmp   #$60
                bcs   :keep            ; $60-$7F inverse lowercase stays
                cmp   #$40
                bcc   :keep            ; $20-$3F inverse symbols stay
                and   #$1f             ; $40-$5F caps -> $00-$1F inverse caps
:keep           rts
```

The `and #$7f` is a no-op for low-bit callers (typed input, ProDOS filenames) and
correct for `asc` strings. This same one-instruction fix corrected both selected
menu labels and focused dialog-button labels. **Whenever inverse text mysteriously
renders normal, suspect high-bit source bytes first.**
