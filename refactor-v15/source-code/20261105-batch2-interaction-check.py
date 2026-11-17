"""Batch 2: interactions under the CSP on the header server (8767)."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]; U = 'http://127.0.0.1:8767/index.html'
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', headless=True)
    pg = b.new_page(viewport={'width': 1440, 'height': 900}); msgs = []
    pg.on('console', lambda m: m.type in ('error', 'warning') and msgs.append(m.text))
    pg.on('pageerror', lambda e: msgs.append(str(e)))
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(5000)
    out['hero_video'] = pg.evaluate("()=>[...document.getElementById('heroFrame').contentDocument.querySelectorAll('video')].map(v=>({paused:v.paused,t:Math.round(v.currentTime*10)/10,src:(v.currentSrc||'').split('/').pop()}))")
    pg.hover('#productsToggle'); pg.wait_for_timeout(1500)
    out['rail'] = pg.evaluate("()=>[...document.querySelectorAll('#productRail img')].map(i=>i.naturalWidth)")
    pg.click('#languageButton'); pg.wait_for_timeout(1000)
    out['lang'] = pg.evaluate("()=>document.documentElement.lang")
    pg.click('#languageButton'); pg.wait_for_timeout(500)
    pg.goto(U + '#contact', wait_until='load'); pg.wait_for_timeout(2500)
    out['contact'] = pg.evaluate("""async()=>{const d=document.getElementById('frame-contact').contentDocument;d.getElementById('contactName').value='Test';d.getElementById('contactEmail').value='test@example.test';d.getElementById('contactForm').requestSubmit();await new Promise(r=>setTimeout(r,600));return d.getElementById('contactStatus').textContent}""")
    out['messages'] = msgs
    m = b.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True); mm = []
    m.on('console', lambda x: x.type in ('error', 'warning') and mm.append(x.text)); m.on('pageerror', lambda e: mm.append(str(e)))
    m.goto(U, wait_until='load'); m.wait_for_timeout(1500); m.click('#menuButton'); m.wait_for_timeout(800)
    if m.is_visible('#productsToggle'): m.click('#productsToggle')
    m.wait_for_timeout(1500)
    out['phone_rail'] = m.evaluate("()=>[...document.querySelectorAll('#productRail img')].map(i=>i.naturalWidth)"); out['phone_messages'] = mm
    b.close()
(ROOT / 'checks' / 'batch2-interactions.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(out, indent=1))
