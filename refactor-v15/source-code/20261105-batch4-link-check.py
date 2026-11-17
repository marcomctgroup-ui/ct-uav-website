"""Batch 4 check: real-file links, link interceptor, merged stylesheet, CT-FRYAN name. Port 8766."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8766/refactor-v06/'
OUT = Path(__file__).resolve().parents[1] / 'checks/20261105-batch4'
res = {}
def frame_of(pg, name):
    for f in pg.frames:
        if f.url.split('?')[0].endswith('/pages/' + name + '.html'): return f
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    for w, h in ((1440, 900), (390, 844)):
        pg = b.new_page(viewport={'width': w, 'height': h}); errs = []; failed = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('requestfailed', lambda r: failed.append(r.url))
        r = {}
        pg.goto(BASE + 'index.html#uav-components'); pg.wait_for_timeout(3500)
        r['stylesheets'] = pg.evaluate("document.styleSheets.length")
        f = frame_of(pg, 'uav-components')
        href = f.eval_on_selector('#grid a[href]', 'a=>a.getAttribute("href")')
        r['card_href'] = href
        f.eval_on_selector('#grid a[href]', 'a=>a.click()'); pg.wait_for_timeout(2500)
        r['after_card_hash'] = pg.evaluate('location.hash')
        cf = frame_of(pg, r['after_card_hash'][1:])
        r['component_hrefs'] = sorted(set(cf.eval_on_selector_all('a[href]', 'as=>as.map(a=>a.getAttribute("href")).filter(h=>!h.startsWith("#"))')))
        cf.eval_on_selector('a[href="../index.html#contact"]', 'a=>a.click()'); pg.wait_for_timeout(2500)
        r['after_contact_hash'] = pg.evaluate('location.hash')
        pg.goto(BASE + 'index.html#uav-components'); pg.wait_for_timeout(3000)
        f = frame_of(pg, 'uav-components')
        f.eval_on_selector('a[href="../index.html"]', 'a=>a.click()'); pg.wait_for_timeout(2500)
        r['after_home_crumb_hash'] = pg.evaluate('location.hash')
        pg.goto(BASE + 'index.html#ct-fyran-firefighting'); pg.wait_for_timeout(3500)
        r['title_fryan'] = pg.title()
        ff = frame_of(pg, 'ct-fyran-firefighting')
        r['h1_fryan'] = ff.eval_on_selector('h1', 'e=>e.textContent')
        pg.screenshot(path=str(OUT / f'fryan-{w}.png'))
        pg.goto(BASE + 'index.html'); pg.wait_for_timeout(4000)
        pg.screenshot(path=str(OUT / f'home-{w}.png'))
        pg.goto(BASE + 'index.html#component-payload-drop'); pg.wait_for_timeout(4000)
        r['payload_drop_failed'] = [u for u in failed if 'payload-drop' in u]
        r['errors'] = errs
        res[w] = r; pg.close()
    # direct open, outside the shell
    pg = b.new_page(); pg.goto(BASE + 'pages/component-10020.html'); pg.wait_for_timeout(1500)
    with pg.expect_navigation(): pg.eval_on_selector('a[href="../index.html#contact"]', 'a=>a.click()')
    pg.wait_for_timeout(1500)
    res['direct_contact_url'] = pg.url; res['direct_contact_title'] = pg.title()
    b.close()
(OUT / 'link-check.json').write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(res, indent=1, ensure_ascii=False))
