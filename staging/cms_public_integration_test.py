"""Published build switch and real template integration. No service writes/network."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build
import cms_published_build as pb


class PublicIntegrationTests(unittest.TestCase):
    def test_default_is_static_without_credentials_or_generation(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(build.public_source(build.SOURCE), (build.SOURCE, {'mode': 'static'}))

    def test_bad_setting_or_missing_public_token_stops(self):
        for env, message in [({'STORYBLOK_PUBLISHED_BUILD': 'yes'}, 'must be 0 or 1'),
                             ({'STORYBLOK_PUBLISHED_BUILD': '1', 'STORYBLOK_PREVIEW_TOKEN': 'fixture-private'}, 'requires STORYBLOK_PUBLIC_TOKEN')]:
            with patch.dict('os.environ', env, clear=True), self.assertRaisesRegex(SystemExit, message):
                build.public_source(build.SOURCE)

    def test_enabled_selects_published_output(self):
        with patch.dict('os.environ', {'STORYBLOK_PUBLISHED_BUILD': '1', 'STORYBLOK_PUBLIC_TOKEN': 'fixture-public'}, clear=True), \
             patch('cms_preview_build.ensure_dependencies'), \
             patch.object(pb, 'build', return_value={'products': ['decarb22'], 'cv': 42}) as generate:
            source, status = build.public_source(build.SOURCE)
        generate.assert_called_once_with('fixture-public', build.SOURCE)
        self.assertEqual(source, pb.CURRENT)
        self.assertEqual(status, {'mode': 'published', 'products': ['decarb22'], 'cv': 42})

    def test_failure_stops_without_private_token_fallback(self):
        with patch.dict('os.environ', {'STORYBLOK_PUBLISHED_BUILD': '1', 'STORYBLOK_PUBLIC_TOKEN': 'fixture-public'}, clear=True), \
             patch('cms_preview_build.ensure_dependencies'), \
             patch.object(pb, 'build', side_effect=ValueError('failed token=fixture-public')):
            with self.assertRaises(SystemExit) as error:
                build.public_source(build.SOURCE)
        self.assertIn('last good site', str(error.exception))
        self.assertNotIn('fixture-public', str(error.exception))

    def test_real_four_product_generation_and_recovery(self):
        # Fixture readiness is a test condition, not content approval/publication.
        snapshot = json.loads((build.PROJECT / 'handoff/20261113-storyblok-candidate-records-v01.json').read_text(encoding='utf-8'))
        snapshot['version'] = 'published'
        snapshot['cv'] = 42
        for story in snapshot['stories']:
            if story['content']['component'] in {'uav_product', 'creative_asset', 'technology'}:
                story['published'] = True
                story['content'].update(review_state='ready', ready_languages=['en', 'vi'])
        pb.CHECKS.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix='test-public-integration-', dir=pb.CHECKS))
        self.addCleanup(shutil.rmtree, root, True)
        manifest = pb.build('fixture-public', build.SOURCE, root=root, fetch=lambda version, token: copy.deepcopy(snapshot))
        self.assertEqual(len(manifest['products']), 4)
        current = root / 'current'
        for product in manifest['products']:
            text = (current / 'pages' / (product + '.html')).read_text(encoding='utf-8')
            self.assertIn('data-cms-vi=', text)
            self.assertNotIn('decarb22-storyblok', text)
            self.assertNotIn('cms-bridge.js', text)
        self.assertEqual((current / 'sitemap.xml').read_bytes(), (build.SOURCE / 'sitemap.xml').read_bytes())
        before = pb.tree_summary(current)
        snapshot['stories'] = [s for s in snapshot['stories'] if s['content'].get('content_id') != 'decarb54']
        with self.assertRaisesRegex(pb.PublishedBuildError, 'missing or unpublished'):
            pb.build('fixture-public', build.SOURCE, root=root, fetch=lambda version, token: snapshot)
        self.assertEqual(pb.tree_summary(current), before)


if __name__ == '__main__':
    unittest.main()
