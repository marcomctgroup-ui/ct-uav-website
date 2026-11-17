"""Batch 3 (small content fixes) for main website refactor v04. 5 November 2026.

Run once from the workspace root:
    python projects/main-website/refactor-v06/source-code/20261105-batch3-content-build.py

Haykal decided: do not change the CT Ency launcher position.
Changes:
1. Page titles: no "Demo Glass 3D v04" text; correct product and component names. New meta description.
2. Vietnamese: skip link, breadcrumb Home, component specification labels, categories, status values,
   two notices, Components intro and sort/search controls, one CT FRYAN sentence.
   All new Vietnamese text is PENDING CONFIRMATION by a Vietnamese reviewer.
3. Phone hero tabs (480 px or less): 2 x 2 grid, each name on one line.
4. A light loading placeholder while a page frame loads.
Changed CSS/JS files get new content-hash names. Before-copies: checks/before-batch3/.
"""
import hashlib, html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / 'pages'
MARK = 'data-content-batch="20261105-b3"'


def rd(p): return p.read_text(encoding='utf-8')
def wr(p, s): p.write_text(s, encoding='utf-8', newline='')


def once(s, old, new, label):
    n = s.count(old)
    if n != 1:
        sys.exit(f'STOP: {label}: expected 1 match, found {n}')
    return s.replace(old, new)


def attr(t): return html.escape(t, quote=True)


index_p = ROOT / 'index.html'
index = rd(index_p)
if MARK in index:
    sys.exit('STOP: Batch 3 is already applied.')

# ---- 2. Vietnamese on component pages -------------------------------------------
SPEC_VI = {
    'Category': 'Danh mục', 'Application': 'Ứng dụng', 'KV': 'KV', 'Power (W)': 'Công suất (W)',
    'Voltage': 'Điện áp', 'Dimensions (mm)': 'Kích thước (mm)', 'Weight (g)': 'Khối lượng (g)',
    'Configuration (Qty)': 'Cấu hình (số lượng)', 'Propeller': 'Cánh quạt', 'MTOW (kg)': 'MTOW (kg)',
    'Payload (kg)': 'Tải trọng (kg)', 'Flight Time (min)': 'Thời gian bay (phút)', 'ESC': 'ESC',
    'Battery': 'Pin', 'Battery Energy (Wh)': 'Năng lượng pin (Wh)', 'BMS (A)': 'BMS (A)',
    'Charger (W)': 'Bộ sạc (W)', 'Segment': 'Phân khúc', 'Status': 'Trạng thái',
}
STATUS_VI = {'Production': 'Sản xuất', 'R&D': 'R&D', 'Production / R&D': 'Sản xuất / R&D'}
NOTES = {
    '<p>Specifications pending confirmation. Contact CT UAV for details.</p>':
        ('Specifications pending confirmation. Contact CT UAV for details.',
         'Thông số kỹ thuật đang chờ xác nhận. Vui lòng liên hệ CT UAV để biết chi tiết.'),
    '<p>Image identity pending confirmation: the supplied image label differs from the supplied folder name.</p>':
        ('Image identity pending confirmation: the supplied image label differs from the supplied folder name.',
         'Nhận dạng hình ảnh đang chờ xác nhận: nhãn trên hình ảnh khác với tên thư mục được cung cấp.'),
}
comp_pages = sorted(PAGES.glob('component-*.html')) + [PAGES / 'uav-components.html']
for p in comp_pages:
    s = rd(p)
    s = once(s, '<a class="skip" href="#main">Skip to content</a>',
             '<a class="skip" data-en="Skip to content" data-vi="Chuyển đến nội dung" href="#main">Skip to content</a>', f'{p.name} skip')
    if p.name != 'uav-components.html':
        if '<h2>Specifications</h2>' in s:   # older detail pages already use data-vi="Thông số"
            s = once(s, '<h2>Specifications</h2>', '<h2 data-en="Specifications" data-vi="Thông số">Specifications</h2>', f'{p.name} spec h2')
        start = s.find('id="specifications"'); end = s.find('</section>', start)
        sec = s[start:end]

        def dt(m):
            key = html.unescape(m.group(1))
            if key not in SPEC_VI:
                sys.exit(f'STOP: {p.name}: no Vietnamese label for {key}')
            out = f'<dt data-en="{attr(key)}" data-vi="{attr(SPEC_VI[key])}">{m.group(1)}</dt><dd'
            val = html.unescape(m.group(2))
            if key == 'Category':
                out += f' data-category="{attr(val)}"'
            elif key == 'Status':
                out += f' data-en="{attr(val)}" data-vi="{attr(STATUS_VI[val])}"'
            return out + f'>{m.group(2)}</dd>'
        sec = re.sub(r'<dt>(.*?)</dt><dd>(.*?)</dd>', dt, sec)
        s = s[:start] + sec + s[end:]
        for old, (en, vi) in NOTES.items():
            if old in s:
                s = once(s, old, f'<p data-en="{attr(en)}" data-vi="{attr(vi)}">{en}</p>', f'{p.name} note')
    wr(p, s)

