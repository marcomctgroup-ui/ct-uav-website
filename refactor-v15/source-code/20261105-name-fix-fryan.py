"""Name fix, 5 November 2026: 'CT FRYAN' -> 'CT-FRYAN' (Haykal: "Its CT-FRYAN").
CT-FYRAN 256 is a different product and is not touched. Byte-exact edit keeps CRLF.
Before-copies: checks/before-name-fix/. The router file is renamed to its new content hash."""
import hashlib, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OLD, NEW = 'CT FRYAN'.encode(), 'CT-FRYAN'.encode()
bak = ROOT / 'checks/before-name-fix'; bak.mkdir(parents=True, exist_ok=True)
expect = {'index.html': 2, 'pages/ct-fyran-firefighting.html': 7, 'pages/line-04.html': 1,
          'assets/js/shared-script-27159330c4a7.js': 1, 'source-code/shared-script-27159330c4a7.js': 1}
for rel, n in expect.items():
    p = ROOT / rel; b = p.read_bytes()
    if b.count(OLD) != n: raise SystemExit(f'STOP {rel}: {b.count(OLD)} != {n}')
    shutil.copy2(p, bak / rel.replace('/', '__'))
    p.write_bytes(b.replace(OLD, NEW))
# rename router to content hash
old = ROOT / 'assets/js/shared-script-27159330c4a7.js'
h = hashlib.sha256(old.read_bytes()).hexdigest()[:12]
new = old.with_name(f'shared-script-{h}.js'); old.rename(new)
src = ROOT / 'source-code/shared-script-27159330c4a7.js'; src.rename(src.with_name(new.name))
idx = ROOT / 'index.html'; b = idx.read_bytes()
assert b.count(b'shared-script-27159330c4a7.js') == 1
idx.write_bytes(b.replace(b'shared-script-27159330c4a7.js', new.name.encode()))
print('router ->', new.name)
