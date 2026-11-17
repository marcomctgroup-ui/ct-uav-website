from pathlib import Path
from bs4 import BeautifulSoup
import json
from playwright.sync_api import sync_playwright
r=Path('projects/main-website/refactor-v03');src=json.loads((r/'checks/20261105-glova-sales-kit-source.json').read_text(encoding='utf-8'))['data'];records=[];errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True)
 for width in [1440,1024,768,390,320]:
  q=b.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');q.on('pageerror',lambda e:errors.append(str(e)));q.goto('http://127.0.0.1:8766/refactor-v03/index.html?check=20261105#ct-glova');f=q.frame_locator('#frame-ct-glova');f.locator('#specifications table').wait_for();f.locator('#specifications').scroll_into_view_if_needed();q.wait_for_timeout(300)
  vals=f.locator('#specifications tbody tr').evaluate_all('(rows)=>rows.map(r=>[r.querySelector("th").textContent,r.querySelector("td").textContent])');assert vals==src['models'][0]['specs'],vals
  records.append({'width':width,'overflow':f.locator('body').evaluate('e=>document.documentElement.scrollWidth>innerWidth+1'),'source_specs_match':True,'technology_count':f.locator('#technology li').count(),'application_count':f.locator('#applications .application-item').count()})
  if width in [1440,390,320]:q.screenshot(path=str(r/'checks'/f'20261105-glova-specifications-{width}.png'))
  q.close()
 b.close()
(r/'checks/20261105-glova-functional.json').write_text(json.dumps({'records':records,'errors':errors},indent=2),encoding='utf-8');print(json.dumps({'records':records,'errors':errors}))
