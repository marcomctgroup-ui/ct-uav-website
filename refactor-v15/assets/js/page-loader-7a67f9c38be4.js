
(()=>{
 // Only an explicitly played video acquires its URL. Existing play/pause logic remains.
 const play=HTMLMediaElement.prototype.play;
 const pause=HTMLMediaElement.prototype.pause,small=matchMedia('(max-width: 900px)').matches,queue=[];let videoReady=document.readyState==='complete';
 // Batch 6: video files load after the page is ready; the poster shows first. Phones get the 720p file.
 const flush=()=>{videoReady=true;queue.splice(0).forEach(v=>v.play().catch(()=>{}))};
 if(!videoReady)addEventListener('load',()=>setTimeout(flush,1200),{once:true});
 HTMLMediaElement.prototype.pause=function(){const i=queue.indexOf(this);if(i>=0)queue.splice(i,1);return pause.apply(this,arguments)};
 HTMLMediaElement.prototype.play=function(){if(this.dataset.videoSrc&&!this.getAttribute('src')){if(!videoReady){if(!queue.includes(this))queue.push(this);return Promise.resolve()}this.src=(small&&this.dataset.videoSrcSmall)||this.dataset.videoSrc;this.load()}return play.apply(this,arguments)};
 const start=()=>{
  const scripts=[...document.querySelectorAll('script[data-deferred-3d]')];if(!scripts.length)return;
  const stage=document.querySelector('[data-ps-stage],[data-u3d-model]');if(!stage)return;
  let started=false;
  const launch=async()=>{if(started)return;started=true;try{
   const p=parent;const key=stage.dataset.psModel||stage.dataset.u3dModel;
   await Promise.all(['uav3dLib','uav3dModel-'+key].map(id=>p.ctuavHydrate(p.document.getElementById(id))));
   for(const source of scripts)await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=source.getAttribute('data-deferred-3d');s.onload=resolve;s.onerror=reject;document.body.append(s)});
  }catch(error){stage.dataset.resourceError=String(error);console.warn('3D resource unavailable',error)}};
  new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting))launch()},{rootMargin:'100px'}).observe(stage);
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
 // Later hero posters load after the page load or on the first slide change.
 const posters=()=>document.querySelectorAll('video[data-defer-poster]').forEach(v=>{v.poster=v.dataset.deferPoster;v.removeAttribute('data-defer-poster')});
 addEventListener('load',()=>setTimeout(posters,1500),{once:true});['pointerdown','keydown'].forEach(t=>document.addEventListener(t,posters,{once:true,capture:true}));
})();
