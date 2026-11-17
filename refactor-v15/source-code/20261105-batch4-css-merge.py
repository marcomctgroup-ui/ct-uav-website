"""Batch 4b (code clean-up: stylesheets), 5 November 2026.
index.html loaded 11 stylesheets (base + 10 patch layers). This script joins them in the same
order into one content-hashed file. All sources are in assets/css, so url() paths do not change.
revision-v02.css stays in place because component pages also use it. The other 10 files are used
only by index.html; they move to checks/before-batch4/css-merged/ (not deleted)."""
import hashlib, re, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
bak = ROOT / 'checks/before-batch4'; (bak / 'css-merged').mkdir(parents=True, exist_ok=True)
idx = ROOT / 'index.html'; s = idx.read_bytes().decode('utf-8')
if not (bak / 'index.html').exists(): shutil.copy2(idx, bak / 'index.html')
tags = list(re.finditer(r'<link\b[^>]*rel="stylesheet"[^>]*>[ \t]*(\r?\n)?', s))
hrefs = [re.search(r'href="(assets/css/[^"]+)"', t.group(0)).group(1) for t in tags]
if len(hrefs) != 11: raise SystemExit(f'STOP: {len(hrefs)} stylesheets')
parts = []
for h in hrefs:
    css = (ROOT / h).read_bytes().decode('utf-8')
    if '@import' in css or '@charset' in css: raise SystemExit('STOP: ' + h)
    parts.append(f'/* ---- from {Path(h).name} ---- */\r\n' + css.rstrip() + '\r\n')
merged = ''.join(parts).encode('utf-8')
name = 'shared-style-' + hashlib.sha256(merged).hexdigest()[:12] + '.css'
(ROOT / 'assets/css' / name).write_bytes(merged)
first = tags[0]
out = s[:first.start()] + f'<link href="assets/css/{name}" rel="stylesheet"/>' + (first.group(1) or '')
pos = first.end()
for t in tags[1:]:
    out += s[pos:t.start()]; pos = t.end()
out += s[pos:]
idx.write_bytes(out.encode('utf-8'))
for h in hrefs:
    if Path(h).name != 'revision-v02.css':
        shutil.move(str(ROOT / h), str(bak / 'css-merged' / Path(h).name))
print(name, len(merged), 'bytes from', len(hrefs), 'files')
