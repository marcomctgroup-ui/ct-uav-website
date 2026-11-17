"""Batch 5A (real page addresses) for main website refactor v05. 5 November 2026.

Haykal: "Start 5A URLs". The site stays local and goes only to free staging tools.
Method (works on any static host and on the local server, with no server rules):
- Each route gets a folder address, for example products/decarb-22/. The folder holds a copy of
  the shell (index.html) with <base href> to the site root, its own <title>, description and
  share (og:) tags. The page content is the same frame page as before.
- The router uses history.pushState with these addresses. Old #route links still work: they are
  changed to the new address on load and on hashchange.
- The seven Home product cards link to the real addresses.
- One address per page; the EN | VI switch is unchanged. No canonical tag (domain PENDING).
- When the site opens as a local file (file://), browsers block address changes, so the router
  keeps the earlier #route behaviour there.
Descriptions come only from each page's own existing text (first paragraph after the h1).
Run once on a fresh copy of v04. Exact-once replacement checks stop on any mismatch.
Address list: source-code/20261105-batch5a-url-map.json.
"""
import hashlib, html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARK = 'data-url-batch="20261105-b5a"'
LINES = {'line-01': 'passenger-uav', 'line-02': 'cargo-uav', 'line-03': 'rescue-emergency-delivery-uav',
         'line-04': 'firefighting-uav', 'line-05': 'carbon-credit-uav', 'line-06': 'drone-light-show',
         'line-07': 'security-uav', 'line-08': 'border-surveillance-uav', 'line-09': 'agricultural-uav',
         'line-10': 'forestry-uav', 'line-11': 'aquaculture-uav', 'line-12': 'digital-transformation-uav',
         'line-13': 'electric-power-uav', 'line-14': 'construction-inspection-uav',
         'line-15': 'renewable-energy-uav', 'line-16': 'bim-uav'}
FIXED = {'home': '', 'decarb22': 'products/decarb-22/', 'decarb54': 'products/decarb-54/',
         'ct-skysilk': 'products/ct-skysilk/', 'ct-camel-256': 'products/ct-camel-256/',
         'ct-pegas-230': 'products/ct-pegas-230/', 'ct-fyran-256': 'products/ct-fyran-256/',
         'ct-frona-44': 'products/ct-frona-44/', 'ct-crova-254': 'products/ct-crova-254/',
         'ct-glova': 'products/ct-glova/', 'ct-fyran-firefighting': 'products/ct-fryan/',
         'products': 'products/', 'uav-components': 'components/', 'about': 'about/',
         'shareholders': 'partnerships/', 'news': 'news/',
         'news-post': 'news/us-joint-venture-assembly-plant/', 'contact': 'contact/'}


def once(s, old, new, label):
    if s.count(old) != 1:
        raise SystemExit(f'STOP {label}: found {s.count(old)}')
    return s.replace(old, new)


idx_path = ROOT / 'index.html'
idx = idx_path.read_bytes().decode('utf-8')
if MARK in idx:
    raise SystemExit('STOP: Batch 5A already applied')
router_name = re.search(r'assets/js/(shared-script-[0-9a-f]{12}\.js)"[^>]*></script>\s*<script src="assets/js/shared-script-640eedc0a6dc', idx)
router_name = 'shared-script-b25c9205c70d.js'
router_path = ROOT / 'assets/js' / router_name
r = router_path.read_bytes().decode('utf-8')
routes = json.loads(re.search(r'const routes=(\[.*?\])', r).group(1))
titles = json.loads(re.search(r'(\{"home":.*?\})', r).group(1))

paths = {}
for route in routes:
    if route in FIXED:
        paths[route] = FIXED[route]
    elif route in LINES:
        paths[route] = 'applications/' + LINES[route] + '/'
    elif route.startswith('component-'):
        paths[route] = 'components/' + route[len('component-'):] + '/'
    else:
        raise SystemExit('STOP: no address for ' + route)
if len(set(paths.values())) != len(paths):
    raise SystemExit('STOP: duplicate address')
for p in paths.values():
    if p.split('/')[0] in ('assets', 'pages', 'checks', 'source-code', 'source-inputs'):
        raise SystemExit('STOP: reserved folder ' + p)
(ROOT / 'source-code/20261105-batch5a-url-map.json').write_text(
    json.dumps(paths, indent=1, ensure_ascii=False), encoding='utf-8')

