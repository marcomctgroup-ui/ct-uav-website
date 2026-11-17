"""Haykal's seven visual corrections. Extend current v04, preserve technical work."""
from pathlib import Path
import shutil, re, json, hashlib
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'checks/20261105-visual-refinement'
assert not OUT.exists(), 'Already applied. Inspect current source before further edits.'
OUT.mkdir()
def read(p):return p.read_text(encoding='utf8')
def write(p,t):
    if p.exists():
        before=OUT/'before'/p.relative_to(ROOT);before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,before)
    p.write_text(t,encoding='utf8',newline='')
def js(name,t):
    write(ROOT/'assets/js'/name,t);write(ROOT/'source-code'/name,t)

index_path=ROOT/'index.html';index=read(index_path);before_hash=hashlib.sha256(index_path.read_bytes()).hexdigest()
# One visible model name; no category row, arrow or action line inside cards.
p=ROOT/'assets/js/shared-script-c650fa76d9e4.js';t=read(p)
needle='</span></a></article>`}).join(\'\');animateCards()}'
assert needle in t
t=t.replace(needle,'</span><h2 class="component-card-name">${esc(p.name)}</h2></a></article>`}).join(\'\');animateCards()}')
t=t.replace("const q=$('#search').value.trim()", "const mobile=$('#categorySelect');if(mobile){mobile.innerHTML=['All',...cats].map(c=>`<option value=\"${esc(c)}\"${category===c?' selected':''}>${c==='All'?tx('All components','Tất cả linh kiện'):label(c)} (${c==='All'?data.length:data.filter(p=>p.category===c).length})</option>`).join('')}const q=$('#search').value.trim()")
t=t.replace("if(grid){$('#categories').addEventListener", "if(grid){$('#categorySelect')?.addEventListener('change',e=>{category=e.target.value;const u=new URL(location);category==='All'?u.searchParams.delete('category'):u.searchParams.set('category',category);if(parent===window)history.replaceState(null,'',u);render()});$('#categories').addEventListener")
js(p.name,t)
p=ROOT/'pages/uav-components.html';s=BeautifulSoup(read(p),'html.parser')
control=BeautifulSoup('<label class="category-select"><span data-en="Category" data-vi="Danh mục">Category</span><select id="categorySelect" aria-label="Component category"></select></label>','html.parser')
s.select_one('#categories').insert_after(control)
s.head.append(BeautifulSoup('<link rel="stylesheet" href="../assets/css/catalogue-refinement-v04.css">','html.parser'))
write(p,str(s))
css='''.toolbar{gap:24px}.categories{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;width:100%}.categories .news-filter{display:flex;justify-content:space-between;align-items:center;gap:12px;width:100%;min-width:0;min-height:60px;padding:14px 20px;border-radius:16px;white-space:normal;text-align:left;line-height:1.4}.categories .news-filter span{flex-shrink:0}.category-select{display:none}.component-card-name{margin:0;padding:20px 24px 24px;font-size:clamp(17px,1.5vw,21px);line-height:1.4;font-weight:600;overflow-wrap:anywhere}.card-link{height:100%;display:flex;flex-direction:column}.card-image{flex:0 0 auto}.intro{padding-bottom:32px;margin-bottom:32px}.toolbar .tools{width:100%}@media(max-width:1050px){.categories{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:760px){.categories{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.categories{display:none}.category-select{display:grid;gap:10px;width:100%;font-size:15px;font-weight:600}.category-select select{display:block;box-sizing:border-box;width:100%;max-width:100%;min-height:52px;padding:12px 16px;border:1px solid var(--glass-border);border-radius:14px;color:var(--site-ink,#172127);background:var(--glass-fill-strong);font:500 15px/1.4 Montserrat,sans-serif}.component-card-name{padding:18px 20px 22px;font-size:18px}.toolbar{gap:18px}.intro{padding-bottom:24px;margin-bottom:24px}}'''
write(ROOT/'assets/css/catalogue-refinement-v04.css',css)

# Local code-native flags avoid emoji/platform font differences.
write(ROOT/'assets/img/flag-en.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 40"><clipPath id="c"><path d="M0 0h60v40H0z"/></clipPath><g clip-path="url(#c)"><path fill="#21468b" d="M0 0h60v40H0z"/><path stroke="#fff" stroke-width="8" d="m0 0 60 40M60 0 0 40"/><path stroke="#c8102e" stroke-width="3" d="m0 0 60 40M60 0 0 40"/><path stroke="#fff" stroke-width="13" d="M30 0v40M0 20h60"/><path stroke="#c8102e" stroke-width="8" d="M30 0v40M0 20h60"/></g></svg>')
write(ROOT/'assets/img/flag-vi.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 40"><path fill="#da251d" d="M0 0h60v40H0z"/><path fill="#ffdf00" d="m30 8 2.82 8.68h9.13l-7.39 5.37 2.82 8.68L30 25.37l-7.38 5.36 2.82-8.68-7.39-5.37h9.13z"/></svg>')
old=re.search(r'<button[^>]*id="languageButton".*?</button>',index,re.S).group()
new='<button aria-label="English. Change language to Vietnamese" title="English — Tiếng Việt" class="language-button" id="languageButton" type="button"><img src="assets/img/flag-en.svg" width="30" height="20" alt="" aria-hidden="true"></button>'
index=index.replace(old,new)
p=ROOT/'assets/js/shared-script-96ab1a036400.js';t=read(p)
old='languageButton.textContent=next==="en"?"EN / VI":"VI / EN";'
assert old in t
t=t.replace(old,'languageButton.innerHTML=`<img src="assets/img/flag-${next}.svg" width="30" height="20" alt="" aria-hidden="true">`;languageButton.title=next==="en"?"English — Tiếng Việt":"Tiếng Việt — English";')
js(p.name,t)

