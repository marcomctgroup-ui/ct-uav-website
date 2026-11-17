"""Check the main website demo against QUALITY-GUARDRAILS.md (22 October 2026).

Measures the rendered page in Microsoft Edge (headless), not the CSS source:
text size, button text size, dark surfaces, dark overlays, text contrast,
element opacity, font, control height, horizontal overflow, broken images
and script errors. Limits come from quality-guardrails.json at the repository root.

Usage:
  python 20261022-ctuav-main-website-guardrails-check-v01.py            # latest files
  python ... path/to/file.html [more.html]                              # named files
  python ... --full                                                     # 5 widths
  python ... --shots DIR                                                # save screenshots
  python ... --json OUT.json                                            # save the result

Exit code 1 when one or more FAIL items exist.
"""
from pathlib import Path
import argparse
import json
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'quality-guardrails.json').is_file())
SITE = ROOT
CONFIG = json.loads((ROOT / 'quality-guardrails.json').read_text(encoding='utf-8'))

MEASURE = r"""
(cfg) => {
  const out = [];
  const phone = cfg.viewport <= cfg.phone_max_width;
  const minText = phone ? cfg.min_text_px.phone : cfg.min_text_px.desktop;
  const minBtn = phone ? cfg.min_button_text_px.phone : cfg.min_button_text_px.desktop;
  const ignore = cfg.ignore_selectors.join(',');
  const allowDark = cfg.approved_dark_exceptions.join(',');

  const parse = (c) => {
    if (!c) return null;
    let m = c.match(/^rgba?\(([^)]+)\)/);
    if (m) {
      const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat);
      return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    }
    m = c.match(/^color\(srgb ([^)]+)\)/);
    if (m) {
      const p = m[1].split(/[\s\/]+/).filter(Boolean).map(parseFloat);
      return { r: p[0] * 255, g: p[1] * 255, b: p[2] * 255, a: p.length > 3 ? p[3] : 1 };
    }
    return null;
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const over = (top, under) => {
    const a = top.a + under.a * (1 - top.a);
    if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
    const mix = (k) => (top[k] * top.a + under[k] * under.a * (1 - top.a)) / a;
    return { r: mix('r'), g: mix('g'), b: mix('b'), a };
  };
  const hex = (c) => '#' + [c.r, c.g, c.b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');
  const name = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const cls = [...el.classList].slice(0, 3);
    if (cls.length) s += '.' + cls.join('.');
    const p = el.parentElement;
    if (p && p !== document.body) {
      let ps = p.tagName.toLowerCase();
      if (p.id) ps += '#' + p.id; else if (p.classList.length) ps += '.' + p.classList[0];
      s = ps + ' > ' + s;
    }
    return s;
  };
  const text = (el) => (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 50);
  const shown = (el) => {
    if (ignore && el.closest(ignore)) return false;
    if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true, contentVisibilityAuto: true })) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const opacity = (el) => {
    let o = 1;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
    return o;
  };
  const backdrop = (el) => {
    let bg = { r: 0, g: 0, b: 0, a: 0 };
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;
      // A nested video can sit behind a sibling control group (Home carousel).
      // Its pixels supply the backdrop, not the ancestor's unused CSS fill.
      // Apply the existing media rule to visible nested media as well. Media
      // contrast still needs decoded-frame review; no limit or exception changes.
      if (e !== el) for (const media of e.querySelectorAll('img, picture, video, canvas')) {
        if (!shown(media) || media.contains(el)) continue;
        const mr = media.getBoundingClientRect(), r = el.getBoundingClientRect();
        let ml = mr.left, mt = mr.top, mw = mr.width, mh = mr.height;
        const naturalW = media.videoWidth || media.naturalWidth;
        const naturalH = media.videoHeight || media.naturalHeight;
        if (getComputedStyle(media).objectFit === 'contain' && naturalW && naturalH) {
          const scale = Math.min(mw / naturalW, mh / naturalH);
          const w = naturalW * scale, h = naturalH * scale;
          ml += (mw - w) / 2; mt += (mh - h) / 2; mw = w; mh = h;
        }
        const overlap = Math.max(0, Math.min(ml + mw, r.right) - Math.max(ml, r.left)) * Math.max(0, Math.min(mt + mh, r.bottom) - Math.max(mt, r.top));
        if (overlap >= r.width * r.height * .5) return null;
      }
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0) { bg = over(bg, c); if (bg.a >= 0.99) return bg; }
    }
    return over(bg, { r: 255, g: 255, b: 255, a: 1 });
  };
  const add = (level, rule, el, detail) => out.push({ level, rule, element: name(el), text: text(el), detail });

  // Text elements: one entry for each element that owns visible text.
  const owners = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode;
    if (!n.textContent.trim() || !n.parentElement) continue;
    const p = n.parentElement;
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(p.tagName)) continue;
    owners.add(p);
  }
  const controlSize = new Map();
  for (const el of owners) {
    if (!shown(el)) continue;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    const control = el.closest('button, a[href], [role="button"], summary, label');
    const isGlyph = /^[\s←-⇿➔-➿×+\-–—|/·•]+$/.test(el.textContent.trim());
    if (!isGlyph) {
      if (control && fs < minBtn) {
        const prev = controlSize.get(control);
        if (prev === undefined || fs < prev) controlSize.set(control, fs);
      } else if (!control && fs < minText) add('FAIL', 'G1 text size', el, `${fs}px < ${minText}px`);
    }
    if (!cs.fontFamily.includes(cfg.required_font)) add('FAIL', 'G6 font', el, cs.fontFamily);
    const o = opacity(el);
    if (o < cfg.min_element_opacity) add('FAIL', 'G5 faded text', el, `effective opacity ${o.toFixed(2)}`);
    const fg = parse(cs.color);
    const bg = backdrop(el);
    if (fg && bg) {
      const f = over(fg, bg);
      const l1 = lum(f), l2 = lum(bg);
      const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
      const bold = parseInt(cs.fontWeight, 10) >= 700;
      const large = fs >= cfg.contrast.large_px || (bold && fs >= cfg.contrast.large_bold_px);
      const need = large ? cfg.contrast.warn_below_large : cfg.contrast.warn_below_normal;
      const d = `${ratio.toFixed(2)}:1 (${hex(f)} on ${hex(bg)})`;
      if (ratio < cfg.contrast.fail_below) add('FAIL', 'G4 contrast', el, d);
      else if (ratio < need) add('WARN', 'G4 contrast', el, d);
    }
  }

  for (const [control, fs] of controlSize) add('FAIL', 'G1 button text size', control, `smallest label ${fs}px < ${minBtn}px`);

  // A fill is not seen when a photo or video covers 90% of it.
  const covered = (el, r) => {
    for (const m of el.querySelectorAll('img, video, picture, canvas')) {
      if (!shown(m)) continue;
      const q = m.getBoundingClientRect();
      const w = Math.min(r.right, q.right) - Math.max(r.left, q.left);
      const h = Math.min(r.bottom, q.bottom) - Math.max(r.top, q.top);
      if (w > 0 && h > 0 && w * h >= 0.9 * r.width * r.height) return true;
    }
    return false;
  };

  // Surfaces: dark background colours and dark gradient overlays.
  for (const el of document.querySelectorAll('body, body *')) {
    if (['IMG', 'VIDEO', 'PICTURE', 'CANVAS', 'SVG', 'svg', 'PATH', 'path', 'SOURCE', 'SCRIPT', 'STYLE'].includes(el.tagName)) continue;
    if (el.closest('svg')) continue;
    if (allowDark && el.closest(allowDark)) continue;
    if (!shown(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width * r.height < cfg.dark.min_area_px2) continue;
    const cs = getComputedStyle(el);
    const c = parse(cs.backgroundColor);
    if (c && c.a >= cfg.dark.min_alpha && lum(c) < cfg.dark.luminance_below && !covered(el, r))
      add('FAIL', 'G2 dark surface', el, `background ${hex(c)} alpha ${c.a} (${Math.round(r.width)}x${Math.round(r.height)})`);
    for (const s of ['backgroundImage', '::before', '::after']) {
      const bi = s === 'backgroundImage' ? cs.backgroundImage : getComputedStyle(el, s).backgroundImage;
      if (!bi || !bi.includes('gradient')) continue;
      if (s !== 'backgroundImage' && getComputedStyle(el, s).content === 'none') continue;
      const stops = (bi.match(/rgba?\([^)]+\)/g) || []).map(parse).filter(Boolean);
      const dark = stops.filter((k) => k.a >= cfg.dark.min_alpha && lum(k) < cfg.dark.luminance_below);
      if (dark.length) add('FAIL', 'G2 dark overlay', el, `${s === 'backgroundImage' ? '' : s + ' '}gradient with ${dark.map((k) => hex(k) + '@' + k.a).join(', ')}`);
    }
  }

  // Controls: height of buttons and links.
  for (const el of document.querySelectorAll('button, a[href], [role="button"], summary, input, select, textarea')) {
    if (!shown(el)) continue;
    if (el.tagName === 'A' && el.closest('p, li') && !el.closest('nav')) continue;
    const h = el.getBoundingClientRect().height;
    if (h < cfg.min_target_px.fail) add('FAIL', 'G3 control height', el, `${Math.round(h)}px < ${cfg.min_target_px.fail}px`);
    else if (h < cfg.min_target_px.warn) add('WARN', 'G3 control height', el, `${Math.round(h)}px < ${cfg.min_target_px.warn}px`);
  }

  // Images and page width.
  for (const img of document.images) {
    if (img.complete && img.naturalWidth === 0 && img.getAttribute('src')) add('FAIL', 'G8 broken image', img, img.getAttribute('src').slice(0, 80));
  }
  const sw = document.documentElement.scrollWidth;
  if (sw > window.innerWidth + 1) out.push({ level: 'FAIL', rule: 'G7 horizontal overflow', element: 'document', text: '', detail: `${sw}px wide in ${window.innerWidth}px` });
  return out;
}
"""


