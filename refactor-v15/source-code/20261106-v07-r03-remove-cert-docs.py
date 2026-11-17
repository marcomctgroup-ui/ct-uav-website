"""v07 r03, 6 November 2026. Haykal: "Yes, remove it" - remove the Home item
"Certification documents / Certification references and compliance documents are coming soon."
from "Capability and standards", because the new ISO 9001:2015 section now follows it.
Applied to the Home shell and all address copies. Before-copies: checks/20261106-batch7-r03/before/."""
import re, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / 'checks/20261106-batch7-r03/before'; BEFORE.mkdir(parents=True, exist_ok=True)
skip = ('assets', 'pages', 'checks', 'source-code', 'source-inputs')
shells = [ROOT / 'index.html'] + sorted(p for p in ROOT.glob('*/**/index.html') if p.relative_to(ROOT).parts[0] not in skip)
pat = re.compile(r'<li>\s*<span aria-hidden="true" class="hs-standards__icon">(?:(?!</li>).)*?<h3>Certification documents</h3>.*?</li>\s*', re.S)
for p in shells:
    s = p.read_bytes().decode('utf-8')
    found = pat.findall(s)
    if len(found) != 1:
        raise SystemExit(f'STOP {p}: {len(found)}')
    shutil.copy2(p, BEFORE / p.relative_to(ROOT).as_posix().replace('/', '__'))
    p.write_bytes(pat.sub('', s, count=1).encode('utf-8'))
print('removed in', len(shells), 'files')