# Use the exact accepted Navbar cutout in the Home product card.
s=BeautifulSoup(index,'html.parser');home=s.select_one('a.hp-card[data-route="ct-fyran-256"] img')
assert home
home['src']='assets/img/fyran-navbar-uav-00204-v03.webp';home['width']='900';home['height']='450';home['alt']='CT-FYRAN 256'
home.attrs.pop('srcset',None);home.attrs.pop('sizes',None)
# Make surgical replacements so inert templates, script bytes and Claude's CSP stay intact.
original_img=re.search(r'(<a class="hp-card" data-route="ct-fyran-256".*?)(<img[^>]+>)(.*?</a>)',index,re.S)
assert original_img
index=index[:original_img.start(2)]+str(home)+index[original_img.end(2):]
index=index.replace('</head>','<link rel="stylesheet" href="assets/css/visual-refinement-v04.css"></head>',1)
assert hashlib.sha256(index_path.read_bytes()).hexdigest()==before_hash,'Concurrent index change; merge before writing.'
write(index_path,index)
css='''#globalHeader .nav-inner{display:flex;max-width:1600px;min-height:84px;margin:0 auto;padding:0 24px;gap:20px;justify-content:space-between}#globalHeader .brand-lockup{flex:0 0 auto;gap:16px}#globalHeader .brand-button{min-width:90px}#globalHeader .brand-button img{width:90px;height:auto}#globalHeader .member-logo{width:270px;height:auto}#globalHeader .main-nav{flex:0 0 auto;margin-left:12px;gap:18px;justify-content:flex-start}#globalHeader .nav-link{padding-left:0;padding-right:0}#globalHeader .nav-contact{padding-left:20px;padding-right:20px}#globalHeader .nav-tools{margin-left:36px;gap:12px;flex-shrink:0}#globalHeader .language-button{display:grid;place-items:center;min-width:44px;min-height:44px;padding:8px;border-radius:50%;background:var(--glass-fill);border:1px solid var(--glass-border)}#globalHeader .language-button img{display:block;width:30px;height:20px;border-radius:3px;object-fit:cover}.cu-widget[data-embedded] .cu-launcher{perspective:400px}.cu-widget[data-embedded] .cu-launcher .ce-mascot{animation:ency-look-v04 8s ease-in-out infinite!important;transform-origin:center;transform-style:preserve-3d}@keyframes ency-look-v04{0%,100%{transform:translate3d(0,3px,0) rotateY(0deg) rotateZ(0deg)}22%{transform:translate3d(-3px,-3px,0) rotateY(-30deg) rotateZ(-4deg)}48%{transform:translate3d(0,-6px,0) rotateY(0deg) rotateZ(0deg)}73%{transform:translate3d(3px,-2px,0) rotateY(30deg) rotateZ(4deg)}}@media(max-width:1350px) and (min-width:1181px){#globalHeader .member-logo{width:230px}#globalHeader .main-nav{gap:14px;margin-left:8px}#globalHeader .nav-inner{gap:16px;padding:0 20px}#globalHeader .nav-tools{margin-left:28px}}@media(max-width:1180px){#globalHeader .nav-inner{min-height:76px;flex-wrap:wrap;gap:0;padding:0 20px}#globalHeader .member-logo{width:240px}#globalHeader .nav-tools{margin-left:auto;gap:12px}#globalHeader .menu-button{display:flex}#globalHeader .main-nav{display:none;order:3;flex:0 0 100%;margin:0;flex-direction:column;align-items:stretch;gap:0;padding:10px 0 14px}#globalHeader .main-nav.is-open{display:flex}#globalHeader .nav-link{width:100%;min-height:48px;padding:10px 4px;justify-content:space-between;text-align:left;font-size:15px;border:0;border-radius:0;background:transparent}#globalHeader .nav-contact{padding-left:4px;padding-right:4px}}@media(max-width:600px){#globalHeader .nav-inner{min-height:76px;padding:0 12px}#globalHeader .brand-button{min-width:66px}#globalHeader .brand-button img{width:66px}#globalHeader .member-logo{width:160px}#globalHeader .brand-lockup{gap:10px}#globalHeader .brand-divider{height:30px}#globalHeader .nav-tools{gap:6px;margin-left:auto}}@media(max-width:360px){#globalHeader .nav-inner{padding:0 10px}#globalHeader .brand-button{min-width:54px}#globalHeader .brand-button img{width:54px}#globalHeader .member-logo{width:120px}#globalHeader .brand-lockup{gap:8px}}@media(prefers-reduced-motion:reduce){.cu-widget[data-embedded] .cu-launcher .ce-mascot{animation:none!important;transform:none!important}}'''
write(ROOT/'assets/css/visual-refinement-v04.css',css)
# Actual 3D mascot also looks left/right after its existing deferred engine starts.
p=ROOT/'assets/js/ctencymascotengine-b2eac36087de.js';t=read(p)
old='inst.look=Math.random()<0.4?[0,0]:[rand(-0.22,0.22),rand(-0.06,0.08)];inst.nextLook=t+rand(3,6.5);'
assert old in t
t=t.replace(old,"inst.look=inst.host.closest('.cu-launcher')?[(Math.sin(t*.7)>=0?1:-1)*.48,rand(-.06,.08)]:(Math.random()<0.4?[0,0]:[rand(-0.22,0.22),rand(-0.06,0.08)]);inst.nextLook=t+(inst.host.closest('.cu-launcher')?2.8:rand(3,6.5));")
js(p.name,t)

