from pathlib import Path
from bs4 import BeautifulSoup
import zipfile,openpyxl,re,json,shutil,html
from PIL import Image
R=Path('projects/main-website/refactor-v02');A=Path(r'C:/Users/ASUS/.t3/userdata/attachments')
def write(p,t):p.write_text(t,encoding='utf-8')
def slug(t):return re.sub('[^a-z0-9]+','-',t.lower()).strip('-')
def norm(t):return re.sub('[^a-z0-9]','',str(t).lower().replace('×','x').replace('�','x'))
def soup(p):return BeautifulSoup(p.read_text(encoding='utf-8'),'html.parser')
def variants(im,stem):
 out=[]
 for size in [480,800,1200]:
  c=im.copy();c.thumbnail((size,size));p=R/'assets/img'/f'{stem}-{size}.webp';c.save(p,'WEBP',quality=80);out.append((p.name,c.width))
 return out
items={}; source=[]
for key in ['a1a9fbda','f149f1ea','58f66160']:
 f=next(A.glob('*'+key+'*'));shutil.copy2(f,R/'source-inputs'/f.name)
 with zipfile.ZipFile(f) as z:
  for info in z.infolist():
   if info.is_dir():continue
   parts=info.filename.split('/');name=parts[-2].replace('�','×');cat=parts[-3] if len(parts)>2 else 'CT-GLOVA'
   if cat=='GNSS & Định vị':cat='GNSS & Positioning'
   if cat=='Module nguồn & PDB':cat='Power Modules & PDB'
   if cat=='Truyền dẫn & Telemetry':cat='Transmission & Telemetry'
   key2=(cat,name);d=items.setdefault(key2,{'id':slug(name),'name':name,'category':cat,'images':[],'detail':True,'variants':{}})
   from io import BytesIO
   im=Image.open(BytesIO(z.read(info))).convert('RGBA');v=variants(im,slug(name)+'-'+slug(Path(parts[-1]).stem));path='../assets/img/'+v[-1][0];d['images'].append(path);d['variants'][path]=v
   source.append({'archive':f.name,'member':info.filename,'delivery':path})
wfile=next(A.glob('*4e9a09fe*'));shutil.copy2(wfile,R/'source-inputs'/wfile.name);w=openpyxl.load_workbook(wfile,data_only=True)
records=[]
for s in w:
 rows=list(s.values)
 headers=rows[2] if s.title=='Linh kien chon' else rows[1]
 for i,row in enumerate(rows):
  if i< (3 if s.title=='Linh kien chon' else 2):continue
  code=row[1] if len(row)>1 else None
  if code:records.append({'name':str(code),'sheet':s.title,'row':i+1,'values':[(str(k),str(v)) for k,v in zip(headers,row) if k and v is not None and str(v) not in ['—','-']]})
# Exact code matches only. Two spelling aliases retain explicit evidence.
alias={'CT-P60-63-HD':'CT-P60-63"HD'}
components=[];matches=[]
for (cat,name),d in items.items():
 if cat=='CT-GLOVA':continue
 cand=[x for x in records if norm(x['name'])==norm(alias.get(name,name)) and x['sheet']!='Linh kien chon']
 d['specs']=cand[0]['values'] if cand else []
 matches.append({'name':name,'category':cat,'match':cand,'status':'matched' if cand else 'PENDING CONFIRMATION'})
 components.append(d)
