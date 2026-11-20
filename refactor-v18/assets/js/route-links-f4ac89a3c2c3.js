/* refactor-v16 route links (20261118-v16-card-links-patch.py). Page documents run inside the
   route shell iframe. Route links are real <a href> for crawlers; a plain click stays in-app. */
(()=>{"use strict";
const SEL='a[data-route-link][href]',CARD='a[data-route-post][href]';
const embedded=()=>{try{return window.parent!==window}catch(e){return true}};
const link=e=>e.target&&e.target.closest?e.target.closest(SEL+','+CARD):null;
addEventListener('click',e=>{const a=link(e);if(!a)return;
 // Modified click: the browser opens the route URL in a new tab or window; no in-app navigation.
 if(e.button||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey){e.stopPropagation();return}
 // Direct open (no shell): follow the href in the top window.
 if(!embedded()){e.stopPropagation();return}
 // In the shell: do not load the shell inside the iframe. The page listener posts the route.
 e.preventDefault();
 // Component cards (JavaScript-built): this handler posts the route; no other page listener runs.
 if(a.matches(CARD)){parent.postMessage({namespace:'ctuav-demo',type:'route',route:a.dataset.routePost},'*');e.stopPropagation()}
},true);
// Space activated the former <button>; keep it for the converted links.
const space=e=>e.key===' '&&!e.altKey&&!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&e.target.matches&&e.target.matches(SEL);
addEventListener('keydown',e=>{if(space(e))e.preventDefault()},true);
addEventListener('keyup',e=>{if(space(e)){e.preventDefault();e.target.click()}},true);
})();
