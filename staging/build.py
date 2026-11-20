"""Build the Cloudflare Pages staging output. Never changes the selected source."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
SOURCE = (PROJECT / json.loads((HERE / 'config.json').read_text(encoding='utf-8'))['source']).resolve()
OUTPUT = HERE / 'dist'
ALLOWED = {'assets', 'pages', 'about', 'applications', 'components', 'contact', 'news', 'partnerships', 'products'}
# Root files copied when the selected version has them (404.html gives a real HTTP 404 on Cloudflare Pages).
ROOT_FILES = {'index.html', '404.html', 'sitemap.xml'}
IMMUTABLE = 'public, max-age=31536000, immutable'
# Worker modules in bundle order. Each one may import only earlier modules.
WORKER_MODULES = ['voice-worker.js', 'cms_published.js', 'cms_preview_auth.js', 'cms_preview.js', 'cms_worker.js']
LOCAL_IMPORT = re.compile(r"^import\s+(.+?)\s+from\s+'\./([\w.-]+\.js)';[ \t]*\n", re.M)


def parse_headers(text):
    rules = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line.startswith((' ', '\t')):
            rules.append((line.strip(), {}))
        else:
            name, value = line.strip().split(':', 1)
            rules[-1][1][name] = value.strip()
    return rules


def content_hashed(path):
    data = path.read_bytes()
    tokens = re.findall(r'(?<![0-9a-f])[0-9a-f]{10,64}(?![0-9a-f])', path.name)
    return any(hashlib.new(algorithm, data).hexdigest().startswith(token)
               for token in tokens for algorithm in ('sha256', 'sha1', 'md5'))


def matches_header_path(path, pattern):
    """Cloudflare Pages supports one splat; no fnmatch character classes."""
    if pattern.count('*') > 1 or any(char in pattern for char in '[]?'):
        raise ValueError('Unsupported Cloudflare header path pattern: ' + pattern)
    if '*' not in pattern:
        return path == pattern
    prefix, suffix = pattern.split('*')
    return path.startswith(prefix) and path.endswith(suffix) and len(path) >= len(prefix) + len(suffix)


def compact_patterns(paths, selected):
    """Group only patterns whose existing files all have the selected policy."""
    result = []

    def visit(prefix, candidates):
        wanted = candidates & selected
        if not wanted:
            return
        if candidates <= selected:
            result.append(prefix if len(candidates) == 1 and prefix in candidates else prefix + '*')
            return
        if prefix in candidates:
            if prefix in selected:
                result.append(prefix)
            candidates = candidates - {prefix}
        for char in sorted({path[len(prefix)] for path in candidates}):
            visit(prefix + char, {path for path in candidates if path.startswith(prefix + char)})

    visit('/assets/', set(paths))
    candidates = {pattern: {path for path in paths if fnmatch.fnmatchcase(path, pattern)}
                  for pattern in result}
    # Suffix groups distinguish original images from responsive derivatives.
    # Every candidate is checked against the complete asset inventory.
    for folder in sorted({path.rsplit('/', 1)[0] for path in paths}):
        group = {path for path in paths if path.rsplit('/', 1)[0] == folder}
        reversed_paths = {'/assets/' + path.rsplit('/', 1)[1][::-1]: path for path in group}
        reversed_selected = {path for path, original in reversed_paths.items() if original in selected}
        reversed_result = []

        def suffix_visit(prefix, items):
            wanted = items & reversed_selected
            if not wanted:
                return
            if items <= reversed_selected:
                tail = prefix.removeprefix('/assets/')
                pattern = folder + '/*' + tail[::-1]
                matches = {path for path in paths if matches_header_path(path, pattern)}
                if matches and matches <= selected:
                    reversed_result.append((pattern, matches))
                return
            items = items - {prefix}
            for char in sorted({path[len(prefix)] for path in items}):
                suffix_visit(prefix + char, {path for path in items if path.startswith(prefix + char)})

        suffix_visit('/assets/', set(reversed_paths))
        candidates.update(reversed_result)
    # Choose disjoint groups: Cloudflare joins duplicate matching header values.
    remaining = set(selected)
    result = []
    while remaining:
        eligible = [(pattern, matches) for pattern, matches in candidates.items() if matches and matches <= remaining]
        if not eligible:
            result.extend(sorted(remaining))
            break
        pattern, matches = max(eligible, key=lambda item: (len(item[1]), -len(item[0]), item[0]))
        result.append(pattern)
        remaining -= matches
    return result


def bundle_worker(folder=HERE):
    """Concatenate the local worker modules reached from cms_worker.js.

    Returns (bundle, modules). Stops on any import that is not a known local module.
    """
    folder = Path(folder)
    texts, reached, pending = {}, set(), ['cms_worker.js']
    while pending:
        name = pending.pop()
        if name in reached:
            continue
        if not (folder / name).is_file():
            raise SystemExit('STOP: worker module is missing: ' + name)
        reached.add(name)
        texts[name] = (folder / name).read_text(encoding='utf-8')
        for binding, target in LOCAL_IMPORT.findall(texts[name]):
            if target not in WORKER_MODULES or WORKER_MODULES.index(target) >= WORKER_MODULES.index(name):
                raise SystemExit(f'STOP: unsupported worker import of {target} in {name}')
            if target == 'voice-worker.js' and binding != 'voiceWorker':
                raise SystemExit('STOP: voice worker must be imported as voiceWorker.')
            pending.append(target)
    reached.add('voice-worker.js')
    if 'voice-worker.js' not in texts:
        texts['voice-worker.js'] = (folder / 'voice-worker.js').read_text(encoding='utf-8')
    if texts['voice-worker.js'].count('export default {') != 1:
        raise SystemExit('STOP: voice worker export changed; review the CMS bundle.')
    texts['voice-worker.js'] = texts['voice-worker.js'].replace('export default {', 'const voiceWorker = {')
    modules = [name for name in WORKER_MODULES if name in reached]
    parts = []
    for name in modules:
        text = LOCAL_IMPORT.sub('', texts[name])
        if re.search(r"""^\s*import[\s{*'"]|\bimport\s*\(|^\s*export\s+(\*|\{[^}]*\}\s*from)""", text, re.M):
            raise SystemExit('STOP: unresolved import remains in worker module ' + name)
        if name != 'cms_worker.js' and re.search(r'^\s*export\s+default\b', text, re.M):
            raise SystemExit('STOP: unexpected default export in worker module ' + name)
        parts.append(text)
    return '\n'.join(parts), modules


def write_preview_status(target, status):
    """Status for operators, served only behind the /cms-preview/ worker gate.

    It holds no token, no content and no URL with credentials.
    """
    status = dict(status, commit=os.environ.get('CF_PAGES_COMMIT_SHA', '')[:12])
    target.mkdir(parents=True, exist_ok=True)
    (target / '_build-status.json').write_text(json.dumps(status), encoding='utf-8', newline='\n')
    return status


def build_preview(output, source):
    """Optional protected draft preview. Any failure leaves the public output unchanged."""
    token = os.environ.get('STORYBLOK_PREVIEW_TOKEN', '')
    target = output / 'cms-preview'
    if not token:
        return write_preview_status(target, {'status': 'skipped', 'reason': 'STORYBLOK_PREVIEW_TOKEN is not available during the build'})
    try:
        import cms_preview_build
    except Exception as error:  # the module itself is optional
        shutil.rmtree(target, ignore_errors=True)
        line = re.sub(r'\s+', ' ', 'WARNING: CMS draft preview skipped; public output unchanged. '
                      + type(error).__name__).replace(token, 'REDACTED')
        print(line)
        return write_preview_status(target, {'status': 'skipped', 'reason': line})
    try:
        manifest = cms_preview_build.build_preview(output, token, source)
    except BaseException as error:
        shutil.rmtree(target, ignore_errors=True)
        if isinstance(error, KeyboardInterrupt):
            raise
        line = cms_preview_build.warning_line(error, token)
        print(line)
        return write_preview_status(target, {'status': 'skipped', 'reason': line.replace(token, 'REDACTED')})
    print(f'CMS draft preview built: {len(manifest["files"])} files below /cms-preview/.')
    return write_preview_status(target, {'status': 'built', 'files': len(manifest['files'])})


def public_source(source):
    """Explicit opt-in. A failed published build must never serve static fallback."""
    mode = os.environ.get('STORYBLOK_PUBLISHED_BUILD', '0')
    if mode == '0':
        return source, {'mode': 'static'}
    if mode != '1':
        raise SystemExit('STOP: STORYBLOK_PUBLISHED_BUILD must be 0 or 1.')
    token = os.environ.get('STORYBLOK_PUBLIC_TOKEN', '')
    if not token.strip():
        raise SystemExit('STOP: published CMS build requires STORYBLOK_PUBLIC_TOKEN.')
    try:
        from cms_preview_build import ensure_dependencies
        ensure_dependencies()
        import cms_published_build
        manifest = cms_published_build.build(token, source)
    except Exception as error:
        import cms_delivery
        message = re.sub(r'\s+', ' ', cms_delivery.redact(error, token))
        raise SystemExit('STOP: published CMS build failed; deployment must keep the last good site: ' + message) from None
    return cms_published_build.CURRENT, {
        'mode': 'published', 'products': manifest['products'], 'cv': manifest['cv']}


def main():
    if SOURCE.parent != PROJECT or not (SOURCE / 'index.html').is_file():
        raise SystemExit('STOP: source must be a website version directly inside main-website.')
    source, cms_public = public_source(SOURCE)
    files = sorted(p for p in source.rglob('*') if p.is_file() and
                   (p.relative_to(source).parts[0] in ALLOWED or p.relative_to(source).as_posix() in ROOT_FILES))
    if any(p.is_symlink() or p.stat().st_size > 25 * 1024 * 1024 for p in files):
        raise SystemExit('STOP: symlink or file above the Cloudflare Pages 25 MiB limit.')
    unresolved = [p.relative_to(source).as_posix() for p in files
                  if p.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1')]
    if unresolved:
        raise SystemExit('STOP: Git LFS media is not downloaded: ' + ', '.join(unresolved))
    if (source / 'index.html').stat().st_size >= 500_000:
        raise SystemExit('STOP: entry HTML is above the project size budget.')
    original_rules = parse_headers((source / '_headers').read_text(encoding='utf-8'))
    security = next(headers for path, headers in original_rules if path == '/*')
    assets = {'/' + p.relative_to(source).as_posix(): p for p in files if p.relative_to(source).parts[0] == 'assets'}
    selected = {path for path, headers in original_rules if headers.get('Cache-Control') == IMMUTABLE}
    if not selected <= assets.keys() or any(not content_hashed(assets[path]) for path in selected):
        raise SystemExit('STOP: an immutable asset is missing or its filename hash does not match its bytes.')
    # Keep every existing HTML cache rule. Compact only immutable asset paths.
    cache_rules = [(path, headers) for path, headers in original_rules
                   if 'Cache-Control' in headers and headers['Cache-Control'] != IMMUTABLE]
    patterns = compact_patterns(assets, selected)
    for path in assets:
        matches = sum(matches_header_path(path, pattern) for pattern in patterns)
        if matches != int(path in selected):
            raise SystemExit(f'STOP: cache policy changed for {path}')
    rules = [('/*', security)] + cache_rules + [(pattern, {'Cache-Control': IMMUTABLE}) for pattern in patterns]
    lines = ['# Generated staging headers. Source security and cache policies are retained.', '']
    for path, headers in rules:
        lines += [path] + [f'  {name}: {value}' for name, value in headers.items()] + ['']
    if len(rules) > 100 or max(map(len, lines)) > 2000:
        raise SystemExit('STOP: Cloudflare Pages header limits exceeded.')
    # The only recursive removal is the fixed, generated staging output below.
    if OUTPUT.is_symlink() or OUTPUT.resolve() != HERE / 'dist' or OUTPUT.parent.resolve() != HERE:
        raise SystemExit('STOP: generated output path is outside the staging folder.')
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()
    manifest = []
    for path in files:
        relative = path.relative_to(source)
        destination = OUTPUT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise SystemExit(f'STOP: byte mismatch for {relative}')
        manifest.append({'path': relative.as_posix(), 'bytes': path.stat().st_size, 'sha256': digest})
    (OUTPUT / '_headers').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    (OUTPUT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8', newline='\n')
    # Advanced-mode worker is server code; only the API path invokes it.
    worker, modules = bundle_worker(HERE)
    (OUTPUT / '_worker.js').write_text(worker, encoding='utf-8', newline='\n')
    include = ['/api/transcribe', '/api/cms/decarb22']
    if 'cms_preview.js' in modules:
        include += ['/cms-preview', '/cms-preview/*']
    (OUTPUT / '_routes.json').write_text(json.dumps({
        'version': 1, 'include': include, 'exclude': []
    }), encoding='utf-8')
    report = {'source': SOURCE.name, 'files_copied': len(manifest), 'source_bytes_unchanged': True,
              'entry_bytes': (source / 'index.html').stat().st_size, 'cms_public': cms_public,
              'total_bytes': sum(item['bytes'] for item in manifest), 'header_rules': len(rules),
              'immutable_assets': len(selected), 'cache_policy_differences': 0,
              'generated_files': ['_headers', 'robots.txt', '_worker.js', '_routes.json'], 'files': manifest}
    # Draft preview only after the public output is complete, and only if the
    # protected worker route is bundled. Without the token nothing changes.
    preview = build_preview(OUTPUT, SOURCE) if 'cms_preview.js' in modules else None
    if preview is None and os.environ.get('STORYBLOK_PREVIEW_TOKEN'):
        print('WARNING: CMS draft preview skipped; public output unchanged. cms_preview.js is not bundled.')
    if preview is not None:
        report['cms_preview'] = preview
    (HERE / 'checks').mkdir(exist_ok=True)
    (HERE / 'checks/build-manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'files'}, indent=2))


if __name__ == '__main__':
    main()
