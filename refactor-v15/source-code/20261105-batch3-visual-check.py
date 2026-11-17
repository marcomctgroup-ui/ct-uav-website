"""Batch 3 visual checks: phone hero tabs (320/375/390/480/768), loading placeholder on a direct link, titles."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]; U = 'http://127.0.0.1:8766/refactor-v06/index.html'; out = {}
TABS = "()=>{const d=document.getElementById('heroFrame').contentDocument;return [...d.querySelectorAll('.slide-choice')].map(b=>{const l=b.querySelector('.slide-label');const r=b.getBoundingClientRect();return {text:l.textContent,lines:Math.round(l.getBoundingClientRect().height/parseFloat(getComputedStyle(l).lineHeight||16)),clipped:l.scrollWidth>l.clientWidth+1,h:Math.round(r.height),w:Math.round(r.width),font:getComputedStyle(l).fontSize}})}"
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', headless=True)
    for w in [320, 375, 390, 480, 768]:
        pg = b.new_page(viewport={'width': w, 'height': 812}); pg.goto(U, wait_until='load'); pg.wait_for_timeout(2500)
        out[f'tabs_{w}'] = pg.evaluate(TABS)
        if w in (320, 390): pg.screenshot(path=str(ROOT/'checks'/f'batch3-hero-tabs-{w}.png'))
        pg.close()
    pg = b.new_page(viewport={'width': 1440, 'height': 900})
    seen = []
    pg.goto(U + '#contact', wait_until='commit')
    for i in range(40):
        try:
            seen.append(pg.evaluate("()=>{const l=document.getElementById('pageLoading');return l?(!l.hidden):null}"))
        except Exception: seen.append('nav')
        if seen[-1] is True and i < 39 and 'shot' not in out:
            pg.screenshot(path=str(ROOT/'checks'/'batch3-loading-1440.png')); out['shot'] = True
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(1500)
    out['loading_seen'] = True in seen; out['loading_hidden_end'] = pg.evaluate("()=>document.getElementById('pageLoading').hidden")
    titles = {}
    for r in ['home', 'ct-glova', 'component-ct-p24-11-5-vz', 'ct-fyran-firefighting', 'decarb22', 'line-05', 'about', 'contact']:
        pg.goto(U + '#' + r, wait_until='load'); pg.wait_for_timeout(600); titles[r] = pg.title()
    out['titles'] = titles
    pg.goto(U + '#line-05', wait_until='load'); pg.wait_for_timeout(1500); pg.evaluate("location.hash='home'"); pg.wait_for_timeout(500)
    out['loading_after_home'] = pg.evaluate("()=>document.getElementById('pageLoading').hidden")
    b.close()
(ROOT/'checks'/'batch3-visual.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(out, indent=1, ensure_ascii=False))
