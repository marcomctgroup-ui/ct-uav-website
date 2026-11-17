"""Batch 3: find visible English text that stays English in VI mode, on every route (8766)."""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8766/refactor-v06/index.html'
routes = json.loads(re.search(r'const routes=(\[.*?\]);', (ROOT/'assets/js/shared-script-0d4957c7241f.js').read_text(encoding='utf-8')).group(1))
EN = re.compile(r'\b(the|and|of|with|for|to|View|Contact|Explore|Browse|Search|Home|Skip|Back|More|Read|Details|Motor|Controller|Filter|All|Reset|Category|order|image|images|products?|Sales|Learn|Download|Send|Name|Email|Message|Phone|Organization|Select|Close|Open|Next|Previous)\b')
JS = r"""r=>{const f=r==='home'?document.getElementById('heroFrame'):document.getElementById('frame-'+r);const docs=[document,f&&f.contentDocument].filter(Boolean);const out=new Set();
for(const d of docs){const w=d.createTreeWalker(d.body,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){const t=n.textContent.trim();if(t.length<3)continue;const e=n.parentElement;if(!e||e.closest('script,style,[hidden],[aria-hidden="true"],.ce-mascot'))continue;const cs=d.defaultView.getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden')continue;if(!e.getClientRects().length&&!e.classList.contains('skip'))continue;out.add(t.replace(/\s+/g,' ').slice(0,140))}}return [...out]}"""
rows = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', headless=True)
    pg = b.new_page(viewport={'width': 1440, 'height': 900})
    for r in routes:
        pg.goto(f'{BASE}#{r}', wait_until='load'); pg.wait_for_timeout(1500)
        en = set(pg.evaluate(JS, r))
        pg.evaluate("document.getElementById('languageButton').click()"); pg.wait_for_timeout(1200)
        vi = set(pg.evaluate(JS, r))
        same = sorted(t for t in vi & en if EN.search(t))
        if same: rows[r] = same
        pg.evaluate("document.getElementById('languageButton').click()"); pg.wait_for_timeout(400)
    b.close()
out = ROOT/'checks'/sys.argv[2] if len(sys.argv) > 2 else ROOT/'checks'/'batch3-vi-scan-before.json'
out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding='utf-8')
from collections import Counter
c = Counter(t for v in rows.values() for t in v)
print('routes with leftovers', len(rows), 'unique strings', len(c))
for t, n in c.most_common(60): print(n, t)
