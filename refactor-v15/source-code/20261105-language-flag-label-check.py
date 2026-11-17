"""Check settled accessible names with normal EN -> VI -> EN pointer clicks."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'checks/20261105-visual-refinement'
rows=[];errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    for width in [1440,1024,390,320]:
        pg=browser.new_page(viewport={'width':width,'height':900})
        pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto('http://127.0.0.1:8766/refactor-v04/index.html#uav-components');pg.wait_for_timeout(1000)
        for lang,label in [('en','English. Change language to Vietnamese'),('vi','Tiếng Việt. Chuyển sang tiếng Anh'),('en','English. Change language to Vietnamese')]:
            if lang!=pg.locator('html').get_attribute('lang'):pg.locator('#languageButton').click()
            pg.wait_for_timeout(1000)
            assert pg.locator('#languageButton').get_attribute('aria-label')==label
            assert pg.locator('#languageButton img').get_attribute('src')==f'assets/img/flag-{lang}.svg'
            assert pg.frame_locator('#frame-uav-components').locator('html').get_attribute('lang')==lang
            # A later generic translation pass must not restore the cached initial label.
            pg.evaluate('window.ctuavI18n.set(document.documentElement.lang)');pg.wait_for_timeout(100)
            assert pg.locator('#languageButton').get_attribute('aria-label')==label
            rows.append({'width':width,'lang':lang,'label':label,'stable':True})
        pg.locator('#languageButton').focus();pg.keyboard.press('Enter');pg.wait_for_timeout(300)
        assert pg.locator('#languageButton').get_attribute('aria-label')=='Tiếng Việt. Chuyển sang tiếng Anh'
        pg.keyboard.press('Enter');pg.wait_for_timeout(300)
        assert pg.locator('#languageButton').get_attribute('aria-label')=='English. Change language to Vietnamese'
        pg.close()
    browser.close()
assert not errors,errors
(OUT/'language-label-runtime.json').write_text(json.dumps({'rows':rows,'errors':errors,'keyboard':True},ensure_ascii=False,indent=2),encoding='utf8')
print('PASS: normal EN -> VI -> EN clicks, stable accessible labels, matching flags and keyboard Enter at four widths')
