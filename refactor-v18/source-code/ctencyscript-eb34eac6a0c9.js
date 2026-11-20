(()=>{'use strict';
const cfg=JSON.parse(document.getElementById('cuConfig').textContent),$=id=>document.getElementById(id),root=$('cuWidget'),panel=$('cuPanel'),scroll=$('cuScrollRegion'),input=$('cuInput'),messages=$('cuMessages'),sendButton=$('cuSend');
// Mascot states for the inline CT Ency mascot component. Mounts: every element with data-mascot-state.
const MASCOT_STATES=['idle','greeting','listening','thinking','excited','sorry'];
const MASCOT_REPLY={carbon:'excited',cargo:'excited',source_carbon:'excited',source_cargo:'excited',hello:'greeting',scope:'sorry',outside:'sorry',figures:'sorry',suitability:'sorry',requirement:'sorry'};
let mascotState='idle',greetTimer=0,lang='en',activeTopic=null,modelReference=null,clarificationState='none',generation=0,pending=false;
const copy=()=>cfg.languages[lang];
const normalize=s=>s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/[’]/g,"'").replace(/\s+/g,' ').replace(/[.!?,;:]+$/g,'').trim();
const phrase=(s,p)=>(' '+s.replace(/[^a-z0-9']/g,' ').replace(/\s+/g,' ')+' ').includes(' '+normalize(p)+' ');
const any=(s,values)=>values.some(p=>phrase(s,p));
const nearEnd=()=>scroll.scrollHeight-scroll.scrollTop-scroll.clientHeight<65;
function sync(){root.dataset.activeTopic=activeTopic||'none';root.dataset.modelReference=modelReference||'none';root.dataset.clarification=clarificationState;root.dataset.pending=String(pending)}
function setTopic(topic,model=null){activeTopic=topic;modelReference=model;clarificationState='none';sync()}
function ambiguous(){if(clarificationState!=='none'){clarificationState='explicitChoiceOnly';sync();return 'scope'}clarificationState='awaitingClarification';sync();return 'clarify'}
function classify(raw,explicit){
 if(explicit){if(explicit==='carbon'||explicit==='cargo'){setTopic(explicit);return explicit}if(explicit==='other'){clarificationState='explicitChoiceOnly';sync();return 'scope'}if(explicit==='mission')return ambiguous();if(explicit==='applications')return activeTopic&&clarificationState!=='explicitChoiceOnly'?activeTopic:ambiguous();if(explicit==='source')return activeTopic?(modelReference?'model':('source_'+activeTopic)):ambiguous();if(explicit==='model'){setTopic('carbon','DECARB 22');return 'model'}return explicit}
 let q=normalize(raw),negated=new Set();
 for(const topic of ['carbon','cargo']){for(const p of cfg.matching.negation[topic]){const n=normalize(p);if(phrase(q,n)){negated.add(topic);q=q.replace(n,' ').replace(/\s+/g,' ').trim()}}}
 const carbon=!negated.has('carbon')&&any(q,cfg.matching.carbon),cargo=!negated.has('cargo')&&any(q,cfg.matching.cargo),single=carbon!==cargo?(carbon?'carbon':'cargo'):null;
 // Read the whole request before committing a topic or reply.
 if(any(q,cfg.matching.outside))return 'outside';
 const needsSuitability=any(q,cfg.matching.suitability),needsFigures=any(q,cfg.matching.figures),needsRequirement=any(q,cfg.matching.requirement);
 if(needsSuitability||needsFigures||needsRequirement){if(single)setTopic(single);return needsRequirement?'requirement':needsSuitability?'suitability':'figures'}
 if(/\b(not|don't|do not|khong)\b/.test(q))return ambiguous();
 if(carbon&&cargo)return ambiguous();
 if(single){setTopic(single,carbon&&phrase(q,'decarb 22')?'DECARB 22':null);return modelReference?'model':single}
 if(negated.size)return ambiguous();
 if(any(q,cfg.matching.applications))return activeTopic&&clarificationState!=='explicitChoiceOnly'?(clarificationState='none',activeTopic):ambiguous();
 if(any(q,cfg.matching.source))return activeTopic?(modelReference?'model':'source_'+activeTopic):ambiguous();
 if(any(q,cfg.matching.contact))return 'contact';
 if(any(q,cfg.matching.ambiguous))return ambiguous();
 if(any(q,cfg.matching.company))return 'company';
 if(any(q,cfg.matching.technology))return 'technology';
 if(cfg.matching.hello.some(p=>q===normalize(p)))return 'hello';
 if(cfg.matching.courtesy.some(p=>q===normalize(p)))return 'courtesy';
 if(clarificationState==='awaitingClarification'){clarificationState='explicitChoiceOnly';sync()}
 return 'scope';
}
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function scrollEnd(){scroll.scrollTop=scroll.scrollHeight;$('cuLatest').hidden=true}
function updateSend(){sendButton.disabled=!input.value.trim()||pending;input.style.height='44px';input.style.height=Math.min(92,Math.max(44,input.scrollHeight))+'px'}
function setMascotState(state){if(!MASCOT_STATES.includes(state))return;mascotState=state;clearTimeout(greetTimer);document.querySelectorAll('[data-mascot-state]').forEach(m=>{m.dataset.mascotState=state});document.dispatchEvent(new CustomEvent('ct-ency:mascot-state',{detail:{state}}))}
window.setMascotState=setMascotState;
function mascotOnOpen(open){if(!open){setMascotState('idle');return}setMascotState('greeting');greetTimer=setTimeout(()=>{if(mascotState==='greeting')setMascotState('idle')},2400)}
// Round 3: one visible CT Ency in chat. One head (animated mascot + name) moves to the latest reply or to the typing row.
let headEl=null;function chatHead(){if(!headEl){headEl=el('div','cu-chat-head');const m=el('span','ce-mascot ce-mascot--chat');m.dataset.mascotState=mascotState;m.setAttribute('aria-hidden','true');m.append(el('span','ce-mascot__fallback','CE'));headEl.append(m,el('span','cu-message__from',copy().assistant))}return headEl}
function addMessage(role,text,kind){const row=el('article','cu-message cu-message--'+role);row.dataset.role=role;if(kind)row.dataset.kind=kind;const stack=el('div','cu-message__stack');if(role==='assistant')row.append(chatHead());stack.append(el('div','cu-bubble',text));row.append(stack);messages.append(row);return {row,stack}}
function link(id){const a=el('a','',copy().links[id]);a.href=cfg.destinations[id];if(id!=='email'){a.target='_blank';a.rel='noopener noreferrer'}return a}
function choices(stack,ids){const group=el('div','cu-followups');for(const id of ids){const b=el('button','cu-followup',copy().choices[id]);b.type='button';b.dataset.cuPrompt=id;group.append(b)}stack.append(group)}
function renderReply(kind){if(isV7(kind))return renderV7(kind);const c=copy(),a=c.answers[kind]||c.answers.scope,{row,stack}=addMessage('assistant',a.text,kind);row.dataset.topic=activeTopic||'none';row.dataset.language=lang;row.dataset.sourceId=a.source||'none';
 if(activeTopic){const topic=el('div','cu-topic-label',c.active+': '+c.topics[activeTopic]);stack.prepend(topic)}
 if(kind==='technology'){const list=el('ul','cu-tech-grid');c.technologies.forEach(t=>list.append(el('li','',t)));stack.append(list)}
 if(a.source){stack.append(el('p','cu-source',c.sources[a.source]))}
 let ids=[...(a.links||[])];if(a.contextLink){ids.unshift(activeTopic||'catalogue')}ids=[...new Set(ids)];
 if(ids.length){const actions=el('div','cu-answer-links');ids.forEach(id=>actions.append(link(id)));stack.append(actions)}
 if(ids.includes('email')){stack.append(el('span','cu-email-address','info@ctuav.global'));stack.append(el('p','cu-source',c.mailNote))}
 pageLinks(stack);
 const follow=a.choices||((kind==='carbon'||kind==='cargo'||kind==='source_carbon'||kind==='source_cargo')?['applications','source','contact']:['carbon','cargo']);if(follow.length)choices(stack,follow);
 return row;
}
// ---- CT Ency v07 (2 November 2026): website pages, 16 product lines, 8 model pages, company pages, small talk ----
// Scripted local prototype. No live AI. No specifications, figures, prices or suitability decisions in chat.
// Page chips: in the combined website they call window.ctuavDemo.navigate(route); in the standalone file they open
// the combined website file at #route. embedded() decides the mode at the moment of use.
const V7=cfg.v07,PAGE_BASE='../../main-website-glass-3d-v04.html';
let pageTopic=null,replyPages=[],multiItems=[];
const t7=()=>copy().v07;
function embedded(){return !!(window.ctuavDemo&&typeof window.ctuavDemo.navigate==='function')}
function negatedKey(q,k){return phrase(q,'not '+k)||phrase(q,'khong '+k)||phrase(q,'no '+k)}
function hits(q,keys){return keys.some(k=>phrase(q,k)&&!negatedKey(q,k))}
const FAMILY_RE=new RegExp('\\s(?:ct\\s?)?('+Object.keys(V7.families).join('|')+')\\s?(\\d{1,3})?(?=\\s)','g');
function lineName(route){return t7().lines[route].name}
function nameFor(route){const v=t7();if(v.lines[route])return v.lines[route].name;if(V7.models[route])return V7.models[route].code;return v.pageNames[route]||route}
// Product entities in a message. Each entity belongs to one product line (its group).
function findEntities(q){
 const out=[],q2=' '+q.replace(/[^a-z0-9]+/g,' ').trim()+' ';let m;FAMILY_RE.lastIndex=0;
 while((m=FAMILY_RE.exec(q2))){const f=V7.families[m[1]],n=m[2]||'',model=f.models.find(x=>x.num===n);
  if(model&&model.route)out.push({type:model.route==='decarb22'?'v5model':'model',route:model.route,line:f.line,code:model.code,rank:3});
  else if(model)out.push({type:'planned',route:f.line,line:f.line,code:model.code,rank:2});
  else{const routed=f.models.filter(x=>x.route);
   if(f.line==='line-05')out.push({type:'v5',topic:'carbon',line:'line-05',rank:1});
   else if(routed.length===1)out.push({type:'model',route:routed[0].route,line:f.line,code:routed[0].code,rank:3});
   else out.push({type:'planned',route:f.line,line:f.line,code:f.display,rank:2})}}
 for(const [route,L] of Object.entries(V7.lines))if(L.keys.length&&hits(q,L.keys))out.push({type:'line',route,line:route,rank:1});
 const negC=cfg.matching.negation.carbon.some(p=>phrase(q,p)),negG=cfg.matching.negation.cargo.some(p=>phrase(q,p));
 if(!negC&&any(q,cfg.matching.carbon))out.push({type:'v5',topic:'carbon',line:'line-05',rank:1});
 if(!negG&&any(q,cfg.matching.cargo))out.push({type:'v5',topic:'cargo',line:'line-02',rank:1});
 const groups=new Map();for(const e of out){const g=groups.get(e.line);if(!g||e.rank>g.rank)groups.set(e.line,e)}
 return [...groups.values()];
}
function contactPage(){const line=pageTopic?pageTopic.line:activeTopic==='carbon'?'line-05':activeTopic==='cargo'?'line-02':null;return {route:'contact',line}}
function needsKind(q){return any(q,cfg.matching.requirement)?'requirement':any(q,cfg.matching.suitability)?'suitability':'figures'}
// v05 kinds keep their reply; v07 adds one page chip.
const V5_PAGES={carbon:'line-05',cargo:'line-02',model:'decarb22',source_carbon:'line-05',source_cargo:'line-02',company:'about',technology:'about',scope:'products',outside:'products'};
function afterV5(k){
 if(['carbon','cargo','model','source_carbon','source_cargo'].includes(k))pageTopic=null;
 if(V5_PAGES[k])replyPages=[{route:V5_PAGES[k]}];
 else if(['contact','figures','suitability','requirement'].includes(k))replyPages=[contactPage()];
 return k;
}
function commit7(type,id,raw){
 if(type==='line'){if(id==='line-05')return afterV5(classify(raw,'carbon'));if(id==='line-02')return afterV5(classify(raw,'cargo'));
  setTopic(null);pageTopic={route:id,line:id};replyPages=[{route:id}];return 'line:'+id}
 if(type==='model'){if(id==='decarb22')return afterV5(classify(raw,'model'));
  setTopic(null);pageTopic={route:id,line:V7.models[id].line};replyPages=[{route:id}];return 'model:'+id}
 if(type==='page'){replyPages=[{route:id}];return 'page:'+id}
 if(type==='small'){replyPages=id==='buy'?[contactPage()]:id==='location'?[{route:'contact'}]:id==='capabilities'?[{route:'products'}]:[];return 'small:'+id}
 return afterV5(classify(raw));
}
function classify07(raw,explicit){
 replyPages=[];multiItems=[];
 if(explicit){
  const m=/^(line|model|page|small):(.+)$/.exec(explicit);if(m)return commit7(m[1],m[2],raw);
  if((explicit==='applications'||explicit==='source')&&pageTopic&&!activeTopic){replyPages=[{route:pageTopic.route}];return explicit==='applications'?'topic:apps':'topic:source'}
  return afterV5(classify(raw,explicit));
 }
 const q=normalize(raw),ents=findEntities(q),own=ents.filter(e=>e.type==='model'||e.type==='planned'||e.type==='line');
 const needs=any(q,cfg.matching.suitability)||any(q,cfg.matching.figures)||any(q,cfg.matching.requirement),buy=hits(q,V7.keys.buy);
 if(own.length){
  if(ents.length>1){multiItems=ents.map(e=>e.type==='v5'?{id:e.topic,label:copy().choices[e.topic]}:e.type==='v5model'?{id:'model',label:'DECARB 22'}:e.type==='line'?{id:'line:'+e.route,label:lineName(e.route)}:e.type==='model'?{id:'model:'+e.route,label:e.code}:{id:'line:'+e.line,label:lineName(e.line)});setTopic(null);return 'multi'}
  const e=own[0];setTopic(null);pageTopic={route:e.route,line:e.line,code:e.code};
  if(needs){replyPages=[contactPage()];return needsKind(q)}
  if(buy){replyPages=[contactPage()];return 'small:buy'}
  if(e.type==='planned'){replyPages=[{route:e.line}];pageTopic.planned=e.code;return 'planned:'+e.line}
  return commit7(e.type,e.route,raw);
 }
 if(ents.length===1&&ents[0].type==='v5model'&&!needs)return afterV5(classify(raw,'model'));
 if(ents.length===1&&ents[0].type==='v5'&&!needs&&!buy&&!any(q,cfg.matching[ents[0].topic]))return afterV5(classify(raw,ents[0].topic));
 if(ents.length===1&&ents[0].type==='v5'&&buy&&!needs){setTopic(ents[0].topic);pageTopic=null;replyPages=[contactPage()];return 'small:buy'}
 if(ents.length)return afterV5(classify(raw));
 if(needs)return afterV5(classify(raw));
 if(buy)return commit7('small','buy',raw);
 if(pageTopic&&!activeTopic&&(any(q,cfg.matching.applications)||any(q,cfg.matching.source))){replyPages=[{route:pageTopic.route}];return any(q,cfg.matching.source)?'topic:source':'topic:apps'}
 for(const k of ['bye','human','capabilities','location'])if(hits(q,V7.keys[k]))return commit7('small',k,raw);
 for(const k of ['news-post','news','shareholders','about','products'])if(hits(q,V7.keys[k]))return commit7('page',k,raw);
 if(hits(q,V7.keys.phone))return afterV5(classify(raw,'contact'));
 return afterV5(classify(raw));
}
function isV7(kind){return kind==='multi'||kind.includes(':')}
function mascotV7(kind){if(/^(line|model|topic):/.test(kind))return 'excited';if(kind==='small:bye'||kind==='small:capabilities')return 'greeting';return 'idle'}
function pageHref(route){return (embedded()?'':PAGE_BASE)+'#'+route}
function pageLabel(p){const v=t7();if(p.route==='contact')return p.line?v.contactAbout.replace('{name}',lineName(p.line)):v.open.replace('{name}',v.pageNames.contact);if(p.route==='news-post')return v.openStory;return v.open.replace('{name}',nameFor(p.route))}
function pageLinks(stack){if(!replyPages.length)return;const wrap=el('div','cu-page-links');for(const p of replyPages){const a=el('a','cu-page-link',pageLabel(p));a.href=pageHref(p.route);a.dataset.route=p.route;if(p.route==='contact'&&p.line)a.dataset.line=V7.lines[p.line].option;if(!embedded()){a.target='_blank';a.rel='noopener noreferrer'}wrap.append(a)}stack.append(wrap)}
function choices7(stack,items){if(!items.length)return;const group=el('div','cu-followups'),v=t7();for(const it of items){const label=it.label||copy().choices[it.id]||v.labels[it.id]||it.id;const b=el('button','cu-followup',label);b.type='button';b.dataset.cuPrompt=it.id;group.append(b)}stack.append(group)}
function renderV7(kind){
 const c=copy(),v=c.v07,i=kind.indexOf(':'),type=i<0?kind:kind.slice(0,i),id=i<0?'':kind.slice(i+1);
 let text='',topic=null,source=null,follow=[];
 if(type==='line'){text=v.lines[id].text;topic=v.lines[id].name;source=v.source.replace('{page}',topic);follow=[...V7.lines[id].models.filter(m=>m.route).slice(0,1).map(m=>({id:'model:'+m.route,label:m.code})),{id:'contact'},{id:'page:products'}]}
 else if(type==='model'){text=v.models[id];topic=V7.models[id].code;source=v.source.replace('{page}',topic);follow=[{id:'line:'+V7.models[id].line,label:lineName(V7.models[id].line)},{id:'contact'},{id:'page:products'}]}
 else if(type==='planned'){const code=pageTopic&&pageTopic.planned||'';text=v.planned.replace('{code}',code).replace('{name}',lineName(id));topic=lineName(id);source=v.source.replace('{page}',topic);follow=[{id:'contact'},{id:'page:products'}]}
 else if(type==='page'){text=v.pages[id];source=v.source.replace('{page}',v.pageNames[id]);follow=V7.pageFollow[id].map(x=>({id:x}))}
 else if(type==='small'){text=v.small[id];if(id==='location')source=v.source.replace('{page}',v.pageNames.contact);follow=V7.smallFollow[id].map(x=>({id:x}))}
 else if(type==='topic'){const name=nameFor(pageTopic.route);topic=name;text=(id==='apps'?v.topicApps:v.topicSource).replace('{name}',name);follow=[{id:'contact'},{id:'page:products'}]}
 else if(type==='multi'){text=v.multi;follow=multiItems}
 const {row,stack}=addMessage('assistant',text,kind);row.dataset.topic=pageTopic?pageTopic.route:'none';row.dataset.language=lang;row.dataset.sourceId=type==='multi'?'none':(replyPages[0]||{}).route||'none';
 if(topic)stack.prepend(el('div','cu-topic-label',c.active+': '+topic));
 if(source)stack.append(el('p','cu-source',source));
 pageLinks(stack);choices7(stack,follow);return row;
}
function openPage(route,line){const d=window.ctuavDemo;if(route==='contact'&&line&&typeof d.contact==='function')d.contact(line);else d.navigate(route);if(matchMedia('(max-width: 650px)').matches)setOpen(false)}
root.addEventListener('click',e=>{const a=e.target.closest('.cu-page-link');if(!a||!embedded())return;e.preventDefault();openPage(a.dataset.route,a.dataset.line||'')});
// In the website the chat follows the site language (the Navbar EN / VI button sets <html lang>).
if(embedded())new MutationObserver(()=>{const next=document.documentElement.lang==='vi'?'vi':'en';if(next!==lang)language(next)}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
// r08 (2 Nov 2026, guardian review): in the website, keep the launcher clear of the visible controls of the
// active page (Home: the hero frame), the status messages, the open menus and any open page dialog. The launcher
// moves only after navigation (again when the page reveal settles), resize, Home scroll, frame load and status messages, so it stays still while the
// visitor reads. It never moves above the Navbar; when no clear place exists, it takes the place with least overlap.
if(embedded()){
 const launcher=$('cuLauncher'),home=document.getElementById('homeView'),hero=document.getElementById('heroFrame'),header=document.getElementById('globalHeader');
 const notes=[...document.querySelectorAll('#demoStatus,.hp-note,.hs-status')];
 const SEL='button,a[href],[role=button],input,select,textarea,summary,.explore-button,.slide-choice,.slide-label';
 const GAP=10;let lift=0,timer=0,modalTimer=0;
 const activeFrame=()=>{const r=window.ctuavDemo.route;return r==='home'?hero:document.getElementById('frame-'+r)};
 const frameDoc=f=>{try{return f&&f.contentDocument&&f.contentDocument.body?f.contentDocument:null}catch(e){return null}};
 const shown=(e,d)=>{const cs=d.defaultView.getComputedStyle(e);return cs.visibility!=='hidden'&&cs.display!=='none'&&parseFloat(cs.opacity)>.05};
 function obstacles(){
  const out=[],vw=innerWidth,vh=innerHeight;
  const add=(l,t,w,h)=>{if(w>0&&h>0&&t+h>0&&t<vh&&l+w>0&&l<vw)out.push({left:l,top:t,right:l+w,bottom:t+h})};
  for(const n of notes)if(!n.hidden&&n.getClientRects().length){const r=n.getBoundingClientRect();add(r.left,r.top,r.width,r.height)}
  const f=activeFrame(),d=frameDoc(f);
  if(f&&!f.hidden&&d){const fr=f.getBoundingClientRect();
   for(const e of d.querySelectorAll(SEL)){const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;
    const top=Math.max(fr.top,r.top+fr.top),bottom=Math.min(fr.bottom,r.bottom+fr.top);if(bottom<=top||!shown(e,d))continue;add(r.left+fr.left,top,r.width,bottom-top)}}
  return out;
 }
 function place(){
  if(getComputedStyle(launcher).display==='none')return;
  const base={left:launcher.offsetLeft,top:launcher.offsetTop,right:launcher.offsetLeft+launcher.offsetWidth,bottom:launcher.offsetTop+launcher.offsetHeight};
  const obs=obstacles().filter(o=>o.right>base.left-GAP&&o.left<base.right+GAP);
  const hit=L=>obs.reduce((s,o)=>{const x=Math.min(base.right,o.right+GAP)-Math.max(base.left,o.left-GAP),y=Math.min(base.bottom-L,o.bottom+GAP)-Math.max(base.top-L,o.top-GAP);return s+(x>0&&y>0?x*y:0)},0);
  const hb=header?header.getBoundingClientRect().bottom:0,maxL=Math.max(0,base.top-Math.max(0,hb)-8);
  const cands=[0,...obs.map(o=>base.bottom-o.top+GAP)].filter(L=>L>=0&&L<=maxL).sort((x,y)=>x-y);
  let best=0,bestHit=Infinity;for(const L of cands){const h=hit(L);if(h===0){best=L;bestHit=0;break}if(h<bestHit){best=L;bestHit=h}}
  lift=Math.round(best);root.style.setProperty('--cu-lift',lift+'px');root.dataset.lift=String(lift);root.dataset.liftClear=bestHit===0?'yes':'no';
 }
 const later=(ms=0)=>{clearTimeout(timer);timer=setTimeout(place,ms)};
 // Page dialogs (for example the product payload dialog): hide the launcher while one is open.
 function modal(){const d=frameDoc(activeFrame());const open=!!(d&&[...d.querySelectorAll('dialog[open],[aria-modal="true"]')].some(e=>e.getClientRects().length&&shown(e,d)));root.dataset.modal=open?'open':'';if(!open)later(60)}
 const modalSoon=()=>{clearTimeout(modalTimer);modalTimer=setTimeout(modal,40)};
 const watchFrame=f=>{const d=frameDoc(f);if(!d||d.__ctEncyWatch)return;d.__ctEncyWatch=true;new MutationObserver(modalSoon).observe(d.documentElement,{subtree:true,attributes:true,attributeFilter:['open','hidden','aria-modal','aria-hidden']})};
 const ctWatch=f=>{watchFrame(f);f.addEventListener('load',()=>{watchFrame(f);if(f===activeFrame()){modal();later(400);setTimeout(()=>later(0),2400)}})};
document.querySelectorAll('iframe').forEach(ctWatch);
// Page frames are created on demand (Batch 1, v04).
document.addEventListener('ctuav:frame',ev=>ctWatch(ev.detail));
 const menu=()=>{const m=document.getElementById('menuButton'),pp=document.getElementById('productsPanel');root.dataset.menu=((m&&m.getAttribute('aria-expanded')==='true')||(pp&&!pp.hidden))?'open':'';if(!root.dataset.menu)later(60)};
 const mo=new MutationObserver(()=>{menu();later(0)});
 notes.forEach(n=>mo.observe(n,{attributes:true,attributeFilter:['hidden','class','style']}));
 ['menuButton','productsPanel'].forEach(id=>{const n=document.getElementById(id);if(n)mo.observe(n,{attributes:true,attributeFilter:['hidden','aria-expanded']})});
 new MutationObserver(()=>later(60)).observe(root,{attributes:true,attributeFilter:['class']});
 if(home)home.addEventListener('scroll',()=>later(120),{passive:true});
 addEventListener('hashchange',()=>{modal();later(900);setTimeout(()=>later(0),2600)});addEventListener('resize',()=>later(200));addEventListener('load',()=>later(300));
 menu();modal();later(1200);
}

function send(text,explicit){text=text.trim().slice(0,500);if(!text||pending)return;input.focus({preventScroll:true});$('cuWelcome').hidden=true;messages.hidden=false;addMessage('user',text);const kind=classify07(text,explicit);pending=true;sync();updateSend();scrollEnd();setMascotState('thinking');const typing=el('div','cu-typing-row'),typingText=el('div','cu-typing',copy().preparing);typingText.setAttribute('role','status');typing.append(chatHead(),typingText);messages.append(typing);scrollEnd();const token=generation;
 setTimeout(()=>{if(token!==generation)return;const followEnd=nearEnd();typing.remove();renderReply(kind);setMascotState(MASCOT_REPLY[kind]||mascotV7(kind));pending=false;sync();updateSend();if(followEnd)scrollEnd();else $('cuLatest').hidden=false},320)
}
function reset(){generation++;pending=false;pageTopic=null;replyPages=[];multiItems=[];activeTopic=null;modelReference=null;clarificationState='none';messages.replaceChildren();messages.hidden=true;$('cuWelcome').hidden=false;input.value='';$('cuLatest').hidden=true;scroll.scrollTop=0;sync();updateSend();setMascotState('idle')}
function language(next){lang=next;root.dataset.lang=lang;if(!embedded())document.documentElement.lang=lang;const c=copy();(embedded()?root:document).querySelectorAll('[data-i18n]').forEach(n=>{n.textContent=c.ui[n.dataset.i18n]});input.placeholder=c.ui.placeholder;input.setAttribute('aria-label',c.ui.placeholder);sendButton.setAttribute('aria-label',c.ui.send);$('cuClose').setAttribute('aria-label',c.ui.close);$('cuNewChat').setAttribute('aria-label',c.ui.reset);$('cuNewChat').title=c.ui.reset;$('cuClose').title=c.ui.close;panel.setAttribute('aria-label',c.ui.dialog);$('cuLangEn').setAttribute('aria-pressed',String(lang==='en'));$('cuLangVi').setAttribute('aria-pressed',String(lang==='vi'));$('cuLauncher').setAttribute('aria-label',panel.hidden?c.ui.open:c.ui.close);$('cuMessages').setAttribute('aria-label',c.ui.conversation);$('cuLatest').textContent=c.ui.latest;}
function setOpen(open,focus=true){panel.hidden=!open;root.classList.toggle('cu-open',open);$('cuLauncher').setAttribute('aria-expanded',String(open));$('cuLauncher').setAttribute('aria-label',open?copy().ui.close:copy().ui.open);if(focus)(open?input:$('cuLauncher')).focus({preventScroll:true});mascotOnOpen(open)}
$('cuLauncher').addEventListener('click',()=>setOpen(panel.hidden));$('cuClose').addEventListener('click',()=>setOpen(false));$('cuNewChat').addEventListener('click',()=>{reset();input.focus({preventScroll:true})});
root.addEventListener('click',e=>{const b=e.target.closest('[data-cu-prompt]');if(b&&!pending){const id=b.dataset.cuPrompt;send(copy().questions[id]||b.textContent,id)}const languageButton=e.target.closest('[data-lang-option]');if(languageButton)language(languageButton.dataset.langOption)});
$('cuComposer').addEventListener('submit',e=>{e.preventDefault();if(pending)return;const q=input.value.trim();if(!q)return;input.value='';send(q);updateSend()});input.addEventListener('input',()=>{updateSend();if(!pending)setMascotState(input.value.trim()?'listening':'idle')});input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('cuComposer').requestSubmit()}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden){e.preventDefault();setOpen(false)}});$('cuLatest').addEventListener('click',()=>{scrollEnd();input.focus({preventScroll:true})});scroll.addEventListener('scroll',()=>{if(nearEnd())$('cuLatest').hidden=true});
if(window.visualViewport){const fit=()=>{if(innerWidth<=650){panel.style.height=Math.max(180,visualViewport.height-16)+'px';panel.style.top=(visualViewport.offsetTop+8)+'px'}else{panel.style.height='';panel.style.top=''}};visualViewport.addEventListener('resize',fit);visualViewport.addEventListener('scroll',fit);fit()}
language(embedded()&&document.documentElement.lang==='vi'?'vi':'en');sync();updateSend();setOpen(root.dataset.startOpen==='true',false);
})();
