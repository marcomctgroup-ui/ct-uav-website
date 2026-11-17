from pathlib import Path
from playwright.sync_api import sync_playwright
import json
r=Path('projects/main-website/refactor-v03');records=[];errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True)
 for width in [1440,390,320]:
  q=b.new_page(viewport={'width':width,'height':900});q.on('pageerror',lambda e:errors.append(str(e)))
  q.goto('http://127.0.0.1:8766/refactor-v03/index.html#ct-glova');f=q.frame_locator('#frame-ct-glova');f.locator('#product-title').wait_for();q.wait_for_timeout(1200)
  records.append({'width':width,'heading':f.locator('h1').inner_text(),'uav_bar':f.locator('.product-bar').count(),'component_layout':f.locator('.detail-hero').count(),'overflow':f.locator('body').evaluate('e=>document.documentElement.scrollWidth>innerWidth+1'),'launcher':q.locator('.cu-launcher').evaluate('e=>({w:e.getBoundingClientRect().width,transition:getComputedStyle(e).transitionDuration})')})
  q.screenshot(path=str(r/'checks'/f'glova-top-{width}.png'));f.locator('#applications').scroll_into_view_if_needed();q.wait_for_timeout(400);q.screenshot(path=str(r/'checks'/f'glova-applications-{width}.png'));q.close()
 b.close()
(r/'checks/focused-parent.json').write_text(json.dumps({'records':records,'errors':errors},indent=2),encoding='utf-8');print(json.dumps({'records':records,'errors':errors}))
