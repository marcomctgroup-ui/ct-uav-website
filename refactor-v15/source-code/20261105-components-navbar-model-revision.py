"""Apply Haykal's component, Navbar and model changes to current v04. Run once.
Preserve current bytes before edits. Never rebuild v04 from an older version.
"""
from pathlib import Path
import json, re, hashlib, shutil, html, unicodedata
from bs4 import BeautifulSoup
from PIL import Image
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / 'checks' / '20261105-components-navbar-model'
assert not CHECK.exists(), 'Revision already started; inspect records before running again.'
CHECK.mkdir()
def rd(p): return p.read_text(encoding='utf-8')
def save(p, text):
    if p.exists():
        backup = CHECK / 'before' / p.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, backup)
    p.write_text(text, encoding='utf-8', newline='')
def j(x): return json.dumps(x, ensure_ascii=False, separators=(',', ':'))
def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(s)).lower())
def slug(s): return re.sub(r'[^a-z0-9]+', '-', str(s).lower()).strip('-')
def esc(s): return html.escape(str(s), quote=True)

index_path = ROOT/'index.html'
index = rd(index_path)
initial_hash = hashlib.sha256(index_path.read_bytes()).hexdigest()
data_path = ROOT/'assets/js/shared-script-6b2b16428671.js'
data = json.loads(rd(data_path).split('=', 1)[1].strip().rstrip(';'))
original_ids = {x['id'] for x in data}
known = {norm(x['name']): x for x in data}
workbook_path = next((ROOT/'source-inputs').glob('*.xlsx'))
book = openpyxl.load_workbook(workbook_path, data_only=True)
rows = {}
for sheet in book:
    if sheet.title in ['May bay', 'Vat lieu', 'Phan mem']: continue
    vals = list(sheet.values)
    hi = 2 if sheet.title == 'Linh kien chon' else 1
    headers = vals[hi]
    for rowno, values in enumerate(vals[hi+1:], hi+2):
        code = values[1] if len(values)>1 else None
        if not code: continue
        pairs = [[str(k),str(v)] for k,v in zip(headers,values) if k and v is not None and str(v).strip() not in ['', '—', '-'] and str(k) not in ['No.', 'Model/Code','Code/Model','Code','Mã']]
        rows.setdefault(norm(code), []).append({'sheet':sheet.title,'row':rowno,'values':pairs})

sources = Path('C:/Users/ASUS/Downloads/Components IMG No Background/Anh')
cats = {'GNSS & Định vị':'GNSS & Positioning', 'Module nguồn & PDB':'Power Modules & PDB', 'Truyền dẫn & Telemetry':'Transmission & Telemetry', 'Bộ điều khiển':'Ground Controller', 'Cứu hộ & Chữa cháy':'Rescue & Firefighting', 'Thả hàng & Hậu cần':'Payload Delivery'}
records, duplicates, image_hashes = [], [], {}
responsive_path=ROOT/'assets/js/component-responsive.js'
responsive=rd(responsive_path)
meta=json.loads(responsive.split('=',1)[1].split(';(()=>',1)[0])
for folder in sorted({p.parent for p in sources.rglob('*.png')}):
    name=folder.name
    if norm(name) in known:
        duplicates.append({'name':name,'existing':known[norm(name)]['id']});continue
    ident=slug(name)
    assert ident not in {p['id'] for p in data}
    images=[]; variants={}; seen=set()
    for src in sorted(folder.glob('*.png')):
        digest=hashlib.sha256(src.read_bytes()).hexdigest()
        if digest in seen: continue
        seen.add(digest)
        im=Image.open(src); widths=sorted({min(im.width,w) for w in [480,800,1200]})
        entries=[]
        for width in widths:
            target=f'component-{ident}-{src.stem}-{width}.webp'
            resized=im.resize((width,round(im.height*width/im.width)),Image.Resampling.LANCZOS)
            resized.save(ROOT/'assets/img'/target,'WEBP',quality=82,method=6)
            entries.append([target,width])
        main='../assets/img/'+entries[-1][0]
        images.append(main);variants[main]=entries
        meta[main[3:]]={'variants':[['assets/img/'+p,w] for p,w in entries],'width':widths[-1],'height':round(im.height*widths[-1]/im.width)}
        image_hashes[str(src)] = digest
    matches=rows.get(norm(name),[])
    # Use a full catalogue row before the selected-components summary.
    match=next((m for m in matches if m['sheet']!='Linh kien chon'),matches[0] if matches else None)
    item={'id':ident,'name':name,'category':cats.get(folder.parent.name,folder.parent.name),'images':images,'variants':variants,'detail':True,'specs':match['values'] if match else []}
    data.append(item);known[norm(name)]=item
    records.append({'name':name,'id':ident,'source':str(folder),'match':match,'status':'matched' if match else 'pending'})

