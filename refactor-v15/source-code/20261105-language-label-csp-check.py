"""Verify current label handlers under regenerated headers, not cached prior rules."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'checks/20261105-visual-refinement'
errors=[];states=[]
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True);g=b.new_page()
    g.on('pageerror',lambda e:errors.append(str(e)))
    g.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    response=g.goto('http://127.0.0.1:8770/index.html#uav-components')
    assert 'content-security-policy' in response.headers
    g.wait_for_timeout(800)
    for expected in ['Tiếng Việt. Chuyển sang tiếng Anh','English. Change language to Vietnamese']:
        g.locator('#languageButton').click();g.wait_for_timeout(500)
        assert g.get_by_role('button',name=expected,exact=True).count()==1
        states.append({'label':expected,'flag':g.locator('#languageButton img').get_attribute('src')})
    b.close()
assert not errors,errors
(OUT/'language-label-csp.json').write_text(json.dumps({'states':states,'errors':errors},ensure_ascii=False,indent=2),encoding='utf8')
print('PASS current accessible names under regenerated CSP')