base=soup(R/'pages/component-3530.html')
for d in components:
 s=BeautifulSoup(str(base),'html.parser');n=d['name'];s.title.string=n+' | CT UAV'
 for x in s.find_all(string=lambda t:t and t.strip()=='3530'):x.replace_with(n)
 for x in s.select('[data-category]'):x['data-category']=d['category'];x.string=d['category']
 im=s.select_one('#product-image');im['src']=d['images'][0];im['alt']=n
 thumbs=s.select_one('.thumbs');thumbs.clear()
 for i,p in enumerate(d['images']):
  b=s.new_tag('button',attrs={'class':'thumb u3d-button','data-src':p,'aria-label':f'Image {i+1}','aria-pressed':str(i==0).lower()});img=s.new_tag('img',src=p,alt=n,loading='lazy',width='100',height='80');b.append(img);thumbs.append(b)
 sec=s.select_one('#specifications');sec.clear();h=s.new_tag('h2');h.string='Specifications';sec.append(h)
 dl=s.new_tag('dl')
 for k,v in d['specs']:
  if k in ['No.','Model/Code','Code','Code/Model']:continue
  div=s.new_tag('div');dt=s.new_tag('dt');dt.string=k;dd=s.new_tag('dd');dd.string=v;div.extend([dt,dd]);dl.append(div)
 if not d['specs']:
  p=s.new_tag('p');p.string='Specifications pending confirmation. Contact CT UAV for details.';sec.append(p)
 else:sec.append(dl)
 write(R/'pages'/('component-'+d['id']+'.html'),str(s))
write(R/'assets/js/shared-script-6b2b16428671.js','window.CTComponents='+json.dumps(components,ensure_ascii=False)+';')
p=R/'assets/js/shared-script-b4c6b5373db6.js';t=p.read_text(encoding='utf-8-sig');t=t.replace("cats=['Fixed-Wing Motor','Propeller','Cylindrical','Gimbal Camera']","cats=[...new Set(data.map(p=>p.category))]")
t=t.replace('<span>${p.detail?tx(\'View details\',\'Xem chi tiết\'):tx(\'View image\',\'Xem ảnh\')}</span>','');t=t.replace('loading="eager" decoding="sync"','loading="lazy" decoding="async"');write(p,t)
p=R/'assets/js/shared-script-a376905ee515.js';t=p.read_text(encoding='utf-8');mapping={d['id']+'-v02.html':'component-'+d['id'] for d in components};mapping['uav-components-v02.html']='uav-components';t=re.sub(r'const routes=\{.*?\};','const routes='+json.dumps(mapping)+';',t,count=1);write(p,t)
# Register routes in shell and router.
s=soup(R/'index.html');newroutes=['ct-glova','ct-fyran-firefighting']+['component-'+d['id'] for d in components]
for route in newroutes:
 if not s.find(id='frame-'+route):
  f=s.new_tag('iframe',attrs={'class':'page-frame product-frame','hidden':'','id':'frame-'+route,'title':route});s.find(id='frame-contact').insert_before(f)
write(R/'index.html',str(s))
p=R/'assets/js/shared-script-3029b0a74f02.js';t=p.read_text(encoding='utf-8');m=re.search(r'const routes=(\[.*?\]);',t);routes=json.loads(m[1]);routes+= [x for x in newroutes if x not in routes];t=t[:m.start(1)]+json.dumps(routes)+t[m.end(1):];write(p,t)
# All component variants, including gallery swaps.
lookup={}
for d in components:
 for path,v in d['variants'].items():lookup[path.removeprefix('../')]={'variants':[['assets/img/'+f,width] for f,width in v],'width':v[-1][1],'height':v[-1][1]}
p=R/'assets/js/component-responsive.js';t=p.read_text(encoding='utf-8');t=re.sub(r'const componentImages=\{.*?\};','const componentImages='+json.dumps(lookup)+';',t,count=1);write(p,t)
# Link planned model rows without changing other models.
for page,old,route,title in [('line-04','CT-FYRAN 44','ct-fyran-firefighting','CT FRYAN (Firefighting)'),('line-06','CT-GLOVA','ct-glova','CT-GLOVA')]:
 s=soup(R/'pages'/f'{page}.html');b=s.select_one(f'[data-planned="{old}"]');b.attrs.pop('data-planned');b['data-route']=route;b.string='Explore '+title+' →'
 for x in b.parent.find_all(string=lambda t:t and t.strip()==old):x.replace_with(title)
 # Existing line script handles data-route.
 write(R/'pages'/f'{page}.html',str(s))
