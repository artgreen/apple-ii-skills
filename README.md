# Apple II Skills

Agent skills for Apple II and IIgs development: assembly, Applesoft BASIC,
MouseText interfaces, static review, optimization, and executable verification.
Each skill is a directory containing `SKILL.md` and any supporting references
or scripts. The CPU-level skills also apply to other 6502-based machines.

## Skills

| Skill | Purpose |
|---|---|
| [apple-ii](apple-ii/SKILL.md) | Master skill: select specialists and coordinate their workflows |
| [apple-assembly-programming](apple-assembly-programming/SKILL.md) | Apple II memory, ROM, graphics, I/O, ProDOS, and IIgs platform guidance |
| [6502-codegen](6502-codegen/SKILL.md) | Generate and verify 6502/65C02 routines with documented contracts |
| [6502-optimization](6502-optimization/SKILL.md) | Tune working code and compare behavior against the original |
| [6502-review](6502-review/SKILL.md) | Static correctness, portability, and maintainability review |
| [6502-testing](6502-testing/SKILL.md) | Test assembled binaries by symbol and integrate with an emulator |
| [apple-ii-textui](apple-ii-textui/SKILL.md) | MouseText glyphs, widget recipes, and screen-memory decoding |
| [applesoft-basic](applesoft-basic/SKILL.md) | Applesoft language behavior, disk I/O, testing, and performance |
| [merlin32](merlin32/SKILL.md) | Merlin32 syntax, directives, macros, and 65816 width tracking |

Use `$apple-ii` for work spanning several areas, or select a specialist directly.
For example: “Use $apple-ii to build a ProDOS utility for the enhanced IIe,” or
“Use $6502-review to inspect this routine without running it.”

## Install

Clone the repository, then keep the skill directories together so sibling
dependencies resolve:

```sh
git clone https://github.com/artgreen/apple-ii-skills.git
cd apple-ii-skills
export APPLE_II_SKILLS="$PWD"
```

For Codex, link the skills into your skill directory. On macOS/Linux:

```sh
skill_target="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_target"
for skill in apple-ii apple-assembly-programming 6502-codegen 6502-optimization \
             6502-review 6502-testing apple-ii-textui applesoft-basic merlin32; do
  if [ -e "$skill_target/$skill" ] || [ -L "$skill_target/$skill" ]; then
    printf 'Already exists; inspect before replacing: %s\n' "$skill_target/$skill"
  else
    ln -s "$APPLE_II_SKILLS/$skill" "$skill_target/$skill"
  fi
done
```

For Claude Code, use `skill_target="$HOME/.claude/skills"` with the same loop.
Other agents that read `SKILL.md` can use their supported skill directory.
On platforms without symlink support, copy all nine directories together.
Start a new agent session if the installed skills are not discovered immediately.

## Dependencies and checks

Reading the skills needs no additional software. The routine and binary test
harnesses require Python 3.9+ and py65. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/check.py
```

The check runs the five bundled self-test suites, validates skill metadata and
relative Markdown links, and checks the distributable file layout. It does not
launch an emulator or call an AI service.

Additional tools are needed only for their corresponding workflows:

- [Merlin32](https://github.com/digarok/merlin32) to build Merlin source.
- [CiderPress2](https://ciderpress2.com/) to manage disk images.
- A microM8 build exposing the MCP extension documented in
  [the integration reference](6502-testing/references/microm8-mcp.md), plus the
  Python MCP v1 client in a Python 3.10+ environment
  (`pip install -r requirements-integration.txt`). Stock
  microM8 builds may not include that extension. The py65 tier works without it.

No emulator, ROM, macro library, or disk image is bundled. Supply your own
installation and images. Configure the optional paths for your machine:

```sh
export APPLE_II_SKILLS="/path/to/apple-ii-skills"
export MERLIN32_LIBRARY="/path/to/merlin32/Library"
export MICROM8_BIN="/path/to/microM8"
export PRODOS_DISK="/path/to/prodos.dsk"
export DOS33_DISK="/path/to/dos33.dsk"
export MICROM8_MCP_URL="http://localhost:8080/mcp/sse"
```

Use the configured paths in the specialist examples. `MICROM8_MCP_URL` changes
the driver endpoint; the other variables supply locations to shell examples. The `uv` examples
select Python 3.12 and keep the MCP SDK below version 2, matching the driver
API ([SDK compatibility guidance](https://github.com/modelcontextprotocol/python-sdk)).
The optional `6502-codegen/lmtest.py` calls a model endpoint you explicitly
configure; it is not part of installation or the check suite.

## Verification limits

The harnesses execute NMOS 6502 and 65C02 logic; they do not execute native
65816 code or reproduce every Apple II peripheral. Some instructions require
reference checks or a separate emulator. Timing estimates are computed from
reference tables, not asserted as hardware measurements. Historical verification
notes describe the checks performed when those references were written;
they are not a promise that every claim has been retested on every machine.

## Sources and license

MIT license for this collection's original instructions, reference prose, and
helper code. See [LICENSE](LICENSE) and [SOURCES.md](SOURCES.md). External books,
magazine archives, source-code mirrors, and disk images are not redistributed
or relicensed here. No local research archive is needed to install or use this
collection.
