"""Batch 5A follow-up (guardian WARN 1), 5 November 2026. 57 component routes had no entry in the
router title map, so their address showed "CT UAV" and later "component-ID | CT UAV".
This adds "<page h1> | CT UAV" (the page's own model name) to the map and to each entry <title>.
The router gets a new content-hash name; index and all entries are updated; run the header builder after."""
import hashlib, html, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
idx = (ROOT / 'index.html').read_bytes().decode('utf-8')
old = re.search(r'assets/js/(shared-script-[0-9a-f]{12}\.js)', idx.split('shared-script-6100184ab7c6.js', 1)[1]).group(1)
r = (ROOT / 'assets/js' / old).read_bytes().decode('utf-8')
m = re.search(r'\{"home":.*?\}', r); titles = json.loads(m.group(0))
routes = json.loads(re.search(r'const routes=(\[.*?\])', r).group(1))
paths = json.loads((ROOT / 'source-code/20261105-batch5a-url-map.json').read_text(encoding='utf-8'))
added = {}
for route in routes:
    if route in titles: continue
    page = (ROOT / 'pages' / f'{route}.html').read_bytes().decode('utf-8')
    h1 = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', re.search(r'<h1\b[^>]*>(.*?)</h1>', page, re.S).group(1)))).strip()
    if not h1: raise SystemExit('STOP no h1 ' + route)
    added[route] = titles[route] = f'{h1} | CT UAV'
r = r[:m.start()] + json.dumps(titles, ensure_ascii=False, separators=(',', ':')) + r[m.end():]
new = 'shared-script-' + hashlib.sha256(r.encode('utf-8')).hexdigest()[:12] + '.js'
for d in ('assets/js', 'source-code'):
    (ROOT / d / new).write_bytes(r.encode('utf-8'))
    if (ROOT / d / old).exists(): (ROOT / d / old).unlink()
entries = [ROOT / 'index.html'] + [ROOT / p / 'index.html' for p in paths.values() if p]
for e in entries:
    s = e.read_bytes().decode('utf-8')
    if s.count(old) != 1: raise SystemExit('STOP ref ' + str(e))
    s = s.replace(old, new)
    route = next((k for k, v in paths.items() if v and e == ROOT / v / 'index.html'), None)
    if route in added:
        t = html.escape(added[route], quote=False)
        s = re.sub(r'<title>.*?</title>', '<title>' + t + '</title>', s, count=1, flags=re.S)
        s = re.sub(r'(<meta property="og:title" content=")[^"]*"', lambda mm: mm.group(1) + html.escape(added[route]) + '"', s, count=1)
    e.write_bytes(s.encode('utf-8'))
print('router', old, '->', new, 'titles added', len(added))
for f in ('20261105-batch2-csp-check.py', '20261105-batch1-route-sweep.py', '20261105-batch3-vi-scan.py'):
    p = ROOT / 'source-code' / f; p.write_text(p.read_text(encoding='utf-8').replace(old[:-3], new[:-3]), encoding='utf-8')
