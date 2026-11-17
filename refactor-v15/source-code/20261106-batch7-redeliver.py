"""Batch 7: make new delivery copies of the readable cart and social files after an edit.

    python projects/main-website/refactor-v07/source-code/20261106-batch7-redeliver.py

For each readable source (inquiry-cart-v01.js / .css, footer-social-v01.css) it minifies the file,
writes it with a new content-hash name, replaces the old name in pages/*.html and all entry shells,
and moves the old delivery file to checks/20261106-batch7/superseded/. It changes nothing when the
bytes are the same. Regenerate _headers after this script.
"""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPERSEDED = ROOT / 'checks' / '20261106-batch7' / 'superseded'


def minify_js(code: str) -> str:  # same as 20261106-batch7-sales-build.py
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    lines = [line.strip() for line in code.splitlines()]
    return '\n'.join(line for line in lines if line) + '\n'


def minify_css(code: str) -> str:  # same as 20261106-batch7-sales-build.py
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    code = re.sub(r'\s+', ' ', code)
    code = re.sub(r'\s*([{};,>])\s*', r'\1', code)
    code = re.sub(r':\s+', ':', code)
    code = code.replace(';}', '}')
    return code.strip() + '\n'

FILES = [('inquiry-cart-v01.js', 'js', 'inquiry-cart', minify_js),
         ('inquiry-cart-v01.css', 'css', 'inquiry-cart', minify_css),
         ('footer-social-v01.css', 'css', 'footer-social', minify_css)]
targets = sorted((ROOT / 'pages').glob('*.html')) + [ROOT / 'index.html'] + sorted(
    p for p in ROOT.glob('*/**/index.html') if p.relative_to(ROOT).parts[0] not in ('assets', 'pages', 'checks', 'source-code', 'source-inputs'))

for readable, folder, stem, minify in FILES:
    data = minify((ROOT / 'source-code' / readable).read_text(encoding='utf-8')).encode('utf-8')
    ext = folder
    new = f'{stem}-{hashlib.sha256(data).hexdigest()[:12]}.{ext}'
    old = [p for p in (ROOT / 'assets' / folder).glob(f'{stem}-*.{ext}') if p.name != new]
    if not old and (ROOT / 'assets' / folder / new).exists():
        print('unchanged', new)
        continue
    (ROOT / 'assets' / folder / new).write_bytes(data)
    changed = 0
    for path in targets:
        text = path.read_text(encoding='utf-8')
        updated = text
        for o in old:
            updated = updated.replace(f'assets/{folder}/{o.name}', f'assets/{folder}/{new}')
        if updated != text:
            path.write_text(updated, encoding='utf-8', newline='')
            changed += 1
    for o in old:
        SUPERSEDED.mkdir(parents=True, exist_ok=True)
        shutil.move(str(o), SUPERSEDED / o.name)
    print(new, 'replaces', [o.name for o in old], 'in', changed, 'files')
