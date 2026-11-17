"""v07 r02 follow-up, 6 November 2026, after the parent screenshot check:
- Home ISO heading: space under the heading (CSS); the ISO CSS is delivered again with a new hash name.
- About ISO heading shortened to "ISO 9001:2015 quality management system" (it took three lines at 1440 px).
  The Vietnamese text (from the ceremony backdrop) is unchanged; only the dictionary key changes."""
import hashlib, re, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SUP = ROOT / 'checks/20261106-batch7-r02/superseded'; SUP.mkdir(parents=True, exist_ok=True)
def minify_css(code):
    code = re.sub(r'/\*[\s\S]*?\*/', '', code); code = re.sub(r'\s+', ' ', code)
    code = re.sub(r'\s*([{};,>])\s*', r'\1', code); code = re.sub(r':\s+', ':', code)
    return code.replace(';}', '}').strip() + '\n'
css = minify_css((ROOT / 'source-code/iso-certificate-v01.css').read_text(encoding='utf-8')).encode()
new = f'iso-certificate-{hashlib.sha256(css).hexdigest()[:12]}.css'
old = [p for p in (ROOT / 'assets/css').glob('iso-certificate-*.css') if p.name != new]
(ROOT / 'assets/css' / new).write_bytes(css)
OLD_H, NEW_H = 'Quality management system following ISO 9001:2015 standard', 'ISO 9001:2015 quality management system'
skip = ('assets', 'pages', 'checks', 'source-code', 'source-inputs')
targets = [ROOT / 'index.html', ROOT / 'pages/about.html'] + [p for p in ROOT.glob('*/**/index.html') if p.relative_to(ROOT).parts[0] not in skip]
n = 0
for t in targets:
    s = t.read_bytes().decode('utf-8'); u = s
    for o in old: u = u.replace(o.name, new)
    u = u.replace(f'"{OLD_H}":', f'"{NEW_H}":').replace(f'>{OLD_H}<', f'>{NEW_H}<')
    if u != s: t.write_bytes(u.encode('utf-8')); n += 1
for o in old: shutil.move(str(o), SUP / o.name)
print(new, 'files', n)
