# MouseText glyph map (verified)

Screen codes **`$40`–`$5F`** render as MouseText **only when ALTCHARSET is on**
(`STA $C00F` / `SETALTCHAR`). With ALTCHARSET off, the same codes are flashing
capitals. Write these bytes straight to text RAM — do **not** print them through
COUT (COUT remaps and high-bits them).

All codes below were rendered on an Enhanced-IIe ROM in microM8 and confirmed by
screenshot + screen-RAM readback. The Apple IIc / IIc+ / IIgs 8-bit ROMs match.

## Character bands (ALTCHARSET on)

| Range     | Band               | Notes                                  |
|-----------|--------------------|----------------------------------------|
| `$00–$1F` | inverse caps       | inverse `@A-Z[\]^_`                     |
| `$20–$3F` | inverse symbols    | `$20` = **inverse space = solid white block** |
| `$40–$5F` | **MouseText**      | the glyph set below                    |
| `$60–$7F` | inverse lowercase  |                                        |
| `$80–$FF` | **normal video**   | normal text = ASCII OR `$80` (high bit)|

So: normal space = `$A0`, inverse space = `$20`, normal `(` = `$A8`, `)` = `$A9`.

## The glyphs that matter for a TUI

| Code  | Const (Word II) | Glyph / use                                            |
|-------|-----------------|--------------------------------------------------------|
| `$40` | MT_CAPPLE       | closed (solid) apple — Solid-Apple shortcut marker     |
| `$41` | MT_OAPPLE       | open apple ⌘ — Open-Apple shortcut marker, menu-bar logo|
| `$44` | MT_CHECK        | checkmark — "on" menu item / checkbox                  |
| `$48` | MT_LEFT         | ← left arrow                                           |
| `$4A` | MT_DOWN         | ↓ down arrow — scrollbar down-cap, "more below"        |
| `$4B` | MT_UP           | ↑ up arrow — scrollbar up-cap, "more above"            |
| `$4C` | MT_HLINE        | horizontal rule that sits at the **TOP** of the cell   |
| `$4D` | MT_RETURN       | ↵ return arrow — "press Return" legend                 |
| `$4E` | MT_BLOCK        | ▮ solid block — scrollbar thumb                        |
| `$53` | —               | mid-height dash — menu group separator                 |
| `$55` | MT_RIGHT        | → right arrow — selection pointer in a list            |
| `$56` | —               | checkerboard dither A ┐ alternate the pair `$56 $57`   |
| `$57` | —               | checkerboard dither B ┘ for a 50% title-bar texture    |
| `$5A` | MT_VLINEL       | vertical rule, **LEFT**-aligned in cell — box LEFT wall|
| `$5B` | MT_DIAMOND      | ◆ diamond — directory marker, Control-key shortcut     |
| `$5F` | MT_VLINE        | vertical rule, **RIGHT**-aligned in cell — box RIGHT wall|

Plus the **normal-video underscore `$DF`** — a rule at the cell **BOTTOM**.
Not MouseText, but essential for box tops (see widget-recipes.md).

## Geometry gotchas — why box corners are hard

The two facts that drive every box recipe:

- **`$4C` (hline) rules at the TOP of its cell.** Good for a box BOTTOM edge
  (flush under the content), wrong for a top edge (it would float mid-gap).
- **`$5A`/`$5F` (vlines) reach the cell TOP but stop short of the bottom.** A
  wall meets a top rule cleanly; an all-`$4C` bottom row floats *below* where the
  walls end unless you handle the join (see the two recipes in widget-recipes.md).
- There is **no clean bottom-of-cell horizontal in MouseText.** The answer is the
  normal underscore `$DF` for the top edge. This is the single non-obvious trick.

## Glyphs that do NOT work as you'd hope (don't use)

- **`$47` is NOT a checkerboard** — it renders as horizontal stripes (≡). Usable
  as a striped end-cap, but for a 50%-grey title texture use the `$56`/`$57` pair.
- **`$4F`+`$50` ("Apple Mouse #6 folder" pair) do NOT render as a folder** on the
  IIe ROM — they come out as box/bar fragments. For a directory marker use the
  `$5B` diamond or a bracketed `[DIR]` label, never the folder pair.
- The `$42 ptr / $46 folderL / $54 folder` names in the table are nominal Apple
  assignments; they do **not** render as recognizable icons on this ROM. Verify
  any glyph before relying on it — the only trustworthy source is screen RAM.

## How these were verified

Every entry was confirmed empirically, not from a datasheet: render the code,
screenshot it, and read it back from screen RAM. See
[screen-ram-verification.md](screen-ram-verification.md) for the exact microM8
procedure. The `H/J/K/U` → left/down/up arrow cluster ($48/$4A/$4B/$55) is the
classic sanity check that the map is aligned correctly.
