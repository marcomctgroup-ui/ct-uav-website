"""Batch 4a (code clean-up: links), 5 November 2026.
- Component and catalogue pages: old demo hrefs -> real files
  (../../20261103-main-website-r08-...-v02.html -> ../index.html; uav-components-v02.html -> uav-components.html).
- Catalogue cards: 'ID-v02.html' -> 'component-ID.html'.
- Link interceptor: the 81-entry '-v02.html' alias map is replaced by a rule on real file names.
- Unused constant 'site' removed.
Byte-exact edits keep CRLF. Changed JS files get new content-hash names. Before-copies: checks/before-batch4/."""
import hashlib, re, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
bak = ROOT / 'checks/before-batch4'; bak.mkdir(parents=True, exist_ok=True)

def edit(rel, pairs):
    p = ROOT / rel; s = p.read_bytes().decode('utf-8')
    if not (bak / rel.replace('/', '__')).exists(): shutil.copy2(p, bak / rel.replace('/', '__'))
    for old, new, n in pairs:
        c = s.count(old)
        if c != n: raise SystemExit(f'STOP {rel}: "{old[:60]}" found {c}, expected {n}')
        s = s.replace(old, new)
    p.write_bytes(s.encode('utf-8'))

OLD_SITE = '../../20261103-main-website-r08-3d-ency-centre-right-v02.html'
# 1. catalogue script
cat = 'assets/js/shared-script-c650fa76d9e4.js'
edit(cat, [("const site='" + OLD_SITE + "';", '', 1),
           ("p.id+'-v02.html'", "'component-'+p.id+'.html'", 1)])
# 2. interceptor
ic = 'assets/js/shared-script-a376905ee515.js'
s = (ROOT / ic).read_bytes().decode('utf-8')
m = re.search(r'const routes=\{.*?\};', s)
edit(ic, [(m.group(0), '', 1),
          ('let route=routes[file];', r"let route=/^(component-[a-z0-9-]+|uav-components)\.html$/.test(file)?file.slice(0,-5):undefined;", 1),
          ("if(raw.includes('" + OLD_SITE[6:] + "'))route=raw.includes('#contact')?'contact':'home';",
           "if(file==='index.html'&&!route)route=raw.includes('#contact')?'contact':'home';", 1)])
# 3. pages
for p in sorted((ROOT / 'pages').glob('*.html')):
    b = p.read_bytes().decode('utf-8')
    if OLD_SITE not in b and 'uav-components-v02.html' not in b: continue
    edit('pages/' + p.name, [(OLD_SITE, '../index.html', b.count(OLD_SITE)),
                             ('uav-components-v02.html', 'uav-components.html', b.count('uav-components-v02.html'))])
# 4. content-hash rename
for rel in (cat, ic):
    old = ROOT / rel
    new = old.with_name('shared-script-' + hashlib.sha256(old.read_bytes()).hexdigest()[:12] + '.js')
    old.rename(new)
    srcc = ROOT / 'source-code' / old.name
    if srcc.exists(): shutil.copy2(new, ROOT / 'source-code' / new.name); srcc.unlink()
    n = 0
    for p in [ROOT / 'index.html', *sorted((ROOT / 'pages').glob('*.html'))]:
        b = p.read_bytes()
        if old.name.encode() in b:
            p.write_bytes(b.replace(old.name.encode(), new.name.encode())); n += 1
    print(old.name, '->', new.name, 'in', n, 'pages')
# Follow-up step (applied separately on 5 November 2026 after the direct-open check):
# the interceptor now returns when the page is not inside the site frame
# ('if(!route)return;' -> 'if(!route||parent===window)return;'), so direct links work.
