"""Simulated capture checks. Never uses a real microphone or OpenAI account."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

OUT=Path(__file__).resolve().parents[1]/'checks/20261109-v08'
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True)
    page=b.new_page(viewport={'width':320,'height':844},reduced_motion='reduce')
    page.route('**/api/transcribe',lambda r:r.fulfill(status=200,content_type='application/json',body=json.dumps({'available':True} if r.request.method=='GET' else {'text':'Show the cargo UAV.'})))
    page.goto('http://127.0.0.1:8790/components/10020/');page.wait_for_timeout(1500)
    page.evaluate('''() => {
      window.stopped=0;
      navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[{stop:()=>window.stopped++}]});
      window.MediaRecorder=class {
        static isTypeSupported(){return true}
        state='inactive';mimeType='audio/webm';
        start(){this.state='recording'}
        stop(){this.state='inactive';this.ondataavailable({data:new Blob(['fake audio'],{type:'audio/webm'})});queueMicrotask(()=>this.onstop())}
      };
    }''')
    page.locator('#cuLauncher').click();page.locator('#cuMicrophone').click();page.wait_for_timeout(500)
    page.locator('#cuVoiceStart').click();page.wait_for_timeout(400)
    page.locator('#cuMicrophone').click();page.wait_for_timeout(600)
    assert page.locator('#cuInput').input_value()=='Show the cargo UAV.'
    assert page.locator('#cuMessages').is_hidden(), 'Transcription must not submit a message'
    assert page.evaluate('window.stopped')>0
    page.screenshot(path=str(OUT/'voice-review-320.png'))
    # A second recording closes without a transcript or retained live track.
    page.locator('#cuMicrophone').click();page.locator('#cuVoiceStart').click();page.wait_for_timeout(300)
    page.locator('#cuClose').click();page.wait_for_timeout(300)
    assert page.locator('#cuInput').input_value()=='Show the cargo UAV.'
    assert page.evaluate('window.stopped')>=2
    result={'simulated_transcription':True,'manual_send_required':True,'tracks_released':True,'close_cancels':True,'live_api_call':False}
    (OUT/'voice-flow.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result));b.close()
