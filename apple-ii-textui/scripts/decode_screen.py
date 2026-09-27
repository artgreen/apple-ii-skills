#!/usr/bin/env python3
"""Reconstruct the Apple II 80-column text screen from two RAM dumps.

The 80-col screen splits each row: EVEN columns live in aux $0400-$07FF,
ODD columns in main $0400-$07FF. Row base = $0400 + (row%8)*$80 + (row/8)*$28,
byte offset within the row = col/2. This script interleaves the two banks back
into the 80x24 grid so you can read how a program drew its UI.

Use it to reverse-engineer the masters (Block Warden, MouseWrite, ProTERM...):
dump both banks in microM8, then decode here to see the exact screen codes.

  read_ram_range region="aux.all"  offset=0x400 count=0x400   -> aux dump
  read_ram_range region="main.all" offset=0x400 count=0x400   -> main dump

Input: two files holding $400 (1024) bytes each, as raw binary OR as hex text
(whitespace/comma/0x separated -- anything non-hex is ignored).

  decode_screen.py aux.bin main.bin              # rendered text grid
  decode_screen.py aux.hex main.hex --codes      # show $hex screen codes
  decode_screen.py aux.bin main.bin --row 8      # one row, both views

With ALTCHARSET on, $40-$5F are MouseText. This script names those glyphs and
flags the band of every byte so you can tell inverse from normal at a glance.
"""
import sys
import argparse
import re

# Verified MouseText names for screen codes $40-$5F (ALTCHARSET on, Enhanced IIe ROM).
MOUSETEXT = {
    0x40: "CApple", 0x41: "OApple", 0x42: "ptr", 0x43: "hourglass",
    0x44: "check", 0x45: "errflag", 0x46: "folderL", 0x47: "hatch",
    0x48: "left", 0x49: "dots", 0x4A: "down", 0x4B: "up",
    0x4C: "Hline_top", 0x4D: "return", 0x4E: "block", 0x4F: "folderUL",
    0x50: "folderUR", 0x51: "tray", 0x52: "vbar", 0x53: "dash_mid",
    0x54: "folder", 0x55: "right", 0x56: "checkerA", 0x57: "checkerB",
    0x58: "lefttee", 0x59: "righttee", 0x5A: "Vline_left", 0x5B: "diamond",
    0x5C: "frag", 0x5D: "leftfill", 0x5E: "fillsh", 0x5F: "Vline_right",
}


def band(code):
    """Name the character band of a screen code (ALTCHARSET on)."""
    if code < 0x40:
        return "inv"          # $00-$3F inverse caps/symbols
    if code < 0x60:
        return "MT"           # $40-$5F MouseText
    if code < 0x80:
        return "inv"          # $60-$7F inverse lowercase
    return "norm"             # $80-$FF normal video


def glyph(code):
    """A printable stand-in for a screen code."""
    b = band(code)
    if b == "MT":
        return "."            # MouseText -- see --codes for the name
    # inverse/normal both fold to ASCII via low 7 bits
    ch = code & 0x7F
    if 0x20 <= ch < 0x7F:
        return chr(ch)
    return "?"


def load(path):
    """Load $400 bytes from a binary or hex-text file."""
    data = open(path, "rb").read()
    text = data.decode("latin-1")
    toks = []
    for line in text.splitlines():
        line = line.split("|", 1)[0]
        if ":" in line:
            line = line.split(":", 1)[1]
        toks.extend(re.findall(r"0[xX]([0-9a-fA-F]{1,2})|(?<![0-9a-fA-F])([0-9a-fA-F]{2})(?![0-9a-fA-F])", line))
    out = bytes(int(a or b, 16) for a, b in toks)
    if len(out) >= 0x400:
        return out
    return data


def row_base(row):
    return (row % 8) * 0x80 + (row // 8) * 0x28


def decode(aux, main, show_codes, only_row):
    rows = range(24) if only_row is None else [only_row]
    for r in rows:
        base = row_base(r)
        cells = []
        for col in range(80):
            bank = aux if (col % 2 == 0) else main
            code = bank[base + (col // 2)]
            cells.append(code)
        if show_codes:
            print(f"r{r:2}: " + " ".join(f"{c:02X}" for c in cells))
            mts = [f"{i}:{MOUSETEXT.get(c, '?')}"
                   for i, c in enumerate(cells) if band(c) == "MT"]
            if mts:
                print("      MT-> " + "  ".join(mts))
        else:
            print(f"r{r:2}|" + "".join(glyph(c) for c in cells) + "|")


def main():
    ap = argparse.ArgumentParser(description="Decode Apple II 80-col screen RAM.")
    ap.add_argument("aux", help="aux $0400-$07FF dump (bin or hex text)")
    ap.add_argument("main", help="main $0400-$07FF dump (bin or hex text)")
    ap.add_argument("--codes", action="store_true",
                    help="show raw screen codes + MouseText names")
    ap.add_argument("--row", type=int, default=None, help="decode only this row")
    args = ap.parse_args()
    aux, main_ = load(args.aux), load(args.main)
    if len(aux) < 0x400 or len(main_) < 0x400:
        sys.exit(f"need >=1024 bytes each (got aux={len(aux)} main={len(main_)})")
    decode(aux, main_, args.codes, args.row)


if __name__ == "__main__":
    main()