uc_p = PAGES / 'uav-components.html'
uc = rd(uc_p)
uc = once(uc, '<a href="../../20261103-main-website-r08-3d-ency-centre-right-v02.html">Home</a>',
          '<a data-en="Home" data-vi="Trang chủ" href="../../20261103-main-website-r08-3d-ency-centre-right-v02.html">Home</a>', 'crumb home')
uc = once(uc, 'data-vi="Khám phá động cơ, cánh quạt, cell hình trụ và camera gimbal."',
          'data-vi="Khám phá động cơ, cánh quạt, ESC, bộ điều khiển bay, định vị, mô-đun nguồn và truyền dẫn."', 'components lead')
uc = once(uc, '<span class="sr">Sort</span>', '<span class="sr" data-en="Sort" data-vi="Sắp xếp">Sort</span>', 'sort label')
uc = once(uc, '<option value="source">Category order</option><option value="az">Name: A–Z</option><option value="za">Name: Z–A</option>',
          '<option data-en="Category order" data-vi="Theo danh mục" value="source">Category order</option>'
          '<option data-en="Name: A–Z" data-vi="Tên: A–Z" value="az">Name: A–Z</option>'
          '<option data-en="Name: Z–A" data-vi="Tên: Z–A" value="za">Name: Z–A</option>', 'sort options')
wr(uc_p, uc)

cat_js = ROOT / 'assets/js/shared-script-b4c6b5373db6.js'
c = rd(cat_js)
c = once(c, "const viCats={'Fixed-Wing Motor':'Động cơ cánh cố định','Propeller':'Cánh quạt','Cylindrical':'Cell hình trụ','Gimbal Camera':'Camera gimbal'};",
         "const viCats={'Fixed-Wing Motor':'Động cơ cánh cố định','Multirotor Motor':'Động cơ đa cánh quạt','Propeller':'Cánh quạt','ESC':'ESC',"
         "'Flight Controller':'Bộ điều khiển bay','GNSS & Positioning':'GNSS & định vị','Power Modules & PDB':'Mô-đun nguồn & PDB',"
         "'Transmission & Telemetry':'Truyền dẫn & đo từ xa','Cylindrical':'Cell hình trụ','Gimbal Camera':'Camera gimbal'};", 'viCats')
c = once(c, "document.querySelectorAll('[data-en]').forEach(e=>e.textContent=e.dataset[lang]);",
         "document.querySelectorAll('[data-en]').forEach(e=>e.textContent=e.dataset[lang]);{const q=$('#search');if(q)q.placeholder=lang==='vi'?'Tìm theo tên mẫu':'Search by model name';}",
         'search placeholder')
wr(cat_js, c)

# ---- 2b. Main dictionary: one missing sentence ------------------------------------
m = re.search(r'(<script data-i18n-skip="" id="i18nVi" type="application/json">)(.*?)(</script>)', index, re.S)
d = json.loads(m.group(2))
key = 'Ask CT UAV about CT FRYAN (Firefighting) and firefighting applications.'
if key in d:
    sys.exit('STOP: dictionary already has the FRYAN sentence')
body = m.group(2).rstrip()
if not body.endswith('}'):
    sys.exit('STOP: dictionary end not found')
body = body[:-1] + ',' + json.dumps(key, ensure_ascii=False) + ':' + json.dumps('Hỏi CT UAV về CT FRYAN (Firefighting) và các ứng dụng phòng cháy chữa cháy.', ensure_ascii=False) + '}'
json.loads(body)
index = index[:m.start(2)] + body + index[m.end(2):]

# ---- 1. Titles and meta -----------------------------------------------------------
router_p = ROOT / 'assets/js/shared-script-bac24ddbcb61.js'
r = rd(router_p)
routes = json.loads(re.search(r'const routes=(\[.*?\]);', r).group(1))
tm = re.search(r'const titles=(\{.*?\});const pageLang', r)
old_titles = json.loads(tm.group(1))
titles = {}
for route in routes:
    if route == 'home':
        titles[route] = 'CT UAV | Member of CT Group'; continue
    page = rd(PAGES / f'{route}.html')
    pt = re.search(r'<title>(.*?)</title>', page, re.S).group(1).strip()
    if route.startswith('component-') or route in ('ct-glova', 'uav-components'):
        titles[route] = html.unescape(pt)
    elif route == 'ct-fyran-firefighting':
        titles[route] = 'CT FRYAN (Firefighting) | CT UAV'
    elif route == 'about':
        titles[route] = 'About CT UAV'
    elif route in old_titles:
        t = old_titles[route]
        for tail in [' | CT UAV Demo Glass 3D v04', ' | CT UAV Review Demo', ' | CT UAV Product Line']:
            t = t.replace(tail, ' | CT UAV')
        titles[route] = t
    else:
        sys.exit(f'STOP: no title source for {route}')
