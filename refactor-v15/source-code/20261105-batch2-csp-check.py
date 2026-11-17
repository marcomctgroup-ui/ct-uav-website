"""Batch 2 check: every asset has exactly one Cache-Control rule; all routes, 3D pages and CT Ency run under the CSP (header server on 8767)."""
import json, re, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]; BASE = 'http://127.0.0.1:8767/'
HASHED = re.compile(r'-[0-9a-f]{10,12}(-[a-z0-9]+)?\.[a-z0-9]+$')
res = {'cache': {'checked': 0, 'problems': []}}
for f in sorted(p for p in (ROOT / 'assets').rglob('*') if p.is_file()):
    rel = '/' + f.relative_to(ROOT).as_posix()
    req = urllib.request.Request(BASE.rstrip('/') + rel, method='HEAD')
    cc = urllib.request.urlopen(req).headers.get('Cache-Control', '')
    import hashlib
    t = re.search(r'-([0-9a-f]{10,12})(?:-[a-z0-9]+)?\.[a-z0-9]+$', f.name)
    real = bool(t) and any(h(f.read_bytes()).hexdigest().startswith(t.group(1)) for h in (hashlib.sha256, hashlib.md5, hashlib.sha1))
    want = 'public, max-age=31536000, immutable' if real else ''
    res['cache']['checked'] += 1
    if cc != want: res['cache']['problems'].append((rel, cc))
routes = json.loads(re.search(r'const routes=(\[.*?\]);', (ROOT / 'assets/js/shared-script-0d4957c7241f.js').read_text(encoding='utf-8')).group(1))
rows = []
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', headless=True)
    pg = b.new_page(viewport={'width': 1440, 'height': 900}); msgs = []
    pg.on('console', lambda m: m.type in ('error', 'warning') and msgs.append(m.text))
    pg.on('pageerror', lambda e: msgs.append('PAGEERROR ' + str(e)))
    for r in routes:
        msgs.clear(); pg.goto(f'{BASE}index.html#{r}', wait_until='load'); pg.wait_for_timeout(1000)
        ok = pg.evaluate("r=>{const f=r==='home'?document.getElementById('heroFrame'):document.getElementById('frame-'+r);return !!f&&f.contentDocument.readyState==='complete'&&f.contentDocument.body.innerText.trim().length>0}", r)
        rows.append({'route': r, 'ok': ok and not msgs, 'messages': list(msgs)})
    three = {}
    for r in ['decarb54', 'ct-frona-44', 'ct-fyran-256', 'ct-pegas-230', 'ct-fyran-firefighting']:
        msgs.clear(); pg.goto(f'{BASE}index.html#{r}', wait_until='load'); pg.wait_for_timeout(1500)
        pg.evaluate("r=>{const f=document.getElementById('frame-'+r);const st=f.contentDocument.querySelector('[data-ps-stage],[data-u3d-model]');f.contentWindow.scrollTo(0,st.getBoundingClientRect().top+f.contentWindow.scrollY-100)}", r)
        pg.wait_for_timeout(9000)
        three[r] = pg.evaluate("r=>{const d=document.getElementById('frame-'+r).contentDocument;const st=d.querySelector('[data-ps-stage],[data-u3d-model]');return {canvas:d.querySelectorAll('canvas').length,error:st.dataset.resourceError||null,fallback:[...d.querySelectorAll('p,div,span')].filter(e=>/could not load|not available/i.test(e.textContent)&&e.children.length===0&&e.offsetParent).length}}", r)
        three[r]['messages'] = list(msgs)
        three[r]['ok'] = three[r]['canvas'] > 0 and not three[r]['error'] and not three[r]['fallback'] and not msgs
        if r == 'decarb54': pg.screenshot(path=str(ROOT / 'checks' / 'csp-3d-decarb54.png'))
    msgs.clear(); pg.goto(BASE + 'index.html', wait_until='load'); pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('cuLauncher').click()"); pg.wait_for_timeout(7000)
    ency = pg.evaluate("()=>({canvas:document.querySelectorAll('#cuWidget canvas').length,bytes:document.getElementById('ctEncyModel').ctuavBytes?.length||0})")
    ency['messages'] = list(msgs); ency['ok'] = ency['canvas'] > 0 and ency['bytes'] > 0 and not msgs
    pg.screenshot(path=str(ROOT / 'checks' / 'csp-ct-ency.png'))
    b.close()
res.update(routes={'rows': len(rows), 'fail': [x for x in rows if not x['ok']]}, three_d=three, ct_ency=ency)
(ROOT / 'checks' / 'batch2-csp-check.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
print('cache checked', res['cache']['checked'], 'problems', len(res['cache']['problems']), res['cache']['problems'][:5])
print('routes', len(rows), 'fail', len(res['routes']['fail']), res['routes']['fail'][:3])
print('3d', {k: v['ok'] for k, v in three.items()}, [v['messages'] for v in three.values() if v['messages']][:2])
print('ency', ency)
