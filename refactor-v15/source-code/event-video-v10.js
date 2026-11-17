(()=>{
let opener;let returnSource=null;let returnKey=null;
const dialog=document.createElement('dialog');
dialog.className='event-video-dialog';
dialog.innerHTML='<button type="button" class="event-video-close" aria-label="Close video">Close ×</button><h2 id="event-video-title"></h2><video controls playsinline preload="none"></video><p id="event-video-description"></p>';
dialog.setAttribute('aria-labelledby','event-video-title');document.body.append(dialog);
function close(){dialog.close();}
dialog.querySelector('button').addEventListener('click',close);
dialog.addEventListener('close',()=>{dialog.querySelector('video').pause();dialog.querySelector('video').removeAttribute('src');dialog.querySelector('video').load();opener?.focus();if(returnSource){returnSource.postMessage({namespace:"ctuav-event-focus",key:returnKey},location.origin);returnSource=null;returnKey=null;}});
function open(key,button){
 const data=key==='vungtau'?['Vung Tau flight demonstration','CT UAV flight demonstration in Vung Tau.','vungtau-demonstration-dc7d448d1799.mp4']:['CT-PEGAS 230 product demonstration','CT-PEGAS 230 in flight during a CT UAV product demonstration.','pegas-demonstration-c74b565cf471.mp4'];
 if(document.documentElement.lang==='vi'){data[0]=key==='vungtau'?'Tr\u00ecnh di\u1ec5n bay t\u1ea1i V\u0169ng T\u00e0u':'Tr\u00ecnh di\u1ec5n s\u1ea3n ph\u1ea9m CT-PEGAS 230';data[1]=key==='vungtau'?'CT UAV tr\u00ecnh di\u1ec5n bay t\u1ea1i V\u0169ng T\u00e0u.':'CT-PEGAS 230 bay trong bu\u1ed5i tr\u00ecnh di\u1ec5n s\u1ea3n ph\u1ea9m CT UAV.';}dialog.querySelector('button').textContent=document.documentElement.lang==='vi'?'\u0110\u00f3ng \u00d7':'Close \u00d7';opener=button;dialog.querySelector('h2').textContent=data[0];dialog.querySelector('p').textContent=data[1];dialog.querySelector('video').src=new URL('assets/video/v10/'+data[2],document.baseURI).href;dialog.showModal();dialog.querySelector('video').play().catch(()=>{});
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-event-video]');if(b){if(parent!==window){parent.postMessage({namespace:'ctuav-event',key:b.dataset.eventVideo},location.origin);return;}open(b.dataset.eventVideo,b);}});
addEventListener('message',e=>{if(e.origin===location.origin&&e.source===parent&&e.data?.namespace==='ctuav-event-focus'){document.querySelector('[data-event-video='+e.data.key+']')?.focus();return;}if(e.origin!==location.origin||e.data?.namespace!=='ctuav-event'||!['vungtau','pegas'].includes(e.data.key))return;if(![...document.querySelectorAll('iframe')].some(f=>f.contentWindow===e.source))return;returnSource=e.source;returnKey=e.data.key;open(e.data.key,null);});
})();
