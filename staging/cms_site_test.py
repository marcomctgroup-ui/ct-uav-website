"""Regression tests for draft content mapping and shared field ownership."""
import copy
import json
import re
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
import cms_site as cms

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / json.loads((ROOT / 'staging/config.json').read_text(encoding='utf-8'))['source']

class CmsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / 'handoff/20261113-storyblok-candidate-records-v01.json').read_text(encoding='utf-8'))
        cls.products = [x['content'] for x in data['stories'] if x['content']['component'] == 'uav_product']
        cls.assets = {x['uuid']: x['content'] for x in data['stories'] if x['content']['component'] == 'creative_asset'}
        cls.tech = {x['uuid']: x['content'] for x in data['stories'] if x['content']['component'] == 'technology'}
    def render(self, product):
        template = (SOURCE / 'pages' / (product['content_id'] + '.html')).read_text(encoding='utf-8')
        return BeautifulSoup(cms.render(template, product, self.assets, self.tech, {}), 'html.parser')
    def test_all_variants_preserve_sections_and_bilingual_fields(self):
        for product in self.products:
            result = self.render(product)
            original = BeautifulSoup((SOURCE / 'pages' / (product['content_id'] + '.html')).read_text(encoding='utf-8'), 'html.parser')
            self.assertEqual([x.get('class') for x in result.select('main > section')], [x.get('class') for x in original.select('main > section')])
            self.assertEqual(len(result.select('#specifications tbody tr')), len(product['specifications']))
            self.assertTrue(all(n.get('data-cms-vi', '').strip() for n in result.select('[data-cms-en]')))
            self.assertIsNone(result.select_one('script[src*="decarb22-storyblok"]'))
    def test_spec_edit_updates_metric_without_duplicate_value(self):
        p = copy.deepcopy(self.products[0]); key = p['metrics'][0]['spec_key']
        row = next(r for r in p['specifications'] if r['spec_key'] == key)
        row['display_value'] = '987 km'; row['display_value__i18n__vi'] = '987 km'
        s = self.render(p)
        self.assertEqual(s.select_one('.metric strong').get_text(), '987 km')
        self.assertIn('987 km', s.select_one('#specifications tbody').get_text())
    def test_gallery_reorders_captions_and_keeps_variants_on_same_image(self):
        p = copy.deepcopy(self.products[0]); p['gallery'].reverse()
        p['gallery'][0]['caption_override'] = 'Edited caption'; p['gallery'][0]['caption_override__i18n__vi'] = 'VI caption'
        s = self.render(p); first = s.select_one('.gallery-grid figure')
        self.assertEqual(first.figcaption.span.get_text(), 'Edited caption')
        self.assertTrue(first.img['srcset'].startswith(first.img['src'] + '/m/'))
    def test_missing_vi_and_bad_asset_origin_fail(self):
        p = copy.deepcopy(self.products[0]); p['payload_options'][0]['description__i18n__vi'] = ''
        with self.assertRaises(ValueError): self.render(p)
        with self.assertRaises(ValueError): cms.asset_url({'file': {'filename': 'https://a.storyblok.com.evil.test/f/a'}})
    def test_no_load_metric_preserves_condition(self):
        p = next(p for p in self.products if p['content_id'] == 'ct-crova-254')
        metric = p['metrics'][1]; row = next(r for r in p['specifications'] if r['spec_key'] == metric['spec_key'])
        self.assertEqual(cms.metric_value(row, metric, 'en'), '45 minutes')
        self.assertNotIn('20', cms.metric_value(row, metric, 'en'))
    def test_missing_vi_chapter_cannot_fall_back_to_english(self):
        p = copy.deepcopy(next(p for p in self.products if p['presentation'] == '3d_story'))
        p['story_sections'][0].pop('body__i18n__vi')
        with self.assertRaises(ValueError): self.render(p)
    def test_chapter_wrappers_do_not_inherit_unit_span_rules(self):
        p = next(p for p in self.products if p['presentation'] == '3d_story')
        s = self.render(p)
        self.assertTrue(s.select('article.ps-chapter cms-text[data-cms-en]'))
        self.assertFalse(s.select('article.ps-chapter span[data-cms-en]'))
    def test_model_and_video_remain_deferred(self):
        for p in self.products:
            s = self.render(p)
            for video in s.select('#overview video'):
                self.assertFalse(video.get('src')); self.assertEqual(video['preload'], 'none')
            for script in s.select('script[data-deferred-3d]'):
                self.assertFalse(script.get('src'))
    def test_private_output_cannot_target_release(self):
        with self.assertRaises(ValueError):
            cms.generate(ROOT / 'handoff/20261113-storyblok-candidate-records-v01.json', ROOT / 'staging/dist', SOURCE)

    def test_model_view_settings_and_poster_are_bound(self):
        p = copy.deepcopy(next(p for p in self.products if p.get('model')))
        p['model'][0]['scale'] = '1.25'; p['model'][0]['front_degrees'] = '37'
        s = self.render(p); stage = s.select_one('[data-ps-stage]')
        self.assertEqual(stage['data-cms-model-scale'], '1.25')
        self.assertEqual(stage['data-cms-model-front'], '37.0')
        self.assertEqual(stage.select_one('.ps-fallback')['src'], cms.asset_url(self.assets[p['model'][0]['poster']]))
        p['model'][0]['front_degrees'] = 'NaN'
        with self.assertRaises(ValueError): self.render(p)

    def test_no_model_fallback_keeps_chapters_without_3d_loader(self):
        p = copy.deepcopy(next(p for p in self.products if p.get('model')))
        p['model'] = []
        s = self.render(p)
        self.assertIsNotNone(s.select_one('[data-cms-static-story]'))
        self.assertTrue(s.select('article.ps-chapter[data-cms-fallback-src]'))
        self.assertFalse(s.select('script[data-deferred-3d]'))
        self.assertFalse(s.select_one('.ps-fallback').has_attr('hidden'))
        self.assertTrue(all('is-in' in n['class'] for n in s.select('.ps-reveal')))

    def test_literal_spec_value_unit_fallback_and_missing_translation(self):
        p = copy.deepcopy(self.products[0]); row = p['specifications'][0]
        row.pop('display_value'); row.pop('display_value__i18n__vi')
        row['value'] = '12.5'; row['unit'] = 'kg'
        self.assertEqual(cms.legacy.specification_value(row, 'vi'), '12.5 kg')
        self.assertIn('12.5 kg', self.render(p).select_one('#specifications').get_text())
        row['display_value'] = '12.5 kg'
        with self.assertRaises(ValueError): self.render(p)

    def test_gallery_uses_reusable_asset_caption_without_override(self):
        p = copy.deepcopy(self.products[0]); placement = p['gallery'][0]
        placement.pop('caption_override'); placement.pop('caption_override__i18n__vi')
        assets = copy.deepcopy(self.assets)
        assets[placement['asset']]['caption'] = 'Shared caption'
        assets[placement['asset']]['caption__i18n__vi'] = 'Shared VI caption'
        template = (SOURCE / 'pages' / (p['content_id'] + '.html')).read_text(encoding='utf-8')
        s = BeautifulSoup(cms.render(template, p, assets, self.tech, {}), 'html.parser')
        self.assertEqual(s.select_one('.gallery-grid figcaption span').get_text(), 'Shared caption')

    def test_cdn_origin_and_canonical_route_are_strict(self):
        self.assertEqual(cms.asset_url({'file':{'filename':'https://a2.storyblok.com/f/123/model.glb'}}), 'https://a2.storyblok.com/f/123/model.glb')
        self.assertEqual(cms.asset_url({'media_type':'model','file':{'filename':'https://a.storyblok.com/f/123/model.glb'}}), 'https://a2.storyblok.com/f/123/model.glb')
        for url in ['http://a.storyblok.com/f/a', 'https://a.storyblok.com.evil.test/f/a', 'https://a2.storyblok.com/f/a?token=x']:
            with self.assertRaises(ValueError): cms.asset_url({'file':{'filename':url}})
        p = copy.deepcopy(self.products[0]);p['route']='/products/changed/'
        with self.assertRaises(ValueError): self.render(p)

    def test_chapter_references_follow_spec_edits_without_changing_source_copy(self):
        from cms_reference_refresh import prepare
        data = json.loads((ROOT / 'handoff/20261116-storyblok-resume-before-v01.json').read_text(encoding='utf-8'))
        candidate = prepare(data)
        p = copy.deepcopy(next(s['content'] for s in candidate['stories'] if s['content'].get('content_id')=='decarb54'))
        p['specifications'][1]['display_value']='9 kg'; p['specifications'][1]['display_value__i18n__vi']='9 kg'
        s = self.render(p)
        self.assertEqual(s.select('article.ps-chapter')[0].select('[data-cms-en]')[2]['data-cms-en'], '9')
        self.assertIn('9 kg', s.select_one('#specifications tbody').get_text())
        ref=p['story_sections'][0]['specification_keys'][0]
        ref['paragraph_index']='1'
        self.assertIn('9', self.render(p).select('article.ps-chapter')[0].get_text())
        ref['paragraph_index']=True
        with self.assertRaises(ValueError): self.render(p)

    def test_conditional_chapter_references_keep_no_load_and_full_load_separate(self):
        from cms_reference_refresh import prepare
        from cms_spec_refs import chapter_values
        data=json.loads((ROOT / 'handoff/20261116-storyblok-resume-before-v01.json').read_text(encoding='utf-8'))
        p=next(s['content'] for s in prepare(data)['stories'] if s['content'].get('content_id')=='ct-pegas-230')
        rows={r['spec_key']:r for r in p['specifications']}
        rows['spec-004']['display_value']='No load: 46 minutes; Full load: 19 minutes'
        values=chapter_values(p['story_sections'][2],rows,'en')
        self.assertEqual(values[5],'46 minutes');self.assertEqual(values[7],'19 minutes')
        rows['spec-004']['display_value']='46 minutes'
        with self.assertRaises(ValueError): chapter_values(p['story_sections'][2],rows,'en')

    def test_shared_cards_follow_cms_identity_but_keep_template_labels(self):
        p = copy.deepcopy(next(p for p in self.products if p['content_id'] == 'decarb54'))
        p['title'] = 'DECARB 54 Edited'; p['summary'] = 'Edited summary'; p['summary__i18n__vi'] = 'VI summary'
        line = BeautifulSoup((SOURCE / 'pages/line-05.html').read_text(encoding='utf-8'), 'html.parser')
        self.assertTrue(cms.bind_shared_cards(line, p))
        card = line.select_one('[data-cart-id="uav:decarb54"]').find_parent(class_='pl-model')
        self.assertEqual(card.h3.get_text(), 'DECARB 54 Edited')
        self.assertEqual(card.img['alt'], 'DECARB 54 Edited')
        self.assertEqual(card.select_one('[data-cart-id]')['data-cart-name'], 'DECARB 54 Edited')
        other = line.select_one('[data-cart-id="uav:decarb22"]').find_parent(class_='pl-model')
        self.assertEqual(other.h3.get_text().strip(), 'DECARB 22')
        home = BeautifulSoup((SOURCE / 'pages/hero.html').read_text(encoding='utf-8'), 'html.parser')
        eyebrow = home.select_one('[data-route="decarb54"]').find_parent(class_='slide-copy').select_one('.eyebrow').get_text()
        cms.bind_shared_cards(home, p, json.loads((SOURCE / 'assets/i18n/vi.json').read_text(encoding='utf-8')))
        slide = home.select_one('[data-route="decarb54"]').find_parent(class_='slide-copy')
        self.assertEqual(slide.select_one('.descriptor')['data-cms-vi'], 'VI summary')
        self.assertEqual(slide.select_one('[data-route]')['data-product'], 'DECARB 54 Edited')
        self.assertEqual(slide.select_one('.eyebrow').get_text(), eyebrow)

    def test_home_grid_slider_and_siblings_follow_identity_only(self):
        p = copy.deepcopy(next(p for p in self.products if p['content_id'] == 'decarb54'))
        p['title'] = 'DECARB 54 Edited'
        vi = json.loads((SOURCE / 'assets/i18n/vi.json').read_text(encoding='utf-8'))
        shell = BeautifulSoup((SOURCE / 'index.html').read_text(encoding='utf-8'), 'html.parser')
        before = shell.select_one('a.hp-card[data-route="decarb54"]')
        src, tagline = before.img['src'], before.select_one('.hp-tagline').get_text()
        self.assertTrue(cms.bind_shared_cards(shell, p, vi))
        card = shell.select_one('a.hp-card[data-route="decarb54"]')
        self.assertEqual(card.select_one('.hp-title').get_text(), 'DECARB 54 Edited')
        self.assertEqual(card.img['alt'], 'DECARB 54 Edited')
        self.assertEqual((card.img['src'], card.select_one('.hp-tagline').get_text()), (src, tagline))
        self.assertEqual(shell.select_one('a.hp-card[data-route="decarb22"] .hp-title').get_text().strip(), 'DECARB 22')
        home = BeautifulSoup((SOURCE / 'pages/hero.html').read_text(encoding='utf-8'), 'html.parser')
        cms.bind_shared_cards(home, p, vi)
        choice = home.select('.slide-choice')[1]
        self.assertEqual(choice.select_one('.slide-label').get_text(), 'DECARB 54 Edited')
        self.assertEqual((choice['data-cms-aria-en'], choice['data-cms-aria-vi']), ('Show DECARB 54 Edited', 'Xem DECARB 54 Edited'))
        self.assertEqual(home.select('.slide-choice')[0]['aria-label'], 'Show DECARB 22')
        self.assertTrue(choice.has_attr('data-i18n-skip'))
        with self.assertRaises(ValueError): cms.bind_shared_cards(BeautifulSoup((SOURCE / 'pages/hero.html').read_text(encoding='utf-8'), 'html.parser'), p, {})
    def test_contextual_alt_and_crova_siblings_are_preserved(self):
        p = copy.deepcopy(next(p for p in self.products if p['content_id'] == 'ct-crova-254')); p['title'] = 'CROVA Edited'
        line = BeautifulSoup((SOURCE / 'pages/line-09.html').read_text(encoding='utf-8'), 'html.parser')
        card = line.select_one('[data-cart-id="uav:ct-crova-254"]').find_parent(class_='pl-model')
        card.img['alt'] = 'Spraying over rice fields'
        cms.bind_shared_cards(line, p)
        self.assertEqual(card.img['alt'], 'Spraying over rice fields')
        self.assertEqual(card.h3.get_text(), 'CROVA Edited')
        for other in ('ct-crova-124', 'ct-crova-256'):
            self.assertEqual(line.select_one('[data-cart-id="uav:' + other + '"]')['data-cart-name'], other.upper().replace('CT-CROVA-', 'CT-CROVA '))

    def test_home_card_tagline_and_figures_follow_cms(self):
        data = json.loads((ROOT / 'handoff/20261117-storyblok-card-fields-readback-v01.json').read_text(encoding='utf-8'))
        products = {x['content']['content_id']: x['content'] for x in data['stories'] if x['content']['component'] == 'uav_product'}
        original = BeautifulSoup((SOURCE / 'index.html').read_text(encoding='utf-8'), 'html.parser')
        shell = BeautifulSoup((SOURCE / 'index.html').read_text(encoding='utf-8'), 'html.parser')
        for key in ('decarb22', 'decarb54', 'ct-pegas-230'):
            cms.bind_shared_cards(shell, products[key])
            new, old = (x.select_one('a.hp-card[data-route="' + key + '"]') for x in (shell, original))
            self.assertEqual(' '.join(new.get_text(' ').split()), ' '.join(old.get_text(' ').split()))
            self.assertEqual(new.select_one('.hp-tagline')['data-cms-vi'] != '', True)
        figures = shell.select_one('a.hp-card[data-route="decarb22"] .hp-figures')
        self.assertEqual([b['data-cms-vi'] for b in figures.select('b')], ['200 km', '400–500 ha', '2 kg'])
        self.assertEqual(figures.select_one('b small').get_text(), 'km')
        self.assertIsNone(shell.select_one('a.hp-card[data-route="decarb54"] .hp-figures'))
        p = copy.deepcopy(products['decarb22'])
        next(r for r in p['specifications'] if r['spec_key'] == 'spec-003')['display_value'] = '250 km'
        p['card_tagline'] = ''; p['card_tagline__i18n__vi'] = ''
        edited = BeautifulSoup((SOURCE / 'index.html').read_text(encoding='utf-8'), 'html.parser')
        cms.bind_shared_cards(edited, p)
        card = edited.select_one('a.hp-card[data-route="decarb22"]')
        self.assertEqual(card.select_one('.hp-figures b')['data-cms-en'], '250 km')
        self.assertIsNone(card.select_one('.hp-tagline'))
        p = copy.deepcopy(products['decarb54']); p['card_metrics'] = copy.deepcopy(products['decarb22']['card_metrics'])
        cms.bind_shared_cards(edited, p)
        added = edited.select_one('a.hp-card[data-route="decarb54"] .hp-figures')
        self.assertEqual([b['data-cms-en'] for b in added.select('b')], ['200 km', '~50 ha', '5 kg'])
        self.assertEqual(added.find_next_sibling()['class'], ['hp-more'])
        p['card_tagline__i18n__vi'] = ''
        with self.assertRaises(ValueError): cms.bind_shared_cards(BeautifulSoup((SOURCE / 'index.html').read_text(encoding='utf-8'), 'html.parser'), p)

