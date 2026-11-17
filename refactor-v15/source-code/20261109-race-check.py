"""Regression checks for failed language loading and cancelled permission sessions."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
OUT=Path(__file__).resolve().parents[1]/'checks/20261109-v08'
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True)
    page=b.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
    page.route('**/assets/i18n/vi.json',lambda r:r.fulfill(status=503,body='unavailable'))
    page.goto('http://127.0.0.1:8790/components/10020/');page.wait_for_timeout(1700)
    page.locator('#languageButton').click();page.locator('[data-language="vi"]').click();page.wait_for_timeout(800)
    assert page.locator('html').get_attribute('lang')=='en'
    assert 'EN' in page.locator('#languageButton').inner_text()
    assert page.locator('[data-page="shareholders"]').first.inner_text()=='Our Partners'
    page.evaluate('''() => {
      window.permissions=[];window.started=0;window.released=0;window.posts=0;
      navigator.mediaDevices.getUserMedia=()=>new Promise(resolve=>window.permissions.push(resolve));
      window.fetch=async(url,options={})=>{if(options.method==='POST')window.posts++;return Response.json({available:true,text:'Old transcript'})};
      window.MediaRecorder=class {
        static isTypeSupported(){return true} state='inactive';
        start(){this.state='recording';window.started++}
        stop(){this.state='inactive';this.ondataavailable({data:new Blob(['fake audio'],{type:'audio/webm'})});queueMicrotask(()=>this.onstop())}
      };
      window.stream=()=>({getTracks:()=>[{stop:()=>window.released++}]});
    }''')
    page.locator('#cuLauncher').click();page.locator('#cuMicrophone').click();page.wait_for_timeout(500)
    page.locator('#cuVoiceStart').click();page.wait_for_timeout(300)
    assert page.locator('#cuVoiceCancel').is_visible()
    page.locator('#cuVoiceCancel').click()
    page.locator('#cuMicrophone').click();page.locator('#cuVoiceStart').click();page.wait_for_timeout(300)
    page.evaluate('window.permissions[0](window.stream())');page.wait_for_timeout(200)
    assert page.evaluate('window.started')==0
    page.evaluate('window.permissions[1](window.stream())');page.wait_for_timeout(200)
    assert page.evaluate('window.started')==1
    assert page.locator('#cuVoiceCancel').is_visible()
    page.screenshot(path=str(OUT/'voice-cancel-visible-390.png'))
    page.locator('#cuVoiceCancel').click();page.wait_for_timeout(200)
    assert page.evaluate('window.posts')==0
    assert page.evaluate('window.released')==2
    result={'language_failure_full_EN_fallback':True,'stale_permission_released':True,'only_current_session_records':True,'cancel_visible':True,'cancel_does_not_upload':True}
    (OUT/'race-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));b.close()
