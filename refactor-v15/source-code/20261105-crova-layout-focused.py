from pathlib import Path
from playwright.sync_api import sync_playwright
import json
r=Path('projects/main-website/refactor-v03');out=[];errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True)
 for w in [1440,390,320]:
  q=b.new_page(viewport={'width':w,'height':900},reduced_motion='reduce');q.on('pageerror',lambda e:errors.append(str(e)));q.goto('http://127.0.0.1:8766/refactor-v03/index.html?crova-check=20261105#ct-glova');f=q.frame_locator('#frame-ct-glova');f.locator('.metrics').wait_for();q.wait_for_timeout(500);q.screenshot(path=str(r/'checks'/f'20261105-crova-layout-hero-{w}.png'));f.locator('#applications').scroll_into_view_if_needed();q.screenshot(path=str(r/'checks'/f'20261105-crova-layout-applications-{w}.png'));out.append({'width':w,'metrics':f.locator('.metric').all_text_contents(),'gallery_white_views':f.locator('#gallery img[src*="ct-glova-white"]').count(),'overflow':f.locator('body').evaluate('()=>document.documentElement.scrollWidth>innerWidth+1')});q.close()
 b.close()
(r/'checks/20261105-crova-layout-focused.json').write_text(json.dumps({'records':out,'errors':errors},indent=2),encoding='utf-8');print(json.dumps({'records':out,'errors':errors}))
