"""Focused runtime checks for current v04 revision. Edge repository workflow."""
from pathlib import Path
import json, re
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'checks/20261105-components-navbar-model'
URL='http://127.0.0.1:8766/refactor-v04/index.html'
data=json.loads((ROOT/'assets/js/shared-script-6b2b16428671.js').read_text(encoding='utf8').split('=',1)[1].strip().rstrip(';'))
result={'views':[],'routes':[],'errors':[],'bad_requests':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page()
    page.on('pageerror',lambda e:result['errors'].append(str(e)))
    page.on('response',lambda r:result['bad_requests'].append(r.url) if r.status>=400 else None)
    for w in [1440,1250,1100,1024,768,390,320]:
        page.set_viewport_size({'width':w,'height':900})
        page.goto(URL+'#uav-components');page.wait_for_timeout(2000)
        f=page.frame_locator('#frame-uav-components')
        cards=f.locator('.card');assert cards.count()==80
        info=page.evaluate("""()=>{const d=document.getElementById('frame-uav-components').contentDocument;return {overflow:document.documentElement.scrollWidth>innerWidth||d.documentElement.scrollWidth>d.defaultView.innerWidth,cardText:[...d.querySelectorAll('.card')].map(c=>c.innerText.trim()).filter(Boolean),navOverflow:document.getElementById('globalHeader').scrollWidth>innerWidth,images:[...d.querySelectorAll('.card img')].slice(0,3).every(i=>i.complete&&i.naturalWidth>0),member:document.querySelector('.member-logo').complete&&document.querySelector('.member-logo').naturalWidth>0}}""")
        result['views'].append({'width':w,**info})
        if w in [1440,390,320]:
            page.screenshot(path=str(OUT/f'catalogue-{w}.png'))
            f.locator('#grid').scroll_into_view_if_needed();page.wait_for_timeout(800)
            page.screenshot(path=str(OUT/f'cards-{w}.png'))
            f.locator('h1').scroll_into_view_if_needed()
        nav=page.evaluate("""()=>{const a=document.querySelector('.brand-lockup').getBoundingClientRect(),b=document.querySelector('.main-nav').getBoundingClientRect(),c=document.querySelector('.nav-tools').getBoundingClientRect();return {brandEnd:a.right,navStart:b.left,navEnd:b.right,toolsStart:c.left,visible:b.height>0}}""")
        if w>850:assert nav['brandEnd']<=nav['navStart'] and nav['navEnd']<=nav['toolsStart'],nav
        if w in [390,320]:
            page.locator('#menuButton').click();page.screenshot(path=str(OUT/f'navbar-menu-{w}.png'));page.locator('#menuButton').click()
        assert not info['overflow'] and not info['navOverflow'],info
        assert not info['cardText'] and info['images'] and info['member'],info
    # Search, category, sort, and accessible card link use normal pointer actions.
    page.set_viewport_size({'width':1440,'height':900})
    f.locator('#search').fill('ABC-SS-108S30HV');assert cards.count()==1
    f.locator('.card-link').click();page.wait_for_timeout(1000)
    result['clicked_route']=page.url
    assert page.url.endswith('#component-abc-ss-108s30hv')
    detail=page.frame_locator('#frame-component-abc-ss-108s30hv')
    detail.locator('a.back').click();page.wait_for_timeout(600)
    assert f.locator('[data-cat="Semi-Solid HV Pack"]').get_attribute('aria-pressed')=='true'
    f.locator('#reset').click();f.locator('#search').fill('no-such-component');assert cards.count()==0
    f.locator('#reset').click();assert cards.count()==80
    # Every new detail route has a matching title, specs and unbroken first image.
    rec=json.loads((OUT/'source-record.json').read_text(encoding='utf8'))
    for item in rec['records']:
        route='component-'+item['id'];page.goto(URL+'#'+route);page.wait_for_timeout(220)
        frame=page.frame_locator('#frame-'+route)
        frame.locator('h1').wait_for()
        assert frame.locator('h1').inner_text()==item['name']
        frame.locator('#product-image').evaluate('(i)=>i.decode()')
        text=frame.locator('#specifications').inner_text()
        if item['match']:
            for k,v in item['match']['values']:assert v in text,(route,k,v)
        else:assert 'pending confirmation' in text
        result['routes'].append(route)
    page.goto(URL+'#component-ct-hrc01');page.wait_for_timeout(1000)
    frame=page.frame_locator('#frame-component-ct-hrc01')
    frame.locator('.thumb').last.click();page.wait_for_timeout(200);frame.locator('#zoom').click();page.wait_for_timeout(300)
    result['gallery']=frame.locator('#enlarged').evaluate('(i)=>({src:i.currentSrc,alt:i.alt,loaded:i.complete&&i.naturalWidth>0})')
    assert '-04-' in result['gallery']['src'],result['gallery']
    frame.locator('#close-image').click()
    page.locator('#languageButton').click();page.wait_for_timeout(400)
    result['vi']=frame.locator('html').get_attribute('lang')
    assert result['vi']=='vi'
    page.locator('#languageButton').click()
    # GLOVA survives without replacing current v04 page/controller.
    page.goto(URL+'#ct-glova');page.wait_for_timeout(1000)
    result['glova']=page.frame_locator('#frame-ct-glova').locator('h1').inner_text()
    # Model stays deferred until its stage approaches the viewport.
    page.goto(URL+'#ct-fyran-firefighting');page.wait_for_timeout(1500)
    result['model_deferred']=page.evaluate("()=>!document.getElementById('uav3dModel-ct-fyran-firefighting').ctuavBytes")
    page.evaluate("()=>{const f=document.getElementById('frame-ct-fyran-firefighting');const s=f.contentDocument.querySelector('[data-ps-stage]');f.contentWindow.scrollTo(0,s.offsetTop+250)}")
    page.wait_for_timeout(12000)
    result['model']=page.evaluate("()=>{const f=document.getElementById('frame-ct-fyran-firefighting');const s=f.contentDocument.querySelector('[data-ps-stage]');return {key:s.dataset.psModel,error:s.dataset.resourceError||null,bytes:document.getElementById('uav3dModel-ct-fyran-firefighting').ctuavBytes?.length,canvas:f.contentDocument.querySelectorAll('canvas').length,text:s.innerText}}")
    page.screenshot(path=str(OUT/'firefighting-model-1440.png'))
    assert result['model']['bytes']==23169860 and not result['model']['error'] and result['model']['canvas']>0
    browser.close()
(OUT/'focused-runtime.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
assert not result['errors'] and not result['bad_requests'],result
print('PASS',len(result['views']),'widths;',len(result['routes']),'new routes; catalogue controls, gallery, VI and 3D model')
