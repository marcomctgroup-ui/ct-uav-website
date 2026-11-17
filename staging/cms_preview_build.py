"""Draft preview build for the protected Storyblok Visual Editor route.

build.py calls build_preview() only after the public output is complete and
only when STORYBLOK_PREVIEW_TOKEN is set. The protected Worker (cms_preview.js)
serves dist/cms-preview/. Any failure removes the partial preview; the public
output never changes. The token is never logged or written to a file.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import cms_delivery

HERE = Path(__file__).resolve().parent
CHECKS = HERE / 'checks'
WORK = CHECKS / 'cms-preview-build'
PYDEPS = CHECKS / 'pydeps'
REQUIREMENTS = HERE / 'cms-requirements.txt'
BRIDGE = HERE / 'cms_bridge.js'
WORKER_MODULE = HERE / 'cms_preview.js'
MANIFEST = CHECKS / 'cms-preview-manifest.json'
PREFIX = 'cms-preview'
BRIDGE_PATH = 'assets/js/cms-bridge.js'
MAX_FILE_BYTES = 25 * 1024 * 1024
# Top-level folders that hold route shells and page documents.
HTML_FOLDERS = {'pages', 'about', 'applications', 'components', 'contact', 'news', 'partnerships', 'products'}
CMS_SCRIPTS = re.compile(r'^assets/js/(cms-fields\.js|cms-product-3d-[0-9a-f]{12}\.js)$')
ROBOTS_META = '<meta name="robots" content="noindex, nofollow">'


class PreviewSkip(RuntimeError):
    """The preview is skipped. The message is safe to print."""


def ensure_dependencies(run=subprocess.run, target=PYDEPS):
    """Import bs4 and rjsmin; else install the pinned set into staging/checks/pydeps."""
    def importable():
        try:
            importlib.invalidate_caches()
            importlib.import_module('bs4')
            importlib.import_module('rjsmin')
            return True
        except ImportError:
            return False
    if importable():
        return 'installed'
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    if importable():
        return 'cached'
    try:
        # Wheels only (no package build scripts), and no CMS credential in the
        # installer environment.
        clean_env = {k: v for k, v in os.environ.items() if not k.upper().startswith('STORYBLOK')}
        run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input',
             '--quiet', '--only-binary=:all:', '--target', str(target), '-r', str(REQUIREMENTS)],
            check=True, timeout=300, capture_output=True, env=clean_env)
    except Exception as error:
        raise PreviewSkip(f'CMS dependencies could not be installed ({type(error).__name__})') from None
    if not importable():
        raise PreviewSkip('CMS dependencies are not importable after installation')
    return 'pip-target'


def base_folder(relative, html):
    folder = posixpath.dirname(relative)
    match = re.search(r'<base\s[^>]*href\s*=\s*["\']([^"\']*)["\']', html, re.I)
    if match:
        href = match.group(1)
        if href.startswith(('/', 'http:', 'https:', '//')):
            raise PreviewSkip(f'Absolute base href in {relative}')
        folder = posixpath.normpath(posixpath.join(folder, href))
        if folder.startswith('..'):
            raise PreviewSkip(f'Base href leaves the site root in {relative}')
    return '' if folder == '.' else folder


def bridge_src(relative, html):
    return posixpath.relpath(BRIDGE_PATH, base_folder(relative, html) or '.')


def inject(relative, html):
    """Add the robots meta and the bridge script tag. Plain text insertion keeps other bytes."""
    if len(re.findall(r'</body\s*>', html, re.I)) != 1 or len(re.findall(r'<head(\s[^>]*)?>', html, re.I)) != 1:
        raise PreviewSkip(f'Cannot place the preview tags in {relative}')
    if 'cms-bridge.js' in html:
        raise PreviewSkip(f'Bridge script already present in {relative}')
    head = re.search(r'<head(\s[^>]*)?>', html, re.I)
    if not re.search(r'<meta[^>]+name=["\']robots["\'][^>]*noindex', html, re.I):
        html = html[:head.end()] + ROBOTS_META + html[head.end():]
    tag = f'<script src="{bridge_src(relative, html)}"></script>'
    end = re.search(r'</body\s*>', html, re.I)
    return html[:end.start()] + tag + html[end.start():]


ATTRIBUTE_URL = re.compile(r'\s(href|src|action|poster|formaction|data-[\w-]+)\s*=\s*["\'](/(?!/)[^"\']*)["\']', re.I)
SRCSET = re.compile(r'\s(?:srcset|imagesrcset)\s*=\s*["\']([^"\']*)["\']', re.I)
CSS_URL = re.compile(r'url\(\s*["\']?(/(?!/)[^)"\']*)', re.I)
SCRIPT_BLOCK = re.compile(r'<script\b[^>]*>(.*?)</script>', re.I | re.S)
SCRIPT_LITERAL = re.compile(r'["\'`](/(?!/)[A-Za-z_][^"\'`\s]*)["\'`]')


def root_absolute(relative, text, is_script=False):
    """List root-absolute URLs that would leave /cms-preview/. Report only; no rewrite."""
    found = []
    if is_script:
        found += [('script-literal', url) for url in SCRIPT_LITERAL.findall(text)]
        return [(relative, kind, url) for kind, url in found]
    found += [(name.lower(), url) for name, url in ATTRIBUTE_URL.findall(text)]
    for value in SRCSET.findall(text):
        found += [('srcset', part.split()[0]) for part in value.split(',')
                  if part.strip().startswith('/') and not part.strip().startswith('//')]
    found += [('css-url', url) for url in CSS_URL.findall(text)]
    for block in SCRIPT_BLOCK.findall(text):
        found += [('inline-script', url) for url in SCRIPT_LITERAL.findall(block)]
    return [(relative, kind, url) for kind, url in found]


def select_files(site):
    html, scripts = [], []
    for path in sorted(p for p in site.rglob('*') if p.is_file()):
        relative = path.relative_to(site).as_posix()
        top = relative.split('/', 1)[0]
        if relative == 'index.html' or (path.suffix == '.html' and top in HTML_FOLDERS):
            html.append(relative)
        elif CMS_SCRIPTS.match(relative):
            scripts.append(relative)
    if 'index.html' not in html or 'assets/js/cms-fields.js' not in scripts:
        raise PreviewSkip('Generated preview is incomplete')
    return html, scripts


def stage(site, staging, bridge_minified):
    html, scripts = select_files(site)
    findings = []
    for relative in html:
        text = (site / relative).read_bytes().decode('utf-8')
        findings += root_absolute(relative, text)
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(inject(relative, text), encoding='utf-8', newline='')
    for relative in scripts:
        findings += root_absolute(relative, (site / relative).read_text(encoding='utf-8'), is_script=True)
        (staging / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(site / relative, staging / relative)
    (staging / BRIDGE_PATH).parent.mkdir(parents=True, exist_ok=True)
    (staging / BRIDGE_PATH).write_text(bridge_minified, encoding='utf-8', newline='\n')
    rows = []
    for path in sorted(p for p in staging.rglob('*') if p.is_file()):
        if path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES:
            raise PreviewSkip('Preview file above the Cloudflare Pages 25 MiB limit: ' + path.relative_to(staging).as_posix())
        rows.append({'path': path.relative_to(staging).as_posix(), 'bytes': path.stat().st_size,
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return rows, findings


def build_preview(dist, token, source, *, fetch=cms_delivery.fetch_snapshot, generate=None,
                  validate=None, work=WORK, manifest_path=MANIFEST, deps=ensure_dependencies):
    """Build dist/cms-preview/ from draft content. Raise on failure; never leaves a partial preview."""
    dist = Path(dist)
    target = dist / PREFIX
    if target.exists():
        raise PreviewSkip('dist/cms-preview already exists before the preview build')
    if not WORKER_MODULE.is_file():
        raise PreviewSkip('cms_preview.js is absent; draft content would not be protected')
    if not BRIDGE.is_file():
        raise PreviewSkip('cms_bridge.js is absent')
    dependency_mode = deps()
    from rjsmin import jsmin
    if generate is None or validate is None:
        import cms_generate
        import cms_site
        generate = generate or cms_site.generate
        validate = validate or cms_generate.validate
    bridge = jsmin(BRIDGE.read_text(encoding='utf-8'))
    snapshot = fetch('draft', token)
    if snapshot.get('version') != 'draft':
        raise PreviewSkip('Snapshot is not a draft snapshot')
    assets = {s['uuid']: s['content'] for s in snapshot['stories'] if s['content'].get('component') == 'creative_asset'}
    for story in snapshot['stories']:
        if story['content'].get('component') == 'uav_product':
            validate(story['content'], assets, preview=True)
    work = Path(work).resolve()
    if not work.is_relative_to(CHECKS.resolve()) or work == CHECKS.resolve():
        raise PreviewSkip('Preview work folder must be below staging/checks')
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        snapshot_path = work / 'snapshot.json'
        snapshot_path.write_text(json.dumps(snapshot), encoding='utf-8')
        try:
            generate(snapshot_path, work / 'site', source)
        finally:
            # Draft content stays only in the generated pages, not in a snapshot file.
            snapshot_path.unlink(missing_ok=True)
        staging = work / 'stage'
        staging.mkdir()
        rows, findings = stage(work / 'site', staging, bridge)
        # Same filesystem: a rename publishes the complete preview at once.
        os.replace(staging, target)
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    manifest = {
        'mode': 'draft-preview', 'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'source': Path(source).name, 'dependencies': dependency_mode, 'output_prefix': '/' + PREFIX + '/',
        'files': rows, 'root_absolute_urls': [
            {'file': f, 'kind': k, 'url': u} for f, k, u in findings],
        **cms_delivery.summary(snapshot),
    }
    text = json.dumps(manifest, indent=2)
    if token and token in text:
        shutil.rmtree(target, ignore_errors=True)
        raise PreviewSkip('Preview manifest would contain a credential')
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(text, encoding='utf-8')
    return manifest


def warning_line(error, token):
    """One redacted line for the build log."""
    message = cms_delivery.redact(f'{type(error).__name__}: {error}', token)
    return 'WARNING: CMS draft preview skipped; public output unchanged. ' + re.sub(r'\s+', ' ', message)[:400]
