from pathlib import Path
from playwright.sync_api import sync_playwright
import json
r=Path('projects/main-website/refactor-v03');url='http://127.0.0.1:8766/refactor-v03/checks/20261105-zip-validation-r02/index.html';out=[];errors=[];failed=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);q=b.new_page(viewport={'width':390,'height':844},reduced_motion='reduce');q.on('pageerror',lambda e:errors.append(str(e)));q.on('response',lambda res:failed.append({'url':res.url,'status':res.status}) if res.status>=400 else None)
 for route in ['home','ct-glova','uav-components','component-3530','contact']:
  q.goto(url+'#'+route);q.wait_for_timeout(900)
  if route!='home':q.frame_locator('#frame-'+route).locator('body').wait_for()
  out.append({'route':route,'loaded':True})
 q.goto(url+'#ct-glova');q.wait_for_timeout(800);g=q.frame_locator('#frame-ct-glova');g.locator('#specifications table').wait_for();q.evaluate('window.ctuavDemo.navigate("products")');q.wait_for_timeout(400);q.locator('#globalLangToggle').count()
 # Normal pointer language click on a page where global navigation is visible.
 lang=q.get_by_role('button',name='Change language to Vietnamese');lang.click();q.wait_for_timeout(200);q.evaluate('window.ctuavDemo.navigate("ct-glova")');q.wait_for_timeout(600)
 labels=g.locator('#specifications th').all_text_contents();out.append({'VI_labels':labels});assert 'Flight Speed' not in labels and 'Wind Resistance Level' not in labels and 'Hovering Time' not in labels
 q.screenshot(path=str(r/'checks/20261105-zip-r02-glova-phone.png'));b.close()
result={'routes':out,'script_errors':errors,'failed_HTTP_requests':failed,'zip_runtime_pass':not errors and not failed};(r/'checks/20261105-zip-r02-browser-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))
