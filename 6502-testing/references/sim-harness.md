# Unit-test tier — symbol-driven py65 harness

The `6502-codegen` skill verifies one routine at a time from a JSON spec.
That's the right tool for a standalone subroutine, but a whole program is
dozens of routines sharing zero page, buffers, and ROM/OS calls. This
tier loads the **real merlin32-built binary** and calls its routines **by
name**, so the thing you test is the thing you ship — same bytes, same
addresses. `scripts/sim.py` is the reusable harness; this file shows the
pattern. Table of contents:

1. Why this tier exists (and what it can't do)
2. Building so the harness can find your symbols
3. The `Program` object
4. Faking ROM and the ProDOS MLI
5. A worked test file
6. Fuzzing: differential and invariant

---

## 1. Why this tier exists (and what it can't do)

Put **all the logic** here: buffer manipulation, parsers, motion/edit
commands, table-driven dispatch, anything computational. It runs in the
py65 simulator — hundreds of assertions in well under a second, fully
deterministic, with every byte of memory inspectable. This is where you
catch regressions while iterating; a behavioral suite here is what lets
you refactor (e.g. an optimization pass) without fear.

What it **cannot** model, and so must go to the microM8 tier:

- ROM and firmware behavior (COUT, HOME, GETLN, the 80-col firmware).
- The real ProDOS MLI (file I/O, prefix handling, error codes).
- Soft switches, real keyboard hardware, the actual text-page mapping as
  the video scanner sees it, and timing/feel.

py65 is **functional, not cycle-accurate** — never assert on cycle counts
here (use the `6502-codegen`/`6502-optimization` reference tables for
those, computed not measured).

## 2. Building so the harness can find your symbols

Assemble with `-V` so merlin32 emits the symbol file:

```
merlin32 -V <macro-lib> src/prog.s        # -> PROG and PROG_Symbols.txt
```

`PROG_Symbols.txt` is semicolon-delimited; `sim.load_symbols()` reads the
`00/XXXX` address field and the name field into `{name: address}`. Label
every routine and state variable you want to drive or inspect — labels
are free and they are your test API.

## 3. The `Program` object

```python
import sim                      # run from this skill's scripts/ dir,
                                # or add it to sys.path
p = sim.Program("build/PROG", "build/PROG_Symbols.txt", org=0x801)

p.sym("TEXTBUF")               # address of a label
p.peek("MODE"); p.poke("MODE", 1)
p.peek16("GAPS"); p.poke16("GAPS", p.sym("TEXTBUF"))
p.read("PATHBUF", 8); p.write("CMDBUF", b"w notes")
p.call("INITST")               # run a routine to its RTS
p.call("DISPATCH", a=0xE9)     # seed A (here a high-bit 'i') then run
p.row(0)                       # decode text-page row 0 to ASCII
```

`peek`/`poke`/`read`/`write` take a symbol **name or a raw address**.
`call(name, a=, x=, y=)` seeds only the registers you pass and runs to
`RTS` (raising if it runs away). Set up state, call a handler, assert on
memory — the same shape as a 6502-codegen case, but across the real
program.

## 4. Faking ROM and the ProDOS MLI

Routines that `JSR` into ROM or the MLI would wander off into
unimplemented territory. Replace those entry points:

```python
p.stub_rom("BELL1")            # JSR BELL1 -> INC a counter / RTS
p.beeps()                      # how many times it "beeped" — assert on errors
p.fake_mli()                   # MLI at $BF00 logs call numbers, returns success
p.mli_calls()                  # e.g. [0xC0,0xC8,0xD0,0xCB,0xCB,0xCC]
```

- `stub_rom(name)` overwrites the entry with `INC counter / RTS`, making a
  call both side-effect-free and **observable** — a beep counter is how
  you assert "this illegal motion was rejected" without a speaker.
- `fake_mli()` installs a gate that records each MLI call number and
  returns carry-clear success, so you can assert the **exact call
  sequence** a file operation emits (did `:w` do CREATE→OPEN→SET_EOF→
  WRITE→CLOSE?) without a real filesystem. To test error handling, poke a
  custom gate that returns carry-set with an error code in A.

This catches contract bugs the happy path hides — e.g. a buffer-overflow
into the saved-zero-page region only shows up when you assert the
saved-ZP bytes are untouched after the call.

## 5. A worked test file

```python
import sim
P = lambda: sim.Program("build/PROG", "build/PROG_Symbols.txt", org=0x801)
fails = []
def check(name, cond, info=""):
    if not cond: fails.append(f"{name} {info}"); print("FAIL", name, info)

def fresh():
    p = P(); p.stub_rom("BEEP"); p.fake_mli(); p.call("INITST"); return p

def set_text(p, s, cursor=0):     # install text with a gap at `cursor`
    b = s.encode(); pre, post = b[:cursor], b[cursor:]
    p.write("TEXTBUF", pre); p.write(0x9000 - len(post), post)
    p.poke16("GAPS", p.sym("TEXTBUF") + len(pre))
    p.poke16("GAPE", 0x9000 - len(post)); p.poke16("TOPL", 0)

def get_text(p):
    g, e = p.peek16("GAPS"), p.peek16("GAPE")
    return (p.read(g, 0) + bytes(p.mpu.memory[e:0x9000])).decode("latin1") \
        if False else \
        (bytes(p.mpu.memory[p.sym("TEXTBUF"):g]) +
         bytes(p.mpu.memory[e:0x9000])).decode("latin1")

def t_insert():
    p = fresh(); set_text(p, "", 0)
    p.call("DISPATCH", a=ord('i') | 0x80)         # enter insert
    for c in b"HI": p.call("DISPATCH", a=c | 0x80)
    check("insert.text", get_text(p) == "HI", get_text(p))
    p.call("RENDER")
    check("insert.row0", p.row(0).rstrip() == "HI", p.row(0))

t_insert()
print(f"{len(fails)} failures")
```

Run with the repository environment so py65 is importable:

```
"$APPLE_II_SKILLS/.venv/bin/python" tests/run_tests.py
```

(`CODEGEN_DIR` is only needed if that skill is not installed as a sibling or at
one of the default skill paths.)

## 6. Fuzzing: differential and invariant

Once routines are callable by name, fuzzing is cheap and finds the edge
cases directed tests miss:

- **Differential** — for anything with a clean spec (search, a parser,
  arithmetic), generate random inputs, compute the answer in Python, and
  compare the 6502 result. A divergence is a precise, minimizable repro.
- **Invariant** — drive random *command* sequences and assert structural
  invariants after every step: pointers stay ordered, a "cursor" stays on
  a legal cell, motions never mutate the document, deletes never grow it,
  a mode toggle always resolves. This found a real "cursor parked in an
  illegal position after o-then-ESC" bug in the editor that built this
  skill — the invariant flagged it; the directed tests had missed it.

Keep the fuzzer seeded and replayable, and when it finds a failure, fold
a directed regression test for that exact case into the suite before
fixing.