def latest_files():
    """Highest version of each component page, plus the latest combined file."""
    groups = {}
    for path in (ROOT / 'components').glob('*/*.html'):
        m = re.match(r'\d{4}-\d{2}-\d{2}-(.+)-v(\d+)\.html$', path.name)
        if not m:
            continue
        key = (path.parent.name, m.group(1))
        if key not in groups or int(m.group(2)) > groups[key][0]:
            groups[key] = (int(m.group(2)), path)
    files = sorted(p for _, p in groups.values())
    combined = [(int(m.group(1)), p) for p in SITE.glob('main-website-v*.html')
                if (m := re.match(r'main-website-v(\d+)\.html$', p.name))]
    if combined:
        files.append(max(combined)[1])
    return files


def exception_for(path, frame_id):
    """Approved exceptions (quality-guardrails.json): a whole component file or a demo frame."""
    rel = path.resolve().as_posix()
    for ex in CONFIG.get('approved_exceptions', []):
        if (frame_id and ex.get('frame') == '#' + frame_id) or (ex.get('file') and rel.endswith(ex['file'])):
            return ex
    return None


def mark_exception(items, ex):
    for item in items:
        if ex and item['level'] == 'FAIL' and item['rule'].split()[0] in ex['rules']:
            item['level'] = 'EXCEPTION'
            item['detail'] += f" (approved: {ex['name']})"
    return items


