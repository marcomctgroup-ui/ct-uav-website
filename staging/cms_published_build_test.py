"""Tests for cms_published_build. Mocked delivery and generation; no network."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import cms_published_build as pb

TOKEN = 'test-only-public-token-ABC'
KEYS = {'decarb22', 'decarb54'}
SOURCE = pb.PROJECT / json.loads((pb.HERE / 'config.json').read_text(encoding='utf-8'))['source']


def product(name, **extra):
    content = {'component': 'uav_product', 'content_id': name, 'review_state': 'ready', 'ready_languages': ['en', 'vi']}
    content.update(extra)
    return {'id': hash(name) % 1000, 'uuid': 'u-' + name, 'published_at': '2026-11-17T00:00:00Z', 'content': content}


def snapshot(*stories):
    return {'version': 'published', 'cv': 42, 'stories': list(stories)}


def fake_generate(snapshot_path, output, source):
    data = json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    output = Path(output)
    (output / 'pages').mkdir(parents=True)
    (output / 'index.html').write_text('<html>' + str(len(data['stories'])) + '</html>', encoding='utf-8')
    for s in data['stories']:
        if s['content']['component'] == 'uav_product':
            (output / 'pages' / (s['content']['content_id'] + '.html')).write_text('p', encoding='utf-8')


def failing_generate(snapshot_path, output, source):
    Path(output).mkdir(parents=True)
    (Path(output) / 'index.html').write_text('partial', encoding='utf-8')
    raise ValueError('template slot missing')


def ok_validate(content, assets, *, preview):
    assert preview is False


class PublishedBuildTest(unittest.TestCase):
    def setUp(self):
        pb.CHECKS.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='test-published-', dir=pb.CHECKS))
        self.addCleanup(shutil.rmtree, self.root, True)

    def run_build(self, snap, generate=fake_generate, validate=ok_validate):
        return pb.build(TOKEN, SOURCE, root=self.root, fetch=lambda version, token: snap,
                        generate=generate, validate=validate, keys=KEYS)

    def good(self):
        return self.run_build(snapshot(product('decarb22'), product('decarb54')))

    def assert_last_good_kept(self, before):
        self.assertEqual((self.root / 'current/index.html').read_text(encoding='utf-8'), before)
        self.assertEqual([p.name for p in self.root.iterdir() if p.name.startswith('.')], [])

    def test_success_writes_output_and_manifest_without_token(self):
        manifest = self.good()
        self.assertTrue((self.root / 'current/pages/decarb22.html').is_file())
        self.assertEqual(manifest['products'], ['decarb22', 'decarb54'])
        self.assertEqual(manifest['cv'], 42)
        self.assertEqual(manifest['output']['files'], 3)
        text = (self.root / 'manifest.json').read_text(encoding='utf-8')
        self.assertNotIn(TOKEN, text)
        self.assertNotIn('"content"', text)
        self.assertFalse((self.root / 'current/snapshot.json').exists())

    def test_second_success_replaces_output(self):
        self.good()
        self.run_build(snapshot(product('decarb22'), product('decarb54'), {'id': 5, 'uuid': 'a', 'content': {'component': 'creative_asset'}}))
        self.assertEqual((self.root / 'current/index.html').read_text(encoding='utf-8'), '<html>3</html>')

    def test_unpublished_product_fails_closed_and_keeps_last_good(self):
        self.good()
        before = (self.root / 'current/index.html').read_text(encoding='utf-8')
        manifest_before = (self.root / 'manifest.json').read_text(encoding='utf-8')
        with self.assertRaisesRegex(pb.PublishedBuildError, 'missing or unpublished: decarb54'):
            self.run_build(snapshot(product('decarb22')))
        self.assert_last_good_kept(before)
        self.assertEqual((self.root / 'manifest.json').read_text(encoding='utf-8'), manifest_before)

    def test_not_ready_product_names_product(self):
        self.good()
        before = (self.root / 'current/index.html').read_text(encoding='utf-8')
        with self.assertRaisesRegex(pb.PublishedBuildError, 'not ready for publication: decarb54'):
            self.run_build(snapshot(product('decarb22'), product('decarb54', review_state='draft')))
        with self.assertRaisesRegex(pb.PublishedBuildError, 'missing a ready language.*decarb22'):
            self.run_build(snapshot(product('decarb22', ready_languages=['en']), product('decarb54')))
        self.assert_last_good_kept(before)

    def test_validation_error_names_product(self):
        def bad_validate(content, assets, *, preview):
            if content['content_id'] == 'decarb22':
                raise ValueError('Invalid hero')
        with self.assertRaisesRegex(pb.PublishedBuildError, 'decarb22: Invalid hero'):
            self.run_build(snapshot(product('decarb22'), product('decarb54')), validate=bad_validate)
        self.assertFalse((self.root / 'current').exists())

    def test_generation_error_keeps_last_good(self):
        self.good()
        before = (self.root / 'current/index.html').read_text(encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'template slot missing'):
            self.run_build(snapshot(product('decarb22'), product('decarb54')), generate=failing_generate)
        self.assert_last_good_kept(before)

    def test_real_validate_refuses_unreviewed(self):
        import cms_generate
        with self.assertRaisesRegex(pb.PublishedBuildError, 'not ready'):
            pb.check_published(snapshot(product('decarb22', review_state='draft')), cms_generate.validate, {'decarb22'})

    def test_output_must_stay_below_checks(self):
        with self.assertRaises(pb.PublishedBuildError):
            pb.build(TOKEN, SOURCE, root=pb.HERE / 'dist', fetch=lambda v, t: snapshot(), generate=fake_generate,
                     validate=ok_validate, keys=KEYS)

    def test_cms_csp_adds_only_storyblok_asset_origins(self):
        source = pb.source_csp((SOURCE / '_headers').read_text(encoding='utf-8'))
        result = pb.cms_csp(source)
        before = {d.split()[0]: d.split()[1:] for d in source.split('; ')}
        after = {d.split()[0]: d.split()[1:] for d in result.split('; ')}
        self.assertEqual(list(before), list(after))
        for name in before:
            added = [t for t in after[name] if t not in before[name]]
            self.assertEqual(after[name][:len(before[name])], before[name])
            expected = {'img-src': ['https://a.storyblok.com', 'https://a2.storyblok.com'],
                        'media-src': ['https://a.storyblok.com', 'https://a2.storyblok.com'],
                        'connect-src': ['https://a2.storyblok.com']}.get(name, [])
            self.assertEqual(added, expected, name)
        self.assertEqual(pb.cms_csp(result), result)

    def test_cms_csp_requires_directives(self):
        with self.assertRaises(pb.PublishedBuildError):
            pb.cms_csp("default-src 'self'; img-src 'self'")


if __name__ == '__main__':
    unittest.main()
