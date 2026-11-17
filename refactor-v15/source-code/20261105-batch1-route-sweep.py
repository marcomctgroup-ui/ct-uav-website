"""Open every route of refactor-v04 at 1440 and 390 px. Record script errors, failed requests, overflow and visible frame."""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8766/refactor-v06/index.html'
root = Path(__file__).resolve().parents[1]
routes = json.loads(re.search(r'const routes=(\[.*?\]);', (root/'assets/js'/'shared-script-0d4957c7241f.js').read_text(encoding='utf-8')).group(1))
rows = []
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', headless=True)
    for w, h in [(1440, 900), (390, 844)]:
        ctx = b.new_context(viewport={'width': w, 'height': h})
        pg = ctx.new_page()
        errs, bad = [], []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.on('requestfailed', lambda r: bad.append(r.url))
        pg.on('response', lambda r: r.status >= 400 and bad.append(f'{r.status} {r.url}'))
        for r in routes:
            errs.clear(); bad.clear()
            pg.goto(f'{BASE}#{r}', wait_until='load')
            pg.wait_for_timeout(1200)
            info = pg.evaluate("""r=>{const f=r==='home'?document.getElementById('heroFrame'):document.getElementById('frame-'+r);
              const d=f&&f.contentDocument;return {frame:!!f,hidden:f?f.hidden:null,ready:d?d.readyState:null,
              href:d?d.location.pathname.split('/').pop():null,text:d?d.body.innerText.trim().length:0,
              overflow:document.documentElement.scrollWidth>innerWidth||(d?d.documentElement.scrollWidth>d.defaultView.innerWidth:false),
              frames:document.querySelectorAll('iframe').length}}""", r)
            ok = info['frame'] and not info['hidden'] and info['ready'] == 'complete' and info['text'] > 0 and not info['overflow'] and not errs and not bad
            rows.append({'width': w, 'route': r, 'ok': ok, **info, 'errors': list(errs), 'failed': list(bad)})
        ctx.close()
    b.close()
fails = [x for x in rows if not x['ok']]
out = root / 'checks' / 'route-sweep.json'
out.write_text(json.dumps({'base': BASE, 'rows': len(rows), 'fail': len(fails), 'items': rows}, indent=1), encoding='utf-8')
print('rows', len(rows), 'fail', len(fails))
for x in fails: print(x['width'], x['route'], {k: x[k] for k in ('hidden','ready','href','text','overflow','errors','failed')})
