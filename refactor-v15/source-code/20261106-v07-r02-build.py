"""Refactor v07 r02 build, 6 November 2026. Run once (marker stops a second run).

Haykal's requests (6 November):
1. TikTok button purple            -> edit of source-code/footer-social-v01.css (delivered by batch7-redeliver).
2. Firefighting line page: CT-FYRAN 256 card uses the Navbar CT-FYRAN image; the earlier card
   image moves to the CT-FRYAN (Firefighting) card.
3. Add to Cart in the glass style   -> edit of source-code/inquiry-cart-v01.css (batch7-redeliver).
4. ISO 9001:2015 section on Home and on About (About: first section after the hero), from the two
   supplied photos (certificate and ceremony). Facts and scope text are copied from the certificate.
5. Product line card images from Haykal's zip: CT-CAMEL 256/44/27, CT-CROVA 124/256,
   CT-GARON 54 (row renamed from CT-GARON 5, Haykal's decision), CT-GLOVA 4 (row renamed from
   CT-GLOVA, Haykal's decision).

Usage: python 20261106-v07-r02-build.py <zip image folder> <folder with 2.jpg and 3.jpg>
Afterwards: 20261106-batch7-redeliver.py, then 20261105-batch2-headers-build.py.
Before-copies: checks/20261106-batch7-r02/before/. Record: checks/20261106-batch7-r02/build-record.json.
"""
from __future__ import annotations

import hashlib, json, re, shutil, sys
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ZIP_DIR = Path(sys.argv[1])
PHOTO_DIR = Path(sys.argv[2])
CHECK = ROOT / 'checks' / '20261106-batch7-r02'
BEFORE = CHECK / 'before'
INPUTS = ROOT / 'source-inputs' / '20261106-v07-r02'
MARK = 'data-v07-revision="20261106-r02"'
record = {'created': [], 'changed': [], 'images': {}, 'renamed_rows': {}, 'dictionary_added': 0}

ENTRY_SKIP = ('assets', 'pages', 'checks', 'source-code', 'source-inputs')
SHELLS = [ROOT / 'index.html'] + sorted(p for p in ROOT.glob('*/**/index.html') if p.relative_to(ROOT).parts[0] not in ENTRY_SKIP)


def sha(data: bytes, n: int = 12) -> str:
    return hashlib.sha256(data).hexdigest()[:n]


def backup(path: Path) -> None:
    rel = path.relative_to(ROOT).as_posix().replace('/', '__')
    dest = BEFORE / rel
    if not dest.exists():
        BEFORE.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def read(path: Path) -> str:
    return path.read_bytes().decode('utf-8')


def write(path: Path, text: str) -> None:
    backup(path)
    path.write_bytes(text.encode('utf-8'))
    record['changed'].append(path.relative_to(ROOT).as_posix())


def once(text: str, old: str, new: str, where: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'STOP {where}: found {n}, expected 1: {old[:80]}')
    return text.replace(old, new)


def slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def card_thumbs(name: str, src: Path, source_label: str) -> tuple[str, str]:
    """Same method as 20261106-batch7-sales-build.py make_thumbs: crop to the UAV, 16:9 white canvas."""
    raw = src.read_bytes()
    image = Image.open(src).convert('RGBA')
    white = Image.new('RGBA', image.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, image).convert('RGB')
    diff = ImageChops.difference(flat, Image.new('RGB', flat.size, (255, 255, 255))).convert('L').point(lambda v: 255 if v > 18 else 0)
    box = diff.getbbox() or (0, 0, *flat.size)
    left, top, right, bottom = box
    w, h = right - left, bottom - top
    pad = int(max(w, h) * 0.08)
    cw = max(w + 2 * pad, int((h + 2 * pad) * 16 / 9))
    ch = int(cw * 9 / 16)
    canvas = Image.new('RGB', (cw, ch), (255, 255, 255))
    canvas.paste(flat.crop(box), ((cw - w) // 2, (ch - h) // 2))
    base = f'uav-option-{slug(name)}-{sha(raw, 10)}'
    for width in (480, 800):
        out = canvas.resize((width, width * 9 // 16), Image.LANCZOS)
        out.save(ROOT / 'assets' / 'img' / f'{base}-{width}.webp', 'WEBP', quality=84, method=6)
        record['created'].append(f'assets/img/{base}-{width}.webp')
    record['images'][name] = {'source': source_label, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                              'source_size': list(image.size), 'crop_box': list(box),
                              'files': [f'{base}-480.webp', f'{base}-800.webp']}
    return f'../assets/img/{base}-480.webp', f'../assets/img/{base}-800.webp'


def card_media(alt: str, small: str, large: str) -> str:
    return (f'<figure class="pl-model__media"><img alt="{alt}" decoding="async" height="270" loading="lazy" '
            f'sizes="(max-width: 640px) 92vw, (max-width: 1100px) 200px, 240px" src="{small}" '
            f'srcset="{small} 480w, {large} 800w" width="480"/></figure>')


def rows(text: str):
    return list(re.finditer(r'<article class="pl-model">.*?</article>', text, re.S))


def edit_row(text: str, page: str, h3: str, fn) -> str:
    found = [m for m in rows(text) if f'<h3>{h3}</h3>' in m.group(0)]
    if len(found) != 1:
        raise SystemExit(f'STOP {page}: row {h3} found {len(found)}')
    m = found[0]
    return text[:m.start()] + fn(m.group(0)) + text[m.end():]


def set_media(row: str, media: str) -> str:
    return re.sub(r'<figure[^>]*class="pl-model__media[^"]*"[^>]*>.*?</figure>', lambda _: media, row, count=1, flags=re.S)


def rename_row(row: str, old: str, new: str, cart_id: str | None) -> str:
    row = once(row, f'<h3>{old}</h3>', f'<h3>{new}</h3>', f'h3 {old}')
    row = once(row, f'data-cart-name="{old}"', f'data-cart-name="{new}"', f'cart name {old}')
    if cart_id:
        row = re.sub(r'data-cart-id="[^"]+"', f'data-cart-id="{cart_id}"', row, count=1)
    row = row.replace(f'data-planned="{old}"', f'data-planned="{new}"')
    return row


# ---------------------------------------------------------------- 0. guard and inputs
index_text = read(ROOT / 'index.html')
if MARK in index_text:
    raise SystemExit('STOP: r02 already applied')
INPUTS.mkdir(parents=True, exist_ok=True)
for f in sorted(ZIP_DIR.glob('*.png')):
    shutil.copy2(f, INPUTS / f.name)
shutil.copy2(PHOTO_DIR / '2.jpg', INPUTS / 'iso-9001-ceremony-supplied.jpg')
shutil.copy2(PHOTO_DIR / '3.jpg', INPUTS / 'iso-9001-certificate-supplied.jpg')

# ---------------------------------------------------------------- 1. line page cards
ZIP_LABEL = "Haykal's zip 'ct uav product line card images.zip' (6 Nov 2026): "
updates = {
    'line-02.html': [('CT-CAMEL 256', 'CT-CAMEL 256.png', None), ('CT-CAMEL 44', 'CT-CAMEL 44.png', None), ('CT-CAMEL 27', 'CT-CAMEL 27.png', None)],
    'line-09.html': [('CT-CROVA 124', 'CT-CROVA 124.png', None), ('CT-CROVA 256', 'CT-CROVA 256.png', None)],
    'line-07.html': [('CT-GARON 5', 'CT-GARON 54.png', ('CT-GARON 54', 'uav:ct-garon-54'))],
    'line-06.html': [('CT-GLOVA', 'CT-GLOVA 4.png', ('CT-GLOVA 4', None))],
}
for page, items in updates.items():
    path = ROOT / 'pages' / page
    text = read(path)
    for h3, file, rename in items:
        name = rename[0] if rename else h3
        small, large = card_thumbs(name, ZIP_DIR / file, ZIP_LABEL + file)

        def fix(row: str, name=name, small=small, large=large, h3=h3, rename=rename) -> str:
            row = set_media(row, card_media(name, small, large))
            if rename:
                row = rename_row(row, h3, rename[0], rename[1])
                record['renamed_rows'][h3] = rename[0]
            return row
        text = edit_row(text, page, h3, fix)
    write(path, text)

# Firefighting line page: CT-FYRAN 256 gets the Navbar image; CT-FRYAN gets the earlier CT-FYRAN 256 card image.
path = ROOT / 'pages' / 'line-04.html'
text = read(path)
old_small = '../assets/img/uav-option-ct-fyran-256-a707070726-480.webp'
old_large = '../assets/img/uav-option-ct-fyran-256-a707070726-800.webp'
nav_src = ROOT / 'assets' / 'img' / 'fyran-navbar-uav-00204-v03.webp'
small, large = card_thumbs('CT-FYRAN 256', nav_src, 'Navbar image assets/img/fyran-navbar-uav-00204-v03.webp (transparent cutout of UAV_00204)')
text = edit_row(text, 'line-04.html', 'CT-FYRAN 256', lambda row: set_media(row, card_media('CT-FYRAN 256', small, large)))
text = edit_row(text, 'line-04.html', 'CT-FRYAN (Firefighting)', lambda row: set_media(row, card_media('CT-FRYAN (Firefighting)', old_small, old_large)))
record['images']['CT-FRYAN (Firefighting)'] = {'source': 'moved from the earlier CT-FYRAN 256 card (Batch 7)', 'files': [Path(old_small).name, Path(old_large).name]}
write(path, text)

# ---------------------------------------------------------------- 2. ISO photos
def photo(src: Path, stem: str, widths=(480, 800, 1200)) -> dict:
    raw = src.read_bytes()
    image = Image.open(src).convert('RGB')
    token = sha(raw, 10)
    files = {}
    for width in widths:
        height = round(image.height * width / image.width)
        name = f'{stem}-{token}-{width}.webp'
        image.resize((width, height), Image.LANCZOS).save(ROOT / 'assets' / 'img' / name, 'WEBP', quality=82, method=6)
        files[width] = (name, height)
        record['created'].append(f'assets/img/{name}')
    record['images'][stem] = {'source': f'source-inputs/20261106-v07-r02/{stem}-supplied.jpg', 'source_sha256': hashlib.sha256(raw).hexdigest(),
                              'source_size': list(image.size), 'files': [v[0] for v in files.values()]}
    return files


cert = photo(PHOTO_DIR / '3.jpg', 'iso-9001-certificate')
ceremony = photo(PHOTO_DIR / '2.jpg', 'iso-9001-ceremony')


def img(files: dict, prefix: str, alt: str, sizes: str) -> str:
    src, h = files[1200]
    srcset = ', '.join(f'{prefix}{n} {w}w' for w, (n, _) in files.items())
    return (f'<img alt="{alt}" decoding="async" height="{h}" loading="lazy" sizes="{sizes}" '
            f'src="{prefix}{src}" srcset="{srcset}" width="1200"/>')


CERT_ALT = 'ISO 9001:2015 Certificate of Registration for CT UAV Joint Stock Company, in English and Vietnamese'
CEREMONY_ALT = 'ISO 9001:2015 certification ceremony for CT UAV Joint Stock Company'
BADGE = ('<p class="iso-badge"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 2.8 4.5 6v5.6c0 4.8 3 8.2 7.5 9.6 4.5-1.4 7.5-4.8 7.5-9.6V6z"></path>'
         '<path d="m8.6 12 2.4 2.4 4.6-4.8"></path></svg><span>ISO 9001:2015</span></p>')
FACTS = ('<dl class="iso-facts">'
         '<div><dt>Certification body</dt><dd>United Registrar of Systems (URS)</dd></div>'
         '<div><dt>Certificate number</dt><dd>149635/A/0001/UK/En</dd></div>'
         '<div><dt>Issue date</dt><dd>21 October 2026</dd></div>'
         '<div><dt>Expiry date</dt><dd>30 September 2029</dd></div>'
         '</dl>')
SCOPE_EN = [
    'Manufacturing composite materials for the aviation industry and UAVs',
    'Manufacturing mechanical components and equipment for UAVs',
    'Manufacturing PCBs and SMT assemblies; producing lithium-polymer batteries, chargers, and UAV flight controllers, ground station handheld',
    'Designing, testing, and assembling UAV prototypes',
    'Assembling, repairing, and maintaining UAVs',
    'Operating and providing UAV technology application solutions for civil, agricultural, forestry, and industrial sectors',
]
SCOPE_VI = [
    'Sản xuất vật liệu composite cho ngành hàng không và UAVs',
    'Sản xuất trang bị, thiết bị cơ khí cho UAVs',
    'Sản xuất bản mạch điện tử PCB, SMT, sản xuất pin lithium polymer, sạc, mạch điều khiển bay, tay cầm điều khiển phương tiện bay không người lái',
    'Thiết kế, thử nghiệm, lắp ráp nguyên mẫu UAVs',
    'Lắp ráp, sửa chữa, bảo dưỡng UAVs',
    'Vận hành và cung cấp dịch vụ giải pháp ứng dụng công nghệ phương tiện bay không người lái trong lĩnh vực dân dụng, nông nghiệp, lâm nghiệp và công nghiệp',
]

HOME_SECTION = (
    '<!-- v07 r02: ISO 9001:2015 certificate (Haykal, 6 Nov 2026). -->\n'
    '<section aria-labelledby="hsIsoTitle" class="hs-section hs-iso" id="homeIso">\n<div class="hs-shell">\n'
    '<header class="hs-head" data-reveal=""><div><p class="hs-kicker">QUALITY CERTIFICATION</p>'
    '<h2 id="hsIsoTitle">ISO 9001:2015 certified</h2></div></header>\n'
    '<div class="hs-iso__grid" data-reveal="">\n'
    f'<figure class="iso-panel iso-figure">{img(cert, "assets/img/", CERT_ALT, "(max-width: 900px) 100vw, 640px")}'
    '<figcaption>Certificate of Registration in English and Vietnamese.</figcaption></figure>\n'
    f'<div class="iso-panel hs-iso__copy">{BADGE}<h3>Quality management system</h3>'
    '<p>The quality management system of CT UAV Joint Stock Company complies with ISO 9001:2015.</p>'
    f'{FACTS}'
    '<button class="hs-button" data-route="about" type="button">See certificate details <span aria-hidden="true">→</span></button></div>\n'
    '</div>\n</div>\n</section>\n')

ABOUT_SECTION = (
    '<!-- v07 r02: ISO 9001:2015 certificate, first section after the hero (Haykal, 6 Nov 2026). -->\n'
    '<section aria-labelledby="iso-title" class="about-iso about-shell" id="iso">\n'
    '<header class="about-section-heading" data-reveal="">\n<p class="about-kicker">QUALITY CERTIFICATION</p>\n'
    '<h2 id="iso-title">Quality management system following ISO 9001:2015 standard</h2>\n</header>\n'
    '<div class="about-iso__grid" data-reveal="">\n'
    f'<figure class="iso-panel iso-figure">{img(cert, "../assets/img/", CERT_ALT, "(max-width: 900px) 100vw, 680px")}'
    '<figcaption>Certificate of Registration in English and Vietnamese.</figcaption></figure>\n'
    '<div class="about-iso__side">\n'
    f'<div class="iso-panel">{FACTS}</div>\n'
    f'<figure class="iso-panel iso-figure">{img(ceremony, "../assets/img/", CEREMONY_ALT, "(max-width: 900px) 100vw, 560px")}'
    '<figcaption>ISO 9001:2015 certification ceremony for CT UAV Joint Stock Company.</figcaption></figure>\n'
    '</div>\n</div>\n'
    '<div class="iso-panel about-iso__scope" data-reveal=""><h3>Certified scope of activities</h3><ul>'
    + ''.join(f'<li>{t}</li>' for t in SCOPE_EN) +
    '</ul></div>\n</section>\n')

# Vietnamese: certificate and ceremony-backdrop text where it exists; other labels PENDING native review.
VI = {
    'QUALITY CERTIFICATION': 'CHỨNG NHẬN CHẤT LƯỢNG',
    'ISO 9001:2015 certified': 'Đạt chứng nhận ISO 9001:2015',
    'Quality management system': 'Hệ thống quản lý chất lượng',
    'The quality management system of CT UAV Joint Stock Company complies with ISO 9001:2015.':
        'Hệ thống Quản lý Chất lượng của Công ty Cổ phần CT UAV phù hợp với ISO 9001:2015.',
    'Certification body': 'Tổ chức chứng nhận',
    'Certificate number': 'Số chứng nhận',
    'Issue date': 'Ngày cấp',
    'Expiry date': 'Ngày hết hạn',
    '21 October 2026': '21/10/2026',
    '30 September 2029': '30/09/2029',
    'See certificate details': 'Xem chi tiết chứng nhận',
    'Certificate of Registration in English and Vietnamese.': 'Giấy chứng nhận bằng tiếng Anh và tiếng Việt.',
    'Quality management system following ISO 9001:2015 standard': 'Hệ thống quản lý chất lượng theo tiêu chuẩn ISO 9001:2015',
    'ISO 9001:2015 certification ceremony for CT UAV Joint Stock Company.': 'Lễ trao chứng nhận ISO 9001:2015 cho Công ty Cổ phần CT UAV.',
    'Certified scope of activities': 'Phạm vi hoạt động được chứng nhận',
    CERT_ALT: 'Giấy chứng nhận ISO 9001:2015 của Công ty Cổ phần CT UAV, bản tiếng Anh và tiếng Việt',
    CEREMONY_ALT: 'Lễ trao chứng nhận ISO 9001:2015 cho Công ty Cổ phần CT UAV',
    **dict(zip(SCOPE_EN, SCOPE_VI)),
}

# ---------------------------------------------------------------- 3. CSS delivery
def minify_css(code: str) -> str:  # same as 20261106-batch7-redeliver.py
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    code = re.sub(r'\s+', ' ', code)
    code = re.sub(r'\s*([{};,>])\s*', r'\1', code)
    code = re.sub(r':\s+', ':', code)
    code = code.replace(';}', '}')
    return code.strip() + '\n'


css = minify_css((ROOT / 'source-code' / 'iso-certificate-v01.css').read_text(encoding='utf-8')).encode('utf-8')
css_name = f'iso-certificate-{sha(css)}.css'
(ROOT / 'assets' / 'css' / css_name).write_bytes(css)
record['created'].append(f'assets/css/{css_name}')

# ---------------------------------------------------------------- 4. Home shell and its address copies
HOME_ANCHOR = '<!-- Sitemap 8 + 9: news and activities in one feed. -->'
added = 0
for shell in SHELLS:
    text = read(shell)
    text = once(text, '<html ', f'<html {MARK} ', 'marker')
    social = re.search(r'<link href="assets/css/footer-social-[0-9a-f]{12}\.css" rel="stylesheet"/>', text)
    if not social:
        raise SystemExit(f'STOP {shell}: no social stylesheet')
    text = text[:social.end()] + f'\n<link href="assets/css/{css_name}" rel="stylesheet"/>' + text[social.end():]
    text = once(text, HOME_ANCHOR, HOME_SECTION + HOME_ANCHOR, 'home anchor')
    m = re.search(r'(<script data-i18n-skip="" id="i18nVi" type="application/json">)(.*?)(</script>)', text, re.S)
    data = json.loads(m.group(2))
    new = {k: v for k, v in VI.items() if k not in data}
    clash = {k for k in VI if k in data and data[k] != VI[k]}
    if clash:
        raise SystemExit(f'STOP dictionary clash: {clash}')
    added = len(new)
    # Append the new entries before the closing brace; the existing dictionary bytes stay as they are.
    body = m.group(2).rstrip()
    if not body.endswith('}'):
        raise SystemExit('STOP dictionary format')
    extra = ''.join(',' + json.dumps(k, ensure_ascii=False) + ':' + json.dumps(v, ensure_ascii=False) for k, v in new.items())
    new_body = body[:-1] + extra + '}'
    json.loads(new_body)
    text = text[:m.start(2)] + new_body + m.group(2)[len(body):] + text[m.end(2):]
    write(shell, text)
record['dictionary_added'] = added

# ---------------------------------------------------------------- 5. About page
path = ROOT / 'pages' / 'about.html'
text = read(path)
social = re.search(r'<link href="\.\./assets/css/footer-social-[0-9a-f]{12}\.css" rel="stylesheet"/>', text)
text = text[:social.end()] + f'\n<link href="../assets/css/{css_name}" rel="stylesheet"/>' + text[social.end():]
text = once(text, '<section aria-labelledby="purpose-title"', ABOUT_SECTION + '<section aria-labelledby="purpose-title"', 'about anchor')
write(path, text)

CHECK.mkdir(parents=True, exist_ok=True)
(CHECK / 'build-record.json').write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding='utf-8')
print('changed', len(record['changed']), 'created', len(record['created']), 'dictionary added', added, 'css', css_name)
