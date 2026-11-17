"""Batch 6 smoothness measure: scroll Home and one product page with 4x CPU slowdown (phone-like),
record frame times with requestAnimationFrame. Optional test CSS can switch effects off.
Usage: python 20261105-batch6-scroll-check.py <site-url> <label> [nofx]"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE, LABEL = sys.argv[1], sys.argv[2]
NOFX = 'nofx' in sys.argv
OUT = Path(__file__).resolve().parents[1] / 'checks/20261105-batch6'; OUT.mkdir(parents=True, exist_ok=True)
FX_OFF = '*,*::before,*::after{backdrop-filter:none!important;-webkit-backdrop-filter:none!important;filter:none!important}'
MEASURE = """async (sel)=>{const el=sel?document.querySelector(sel):document.scrollingElement;const t=[];let last=performance.now(),run=true;
const tick=n=>{t.push(n-last);last=n;if(run)requestAnimationFrame(tick)};requestAnimationFrame(tick);
const max=el.scrollHeight-el.clientHeight;const start=performance.now();
await new Promise(res=>{const step=()=>{const k=(performance.now()-start)/6000;el.scrollTop=max*Math.min(k,1);if(k<1)requestAnimationFrame(step);else res()};step()});
run=false;t.shift();const long=t.filter(x=>x>50).length;const avg=t.reduce((a,b)=>a+b,0)/t.length;
return {frames:t.length,avg_ms:+avg.toFixed(1),fps:+(1000/avg).toFixed(1),long_frames:long,long_pct:+(100*long/t.length).toFixed(1),worst_ms:+Math.max(...t).toFixed(0)}}"""
res = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    for w, h in ((390, 844), (1440, 900)):
        pg = b.new_page(viewport={'width': w, 'height': h})
        cdp = pg.context.new_cdp_session(pg); cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
        pg.goto(SITE); pg.wait_for_timeout(6000)
        if NOFX:
            pg.add_style_tag(content=FX_OFF)
        res[f'home-{w}'] = pg.evaluate(MEASURE, '#homeView')
        pg.goto(SITE + 'products/decarb-22/'); pg.wait_for_timeout(6000)
        f = next(x for x in pg.frames if x.url.endswith('/pages/decarb22.html'))
        if NOFX:
            f.add_style_tag(content=FX_OFF); pg.add_style_tag(content=FX_OFF)
        res[f'decarb22-{w}'] = f.evaluate(MEASURE, None)
        pg.close()
    b.close()
(OUT / f'scroll-{LABEL}.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
for k, v in res.items():
    print(LABEL, k, v)
