# 6502 / 65C02 / 65C816(8-bit) Programming Techniques — Merged Agent Reference

**Status:** Draft v1 (merge of the narrative "silicon/algorithm" reference and the structured "agent skill" reference).
**Primary audience:** another AI agent generating new 65xx assembly. **Do not assume the reading agent is a frontier model.** Prefer lookup over recall, copy the fallbacks verbatim, and obey the hard rules in Section 0 literally.
**Secondary audience:** human programmers.
**Last updated:** 2026-06-02.

---

## HOW TO USE THIS DOCUMENT (READ FIRST)

You are most likely an AI agent. Follow this procedure on every code-generation request:

1. **Determine the CPU target** before writing any instruction. If the user did not state one, default to **documented NMOS 6502** (the most portable). The four recognized targets are defined in Section 1.
2. **Read Section 0 (Hard Rules).** These are inviolable. They are written as flat checks so you can verify your output against them line by line.
3. **Use Section 2 (Quick-Reference Tables) for cycle counts, flag effects, and opcodes. Do not recall these from memory — look them up here.** This is the single most important instruction in this document. Memorized 65xx cycle counts and "illegal" opcode behavior are a known source of model error.
4. **Find the technique** in Parts I–IX. Each uses the same fixed template (below).
5. **Emit the fallback, not the fancy version, unless the target profile allows the fancy version.** Every CPU-specific or undocumented technique ships with a portable fallback. When in doubt, emit the fallback.
6. **Annotate your output.** Use the templates in Part XI to state register/flag clobbers, cycle costs, and CPU assumptions. A weaker downstream consumer relies on these annotations.

### The per-technique template

```
### Tn: Title
What:       one-sentence description.
Code:       the canonical example (assembler syntax below), with cycle/flag notes.
Compat:     NMOS / 65C02 / 816-8bit, each marked yes / no / conditional.
Use when:   the situation that justifies it.
Watch out:  the failure mode.
Agent rules: terse do/don't, plus the FALLBACK if the technique is non-portable.
```

### Assembler syntax used here

Portable Merlin-8-style. You can copy these conventions directly:

- Labels start in column 1. Local labels begin with `:` (e.g. `:LOOP`).
- `EQU` defines a constant/symbol. `$` prefixes hexadecimal. `%` prefixes binary. `#` is an immediate operand.
- `#<EXPR` is the **low** byte of EXPR; `#>EXPR` is the **high** byte. (Low byte first is the 6502 convention everywhere.)
- `DFB` defines one or more bytes. `DA` defines a 16-bit word (low byte first). `DS n` reserves n bytes.
- Comments follow `;`.
- For self-modifying code, address an operand as `LABEL+1` (operand byte 1) or `LABEL+1` / `LABEL+2` (low/high of an absolute operand).
- **No platform specifics.** No ROM calls, no fixed I/O addresses, no display/timer races, no firmware vectors. Those belong in a separate machine-specific skill. RAM addresses in examples are generic placeholders (see Section 3).

---

## SECTION 0 — HARD RULES (NEVER VIOLATE)

Check every generated routine against this list.

1. **CLC before a standalone `ADC`.** `ADC` always adds the carry. Forgetting `CLC` adds an unwanted 1.
2. **SEC before a standalone `SBC`.** `SBC` subtracts an inverted borrow. Carry **clear** means "borrow in." Forgetting `SEC` subtracts an extra 1.
3. **Carry is an inverted borrow.** After `SBC`/`CMP`: carry **set** = no borrow = (A ≥ operand). Carry **clear** = borrow = (A < operand). Do not treat carry like a normal borrow flag.
4. **Never emit `LDA (zp)` (or any `(zp)` non-indexed indirect) for a plain-NMOS target.** That addressing mode does not exist on the NMOS 6502. Use `LDY #0 / LDA (zp),Y`. (`(zp)` is 65C02/816 only — Technique 5.)
5. **Never emit `STZ`, `PHX`, `PHY`, `PLX`, `PLY`, `BRA`, `TRB`, `TSB`, `INC A`, `DEC A`, `BIT #imm`, `JMP (abs,X)`, `RMB`, `SMB`, `BBR`, `BBS`, `WAI`, or `STP` for a plain-NMOS target.** All are 65C02/816 additions (some are WDC/Rockwell-only). Use the documented fallback.
6. **Never emit undocumented/"illegal" NMOS opcodes (LAX, SAX, DCP, ISC, SLO, RLA, SRE, RRA, ANC, ALR, ARR, SBX, and especially the unstable SHA/SHX/SHY/TAS/LAS/ANE/LXA) unless the target is explicitly NMOS-only AND the user has enabled undocumented opcodes.** They do not exist on any CMOS part. See Part IX.
7. **Never emit a `JAM`/`KIL` opcode** ($02, $12, $22, $32, $42, $52, $62, $72, $92, $B2, $D2, $F2 on NMOS). They hang the CPU until reset.
8. **On the NMOS 6502, never place an indirect-`JMP` vector so its low byte is at `$xxFF`.** `JMP ($xxFF)` reads the high byte from `$xx00`, not `$(xx+1)00`. (The 65C02/816 fix this; see Section 2 and Technique 8.)
9. **`CLD` early in NMOS interrupt handlers** if the handler does any binary `ADC`/`SBC`. The NMOS does not clear decimal mode on interrupt. (The 65C02/816 clear it automatically — but a defensive `CLD` is harmless.)
10. **Do not put self-modifying code in ROM, and do not assume it is re-entrant.** An interrupt landing between an operand patch and its use, or recursion, will corrupt it. (Part III.)
11. **Decimal mode (`SED`) is for `ADC`/`SBC` only, and you must `CLD` afterward.** On NMOS, do not branch on N/V/Z after a decimal `ADC`/`SBC` — only carry is valid. (Section 2 / Part V.)
12. **State your assumptions.** Every routine you emit should declare its CPU target, register/flag clobbers, and (if timing-sensitive) cycle behavior. Use Part XI templates.


---

## SECTION 1 — CPU COMPATIBILITY FRAME

### The four targets

| Target | Meaning in this document |
|---|---|
| **NMOS 6502** | Original MOS/Rockwell/Synertek-style 6502. Has undefined decimal flags, the indirect-`JMP` page bug, the BRK/IRQ hijack bug, RMW double-write, and undocumented opcodes. The most portable baseline. |
| **W65C02S** | Modern WDC CMOS 65C02. Bugs fixed; adds `(zp)`, `JMP (abs,X)`, `BRA`, `STZ`, `PHX/PHY/PLX/PLY`, `INC A`/`DEC A`, `TRB/TSB`, `BIT #imm`, and the WDC-only `WAI`/`STP`. Also has the Rockwell bit ops `RMB/SMB/BBR/BBS`. Undefined opcodes act as defined NOPs. |
| **Rockwell 65C02** | CMOS 65C02 with the bit ops `RMB/SMB/BBR/BBS`. Some non-WDC variants differ on `WAI`/`STP`. The **65SC02** sub-variant lacks `RMB/SMB/BBR/BBS`. |
| **W65C816 (8-bit mode)** | Emulation mode, or native mode with 8-bit accumulator/index. Fixes the NMOS bugs and generally follows **NMOS cycle timing**, not 65C02 timing. **Omits** the Rockwell bit ops `RMB/SMB/BBR/BBS`. Do **not** assume undocumented NMOS opcodes. Bank/mode handling belongs in a separate 65816 skill. |

### Agent default policy

Default to **documented NMOS-compatible 6502**. Escalate only when the request explicitly allows it:

1. **65C02 requested** → use W65C02S-compatible idioms (`BRA`, `STZ`, `PHX/PHY/PLX/PLY`, `(zp)`, `JMP (abs,X)`, `TRB/TSB`, `BIT #imm`).
2. **Rockwell bit ops requested** → may use `RMB/SMB/BBR/BBS`. Do not emit these for W65C816 or 65SC02.
3. **W65C816 8-bit requested** → keep M/X width assumptions explicit; avoid NMOS undocumented opcodes; do not use `RMB/SMB/BBR/BBS`.
4. **NMOS undocumented opcodes explicitly enabled** → only the "stable" class (Part IX), always with a fallback and a startup conformance test.
5. **Cycle-stable code requested** → annotate cycle counts, page-crossing behavior, and interrupt assumptions (Part XI).

---

## SECTION 2 — QUICK-REFERENCE TABLES (LOOK UP, DO NOT RECALL)

### 2A. Flag-effects cheat sheet