for t in titles.values():
    if 'Demo' in t or 'Glass' in t or t == t.lower():
        sys.exit(f'STOP: bad title {t}')
r = r[:tm.start(1)] + json.dumps(titles, ensure_ascii=False, separators=(',', ':')) + r[tm.end(1):]

# Page documents carry the same title (used when a page is opened alone).
for route, t in titles.items():
    if route == 'home':
        continue
    p = PAGES / f'{route}.html'
    s = rd(p)
    s2 = re.sub(r'<title>.*?</title>', '<title>' + html.escape(t, quote=False) + '</title>', s, count=1, flags=re.S)
    if s2 != s:
        wr(p, s2)
hero_p = PAGES / 'hero.html'
h = rd(hero_p)
h = re.sub(r'<title>.*?</title>', '<title>CT UAV | Home hero</title>', h, count=1, flags=re.S)

index = once(index, '<title>CT UAV - Main Website Demo Glass 3D v04</title>', '<title>CT UAV | Member of CT Group</title>', 'index title')
index = re.sub(r'<meta content="[^"]*" name="description"/>',
               '<meta content="CT UAV, a member of CT Group, makes UAV solutions for the Low Altitude Economy (LAE). '
               'See the UAV product lines, models, components, news and sales contacts." name="description"/>', index, count=1)
index = once(index, '<html ', f'<html {MARK} ', 'batch marker')

# ---- 4. Loading placeholder --------------------------------------------------------
index = once(index, '</template>\n', '</template>\n<div class="page-loading" hidden="" id="pageLoading" role="status">'
             '<span data-i18n-en="Loading page…" data-i18n-vi="Đang tải trang…">Loading page…</span></div>\n', 'loading element')
r = once(r, "const frames={};", "const frames={};const loading=document.getElementById('pageLoading');const ready=new Set();", 'router loading vars')
r = once(r, "function attachFrame(name,frame){frame.addEventListener('load',()=>{",
         "function attachFrame(name,frame){frame.addEventListener('load',()=>{ready.add(name);if(name===route&&loading)loading.hidden=true;", 'router load hide')
r = once(r, "Object.entries(frames).forEach(([name,frame])=>{frame.hidden=name!==route;});",
         "Object.entries(frames).forEach(([name,frame])=>{frame.hidden=name!==route;});if(loading)loading.hidden=route==='home'||ready.has(route);", 'router route show')
wr(router_p, r)

shell_css = ROOT / 'assets/css/shared-style-43ad517d64f3.css'
sc = rd(shell_css).rstrip() + (
    '\n#content>.page-loading{position:absolute;top:var(--nav-height);left:0;right:0;bottom:0;z-index:2;display:grid;place-items:center;'
    'background:var(--glass-amb-base,#f5f5f5);font:600 15px/1.4 Montserrat,sans-serif}'
    '#content>.page-loading[hidden]{display:none}'
    '.page-loading span::after{content:"";display:block;width:120px;height:3px;margin:14px auto 0;border-radius:3px;opacity:.45;'
    'background:linear-gradient(90deg,transparent,currentColor,transparent);background-size:200% 100%;animation:ct-page-load 1.6s ease-in-out infinite}'
    '@keyframes ct-page-load{from{background-position:100% 0}to{background-position:-100% 0}}'
    '@media (prefers-reduced-motion:reduce){.page-loading span::after{animation:none}}\n')
wr(shell_css, sc)

# ---- 3. Phone hero tabs ------------------------------------------------------------
hero_css = ROOT / 'assets/css/shared-style-69634d9b9a53.css'
hc = rd(hero_css).rstrip() + (
    '\n@media (max-width:480px){.slide-nav{grid-template-columns:repeat(2,minmax(0,1fr));row-gap:4px}'
    '.slide-choice{min-height:44px;white-space:nowrap}.slide-label{overflow:hidden;text-overflow:ellipsis}}\n')
wr(hero_css, hc)
wr(hero_p, h)
wr(index_p, index)

# ---- Content-hash names for changed CSS/JS -----------------------------------------
renamed = {}
for p in [cat_js, router_p, shell_css, hero_css]:
    digest = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    new = p.with_name(p.stem.rsplit('-', 1)[0] + f'-{digest}{p.suffix}')
    p.rename(new); renamed[p.name] = new.name
for doc in [index_p] + sorted(PAGES.glob('*.html')):
    s = rd(doc); t = s
    for o, n in renamed.items():
        t = t.replace(o, n)
    if t != s:
        wr(doc, t)
for o, n in renamed.items():
    print(o, '->', n)
print('titles', len(titles))
print('Batch 3 build complete. Run the headers generator next.')
