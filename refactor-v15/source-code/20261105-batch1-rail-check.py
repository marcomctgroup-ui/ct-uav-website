"""Check Navbar product rail images in v04: deferred at start, loaded on menu intent (1440 hover, 390 phone menu) and after EN/VI switch."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
U = 'http://127.0.0.1:8766/refactor-v06/index.html'
JS = "()=>[...document.querySelectorAll('#productRail img')].map(i=>({src:(i.getAttribute('src')||'').split('/').pop(),w:i.naturalWidth}))"
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', headless=True)
    pg = b.new_page(viewport={'width': 1440, 'height': 900}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(U, wait_until='domcontentloaded'); pg.wait_for_timeout(300)
    out['start_1440'] = pg.evaluate(JS)
    pg.hover('#productsToggle'); pg.wait_for_timeout(2000)
    out['hover_1440'] = pg.evaluate(JS)
    pg.screenshot(path=str(Path(__file__).resolve().parents[1]/'checks'/'rail-hover-1440.png'))
    pg.click('#languageButton'); pg.wait_for_timeout(1200)
    out['after_vi_1440'] = pg.evaluate(JS)
    pg.click('#languageButton'); pg.wait_for_timeout(800)
    m = b.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    m.on('pageerror', lambda e: errs.append(str(e)))
    m.goto(U, wait_until='domcontentloaded'); m.wait_for_timeout(300)
    out['start_390'] = m.evaluate(JS)
    m.click('#menuButton'); m.wait_for_timeout(800)
    if m.is_visible('#productsToggle'): m.click('#productsToggle')
    m.wait_for_timeout(2000)
    out['menu_390'] = m.evaluate(JS)
    m.screenshot(path=str(Path(__file__).resolve().parents[1]/'checks'/'rail-phone-menu-390.png'))
    q = b.new_page(viewport={'width': 1440, 'height': 900}); q.goto(U, wait_until='load'); q.wait_for_timeout(4500)
    out['idle_after_load'] = q.evaluate(JS)
    out['errors'] = errs
    b.close()
(Path(__file__).resolve().parents[1]/'checks'/'rail-check.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
for k, v in out.items(): print(k, v if k == 'errors' else [x['w'] for x in v])