# Firefighting page copies requested copy, replacing hero with existing application photo.
s=soup(R/'pages/ct-fyran-256.html');gallery=[x for x in s.find_all('img') if 'burning' in x.get('alt','')];v=s.find('video');hero=BeautifulSoup(str(gallery[0]),'html.parser').img;hero['class']=v.get('class',[]);hero['loading']='eager';v.replace_with(hero)
for x in s.find_all(string=True):
 if 'CT-FYRAN 256' in x:x.replace_with(str(x).replace('CT-FYRAN 256','CT FRYAN (Firefighting)'))
write(R/'pages/ct-fyran-firefighting.html',str(s))
# CT GLOVA uses the supplied images and existing light-show source copy, no invented specs.
glova=items[('CT-GLOVA','CT-GLOVA')];line=soup(R/'pages/line-06.html');s=BeautifulSoup(str(base),'html.parser');s.title.string='CT-GLOVA | CT UAV'
for x in s.find_all(string=lambda t:t and t.strip()=='3530'):x.replace_with('CT-GLOVA')
for x in s.select('[data-category]'):x.string='Drone Light Show';x['data-category']='Drone Light Show'
s.select_one('#product-image')['src']=glova['images'][0];s.select_one('#product-image')['alt']='CT-GLOVA'
hero=BeautifulSoup(str(line.find('img')),'html.parser').img;hero['loading']='eager';wrap=s.new_tag('section',attrs={'class':'glova-hero'});wrap.append(hero);s.select_one('.detail-hero').insert_before(wrap)
s.select_one('.thumbs').clear()
for i,p in enumerate(glova['images']):
 b=s.new_tag('button',attrs={'class':'thumb u3d-button','data-src':p,'aria-label':f'CT-GLOVA image {i+1}','aria-pressed':str(i==0).lower()});b.append(s.new_tag('img',src=p,alt='CT-GLOVA',width='100',height='80',loading='lazy'));s.select_one('.thumbs').append(b)
lead=s.select_one('.lead');lead.attrs.pop('data-category',None);lead.string='A modern and environmentally responsible alternative to fireworks for festivals, brand activations, private events, tourism, and multimedia performances.'
write(R/'pages/ct-glova.html',str(s))
# Launcher visibility uses actual home hero geometry and follows normal document scrolling.
css='''\n.cu-widget[data-embedded] .cu-launcher{width:76px!important;height:76px!important}.cu-widget[data-embedded] .cu-launcher .ce-mascot{width:76px!important;height:76px!important}html[data-home-hero-visible] .cu-widget .cu-launcher{visibility:hidden!important;pointer-events:none!important}.glova-hero img{width:100%;max-height:70vh;object-fit:cover;border-radius:22px}\n'''
write(R/'assets/css/revision-v02.css',css)
s=soup(R/'index.html');s.head.append(s.new_tag('link',rel='stylesheet',href='assets/css/revision-v02.css'));s.body.append(s.new_tag('script',src='assets/js/revision-v02.js'));write(R/'index.html',str(s))
js='''(()=>{const home=document.getElementById('homeView'),hero=document.getElementById('heroFrame');function update(){const isHome=window.ctuavDemo?.route==='home';const r=hero.getBoundingClientRect();document.documentElement.toggleAttribute('data-home-hero-visible',isHome&&r.bottom>0)}addEventListener('scroll',update,{passive:true});home.addEventListener('scroll',update,{passive:true});addEventListener('resize',update);addEventListener('hashchange',()=>requestAnimationFrame(update));new ResizeObserver(update).observe(hero);update()})();'''
write(R/'assets/js/revision-v02.js',js)
for page in ['ct-glova','ct-fyran-firefighting']:
 s=soup(R/'pages'/f'{page}.html');s.head.append(s.new_tag('link',rel='stylesheet',href='../assets/css/revision-v02.css'));write(R/'pages'/f'{page}.html',str(s))
write(R/'checks/component-matches.json',json.dumps(matches,ensure_ascii=False,indent=2));write(R/'checks/input-map.json',json.dumps(source,ensure_ascii=False,indent=2))
print(len(components),'components',len([x for x in matches if x['match']]),'matched');print('UNMATCHED',[x['name'] for x in matches if not x['match']])
