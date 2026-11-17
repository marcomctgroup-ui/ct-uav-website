"""Batch 7 check (refactor v07, 6 November 2026). Uses the header server on port 8767, so the CSP is active.

    python projects/main-website/refactor-v07/source-code/20261106-batch7-check.py

1. Direct open of every page address that exists in v07: shown route, page errors, CSP messages, HTTP errors.
2. Cart flow at 1440 and 390 px: Add to Cart on a line page, the count in another page, the cart window below
   the Navbar, form errors, result screen, EN/VI labels, component card and detail buttons, no page overflow.
3. Model images on all 16 line pages load; footer social colours and hover colour change.
Writes checks/20261106-batch7/batch7-check.json and screenshots.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = 'http://127.0.0.1:8767/'
OUT = ROOT / 'checks/20261106-batch7'
url_map = json.loads((ROOT / 'source-code/20261105-batch5a-url-map.json').read_text(encoding='utf-8'))
paths = {route: path for route, path in url_map.items() if (ROOT / path / 'index.html').exists() or path == ''}
res = {'sweep': [], 'flows': {}, 'line_images': [], 'social': None}

FRAME = "(sel)=>{const f=[...document.querySelectorAll('iframe')].find(x=>{try{return x.contentDocument&&x.contentDocument.querySelector(sel)}catch(e){return false}});return f?f.name||f.id:null}"


def visible_route(pg):
    return pg.evaluate("""(()=>{const f=[...document.querySelectorAll('iframe')].find(f=>f.offsetParent!==null&&!f.closest('[hidden]')&&f.getBoundingClientRect().height>200&&!f.src.endsWith('hero.html'));
      const home=document.getElementById('homeView');if(home&&!home.hidden)return 'home';return f?f.src.split('/pages/')[1].replace('.html',''):null;})()""")


def frame_with(pg, selector):
    for fr in pg.frames:
        try:
            if fr.query_selector(selector):
                return fr
        except Exception:
            pass
    return None


def watch(pg):
    log = {'errors': [], 'csp': [], 'http': []}
    pg.on('pageerror', lambda e: log['errors'].append(str(e)))
    pg.on('console', lambda m: log['csp'].append(m.text) if 'Content Security Policy' in m.text or 'Refused' in m.text else None)
    pg.on('response', lambda r: log['http'].append(f'{r.status} {r.url}') if r.status >= 400 else None)
    return log


with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge')

    # 1. Direct opens
    pg = browser.new_page(viewport={'width': 1440, 'height': 900})
    log = watch(pg)
    for route, path in paths.items():
        for key in log:
            log[key].clear()
        pg.goto(SITE + path)
        pg.wait_for_timeout(1600)
        row = {'route': route, 'path': path, 'shown': visible_route(pg), 'title': pg.title(), **{k: list(v) for k, v in log.items()}}
        row['ok'] = (row['shown'] == route or (route == 'home' and row['shown'] == 'home')) and not row['errors'] and not row['csp'] and not row['http']
        res['sweep'].append(row)
    pg.close()

    # 2. Flows at two widths
    for w, h in ((1440, 900), (390, 844)):
        ctx = browser.new_context(viewport={'width': w, 'height': h})
        pg = ctx.new_page()
        log = watch(pg)
        f = {}
        pg.goto(SITE + 'applications/agricultural-uav/')
        pg.wait_for_timeout(3000)
        fr = frame_with(pg, '.pl-models')
        buttons = fr.query_selector_all('.pl-model [data-cart-add]')
        f['line_rows'] = len(buttons)
        buttons[0].scroll_into_view_if_needed()
        buttons[0].click()
        buttons[1].click()
        pg.wait_for_timeout(400)
        f['line_button_after_click'] = buttons[0].inner_text()
        f['fab_after_two'] = fr.eval_on_selector('.cart-fab', 'b=>b.getAttribute("aria-label")')
        f['line_overflow'] = fr.evaluate('document.documentElement.scrollWidth>innerWidth')
        pg.screenshot(path=str(OUT / f'flow-line-{w}.png'))
        pg.goto(SITE + 'products/ct-crova-254/')
        pg.wait_for_timeout(3500)
        fr = frame_with(pg, '.product-bar__cart')
        f['product_fab_count'] = fr.eval_on_selector('.cart-fab__count', 'b=>b.textContent')
        bar = fr.eval_on_selector('.product-bar__cart .cart-add', 'b=>{const r=b.getBoundingClientRect();return [r.left,r.right,r.top,r.height,innerWidth]}')
        f['product_bar_button'] = bar
        f['product_bar_button_visible'] = bar[0] >= 0 and bar[1] <= bar[4] and bar[3] >= 44
        fr.click('.product-bar__cart .cart-add')
        pg.wait_for_timeout(300)
        f['product_count_after_bar_click'] = fr.eval_on_selector('.cart-fab__count', 'b=>b.textContent')
        f['product_overflow'] = fr.evaluate('document.documentElement.scrollWidth>innerWidth')
        pg.screenshot(path=str(OUT / f'flow-product-{w}.png'))
        fr.click('.cart-fab')
        pg.wait_for_timeout(400)
        f['dialog_open'] = fr.eval_on_selector('.cart-dialog', 'd=>d.open')
        header_bottom = pg.evaluate("document.getElementById('globalHeader').getBoundingClientRect().bottom")
        dialog_top = fr.eval_on_selector('.cart-dialog', 'd=>d.getBoundingClientRect().top')
        f['dialog_below_header'] = [round(dialog_top), round(header_bottom), dialog_top >= header_bottom - 1]
        f['dialog_items'] = fr.eval_on_selector_all('.cart-item__name', 'n=>n.map(x=>x.textContent)')
        pg.screenshot(path=str(OUT / f'flow-cart-{w}.png'))
        fr.click('.cart-panel button[type=submit]')
        pg.wait_for_timeout(200)
        f['empty_submit_errors'] = fr.eval_on_selector_all('.cart-field__error', 'n=>n.map(x=>x.textContent).filter(Boolean)')
        fr.fill('#cart-name', 'Test Buyer')
        fr.fill('#cart-email', 'buyer@example.com')
        fr.fill('#cart-phone', '+84 900 000 000')
        fr.click('.cart-panel button[type=submit]')
        pg.wait_for_timeout(300)
        f['done_title'] = fr.eval_on_selector('#cartDialogTitle', 'n=>n.textContent')
        pg.screenshot(path=str(OUT / f'flow-done-{w}.png'))
        fr.click('.cart-primary')
        pg.wait_for_timeout(200)
        # Language
        pg.evaluate("document.getElementById('languageButton').click()")
        pg.wait_for_timeout(900)
        f['vi_bar_label'] = fr.eval_on_selector('.product-bar__cart .cart-add', 'b=>b.innerText')
        f['vi_fab_label'] = fr.eval_on_selector('.cart-fab__label', 'b=>b.textContent')
        pg.evaluate("document.getElementById('languageButton').click()")
        pg.wait_for_timeout(900)
        f['en_again_bar_label'] = fr.eval_on_selector('.product-bar__cart .cart-add', 'b=>b.innerText')
        # Components
        pg.goto(SITE + 'components/')
        pg.wait_for_timeout(3500)
        fr = frame_with(pg, '#grid .card')
        f['component_cards'] = fr.eval_on_selector_all('#grid .card', 'c=>c.map(x=>x.querySelector("h2").innerText.replace("\\n"," / "))')
        fr.click('#grid .card .cart-add')
        pg.wait_for_timeout(300)
        f['component_count'] = fr.eval_on_selector('.cart-fab__count', 'b=>b.textContent')
        f['components_overflow'] = fr.evaluate('document.documentElement.scrollWidth>innerWidth')
        pg.screenshot(path=str(OUT / f'flow-components-{w}.png'), full_page=False)
        pg.goto(SITE + 'components/ct-hrc01/')
        pg.wait_for_timeout(3500)
        fr = frame_with(pg, '.product-copy h1')
        f['component_detail'] = fr.eval_on_selector('.product-copy', 'c=>[c.querySelector("h1").textContent,c.querySelector(".component-code").textContent,c.querySelector(".cart-add").innerText]')
        f['component_detail_overflow'] = fr.evaluate('document.documentElement.scrollWidth>innerWidth')
        f.update({k: list(v) for k, v in log.items()})
        res['flows'][w] = f
        ctx.close()

    # 3. Line page images and social colours
    pg = browser.new_page(viewport={'width': 1440, 'height': 900})
    for n in range(1, 17):
        pg.goto(SITE + f'pages/line-{n:02d}.html')
        pg.wait_for_timeout(500)
        pg.evaluate("document.querySelectorAll('.pl-model__media img').forEach(i=>i.loading='eager')")
        pg.wait_for_timeout(700)
        res['line_images'].append({'page': f'line-{n:02d}', 'rows': pg.evaluate("document.querySelectorAll('.pl-model').length"),
                                   'images': pg.evaluate("[...document.querySelectorAll('.pl-model__media img')].map(i=>[i.alt||'(pending)',i.complete&&i.naturalWidth>0])")})
    pg.goto(SITE + 'pages/line-09.html')
    pg.wait_for_timeout(800)
    link = pg.query_selector('.site-footer__social a[aria-label="YouTube"]')
    link.scroll_into_view_if_needed()
    before = pg.evaluate("a=>[getComputedStyle(a).backgroundColor,getComputedStyle(a).color]", link)
    link.hover()
    pg.wait_for_timeout(500)
    after = pg.evaluate("a=>[getComputedStyle(a).backgroundColor,getComputedStyle(a).color]", link)
    res['social'] = {'youtube_rest': before, 'youtube_hover': after, 'changes': before != after}
    pg.screenshot(path=str(OUT / 'social-hover-1440.png'))
    pg.close()
    browser.close()

res['summary'] = {'sweep_total': len(res['sweep']), 'sweep_fail': [r['route'] for r in res['sweep'] if not r['ok']],
                  'flow_errors': {w: f['errors'] + f['csp'] + f['http'] for w, f in res['flows'].items()},
                  'line_images_failed': [(r['page'], i[0]) for r in res['line_images'] for i in r['images'] if not i[1]]}
(OUT / 'batch7-check.json').write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(res['summary'], indent=1, ensure_ascii=False))
for w, f in res['flows'].items():
    print(w, json.dumps({k: v for k, v in f.items() if k not in ('errors', 'csp', 'http')}, ensure_ascii=False))
print(json.dumps(res['social']))