template=BeautifulSoup(rd(ROOT/'pages/component-3530.html'),'html.parser')
label_vi={x.get('data-en', x.text):x.get('data-vi',x.text) for x in template.select('[data-en]')}
label_vi.update({'Code':'Mã','Name':'Tên','Type':'Loại','Key Specs':'Thông số chính','Features':'Tính năng','Sensor':'Cảm biến','Resolution':'Độ phân giải','Capacity':'Dung lượng','Energy':'Năng lượng','Cell Config':'Cấu hình cell','Cycles':'Chu kỳ','Compatibility':'Tương thích','Notes':'Ghi chú','CDR / Power':'Dòng xả liên tục / Công suất','Burst / Current':'Dòng xả tức thời / Dòng điện','Charge / Special':'Sạc / Đặc điểm','Weight / Energy Density':'Khối lượng / Mật độ năng lượng','Thông số chính':'Thông số chính','Ứng dụng':'Ứng dụng','Trạng thái':'Trạng thái','Nhóm':'Nhóm'})
for item in data:
    if item['id'] in original_ids: continue
    s=BeautifulSoup(str(template),'html.parser'); name=item['name'];category=item['category']
    s.title.string=name+' | CT UAV Components'
    s.select_one('h1').string=name
    s.select_one('.crumb span:last-child').string=name
    for e in s.select('[data-category]'): e['data-category']=category;e.string=category
    s.select_one('#overview .eyebrow').string=name
    overview=s.select_one('#overview dl');overview.find('dd').string=name
    back=s.select_one('a.back');back['href']='uav-components-v02.html?category='+__import__('urllib.parse',fromlist=['quote']).quote(category)
    gallery=s.select_one('.gallery');gallery.clear()
    gallery.append(BeautifulSoup('<div class="main-image"><button id="zoom" aria-label="Enlarge product image"><img id="product-image" src="'+esc(item['images'][0])+'" alt="'+esc(name)+'" width="1200" height="1000" loading="eager" decoding="async"></button></div><div class="thumbs" aria-label="Product images">'+''.join('<button class="thumb u3d-button" data-src="'+esc(im)+'" aria-label="Image '+str(i+1)+'" aria-pressed="'+str(i==0).lower()+'"><img src="'+esc(im)+'" alt="'+esc(name)+'" width="100" height="80" loading="lazy"></button>' for i,im in enumerate(item['images']))+'</div>','html.parser'))
    spec=s.select_one('#specifications');spec.clear();spec.append(BeautifulSoup('<h2 data-en="Specifications" data-vi="Thông số">Specifications</h2>','html.parser'))
    pairs=item['specs']
    if pairs:
        spec.append(BeautifulSoup('<dl>'+''.join('<div><dt data-en="'+esc(k)+'" data-vi="'+esc(label_vi.get(k,k))+'">'+esc(k)+'</dt><dd>'+esc(v)+'</dd></div>' for k,v in pairs)+'</dl>','html.parser'))
    else:spec.append(BeautifulSoup('<p data-en="Specifications pending confirmation. Contact CT UAV for details." data-vi="Thông số kỹ thuật đang chờ xác nhận. Vui lòng liên hệ CT UAV để biết chi tiết.">Specifications pending confirmation. Contact CT UAV for details.</p>','html.parser'))
    s.select_one('#enlarged')['src']=item['images'][0];s.select_one('#enlarged')['alt']=name
    save(ROOT/'pages'/('component-'+item['id']+'.html'),str(s))

save(data_path,'window.CTComponents='+j(data)+';')
save(responsive_path,'const componentImages='+j(meta)+';(()=>'+responsive.split(';(()=>',1)[1])
# Keep one link per card. Its accessible name retains the model name.
catalogue_path=ROOT/'assets/js/shared-script-c650fa76d9e4.js'
catalogue=rd(catalogue_path)
catalogue=re.sub(r'<div class="card-content">.*?</div></a></article>', '</a></article>',catalogue,count=1)
assert 'class="card-content"' not in catalogue
save(catalogue_path,catalogue)
map_path=ROOT/'assets/js/shared-script-a376905ee515.js';route_adapter=rd(map_path)
route_map=json.loads(re.search(r'const routes=(\{.*?\});',route_adapter).group(1))
for item in data:route_map[item['id']+'-v02.html']='component-'+item['id']
route_adapter=re.sub(r'const routes=\{.*?\};','const routes='+j(route_map)+';',route_adapter,count=1)
save(map_path,route_adapter)
# Extend the current lazy-frame router. Do not replace Claude's router changes.
router_path=ROOT/'assets/js/shared-script-27159330c4a7.js';router=rd(router_path)
routes=json.loads(re.search(r'const routes=(\[.*?\]);',router).group(1))
for item in data:
    route='component-'+item['id']
    if route not in routes:
        routes.append(route)
        index=index.replace('</template>','<iframe class="page-frame" hidden id="frame-'+route+'" title="'+esc(item['name'])+'"></iframe></template>',1)
router=re.sub(r'const routes=\[.*?\];','const routes='+j(routes)+';',router,count=1)
save(router_path,router)

