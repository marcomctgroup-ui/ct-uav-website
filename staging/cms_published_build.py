"""Published-only CMS site generation for a later staging release.

NOT connected to build.py. It reads published stories only (Public token),
validates every representative product as publish-ready, generates into a fresh
folder below staging/checks and replaces the last good output only after full
success. On any failure the last good output stays unchanged. A missing or
unpublished product stops the build; it never returns through static content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cms_delivery

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
CHECKS = HERE / 'checks'
ROOT = CHECKS / 'cms-published'
CURRENT = ROOT / 'current'
MANIFEST = ROOT / 'manifest.json'
MAX_FILE_BYTES = 25 * 1024 * 1024
STORYBLOK_ASSETS = 'https://a.storyblok.com https://a2.storyblok.com'
# Only these sources are added to the source CSP. Nothing else is widened.
CSP_ADDITIONS = {
    'img-src': STORYBLOK_ASSETS.split(),
    'media-src': STORYBLOK_ASSETS.split(),
    'connect-src': ['https://a2.storyblok.com'],
}


class PublishedBuildError(RuntimeError):
    pass


def source_csp(headers_text):
    """Return the Content-Security-Policy of the source '/*' header rule."""
    rule = None
    for line in headers_text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line.startswith((' ', '\t')):
            rule = line.strip()
        elif rule == '/*':
            name, value = line.strip().split(':', 1)
            if name.strip().lower() == 'content-security-policy':
                return value.strip()
    raise PublishedBuildError('Source /* rule has no Content-Security-Policy')


def cms_csp(policy):
    """Add only the Storyblok asset origins; keep every other directive unchanged."""
    directives = [part.strip() for part in policy.split(';') if part.strip()]
    names = [part.split()[0].lower() for part in directives]
    missing = [name for name in CSP_ADDITIONS if name not in names]
    if missing:
        raise PublishedBuildError('Source CSP lacks directive(s): ' + ', '.join(missing))
    result = []
    for part, name in zip(directives, names):
        tokens = part.split()
        for origin in CSP_ADDITIONS.get(name, []):
            if origin not in tokens[1:]:
                tokens.append(origin)
        result.append(' '.join(tokens))
    return '; '.join(result)


def cms_csp_from_source(source):
    return cms_csp(source_csp((Path(source) / '_headers').read_text(encoding='utf-8')))


def check_published(snapshot, validate, keys):
    """Fail closed with the product name when a product cannot be published."""
    assets = {s['uuid']: s['content'] for s in snapshot['stories'] if s['content'].get('component') == 'creative_asset'}
    products = {}
    for s in snapshot['stories']:
        content = s['content']
        if content.get('component') != 'uav_product':
            continue
        name = content.get('content_id') or str(s.get('id'))
        if name in products:
            raise PublishedBuildError(f'Duplicate published product: {name}')
        if s.get('published') is False:
            raise PublishedBuildError(f'Product is not published: {name}')
        products[name] = content
    missing = sorted(set(keys) - products.keys())
    if missing:
        raise PublishedBuildError('Representative product missing or unpublished: ' + ', '.join(missing))
    unknown = sorted(products.keys() - set(keys))
    if unknown:
        raise PublishedBuildError('Published product has no approved template: ' + ', '.join(unknown))
    for name in sorted(products):
        content = products[name]
        languages = set(content.get('ready_languages') or [])
        if content.get('review_state') != 'ready':
            raise PublishedBuildError(f'Product is not ready for publication: {name}')
        if not {'en', 'vi'} <= languages:
            raise PublishedBuildError(f'Product is missing a ready language (en, vi): {name}')
        try:
            validate(content, assets, preview=False)
        except Exception as error:
            raise PublishedBuildError(f'Product failed published validation: {name}: {error}') from None
    return sorted(products)


def tree_summary(folder):
    rows = []
    for path in sorted(p for p in folder.rglob('*') if p.is_file()):
        if path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES:
            raise PublishedBuildError(f'Symlink or file above 25 MiB: {path.relative_to(folder).as_posix()}')
        rows.append(f'{path.relative_to(folder).as_posix()}\t{hashlib.sha256(path.read_bytes()).hexdigest()}')
    return {'files': len(rows), 'tree_sha256': hashlib.sha256('\n'.join(rows).encode()).hexdigest()}


def _replace(candidate, current):
    """Swap the candidate into place. Restore the previous output on failure."""
    previous = current.with_name(current.name + '.previous-' + uuid.uuid4().hex[:8])
    if current.exists():
        os.replace(current, previous)
    try:
        os.replace(candidate, current)
    except Exception:
        if previous.exists():
            os.replace(previous, current)
        raise
    if previous.exists():
        shutil.rmtree(previous)


def build(token, source, *, root=ROOT, fetch=cms_delivery.fetch_snapshot, generate=None, validate=None, keys=None):
    """Return the manifest of a successful build; raise and keep the last good output on failure."""
    root = Path(root).resolve()
    if not root.is_relative_to(CHECKS.resolve()) or root == CHECKS.resolve():
        raise PublishedBuildError('Published CMS output must be below staging/checks')
    if generate is None or validate is None or keys is None:
        import cms_generate
        import cms_site
        generate = generate or cms_site.generate
        validate = validate or cms_generate.validate
        keys = keys or cms_generate.KEYS
    current = root / 'current'
    snapshot = fetch('published', token)
    if snapshot.get('version') != 'published':
        raise PublishedBuildError('Snapshot is not a published snapshot')
    names = check_published(snapshot, validate, keys)
    csp = cms_csp_from_source(source)
    root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.candidate-', dir=root))
    try:
        snapshot_path = work / 'snapshot.json'
        snapshot_path.write_text(json.dumps(snapshot), encoding='utf-8')
        candidate = work / 'site'
        generate(snapshot_path, candidate, source)
        snapshot_path.unlink()
        if not (candidate / 'index.html').is_file():
            raise PublishedBuildError('Generated site has no index.html')
        files = tree_summary(candidate)
        manifest = {
            'mode': 'published', 'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'source': Path(source).name, 'products': names, 'csp': csp,
            'output': files, **cms_delivery.summary(snapshot),
        }
        text = json.dumps(manifest, indent=2)
        if token and token in text:
            raise PublishedBuildError('Manifest would contain a credential')
        (work / 'manifest.json').write_text(text, encoding='utf-8')
        _replace(candidate, current)
        os.replace(work / 'manifest.json', root / 'manifest.json')
        return manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=str(PROJECT / json.loads((HERE / 'config.json').read_text(encoding='utf-8'))['source']))
    args = parser.parse_args()
    token = os.environ.get('STORYBLOK_PUBLIC_TOKEN', '')
    try:
        manifest = build(token, args.source)
    except Exception as error:
        message = re.sub(r'\s+', ' ', cms_delivery.redact(error, token))
        raise SystemExit('STOP: published CMS build failed; last good output kept: ' + message)
    print(json.dumps({k: manifest[k] for k in ('products', 'output', 'cv')}))


if __name__ == '__main__':
    main()
