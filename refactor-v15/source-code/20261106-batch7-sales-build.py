"""Batch 7 (sales feedback) build for refactor v07 - 6 November 2026.

Higher-up feedback, with Haykal's decisions:
1. Product line pages: show a product image in each model row and an "Add to Cart" button next to each model.
2. Product detail pages: "Add to Cart" in the sticky product bar, in the hero and beside Contact Sales;
   a floating cart button; a cart window with an inquiry form (checks fields only; sends nothing - Batch 5B).
3. Footer social buttons: brand colours, colour change on hover.
4. Components: product name first, model code second (names from the workbook category; PENDING CONFIRMATION).

Run once on a fresh copy of v06:  python projects/main-website/refactor-v07/source-code/20261106-batch7-sales-build.py
It stops if the marker (data-cart-add in pages/line-09.html) already exists.
Pillow is in the user site-packages, so do not run it with python -I.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[2]
SRC_IMAGES = WORKSPACE / 'sources' / 'assets' / 'uav-images'
PAGES = ROOT / 'pages'
BEFORE = ROOT / 'checks' / '20261106-batch7' / 'before'
RECORD = ROOT / 'checks' / '20261106-batch7' / 'build-record.json'
record: dict = {'changed': [], 'created': [], 'moved': [], 'images': {}, 'pending_images': []}

marker = (PAGES / 'line-09.html').read_text(encoding='utf-8')
if 'data-cart-add' in marker:
    raise SystemExit('Batch 7 already applied: data-cart-add is in pages/line-09.html')


def sha(data: bytes, n: int = 12) -> str:
    return hashlib.sha256(data).hexdigest()[:n]


def backup(path: Path) -> None:
    rel = path.relative_to(ROOT)
    target = BEFORE / str(rel).replace('\\', '__').replace('/', '__')
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def write_text(path: Path, text: str) -> None:
    backup(path)
    path.write_text(text, encoding='utf-8', newline='')
    record['changed'].append(str(path.relative_to(ROOT)).replace('\\', '/'))


def replace_once(text: str, old: str, new: str, where: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{where}: expected 1 match, found {count}: {old[:90]!r}')
    return text.replace(old, new)


def minify_js(code: str) -> str:
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    lines = [line.strip() for line in code.splitlines()]
    return '\n'.join(line for line in lines if line) + '\n'


def minify_css(code: str) -> str:
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    code = re.sub(r'\s+', ' ', code)
    code = re.sub(r'\s*([{};,>])\s*', r'\1', code)
    code = re.sub(r':\s+', ':', code)
    code = code.replace(';}', '}')
    return code.strip() + '\n'


def deliver(readable: str, folder: str, stem: str, ext: str, minify) -> str:
    data = minify((ROOT / 'source-code' / readable).read_text(encoding='utf-8')).encode('utf-8')
    name = f'{stem}-{sha(data)}.{ext}'
    (ROOT / 'assets' / folder / name).write_bytes(data)
    record['created'].append(f'assets/{folder}/{name}')
    return name


# 1. Delivery files with content-hash names -------------------------------------------------
CART_JS = deliver('inquiry-cart-v01.js', 'js', 'inquiry-cart', 'js', minify_js)
CART_CSS = deliver('inquiry-cart-v01.css', 'css', 'inquiry-cart', 'css', minify_css)
SOCIAL_CSS = deliver('footer-social-v01.css', 'css', 'footer-social', 'css', minify_css)
CART_LINK = f'<link href="../assets/css/{CART_CSS}" rel="stylesheet"/>'
CART_SCRIPT = f'<script src="../assets/js/{CART_JS}"></script>'
SOCIAL_LINK_PAGE = f'<link href="../assets/css/{SOCIAL_CSS}" rel="stylesheet"/>'
SOCIAL_LINK_SHELL = f'<link href="assets/css/{SOCIAL_CSS}" rel="stylesheet"/>'

CART_ICON = ('<svg class="cart-icon" aria-hidden="true" viewBox="0 0 24 24" focusable="false"><path d="M3 4h2.2l2.3 10.2a1.6 1.6 0 0 0 1.6 1.3h8.6a1.6 1.6 0 0 0 1.6-1.2L21 8H6.4" '
             'fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9.5" cy="19.6" r="1.5" fill="currentColor"/>'
             '<circle cx="17.3" cy="19.6" r="1.5" fill="currentColor"/></svg>')


def cart_button(cart_id: str, name: str, extra: str = '') -> str:
    cls = 'cart-add' + (f' {extra}' if extra else '')
    safe = name.replace('&', '&amp;').replace('"', '&quot;')
    return (f'<button class="{cls}" data-cart-add="" data-cart-id="{cart_id}" data-cart-name="{safe}" data-i18n-skip="" type="button">'
            f'{CART_ICON}<span data-cart-label="">Add to Cart</span></button>')


def add_head_tail(text: str, where: str, head: list[str], tail: list[str]) -> str:
    if head:
        text = replace_once(text, '</head>', ''.join(head) + '</head>', where)
    if tail:
        text = replace_once(text, '</body>', ''.join(tail) + '</body>', where)
    return text


# 2. Model images for product line pages ----------------------------------------------------
IMAGE_SOURCES = {
    'CT SKYSILK': 'passenger/CT SKYSILK.jpg',
    'CT-CAMEL 256': 'cargo/CT-CAMEL 256.png', 'CT-CAMEL 44': 'cargo/CT-CAMEL 44.png', 'CT-CAMEL 27': 'cargo/CT-CAMEL 27.png',
    'CT-PEGAS 230': 'rescue-emergency/CT-PEGAS 230.jpg',
    'CT-FYRAN 256': 'firefighting/CT-FYRAN 256.png',
    'DECARB 22': 'cabon-credit/DECARB 22.png', 'DECARB 54': 'cabon-credit/DECARB 54.png',
    'CT-GLOVA': 'drone-light/CT-GLOVA.jpg',
    'CT-FRONA 44': 'border-surveillance/CT-FRONA 44.png', 'CT-FRONA 27': 'border-surveillance/CT-FRONA 27.png',
    'CT-CROVA 254': 'agricultural/CT-CROVA 254.jpg', 'CT-CROVA 124': 'agricultural/CT-CROVA 124.jpg', 'CT-CROVA 256': 'agricultural/CT-CROVA 256.jpg',
    'CT-FOLRA 44': 'forestry/CT-FOLRA 44.png', 'CT-FOLRA 27': 'forestry/CT-FOLRA 27.png',
    'CT-MARVO 35': 'aquaculture/CT-MARVO 35.png', 'CT-MARVO 44': 'aquaculture/CT-MARVO 44.png', 'CT-MARVO 27': 'aquaculture/CT-MARVO 27.png',
    'CT-PIXRA 5': 'digital-transformation/CT-PIXRA 5.jpg', 'CT-PIXRA 44': 'digital-transformation/CT-PIXRA 44.png', 'CT-PIXRA 27': 'digital-transformation/CT-PIXRA 27.png',
    'CT-EDIXO 5': 'electric-power/CT-EDIXO 5.jpg', 'CT-EDIXO 230': 'electric-power/CT-EDIXO 230.jpg',
    'CT-BIMRA 5': 'construction-inspection/CT-BIMRA 5.jpg',
    'CT-ECOVA 5': 'renewable-energy/CT-ECOVA 5.jpg', 'CT-ECOVA 27': 'renewable-energy/CT-ECOVA 27.png',
}
# No matching approved white-background image: CT-FRYAN (Firefighting), CT-FYRAN 5,
# CT-GARON 5 (the security folder has "CT-NEXVIS 5", a different name) and "BIM solution".


def slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def make_thumbs(name: str) -> tuple[str, str]:
    src = SRC_IMAGES / IMAGE_SOURCES[name]
    raw = src.read_bytes()
    image = Image.open(src).convert('RGBA')
    white = Image.new('RGBA', image.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, image).convert('RGB')
    diff = ImageChops.difference(flat, Image.new('RGB', flat.size, (255, 255, 255))).convert('L').point(lambda v: 255 if v > 18 else 0)
    box = diff.getbbox() or (0, 0, *flat.size)
    left, top, right, bottom = box
    w, h = right - left, bottom - top
    pad = int(max(w, h) * 0.08)
    # Fit the UAV into a 16:9 white canvas so that all rows have a similar visual size.
    cw = max(w + 2 * pad, int((h + 2 * pad) * 16 / 9))
    ch = int(cw * 9 / 16)
    canvas = Image.new('RGB', (cw, ch), (255, 255, 255))
    canvas.paste(flat.crop(box), ((cw - w) // 2, (ch - h) // 2))
    token = sha(raw, 10)
    base = f'uav-option-{slug(name)}-{token}'
    for width in (480, 800):
        out = canvas.resize((width, width * 9 // 16), Image.LANCZOS)
        out.save(ROOT / 'assets' / 'img' / f'{base}-{width}.webp', 'WEBP', quality=84, method=6)
        record['created'].append(f'assets/img/{base}-{width}.webp')
    record['images'][name] = {'source': f'sources/assets/uav-images/{IMAGE_SOURCES[name]}', 'source_sha256': hashlib.sha256(raw).hexdigest(),
                              'crop_box': list(box), 'files': [f'{base}-480.webp', f'{base}-800.webp']}
    return f'../assets/img/{base}-480.webp', f'../assets/img/{base}-800.webp'


LOGO = '../assets/img/ct-uav-d4035ad7bb.svg'
row_re = re.compile(r'<article class="pl-model"><p class="pl-model__number">(OPTION \d\d)</p><h3>([^<]+)</h3>(<button [^>]*>.*?</button>)</article>')
for page in sorted(PAGES.glob('line-*.html')):
    text = page.read_text(encoding='utf-8')
    rows = row_re.findall(text)
    if not rows:
        raise SystemExit(f'{page.name}: no model rows')

    def rebuild(match: re.Match) -> str:
        number, name, button = match.groups()
        plain = name.replace('&amp;', '&')
        if plain in IMAGE_SOURCES:
            small, large = make_thumbs(plain)
            media = (f'<figure class="pl-model__media"><img alt="{name}" decoding="async" height="270" loading="lazy" '
                     f'sizes="(max-width: 640px) 92vw, (max-width: 1100px) 200px, 240px" src="{small}" '
                     f'srcset="{small} 480w, {large} 800w" width="480"/></figure>')
        else:
            record['pending_images'].append(plain)
            media = (f'<figure aria-hidden="true" class="pl-model__media pl-model__media--pending">'
                     f'<img alt="" decoding="async" height="66" loading="lazy" src="{LOGO}" width="112"/></figure>')
        route = re.search(r'data-route="([^"]+)"', button)
        cart_id = f'uav:{route.group(1)}' if route else f'uav:{slug(plain)}'
        return (f'<article class="pl-model">{media}<div class="pl-model__body"><p class="pl-model__number">{number}</p><h3>{name}</h3></div>'
                f'<div class="pl-model__actions">{cart_button(cart_id, plain)}{button}</div></article>')

    text = row_re.sub(rebuild, text)
    text = add_head_tail(text, page.name, [CART_LINK, SOCIAL_LINK_PAGE], [CART_SCRIPT])
    write_text(page, text)

# 3. Product detail pages ----------------------------------------------------------------------
CONTACT_BUTTON = '<button class="button button-primary" data-contact="" type="button">Contact Sales <span aria-hidden="true">↗</span></button>'
PRODUCT_PAGES = {
    'ct-camel-256.html': 'ct-camel-256', 'ct-crova-254.html': 'ct-crova-254', 'ct-frona-44.html': 'ct-frona-44',
    'ct-fyran-256.html': 'ct-fyran-256', 'ct-fyran-firefighting.html': 'ct-fyran-firefighting', 'ct-glova.html': 'ct-glova',
    'ct-pegas-230.html': 'ct-pegas-230', 'ct-skysilk.html': 'ct-skysilk', 'decarb22.html': 'decarb22', 'decarb54.html': 'decarb54',
}
for file, route in PRODUCT_PAGES.items():
    page = PAGES / file
    text = page.read_text(encoding='utf-8')
    name = re.search(r'<h1 id="product-title">([^<]+)</h1>', text).group(1)
    plain = name.replace('&amp;', '&')
    cart_id = f'uav:{route}'
    text = replace_once(text, '</nav>\n</div>\n</header>',
                        f'</nav>\n<div class="product-bar__cart">{cart_button(cart_id, plain, "cart-add--bar")}</div>\n</div>\n</header>', file)
    if '<div class="hero-actions">' in text:
        text = re.sub(r'(<div class="hero-actions">)(.*?)(</div>)', lambda m: m.group(1) + m.group(2) + cart_button(cart_id, plain) + m.group(3), text, count=1, flags=re.S)
    else:
        text = replace_once(text, f'<h1 id="product-title">{name}</h1>\n</div>\n</div>\n</section>',
                            f'<h1 id="product-title">{name}</h1>\n</div>\n<div class="hero-actions">{cart_button(cart_id, plain)}</div>\n</div>\n</section>', file)
    text = replace_once(text, CONTACT_BUTTON, f'<div class="contact-actions">{cart_button(cart_id, plain)}{CONTACT_BUTTON}</div>', file)
    text = add_head_tail(text, file, [CART_LINK, SOCIAL_LINK_PAGE], [CART_SCRIPT])
    write_text(page, text)

# 4. Components: product names first, model codes second -----------------------------------------
NAMES = {
    'ESC': ('Electronic Speed Controller', 'Bộ điều tốc điện tử (ESC)'),
    'Propeller': ('Propeller', 'Cánh quạt'),
    'Multirotor Motor': ('Multirotor Motor', 'Động cơ đa cánh quạt'),
    'Fixed-Wing Motor': ('Fixed-Wing Motor', 'Động cơ cánh cố định'),
    'Cylindrical': ('Cylindrical Battery Cell', 'Cell pin hình trụ'),
    'Intelligent Battery': ('Intelligent Battery', 'Pin thông minh'),
    'Semi-Solid Cell': ('Semi-Solid Battery Cell', 'Cell pin bán rắn'),
    'Ground Controller': ('Ground Controller', 'Bộ điều khiển mặt đất'),
    'EO-IR': ('EO-IR Camera', 'Camera EO-IR'),
    'Gimbal Camera': ('Gimbal Camera', 'Camera gimbal'),
}
record['component_names'] = {k: {'en': v[0], 'vi': v[1], 'status': 'PENDING CONFIRMATION (from workbook category)'} for k, v in NAMES.items()}

old_js_name = 'shared-script-9be0de6586bc.js'
old_js = (ROOT / 'assets' / 'js' / old_js_name).read_text(encoding='utf-8')
names_js = 'const productNames=' + json.dumps({k: list(v) for k, v in NAMES.items()}, ensure_ascii=False, separators=(',', ':')) + \
    ";const pname=p=>{const n=productNames[p.category];return n?tx(n[0],n[1]):p.category};const pnameEn=p=>(productNames[p.category]||[p.category])[0];"
js = replace_once(old_js, '"Payload Delivery":"Thiết bị thả hàng"};', '"Payload Delivery":"Thiết bị thả hàng"};' + names_js, 'catalogue js names')
js = replace_once(js, '`${p.name} ${p.category} ${viCats[p.category]}`',
                  "`${p.name} ${p.category} ${viCats[p.category]} ${(productNames[p.category]||[]).join(' ')}`", 'catalogue js search')
js = replace_once(js, 'aria-label="${esc(p.name)} — ${p.detail',
                  'aria-label="${esc(pname(p))} ${esc(p.name)} — ${p.detail', 'catalogue js aria')
js = replace_once(js, '<h2 class="component-card-name">${esc(p.name)}</h2></a></article>',
                  '<h2 class="component-card-name"><span class="component-card-product">${esc(pname(p))}</span><span class="component-card-code">${esc(p.name)}</span></h2></a>'
                  '<div class="component-card-actions"><button class="cart-add" data-cart-add="" data-cart-id="component:${p.id}" data-cart-name="${esc(pnameEn(p)+\' \'+p.name)}" data-i18n-skip="" type="button">'
                  + CART_ICON.replace('`', '') +
                  '<span data-cart-label="">${tx(\'Add to Cart\',\'Thêm vào giỏ\')}</span></button></div></article>', 'catalogue js card')
new_js_bytes = js.encode('utf-8')
new_js_name = f'shared-script-{sha(new_js_bytes)}.js'
(ROOT / 'assets' / 'js' / new_js_name).write_bytes(new_js_bytes)
(ROOT / 'source-code' / new_js_name).write_bytes(new_js_bytes)
record['created'] += [f'assets/js/{new_js_name}', f'source-code/{new_js_name}']
moved = BEFORE / 'assets__js__' / old_js_name
moved.parent.mkdir(parents=True, exist_ok=True)
shutil.move(str(ROOT / 'assets' / 'js' / old_js_name), moved)
record['moved'].append({'from': f'assets/js/{old_js_name}', 'to': str(moved.relative_to(ROOT)).replace('\\', '/')})

for page in sorted(PAGES.glob('component-*.html')) + [PAGES / 'uav-components.html']:
    text = page.read_text(encoding='utf-8')
    text = replace_once(text, f'src="../assets/js/{old_js_name}"', f'src="../assets/js/{new_js_name}"', page.name)
    if page.name != 'uav-components.html':
        m = re.search(r'<p class="eyebrow" data-category="([^"]+)">[^<]*</p>(\s*)<h1>([^<]+)</h1>(\s*)<p class="lead" data-category="\1">[^<]*</p>', text)
        if not m:
            raise SystemExit(f'{page.name}: component title block not found')
        category, gap1, code, gap2 = m.group(1), m.group(2), m.group(3), m.group(4)
        en, vi = NAMES[category]
        text = text.replace(m.group(0),
                            f'<p class="eyebrow" data-en="UAV component" data-vi="Linh kiện UAV">UAV component</p>{gap1}'
                            f'<h1 data-en="{en}" data-vi="{vi}">{en}</h1>{gap2}<p class="lead component-code">{code}</p>')
        component_id = page.stem.replace('component-', '', 1)
        code_plain = code.replace('&amp;', '&')
        text = replace_once(text, '<a class="button hs-button hs-button--fill" data-en="Enquire about this component ↗"',
                            cart_button(f'component:{component_id}', f'{en} {code_plain}') + '<a class="button hs-button hs-button--fill" data-en="Enquire about this component ↗"', page.name)
    text = add_head_tail(text, page.name, [CART_LINK], [CART_SCRIPT])
    write_text(page, text)

# 5. Footer social CSS on the other pages with a footer, and in every entry shell -------------
for page in sorted(PAGES.glob('*.html')):
    text = page.read_text(encoding='utf-8')
    if 'site-footer__social' in text and SOCIAL_CSS not in text:
        write_text(page, add_head_tail(text, page.name, [SOCIAL_LINK_PAGE], []))
SHELL_ANCHOR = '<link href="assets/css/shared-style-63437eb5a8d1.css" rel="stylesheet"/>'
shells = [ROOT / 'index.html'] + sorted(p for p in ROOT.glob('*/**/index.html')
                                        if p.relative_to(ROOT).parts[0] not in ('assets', 'pages', 'checks', 'source-code', 'source-inputs'))
for shell in shells:
    text = shell.read_text(encoding='utf-8')
    write_text(shell, replace_once(text, SHELL_ANCHOR, SHELL_ANCHOR + SOCIAL_LINK_SHELL, str(shell.relative_to(ROOT))))
record['shells'] = len(shells)

RECORD.parent.mkdir(parents=True, exist_ok=True)
RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'cart_js': CART_JS, 'cart_css': CART_CSS, 'social_css': SOCIAL_CSS, 'catalogue_js': new_js_name,
                  'changed': len(record['changed']), 'images': len(record['images']), 'pending_images': record['pending_images'],
                  'shells': len(shells)}, ensure_ascii=False, indent=1))
