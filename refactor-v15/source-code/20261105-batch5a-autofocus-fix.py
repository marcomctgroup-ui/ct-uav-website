"""Batch 5A follow-up, 5 November 2026. Ten product pages had autofocus="" on the payload dialog
close button. Opened as a local file, the frame is cross-origin and the browser logs
"Blocked autofocusing" (checker G8 FAIL). The button is the first element in the dialog, so
showModal() focuses it without the attribute. Only that attribute is removed.
Before-copies: checks/before-batch5a/."""
import re, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
bak = ROOT / 'checks/before-batch5a'; bak.mkdir(parents=True, exist_ok=True)
n = 0
for p in sorted((ROOT / 'pages').glob('*.html')):
    s = p.read_bytes().decode('utf-8')
    if 'autofocus' not in s: continue
    m = re.search(r'(<dialog\b[^>]*>\s*<button\b[^>]*?) autofocus=""', s)
    if s.count('autofocus') != 1 or not m: raise SystemExit('STOP ' + p.name)
    shutil.copy2(p, bak / p.name)
    p.write_bytes((s[:m.start()] + m.group(1) + s[m.end():]).encode('utf-8')); n += 1
print('pages', n)
