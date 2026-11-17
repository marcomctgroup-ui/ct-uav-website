/* CMS owns content fields; the legacy dictionary owns interface labels. */
(()=>{'use strict';
let language=document.documentElement.lang==='vi'?'vi':'en';
function apply(lang){
  language=lang==='vi'?'vi':'en';
  document.querySelectorAll('[data-cms-en]').forEach(el=>{
    const value=el.getAttribute('data-cms-'+language);if(value===null)return;
    const property=el.dataset.cmsProperty;
    if(property==='alt')el.setAttribute('alt',value);
    else if(property==='content')el.setAttribute('content',value);
    else if(property==='metric'){
      const match=value.match(/^(.*)\s+(kg|km|ha|m\/s|minutes|min|phút)$/);
      el.textContent=match?match[1]+' ':value;
      if(match){const unit=document.createElement('span');unit.textContent=match[2];el.append(unit);}
    }else if(property==='figure'){
      const match=value.match(/^(.*\S)\s+(kg|km|ha|m\/s|minutes|min|phút)$/);
      el.textContent=match?match[1]+' ':value;
      if(match){const unit=document.createElement('small');unit.textContent=match[2];el.append(unit);}
    }else el.textContent=value;
  });
  document.querySelectorAll('[data-cms-aria-en]').forEach(el=>{
    const value=el.getAttribute('data-cms-aria-'+language);if(value)el.setAttribute('aria-label',value);
  });
  updateStaticStories();
}
function updateStaticStories(){
  document.querySelectorAll('[data-cms-static-story]').forEach(stage=>{
    const chapters=[...stage.querySelectorAll('[data-cms-fallback-src]')];
    if(!chapters.length)return;
    const focus=innerHeight*(innerWidth<900?.68:.5);
    const distance=el=>Math.abs((el.querySelector('.ps-card')||el).getBoundingClientRect().top-focus);
    const nearest=chapters.reduce((a,b)=>distance(a)<=distance(b)?a:b);
    const image=stage.querySelector('.ps-fallback'),src=nearest.dataset.cmsFallbackSrc;
    if(image.getAttribute('src')!==src){image.src=src;image.srcset=[480,800,1600].map(w=>`${src}/m/${w}x0 ${w}w`).join(', ');}
    image.dataset.cmsEn=nearest.dataset.cmsFallbackEn;image.dataset.cmsVi=nearest.dataset.cmsFallbackVi;
    image.alt=nearest.getAttribute('data-cms-fallback-'+language)||'';
  });
}
addEventListener('message',event=>{if(event.source===parent&&event.data?.namespace==='ctuav-demo'&&event.data.type==='lang')apply(event.data.lang);});
new MutationObserver(()=>apply(document.documentElement.lang)).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
let queued=false;addEventListener('scroll',()=>{if(!queued){queued=true;requestAnimationFrame(()=>{queued=false;updateStaticStories();});}},{passive:true});
addEventListener('resize',updateStaticStories);
try{language=parent.ctuavI18n?.lang||language;}catch{}
// Re-apply hook for the Storyblok preview bridge after it changes data-cms-en/vi.
window.ctuavCmsApply=lang=>apply(lang===undefined?language:lang);
apply(language);
})();
