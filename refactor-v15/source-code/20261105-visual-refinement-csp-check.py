"""Check revised routes with freshly generated CSP and cache headers on port 8769."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'checks/20261105-visual-refinement'
result={'errors':[],'routes':[]}
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True)
 pg=b.new_page(viewport={'width':1440,'height':900})
 pg.on('pageerror',lambda e:result['errors'].append(str(e)))
 pg.on('console',lambda m:result['errors'].append(m.text) if m.type=='error' else None)
 for route in ['uav-components','component-abc-1865v2','component-abc-ss-108s30hv','component-ct-hrc01','component-ct-ez30','component-vtx-and-vrx','component-payload-drop','ct-glova','ct-fyran-firefighting']:
  response=pg.goto('http://127.0.0.1:8769/index.html#'+route);pg.wait_for_timeout(600)
  if response:assert 'content-security-policy' in response.headers
  f=pg.frame_locator('#frame-'+route);f.locator('h1').wait_for()
  result['routes'].append(route)
 pg.evaluate("()=>{const f=document.getElementById('frame-ct-fyran-firefighting');const s=f.contentDocument.querySelector('[data-ps-stage]');f.contentWindow.scrollTo(0,s.offsetTop+250)}")
 pg.wait_for_timeout(12000)
 result['model_bytes']=pg.evaluate("document.getElementById('uav3dModel-ct-fyran-firefighting').ctuavBytes?.length")
 result['canvas']=pg.frame_locator('#frame-ct-fyran-firefighting').locator('canvas').count()
 assert result['canvas']>0 and result['model_bytes']==23169860
 pg.locator('#languageButton').click();pg.wait_for_timeout(300)
 assert pg.locator('#languageButton img').get_attribute('src').endswith('flag-vi.svg')
 pg.locator('#languageButton').click()
 pg.locator('#cuLauncher').click();pg.wait_for_timeout(9000)
 result['mascot']=pg.evaluate('window.CTEncyMascot.status()')
 assert result['mascot']['engine']=='ready',result['mascot']
 pg.locator('#cuClose').click();pg.wait_for_timeout(300)
 b.close()
(OUT/'csp-runtime.json').write_text(json.dumps(result,indent=2),encoding='utf8')
assert not result['errors'],result['errors']
print('PASS: revised routes and model under generated CSP')
