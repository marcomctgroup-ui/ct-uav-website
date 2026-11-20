/* Deferred speech capture. Each session owns its resources. */
(() => {
 const button=document.getElementById('cuMicrophone'),input=document.getElementById('cuInput'),form=document.getElementById('cuComposer'),status=document.getElementById('cuVoiceStatus'),disclosure=document.getElementById('cuVoiceDisclosure'),cancelButton=document.getElementById('cuVoiceCancel');
 let session=null;
 const say=text=>{status.textContent=text};
 /* v09: the icon stays; state, aria-pressed and aria-busy change. revision-v09.js sets the EN/VI accessible name from data-voice-state. */
 const mode=state=>{button.dataset.voiceState=state;button.setAttribute('aria-pressed',String(state==='recording'));if(state==='converting')button.setAttribute('aria-busy','true');else button.removeAttribute('aria-busy')};
 const expand=()=>button.setAttribute('aria-expanded',String(!disclosure.hidden));
 const release=s=>{clearTimeout(s.timer);s.stream?.getTracks().forEach(t=>t.stop());s.stream=null};
 function reset(s){release(s);if(session!==s)return;session=null;mode('idle');cancelButton.hidden=true}
 function cancel(){const s=session;session=null;if(s){s.controller.abort();release(s);if(s.recorder?.state==='recording')s.recorder.stop()}disclosure.hidden=true;expand();cancelButton.hidden=true;mode('idle');say('Recording cancelled. You can type your question.')}
 button.addEventListener('click',()=>{if(session?.recorder?.state==='recording'){session.recorder.stop();release(session)}else if(!session){disclosure.hidden=!disclosure.hidden;expand();cancelButton.hidden=disclosure.hidden}});
 cancelButton.addEventListener('click',cancel);
 document.getElementById('cuVoiceStart').addEventListener('click',async()=>{
  if(session)return;
  if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){say('Microphone is unavailable in this browser. Please type your question.');return}
  const s={controller:new AbortController(),chunks:[],stream:null,timer:null,recorder:null};session=s;disclosure.hidden=true;expand();cancelButton.hidden=false;
  try{
   s.timer=setTimeout(()=>s.controller.abort(),10000);
   const ready=await fetch('/api/transcribe',{signal:s.controller.signal,cache:'no-store'});
   clearTimeout(s.timer);if(session!==s)return;
   if(!ready.ok)throw Error('Voice input is not connected yet. Please type your question.');
   const acquired=await navigator.mediaDevices.getUserMedia({audio:true});
   if(session!==s){acquired.getTracks().forEach(t=>t.stop());return}s.stream=acquired;
   const mimeType=['audio/webm;codecs=opus','audio/mp4','audio/webm'].find(t=>MediaRecorder.isTypeSupported(t));
   if(!mimeType)throw Error('Recording format unavailable. Please type your question.');
   const recorder=s.recorder=new MediaRecorder(s.stream,{mimeType,audioBitsPerSecond:64000}),original=input.value;
   recorder.ondataavailable=e=>{if(e.data.size)s.chunks.push(e.data)};
   recorder.onerror=()=>{if(session===s){cancel();say('Recording failed. Please type your question.')}};
   recorder.onstop=async()=>{
    release(s);if(session!==s)return;say('Converting speech to text…');mode('converting');
    try{
     const audio=new Blob(s.chunks,{type:mimeType});s.chunks=[];
     if(!audio.size||audio.size>4*1024*1024)throw Error('Recording is empty or too large. Please try again.');
     const data=new FormData();data.append('audio',audio,mimeType.includes('mp4')?'question.mp4':'question.webm');
     s.timer=setTimeout(()=>s.controller.abort(),35000);
     const response=await fetch('/api/transcribe',{method:'POST',body:data,signal:s.controller.signal});
     if(session!==s)return;
     if(!response.ok)throw Error(response.status===429?'Voice request limit reached. Please type your question.':'Speech conversion failed. Please type your question.');
     const result=await response.json();if(session!==s)return;
     if(!result.text?.trim())throw Error('No speech was found. Please try again or type.');
     if(input.value!==original){say('Your question changed during recording. Please record again or keep typing.');return}
     input.value=(original+(original?' ':'')+result.text.trim()).slice(0,input.maxLength||500);input.dispatchEvent(new Event('input',{bubbles:true}));input.focus();say('Check the written question. Press Send when the question is correct.');
    }catch(error){if(session===s)say(error.name==='AbortError'?'Voice request timed out. Please type your question.':error.message)}finally{s.chunks=[];reset(s)}
   };
   recorder.start();mode('recording');say('Recording. Press Stop microphone when finished. Recording stops after 30 seconds.');
   s.timer=setTimeout(()=>{if(session===s&&recorder.state==='recording')recorder.stop();release(s)},30000);
  }catch(error){if(session===s)say(error.name==='NotAllowedError'?'Microphone permission was denied. Please type your question.':error.name==='AbortError'?'Voice request timed out. Please type your question.':error.message);reset(s)}
 });
 form.addEventListener('submit',event=>{if(session){event.preventDefault();event.stopImmediatePropagation();say('Stop the recording and check the written question before Send.')}},true);
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&session)cancel()});
 new MutationObserver(()=>{if(document.getElementById('cuPanel').hidden)cancel()}).observe(document.getElementById('cuPanel'),{attributes:true,attributeFilter:['hidden']});
 addEventListener('pagehide',()=>{if(session)cancel()});
 disclosure.hidden=false;expand();cancelButton.hidden=false;
})();
