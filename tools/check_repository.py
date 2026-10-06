"""Check local Markdown links, JSON syntax and Python syntax without running services.

Run from a source checkout or extracted source distribution. External URLs are not
fetched. Only Markdown's inline links and generated heading anchors are checked;
this is a repository consistency check, not a full Markdown renderer or secret scan.
"""
import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def source_files():
    # Explicit source roots keep private runtime directories and environments out.
    yield from ROOT.glob('*.md')
    for name in ('.github', 'docs', 'src', 'tests', 'tools', 'pilot', 'examples', 'config'):
        yield from (ROOT / name).rglob('*')


def markdown_body(text):
    return re.sub(r'^(`{3,}|~{3,}).*?^\1\s*$', '', text, flags=re.M | re.S)


def anchors(text):
    seen = {}
    result = set()
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', markdown_body(text), re.M):
        heading = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        count = seen.get(heading, 0)
        seen[heading] = count + 1
        result.add(heading if not count else f'{heading}-{count}')
    return result


def main():
    errors = []
    files = sorted({p for p in source_files() if p.is_file() and p.suffix in {'.md', '.json', '.py'}
                    and '__pycache__' not in p.parts})
    links = 0
    for path in files:
        text = path.read_text(encoding='utf-8')
        relative = path.relative_to(ROOT)
        try:
            if path.suffix == '.py':
                ast.parse(text, filename=str(relative))
            elif path.suffix == '.json':
                json.loads(text)
            else:
                for value in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', markdown_body(text)):
                    value = value.strip().split(' "', 1)[0].strip('<>')
                    parsed = urlsplit(value)
                    if parsed.scheme or parsed.netloc:
                        continue
                    links += 1
                    target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
                    if not target.is_relative_to(ROOT):
                        errors.append(f'{relative}: link leaves repository: {value}')
                    elif not target.exists():
                        errors.append(f'{relative}: missing link: {value}')
                    elif parsed.fragment and target.suffix == '.md' and unquote(parsed.fragment) not in anchors(target.read_text()):
                        errors.append(f'{relative}: missing heading: {value}')
        except (SyntaxError, ValueError) as exc:
            errors.append(f'{relative}: {exc}')
    for error in errors:
        print(error, file=sys.stderr)
    print(f'Repository check: {len(files)} text files, {links} local links, {len(errors)} errors')
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