def measure_page(page, cfg, width, path=None):
    found = []
    for frame in page.frames:
        try:
            frame_id = None
            if frame != page.main_frame:
                handle = frame.frame_element()
                if not handle.is_visible():
                    continue
                frame_id = handle.get_attribute('id')
            ex = exception_for(path, frame_id) if path else None
            found += mark_exception(frame.evaluate(MEASURE, {**cfg, 'viewport': width}), ex)
        except Exception as exc:  # detached or blocked frame
            found.append({'level': 'WARN', 'rule': 'checker', 'element': frame.url[:60], 'text': '', 'detail': str(exc)[:120]})
    return found


def click_state(page, selector):
    for frame in page.frames:
        loc = frame.locator(selector)
        for i in range(loc.count()):
            # A control that is moved out of the screen on purpose (Glass 3D v04 r03: the Navbar hides on product
            # heroes) is skipped, the same as a hidden control.
            box = loc.nth(i).bounding_box() if loc.nth(i).is_visible() else None
            if box and box['y'] + box['height'] > 0:
                loc.nth(i).click()
                return True
    return False


def apply_theme(page, theme):
    """Use the demo palette switch when it exists; otherwise set data-theme on each document."""
    if page.evaluate('typeof window.ctuavPalette === "function"'):
        page.evaluate('t => window.ctuavPalette(t)', theme)
    else:
        for frame in page.frames:
            frame.evaluate('t => { document.documentElement.dataset.theme = t; if (document.body) document.body.dataset.theme = t; }', theme)
    page.wait_for_timeout(CONFIG['state_wait_ms'])


PALETTE_HEX = re.compile(r'#(f4ae52|fff4e5|f97316|a35400|e8a243|a76510|8d5c18|a9d8e8|eaf7fb|1d4ed8)', re.I)