# The supplied PNG already has true alpha. Resize without changing the logo.
logo=Image.open('C:/Users/ASUS/.t3/userdata/attachments/dd337a6c-a8bc-49e2-87ee-c984272aafad-e3129806-4569-4a7c-acb7-335d78b3b4db.png')
assert logo.mode=='RGBA' and logo.getextrema()[3][0]==0
logo.thumbnail((900,120),Image.Resampling.LANCZOS)
logo.save(ROOT/'assets/img/ct-group-member-v04.webp','WEBP',lossless=True)
brand=re.search(r'(<button[^>]*class="brand-button".*?</button>)',index,re.S)
assert brand
index=index[:brand.start()]+'<div class="brand-lockup">'+brand.group(1)+'<span class="brand-divider" aria-hidden="true"></span><img class="member-logo" src="assets/img/ct-group-member-v04.webp" alt="A member of CT Group Hi-Tech" width="900" height="98" decoding="async"></div>'+index[brand.end():]
index=index.replace('</head>','<link rel="stylesheet" href="assets/css/haykal-v04-revision.css"></head>',1)
css='''#globalHeader .nav-inner{max-width:none;gap:18px;padding:0 24px}#globalHeader .brand-lockup{display:flex;align-items:center;gap:18px;flex-shrink:0}#globalHeader .brand-divider{height:36px;width:1px;background:var(--site-soft-line,#d3dde2)}#globalHeader .member-logo{width:205px;height:auto;object-fit:contain}#globalHeader .main-nav{margin-left:auto}#globalHeader .nav-tools{margin-left:0;flex-shrink:0}@media(max-width:1250px){#globalHeader .nav-inner{gap:12px}#globalHeader .member-logo{width:160px}#globalHeader .brand-lockup{gap:12px}#globalHeader .nav-link{padding-left:9px;padding-right:9px}}@media(max-width:1100px){#globalHeader .member-logo{width:135px}#globalHeader .nav-inner{padding:0 16px}#globalHeader .nav-tools{margin-left:auto}#globalHeader .main-nav{margin-left:0}}@media(max-width:380px){#globalHeader .member-logo{width:115px}#globalHeader .brand-lockup{gap:8px}#globalHeader .brand-button{min-width:58px}#globalHeader .brand-button img{width:58px}#globalHeader .nav-inner{gap:8px;padding:0 10px}}'''
save(ROOT/'assets/css/haykal-v04-revision.css',css)

model_src=Path('C:/Users/ASUS/.t3/userdata/attachments/dd337a6c-a8bc-49e2-87ee-c984272aafad-41288040-9483-4a82-8787-0275d634e405-glb.glb')
model_hash=hashlib.sha256(model_src.read_bytes()).hexdigest();model_name='ct-fyran-firefighting-'+model_hash[:12]+'.glb'
shutil.copy2(model_src,ROOT/'assets/models'/model_name)
index=index.replace('</body>','<script data-encoding="base64" data-resource="assets/models/'+model_name+'" id="uav3dModel-ct-fyran-firefighting" type="application/octet-stream"></script></body>',1)
fire_path=ROOT/'pages/ct-fyran-firefighting.html';fire=rd(fire_path).replace('data-ps-model="ct-fyran-256"','data-ps-model="ct-fyran-firefighting"')
for old in ['shared-script-72c298408fef.js','shared-script-8fa5ef83d2b3.js']:
    new='firefighting-'+old
    save(ROOT/'assets/js'/new,rd(ROOT/'assets/js'/old).replace("'ct-fyran-256'","'ct-fyran-firefighting'"))
    fire=fire.replace(old,new)
save(fire_path,fire)
assert hashlib.sha256(index_path.read_bytes()).hexdigest()==initial_hash, 'Concurrent index edit: stop and merge.'
save(index_path,index)
# Keep readable copies consistent with changed delivery scripts.
for name in [data_path.name,responsive_path.name,catalogue_path.name,map_path.name,router_path.name,'firefighting-shared-script-72c298408fef.js','firefighting-shared-script-8fa5ef83d2b3.js']:
    save(ROOT/'source-code'/name,rd(ROOT/'assets/js'/name))
summary={'existing':len(original_ids),'added':len(data)-len(original_ids),'total':len(data),'duplicate_models_skipped':duplicates,'new_spec_matches':sum(x['status']=='matched' for x in records),'new_pending_specs':sum(x['status']=='pending' for x in records),'records':records,'image_source_hashes':image_hashes,'workbook':str(workbook_path),'model_sha256':model_hash,'model_bytes':model_src.stat().st_size,'glova_already_matches_v03':(ROOT/'pages/ct-glova.html').read_bytes()==(ROOT.parent/'refactor-v03/pages/ct-glova.html').read_bytes()}
(CHECK/'source-record.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print(j({k:v for k,v in summary.items() if k not in ['records','image_source_hashes','duplicate_models_skipped']}))
