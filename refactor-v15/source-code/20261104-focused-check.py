from pathlib import Path
import json,sys
from playwright.sync_api import sync_playwright
r=Path('projects/main-website/refactor-v02');out=[];errors=[]
models=json.loads((r/'checks/component-matches.json').read_text(encoding='utf-8'))
import re
routes=['uav-components','ct-glova','ct-fyran-firefighting']+['component-'+re.sub('[^a-z0-9]+','-',x['name'].lower()).strip('-') for x in models]
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':390,'height':844},reduced_motion='reduce');page.on('pageerror',lambda e:errors.append(str(e)))
 for route in routes:
  page.goto('http://127.0.0.1:8766/refactor-v02/index.html#'+route);page.wait_for_timeout(700)
  f=page.frame_locator('#frame-'+route)
  try:
   body=f.locator('body');body.wait_for(timeout=15000)
   info=body.evaluate('(b)=>({overflow:b.ownerDocument.documentElement.scrollWidth>innerWidth+1,text:b.innerText.slice(0,150),images:[...b.querySelectorAll("img[src]")].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src)})');out.append({'route':route,**info})
  except Exception as e:out.append({'route':route,'error':str(e)})
 page.goto('http://127.0.0.1:8766/refactor-v02/index.html');page.wait_for_timeout(1000);print('launcher home',page.locator('.cu-launcher').evaluate('(e)=>getComputedStyle(e).visibility'))
 page.locator('#homeView').evaluate('(e)=>e.scrollTop=innerHeight+100');page.wait_for_timeout(500);print('launcher after',page.locator('.cu-launcher').evaluate('(e)=>getComputedStyle(e).visibility'))
 b.close()
(r/'checks/focused-routes.json').write_text(json.dumps({'routes':out,'errors':errors},indent=2),encoding='utf-8');print(len(out),'routes',errors);print([x for x in out if x.get('error') or x.get('overflow')])
