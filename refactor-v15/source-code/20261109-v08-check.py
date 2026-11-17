"""Focused Edge verification for v08. No live speech API call."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'checks/20261109-v08';OUT.mkdir(parents=True,exist_ok=True)
records=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    for width in [1440,390,320]:
        ctx=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce')
        page=ctx.new_page();errors=[];requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url))
        page.goto('http://127.0.0.1:8790/');page.wait_for_timeout(3500)
        assert not any('/i18n/vi.json' in x or '/voice-input-' in x or '/api/transcribe' in x for x in requests)
        page.locator('#languageButton').click();page.locator('[data-language="vi"]').click();page.wait_for_timeout(2500)
        assert any('/i18n/vi.json' in x for x in requests)
        assert page.locator('html').get_attribute('lang')=='vi'
        page.locator('#languageButton').click();page.locator('[data-language="id"]').click();page.wait_for_timeout(500)
        assert page.locator('html').get_attribute('lang')=='en'
        page.locator('#languageButton').click();page.locator('[data-language="tl"]').click()
        page.locator('#languageButton').click();page.locator('[data-language="en"]').click()
        page.screenshot(path=str(OUT/f'home-{width}.png'))
        for route,status in [('10020','R&D'),('abc-ss-12s30','Pilot Production')]:
            page.goto('http://127.0.0.1:8790/components/'+route+'/');page.wait_for_timeout(2500)
            frame=next(f for f in page.frames if 'pages/component-'+route in f.url)
            assert status in frame.locator('.component-source-status').inner_text()
            assert frame.locator('h1').inner_text() in ['Multirotor Motor','Semi-Solid Pack']
            assert frame.locator('#product-image').evaluate('(e)=>e.complete&&e.naturalWidth>0')
            frame.locator('[data-cart-add]').click()
            page.screenshot(path=str(OUT/f'{route}-{width}.png'))
        page.goto('http://127.0.0.1:8790/components/');page.wait_for_timeout(2500)
        frame=next(f for f in page.frames if 'pages/uav-components' in f.url)
        assert len(frame.evaluate('window.CTComponents'))==12
        frame.locator('#search').fill('10020');assert 'R&D' in frame.locator('#grid').inner_text()
        frame.locator('#search').fill('ABC-SS-12S30');assert 'Pilot Production' in frame.locator('#grid').inner_text()
        # Both success and unavailable paths use controlled responses, never live audio.
        page.locator('#cuLauncher').click();page.locator('#cuMicrophone').click();page.wait_for_timeout(1000)
        assert page.locator('#cuVoiceDisclosure').is_visible()
        page.route('**/api/transcribe',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Not connected"}'))
        page.locator('#cuVoiceStart').click();page.wait_for_timeout(800)
        assert 'not connected' in page.locator('#cuVoiceStatus').inner_text()
        assert page.locator('#cuInput').is_enabled()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        records.append({'width':width,'errors':errors,'language_deferred':True,'catalogue':12,'voice_unavailable_typing':True})
        assert not errors,errors
        ctx.close()
    browser.close()
(OUT/'focused.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps(records))
