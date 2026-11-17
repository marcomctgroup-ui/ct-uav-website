"""Focused regression checks for CMS validation and intermediate rendering."""
import copy
import json
from pathlib import Path
import unittest

import cms_generate as cms


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parent.parent
        data = json.loads((root / 'handoff/20261112-storyblok-draft-records-v01.json').read_text(encoding='utf-8'))
        cls.assets = {a['uuid']: a['content'] for a in data['assets'].values()}
        cls.products = [r['content'] for r in data['records'] if r['content']['component'] == 'uav_product']
        cls.template = (root / 'refactor-v09/pages/decarb22.html').read_text(encoding='utf-8')

    def test_four_variants_validate_as_drafts(self):
        self.assertEqual(len(self.products), 4)
        for product in self.products:
            cms.validate(product, self.assets, preview=True)

    def test_drafts_cannot_pass_publication_gate(self):
        for product in self.products:
            with self.assertRaises(ValueError):
                cms.validate(product, self.assets, preview=False)

    def test_blank_and_duplicate_specs_rejected(self):
        p = copy.deepcopy(self.products[0])
        p['specifications'][0]['display_value'] = ' '
        with self.assertRaises(ValueError):
            cms.validate(p, self.assets, preview=True)
        p = copy.deepcopy(self.products[0])
        p['specifications'][1]['spec_key'] = p['specifications'][0]['spec_key']
        with self.assertRaises(ValueError):
            cms.validate(p, self.assets, preview=True)

    def test_vi_rows_preserved_and_legacy_fetch_removed(self):
        output = cms.render(self.template, self.products[0], self.assets, 'vi')
        self.assertIn('150+ phút', output)
        self.assertIn('cấp cm (1–3 cm)', output)
        self.assertNotIn('decarb22-storyblok-v01.js', output)

    def test_cms_text_is_escaped(self):
        p = copy.deepcopy(self.products[0])
        p['hero'][0]['description'] = '<script>alert(1)</script>'
        output = cms.render(self.template, p, self.assets, 'en')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', output)

    def test_missing_poster_and_invalid_camera_rejected(self):
        p = copy.deepcopy(self.products[0])
        a = copy.deepcopy(self.assets)
        a[p['hero'][0]['media']].pop('poster')
        with self.assertRaises(ValueError):
            cms.validate(p, a, preview=True)
        p = copy.deepcopy(next(p for p in self.products if p['presentation'] == '3d_story'))
        p['story_sections'][0]['zoom'] = 'nan'
        with self.assertRaises(ValueError):
            cms.validate(p, self.assets, preview=True)

    def test_whitespace_vi_rejected(self):
        p = copy.deepcopy(self.products[0])
        p['specifications'][0]['display_value__i18n__vi'] = '   '
        with self.assertRaises(ValueError):
            cms.validate(p, self.assets, preview=True)

    def test_poster_must_be_an_image(self):
        p = copy.deepcopy(self.products[0])
        a = copy.deepcopy(self.assets)
        media = p['hero'][0]['media']
        a[media]['poster'] = media
        with self.assertRaises(ValueError):
            cms.validate(p, a, preview=True)

    def test_image_template_cannot_silently_accept_video(self):
        root = Path(__file__).resolve().parent.parent
        template = (root / 'refactor-v09/pages/ct-crova-254.html').read_text(encoding='utf-8')
        with self.assertRaises(ValueError):
            cms.render(template, self.products[0], self.assets, 'en')

    def test_application_changes_use_cms_values(self):
        p = copy.deepcopy(self.products[0])
        p['applications_intro'] = 'CMS intro test'
        p['applications'][0]['title'] = 'CMS feature test'
        output = cms.render(self.template, p, self.assets, 'en')
        self.assertIn('CMS intro test', output)
        self.assertIn('CMS feature test', output)

    def test_four_templates_render_both_languages(self):
        root = Path(__file__).resolve().parent.parent
        for product in self.products:
            template = (root / 'refactor-v09/pages' / (product['content_id'] + '.html')).read_text(encoding='utf-8')
            for language in ('en', 'vi'):
                output = cms.render(template, product, self.assets, language)
                self.assertIn('https://a.storyblok.com/f/', output)
                self.assertNotIn('decarb22-storyblok-v01.js', output)

    def test_chapter_text_and_camera_use_cms_values(self):
        root = Path(__file__).resolve().parent.parent
        p = copy.deepcopy(next(p for p in self.products if p['presentation'] == '3d_story'))
        chapter = p['story_sections'][0]
        chapter['body']['content'][0]['content'][0]['text'] = 'CMS chapter text'
        chapter['azimuth'] = '123'
        template = (root / 'refactor-v09/pages' / (p['content_id'] + '.html')).read_text(encoding='utf-8')
        output = cms.render(template, p, self.assets, 'en')
        self.assertIn('CMS chapter text', output)
        self.assertIn('data-ps-cam="123,', output)
        chapter['body']['content'].pop()
        with self.assertRaises(ValueError):
            cms.render(template, p, self.assets, 'en')

    def test_technology_changes_and_missing_targets(self):
        p = copy.deepcopy(self.products[0])
        p['_resolved_technologies'] = [{'title': 'CMS technology', 'summary': 'CMS list item'}]
        output = cms.render(self.template, p, self.assets, 'en')
        self.assertIn('CMS technology', output)
        self.assertIn('<li>CMS list item</li>', output)
        with self.assertRaises(ValueError):
            cms.render(self.template.replace('technology-title', 'absent-target'), p, self.assets, 'en')


if __name__ == '__main__':
    unittest.main()