# Model-specific display materials follow Haykal's supplied colour reference.
# Keep supplied GLB and geometry unchanged. Clone materials per mesh for safe colour assignment.
palette="""function styleFirefighting(object){const list=Array.isArray(object.material)?object.material:[object.material];const path=[];for(let p=object;p;p=p.parent)path.push(p.name||'');const part=path.join(' ').toLowerCase();object.material=list.map(original=>{const m=original.clone(),name=(m.name||'').toLowerCase(),c=m.color;const r=c.r,g=c.g,b=c.b;const neutral=Math.abs(r-g)<.015&&Math.abs(g-b)<.015;if(name.includes('steel')){c.set('#8b9298');m.roughness=.55;m.metalness=.6;}else if(name==='white high gloss plastic'){c.set('#c8cbcd');m.roughness=.5;}else if(part.includes('bola_oren')){c.set('#db7800');m.roughness=.48;m.metalness=.1;}else if(name.includes('blue glass')){c.set('#182b50');m.transmission=.3;}else if(name.includes('clear glass')){m.roughness=.1;}else if(name.includes('red')||(r>.5&&g<.12&&b<.12)){c.set('#b8000b');m.roughness=.45;}else if(neutral){c.set(name.includes('black')?'#202428':'#33383c');m.roughness=.6;m.metalness=.18;}else if(r>.5&&g>.4&&b<.55){c.set('#ac8f3f');m.roughness=.6;}m.envMapIntensity=.55;return m});if(!Array.isArray(originalMaterial(object)))object.material=object.material[0];}function originalMaterial(object){return object.userData.ctOriginalMaterialArray?[]:null;}"""
# Preserve material-array shape without storing object references in userData.
palette=palette.replace("const list=Array.isArray(object.material)?object.material:[object.material];", "const wasArray=Array.isArray(object.material),list=wasArray?object.material:[object.material];")
palette=palette.replace("if(!Array.isArray(originalMaterial(object)))object.material=object.material[0];}function originalMaterial(object){return object.userData.ctOriginalMaterialArray?[]:null;}","if(!wasArray)object.material=object.material[0];}")
for name in ['firefighting-shared-script-72c298408fef.js','firefighting-shared-script-8fa5ef83d2b3.js']:
    p=ROOT/'assets/js'/name;t=read(p)
    old='model.traverse(object=>{if(object.isMesh)config.tweak(object.material);});'
    assert old in t
    t=t.replace(old,palette+'model.traverse(object=>{if(object.isMesh)styleFirefighting(object);});')
    t=t.replace('renderer.toneMappingExposure=1.05','renderer.toneMappingExposure=.9').replace('scene.environmentIntensity=.9','scene.environmentIntensity=.5').replace('DirectionalLight(0xffffff,1.6)','DirectionalLight(0xffffff,1.15)').replace('DirectionalLight(0xeef3f6,.8)','DirectionalLight(0xeef3f6,.55)').replace('HemisphereLight(0xffffff,0xd8dee1,.6)','HemisphereLight(0xffffff,0xd8dee1,.45)')
    js(name,t)
(OUT/'source-notes.json').write_text(json.dumps({'date':'2026-11-05','version':'refactor-v04 r03','model_geometry_unchanged':True,'model_colour_reference':'Screenshot 2026-11-05 105505.png supplied by Haykal','home_fyran_image':'Same existing Navbar cutout','language_flags':'UK for English, Vietnam for Vietnamese; flag shows current language; accessible label gives switch action','existing_data_and_pending_specifications_unchanged':True},indent=2),encoding='utf8')
print('Applied seven corrections to current v04. Backups saved.')
