"""Quick fix, 5 November 2026. Haykal: CT-FRYAN (Firefighting) 3D model faces backwards.
Display setting only: 'ct-fyran-firefighting' front 0 -> 180 degrees in the two firefighting viewer
scripts. GLB bytes, geometry and other models are unchanged. Files get new content-hash names.
Before-copies: checks/20261105-fryan-front/."""
import hashlib, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
bak = ROOT / 'checks/20261105-fryan-front'
page = ROOT / 'pages/ct-fyran-firefighting.html'; ps = page.read_bytes().decode('utf-8')
shutil.copy2(page, bak / page.name)
OLD, NEW = "'ct-fyran-firefighting':{front:0,", "'ct-fyran-firefighting':{front:180,"
for name in ['firefighting-shared-script-72c298408fef.js', 'firefighting-shared-script-8fa5ef83d2b3.js']:
    f = ROOT / 'assets/js' / name; s = f.read_bytes().decode('utf-8')
    if s.count(OLD) != 1: raise SystemExit('STOP ' + name)
    shutil.copy2(f, bak / name)
    s = s.replace(OLD, NEW).encode('utf-8')
    new = 'firefighting-shared-script-' + hashlib.sha256(s).hexdigest()[:12] + '.js'
    (ROOT / 'assets/js' / new).write_bytes(s); f.unlink()
    src = ROOT / 'source-code' / name
    if src.exists(): src.unlink(); (ROOT / 'source-code' / new).write_bytes(s)
    if ps.count(name) != 1: raise SystemExit('STOP ref ' + name)
    ps = ps.replace(name, new); print(name, '->', new)
page.write_bytes(ps.encode('utf-8'))
