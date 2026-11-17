"""Check Haykal's seven current v04 corrections with the repository Edge workflow."""
from pathlib import Path
import json,hashlib
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'checks/20261105-visual-refinement';URL='http://127.0.0.1:8766/refactor-v04/index.html'
result={'widths':[],'errors':[],'bad_requests':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page()
    page.on('pageerror',lambda e:result['errors'].append(str(e)))
    page.on('response',lambda r:result['bad_requests'].append(r.url) if r.status>=400 else None)
    for width in [1440,1250,1180,1100,1024,768,390,320]:
        page.set_viewport_size({'width':width,'height':900});page.goto(URL+'#uav-components');page.wait_for_timeout(1800)
        frame=page.frame_locator('#frame-uav-components')
        assert frame.locator('.card').count()==80
        assert frame.locator('.component-card-name').count()==80
        assert frame.locator('.component-card-name').first.inner_text()=='ESC-100A-6S'
        assert frame.locator('.card-action').count()==0
        info=page.evaluate("""()=>{const d=document.getElementById('frame-uav-components').contentDocument,brand=document.querySelector('.brand-lockup').getBoundingClientRect(),nav=document.querySelector('.main-nav').getBoundingClientRect(),tools=document.querySelector('.nav-tools').getBoundingClientRect(),member=document.querySelector('.member-logo').getBoundingClientRect();return {overflow:document.documentElement.scrollWidth>innerWidth||d.documentElement.scrollWidth>d.defaultView.innerWidth,brandEnd:brand.right,navStart:nav.left,navEnd:nav.right,toolsStart:tools.left,navVisible:nav.height>0,memberWidth:member.width,flag:document.querySelector('#languageButton img').getAttribute('src'),categoryMode:getComputedStyle(d.getElementById('categories')).display,selectVisible:!!d.getElementById('categorySelect').offsetParent}}""")
        assert not info['overflow'],(width,info)
        if width>1180:assert info['brandEnd']<=info['navStart'] and info['navEnd']<=info['toolsStart'],(width,info)
        else:
            assert info['brandEnd']<=info['toolsStart'],(width,info)
            page.locator('#menuButton').click();assert page.locator('#mainNav').is_visible();page.locator('#menuButton').click()
        assert info['flag'].endswith('flag-en.svg')
        page.locator('#languageButton').click();page.wait_for_timeout(350)
        assert page.locator('#languageButton img').get_attribute('src').endswith('flag-vi.svg')
        assert frame.locator('html').get_attribute('lang')=='vi'
        assert frame.locator('html').evaluate('(e)=>e.scrollWidth<=innerWidth')
        page.locator('#languageButton').click();page.wait_for_timeout(250)
        if width<=600:
            frame.locator('#categorySelect').select_option('Smart BMS');assert frame.locator('.card').count()==4
            frame.locator('#categorySelect').select_option('All')
        else:
            frame.locator('[data-cat="Smart BMS"]').click();assert frame.locator('.card').count()==4
            frame.locator('[data-cat="All"]').click()
        if width in [1440,390,320]:
            page.screenshot(path=str(OUT/f'categories-{width}.png'))
            frame.locator('.card').first.scroll_into_view_if_needed();page.wait_for_timeout(2200)
            page.screenshot(path=str(OUT/f'cards-{width}.png'))
        result['widths'].append({'width':width,**info})
    page.set_viewport_size({'width':1440,'height':900});page.goto(URL)
    page.wait_for_timeout(1500)
    result['hero_launcher_hidden']=page.locator('#cuLauncher').evaluate('(e)=>getComputedStyle(e).visibility==="hidden"')
    assert result['hero_launcher_hidden']
    page.locator('a.hp-card[data-route="ct-fyran-256"]').scroll_into_view_if_needed();page.wait_for_timeout(1200)
    result['home_image']=page.locator('a.hp-card[data-route="ct-fyran-256"] img').evaluate('(i)=>({src:i.currentSrc,complete:i.complete&&i.naturalWidth>0,srcset:i.srcset})')
    assert 'fyran-navbar-uav-00204' in result['home_image']['src']
    page.screenshot(path=str(OUT/'home-fyran-card-1440.png'))
    mascot=page.locator('#cuLauncher .ce-mascot')
    result['motion']=[]
    for i in range(3):
        result['motion'].append(mascot.evaluate('(e)=>({transform:getComputedStyle(e).transform,animation:getComputedStyle(e).animationName})'));page.wait_for_timeout(1100)
    assert len({x['transform'] for x in result['motion']})>1
    page.emulate_media(reduced_motion='reduce');assert mascot.evaluate('(e)=>getComputedStyle(e).animationName')=='none'
    result['reduced_motion']=True;page.emulate_media(reduced_motion='no-preference')
    page.goto(URL+'#ct-fyran-firefighting');page.wait_for_timeout(12000)
    frame=page.frame_locator('#frame-ct-fyran-firefighting');frame.locator('[data-ps-stage]').evaluate('(e)=>scrollTo(0,e.offsetTop+140)');page.wait_for_timeout(1500)
    assert frame.locator('canvas').count()>0
    page.screenshot(path=str(OUT/'firefighting-colours-1440.png'))
    frame.locator('canvas').press('ArrowRight');page.wait_for_timeout(500)
    result['model_bytes']=page.evaluate("document.getElementById('uav3dModel-ct-fyran-firefighting').ctuavBytes.length")
    assert result['model_bytes']==23169860
    browser.close()
result['entry_bytes']=(ROOT/'index.html').stat().st_size
result['model_sha256']=hashlib.sha256(next((ROOT/'assets/models').glob('ct-fyran-firefighting-*')).read_bytes()).hexdigest()
(OUT/'functional.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
assert not result['errors'] and not result['bad_requests'],result
print('PASS: eight widths, named cards, category controls, flags, Navbar, Home image, mascot motion and 3D model')