def hardcoded_palette(path):
    """G9: accent colours must come from the shared --site-* tokens or a [data-theme] rule."""
    found = []
    if not path.name.startswith('20') or not path.parent.parent.name == 'components':
        return found
    html_text = path.read_text(encoding='utf-8')
    for href in re.findall(r'<link rel="stylesheet" href="([^"]+)"', html_text):
        css = (path.parent / href).resolve()
        if 'shared' in css.parts or not css.exists():
            continue
        for n, line in enumerate(css.read_text(encoding='utf-8').splitlines(), 1):
            if 'data-theme' in line or 'swatch' in line or 'approved' in line:
                continue
            for m in PALETTE_HEX.finditer(line):
                found.append({'level': 'WARN', 'rule': 'G9 fixed palette colour', 'element': f'{css.name}:{n}', 'text': '', 'detail': f'{m.group()} is not a palette token', 'width': 0, 'state': 'source'})
    return found


def check_file(browser, path, widths, shots):
    results = hardcoded_palette(path)
    for width in widths:
        height = 844 if width <= CONFIG['phone_max_width'] else 900
        ctx = browser.new_context(viewport={'width': width, 'height': height}, reduced_motion='reduce')
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)[:160]))
        page.on('console', lambda m: errors.append(m.text[:160]) if m.type == 'error' else None)
        runs = [(None, 'mono')] + [(s, 'mono') for s in CONFIG['states']] + [(None, t) for t in CONFIG.get('themes', ['mono'])[1:]]
        for state, theme in runs:
            page.goto(path.resolve().as_uri(), wait_until='load')
            page.wait_for_timeout(CONFIG['settle_ms'])
            label = 'default' if theme == 'mono' else 'palette-' + theme
            if theme != 'mono':
                apply_theme(page, theme)
            if state:
                if not click_state(page, state['click']):
                    continue
                label = state['name']
                page.wait_for_timeout(CONFIG['state_wait_ms'])
            for item in measure_page(page, CONFIG, width, path):
                results.append({**item, 'width': width, 'state': label})
            if shots:
                out = Path(shots) / f'{path.stem}-{width}-{label}.png'
                out.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(out), full_page=(state is None))
        for e in sorted(set(errors)):
            results.append({'level': 'FAIL', 'rule': 'G8 script error', 'element': 'console', 'text': '', 'detail': e, 'width': width, 'state': 'any'})
        ctx.close()
    return results


def group(results):
    """Merge identical findings across widths and states."""
    merged = {}
    for r in results:
        key = (r['level'], r['rule'], r['element'], r['text'], r['detail'])
        entry = merged.setdefault(key, {k: r[k] for k in ('level', 'rule', 'element', 'text', 'detail')} | {'where': []})
        where = 'source' if r['state'] == 'source' else f"{r['width']}px/{r['state']}"
        if where not in entry['where']:
            entry['where'].append(where)
    order = {'FAIL': 0, 'WARN': 1, 'EXCEPTION': 2}
    return sorted(merged.values(), key=lambda e: (order.get(e['level'], 3), e['rule'], e['element']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--full', action='store_true', help='check 5 widths instead of 3')
    ap.add_argument('--shots', help='folder for screenshots')
    ap.add_argument('--json', help='write the result to this JSON file')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')

    files = [Path(f) for f in args.files] or latest_files()
    widths = CONFIG['full_widths'] if args.full else CONFIG['widths']
    report = {'config_version': CONFIG['version'], 'widths': widths, 'files': []}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel='msedge', headless=True)
        except Exception:  # Edge is not installed (Linux, CI): use Playwright Chromium.
            browser = p.chromium.launch(headless=True)
        for path in files:
            items = group(check_file(browser, path, widths, args.shots))
            fails = sum(i['level'] == 'FAIL' for i in items)
            warns = sum(i['level'] == 'WARN' for i in items)
            excepted = sum(i['level'] == 'EXCEPTION' for i in items)
            rel = path.resolve().relative_to(ROOT) if path.resolve().is_relative_to(ROOT) else path
            report['files'].append({'file': str(rel).replace('\\', '/'), 'fail': fails, 'warn': warns, 'approved_exception': excepted, 'items': items})
            print(f'\n== {rel}  FAIL {fails}  WARN {warns}  APPROVED EXCEPTION {excepted}')
            for i in items:
                where = ', '.join(i['where'][:4]) + (' ...' if len(i['where']) > 4 else '')
                txt = f' "{i["text"]}"' if i['text'] else ''
                print(f"  {i['level']:9} {i['rule']:24} {i['element'][:60]}{txt[:40]} | {i['detail']} | {where}")
        browser.close()
    total = sum(f['fail'] for f in report['files'])
    report['total_fail'] = total
    report['total_warn'] = sum(f['warn'] for f in report['files'])
    print(f"\nTOTAL  FAIL {total}  WARN {report['total_warn']}  ({len(files)} files, widths {widths})")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
