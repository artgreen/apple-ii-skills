#!/usr/bin/env python3
"""Validate the distributable layout and run the bundled offline self-tests."""
from pathlib import Path
import importlib.util
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SKILLS = {
    'apple-ii', 'apple-assembly-programming', '6502-codegen',
    '6502-optimization', '6502-review', '6502-testing', 'apple-ii-textui',
    'applesoft-basic', 'merlin32',
}
ROOT_FILES = {
    'README.md', 'LICENSE', 'SOURCES.md', 'requirements.txt',
    'requirements-integration.txt', '.gitignore',
}
IGNORED = {'.git', '.venv', '__pycache__', '.DS_Store'}


def main():
    errors = []
    for p in ROOT.iterdir():
        if p.name not in SKILLS | ROOT_FILES | IGNORED | {'scripts', '.github'}:
            errors.append(f'Unexpected distribution entry: {p.name}')
    for name in sorted(SKILLS):
        p = ROOT / name / 'SKILL.md'
        if not p.is_file():
            errors.append(f'Missing skill: {name}')
            continue
        s = p.read_text()
        parts = s.split('---', 2)
        if not s.startswith('---\n') or len(parts) != 3:
            errors.append(f'Invalid frontmatter: {name}')
        elif (f'\nname: {name}\n' not in parts[1]
              or not re.search(r'^description: .+', parts[1], re.M)):
            errors.append(f'Missing name or description: {name}')
    for p in ROOT.rglob('*'):
        rel = p.relative_to(ROOT)
        if set(rel.parts) & IGNORED:
            continue
        if p.is_symlink():
            errors.append(f'Symlink is not a distributable file: {rel}')
            continue
        if not p.is_file():
            continue
        if 'vendor' in rel.parts or p.suffix.lower() in {
            '.db', '.sqlite', '.sqlite3', '.dsk', '.rom', '.zip', '.skill', '.po', '.2mg'
        }:
            errors.append(f'Unexpected bundled asset: {rel}')
        if p.suffix in {'.py', '.md'}:
            text = p.read_text()
            if re.search(r'/(?:Users|home)/[^/\s]+/', text):
                errors.append(f'Personal home path: {rel}')
            if p.suffix == '.py':
                compile(text, str(p), 'exec')
            else:
                for link in re.findall(r'\]\(([^)]+)\)', text):
                    link = link.split('#', 1)[0]
                    if not link or '://' in link or link.startswith('mailto:'):
                        continue
                    if not (p.parent / link).exists():
                        errors.append(f'Broken link in {rel}: {link}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    for name in ['6502-codegen', '6502-optimization', '6502-review',
                 '6502-testing', 'apple-ii-textui']:
        result = subprocess.run([sys.executable, str(ROOT / name / 'scripts/selftest.py')])
        if result.returncode:
            return result.returncode
    # Configuring a different emulator endpoint must not initiate a connection.
    spec = importlib.util.spec_from_file_location('m8_endpoint_check', ROOT / '6502-testing/scripts/m8.py')
    previous = os.environ.get('MICROM8_MCP_URL')
    try:
        os.environ['MICROM8_MCP_URL'] = 'http://localhost:18080/mcp/sse'
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.SSE_URL != os.environ['MICROM8_MCP_URL']:
            raise AssertionError('MCP endpoint override was not used')
    finally:
        if previous is None:
            os.environ.pop('MICROM8_MCP_URL', None)
        else:
            os.environ['MICROM8_MCP_URL'] = previous
    print('Distribution checks and all five self-test suites passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