# 1. Router: pushState addresses, legacy hash support, shell link clicks.
helper = ("const PATHS=" + json.dumps(paths, separators=(',', ':')) + ";"
          "const SITE=new URL('./',document.baseURI);"
          "const urlFor=r=>new URL(PATHS[r]||'',SITE).href;"
          "const relPath=u=>u.pathname.startsWith(SITE.pathname)?u.pathname.slice(SITE.pathname.length).replace(/index\\.html$/,''):null;"
          "const fromPath=()=>{const p=relPath(location);for(const k in PATHS)if(PATHS[k]===p)return k;return 'home';};"
          "const FILE=location.protocol==='file:';"
          "const go=(next,replace)=>{if(FILE){if(location.hash.slice(1)!==next)location.hash=next;else showRoute(next);return;}"
          "const url=urlFor(next);if(location.href!==url)history[replace?'replaceState':'pushState'](null,'',url);showRoute(next);};"
          "document.addEventListener('click',e=>{const a=e.target.closest&&e.target.closest('a[href]');"
          "if(!a||e.defaultPrevented||e.button||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||a.target)return;"
          "const u=new URL(a.getAttribute('href'),document.baseURI);if(u.origin!==location.origin||u.hash)return;"
          "const p=relPath(u);if(p===null)return;for(const k in PATHS)if(PATHS[k]===p){e.preventDefault();window.ctuavDemo.navigate(k);return;}});")
r = once(r, "window.ctuavDemo={", helper + "window.ctuavDemo={", 'router helper')
r = once(r, "if(location.hash!=='#'+next)location.hash=next;else showRoute(next);", "go(next);", 'navigate')
r = once(r, "addEventListener('hashchange',()=>showRoute(location.hash.slice(1)));",
         "addEventListener('hashchange',()=>{const h=location.hash.slice(1);if(FILE)showRoute(h||fromPath());else if(routes.includes(h))go(h,true);});"
         "addEventListener('popstate',()=>showRoute(fromPath()));", 'hashchange')
r = once(r, "showRoute(location.hash.slice(1));})();",
         "{const h=location.hash.slice(1);if(FILE&&routes.includes(h)){showRoute(h);}else{if(routes.includes(h))history.replaceState(null,'',urlFor(h));showRoute(fromPath());}}})();", 'init')
new_router = 'shared-script-' + hashlib.sha256(r.encode('utf-8')).hexdigest()[:12] + '.js'
(ROOT / 'assets/js' / new_router).write_bytes(r.encode('utf-8'))
router_path.unlink()
src_copy = ROOT / 'source-code' / router_name
if src_copy.exists():
    src_copy.unlink()
(ROOT / 'source-code' / new_router).write_bytes(r.encode('utf-8'))
idx = once(idx, router_name, new_router, 'router reference')

# 2. Home product cards: real addresses.
for route in ['ct-skysilk', 'ct-camel-256', 'ct-fyran-256', 'decarb22', 'ct-crova-254', 'ct-pegas-230', 'ct-frona-44']:
    idx = once(idx, f'href="#{route}"', f'href="{paths[route]}"', 'card ' + route)
idx = once(idx, '<html ', f'<html {MARK} ', 'marker') if '<html ' in idx else once(idx, '<html>', f'<html {MARK}>', 'marker')
# A fixed <base> before the first script. pushState changes the address, so without a fixed base
# later relative URLs (frames, deferred images, scripts) would load from the new folder.
idx = once(idx, '<head>', '<head><base href="./"/>', 'root base')
idx_path.write_bytes(idx.encode('utf-8'))


# 3. One entry file per route.
def page_description(route):
    page = ROOT / 'pages' / f'{route}.html'
    if not page.exists():
        return None
    s = page.read_bytes().decode('utf-8')
    h1 = s.find('<h1')
    if h1 < 0:
        return None
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>', s[h1:], re.S):
        text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))).strip()
        if len(text) >= 50:
            if len(text) > 160:
                text = text[:157].rsplit(' ', 1)[0].rstrip(',.;:') + '…'
            return text
    return None


site_desc = re.search(r'<meta content="([^"]*)" name="description"/>', idx).group(1)
report = {}
for route, path in paths.items():
    if route == 'home':
        continue
    depth = path.count('/')
    base = '../' * depth
    title = titles.get(route, 'CT UAV')
    desc = page_description(route)
    used = desc or html.unescape(site_desc)
    report[route] = {'path': path, 'title': title, 'description_source': 'page text' if desc else 'site description'}
    e = idx
    e = once(e, '<head><base href="./"/>', f'<head><base href="{base}"/>', 'base ' + route)
    e = re.sub(r'<title>.*?</title>', '<title>' + html.escape(title, quote=False) + '</title>', e, count=1, flags=re.S)
    tags = (f'<meta content="{html.escape(used)}" name="description"/>'
            f'<meta property="og:type" content="website"/>'
            f'<meta property="og:title" content="{html.escape(title)}"/>'
            f'<meta property="og:description" content="{html.escape(used)}"/>')
    e = once(e, f'<meta content="{site_desc}" name="description"/>', tags, 'description ' + route)
    out = ROOT / path / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(e.encode('utf-8'))
(ROOT / 'source-code/20261105-batch5a-entries.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
print('router', new_router, 'entries', len(report),
      'page-text descriptions', sum(v['description_source'] == 'page text' for v in report.values()))
