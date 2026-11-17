"""Batch 5A check: real addresses, history, legacy # links, direct entry opens. Port 8766 (no headers).
Usage: python source-code/20261105-batch5a-url-check.py [--sweep]"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = 'http://127.0.0.1:8766/refactor-v06/'
OUT = ROOT / 'checks/20261105-batch5a'; OUT.mkdir(parents=True, exist_ok=True)
paths = json.loads((ROOT / 'source-code/20261105-batch5a-url-map.json').read_text(encoding='utf-8'))
res = {'flows': {}, 'sweep': []}


def visible_route(pg):
    return pg.evaluate("""(()=>{const f=[...document.querySelectorAll('iframe')].find(f=>f.offsetParent!==null&&!f.closest('[hidden]')&&f.getBoundingClientRect().height>200&&!f.src.endsWith('hero.html'));
      const home=document.getElementById('homeView');if(home&&!home.hidden)return 'home';return f?f.src.split('/pages/')[1].replace('.html',''):null;})()""")


with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    for w, h in ((1440, 900), (390, 844)):
        pg = b.new_page(viewport={'width': w, 'height': h}); errs, failed = [], []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('requestfailed', lambda r: failed.append(r.url))
        pg.on('response', lambda r: failed.append(f'{r.status} {r.url}') if r.status >= 400 else None)
        f = {}
        pg.goto(SITE); pg.wait_for_timeout(3000)
        f['home'] = [pg.url, visible_route(pg)]
        pg.eval_on_selector('a.hp-card[data-route="decarb22"]', 'a=>a.click()'); pg.wait_for_timeout(2500)
        f['card_decarb22'] = [pg.url, pg.title(), visible_route(pg)]
        pg.go_back(); pg.wait_for_timeout(2000); f['back'] = [pg.url, visible_route(pg)]
        pg.go_forward(); pg.wait_for_timeout(2000); f['forward'] = [pg.url, visible_route(pg)]
        pg.goto(SITE + 'index.html#contact'); pg.wait_for_timeout(3000)
        f['legacy_hash_contact'] = [pg.url, pg.title(), visible_route(pg)]
        pg.evaluate("window.ctuavDemo.navigate('ct-pegas-230')"); pg.wait_for_timeout(2500)
        f['navigate_api'] = [pg.url, pg.title(), visible_route(pg)]
        pg.goto(SITE + 'products/ct-fryan/'); pg.wait_for_timeout(3500)
        f['direct_ct_fryan'] = [pg.url, pg.title(), visible_route(pg)]
        pg.screenshot(path=str(OUT / f'direct-ct-fryan-{w}.png'))
        pg.goto(SITE + 'components/'); pg.wait_for_timeout(3500)
        fr = next(x for x in pg.frames if x.url.endswith('/pages/uav-components.html'))
        fr.eval_on_selector('#grid a[href]', 'a=>a.click()'); pg.wait_for_timeout(2500)
        f['component_card'] = [pg.url, pg.title(), visible_route(pg)]
        pg.reload(); pg.wait_for_timeout(3500)
        f['reload_component'] = [pg.url, pg.title(), visible_route(pg)]
        pg.screenshot(path=str(OUT / f'reload-component-{w}.png'))
        f['errors'] = errs; f['failed'] = failed
        res['flows'][w] = f; pg.close()
    if '--sweep' in sys.argv:
        pg = b.new_page(viewport={'width': 1440, 'height': 900})
        for route, path in paths.items():
            errs, failed = [], []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('response', lambda r: failed.append(f'{r.status} {r.url}') if r.status >= 400 else None)
            pg.goto(SITE + path); pg.wait_for_timeout(1800)
            row = {'route': route, 'path': path, 'url_kept': pg.url == SITE + path, 'shown': visible_route(pg),
                   'title': pg.title(), 'errors': list(errs), 'http_errors': list(failed)}
            row['ok'] = row['url_kept'] and row['shown'] == route and not errs and not failed
            res['sweep'].append(row)
        pg.close()
    b.close()
(OUT / 'url-check.json').write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(res['flows'], indent=1, ensure_ascii=False))
if res['sweep']:
    bad = [r for r in res['sweep'] if not r['ok']]
    print('sweep', len(res['sweep']), 'fail', len(bad)); [print(x) for x in bad[:10]]
