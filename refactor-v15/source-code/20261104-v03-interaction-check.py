import sys;sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
r=Path('projects/main-website/refactor-v03');out={};errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);q=b.new_page(viewport={'width':390,'height':844});q.on('pageerror',lambda e:errors.append(str(e)))
 q.goto('http://127.0.0.1:8766/refactor-v03/index.html');q.locator('.cu-launcher').wait_for(state='attached');q.wait_for_timeout(1000)
 out['hidden_on_home']=q.locator('.cu-launcher').evaluate('e=>({opacity:getComputedStyle(e).opacity,visibility:getComputedStyle(e).visibility})')
 q.locator('#homeView').evaluate('e=>e.scrollTop=innerHeight+100');q.wait_for_timeout(150);out['entrance_150ms']=q.locator('.cu-launcher').evaluate('e=>({opacity:getComputedStyle(e).opacity,transform:getComputedStyle(e).transform})');q.wait_for_timeout(1000);out['entrance_finished']=q.locator('.cu-launcher').evaluate('e=>({opacity:getComputedStyle(e).opacity,width:e.getBoundingClientRect().width})')
 out['motion_1']=q.locator('.cu-launcher .ce-mascot').evaluate('e=>getComputedStyle(e).transform');q.wait_for_timeout(900);out['motion_2']=q.locator('.cu-launcher .ce-mascot').evaluate('e=>getComputedStyle(e).transform')
 q.emulate_media(reduced_motion='reduce');out['reduced_motion']=q.locator('.cu-launcher .ce-mascot').evaluate('e=>getComputedStyle(e).animationName')
 q.evaluate("ctuavDemo.navigate('line-06')");f=q.frame_locator('#frame-line-06');btn=f.locator('[data-route="ct-glova"]');out['glova_button']=btn.inner_text();btn.click();q.wait_for_timeout(500);out['button_route']=q.url
 g=q.frame_locator('#frame-ct-glova');g.locator('.product-nav a[href="#applications"]').click();q.wait_for_timeout(400);out['applications_scroll']=g.locator('body').evaluate('()=>scrollY');g.locator('[data-contact]').click();q.wait_for_timeout(500);out['contact_route']=q.url;out['errors']=errors;b.close()
(r/'checks/interactions.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
