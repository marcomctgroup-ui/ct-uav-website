"""Tests for cms_preview_build and the build.py worker bundler / preview hook.

No network and no pip: delivery, generation and installation are mocked.
One integration case runs the real cms_site.generate on a saved read-back.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build
import cms_preview_build as cp

TOKEN = 'test-only-preview-token-QWE789'
SOURCE = build.SOURCE
READBACK = cp.HERE.parent / 'handoff/20261117-storyblok-card-fields-readback-v01.json'


def stub_generate(snapshot_path, output, source):
    output = Path(output)
    for relative, text in {
        'index.html': '<!doctype html><html><head><meta charset="utf-8"></head><body><a href="/products/x/">x</a></body></html>',
        'pages/decarb22.html': '<html>\r\n<head></head>\r\n<body><img srcset="/assets/a.png 1x, b.png 2x"></body>\r\n</html>',
        'products/decarb-22/index.html': '<html><head><base href="../../"/></head><body><script>fetch("/api/cms/decarb22")</script></body></html>',
        'source-code/readable.html': '<html><head></head><body></body></html>',
        'assets/js/cms-fields.js': 'var a=1;',
        'assets/js/cms-product-3d-0123456789ab.js': 'var b="/assets/models/x.glb";',
        'assets/js/main.js': 'var c=1;',
        'assets/img/x.png': 'png',
    }.items():
        (output / relative).parent.mkdir(parents=True, exist_ok=True)
        (output / relative).write_bytes(text.encode())


def draft(stories=None):
    return {'version': 'draft', 'cv': 7, 'stories': stories or [
        {'id': 1, 'uuid': 'a', 'updated_at': '2026-11-17T01:00:00Z',
         'content': {'component': 'uav_product', 'content_id': 'decarb22', 'title': 'Draft words'}}]}


class PreviewCase(unittest.TestCase):
    def setUp(self):
        cp.CHECKS.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(prefix='test-preview-', dir=cp.CHECKS))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.dist = self.tmp / 'dist'
        self.dist.mkdir()
        (self.dist / 'index.html').write_text('public', encoding='utf-8')
        self.bridge = self.tmp / 'cms_bridge.js'
        self.bridge.write_text('/* readable */\nwindow.previewBridge = function () { return 1; };\n', encoding='utf-8')
        patcher = mock.patch.object(cp, 'BRIDGE', self.bridge)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_preview(self, **overrides):
        options = dict(fetch=lambda version, token: draft(), generate=stub_generate,
                       validate=lambda c, a, *, preview: None, work=self.tmp / 'work',
                       manifest_path=self.tmp / 'manifest.json', deps=lambda: 'installed')
        options.update(overrides)
        return cp.build_preview(self.dist, TOKEN, SOURCE, **options)

    def public_unchanged(self):
        self.assertEqual(sorted(p.name for p in self.dist.iterdir() if p.name != 'cms-preview'), ['index.html'])
        self.assertEqual((self.dist / 'index.html').read_text(encoding='utf-8'), 'public')


class PreviewBuildTest(PreviewCase):
    def test_success_copies_only_html_and_cms_scripts(self):
        manifest = self.run_preview()
        root = self.dist / 'cms-preview'
        files = sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file())
        self.assertEqual(files, ['assets/js/cms-bridge.js', 'assets/js/cms-fields.js',
                                 'assets/js/cms-product-3d-0123456789ab.js', 'index.html',
                                 'pages/decarb22.html', 'products/decarb-22/index.html'])
        self.assertNotIn('readable', (root / 'assets/js/cms-bridge.js').read_text(encoding='utf-8'))
        index = (root / 'index.html').read_text(encoding='utf-8')
        self.assertIn(cp.ROBOTS_META, index)
        self.assertIn('<script src="assets/js/cms-bridge.js"></script></body>', index)
        page = (root / 'pages/decarb22.html').read_bytes()
        self.assertIn(b'<script src="../assets/js/cms-bridge.js"></script></body>', page)
        self.assertIn(b'\r\n', page)  # original line endings kept
        shell = (root / 'products/decarb-22/index.html').read_text(encoding='utf-8')
        self.assertIn('<script src="assets/js/cms-bridge.js"></script>', shell)
        text = (self.tmp / 'manifest.json').read_text(encoding='utf-8')
        self.assertNotIn(TOKEN, text)
        self.assertNotIn('Draft words', text)
        self.assertEqual(manifest['stories'][0]['updated_at'], '2026-11-17T01:00:00Z')
        urls = {(f['file'], f['url']) for f in manifest['root_absolute_urls']}
        self.assertIn(('index.html', '/products/x/'), urls)
        self.assertIn(('pages/decarb22.html', '/assets/a.png'), urls)
        self.assertIn(('products/decarb-22/index.html', '/api/cms/decarb22'), urls)
        self.assertIn(('assets/js/cms-product-3d-0123456789ab.js', '/assets/models/x.glb'), urls)
        self.assertFalse((self.tmp / 'work').exists())

    def test_generation_error_leaves_no_preview(self):
        def broken(snapshot_path, output, source):
            stub_generate(snapshot_path, output, source)
            raise ValueError('slot missing')
        with self.assertRaises(ValueError):
            self.run_preview(generate=broken)
        self.public_unchanged()
        self.assertFalse((self.tmp / 'work').exists())

    def test_validation_and_fetch_errors_leave_no_preview(self):
        def invalid(content, assets, *, preview):
            assert preview is True
            raise ValueError('Invalid hero')
        with self.assertRaises(ValueError):
            self.run_preview(validate=invalid)
        def offline(version, token):
            raise cp.cms_delivery.DeliveryError('Storyblok CDN request failed: timed out')
        with self.assertRaises(cp.cms_delivery.DeliveryError):
            self.run_preview(fetch=offline)
        self.public_unchanged()

    def test_published_snapshot_is_refused(self):
        with self.assertRaises(cp.PreviewSkip):
            self.run_preview(fetch=lambda v, t: {'version': 'published', 'stories': []})
        self.public_unchanged()

    def test_size_limit_fails_preview_only(self):
        with mock.patch.object(cp, 'MAX_FILE_BYTES', 10):
            with self.assertRaisesRegex(cp.PreviewSkip, '25 MiB'):
                self.run_preview()
        self.public_unchanged()

    def test_missing_bridge_or_worker_skips(self):
        with mock.patch.object(cp, 'BRIDGE', self.tmp / 'absent.js'):
            with self.assertRaisesRegex(cp.PreviewSkip, 'cms_bridge.js'):
                self.run_preview()
        with mock.patch.object(cp, 'WORKER_MODULE', self.tmp / 'absent.js'):
            with self.assertRaisesRegex(cp.PreviewSkip, 'cms_preview.js'):
                self.run_preview()
        self.public_unchanged()

    def test_warning_line_is_redacted_single_line(self):
        line = cp.warning_line(RuntimeError(f'bad\nhttps://x/?token={TOKEN}&a=1 {TOKEN}'), TOKEN)
        self.assertNotIn(TOKEN, line)
        self.assertNotIn('\n', line)
        self.assertTrue(line.startswith('WARNING:'))


class InjectTest(unittest.TestCase):
    def test_paths_and_meta(self):
        self.assertEqual(cp.bridge_src('index.html', '<head>'), 'assets/js/cms-bridge.js')
        self.assertEqual(cp.bridge_src('pages/a.html', '<head>'), '../assets/js/cms-bridge.js')
        self.assertEqual(cp.bridge_src('products/a/index.html', '<base href="../../">'), 'assets/js/cms-bridge.js')
        self.assertEqual(cp.bridge_src('news/index.html', '<base href="../"/>'), 'assets/js/cms-bridge.js')
        self.assertEqual(cp.bridge_src('news/index.html', '<head>'), '../assets/js/cms-bridge.js')
        html = cp.inject('index.html', '<html><head lang="en"><meta name="robots" content="noindex"></head><body></body></html>')
        self.assertEqual(html.count('name="robots"'), 1)
        for bad in ('<html><body></body></html>', '<head></head><body></body></body>', '<head><base href="/x/"></head><body></body>'):
            with self.assertRaises(cp.PreviewSkip):
                cp.inject('index.html', bad)


class DependencyTest(unittest.TestCase):
    def test_installed_packages_are_used(self):
        self.assertEqual(cp.ensure_dependencies(run=lambda *a, **k: self.fail('pip must not run')), 'installed')

    def test_missing_packages_install_into_target_or_skip(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            raise subprocess.CalledProcessError(1, command)
        real = cp.importlib.import_module
        def missing(name, *args):
            if name in ('bs4', 'rjsmin'):
                raise ImportError(name)
            return real(name, *args)
        target = cp.CHECKS / 'pydeps-test-absent'
        path_before = list(sys.path)
        try:
            with mock.patch.object(cp.importlib, 'import_module', missing):
                with self.assertRaisesRegex(cp.PreviewSkip, 'could not be installed'):
                    cp.ensure_dependencies(run=run, target=target)
                with self.assertRaisesRegex(cp.PreviewSkip, 'not importable'):
                    cp.ensure_dependencies(run=lambda *a, **k: None, target=target)
        finally:
            sys.path[:] = path_before
        command = calls[0]
        self.assertEqual(command[1:4], ['-m', 'pip', 'install'])
        self.assertEqual(command[command.index('--target') + 1], str(target))
        self.assertEqual(command[command.index('-r') + 1], str(cp.REQUIREMENTS))


class BuildHookTest(PreviewCase):
    def test_no_token_does_nothing(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('STORYBLOK_PREVIEW_TOKEN', None)
            result = build.build_preview(self.dist, SOURCE)
        self.assertEqual(result['status'], 'skipped')
        self.status_only()
        self.public_unchanged()

    def status_only(self):
        # A failed or skipped preview leaves only the gated status file.
        files = [p.name for p in (self.dist / 'cms-preview').iterdir()]
        self.assertEqual(files, ['_build-status.json'])
        text = (self.dist / 'cms-preview' / '_build-status.json').read_text(encoding='utf-8')
        self.assertNotIn(TOKEN, text)
        return json.loads(text)

    def test_failure_prints_one_redacted_warning(self):
        def explode(dist, token, source):
            (Path(dist) / 'cms-preview').mkdir()
            raise RuntimeError(f'network down for token={token}')
        out = io.StringIO()
        with mock.patch.dict(os.environ, {'STORYBLOK_PREVIEW_TOKEN': TOKEN}), \
                mock.patch.object(cp, 'build_preview', explode), contextlib.redirect_stdout(out):
            result = build.build_preview(self.dist, SOURCE)
        self.assertEqual(result['status'], 'skipped')
        self.assertIn('REDACTED', self.status_only()['reason'])
        self.assertEqual(len(out.getvalue().strip().splitlines()), 1)
        self.assertNotIn(TOKEN, out.getvalue())
        self.public_unchanged()


STUBS = {
    'voice-worker.js': "export default {\n  async fetch(){return new Response('voice');}\n};\n",
    'cms_published.js': "export async function readPublishedPilot(){return new Response('pilot');}\n",
    'cms_preview_auth.js': "export async function verifyStoryblokPreview(){return true;}\n",
    'cms_preview.js': "import {verifyStoryblokPreview} from './cms_preview_auth.js';\nexport async function servePreview(r){return new Response(String(await verifyStoryblokPreview(r)));}\n",
    'cms_worker.js': ("import voiceWorker from './voice-worker.js';\nimport {readPublishedPilot} from './cms_published.js';\n"
                      "import {servePreview} from './cms_preview.js';\nexport default {async fetch(request,env,ctx){\n"
                      "  const p=new URL(request.url).pathname;\n  if(p==='/api/cms/decarb22')return readPublishedPilot(request,env);\n"
                      "  if(p.startsWith('/cms-preview'))return servePreview(request,env);\n  return voiceWorker.fetch(request,env,ctx);\n}};\n"),
}


class BundleTest(unittest.TestCase):
    def folder(self, files):
        folder = Path(tempfile.mkdtemp(prefix='bundle-', dir=cp.CHECKS))
        self.addCleanup(shutil.rmtree, folder, True)
        for name, text in files.items():
            (folder / name).write_text(text, encoding='utf-8', newline='\r\n' if name == 'voice-worker.js' else '\n')
        return folder

    def test_full_bundle_order_and_runtime(self):
        folder = self.folder(STUBS)
        bundle, modules = build.bundle_worker(folder)
        self.assertEqual(modules, build.WORKER_MODULES)
        self.assertNotIn('import ', bundle)
        self.assertNotIn('\r', bundle)
        positions = [bundle.index(marker) for marker in ('const voiceWorker = {', 'readPublishedPilot(){',
                                                          'verifyStoryblokPreview(){', 'servePreview(r)', 'export default {async fetch')]
        self.assertEqual(positions, sorted(positions))
        node = shutil.which('node')
        if node:
            (folder / 'bundle.mjs').write_text(bundle, encoding='utf-8')
            script = ("const m=await import(process.argv[1]);const f=async p=>(await m.default.fetch(new Request('https://x'+p),{},{})).text();"
                      "console.log([await f('/api/cms/decarb22'),await f('/cms-preview/'),await f('/api/transcribe')].join(','));")
            result = subprocess.run([node, '--input-type=module', '-e', script, (folder / 'bundle.mjs').as_uri()],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.stdout.strip(), 'pilot,true,voice', result.stderr)

    def test_without_preview_module_matches_previous_bundle(self):
        files = {k: v for k, v in STUBS.items() if k not in ('cms_preview.js',)}
        files['cms_worker.js'] = "import voiceWorker from './voice-worker.js';\nimport {readPublishedPilot} from './cms_published.js';\nexport default {};\n"
        folder = self.folder(files)
        bundle, modules = build.bundle_worker(folder)
        self.assertEqual(modules, ['voice-worker.js', 'cms_published.js', 'cms_worker.js'])
        voice = STUBS['voice-worker.js'].replace('export default {', 'const voiceWorker = {')
        self.assertEqual(bundle, voice + '\n' + STUBS['cms_published.js'] + '\n' + 'export default {};\n')

    def test_unknown_or_leftover_imports_stop(self):
        for name, text in {
            'cms_worker.js': "import x from './other.js';\nexport default {};\n",
            'cms_published.js': "import {y} from 'npm-package';\nexport async function readPublishedPilot(){}\n",
            'cms_preview.js': "export async function servePreview(){return import('./late.js');}\n",
        }.items():
            files = dict(STUBS, **{name: text})
            with self.assertRaises(SystemExit, msg=name):
                build.bundle_worker(self.folder(files))
        files = dict(STUBS, **{'cms_preview_auth.js': "import {servePreview} from './cms_preview.js';\n"})
        with self.assertRaises(SystemExit):
            build.bundle_worker(self.folder(files))

    def test_repository_modules_bundle(self):
        bundle, modules = build.bundle_worker()
        self.assertIn('cms_worker.js', modules)
        self.assertEqual(bundle.count('const voiceWorker = {'), 1)


@unittest.skipUnless(READBACK.is_file(), 'saved read-back snapshot is absent')
class IntegrationTest(PreviewCase):
    """Real cms_site.generate on the saved 17 November read-back (local file, no network)."""
    def test_real_generation(self):
        data = json.loads(READBACK.read_text(encoding='utf-8'))
        snapshot = {'version': 'draft', 'cv': None, 'stories': data['stories']}
        manifest = self.run_preview(fetch=lambda v, t: snapshot, generate=None, validate=None)
        root = self.dist / 'cms-preview'
        html = [p for p in root.rglob('*.html')]
        self.assertGreater(len(html), 10)
        for path in html:
            text = path.read_text(encoding='utf-8')
            self.assertEqual(text.count('cms-bridge.js'), 1, path)
            self.assertIn('noindex', text)
        self.assertFalse((root / 'source-code').exists())
        print('\nintegration preview files:', len(manifest['files']),
              'root-absolute findings:', len(manifest['root_absolute_urls']),
              sorted({f['url'] for f in manifest['root_absolute_urls']})[:40])


if __name__ == '__main__':
    unittest.main()