- **Set N and Z from their result:** `LDA/LDX/LDY`, `TAX/TAY/TXA/TYA`, **`TSX`**, `AND/ORA/EOR`, `ADC/SBC`, `INC/DEC`, `INX/DEX/INY/DEY`, `ASL/LSR/ROL/ROR`, `PLA` (and 65C02 `PLX/PLY`, `INC A`/`DEC A`).
- **`TXS` affects NO flags.** (Common trap: `TSX` sets N/Z, `TXS` does not.)
- **`CMP/CPX/CPY` set N, Z, C — but NOT V.**
- **Only these affect V:** `ADC`, `SBC`, `BIT` (copies memory bit 6 → V; **but `BIT #imm` affects Z only, not N or V**), `CLV` (clears it), `PLP`, `RTI`. There is **no SEV** — force V with `BIT` against a byte whose bit 6 is set (e.g. an `RTS` opcode byte, `$60`).
- **Carry as inverted borrow:** see Hard Rule 3.
- **Decimal-mode flag validity:** NMOS = only C meaningful after decimal `ADC`/`SBC`; 65C02/816 = C, N, Z valid (recomputed from the corrected result — that's the +1 cycle) but **V is unchanged from NMOS** — identical binary-derived value on every CPU, never a BCD overflow indicator (B. Clark, 6502.org). (See 2B.)

### 2B. NMOS 6502 vs 65C02 — precise behavioral differences

| Area | NMOS 6502 | 65C02 (W65C02S) | Note for W65C816 8-bit |
|---|---|---|---|
| Illegal opcodes | Execute (often useful, sometimes hang) | All act as NOPs or defined ops | Treated as defined; no NMOS illegals |
| `JMP (abs)` indirect | **Page-wrap bug**: vector at `$xxFF` reads high byte from `$xx00`. 5 cycles | Bug fixed. **6 cycles** (one extra) | Fixed; **5 cycles** (no extra), follows NMOS timing |
| Decimal `ADC`/`SBC` flags | Only **C** meaningful; N/V/Z come from binary intermediates | C, N, Z valid; **V unchanged from NMOS** (binary-derived) | as 65C02 |
| Decimal `ADC`/`SBC` timing | No extra cycle | **+1 cycle** when D=1 | Generally no extra cycle (NMOS-style) |
| D flag on IRQ/NMI/BRK | **Unchanged** (handler must `CLD`) | **Cleared automatically** after pushing P | Cleared automatically |
| RMW bus pattern (`INC/DEC/ASL/LSR/ROL/ROR`) | read → write-**original** → write-modified (a double write; strobes I/O twice) | read → **dummy read** → write | NMOS-style double write |
| Indexed read, page-cross dummy cycle | Reads an **invalid** partially-formed address (PFA) | Reads the **previous bus address** (PBA) — safe | NMOS-style |
| `STA`/`STZ abs,X` (and `abs,Y`) dummy cycle | dummy access | On 65C02, when **no** page cross, the dead cycle **reads the fully-formed target address** (destructive on read-sensitive I/O — observed on real hardware touching a UART register twice; Apple's Super Serial Card firmware ships a workaround for it). Workarounds: force a page cross so the dead read hits the safe PBA, or drop indexing near I/O — `(zp)` and plain `abs` stores have no false read | NMOS-style |
| `ASL/LSR/ROL/ROR abs,X` timing | **Always 7 cycles** | **6 cycles**, or 7 if indexing crosses a page | NMOS-style (7 always) |
| `INC abs,X` / `DEC abs,X` timing | **Always 7 cycles** | **Always 7 cycles** (NOT optimized like the shifts — a widely mis-documented point) | 7 |
| `BRK` colliding with IRQ/NMI | **Hijack bug**: the BRK can be silently dropped; pushed status still shows B set | Handled correctly | Handled correctly |

**Runtime CPU discrimination (uses the decimal-flag difference):**
`SED / CLC / LDA #$99 / ADC #$01 / CLD` — the accumulator ends at `$00` on
every CPU, but **Z=0 on NMOS** (set from the binary intermediate `$9A`) and
**Z=1 on 65C02/816** (set from the corrected result). The classic
NMOS-vs-CMOS probe.

### 2C. 65C02 new instructions (opcode / bytes / cycles)

| Instr | Opcode | Bytes | Cycles | Flags | Availability |
|---|---|---|---|---|---|
| `BRA rel` | `$80` | 2 | 3 (+1 page cross) | — | 65C02/816 |
| `STZ zp` | `$64` | 2 | 3 | — | 65C02/816 |
| `STZ zp,X` | `$74` | 2 | 4 | — | 65C02/816 |
| `STZ abs` | `$9C` | 3 | 4 | — | 65C02/816 |
| `STZ abs,X` | `$9E` | 3 | 5 | — | 65C02/816 |
| `PHX` | `$DA` | 1 | 3 | — | 65C02/816 |
| `PHY` | `$5A` | 1 | 3 | — | 65C02/816 |
| `PLX` | `$FA` | 1 | 4 | N,Z | 65C02/816 |
| `PLY` | `$7A` | 1 | 4 | N,Z | 65C02/816 |
| `INC A` (INA) | `$1A` | 1 | 2 | N,Z | 65C02/816 |
| `DEC A` (DEA) | `$3A` | 1 | 2 | N,Z | 65C02/816 |
| `TSB zp` | `$04` | 2 | 5 | Z | 65C02/816 |
| `TSB abs` | `$0C` | 3 | 6 | Z | 65C02/816 |
| `TRB zp` | `$14` | 2 | 5 | Z | 65C02/816 |
| `TRB abs` | `$1C` | 3 | 6 | Z | 65C02/816 |
| `BIT #imm` | `$89` | 2 | 2 | **Z only** | 65C02/816 |
| `BIT zp,X` | `$34` | 2 | 4 | N,V,Z | 65C02/816 |
| `BIT abs,X` | `$3C` | 3 | 4 (+1 page cross) | N,V,Z | 65C02/816 |
| `JMP (abs,X)` | `$7C` | 3 | 6 | — | 65C02/816 |
| `(zp)` modes (ORA/AND/EOR/ADC/STA/LDA/CMP/SBC) | $12/$32/$52/$72/$92/$B2/$D2/$F2 | 2 | 5 (ADC/SBC: 6 in decimal) | per op | 65C02/816 |
| `RMBx zp` / `SMBx zp` | `$x7` | 2 | 5 | — | WDC + Rockwell only |
| `BBRx zp,rel` / `BBSx zp,rel` | `$xF` | 3 | 5; 6 taken; 7 taken across page (see note) | — | WDC + Rockwell only |
| `WAI` | `$CB` | 1 | 3 (then waits) | — | WDC only |
| `STP` | `$DB` | 1 | 3 (then stops) | — | WDC only |

**BBR/BBS timing note (resolved):** **5 cycles not taken, 6 taken within page, 7 taken across a page** — settled by cycle-level bus capture of Rockwell silicon (hoglet's 6502 Decoder; 6502.org thread "Instruction timing of BBRx and BBSx", 2022), expected identical on WDC parts. The "always five whether taken or not" sentence in the otherwise-authoritative 65C02 tutorial was acknowledged by its author as an error under correction. Budget 5/6/7; verify on hardware only if an exotic variant matters.

### 2D. Cycle-count rules you must apply

- **Branch not taken: 2 cycles. Branch taken (same page): 3. Branch taken (crosses page): 4.** Applies to all `Bxx` conditional branches and to `BRA`.
- **Indexed reads (`abs,X`, `abs,Y`, `(zp),Y`) add +1 cycle if the effective address crosses a page boundary.** Indexed **stores** (`STA abs,X`, etc.) pay the cycle **always**, so they are constant-time.
- **Page boundary = the high byte of the address changes.** A page is 256 bytes; page n spans `256*n` … `256*n+255`.
- In tight timing loops, keep the loop body and its branch target **within one 256-byte page**, or the per-iteration cost varies.


---

## SECTION 3 — WORKSPACE CONVENTIONS

These symbols are generic RAM placeholders used by every example. They are **not** platform addresses — substitute real addresses for the target system.

```asm
ZP_PTR      EQU   $00        ; 16-bit pointer (low, high)
ZP_PTR2     EQU   $02        ; 16-bit pointer (low, high)
ZP_TMP      EQU   $04        ; 8-bit scratch
ZP_TMP2     EQU   $05        ; 8-bit scratch
ZP_COUNT    EQU   $06        ; 8-bit counter
ZP_STATE    EQU   $07        ; 8-bit flags/state

WORKBUF     EQU   $2000      ; generic RAM buffer
WORKBUF2    EQU   $2100      ; generic RAM buffer
CODEBUF     EQU   $3000      ; generic *writable* code buffer (for SMC/codegen)
TABLE       EQU   $4000      ; generic table base
```

**Zero-page ownership:** zero page is scarce and shared. A reusable routine must either (a) require caller-provided ZP symbols, or (b) save and restore any ZP bytes it touches. Always document which ZP bytes a routine owns or clobbers.

---

# PART I — ADDRESSING, DATA MOVEMENT, ZERO PAGE

### T1: Zero Page as a Register File
**What:** Treat selected zero-page bytes as pseudo-registers; zero-page access is 1 byte shorter and ~1 cycle faster than absolute, and is the only base for the indirect modes.
**Code:**
```asm
; A = A + ZP_TMP, binary mode.
ADD_TMP  CLC                 ; Hard Rule 1
         ADC   ZP_TMP        ; zp read: 3 cycles (vs 4 for absolute)
         RTS
```
**Compat:** NMOS yes · 65C02 yes · 816-8bit yes (in native mode the "direct page" can move; in emulation it behaves like zero page).
**Use when:** hot-path temporaries, pointers, counters, anything accessed repeatedly.
**Watch out:** zero page is a shared, limited resource. Zero-page **indexed** addressing (`zp,X` / `zp,Y`) wraps within page zero on every 6502-family CPU — the effective address is `(base + index) AND $FF`, so `LDA $FF,X` with X >= 1 reads `$00xx`, never `$01xx`. Never index a zero-page base expecting it to spill into page one (use an absolute base for that).
**Agent rules:** document ZP ownership; for reusable routines, require caller-provided symbols or save/restore; prefer ZP for loop counters and pointers in cycle-sensitive code.

### T2: Little-Endian Pointer Pairs
**What:** 16-bit addresses are stored low byte first, high byte second. Every indirect trick depends on this.
**Code:**
```asm
; ZP_PTR = WORKBUF
SET_PTR  LDA   #<WORKBUF     ; low byte
         STA   ZP_PTR
         LDA   #>WORKBUF     ; high byte
         STA   ZP_PTR+1
         RTS
```
**Compat:** all CPUs.
**Use when:** setting up any `(zp),Y`, `(zp,X)`, `JMP (abs)`, or 65C02 `(zp)` access.
**Watch out:** do not place a 2-byte ZP pointer at `$FF` unless you want zero-page wraparound (the high-byte fetch wraps to `$00`). Pointer increment does not auto-carry into the high byte (see T6).
**Agent rules:** name low byte `PTR`, high byte `PTR+1`; never assume high-byte carry; on NMOS keep indirect-`JMP` vectors off `$xxFF` (T8).

### T3: Streaming Through `(zp),Y`
**What:** A zero-page pointer plus Y is a moving window — the canonical array/string/stream addressing mode.
**Code:**
```asm
; Copy 256 bytes ZP_PTR -> ZP_PTR2. Y wraps $FF->$00 after 256 bytes.
COPY256  LDY   #$00
:CLOOP   LDA   (ZP_PTR),Y    ; 5 cycles (+1 if page cross)
         STA   (ZP_PTR2),Y   ; 6 cycles (store: constant-time)
         INY
         BNE   :CLOOP
         RTS
```
**Compat:** all CPUs.
**Use when:** bulk byte streams and tables up to 256 bytes.
**Watch out:** loads/arithmetic via `(zp),Y` add a cycle on page cross; stores do not. If cycle stability matters, place data so `base_low + Y` does not cross a page.
**Agent rules:** for >256 bytes, increment the pointer high byte each page (T7); state whether page crossings are possible in timing-sensitive code.

### T4: Pointer-Array Dispatch with `(zp,X)`
**What:** `(zp,X)` adds X to the zero-page operand FIRST, then fetches a 16-bit pointer from zero page. Good for small mutable pointer tables in zero page.
**Code:**
```asm
; ZP vector table at $20: low0,high0, low1,high1, ...
; X = even byte offset (entry number * 2).
ZP_VECT  EQU   $20
LOADVEC  LDA   (ZP_VECT,X)   ; fetch via selected pointer
         RTS
```
**Compat:** all CPUs.
**Use when:** the vector table must be mutable, fast, and small enough for zero page.
**Watch out:** X is a **byte** offset, not an entry number. Convert with `ASL`. NMOS `(zp,X)` wraps inside zero page (`($FF,X)` reads the high byte from `$00`).
**Agent rules:** `ASL A` to convert entry# → byte offset; on 65C02 prefer `JMP (TABLE,X)` (T21) for code dispatch outside zero page.

### T5: 65C02 True Zero-Page Indirect `(zp)`
**What:** Non-indexed zero-page indirect — frees X and Y when no index is needed.
**Code:**
```asm
; 65C02/816 only.
LOADIND  LDA   (ZP_PTR)      ; 5 cycles
         RTS
```
**Compat:** **NMOS no** · 65C02 yes · 816-8bit yes.
**Use when:** pointer-based scalar access without burning Y as a zero index.
**Watch out:** this is a major portability divider (Hard Rule 4).
**Agent rules — FALLBACK (NMOS):**
```asm
LOADNM   LDY   #$00
         LDA   (ZP_PTR),Y
         RTS
```
Emit `(zp)` only when the target is 65C02/816; prefer it over `LDY #0 / (zp),Y` only when Y must be preserved.

### T6: Increment a 16-Bit Pointer
**What:** There is no 16-bit increment; carry manually.
**Code:**
```asm
INCPTR   INC   ZP_PTR        ; low byte
         BNE   :DONE
         INC   ZP_PTR+1      ; carry into high byte
:DONE    RTS
```
**Compat:** all CPUs.
**Use when:** walking variable-length streams one byte at a time.
**Watch out:** `INC zp` sets N and Z; save/restore P with `PHP`/`PLP` if flags must survive (costs stack + cycles). Decrementing a 16-bit value is trickier because `DEC` sets no borrow — test the low byte for zero before decrementing the high byte, or use the `SBC` form.
**Agent rules:** prefer Y-indexing within a page and pointer-increment only at page boundaries; state flag clobbers.

### T7: Copy Arbitrary Length (Page Counter)
**What:** Y handles the inner 256-byte page; an outer counter handles whole pages.
**Code:**
```asm
; Copy ZP_COUNT pages (256 bytes each) ZP_PTR -> ZP_PTR2. 0 means copy nothing.
COPYPAG  LDA   ZP_COUNT
         BEQ   :DONE
:PAGE    LDY   #$00
:BYTE    LDA   (ZP_PTR),Y
         STA   (ZP_PTR2),Y
         INY
         BNE   :BYTE
         INC   ZP_PTR+1
         INC   ZP_PTR2+1
         DEC   ZP_COUNT
         BNE   :PAGE
:DONE    RTS
```
**Compat:** all CPUs.
**Use when:** bulk copy / table init when source and destination do not overlap.
**Watch out:** this is memcpy-like, NOT memmove — it does not handle overlap. For overlap, copy backward when the destination lies inside the source range.
**Agent rules:** for exact page counts use this; for arbitrary byte counts, add a low-count tail loop; never call it "memmove."

### T8: The NMOS `JMP ($xxFF)` Bug
**What:** On NMOS, `JMP ($12FF)` reads the low byte from `$12FF` and the high byte from `$1200` (not `$1300`). Fixed on 65C02/816.
**Code:**
```asm
; Portable-safe rule: never place an indirect-JMP vector at $xxFF.
         JMP   (VECTOR)      ; safe only if VECTOR's low byte is not at $xxFF
```
**Compat:** bug on **NMOS** · fixed on 65C02 (at +1 cycle) · fixed on 816.
**Use when:** never intentionally, except deliberate NMOS-only size tricks.
**Watch out:** classic "worked on my emulator" trap; many emulators model it inconsistently.
**Agent rules:** never generate an indirect-`JMP` vector at `$xxFF`; if deliberately exploiting it, label `NMOS_ONLY_JMP_WRAP` and require explicit permission; for 65C02 dispatch prefer `JMP (TABLE,X)` (T21).


---

# PART II — BRANCHES, FLOW CONTROL, CYCLE DISCIPLINE

### T9: Branch Chaining for Long Conditional Branches
**What:** Branches reach only about -128…+127 bytes. To branch farther, branch over a `JMP` using the inverted condition.
**Code:**
```asm
; "Long branch if Z set" — invert to BNE around the JMP.
         BNE   :SKIP         ; if Z clear, skip the long jump
         JMP   FAR_TARGET    ; taken only when Z set
:SKIP    ; falls through here when Z clear
```
**Compat:** all CPUs.
**Use when:** the target may be out of branch range.
**Watch out:** the taken and not-taken paths now differ in cycles; matters for cycle-counted code.
**Agent rules:** use inverted condition around `JMP`; annotate timing if cycle-sensitive.

### T10: Branch-Always Idioms
**What:** Unconditional relative branch. `BRA` on 65C02; on NMOS use `JMP` or a deliberately forced flag.
**Code:**
```asm
; 65C02/816:
         BRA   TARGET        ; 3 cycles, position-independent

; NMOS portable:
         JMP   TARGET

; NMOS forced-flag (only if a flag state is deliberately established):
         CLV                 ; V is untouched by most instructions
         BVC   TARGET        ; always taken
```
**Compat:** `BRA` 65C02/816 only · `JMP`/forced-flag all CPUs.
**Use when:** `BRA` for compact, relocatable nearby jumps on 65C02; `JMP` for portable code.
**Watch out:** do not fake `BRA` with `BNE`/`BEQ` on "whatever Z happens to be" — only on a flag you just set on purpose. `CLV`/`BVC` is the cleanest forced branch because almost nothing else touches V.
**Agent rules:** plain 6502 → `JMP`; 65C02 → `BRA`; never rely on incidental flag state.

### T11: Equalize Branch Timing
**What:** Make both paths cost the same number of cycles by padding, so external timing is deterministic.
**Code:**
```asm
; Goal: both paths reach :JOIN at 7 cycles (assumes BEQ does not cross a page).
; False path: BEQ not taken (2) + NOP (2) + JMP (3) = 7
; True  path: BEQ taken     (3) + NOP (2) + NOP (2) = 7
         BEQ   :TAKEN
         NOP
         JMP   :JOIN
:TAKEN   NOP
         NOP
:JOIN    RTS
```
**Compat:** all CPUs (`BRA` could replace the `JMP` on 65C02, but `BRA` is also relative — keep it on-page if timing matters).
**Use when:** bit-banged protocols, wait-state windows, deterministic benchmark loops.
**Watch out:** easy to get wrong; a page-crossing branch breaks the arithmetic. Assert code placement.
**Agent rules:** include a per-path cycle table; keep cycle-stable code within one page; prefer straight-line code or table lookups when exact timing is required.

### T12: Page-Align Timing-Critical Loops
**What:** A taken branch crossing a page costs +1 cycle. Keep the loop body and its branch target in the same 256-byte page.
**Code:**
```asm
; Place LOOP and its BNE within one page so each taken iteration is exactly 5 cycles.
LOOP     DEX                 ; 2
         BNE   LOOP          ; 3 taken (same page); final not-taken = 2
         RTS
```
**Compat:** all CPUs.
**Use when:** stable loops, predictable delays, cycle-counted routines.
**Watch out:** assembler/linker placement can silently break the assumption.
**Agent rules:** add build-time page assertions if the assembler supports them; in portable snippets, document "must not cross page"; avoid exact-timing reliance unless interrupts are disabled or accounted for.

### T13: Cycle-Counted Delay Loops
**What:** Simple loop delays, plus a precise 16-bit delay formula.
**Code:**
```asm
; Simple: total ~= (N-1)*5 + 4 (+ RTS). X=0 means 256 iterations.
DELAYX   DEX                 ; 2
         BNE   DELAYX        ; 3 taken / 2 final
         RTS

; Precise (Bruce Clark). A:Y = 16-bit value V. Delay = 9*V + 8 cycles.
; Range 8..589832, resolution 9, assuming BCS does not cross a page.
DELAY9   CPY   #1
         DEY
         SBC   #0
         BCS   DELAY9
```
**Compat:** all CPUs.
**Use when:** generic wait loops, pacing, calibration scaffolding.
**Watch out:** interrupts add jitter; page crossing alters timing; X=0 means 256, not 0.
**Agent rules:** state whether X=0 means 256; include entry/exit overhead in "exact" delays; if jitter-intolerant, mask IRQ but note NMI may still fire.

### T14: Duff-Style Entry into Unrolled Code
**What:** Enter an unrolled, fall-through block at a computed point to handle small counts without a per-byte branch. (The "jump into an unrolled loop" idea predates Duff's device, which is a C construct.)
**Code:**
```asm
; Copy 1..4 bytes WORKBUF -> WORKBUF2. A = count 1..4.
; Count 4 copies bytes 3,2,1,0; count 3 copies 2,1,0; etc.
COPY1_4  CMP   #$04
         BEQ   :FOUR
         CMP   #$03
         BEQ   :THREE
         CMP   #$02
         BEQ   :TWO
         JMP   :ONE          ; assume count 1 if not 2..4
:FOUR    LDA   WORKBUF+3
         STA   WORKBUF2+3
:THREE   LDA   WORKBUF+2
         STA   WORKBUF2+2
:TWO     LDA   WORKBUF+1
         STA   WORKBUF2+1
:ONE     LDA   WORKBUF
         STA   WORKBUF2
         RTS
```
**Compat:** all CPUs.
**Use when:** small fixed maximum counts where per-iteration branch overhead dominates.
**Watch out:** code size grows fast; the fall-through order must match the intended byte order.
**Agent rules:** use only for small fixed bounds; label the fall-through intentionally.

### T15: Tail Calls with `JMP`
**What:** When a routine ends by calling another and doing nothing after, replace `JSR x / RTS` with `JMP x`.
**Code:**
```asm
; Instead of:  FOO  JSR BAR / RTS
FOO2     JMP   BAR           ; BAR's RTS returns to FOO2's caller
```
**Compat:** all CPUs.
**Use when:** the final action is a call.
**Watch out:** valid only when nothing must happen after `BAR` returns (no cleanup, register restore, or stack fix-up pending).
**Agent rules:** use `JMP` for tail calls; do not tail-call if work remains after the callee.


---

# PART III — SELF-MODIFYING CODE (SMC)

**Global SMC caveats (apply to every technique in this part):** requires writable code memory — **never in ROM**; **not re-entrant** — an interrupt or recursion between a patch and its use corrupts it (Hard Rule 10); makes disassembly/debugging harder. Classic 65xx has a unified bus and no instruction cache, so no cache-coherency issue exists (unlike modern CPUs). Always ship a non-SMC fallback for portable/library code.

### T16: Patch an Immediate Operand
**What:** Use an instruction's immediate operand byte as a fast variable. Cleanest SMC form — the opcode stays put.
**Code:**
```asm
; The byte at LOADIMM+1 is the value LDA loads. Change it via STA LOADIMM+1.
LOADIMM  LDA   #$00          ; operand byte at LOADIMM+1
         RTS
SETIMM   STA   LOADIMM+1     ; patch the operand
         RTS
```
**Compat:** NMOS/65C02/816 (writable memory required).
**Use when:** loop bounds, masks, compare values, constants read every iteration of a hot loop.
**Agent rules:** prefer operand patching over opcode patching; name patch points explicitly; do not patch code reachable from an interrupt unless the write is atomic; never in ROM-bound generic routines. **FALLBACK:** keep the variable in zero page and read it normally.

### T17: Patch an Absolute Address Operand
**What:** Modify the low/high operand bytes of an absolute instruction to synthesize a computed address without indirect-addressing overhead.
**Code:**
```asm
GETABS   LDA   $FFFF         ; operand low at GETABS+1, high at GETABS+2
         RTS
SETABS   LDA   ZP_PTR
         STA   GETABS+1      ; patch low
         LDA   ZP_PTR+1
         STA   GETABS+2      ; patch high
         RTS
```
**Compat:** all CPUs (writable memory).
**Use when:** hot loops where `LDA abs` beats `LDA (zp),Y`, or the index registers are already busy.
**Watch out:** a two-byte address patch is **not atomic** — an interrupt between the low and high writes that calls the patched code sees a torn address.
**Agent rules:** patch with interrupts masked if the routine is IRQ-reachable; patch low then high in a documented order; avoid in re-entrant routines.

### T18: Patch an Opcode to Toggle Behavior
**What:** Swap an instruction for another of the **same length** to switch behavior at runtime. Toggling a call on/off: `JSR abs` ($20) ↔ `BIT abs` ($2C), both 3 bytes. `BIT abs` reads the operand address and sets flags but does not call.
**Code:**
```asm
CALLPT   JSR   WORK          ; opcode byte at CALLPT
         RTS
ENABLE   LDA   #$20          ; JSR abs
         STA   CALLPT
         RTS
DISABLE  LDA   #$2C          ; BIT abs (3 bytes, does not call)
         STA   CALLPT
         RTS
WORK     INC   ZP_STATE
         RTS
```
**Compat:** all CPUs (`BIT abs` exists on NMOS).
**Use when:** fast feature gates, instrumentation toggles, conditional hooks.
**Watch out:** `BIT abs` changes N, V, Z based on memory/A — not transparent if flags matter at that site.
**Agent rules:** only swap opcodes of equal length (or manage the leftover bytes); account for the replacement's flag side effects; prefer operand patching unless opcode patching gives a real win.

### T19: Generate Small Code Stubs
**What:** Build a short, specialized instruction sequence in RAM instead of interpreting a data structure repeatedly.
**Code:**
```asm
; Build at CODEBUF:  LDA #ZP_TMP_value ; STA WORKBUF ; RTS
GENSTUB  LDA   #$A9          ; LDA #imm opcode
         STA   CODEBUF
         LDA   ZP_TMP
         STA   CODEBUF+1     ; the immediate value
         LDA   #$8D          ; STA abs opcode
         STA   CODEBUF+2
         LDA   #<WORKBUF
         STA   CODEBUF+3
         LDA   #>WORKBUF
         STA   CODEBUF+4
         LDA   #$60          ; RTS opcode
         STA   CODEBUF+5
         RTS
```
**Compat:** all CPUs (executable RAM required).
**Use when:** specialized interpreters, threaded engines, dispatch-dominated table code.
**Watch out:** generated code must be inspectable and testable; this is the highest-risk SMC form.
**Agent rules:** use named opcode constants in production, not bare magic numbers; include a test that byte-checks the generated stub; do not generate code when normal indexed/indirect addressing is fast enough.

---

# PART IV — STACK TECHNIQUES

### T20: `RTS` as a Computed Jump (the "RTS trick")
**What:** `RTS` pulls a 16-bit address, adds 1, and jumps there. Push `target-1` (high byte first) to dispatch via the stack — re-entrant, needs no fixed RAM pointer. Works on NMOS, unlike `JMP (abs,X)`.
**Code:**
```asm
; X = entry number 0..N-1. Split low/high tables of (TARGET-1).
DISPATCH LDA   JTHI,X        ; push HIGH byte first
         PHA
         LDA   JTLO,X        ; then LOW byte (RTS pulls low first)
         PHA
         RTS                 ; "returns" into the selected routine
JTLO     DFB   <(HAND0-1),<(HAND1-1),<(HAND2-1)
JTHI     DFB   >(HAND0-1),>(HAND1-1),>(HAND2-1)
HAND0    RTS
HAND1    RTS
HAND2    RTS
```
**Compat:** all CPUs.
**Use when:** jump tables on NMOS; any time you want stack-based, re-entrant dispatch.
**Watch out:** the stack must stay balanced; split low/high tables (indexed by entry number) scale to 256 entries. Tradeoff vs `JMP (abs,X)`: typically a few bytes smaller but ~1 cycle slower, and it is re-entrant. Do not leave a half-pushed address on the stack across an interruptible region.
**Agent rules:** push high then low; store `target-1`; on 65C02 prefer `JMP (TABLE,X)` (T21) when entries can be absolute; mask IRQ (or guarantee no interrupt path re-enters) while the address is half-formed.

### T21: 65C02 `JMP (abs,X)` Jump Table
**What:** Indexed absolute indirect jump — reads the vector from `TABLE+X`. The clean 65C02 dispatch primitive.
**Code:**
```asm
; 65C02/816 only. Convert entry number -> even byte offset with ASL.
         LDA   ZP_STATE
         ASL                 ; entry# * 2
         TAX
         JMP   (JTABLE,X)    ; 6 cycles
JTABLE   DA    HAND0,HAND1,HAND2   ; absolute addresses (NO -1, unlike the RTS trick)
```
**Compat:** **NMOS no** · 65C02 yes · 816 yes.
**Use when:** default 65C02 dispatch, outside zero page, no stack manipulation.
**Watch out:** X is a byte offset, not an entry number; `ASL` to convert. Note the table stores **actual** addresses (no `-1`), unlike T20.
**Agent rules — FALLBACK (NMOS):** use the RTS trick (T20). Ensure the table does not straddle a boundary unexpectedly.

### T22: Stack as Scratch Storage
**What:** Use the stack to save A (or X/Y) briefly while reusing the register.
**Code:**
```asm
; Save A while modifying X (NMOS-compatible):
SAVE_AX  PHA
         TXA
         PHA
         ; ... work using A and X ...
         PLA
         TAX
         PLA                 ; restore A
         RTS

; 65C02/816 — direct:
SAVE_XY  PHX
         PHY
         ; ... work ...
         PLY
         PLX
         RTS
```
**Compat:** all CPUs (`PHX/PHY/PLX/PLY` are 65C02/816 only).
**Use when:** the stack is faster/smaller than absolute saves; brief register juggling.
**Watch out:** nested routines and interrupts share the same stack; restore in exact reverse order.
**Agent rules:** restore reverse-order; document stack depth; keep interrupt-handler stack use bounded.

### T23: Read Caller-Pushed Arguments with `TSX`
**What:** Inspect bytes the caller pushed (above the return address) using `TSX` + absolute-indexed addressing into page 1.
**Code:**
```asm
; Caller:  LDA #$55 / PHA / JSR USEARG / PLA   (discard arg after)
; On entry, nothing pushed by the callee yet:
USEARG   TSX
         LDA   $0103,X       ; the caller-pushed byte (see offset note)
         STA   ZP_TMP
         RTS
```
*(Offset: after entry, X = S. Return-low is at `$0100+S+1`, return-high at `+2`, the pushed arg at `+3`. `$0103,X` = `$0103+S` = `$0100+S+3` = the argument.)*
**Compat:** all CPUs.
**Use when:** small calling conventions, especially when zero page must remain untouched.
**Watch out:** offsets depend on exactly what has been pushed since entry. If the callee pushes anything before `TSX`, the offsets shift.
**Agent rules:** do `TSX` before pushing callee-saved values (or adjust offsets); define whether the caller or callee cleans the arguments.

### T24: Inline Data After `JSR`
**What:** A routine reads its return address, treats the bytes after the `JSR` as inline data, then advances the return address past them so `RTS` skips the data.
**Code:**
```asm
; Caller:  JSR GETBYTE / DFB $7E / ...   (A = $7E on return)
; JSR pushes (inline_addr - 1). Add 1 to point at the inline byte.
GETBYTE  TSX
         CLC
         LDA   $0101,X       ; return low  (= inline_addr - 1, low)
         ADC   #$01
         STA   ZP_PTR
         LDA   $0102,X       ; return high
         ADC   #$00
         STA   ZP_PTR+1      ; ZP_PTR = inline_addr
         LDY   #$00
         LDA   (ZP_PTR),Y    ; fetch the inline byte
         PHA                 ; hold it
         LDA   ZP_PTR        ; write inline_addr back as the return address;
         STA   $0101,X       ; RTS adds 1 -> resumes AFTER the inline byte
         LDA   ZP_PTR+1
         STA   $0102,X
         PLA
         RTS
```
**Compat:** all CPUs.
**Use when:** compact bytecode interpreters, embedded constants, immediate string/data parameters.
**Watch out:** manipulates the return address (confuses debuggers/stack tracers); not re-entrant if it uses shared ZP scratch and can interrupt itself; the 256-byte stack limits nesting depth.
**Agent rules:** document how many bytes are consumed; for multi-byte inline data, add the count to the stacked return address; an alternative is a static parameter block whose address is passed in A/X.

### T25: `RTI` for Full Status + PC Transfer
**What:** `RTI` pulls processor status, then PC (and does **not** add 1, unlike `RTS`). Hand-stacking P + target PC gives a computed transfer that also restores flags.
**Code:**
```asm
; Push target HIGH, target LOW, then status. RTI pulls status, low, high.
; NOTE: target is exact (NOT target-1).
GO_RTI   PHP
         PLA
         STA   ZP_TMP        ; capture current status
         LDA   #>TARGET
         PHA                 ; PC high
         LDA   #<TARGET
         PHA                 ; PC low
         LDA   ZP_TMP
         PHA                 ; status
         RTI
TARGET   RTS
```
**Compat:** all CPUs.
**Use when:** context switches, tiny schedulers, coroutines, returning from synthetic interrupts.
**Watch out:** status includes I (interrupt disable) and D (decimal); on 65C02 D handling around interrupts differs from NMOS. Easy to get the stack order wrong — test it.
**Agent rules:** do not emit RTI-transfer code unless explicitly requested; prefer `JMP`/`RTS` unless P restoration is required; verify byte order with a test (Part X).


---

# PART V — ARITHMETIC, FLAGS, BCD

### T26: Multi-Byte Binary Addition / Subtraction
**What:** Propagate carry (add) or borrow (subtract) through bytes, low to high.
**Code:**
```asm
; 16-bit add: ZP_PTR = ZP_PTR + ZP_PTR2
ADD16    CLC                 ; Hard Rule 1
         LDA   ZP_PTR
         ADC   ZP_PTR2
         STA   ZP_PTR
         LDA   ZP_PTR+1
         ADC   ZP_PTR2+1
         STA   ZP_PTR+1
         RTS
; 16-bit subtract: identical but SEC first and SBC the bytes in the same order.
```
**Compat:** all CPUs.
**Use when:** pointer math, counters, fixed-point arithmetic.
**Watch out:** carry out of the top byte = overflow beyond the width; preserve it if it matters.
**Agent rules:** `CLC` before add, `SEC` before subtract; state whether the final carry is meaningful.

### T27: 16-Bit Increment / Decrement
**What:** No native 16-bit inc/dec; sequence them.
**Code:**
```asm
; 16-bit increment of ZP_PTR
INC16    INC   ZP_PTR
         BNE   :DONE
         INC   ZP_PTR+1
:DONE    RTS

; 16-bit decrement of ZP_PTR (DEC sets no borrow, so test the low byte first)
DEC16    LDA   ZP_PTR
         BNE   :SKIP
         DEC   ZP_PTR+1
:SKIP    DEC   ZP_PTR
         RTS
```
**Compat:** all CPUs.
**Use when:** counters, pointers, loop variables wider than 8 bits.
**Watch out:** decrement order matters; to add/subtract a constant >1, use the `ADC`/`SBC` form with carry propagation.
**Agent rules:** state flag clobbers (`INC`/`DEC` set N,Z).

### T28: Unsigned Comparison
**What:** `CMP` sets carry when A ≥ operand (unsigned).
**Code:**
```asm
         CMP   ZP_TMP
         BCS   :GE           ; A >= ZP_TMP  (unsigned)
         ; A < ZP_TMP here
:GE
```
**Compat:** all CPUs.
**Use when:** bounds checks, table indices, buffer limits.
**Watch out:** `CMP` does **not** affect V. `BCC` = unsigned less-than, `BCS` = unsigned greater-or-equal, `BEQ` = equal. Do not use N alone for comparison.
**Agent rules:** use carry for unsigned decisions; for signed, see T29.

### T29: Signed Comparison (the N⊕V trick)
**What:** A signed comparison result is **N EOR V**, not N alone. Use `SBC` (which affects V; `CMP` does not), then fold V into the sign.
**Code:**
```asm
; Signed: is A < NUM ?  (binary mode only)
         SEC
         SBC   NUM           ; affects N and V
         BVC   :NOOV         ; if V clear, N already correct
         EOR   #$80          ; fold V into the sign bit
:NOOV    ; N set  => signed A < NUM ;  N clear => signed A >= NUM
```
**Compat:** all CPUs.
**Use when:** comparing signed bytes.
**Watch out:** this trick is **invalid in decimal mode**. An alternative folds the signed result into carry (`BVS / EOR #$80 / ASL`) so `BCC`/`BCS` work for signed values.
**Agent rules:** comment the cleverness; ensure binary mode; do not use after a decimal operation.

### T30: BCD Mode Hygiene
**What:** `SED` makes `ADC`/`SBC` do packed BCD ($00–$99 per byte); `CLD` returns to binary.
**Code:**
```asm
; $45 + $27 = $72 (BCD). C set if the result exceeds 99.
BCDADD   SED
         CLC
         LDA   #$45
         ADC   #$27          ; A = $72
         CLD                 ; ALWAYS restore binary mode
         RTS
```
**Compat:** result arithmetic works on all CPUs, but **flag validity differs**: on **NMOS** only **C** is meaningful after a decimal `ADC`/`SBC`; on **65C02/816** C, N, Z are valid (the +1 cycle recomputes N/Z from the corrected result) — but **V is the same binary-derived value on every CPU**, never a BCD overflow flag (B. Clark, 6502.org).
**Use when:** human-readable decimal counters, scorekeeping, packed-decimal display.
**Watch out:** D is **undefined at NMOS power-on** — `CLD` in init. NMOS does **not** clear D on interrupt — `CLD` early in handlers (Hard Rule 9). 65C02/816 clear D on every interrupt/BRK. Do not branch on N/Z/V after an NMOS decimal op.
**Agent rules:** `CLD` at init and at interrupt entry; wrap decimal routines so they exit with D clear; never assume D survives an interrupt.

### T31: Multi-Byte BCD Addition
**What:** BCD carry propagates exactly like binary carry; each byte is two decimal digits.
**Code:**
```asm
; 4-digit BCD: ZP_PTR(high:low) += ZP_PTR2(high:low)
BCD16    SED
         CLC
         LDA   ZP_PTR
         ADC   ZP_PTR2
         STA   ZP_PTR
         LDA   ZP_PTR+1
         ADC   ZP_PTR2+1
         STA   ZP_PTR+1
         CLD
         RTS
```
**Compat:** all CPUs (flag-validity caveats as in T30).
**Use when:** decimal counters larger than 99.
**Watch out:** input nibbles must be valid BCD (0–9) for portable meaning; invalid BCD is a test-suite topic, not an application technique.
**Agent rules:** validate/constrain BCD inputs; exit with D clear; treat C as decimal carry-out.

### T32: Nibble → ASCII Hex (two valid methods)
**What:** Convert a 4-bit value (0–15) to its ASCII hex character. Method A uses binary-mode compare-and-add; Method B uses decimal mode. Both are correct — pick by whether you are already in decimal mode.
**Code:**
```asm
; --- Method A: binary mode (D must be clear). Carry-driven. ---
NYBHEXA  AND   #$0F
         CMP   #$0A
         BCC   :DIGIT        ; 0..9 -> add $30 with C clear
         ADC   #$06          ; C=1 here: A + 6 + 1 = A + 7  (maps A..F)
:DIGIT   ADC   #$30          ; C is clear on both paths here -> '0'..'9' / 'A'..'F'
         RTS

; --- Method B: decimal mode. ---
NYBHEXB  SED
         CLC
         ADC   #$90          ; $90..$99 (C=0) or wraps (C=1) for A..F
         ADC   #$40          ; -> $30..$39 ('0'..'9') or $41..$46 ('A'..'F')
         CLD
         RTS
```
**Compat:** all CPUs.
**Use when:** debug/monitor output, binary-to-text.
**Watch out:** Method A relies on carry state after `CMP #$0A` and assumes **binary** mode; Method B assumes the input nibble is already isolated (0–15) and leaves D clear on exit.
**Agent rules:** comment carry-dependent steps; assert/establish the required D state before either method.

---

# PART VI — MATH ROUTINES

*All routines here have been verified exhaustively in a 6502 simulator (py65) over their full input ranges: the unsigned MUL8 and quarter-square T34 against all 65,536 operand pairs; DIV8 against all 65,280 dividend/divisor pairs; BIN2BCD over 0–255; BCD2BIN (T37) over 0–9999; and the signed wrappers SMUL8 (T33S) and SDIV8 (T35S) against all signed operand pairs. Unsigned routines assume binary mode (D=0). The signed wrappers take the result sign from EOR of the operands and run the magnitudes through the unsigned primitives (`LSR`/`ROR` are not sign-preserving, which is why magnitude-then-sign is the right structure).*

### T33: 8×8 → 16 Unsigned Multiply (shift-and-add)
**What:** Classic right-shifting multiply. ~120–150 cycles depending on operands.
**Code:**
```asm
; In:  ZP_TMP  = multiplicand,  ZP_TMP2 = multiplier
; Out: ZP_PTR  = product low,   ZP_PTR+1 = product high
; Clobbers A, X, flags. (ZP_PTR low needs no init: 8 RORs overwrite all 8 bits.)
MUL8     LDA   #$00
         STA   ZP_PTR+1      ; product high = 0
         LDX   #$08
:ROT     LSR   ZP_TMP2       ; multiplier >> 1, LSB -> C
         BCC   :NOADD
         CLC
         ADC   ZP_TMP        ; product high += multiplicand
:NOADD   ROR   A
         ROR   ZP_PTR        ; shift result bit into product low
         DEX
         BNE   :ROT
         STA   ZP_PTR+1      ; final product high
         RTS
```
**Compat:** all CPUs.
**Use when:** general 8×8 multiply.
**Watch out:** binary mode only; multiplier in `ZP_TMP2` is destroyed.
**Agent rules:** for small fixed multipliers, prefer shifts/adds (e.g. ×10 = `(x<<3)+(x<<1)`); for a bounded range, prefer a table of squares (T34).

### T34: Multiply via Table of Squares (quarter-square)
**What:** Use the identity `a*b = floor((a+b)^2 / 4) - floor((a-b)^2 / 4)`. `(a+b)` and `(a-b)` always share parity, so the floors are exact and the identity holds for **all** unsigned `a,b`. With a precomputed table of `floor(n^2/4)`, an 8×8 multiply becomes two table lookups plus a 16-bit subtract — much faster than shift-and-add when multiplies are hot.
**Code:**
```asm
; In:  ZP_TMP = a, ZP_TMP2 = b
; Out: ZP_PTR = product low, ZP_PTR+1 = product high
; Scratch: ZP_PTR2, ZP_STATE, A, X, Y.
; Tables (PAGE-ALIGNED, 512 bytes each, generated at assemble time):
;   SQLO[n] = <(n*n/4),  SQHI[n] = >(n*n/4),  for n = 0..510
;   SQHI must sit exactly $200 above SQLO (e.g. SQLO=$4000, SQHI=$4200).
; sum = a+b is 9 bits (0..510); diff = |a-b| is 8 bits (0..255).
MUL_QS   LDA   #>SQLO         ; build a pointer to SQLO[sum]
         STA   ZP_PTR+1
         CLC
         LDA   ZP_TMP         ; a
         ADC   ZP_TMP2        ; + b  -> A = sum low, C = sum bit 8
         STA   ZP_PTR         ; low byte (valid because SQLO is page-aligned)
         LDA   ZP_PTR+1
         ADC   #$00           ; fold bit 8 into the high byte
         STA   ZP_PTR+1
         LDY   #$00
         LDA   (ZP_PTR),Y     ; SQLO[sum]
         STA   ZP_PTR2        ; stash sum-square low
         LDA   ZP_PTR+1
         CLC
         ADC   #$02           ; +$200 moves the pointer into the SQHI table
         STA   ZP_PTR+1
         LDA   (ZP_PTR),Y     ; SQHI[sum]
         STA   ZP_STATE       ; stash sum-square high
         SEC                  ; diff = |a - b|  -> X
         LDA   ZP_TMP
         SBC   ZP_TMP2
         BCS   :DPOS
         SEC
         LDA   ZP_TMP2
         SBC   ZP_TMP
:DPOS    TAX                  ; X = |a-b| (0..255 -> 8-bit index, no carry needed)
         SEC                  ; product = SQ[sum] - SQ[diff]
         LDA   ZP_PTR2
         SBC   SQLO,X
         STA   ZP_PTR         ; product low
         LDA   ZP_STATE
         SBC   SQHI,X
         STA   ZP_PTR+1       ; product high
         RTS
```
**Compat:** all CPUs.
**Use when:** many multiplies over the full 8-bit range and you can spare the ~1 KB of tables.
**Watch out:** the tables **must be page-aligned**, and `SQHI` **must be exactly $200 above `SQLO`** — the routine depends on both facts. `diff` uses `|a-b|` because the table is symmetric in n. For operands bounded well below 255, both tables can be shrunk.
**Agent rules:** generate `SQLO`/`SQHI` at assemble time as `floor(n*n/4)` for n=0..510; use only when the table fits and multiplies are hot, otherwise use T33. **Verified exhaustively over all 65,536 operand pairs.**

### T35: Divide and Multiply by Powers of Two; 8/8 Unsigned Divide
**What:** ×2 = `ASL`/`ROL` chain; ÷2 = `LSR`/`ROR` chain. General division is shift-and-subtract.
**Code:**
```asm
; 8-bit / 8-bit unsigned. In: ZP_TMP = dividend, ZP_TMP2 = divisor.
; Out: ZP_TMP = quotient (in place), A = remainder. Clobbers X, flags.
DIV8     LDA   #$00          ; remainder = 0
         LDX   #$08
:LOOP    ASL   ZP_TMP        ; dividend << 1, MSB -> C
         ROL   A             ; bring bit into remainder
         CMP   ZP_TMP2       ; remainder >= divisor?
         BCC   :SKIP
         SBC   ZP_TMP2       ; yes: subtract (C stays set)
         INC   ZP_TMP        ; set this quotient bit
:SKIP    DEX
         BNE   :LOOP
         RTS
```
**Compat:** all CPUs.
**Use when:** general 8/8 divide; use bare `LSR`/`ROR` for ÷2^n.
**Watch out:** binary mode; divide by zero is undefined (guard the caller). Dividend is destroyed (becomes the quotient).
**Agent rules:** guard divisor ≠ 0; for ÷2^n prefer shift chains.

### T36: Binary → Decimal (via decimal mode)
**What:** Build the decimal representation by shifting binary bits in MSB-first and doubling a BCD accumulator in decimal mode — the hardware does the digit correction, so no per-nibble "add 3" logic is needed.
**Code:**
```asm
; In:  ZP_TMP = binary 0..255
; Out: ZP_PTR = packed BCD (tens:units), ZP_PTR+1 = hundreds (high byte)
BIN2BCD  SED
         LDA   #$00
         STA   ZP_PTR
         STA   ZP_PTR+1
         LDX   #$08
:LOOP    ASL   ZP_TMP        ; next binary bit (MSB first) -> C
         LDA   ZP_PTR        ; BCD_low = BCD_low*2 + C   (decimal)
         ADC   ZP_PTR        ; (LDA/STA preserve carry between the two ADCs)
         STA   ZP_PTR
         LDA   ZP_PTR+1      ; BCD_high = BCD_high*2 + carry  (decimal)
         ADC   ZP_PTR+1
         STA   ZP_PTR+1
         DEX
         BNE   :LOOP
         CLD
         RTS
```
**Compat:** all CPUs.
**Use when:** displaying a binary value as decimal digits.
**Watch out:** decimal mode; to emit ASCII, split each BCD nibble and OR with `$30`.
**Agent rules:** restore D with `CLD`; extend the accumulator width for inputs >255.

### T37: Decimal → Binary (packed BCD, multi-byte)
**What:** Reverse of T36. Process BCD digits most-significant first, accumulating `binary = binary*10 + digit` (Horner's method). Converts up to 4 packed-BCD digits (0–9999) into a 16-bit binary result.
**Code:**
```asm
; In:  ZP_PTR   = packed BCD tens:units
;      ZP_PTR+1 = packed BCD thousands:hundreds   (value 0..9999)
; Out: ZP_PTR2  = binary low,  ZP_PTR2+1 = binary high
; Scratch: ZP_TMP, ZP_TMP2, A. (Input ZP_PTR / ZP_PTR+1 is preserved.)
BCD2BIN  LDA   #$00
         STA   ZP_PTR2
         STA   ZP_PTR2+1
         LDA   ZP_PTR+1       ; thousands:hundreds
         LSR
         LSR
         LSR
         LSR                  ; A = thousands
         JSR   MUL10ADD
         LDA   ZP_PTR+1
         AND   #$0F           ; A = hundreds
         JSR   MUL10ADD
         LDA   ZP_PTR         ; tens:units
         LSR
         LSR
         LSR
         LSR                  ; A = tens
         JSR   MUL10ADD
         LDA   ZP_PTR
         AND   #$0F           ; A = units
         JSR   MUL10ADD
         RTS

; acc(ZP_PTR2:+1) = acc*10 + A (digit 0..9).  acc*10 = ((acc*4) + acc) * 2.
MUL10ADD PHA                  ; save digit
         LDA   ZP_PTR2        ; copy acc -> ZP_TMP:ZP_TMP2
         STA   ZP_TMP
         LDA   ZP_PTR2+1
         STA   ZP_TMP2
         ASL   ZP_PTR2        ; acc <<= 2   (acc * 4)
         ROL   ZP_PTR2+1
         ASL   ZP_PTR2
         ROL   ZP_PTR2+1
         CLC                  ; acc += copy (acc * 5)
         LDA   ZP_PTR2
         ADC   ZP_TMP
         STA   ZP_PTR2
         LDA   ZP_PTR2+1
         ADC   ZP_TMP2
         STA   ZP_PTR2+1
         ASL   ZP_PTR2        ; acc <<= 1   (acc * 10)
         ROL   ZP_PTR2+1
         PLA                  ; digit
         CLC
         ADC   ZP_PTR2
         STA   ZP_PTR2
         LDA   ZP_PTR2+1
         ADC   #$00
         STA   ZP_PTR2+1
         RTS
```
**Compat:** all CPUs.
**Use when:** parsing packed-BCD (or ASCII-decimal) input into a binary value.
**Watch out:** binary mode — this is binary arithmetic on digit values, so do **not** `SED`. For an ASCII decimal string, mask each character with `#$0F` to get the digit and call `MUL10ADD` once per character. Extend the accumulator beyond 16 bits for inputs >9999.
**Agent rules:** validate that digits are 0–9; size the accumulator for the expected range. **Verified exhaustively over all values 0–9999.**

### T33S: Signed 8×8 → 16 Multiply (wrapper around T33)
**What:** Signed product. Take the result sign from `a EOR b`, multiply the magnitudes with the unsigned routine (T33 `MUL8`), then negate the 16-bit result if the sign bit is set. The result always fits signed 16-bit (range −16256…+16384).
**Code:**
```asm
; In:  ZP_TMP = a (signed), ZP_TMP2 = b (signed)
; Out: ZP_PTR / ZP_PTR+1 = signed product (16-bit two's complement)
; Calls MUL8 (T33). Scratch: ZP_STATE, A, X, Y.
SMUL8    LDA   ZP_TMP
         EOR   ZP_TMP2
         STA   ZP_STATE       ; bit 7 = result sign
         LDA   ZP_TMP         ; |a| -> ZP_TMP
         BPL   :AOK
         EOR   #$FF
         CLC
         ADC   #$01
         STA   ZP_TMP
:AOK     LDA   ZP_TMP2        ; |b| -> ZP_TMP2
         BPL   :BOK
         EOR   #$FF
         CLC
         ADC   #$01
         STA   ZP_TMP2
:BOK     JSR   MUL8           ; unsigned |a|*|b| -> ZP_PTR/ZP_PTR+1
         LDA   ZP_STATE
         BPL   :DONE          ; positive result: leave as is
         LDA   ZP_PTR         ; negative: two's-complement negate the 16-bit value
         EOR   #$FF
         CLC
         ADC   #$01
         STA   ZP_PTR
         LDA   ZP_PTR+1
         EOR   #$FF
         ADC   #$00           ; +carry from the low-byte +1
         STA   ZP_PTR+1
:DONE    RTS
```
**Compat:** all CPUs.
**Use when:** signed 8-bit multiply.
**Watch out:** `|−128|` is held as `$80` (=128) and multiplied as unsigned — correct here, because the product still fits signed 16-bit. Do not `SED`.
**Agent rules:** swap in T34 (`MUL_QS`) for the magnitude step if multiplies are hot. **Verified exhaustively over all 65,536 signed operand pairs.**

### T35S: Signed 8÷8 Divide (wrapper around T35)
**What:** Signed divide, **truncating toward zero** (C semantics): the remainder takes the **dividend's** sign and `q*b + r == a`. Quotient sign is `a EOR b`; the magnitudes go through the unsigned routine (T35 `DIV8`).
**Code:**
```asm
; In:  ZP_TMP = a (signed dividend), ZP_TMP2 = b (signed divisor, != 0)
; Out: ZP_PTR = signed quotient, ZP_PTR+1 = signed remainder
; Calls DIV8 (T35). Scratch: ZP_STATE (q sign), ZP_COUNT (dividend), A, X.
SDIV8    LDA   ZP_TMP
         EOR   ZP_TMP2
         STA   ZP_STATE       ; quotient sign (bit 7)
         LDA   ZP_TMP
         STA   ZP_COUNT       ; save dividend; its bit 7 is the remainder sign
         LDA   ZP_TMP         ; |a|
         BPL   :AOK
         EOR   #$FF
         CLC
         ADC   #$01
         STA   ZP_TMP
:AOK     LDA   ZP_TMP2        ; |b|
         BPL   :BOK
         EOR   #$FF
         CLC
         ADC   #$01
         STA   ZP_TMP2
:BOK     JSR   DIV8           ; |a|/|b|: ZP_TMP = |q|, A = |r|
         STA   ZP_PTR+1       ; |r| -> remainder slot
         LDA   ZP_TMP
         STA   ZP_PTR         ; |q| -> quotient slot
         LDA   ZP_STATE       ; apply quotient sign
         BPL   :QOK
         LDA   ZP_PTR
         EOR   #$FF
         CLC
         ADC   #$01
         STA   ZP_PTR
:QOK     LDA   ZP_COUNT       ; apply remainder sign (= dividend sign)
         BPL   :ROK
         LDA   ZP_PTR+1
         EOR   #$FF
         CLC
         ADC   #$01
         STA   ZP_PTR+1
:ROK     RTS
```
**Compat:** all CPUs.
**Use when:** signed 8-bit divide with C-style truncation.
**Watch out:** divide-by-zero is undefined (guard the caller). The one unrepresentable result is **−128 ÷ −1 = +128**, which overflows a signed byte and returns `$80` (correct only mod 256) — the classic `INT_MIN / −1` overflow. For floored division (Python `//` semantics) instead of truncation, adjust the quotient down by 1 and add the divisor to the remainder when the remainder is nonzero and the operand signs differ.
**Agent rules:** guard divisor ≠ 0; state which rounding convention you used. **Verified exhaustively over all 65,280 nonzero-divisor signed pairs.**


---

# PART VII — 65C02-SPECIFIC POWER TOOLS

*All of Part VII is **non-NMOS**. Each entry gives the NMOS fallback. See Section 2C for opcodes/cycles.*

### T38: `STZ` — Store Zero
**What:** Store $00 without loading a register (preserves A).
**Code:**
```asm
; 65C02/816
CLRVAR   STZ   ZP_TMP
         STZ   WORKBUF
         RTS
```
**Compat:** **NMOS no** · 65C02/816 yes.
**Use when:** clearing memory while keeping A.
**Agent rules — FALLBACK (NMOS):** `LDA #$00 / STA ...` (or reuse a register already known to be zero).

### T39: `PHX`/`PHY`/`PLX`/`PLY`
**What:** Push/pull X and Y directly (`PLX`/`PLY` set N,Z).
**Code:**
```asm
; 65C02/816
SAVE65   PHX
         PHY
         ; ... work ...
         PLY
         PLX
         RTS
```
**Compat:** **NMOS no** · 65C02/816 yes.
**Use when:** cleaner subroutines and interrupt handlers.
**Agent rules — FALLBACK (NMOS):** `TXA/PHA … PLA/TAX` and `TYA/PHA … PLA/TAY`. Restore in reverse order.

### T40: `BIT #imm` — Non-Destructive Mask Test
**What:** Test bits of A without changing A. **`BIT #imm` affects Z only** (not N or V — it has no memory byte to source bits 7/6 from).
**Code:**
```asm
; 65C02/816 — is bit 5 of A set?
         BIT   #%00100000
         BEQ   :BIT5_CLEAR
```
**Compat:** **NMOS no** · 65C02/816 yes.
**Use when:** mask tests that must preserve A.
**Watch out:** do not assume memory-`BIT` N/V semantics for the immediate form.
**Agent rules — FALLBACK (NMOS):** save A (`PHA`), `AND #mask`, branch, `PLA`; or `AND #mask` if A may be destroyed.

### T41: `TRB` / `TSB` — Bitfield Update
**What:** `TSB` sets the bits of A in memory (memory OR A); `TRB` clears them (memory AND NOT A). Z reports whether `(A AND memory)` was zero. Neither alters A. Read-modify-write.
**Code:**
```asm
; 65C02/816
SETBITS  TSB   ZP_STATE      ; set bits; Z = were any already set?
         RTS
CLRBITS  TRB   ZP_STATE      ; clear bits; Z = were any set before?
         RTS
```
**Compat:** **NMOS no** · 65C02/816 yes.
**Use when:** RAM flag/state bitfields.
**Watch out:** RMW — avoid on read-sensitive memory-mapped I/O unless the hardware spec confirms it is safe.
**Agent rules — FALLBACK (NMOS):** `LDA mem / ORA #mask / STA mem` (set) or `LDA mem / AND #~mask / STA mem` (clear).

### T42: `RMBx` / `SMBx` — Single-Bit Set/Reset (Rockwell/WDC)
**What:** Reset/set bit x (0–7) of a zero-page byte in one instruction.
**Code:**
```asm
; WDC/Rockwell 65C02 only.
         SMB3  ZP_STATE      ; set bit 3
         RMB0  ZP_STATE      ; reset bit 0
```
**Compat:** **NMOS no** · WDC/Rockwell 65C02 yes · **65SC02 no** · **W65C816 no**.
**Use when:** compact single-bit flag manipulation when the target allows it.
**Agent rules — FALLBACK:** `LDA zp / ORA #bit / STA zp` (set) or `LDA zp / AND #~bit / STA zp` (reset). Emit `RMB/SMB` only when the profile explicitly allows Rockwell/WDC bit ops.

### T43: `BBRx` / `BBSx` — Branch on Bit (Rockwell/WDC)
**What:** Branch if bit x of a zero-page byte is reset/set, without using a register or affecting flags.
**Code:**
```asm
; WDC/Rockwell 65C02 only. Branch if bit 3 of ZP_STATE is set.
         BBS3  ZP_STATE,:SET
         ; bit-clear path
         RTS
:SET     RTS
```
**Compat:** **NMOS no** · WDC/Rockwell 65C02 yes · **65SC02 no** · **W65C816 no**.
**Use when:** compact bit-driven state machines on a supporting part.
**Watch out:** timing is **5 / 6 taken / 7 taken across a page** (Section 2C note — bus-capture confirmed on Rockwell silicon). Budget the taken-branch cycle exactly as for any other `Bxx`.
**Agent rules — FALLBACK:** `LDA zp / AND #bit / BEQ` (or `BNE`). Emit only when Rockwell/WDC bit ops are allowed.

### T44: `WAI` / `STP` — Low-Power / Latency (WDC only)
**What:** `WAI` halts the CPU until an interrupt (very low latency — placing `WAI` at an ISR start with I set gives ~1-clock response). `STP` stops the clock entirely until reset (microamp draw). Both retain registers/RAM (the WDC core is fully static).
**Code:**
```asm
; WDC W65C02S / 65C816 only.
IDLE     WAI                 ; sleep until an interrupt
         BRA   IDLE
```
**Compat:** **NMOS no** · **WDC only** (verify on Rockwell/other variants).
**Use when:** low-power idle, deterministic "wait until interrupt" sync, minimal interrupt latency.
**Watch out:** behavior with IRQ disabled depends on the part; consult the datasheet. After `WAI`, the handler can run inline (it need not end in `RTI`).
**Agent rules:** use only with an explicit WDC/816 target; document IRQ-enabled/disabled state before `WAI`. **FALLBACK (NMOS):** a polling loop.

---

# PART VIII — INTERRUPTS AND RE-ENTRANCY

*Vector placement, timer setup, and IRQ-source clearing are platform-specific and omitted. Interrupt sequence: the CPU pushes PCH, PCL, then P, sets I, and vectors (IRQ/BRK, NMI, RESET). `RTI` pulls P then PC. Typical latency: 7 clocks in, 6 for `RTI`.*

### T45: Minimal NMOS-Compatible IRQ Prologue/Epilogue
**What:** Save the registers you clobber; restore in reverse; `CLD` for binary-arithmetic hygiene.
**Code:**
```asm
IRQ      PHA
         TXA
         PHA
         TYA
         PHA
         CLD                 ; NMOS does not clear D on IRQ (Hard Rule 9)
         ; ... interrupt work ...
         PLA
         TAY
         PLA
         TAX
         PLA
         RTI
```
**Compat:** all CPUs.
**Use when:** safe baseline handler.
**Watch out:** `CLD` only affects the handler's D; the caller's D is preserved in the stacked P and restored by `RTI`. `SEI` does **not** block NMI.
**Agent rules:** in latency-critical handlers save only used registers; always end with `RTI`, never `RTS`.

### T46: 65C02 IRQ Prologue (Direct Stack Ops)
**What:** Smaller/clearer save using `PHX`/`PHY`.
**Code:**
```asm
; 65C02/816
IRQ65    PHA
         PHX
         PHY
         CLD                 ; redundant on 65C02 (D auto-cleared) but harmless
         ; ... interrupt work ...
         PLY
         PLX
         PLA
         RTI
```
**Compat:** **NMOS no** (uses `PHX/PHY/PLX/PLY`) · 65C02/816 yes.
**Use when:** 65C02 handlers.
**Agent rules — FALLBACK (NMOS):** use T45.

### T47: Distinguish `BRK` from `IRQ`
**What:** `BRK` and hardware `IRQ` share the `$FFFE` vector. The **B flag exists only in the pushed status byte** — pull the stacked P and test bit 4 (set ⇒ BRK, clear ⇒ IRQ). `BRK` is effectively two bytes (it pushes BRK+2), so the byte after `BRK` is a usable signature.
**Code:**
```asm
; In the shared handler, after the standard register saves:
; (TSX, then read the stacked status byte and test bit 4 = B.)
         TSX
         LDA   $0104,X       ; stacked P (offset depends on how many bytes you pushed)
         AND   #%00010000    ; isolate B
         BNE   :WAS_BRK
         ; was a hardware IRQ
:WAS_BRK ; was a BRK
```
**Compat:** all CPUs (NMOS has the BRK/IRQ hijack bug — see Section 2B).
**Use when:** software breakpoints, syscall-via-BRK, mixed BRK/IRQ handlers.
**Watch out:** you **cannot** test B with `PHP/PLA` inside the handler — `PHP` always pushes B set. The offset to the stacked P depends on how many bytes the prologue pushed before `TSX`; compute it explicitly.
**Agent rules:** read B from the **stacked** status only; document the exact stack offset used.

### T48: Interrupt Latency Budgeting
**What:** Response time = finishing the current instruction + interrupt entry (7) + your prologue. Worst case is set by the longest interruptible instruction.
**Code:**
```asm
; Low-latency handler: save only A because only A is used.
FASTIRQ  PHA
         CLD
         LDA   ZP_STATE
         AND   #%11111110    ; clear a flag bit (example work)
         STA   ZP_STATE
         PLA
         RTI
```
**Compat:** all CPUs (65C02 differs in available opcodes and D handling).
**Use when:** bit-banged protocols, periodic timers, externally visible cycle windows.
**Watch out:** if an interrupt can land during SMC address patching (T17) or stack-built dispatch (T20), wrap the critical region in `SEI`/`CLI`. NMI cannot be masked. Also: a **taken branch does not sample IRQ on its final cycle** — recognition slips past the *following* instruction (~1 extra instruction of latency; measured on silicon and visual6502). Worst case = taken branch + your longest instruction, not the longest instruction alone.
**Agent rules:** for latency-sensitive code list max-interrupted-instruction cycles, entry cycles, prologue, work, epilogue; do not promise exact latency while NMI/DMA/wait-states/platform hardware are unknown.

### T49: Re-Entrant Routine Pattern
**What:** Avoid shared mutable ZP state, or save it; take pointers from the caller and touch only A/Y.
**Code:**
```asm
; Re-entrant-ish 16-byte copy: caller supplies ZP_PTR (src) and ZP_PTR2 (dst).
; Uses only A and Y; does not modify the pointer bytes.
COPY16   LDY   #$0F
:LOOP    LDA   (ZP_PTR),Y
         STA   (ZP_PTR2),Y
         DEY
         BPL   :LOOP
         RTS
```
**Compat:** all CPUs.
**Use when:** routines callable from both mainline and interrupt code without scratch collisions.
**Watch out:** still relies on caller-owned ZP pointers; if an interrupt reuses the same ZP pointers it is not re-entrant.
**Agent rules:** mark a routine re-entrant only if it uses no shared writable global state; for interrupt-safe routines use distinct ZP banks or save/restore all scratch; on 816 native mode, stack-relative and movable direct page help (keep that in a 65816 skill).

### T50: WAI-Based Minimal-Latency Handler (WDC)
**What:** With I set, `SEI`/`WAI` parks the CPU; the handler body runs inline immediately after the interrupt asserts, with ~1-clock latency. See T44 for `WAI` semantics.
**Code:**
```asm
; WDC only. Outline:
;   SEI
;   WAI            ; wakes on interrupt; execution continues inline here
;   ... handle event ...   (need not RTI if entered this way)
```
**Compat:** **WDC only.**
**Use when:** the tightest deterministic interrupt response on a WDC part.
**Watch out:** semantics with I set/clear are part-specific; read the datasheet.
**Agent rules:** WDC target only; **FALLBACK:** a normal vectored handler (T45/T46) plus a polling loop.


---

# PART IX — UNDOCUMENTED NMOS 6502 OPCODES (NMOS-ONLY, RADIOACTIVE)

## Policy: first-class, but do not emit by default

Undocumented opcodes are real behavior on most NMOS 6502/6510 chips — they arise from the instruction decoder activating multiple internal control paths at once (open-drain logic ANDs the conflicting values; the lower voltage wins). They are **not portable**: the 65C02, 65SC02, and 65816 replace every one of them with a NOP or a defined instruction.

**An agent may emit an undocumented opcode only when ALL are true:** (1) target is explicitly NMOS-only or a tested compatible part; (2) the user permits undocumented opcodes; (3) a documented fallback is included; (4) the opcode is in the **stable** class below; (5) a startup conformance test is provided. **Never** emit the unstable "magic constant" opcodes (SHA/SHX/SHY/TAS, ANE/XAA, LXA) except for explicit chip-characterization work, and **never** emit `JAM`/`KIL`.

### Naming caution
The mnemonic **`AXS`** is used ambiguously in the literature for **two different** opcodes: `$87` **SAX** (store A AND X) and `$CB` **SBX** ((A AND X) − imm → X). Disambiguate by **opcode value**, not mnemonic. (`SAX` also appears as `AAX`; `SBX` also appears as `AXS`/`SAX` depending on the source.)

## Stable class (usable on most NMOS parts, with care)

| Mnemonic (aliases) | Opcode family | Operation | Typical use |
|---|---|---|---|
| **LAX** | $A3/$A7/$AF/$B3/$B7/$BF | M → A and M → X | load A and X together |
| **SAX** (AXS, AAX) | $83/$87/$8F/$97 | A AND X → M (no flags) | masked store |
| **DCP** (DCM) | $C3/$C7/$CF/$D3/$D7/$DB/$DF | DEC M, then CMP M | decrement-and-compare in loops |
| **ISC** (ISB, INS) | $E3/$E7/$EF/$F3/$F7/$FB/$FF | INC M, then SBC M | increment-and-subtract |
| **SLO** (ASO) | $03/$07/$0F/$13/$17/$1B/$1F | ASL M, then ORA M | bitstream/packed-data ops |
| **RLA** | $23/$27/$2F/$33/$37/$3B/$3F | ROL M, then AND M | bitstream/packed-data ops |
| **SRE** (LSE) | $43/$47/$4F/$53/$57/$5B/$5F | LSR M, then EOR M | bitstream/packed-data ops |
| **RRA** | $63/$67/$6F/$73/$77/$7B/$7F | ROR M, then ADC M | bitstream/packed-data ops |
| **ANC** | $0B/$2B | A AND #imm, then C = bit 7 of result | AND that also sets carry from N |
| **ALR** (ASR) | $4B | A AND #imm, then LSR A | combined mask + shift |
| **ARR** | $6B | A AND #imm, then ROR A; C/V set from bits 6/5 | (analog-sensitive flags) |
| **SBX** (AXS) | $CB | (A AND X) − #imm → X; sets N,Z,C like CMP | fast index stepping |

### T51: `LAX` — Load A and X
```asm
; NMOS undocumented. Intent: LDA TABLE,Y / TAX in one op.
        LAX   TABLE,Y
```
**Compat:** **NMOS only** (CMOS: NOP/defined). **FALLBACK:** `LDA TABLE,Y / TAX`.

### T52: `SAX` — Store A AND X
```asm
; NMOS undocumented. Stores (A AND X) to ZP_TMP; does NOT change A, X, or flags.
        SAX   ZP_TMP
```
**FALLBACK (preserves A; clobbers flags, uses scratch):**
```asm
        PHA
        STX   ZP_TMP2        ; scratch = X
        AND   ZP_TMP2        ; A = A AND X
        STA   ZP_TMP
        PLA                  ; restore A
```
**Compat:** **NMOS only.** State whether the fallback preserves A/X/flags.

### T53: `DCP` — Decrement Memory then Compare
```asm
; NMOS undocumented. Replaces DEC counter / CMP counter in countdown loops.
        DCP   ZP_COUNT       ; ZP_COUNT--, then CMP A with ZP_COUNT
        BNE   :more
```
**FALLBACK:** `DEC ZP_COUNT / CMP ZP_COUNT`. RMW side effects apply — not for I/O. **NMOS only.**

### T54: `ISC` — Increment Memory then Subtract
```asm
; NMOS undocumented. Inherits SBC's carry dependency exactly.
        ISC   ZP_TMP         ; ZP_TMP++, then SBC ZP_TMP
```
**FALLBACK:** `INC ZP_TMP / SBC ZP_TMP` (with `SEC` precondition as for any SBC). **NMOS only.**

### T55: `SLO` / `RLA` / `SRE` / `RRA` — Shift/Logic Hybrids
```asm
; NMOS undocumented. SLO ZP_TMP == ASL ZP_TMP / ORA ZP_TMP.
        SLO   ZP_TMP
```
**FALLBACK:** the two documented ops shown in the stable table. Carry is both input and output for the rotate/arithmetic variants (`RLA`/`RRA`); RMW side effects apply — RAM only. **NMOS only.**

### T56: `SBX` (index stepping), `ANC`, `ALR`, `ARR`
```asm
; SBX: X = (A AND X) - imm. With A=$FF (or TXA first so A=X), this is X = X - imm,
; in 2 bytes / 2 cycles, ignoring incoming carry. Sets N,Z,C like CMP.
        TXA
        SBX   #$10           ; X = X - $10  (e.g. step an array-of-structs index)

; ANC: A = A AND imm, then C = bit 7 of the result (one NMOS op).
        ANC   #$80
```
**Compat:** **NMOS only.**
**Watch out:** `ANC`/`ALR`/`ARR` have **analog-sensitive** behavior on real silicon — testing shows the immediate step and flag results can be part-dependent. Treat their exact semantics as needing per-chip verification.
**FALLBACK:** `SBX #imm` → `TXA / SEC / SBC #imm / TAX` (8 cycles vs 4); `ANC #imm` → `AND #imm / ` then set carry from N as needed.

### T57: The Unstable "Magic Constant" Family — DO NOT EMIT
**What:** A group of NMOS stores/loads whose stored value is ANDed with **{H+1}** (the high byte of the **base** absolute address, plus one). They are unstable for two independent reasons and **must not appear in shipping code**.

| Opcode | Mnemonic | Mode | Formula |
|---|---|---|---|
| $9F | SHA (AHX, AXA) | abs,Y | {addr} = A AND X AND {H+1} |
| $93 | SHA (AHX, AXA) | (zp),Y | {addr} = A AND X AND {H+1} |
| $9E | SHX (SXA, XAS) | abs,Y | {addr} = X AND {H+1} |
| $9C | SHY (SYA, SAY) | abs,X | {addr} = Y AND {H+1} |
| $9B | TAS (SHS, XAS) | abs,Y | S = A AND X; {addr} = (A AND X) AND {H+1} |
| $BB | LAS (LAR, LAE) | abs,Y | A,X,S = {addr} AND S (this one is a load; relatively less unstable) |

Worked example: `SHX $6430,Y` stores `X AND $65` (since {H+1} = $64+1 = $65).

**Two instabilities:**
1. **Page-cross address corruption** — if indexing crosses a page boundary, on some chips the store goes to a corrupted address (the high byte of the target becomes the stored value). May not occur on all chips. **Mitigation:** keep the index small enough that no page boundary is crossed.
2. **The AND-{H+1} term dropping** — if RDY is pulled low (DMA, etc.) in the cycle after the opcode fetch, the `AND {H+1}` can drop, turning e.g. `SHY` into a plain `STY`.

**Disarming trick** (if you must, for characterization): choose a target whose high byte is `$FE`, so {H+1} = `$FF`, and `AND $FF` is a no-op — `SHX $FE00,Y` behaves like `STX $FE00,Y`.

### T58: `ANE`/`LXA` (highly unstable) and `JAM`/`KIL` (fatal)
- **`ANE`/`XAA`** ($8B) and **`LXA`** ($AB) involve a magic constant depending on A's contents, data-bus line noise, temperature, and chip series (e.g. `(A OR CONST) AND X AND imm → A` for ANE). The constant genuinely differs chip to chip (one VIC-20 measured `$FF` for ANE and `$EE` for LXA; other parts differ). The only "safe harbor" (per the VICE team): an immediate of `$00`, or A=`$FF` first — generally, every bit that could be 0 in A must already be 0 in the immediate — which cancels the constant entirely. Even then: characterization only. **Never emit** in shipping code.
- **`JAM`/`KIL`/`HLT`** ($02, $12, $22, $32, $42, $52, $62, $72, $92, $B2, $D2, $F2) halt the CPU until reset. **Never emit** (Hard Rule 7).

### Undocumented-opcode mini-test policy
For a "stable" undocumented op, emit a startup self-test that runs the op on known inputs and checks A/X/memory/flags against the expected result; if it mismatches (e.g. the binary is on a CMOS part or an atypical NMOS variant), fall back to the documented path. Never include a `JAM` runtime test unless the harness can recover via hardware reset.


---

# PART X — VERIFICATION SNIPPETS

**Safety:** running a CMOS opcode on an NMOS part (or vice versa) can trigger undocumented behavior. Run feature probes only in a controlled environment (emulator or known hardware), ideally once at startup, and record the result in a flag your code reads thereafter.

### Probe: 65C02 vs NMOS via `INC A`
```asm
; INC A ($1A) increments A on 65C02/816. On NMOS, $1A is a 1-byte NOP, so A is unchanged.
PROBEINC LDA   #$00
         INC   A             ; $1A
         ; A = $01  -> 65C02/816 ;  A = $00 -> NMOS
         RTS
```

### Probe: 65C02 `BRA`
```asm
; Controlled environment only. On 65C02, A becomes $65.
; On NMOS, $80 is typically a 2-byte NOP (consumes the offset byte), so A ends $00.
PROBE65  LDA   #$02
         BRA   :CMOS
         LDA   #$00
         RTS
:CMOS    LDA   #$65
         RTS
```

### Test: decimal-mode result (works on NMOS and CMOS — checks only C and Z, both valid)
```asm
; $99 + $01 in BCD must give $00 with carry set.
TBCD     SED
         CLC
         LDA   #$99
         ADC   #$01
         PHP                 ; capture the (valid) carry before it is disturbed
         CLD
         CMP   #$00
         BNE   :FAIL
         PLP
         BCC   :FAIL         ; carry should indicate decimal overflow past 99
         RTS
:FAIL    BRK                 ; replace with platform-appropriate failure signal
```

### Test: self-modifying operand
```asm
TSMC     LDA   #$5A
         STA   :TLDA+1       ; patch the immediate operand
:TLDA    LDA   #$00
         CMP   #$5A
         BNE   :FAIL
         RTS
:FAIL    BRK
```

### Test: RTS-trick dispatch (T20)
```asm
TRTSD    LDX   #$02
         JSR   DISPATCH       ; should land in HAND2 and return here
         RTS
```

---

# PART XI — AGENT SKILL RULES & OUTPUT TEMPLATES

### Code-generation ladder (follow top-down; stop at the first matching tier)
1. **Default:** emit documented NMOS-compatible 6502.
2. **Target = 65C02:** you may use `BRA`, `STZ`, `PHX/PHY/PLX/PLY`, `INC A`/`DEC A`, `BIT #imm`, `(zp)`, `JMP (abs,X)`, `TRB/TSB`.
3. **Target allows Rockwell/WDC bit ops:** you may add `RMB/SMB`, `BBR/BBS`. (Not on 65SC02 or 65816.)
4. **Target = W65C816 8-bit:** keep M/X width assumptions explicit; avoid NMOS undocumented opcodes; do **not** use `RMB/SMB/BBR/BBS`; treat bank/mode transitions in a separate 65816 skill.
5. **Target = NMOS + undocumented opcodes explicitly enabled:** emit only stable-class opcodes (Part IX), always with a fallback and a startup conformance test.

At every tier, when unsure, emit the **fallback** rather than the CPU-specific instruction.

### Register-preservation contract (state this for every routine you emit)
```text
Routine: <name>
CPU:     NMOS 6502 / 65C02 / W65C816 8-bit
Input:   A = ...   X = ...   Y = ...   ZP_xxx = ...   carry/decimal = ...
Output:  A = ...   X = preserved|clobbered   Y = preserved|clobbered
         Flags = meaningful (which) | clobbered
         Zero page used: <list>
         Memory touched: <list>
         Max stack depth: <bytes>
```

### Timing annotation (add when timing matters)
```text
Timing:
  Setup:          N cycles
  Inner loop:     M cycles per taken iteration
  Final iteration:K cycles
  Page crossing:  impossible | possible +1 | intentionally equalized
  Interrupts:     allowed | masked (SEI region) | jitter tolerated
  Decimal extra:  none | +1 per ADC/SBC (65C02 with D=1)
```

### Self-modifying-code annotation
```text
SMC patch points:
  LABEL+1            = immediate operand
  LABEL+1 / LABEL+2  = absolute address low / high
Atomicity: safe only when non-interruptible, or no IRQ path calls the patched code
Storage:   requires writable (RAM) code
Fallback:  <non-SMC version provided? yes/no>
```

### Undocumented-opcode annotation
```text
Undocumented opcode:
  Mnemonic / opcode byte:
  Stability class:    stable | unstable (do not ship)
  Operation:
  CMOS behavior:      NOP | defined-other  (i.e. NOT portable)
  Tested on:          <emulator/hardware>
  Fallback provided:  yes/no
  Startup self-test:  yes/no
```

---

# BIBLIOGRAPHY

**Primary datasheets**
- Western Design Center, *W65C02S Datasheet*: https://www.westerndesigncenter.com/wdc/documentation/w65c02s.pdf
- Western Design Center, *W65C816S Datasheet*: https://www.westerndesigncenter.com/wdc/documentation/w65c816s.pdf
- WDC product/feature pages: https://wdc65xx.com/

**Decimal mode, 65C02 opcodes, interrupts, timing**
- Bruce Clark, *Decimal Mode* (6502.org): https://6502.org/tutorials/decimal_mode.html
- *65C02 Opcodes* (6502.org): https://6502.org/tutorials/65c02opcodes.html
- *Investigating Interrupts* (6502.org): https://6502.org/tutorials/interrupts.html
- Bruce Clark, delay-loop notes and `9*V+8` formula (6502.org forum/tutorials)
- Klaus Dormann, *6502/65C02 functional tests* (incl. Bruce Clark decimal tests): https://github.com/Klaus2m5/6502_65C02_functional_tests

**Self-modifying code, stacks, RTS/RTI synthesis**
- Garth Wilson, *Self-modifying code on 65xx*: http://wilsonminesco.com/SelfModCode/
- Garth Wilson, *6502 Stacks Treatise*: http://wilsonminesco.com/stacks/
- Garth Wilson, *Synthesizing instructions with RTS/RTI/JSR*: http://wilsonminesco.com/stacks/RTSsynth.html

**Undocumented / illegal opcodes**
- masswerk, *6502 Illegal Opcodes Demystified*: https://www.masswerk.at/nowgobang/2021/6502-illegal-opcodes
- masswerk, *6502 Instruction Set* (reference): https://www.masswerk.at/6502/6502_instruction_set.html
- Michael Steil / pagetable, *How MOS 6502 Illegal Opcodes Really Work*: https://www.pagetable.com/?p=39
- oxyron 6502 opcode matrix (illegal-opcode timing/behavior table)
- NESdev / Visual6502 wiki, *6502 Timing States* and unsupported-opcode notes: https://www.nesdev.org/wiki/Visual6502wiki/6502_Timing_States

**Cycle-level bus behavior / dead cycles**
- Mark Laughton, *6502 Dead Cycles* (c74project.com) — RMW double-write, dummy-read-on-write, PBA vs PFA on page-cross
- Neil Parker, *6502/65C02 addressing-mode and opcode notes* (LLX): http://www.llx.com/~nparker/a2/opcodes.html

**Classic technique sources**
- Joe Holt, "6502 Tricks and Traps," *Byte*, June 1985

---

*End of draft v1. All Part VI math routines — unsigned and signed — are simulator-verified over their full input ranges. The one documented arithmetic edge case is signed −128 ÷ −1 (T35S), which overflows a signed byte exactly as `INT_MIN / −1` does on any two's-complement machine. The BBR/BBS timing ambiguity (Section 2C / T43) is now the one genuinely unresolved point in the document and should be settled against silicon before any cycle-critical use.*
