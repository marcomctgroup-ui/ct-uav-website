"""Unit tests for cms_delivery. No network: every request uses a mocked opener."""
import io
import json
import unittest
import urllib.error
import urllib.parse

import cms_delivery

TOKEN = 'test-only-token-XYZ123'


class Response(io.BytesIO):
    def __init__(self, data, total=None, status=200):
        super().__init__(json.dumps(data).encode())
        self.status = status
        self.headers = {} if total is None else {'Total': str(total)}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def story(n, component='uav_product'):
    return {'id': n, 'uuid': f'u{n}', 'published_at': None, 'content': {'component': component}}


class Opener:
    def __init__(self, pages, total=None):
        self.pages, self.total, self.urls, self.timeouts = pages, total, [], []

    def __call__(self, request, timeout):
        self.urls.append(request.full_url)
        self.timeouts.append(timeout)
        page = int(urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)['page'][0])
        return Response({'stories': self.pages[page - 1], 'cv': 1700000000}, self.total)


class DeliveryTest(unittest.TestCase):
    def test_pagination_reads_every_page(self):
        pages = [[story(1), story(2)], [story(3), story(4)], [story(5)]]
        opener = Opener(pages)
        snapshot = cms_delivery.fetch_snapshot('draft', TOKEN, opener=opener, per_page=2, languages=())
        self.assertEqual([s['id'] for s in snapshot['stories']], [1, 2, 3, 4, 5])
        self.assertEqual(len(opener.urls), 3)
        self.assertEqual(snapshot['cv'], 1700000000)
        self.assertTrue(all(t == cms_delivery.TIMEOUT for t in opener.timeouts))

    def test_total_header_stops_on_exact_page(self):
        opener = Opener([[story(1), story(2)], []], total=2)
        cms_delivery.fetch_snapshot('published', TOKEN, opener=opener, per_page=2, languages=())
        self.assertEqual(len(opener.urls), 1)

    def test_version_passthrough_and_filter(self):
        for version in ('draft', 'published'):
            opener = Opener([[story(1)]])
            snapshot = cms_delivery.fetch_snapshot(version, TOKEN, opener=opener)
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(opener.urls[0]).query)
            self.assertEqual(query['version'], [version])
            self.assertEqual(snapshot['version'], version)
            self.assertEqual(query['filter_query[component][in]'], [','.join(cms_delivery.COMPONENTS)])
            self.assertTrue(opener.urls[0].startswith(cms_delivery.API + '?'))

    def test_pilot_and_other_components_are_excluded(self):
        pilot = {'id': cms_delivery.PILOT_STORY_ID, 'uuid': 'p', 'content': {'component': 'uav_product'}}
        old = story(9, 'product_page')
        opener = Opener([[story(1), pilot, old, story(2, 'page'), story(3, 'technology')]])
        snapshot = cms_delivery.fetch_snapshot('draft', TOKEN, opener=opener)
        self.assertEqual([s['id'] for s in snapshot['stories']], [1, 3])

    def test_unknown_version_is_refused_before_any_request(self):
        opener = Opener([[story(1)]])
        for version in ('Draft', 'latest', '', None):
            with self.assertRaises(ValueError):
                cms_delivery.fetch_snapshot(version, TOKEN, opener=opener)
        self.assertEqual(opener.urls, [])

    def test_missing_token_is_refused(self):
        with self.assertRaises(cms_delivery.DeliveryError):
            cms_delivery.fetch_snapshot('draft', '', opener=Opener([[]]))

    def test_http_error_is_redacted(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 401, 'Unauthorized ' + TOKEN, {}, None)
        with self.assertRaises(cms_delivery.DeliveryError) as caught:
            cms_delivery.fetch_snapshot('draft', TOKEN, opener=opener)
        message = str(caught.exception)
        self.assertIn('HTTP 401', message)
        self.assertIn('token=REDACTED', message)
        self.assertNotIn(TOKEN, message)
        self.assertIsNone(caught.exception.__cause__)
        self.assertTrue(caught.exception.__suppress_context__)

    def test_network_error_is_redacted(self):
        def opener(request, timeout):
            raise urllib.error.URLError('timed out for ' + request.full_url)
        with self.assertRaises(cms_delivery.DeliveryError) as caught:
            cms_delivery.fetch_snapshot('published', TOKEN, opener=opener)
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_invalid_json_and_shape(self):
        class Bad(Response):
            def __init__(self):
                io.BytesIO.__init__(self, b'not json')
                self.status, self.headers = 200, {}
        with self.assertRaises(cms_delivery.DeliveryError):
            cms_delivery.fetch_snapshot('draft', TOKEN, opener=lambda r, timeout: Bad())
        with self.assertRaises(cms_delivery.DeliveryError):
            cms_delivery.fetch_snapshot('draft', TOKEN, opener=lambda r, timeout: Response({'x': 1}))

    def test_summary_has_no_content(self):
        snap = {'version': 'draft', 'cv': 1, 'stories': [
            {'id': 1, 'uuid': 'a', 'updated_at': 'T', 'content': {'component': 'uav_product', 'content_id': 'decarb22', 'title': 'secret text'}}]}
        text = json.dumps(cms_delivery.summary(snap))
        self.assertIn('decarb22', text)
        self.assertNotIn('secret text', text)


class LanguageMergeTest(unittest.TestCase):
    def test_vi_copy_becomes_i18n_fields(self):
        en = {'id': 1, 'uuid': 'u1', 'content': {'component': 'uav_product', 'summary': 'Fast', 'title': 'X',
              'specifications': [{'_uid': 'a', 'component': 'specification', 'label': 'Range'}],
              'story_sections': [{'_uid': 'c', 'body': {'type': 'doc', 'content': []}}]}}
        vi = json.loads(json.dumps(en))
        vi['content']['summary'] = 'Nhanh'
        vi['content']['specifications'][0]['label'] = 'T\u1ea7m bay'
        vi['content']['story_sections'][0]['body'] = {'type': 'doc', 'content': [{'type': 'paragraph'}]}
        seen = []

        def opener(request, timeout):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
            seen.append(query.get('language', ['default'])[0])
            return Response({'stories': [vi if query.get('language') == ['vi'] else en], 'cv': 1})
        snapshot = cms_delivery.fetch_snapshot('draft', TOKEN, opener=opener)
        c = snapshot['stories'][0]['content']
        self.assertEqual(seen, ['default', 'vi'])
        self.assertEqual(c['summary__i18n__vi'], 'Nhanh')
        self.assertEqual(c['specifications'][0]['label__i18n__vi'], 'T\u1ea7m bay')
        self.assertEqual(c['story_sections'][0]['body__i18n__vi']['content'], [{'type': 'paragraph'}])
        self.assertNotIn('_uid__i18n__vi', c['specifications'][0])
        self.assertNotIn('component__i18n__vi', c)


if __name__ == '__main__':
    unittest.main()