class CmsMappingTests(unittest.TestCase):
    """Remaining field mappings and the Visual Editor path contract (17 Nov snapshot)."""
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / 'handoff/20261117-storyblok-card-fields-readback-v01.json').read_text(encoding='utf-8'))
        cls.products = {x['content']['content_id']: x['content'] for x in data['stories'] if x['content']['component'] == 'uav_product'}
        cls.assets = {x['uuid']: x['content'] for x in data['stories'] if x['content']['component'] == 'creative_asset'}
        cls.tech = {x['uuid']: x['content'] for x in data['stories'] if x['content']['component'] == 'technology'}
        cls.stories = dict(cls.products)
        cls.stories.update({'asset:' + k: v for k, v in cls.assets.items()})
        cls.stories.update({'technology:' + k: v for k, v in cls.tech.items()})
        cls.vi = json.loads((SOURCE / 'assets/i18n/vi.json').read_text(encoding='utf-8'))
    def template(self, key):
        return (SOURCE / 'pages' / (key + '.html')).read_text(encoding='utf-8')
    def render(self, product):
        return BeautifulSoup(cms.render(self.template(product['content_id']), product, self.assets, self.tech, self.vi), 'html.parser')
    def product(self, key):
        return copy.deepcopy(self.products[key])
    def fails(self, product, text='layout decision'):
        with self.assertRaises(ValueError) as caught: self.render(product)
        self.assertIn(text, str(caught.exception))

    def test_sharing_image_fails_closed_with_layout_decision(self):
        uuid = next(iter(self.assets))
        for key in ('sharing_image', 'share_image'):
            p = self.product('decarb22'); p['seo'][0][key] = uuid
            self.fails(p, 'og:image')

    def test_hero_action_maps_to_existing_in_page_link_slot(self):
        p = self.product('ct-crova-254')
        action = {'component': 'action', 'key': 'view-specs', 'label': 'View specifications',
                  'label__i18n__vi': self.vi['View specifications'], 'behaviour': 'navigate',
                  'destination': {'url': '#specifications', 'linktype': 'url', 'fieldtype': 'multilink'}}
        p['hero'][0]['actions'] = [action]
        link = self.render(p).select_one('.hero-actions a.hero-cta')
        original = BeautifulSoup(self.template('ct-crova-254'), 'html.parser').select_one('.hero-actions a.hero-cta')
        self.assertEqual(link.get_text(), original.get_text())
        self.assertEqual(link['href'], '#specifications')
        text = link.select_one('cms-text')
        self.assertEqual((text['data-cms-path'], text['data-cms-vi']), ('hero.0.actions.0.label', 'Xem thông số kỹ thuật'))
        self.assertIsNotNone(link.select_one('span[aria-hidden]'))
        action['label'] = 'Edited'; action['label__i18n__vi'] = 'VI edited'
        self.assertEqual(self.render(p).select_one('.hero-cta cms-text').get_text(), 'Edited')
        for change in ({'behaviour': 'enquiry'}, {'destination': {'url': '/contact/', 'linktype': 'url'}},
                       {'destination': {'url': '#missing-section', 'linktype': 'url'}},
                       {'destination': {'url': 'javascript:alert(1)', 'linktype': 'url'}}):
            bad = copy.deepcopy(p); bad['hero'][0]['actions'][0].update(change); self.fails(bad)
        bad = copy.deepcopy(p); bad['hero'][0]['actions'].append(copy.deepcopy(action)); self.fails(bad)
        bad = copy.deepcopy(p); bad['hero'][0]['actions'][0]['label__i18n__vi'] = ''; self.fails(bad, 'EN and VI')
        video = self.product('decarb22'); video['hero'][0]['actions'] = [copy.deepcopy(action)]
        self.fails(video, '0 hero link slot')

    def test_feature_figures_and_contextual_media_fail_closed(self):
        p = self.product('ct-crova-254')
        p['applications'][1]['specification_keys'] = [{'component': 'spec_reference', 'spec_key': p['specifications'][0]['spec_key']}]
        self.fails(p, 'no figure slot')
        p = self.product('ct-crova-254'); images = [k for k, v in self.assets.items() if v.get('media_type') == 'image']
        p['applications'][1]['media'] = next(k for k in images if k != p['applications'][0]['media'])
        self.fails(p, 'one shared image')
        p = self.product('ct-pegas-230'); p['applications'] = copy.deepcopy(self.products['ct-crova-254']['applications'])
        self.fails(p, 'no applications section')

    def test_sales_label_drives_every_enquiry_button_and_keeps_arrow(self):
        for key, product in self.products.items():
            original = BeautifulSoup(self.template(key), 'html.parser')
            result = self.render(copy.deepcopy(product))
            buttons = result.select('[data-contact]')
            self.assertEqual(len(buttons), 2)
            self.assertEqual([b.get_text() for b in buttons], [b.get_text() for b in original.select('[data-contact]')])
            for button in buttons:
                text = button.select_one('cms-text')
                self.assertEqual((text['data-cms-path'], text['data-cms-vi']), ('sales_action.0.label', 'Liên hệ kinh doanh'))
                self.assertIsNotNone(button.select_one('span[aria-hidden]'))
        p = self.product('decarb54'); p['sales_action'][0]['label'] = 'Ask sales'; p['sales_action'][0]['label__i18n__vi'] = 'Hỏi'
        self.assertEqual({b.select_one('cms-text').get_text() for b in self.render(p).select('[data-contact]')}, {'Ask sales'})
        p['sales_action'][0]['label__i18n__vi'] = ''
        with self.assertRaises(ValueError): self.render(p)

    def resolve(self, story, path):
        node = self.stories[story]
        *parents, last = path.split('.')
        for part in parents:
            node = node[int(part)] if part.isdigit() else node[part]
        en = node[last]
        # Shared fields (title) have no VI key; a blank VI falls back to EN.
        return en, node.get(last + '__i18n__vi') or en

    def test_visual_editor_path_contract(self):
        products = [copy.deepcopy(p) for p in self.products.values()]
        documents = {}
        for p in products:
            documents['pages/' + p['content_id'] + '.html'] = self.render(p)
        for path in SOURCE.rglob('*.html'):
            name = path.relative_to(SOURCE).as_posix()
            if name.startswith(('assets/', 'source-code/', 'checks/')) or name in documents:
                continue
            soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
            if cms.bind_document(soup, products, self.assets, self.vi):
                documents[name] = soup
        self.assertIn('index.html', documents)
        self.assertTrue(any(n.startswith('products/') for n in documents))
        checked, paths = 0, set()
        for name, soup in documents.items():
            for node in soup.select('[data-cms-en]'):
                self.assertIn(node.get('data-cms-story'), self.stories, name)
                self.assertNotEqual(node.has_attr('data-cms-path'), node.has_attr('data-cms-derived'), (name, str(node)[:120]))
                if node.has_attr('data-cms-path'):
                    self.assertEqual(self.resolve(node['data-cms-story'], node['data-cms-path']),
                                     (node['data-cms-en'], node['data-cms-vi']), (name, node['data-cms-path']))
                    paths.add(re.sub(r'\.\d+', '.N', node['data-cms-path'])); checked += 1
        self.assertGreater(checked, 100)
        for expected in ('title', 'summary', 'seo.N.title', 'seo.N.description', 'hero.N.heading', 'hero.N.description',
                         'specifications.N.label', 'applications.N.title', 'payload_options.N.description',
                         'sales_action.N.label', 'card_tagline', 'story_sections.N.heading', 'gallery.N.caption_override',
                         'gallery.N.alt_override', 'applications_intro'):
            self.assertIn(expected, paths)
        page = documents['pages/decarb22.html']
        self.assertTrue(page.select_one('#specifications td').has_attr('data-cms-derived'))
        self.assertTrue(page.select_one('.metric strong').has_attr('data-cms-derived'))
        self.assertEqual(page.select_one('#technology-title')['data-cms-story'].split(':')[0], 'technology')
        self.assertTrue(documents['pages/decarb54.html'].select_one('article.ps-chapter cms-text').has_attr('data-cms-derived'))

if __name__ == '__main__': unittest.main()
