"""Batch 6 (components), 5 November 2026. Haykal: "delete some components and just keep 10 of it",
then chose the mixed set: one from each main type, all with workbook specifications and no
photo-identity question. All other component routes, pages, addresses, frames and unused images
are removed from v06. Removed pages and images are moved to checks/before-batch6/ (not deleted).
Run the cache-safe-names script and the header builder after this script."""
import json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAK = ROOT / 'checks/before-batch6'
KEEP = ['esc-100a-6s', 'ct-p42-16-5-vz', '5008', '3530', 'abc-2170p4',
        'ct-ib-14s', 'abc-ss-30ah', 'ct-hrc01', 'ct-ez40-ai', 'ct-amc01-61']
INTERNAL = ('checks', 'source-code', 'source-inputs', 'assets', 'pages')


def rd(p): return p.read_bytes().decode('utf-8')
def wr(p, s): p.write_bytes(s.encode('utf-8'))


def backup(p):
    dest = BAK / p.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(p, dest)


idx = rd(ROOT / 'index.html')
router_name = re.findall(r'assets/js/(shared-script-[0-9a-f]{12}\.js)', idx)[1]
router_path = ROOT / 'assets/js' / router_name
r = rd(router_path)
routes = json.loads(re.search(r'const routes=(\[.*?\])', r).group(1))
comp_routes = [x for x in routes if x.startswith('component-')]
keep_routes = {'component-' + k for k in KEEP}
missing = keep_routes - set(comp_routes)
if missing:
    raise SystemExit(f'STOP: unknown keep ids {missing}')
remove = [x for x in comp_routes if x not in keep_routes]
print('component routes', len(comp_routes), 'keep', len(keep_routes), 'remove', len(remove))

# 1. Router: routes list, title map, address map.
backup(router_path)
new_routes = [x for x in routes if x not in remove]
r = r.replace(re.search(r'const routes=(\[.*?\])', r).group(1), json.dumps(new_routes, separators=(',', ':')), 1)
m = re.search(r'\{"home":.*?\}', r)
titles = {k: v for k, v in json.loads(m.group(0)).items() if k not in remove}
r = r[:m.start()] + json.dumps(titles, ensure_ascii=False, separators=(',', ':')) + r[m.end():]
m = re.search(r'const PATHS=(\{.*?\});', r)
paths = {k: v for k, v in json.loads(m.group(1)).items() if k not in remove}
r = r[:m.start(1)] + json.dumps(paths, separators=(',', ':')) + r[m.end(1):]
wr(router_path, r)
(ROOT / 'source-code/20261105-batch5a-url-map.json').write_text(json.dumps(paths, indent=1, ensure_ascii=False), encoding='utf-8')

# 2. Frame template in the root shell and every kept entry page.
entries = [ROOT / 'index.html'] + [ROOT / p / 'index.html' for p in paths.values() if p]
for e in entries:
    s = rd(e)
    for route in remove:
        frame = re.search(r'<iframe[^>]*id="frame-' + re.escape(route) + r'"[^>]*>\s*</iframe>\s*', s)
        if not frame:
            raise SystemExit(f'STOP: frame {route} not in {e}')
        s = s[:frame.start()] + s[frame.end():]
    wr(e, s)

# 3. Remove entry folders and pages of removed components.
for route in remove:
    folder = ROOT / 'components' / route[len('component-'):]
    if folder.exists():
        shutil.rmtree(folder)  # generated copies of the shell; rebuildable
    page = ROOT / 'pages' / f'{route}.html'
    if page.exists():
        backup(page); page.unlink()

# 4. Catalogue data.
cat = next(p for p in (ROOT / 'assets/js').glob('*.js') if re.search(r'window\.CTComponents\s*=\s*\[', rd(p)))
backup(cat)
s = rd(cat)
m = re.search(r'window\.CTComponents\s*=\s*(\[.*?\]);', s, re.S)
data = [d for d in json.loads(m.group(1)) if d['id'] in KEEP]
if len(data) != 10:
    raise SystemExit(f'STOP: catalogue keeps {len(data)}')
wr(cat, s[:m.start(1)] + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + s[m.end(1):])

# 5. Served text after removal, then the image map and unused images.
def served():
    out = [ROOT / 'index.html', *(ROOT / 'pages').glob('*.html'), *(ROOT / 'assets/js').glob('*.js'), *(ROOT / 'assets/css').glob('*.css')]
    out += [p for p in ROOT.glob('*/**/index.html') if p.relative_to(ROOT).parts[0] not in INTERNAL]
    return out

imgmap = next(p for p in (ROOT / 'assets/js').glob('*.js') if 'const componentImages=' in rd(p))
backup(imgmap)
s = rd(imgmap)
m = re.search(r'const componentImages=(\{.*?\});', s, re.S)
images = json.loads(m.group(1))
other = '\n'.join(rd(p) for p in served() if p != imgmap)
kept = {k: v for k, v in images.items() if k in other or k.replace('assets/', '../assets/') in other}
wr(imgmap, s[:m.start(1)] + json.dumps(kept, separators=(',', ':')) + s[m.end(1):])
print('image map', len(images), '->', len(kept))

text = '\n'.join(rd(p) for p in served())
moved = 0
for img in sorted((ROOT / 'assets/img').iterdir()):
    if img.name in text:
        continue
    removed_page_text = any(img.name in rd(p) for p in (BAK / 'pages').glob('*.html')) or img.name in json.dumps(images)
    if removed_page_text:  # only images that belonged to removed components
        dest = BAK / 'assets/img' / img.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(img), str(dest)); moved += 1
print('images moved', moved)
