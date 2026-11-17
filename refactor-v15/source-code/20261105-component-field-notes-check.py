"""Final note and UTF-8 checks for the corrected source-field pages."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'checks/20261105-components-navbar-model'
results=[]
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True)
    for width in [1440,390,320]:
        g=b.new_page(viewport={'width':width,'height':900})
        for name,vi in [('ct-ib-6s','Pin thông minh'),('bms-150a','BMS thông minh'),('ct-1600w-12s','Bộ sạc thông minh')]:
            route='component-'+name;g.goto('http://127.0.0.1:8766/refactor-v04/index.html#'+route)
            f=g.frame_locator('#frame-'+route);f.locator('#specifications').wait_for();f.locator('#specifications').scroll_into_view_if_needed()
            assert f.locator('.source-confirmation').is_visible()
            assert f.locator('#specifications dt[data-en="Cycles"]').count()==0
            assert f.locator('#specifications dt[data-en="Application"]').count()==0
            g.locator('#languageButton').click();g.wait_for_timeout(300)
            assert f.locator('.source-confirmation').inner_text().startswith('Một số cột')
            assert f.locator('#specifications dd[data-category]').inner_text()==vi
            assert f.locator('html').evaluate('(e)=>e.scrollWidth<=innerWidth')
            g.screenshot(path=str(OUT/f'pending-fields-{name}-{width}.png'))
            results.append({'model':name,'width':width,'vi_note':True,'overflow':False})
            g.locator('#languageButton').click()
        g.close()
    g=b.new_page();g.goto('http://127.0.0.1:8766/refactor-v04/index.html#component-abc-1865v2')
    f=g.frame_locator('#frame-component-abc-1865v2');f.locator('#specifications').wait_for();g.locator('#languageButton').click();g.wait_for_timeout(300)
    assert f.locator('#specifications dt[data-en="Status"] + dd').inner_text()=='Sản xuất'
    b.close()
(OUT/'field-notes-runtime.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print('PASS source notes and Vietnamese category/status hooks, 3 models at 3 widths')
