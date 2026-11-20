"""refactor-v16: performance and SEO changes on top of a copy of refactor-v15.

Usage (from the repository root):
    python projects/main-website/refactor-v16/source-code/20261117-v16-perf-seo-build.py

Writes only inside refactor-v16. Safe to run again: each injected block sits
between <!-- seo:v16 --> markers and is replaced, not added twice.
Settings: 20261117-v16-seo-config-v01.json (URLs are NOT final).

Changes
1. Font preload (regular/semibold/bold) in every shell and page document:
   removes the web-font layout shift (Lighthouse CLS cause "Web font loaded").
2. Route shells: own <title>, meta description, canonical, Open Graph,
   JSON-LD (Organization + WebSite on Home, BreadcrumbList, Product),
   one page H1 (visually hidden, same text as the visible page H1), the
   chatbot greeting changes from <h1> to <p> with the same style, and the
   navbar / footer / Home buttons become crawlable <a href> links.
3. Page documents (iframe content): robots "noindex, indexifembedded" so
   Google indexes their text as part of the route URL, not as separate URLs.
4. page-loader: the 3D model downloads in the background after page load;
   the 3D start-up (CPU work) waits until the stage is on screen.
4b. Shell router: the hidden Home hero frame loads only on Home, or after the
   first user action on other routes; runtime titles equal the HTML titles.
5. sitemap.xml and 404.html at the version root.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'source-code/20261117-v16-seo-config-v01.json').read_text(encoding='utf-8'))
URL_MAP = json.loads((ROOT / 'source-code/20261105-batch5a-url-map.json').read_text(encoding='utf-8'))
BASE = CONFIG['canonical_base']
START, END = '<!-- seo:v16 -->', '<!-- /seo:v16 -->'
FONTS = ['montserrat-regular-sub-3e99c730aa.woff2', 'montserrat-semibold-sub-7f7c80cd93.woff2',
         'montserrat-bold-sub-468a527258.woff2']
TODAY = date.today().isoformat()
DEFAULT_OG_IMAGE = 'assets/img/decarb22-poster-b3129b609e-measured.webp'

# ---------------------------------------------------------------- helpers

def text_of(fragment: str) -> str:
    fragment = re.sub(r'<(script|style|template|noscript)\b[^>]*>.*?</\1>', ' ', fragment, flags=re.S | re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment))).strip()


def first(pattern: str, source: str, flags=re.S | re.I) -> str:
    m = re.search(pattern, source, flags)
    return m.group(1) if m else ''


def clip(text: str, limit: int = 158) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0].rstrip(',;:-–')
    return cut + '…'


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def put_block(doc: str, block: str) -> str:
    doc = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\n?', '', doc, flags=re.S)
    return doc.replace('</head>', f'{START}\n{block}\n{END}\n</head>', 1)


def routes() -> dict:
    """route key -> {page, path, type, parents}. Explicit config first, then the URL map."""
    out = {}
    for key, path in URL_MAP.items():
        kind = 'line' if key.startswith('line-') else 'component' if key.startswith('component-') else 'page'
        parents = ['products'] if kind == 'line' else ['uav-components'] if kind == 'component' else []
        out[key] = {'page': key, 'path': path, 'type': kind, 'parents': parents}
    for key, value in CONFIG['routes'].items():
        out.setdefault(key, {'parents': []}).update(value)
        out[key].setdefault('type', 'page')
        if out[key]['type'] == 'product':
            out[key]['parents'] = ['products']
    return out


ROUTES = routes()
PATH_OF = {key: r['path'] for key, r in ROUTES.items()}

# ---------------------------------------------------------------- page facts

def page_facts(page_id: str) -> dict:
    doc = (ROOT / 'pages' / f'{page_id}.html').read_text(encoding='utf-8')
    title = text_of(first(r'<title>(.*?)</title>', doc)) or 'CT UAV'
    h1 = text_of(first(r'<h1\b[^>]*>(.*?)</h1>', doc))
    body = re.sub(r'<(header|nav|footer)\b[^>]*>.*?</\1>', ' ', doc, flags=re.S | re.I)
    desc = ''
    for para in re.findall(r'<p\b[^>]*>(.*?)</p>', body, flags=re.S | re.I):
        candidate = text_of(para)
        if len(candidate) >= 70 and not candidate.lower().startswith(('©', 'copyright')):
            desc = candidate
            break
    img = ''
    for src in re.findall(r'<(?:img|video)\b[^>]*?(?:src|poster|data-defer-src)="([^"]+\.(?:webp|jpe?g|png))"', doc, flags=re.I):
        img = src.replace('../', '', 1) if src.startswith('../') else src
        break
    return {'title': title, 'h1': h1 or title.split('|')[0].strip(), 'description': clip(desc), 'image': img}


# ---------------------------------------------------------------- approved copy corrections (18 November 2026)
# User decisions: product name "CT-FYRAN" (not "CT-FRYAN"); membership wording "Member of CT Group Hi-tech"
# (root AGENTS.md, confirmed 16 November). Page addresses (lowercase ct-fryan) are not changed.
COPY_FIXES = [
    (r'CT-FRYAN', 'CT-FYRAN'),
    (r'CT Group Hi-Tech', 'CT Group Hi-tech'),
    (r'([Mm]ember of CT Group)(?! Hi-)', r'\1 Hi-tech'),
    (r'([Tt]hành viên (?:của )?(?:Tập đoàn )?CT Group)(?! Hi-)', r'\1 Hi-tech'),
]


def copy_corrections() -> int:
    files = [*ROOT.glob('pages/*.html'), ROOT / 'assets/i18n/vi.json']
    files += [p for p in ROOT.rglob('index.html') if not {'source-code', 'checks', 'source-inputs'} & set(p.relative_to(ROOT).parts)]
    changed = 0
    for f in files:
        text = f.read_bytes().decode('utf-8')  # keep CRLF/LF exactly as stored
        new = text
        for pattern, repl in COPY_FIXES:
            new = re.sub(pattern, repl, new)
        if new != text:
            f.write_bytes(new.encode('utf-8'))
            changed += 1
    return changed


# ---------------------------------------------------------------- shells

FONT_LINKS = lambda prefix: '\n'.join(
    f'<link rel="preload" href="{prefix}assets/fonts/{f}" as="font" type="font/woff2" crossorigin/>' for f in FONTS)

SHELL_CSS = ('<style>'
             '.seo-h1{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;'
             'clip:rect(0 0 0 0);white-space:nowrap;border:0}'
             '.cu-widget .cu-welcome .cu-hi{margin:14px 0 4px;font-size:21px;line-height:1.3;font-weight:600;'
             'letter-spacing:-.03em;color:var(--cu-ink)}'
             ':where(a.nav-link,a.brand-button,a[data-footer-route],a.hs-button,a.hs-feature)'
             '{text-decoration:none;color:inherit;cursor:pointer;text-align:center}'
             # v15 buttons rendered 16 px / 400; section link rules must not change that.
             'a.hs-button,a.hs-feature{font-size:16px;font-weight:400}a[data-footer-route]{font-size:15px;font-weight:600}'
             # v15 buttons used button:focus-visible{outline:2px solid #2479a5;outline-offset:3px}
             ':is(a.nav-link,a.brand-button,a[data-footer-route],a.hs-button,a.hs-feature):focus-visible'
             '{outline:2px solid #2479a5;outline-offset:3px}'
             # CT Ency "Coming soon" (user decision 18 Nov): no chips, no composer, no voice.
             '.cu-widget .cu-starts,.cu-widget .cu-composer,.cu-widget #cuVoiceStatus,.cu-widget #cuVoiceDisclosure{display:none!important}'
             '.cu-widget .cu-welcome .cu-soon{margin:4px 0 0;font-size:16px;line-height:1.45;font-weight:600;color:var(--cu-ink)}'
             '.cu-widget .cu-welcome .cu-soon-note{margin:8px 0 0;font-size:15px;line-height:1.5;color:var(--cu-ink)}'
             '.cu-widget[data-lang="vi"] .cu-welcome [lang="en"],.cu-widget:not([data-lang="vi"]) .cu-welcome [lang="vi"]{display:none}'
             '.cu-widget #cuNewChat{display:none!important}'
             # Static copy of the poster rules that the mascot script injects later (BLEED 0.14).
             '.cu-launcher .ce-mascot{position:relative}'
             '.cu-launcher .ce-mascot__poster{position:absolute;left:-14.0%;top:-14.0%;width:128.0%;height:128.0%;max-width:none;'
             'display:block;pointer-events:none;-webkit-user-select:none;user-select:none;object-fit:contain}'
             '.cu-launcher .ce-mascot:has(.ce-mascot__poster) .ce-mascot__fallback{display:none}'
             # Keep a route frame invisible while the "Loading page" layer shows; its first paint shifted (CLS ~1).
             '#content:has(> #pageLoading:not([hidden])) > iframe.page-frame:not(#heroFrame){visibility:hidden}'
             '.cu-widget .cu-welcome .cu-soon-link{display:inline-flex;align-items:center;justify-content:center;min-height:44px;'
             'margin-top:14px;padding:0 20px;border:1px solid var(--cu-ink);border-radius:999px;color:var(--cu-ink);'
             'background:#fff;font-size:15px;font-weight:600;text-decoration:none}'
             '.cu-widget .cu-welcome .cu-soon-link:focus-visible{outline:2px solid #2479a5;outline-offset:3px}'
             '</style>')


def json_ld(key: str, facts: dict, url: str, description: str) -> list:
    org = {'@type': 'Organization', '@id': BASE + '#organization', 'name': CONFIG['organization']['name'],
           'url': BASE, 'logo': BASE + CONFIG['organization']['logo'],
           'parentOrganization': {'@type': 'Organization', 'name': CONFIG['organization']['parent']},
           'telephone': CONFIG['organization']['telephone']}
    graph = []
    if key == 'home':
        graph += [org, {'@type': 'WebSite', '@id': BASE + '#website', 'name': CONFIG['site_name'], 'url': BASE,
                        'publisher': {'@id': BASE + '#organization'}}]
    else:
        items = [('Home', BASE)]
        for parent in ROUTES[key].get('parents', []):
            items.append((page_facts(ROUTES[parent]['page'])['h1'] if parent != 'products' else 'Products',
                          BASE + ROUTES[parent]['path']))
        items.append((facts['h1'], url))
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': name, 'item': link} for i, (name, link) in enumerate(items)]})
    if ROUTES[key]['type'] == 'product':
        product = {'@type': 'Product', 'name': facts['h1'], 'description': description, 'url': url,
                   'brand': {'@type': 'Brand', 'name': 'CT UAV'},
                   'manufacturer': {'@type': 'Organization', 'name': 'CT UAV'}}
        if facts['image']:
            product['image'] = BASE + facts['image']
        graph.append(product)
    return graph



SOON = ('<p class="cu-soon"><span lang="en">Coming soon</span><span lang="vi">Sắp ra mắt</span></p>'
        '<p class="cu-soon-note"><span lang="en">CT Ency, our AI assistant, is coming soon. For questions, please contact our team.</span>'
        '<span lang="vi">Trợ lý AI CT Ency sắp ra mắt. Nếu có câu hỏi, vui lòng liên hệ đội ngũ của chúng tôi.</span></p>'
        '<a class="cu-soon-link" href="contact/"><span lang="en">Contact CT UAV</span><span lang="vi">Liên hệ CT UAV</span></a>')


def ency_coming_soon(doc: str) -> str:
    """User decision 18 Nov 2026: CT Ency stays visible as "Coming soon"; chatbot service stays stopped."""
    if SOON not in doc:
        doc = re.sub(r'<p class="cu-soon">.*?(?:</a>|</p>(?=\s*<div class="cu-starts"))(?:</p>)?', '', doc, count=1, flags=re.S) if 'class="cu-soon"' in doc else doc
        doc = re.sub(r'<p class="cu-soon-note">.*?</p>', '', doc, count=1, flags=re.S)
        doc = re.sub(r'<p class="cu-tagline" data-i18n="tagline">[^<]*</p>', SOON, doc, count=1)
        if SOON not in doc:
            doc = doc.replace('<div class="cu-starts">', SOON + '<div class="cu-starts">', 1)
    doc = doc.replace('aria-label="Open CT Ency chat"', 'aria-label="Open CT Ency chat (coming soon)"')
    return doc

def nav_to_links(doc: str) -> tuple[str, int]:
    """<button ... data-page|data-footer-route|data-route="X" ...>…</button> -> <a ... href="path">…</a>."""
    count = 0

    def swap(m):
        nonlocal count
        attrs, inner = m.group(1), m.group(2)
        key = first(r'data-(?:page|footer-route|route)="([^"]+)"', attrs, 0)
        if key not in PATH_OF or 'href=' in attrs:
            return m.group(0)
        count += 1
        attrs = re.sub(r'\s+type="button"', '', attrs)
        return f'<a{attrs} href="{PATH_OF[key] or "./"}">{inner}</a>'

    doc = re.sub(r'<button((?:(?!>)[\s\S])*?\sdata-(?:page|footer-route|route)="[^"]+"[^>]*)>(.*?)</button>',
                 swap, doc, flags=re.S)
    return doc, count


def build_shell(key: str, shell: Path) -> dict:
    doc = shell.read_text(encoding='utf-8')
    facts = page_facts(ROUTES[key]['page'])
    facts['h1'] = CONFIG.get('h1_overrides', {}).get(key, facts['h1'])
    url = BASE + ROUTES[key]['path']
    title = 'CT UAV | Member of CT Group Hi-tech' if key == 'home' else facts['title']
    override = CONFIG['description_overrides'].get(key)
    description = override or facts['description'] or CONFIG['description_overrides']['home']
    if ROUTES[key]['type'] == 'component':
        # Model code + component name from the page itself; the shared contact line stays.
        model = facts['title'].split('|')[0].strip()
        title = f"{model} {facts['h1']} | CT UAV Components"
        facts['h1'] = f"{facts['h1']} {model}"  # unique H1 per component (two pages shared "Multirotor Motor")
        description = clip(f"{facts['h1']} {model}, a UAV component from CT UAV. {facts['description']}")
    doc = re.sub(r'<title>.*?</title>', f'<title>{esc(title)}</title>', doc, count=1, flags=re.S)
    doc = re.sub(r'<meta content="[^"]*" name="description"/>', f'<meta content="{esc(description)}" name="description"/>', doc, count=1)
    # Social platforms do not show SVG share images: fall back to a raster product photo.
    image = BASE + (facts['image'] if facts['image'] and not facts['image'].endswith('.svg') else DEFAULT_OG_IMAGE)
    block = '\n'.join([
        FONT_LINKS(''),
        f'<link rel="canonical" href="{esc(url)}"/>',
        '<meta property="og:type" content="{}"/>'.format('product' if ROUTES[key]['type'] == 'product' else 'article' if key == 'news-post' else 'website'),
        f'<meta property="og:site_name" content="{esc(CONFIG["site_name"])}"/>',
        f'<meta property="og:title" content="{esc(title)}"/>',
        f'<meta property="og:description" content="{esc(description)}"/>',
        f'<meta property="og:url" content="{esc(url)}"/>',
        f'<meta property="og:image" content="{esc(image)}"/>',
        '<meta name="twitter:card" content="summary_large_image"/>',
        '<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': json_ld(key, facts, url, description)},
                                                           ensure_ascii=False).replace('</', '<\\/') + '</script>',
        SHELL_CSS])
    doc = put_block(doc, block)
    doc = doc.replace('<h1 data-i18n="hi">', '<p class="cu-hi" data-i18n="hi">', 1)
    doc = re.sub(r'(<p class="cu-hi" data-i18n="hi">[^<]*)</h1>', r'\1</p>', doc, count=1)
    doc = re.sub(r'<h1 class="seo-h1">.*?</h1>', '', doc, flags=re.S)
    doc = re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1) + f'<h1 class="seo-h1">{esc(facts["h1"])}</h1>', doc, count=1)
    doc = ency_coming_soon(doc)
    doc = launcher_poster(doc)
    # Home "All products" mosaic images display 134-221 px wide; their sizes said 100vw (PageSpeed: 437 KiB waste).
    doc = re.sub(r'(<span aria-hidden="true" class="hp-all-grid">.*?</span>)',
                 lambda m: m.group(1).replace('sizes="(max-width: 600px) 100vw, (max-width: 1024px) 50vw, 700px"',
                                              'sizes="(max-width: 600px) 42vw, (max-width: 1024px) 22vw, 225px"'),
                 doc, count=1, flags=re.S)
    if key == 'home' and 'data-home-hero-visible' not in doc[:600]:
        # Home starts with the hero visible: hide the CT Ency launcher from the first paint (it was the late
        # mobile LCP element on PageSpeed, painted before the script that hides it ran).
        doc = re.sub(r'<html\b', '<html data-home-hero-visible=""', doc, count=1)
    doc, links = nav_to_links(doc)
    shell.write_text(doc, encoding='utf-8', newline='')
    return {'route': key, 'shell': shell.relative_to(ROOT).as_posix(), 'title': title, 'h1': facts['h1'],
            'description': description, 'description_source': ('draft override' if key in CONFIG.get('_draft_descriptions', []) else 'override') if override else 'auto: first page paragraph',
            'canonical': url, 'links_converted_this_run': links,
            'route_links_in_output': len(re.findall(r'<a\b[^>]*data-(?:page|footer-route|route)="[^"]+"[^>]*href=', doc))}


# ---------------------------------------------------------------- page documents

EARLY_STYLE = ('<style id="v16-early">html,body{margin:0}.review-bar{display:none!important}'
               # Product bar: main overlaps it by a negative margin equal to its height (62 px / 102 px up to 1000 px).
               # A fixed height keeps main still if the bar content changes while loading (DECARB 22 CLS on main).
               '.product-bar{height:62px}@media (max-width:1000px){.product-bar{height:102px}}</style>')


def build_page_doc(path: Path) -> None:
    doc = path.read_text(encoding='utf-8')
    # The page document can be laid out before its stylesheets apply (CLS ~1 on product pages: body y8 -> 0).
    # Set the reset margin before any script or stylesheet.
    if EARLY_STYLE not in doc:
        doc = re.sub(r'<style id="v16-early">.*?</style>', '', doc, count=1)
        doc = re.sub(r'(<head\b[^>]*>)', lambda m: m.group(1) + EARLY_STYLE, doc, count=1)
    block = FONT_LINKS('../') + '\n<meta name="robots" content="noindex, indexifembedded"/>'
    outside = re.sub(re.escape(START) + r'.*?' + re.escape(END), '', doc, flags=re.S)
    if 'rel="icon"' not in outside:  # direct opens otherwise request /favicon.ico (404); ignore our own old block
        block += '\n<link rel="icon" href="../assets/img/ct-uav-d4035ad7bb.svg"/>'
    path.write_text(put_block(doc, block), encoding='utf-8', newline='')


# ---------------------------------------------------------------- page-loader (3D)

OLD_3D = "new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting))launch()},{rootMargin:'100px'}).observe(stage);"
NEW_3D = ("// v16: download the model on the first scroll/touch/key (only when needed); start the 3D CPU work when the stage is on screen.\n"
          "  const prefetch=()=>{const p=parent;const key=stage.dataset.psModel||stage.dataset.u3dModel;"
          "['uav3dLib','uav3dModel-'+key].forEach(id=>p.ctuavHydrate&&p.ctuavHydrate(p.document.getElementById(id)).catch(()=>{}))};"
          "['scroll','wheel','touchstart','keydown','pointerdown'].forEach(t=>addEventListener(t,prefetch,{once:true,passive:true}));\n"
          "  new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting))launch()},{rootMargin:'0px 0px -20% 0px'}).observe(stage);")


def rehash(old: Path, content: str) -> Path:
    digest = hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]
    new = old.with_name(re.sub(r'-[0-9a-f]{12}\.js$', f'-{digest}.js', old.name))
    new.write_text(content, encoding='utf-8', newline='')
    if new != old:
        old.unlink()
    return new


def patch_page_loader() -> str:
    candidates = sorted((ROOT / 'assets/js').glob('page-loader-*.js'))
    assert len(candidates) == 1, candidates
    old = candidates[0]
    text = old.read_text(encoding='utf-8')
    if NEW_3D not in text:
        earlier = re.search(r"// v16: download the model.*?observe\(stage\);", text, re.S)
        if earlier:
            text = text.replace(earlier.group(0), NEW_3D, 1)
        else:
            assert OLD_3D in text, 'page-loader 3D trigger not found'
            text = text.replace(OLD_3D, NEW_3D, 1)
    new = rehash(old, text)
    if new.name != old.name:
        for f in [*ROOT.glob('pages/*.html'), ROOT / '_headers']:
            t = f.read_text(encoding='utf-8')
            if old.name in t:
                f.write_text(t.replace(old.name, new.name), encoding='utf-8', newline='')
    return new.name


# ---------------------------------------------------------------- shell router (v10 shared script)

OLD_HERO = 'c.src="pages/hero.html",V();'
# Home route: load the hero at once (y() below). Other routes: load it on the first user action,
# so a later return to Home stays fast but the hidden hero (scripts, posters) does not load at start.
NEW_HERO = ('document.addEventListener("click",e=>{const t=e.target.closest&&e.target.closest("a[href]");'
            't&&(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button)&&e.stopImmediatePropagation()},!0),'
            '["pointerdown","keydown","touchstart","wheel"].forEach(t=>addEventListener(t,()=>{c.getAttribute("src")||'
            '(c.src="pages/hero.html")},{once:!0,passive:!0,capture:!0})),V();')
OLD_Y = 'function y(n){'
NEW_Y = 'function y(n){if(!c.getAttribute("src")&&!(e.includes(n)&&"home"!==n))c.src="pages/hero.html";'


def patch_router(titles: dict) -> str:
    """Lazy hero frame + runtime titles equal to the HTML titles (one source: the SEO config)."""
    old = ROOT / 'assets/js/v10/shared-script-308abf9d90d1.js'
    if not old.exists():
        old = next(p for p in (ROOT / 'assets/js/v10').glob('shared-script-*.js') if 'pages/hero.html' in p.read_text(encoding='utf-8'))
    text = old.read_text(encoding='utf-8')
    if NEW_HERO not in text:
        earlier = re.search(r'(?:document\.addEventListener\("click",e=>\{const t=e\.target\.closest[^;]*?!0\),)?\["pointerdown","keydown","touchstart","wheel"\]\.forEach\(.*?\),V\(\);', text, re.S)
        if earlier:
            text = text.replace(earlier.group(0), NEW_HERO, 1)
        else:
            assert text.count(OLD_HERO) == 1 and text.count(OLD_Y) == 1, 'router patterns not found'
            text = text.replace(OLD_HERO, NEW_HERO).replace(OLD_Y, NEW_Y)
    end = text.index('},n=()=>')
    start = text.rindex(',t={', 0, end) + 1
    table = text[start:end]
    for key, title in titles.items():
        pattern = r'((?:"' + re.escape(key) + r'"|(?<=[{,])' + re.escape(key) + r'):")[^"]*(")'
        table, _ = re.subn(pattern, lambda m: m.group(1) + title.replace('\\', '\\\\').replace('"', '\\"') + m.group(2), table, count=1)
    text = text[:start] + table + text[end:]
    new = rehash(old, text)
    readable = ROOT / 'source-code' / old.name
    if readable.exists():  # the readable copy equals the delivery file for this script
        (ROOT / 'source-code' / new.name).write_text(text, encoding='utf-8', newline='')
        if new.name != old.name:
            readable.unlink()
    if new.name != old.name:
        for f in [*ROOT.rglob('index.html'), ROOT / '_headers']:
            if {'source-code', 'checks'} & set(f.relative_to(ROOT).parts):
                continue
            t = f.read_text(encoding='utf-8')
            if old.name in t:
                f.write_text(t.replace(old.name, new.name), encoding='utf-8', newline='')
    return 'v10/' + new.name


# ---------------------------------------------------------------- CT Ency launcher poster in the HTML (LCP)
# PageSpeed (product routes): the launcher mascot poster was the mobile LCP element, added late by the mascot
# script (render delay ~1 s). The poster <img> is now in the HTML; the script reuses it instead of adding a copy.
POSTER_IMG = ('<img class="ce-mascot__poster" alt="" draggable="false" decoding="async" '
              'src="assets/img/ct-ency-poster-498e3c117b.webp"/>')
OLD_SHOW = "var img=new Image();img.className='ce-mascot__poster';"
NEW_SHOW = "var img=host.querySelector('img.ce-mascot__poster')||new Image();img.className='ce-mascot__poster';"
OLD_APPEND = "img.src=src;host.appendChild(img);}"
NEW_APPEND = ("if(img.getAttribute('src')!==src)img.src=src;if(!img.parentNode)host.appendChild(img);"
              "if(img.complete&&img.naturalWidth){var f0=host.querySelector('.ce-mascot__fallback');if(f0)f0.remove();}}")


def patch_mascot_engine() -> str:
    old = next((ROOT / 'assets/js').glob('ctencymascotengine-*.js'))
    text = old.read_text(encoding='utf-8')
    if NEW_SHOW not in text:
        assert text.count(OLD_SHOW) == 1 and text.count(OLD_APPEND) == 1, 'mascot engine patterns not found'
        text = text.replace(OLD_SHOW, NEW_SHOW).replace(OLD_APPEND, NEW_APPEND)
    new = rehash(old, text)
    readable = ROOT / 'source-code' / old.name
    if readable.exists():
        (ROOT / 'source-code' / new.name).write_text(text, encoding='utf-8', newline='')
        if new.name != old.name:
            readable.unlink()
    if new.name != old.name:
        for f in [*ROOT.rglob('index.html'), ROOT / '_headers']:
            if {'source-code', 'checks'} & set(f.relative_to(ROOT).parts):
                continue
            t = f.read_text(encoding='utf-8')
            if old.name in t:
                f.write_text(t.replace(old.name, new.name), encoding='utf-8', newline='')
    return new.name


def launcher_poster(doc: str) -> str:
    if POSTER_IMG in doc:
        return doc
    return re.sub(r'(<span aria-hidden="true" class="ce-mascot ce-mascot--launcher"[^>]*><span class="ce-mascot__fallback">CE</span>)',
                  lambda m: m.group(1) + POSTER_IMG, doc, count=1)


# ---------------------------------------------------------------- sitemap and 404

def write_sitemap(entries: list) -> None:
    urls = '\n'.join(f'  <url><loc>{esc(e["canonical"])}</loc><lastmod>{TODAY}</lastmod></url>' for e in entries)
    (ROOT / 'sitemap.xml').write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
        encoding='utf-8', newline='\n')


PAGE_404 = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="robots" content="noindex"/>
<title>Page not found | CT UAV</title>
<link rel="icon" href="/assets/img/ct-uav-d4035ad7bb.svg"/>
<link rel="preload" href="/assets/fonts/montserrat-regular-sub-3e99c730aa.woff2" as="font" type="font/woff2" crossorigin/>
<style>
@font-face{font-family:Montserrat;src:url("/assets/fonts/montserrat-regular-sub-3e99c730aa.woff2") format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:Montserrat;src:url("/assets/fonts/montserrat-semibold-sub-7f7c80cd93.woff2") format("woff2");font-weight:600;font-display:swap}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f5;color:#1f2328;font:400 16px/1.6 Montserrat,Arial,sans-serif;padding:24px;box-sizing:border-box}
main{max-width:560px;background:#fff;border:1px solid #e3e5e8;border-radius:16px;padding:40px 32px;text-align:center}
img{width:96px;height:auto}
h1{font-size:28px;font-weight:600;margin:16px 0 8px}
p{margin:0 0 24px}
a{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 24px;border:1px solid #1f2328;border-radius:999px;color:#1f2328;text-decoration:none;font-weight:600}
a:focus-visible{outline:3px solid #52616b;outline-offset:3px}
</style>
</head>
<body>
<main>
<img src="/assets/img/ct-uav-d4035ad7bb.svg" alt="CT UAV" width="96" height="96"/>
<h1>Page not found</h1>
<p>This page does not exist or has moved. Không tìm thấy trang.</p>
<a href="/">Go to CT UAV home</a>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- main

def main() -> None:
    fixed = copy_corrections()
    by_path = {r['path']: k for k, r in ROUTES.items()}
    report = []
    for shell in sorted(ROOT.rglob('index.html')):
        rel = shell.relative_to(ROOT)
        if rel.parts[0] in {'source-code', 'checks', 'source-inputs'}:
            continue
        path = '' if rel.as_posix() == 'index.html' else rel.parent.as_posix() + '/'
        key = by_path.get(path)
        if key is None:
            raise SystemExit(f'STOP: no route for {rel}')
        report.append(build_shell(key, shell))
    for page in sorted((ROOT / 'pages').glob('*.html')):
        build_page_doc(page)
    loader = patch_page_loader()
    router = patch_router({r['route']: r['title'] for r in report})
    engine = patch_mascot_engine()
    write_sitemap(report)
    (ROOT / '404.html').write_text(PAGE_404, encoding='utf-8', newline='\n')
    out = ROOT / 'checks/20261117-v16'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'seo-build-report.json').write_text(json.dumps({'date': TODAY, 'page_loader': loader, 'router': router, 'routes': report},
                                                          indent=1, ensure_ascii=False), encoding='utf-8')
    print(f'copy fixes in {fixed} files; {len(report)} shells, {len(list((ROOT / "pages").glob("*.html")))} page documents, loader {loader}, router {router}, '
          f'route links in output {sum(r["route_links_in_output"] for r in report)} (new this run {sum(r["links_converted_this_run"] for r in report)})')


if __name__ == '__main__':
    main()
