"""Tests for the three-way editor guard. Run: python cms_refresh_guard_test.py"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

import cms_refresh_guard as g

HERE = Path(__file__).resolve().parent
HANDOFF = HERE.parent / 'handoff'
REAL = HANDOFF / '20261117-storyblok-card-fields-readback-v01.json'


def snapshot(**content):
    base = {'component': 'uav_product', '_uid': 'root', 'title': 'Old', 'title__i18n__vi': 'Cu',
            'metrics': [{'component': 'metric', '_uid': 'm1', 'label_override': 'Range'},
                        {'component': 'metric', '_uid': 'm2', 'label_override': 'Payload'}]}
    base.update(content)
    return {'stories': [{'id': 1, 'uuid': 'u1', 'name': 'P', 'published': False,
                         'updated_at': '2026-11-17T00:00:00Z', 'current_version_id': 10, 'content': base}]}


def content(snap):
    return snap['stories'][0]['content']


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.base = snapshot()
        self.current = copy.deepcopy(self.base)
        self.candidate = copy.deepcopy(self.base)

    def run_guard(self):
        return g.guard(self.base, self.current, self.candidate)

    def test_unchanged_editor_field_takes_candidate_value(self):
        content(self.candidate)['title'] = 'New'
        merged, report = self.run_guard()
        self.assertTrue(report['ok'])
        self.assertEqual(content(merged)['title'], 'New')
        self.assertEqual([x['path'] for x in report['changed']], ['content.title'])
        self.assertEqual(report['write_stories'][0]['expected_current_version_id'], 10)

    def test_editor_edit_and_different_candidate_is_conflict(self):
        content(self.current)['title'] = 'Editor'
        content(self.candidate)['title'] = 'Source'
        merged, report = self.run_guard()
        self.assertFalse(report['ok'])
        self.assertIsNone(merged)
        self.assertEqual(report['conflicts'][0]['path'], 'content.title')
        self.assertEqual(report['conflicts'][0]['current'], 'Editor')

    def test_editor_edit_kept_when_candidate_equals_base(self):
        content(self.current)['title'] = 'Editor'
        content(self.candidate)['summary'] = 'Added by source'
        merged, report = self.run_guard()
        self.assertTrue(report['ok'])
        self.assertEqual(content(merged)['title'], 'Editor')
        self.assertEqual(content(merged)['summary'], 'Added by source')
        self.assertEqual([x['path'] for x in report['kept_editor_values']], ['content.title'])

    def test_nested_blok_matched_by_uid(self):
        # The editor moves m2 first and edits it; the source edits m1 only.
        content(self.current)['metrics'].reverse()
        content(self.current)['metrics'][0]['label_override'] = 'Payload (editor)'
        content(self.candidate)['metrics'][0]['label_override'] = 'Range (source)'
        merged, report = self.run_guard()
        self.assertTrue(report['ok'], report)
        self.assertEqual([(m['_uid'], m['label_override']) for m in content(merged)['metrics']],
                         [('m2', 'Payload (editor)'), ('m1', 'Range (source)')])
        self.assertEqual([x['path'] for x in report['changed']], ['content.metrics[_uid=m1].label_override'])
        paths = [x['path'] for x in report['kept_editor_values']]
        self.assertEqual(paths, ['content.metrics[_uid=m2].label_override', 'content.metrics#order'])

    def test_same_uid_field_edited_on_both_sides_is_conflict(self):
        content(self.current)['metrics'][1]['label_override'] = 'Editor'
        content(self.candidate)['metrics'][1]['label_override'] = 'Source'
        _, report = self.run_guard()
        self.assertEqual(report['conflicts'][0]['path'], 'content.metrics[_uid=m2].label_override')

    def test_candidate_cannot_delete_editor_edited_blok(self):
        content(self.current)['metrics'][1]['label_override'] = 'Editor'
        del content(self.candidate)['metrics'][1]
        _, report = self.run_guard()
        self.assertFalse(report['ok'])
        self.assertEqual(report['conflicts'][0]['path'], 'content.metrics[_uid=m2]')

    def test_list_without_uid_matched_by_position(self):
        for snap in (self.base, self.current, self.candidate):
            content(snap)['rows'] = [{'v': 'a'}, {'v': 'b'}]
        content(self.current)['rows'][0]['v'] = 'editor'
        content(self.candidate)['rows'][1]['v'] = 'source'
        merged, report = self.run_guard()
        self.assertTrue(report['ok'])
        self.assertEqual(content(merged)['rows'], [{'v': 'editor'}, {'v': 'source'}])
        self.assertEqual(report['changed'][0]['path'], 'content.rows[1].v')

    def test_translation_field_is_separate(self):
        content(self.current)['title__i18n__vi'] = 'Bien tap'
        content(self.candidate)['title'] = 'New'
        merged, report = self.run_guard()
        self.assertTrue(report['ok'])
        self.assertEqual((content(merged)['title'], content(merged)['title__i18n__vi']), ('New', 'Bien tap'))
        self.assertEqual(report['kept_editor_values'][0]['path'], 'content.title__i18n__vi')
        content(self.candidate)['title__i18n__vi'] = 'Nguon'
        _, report = self.run_guard()
        self.assertEqual(report['conflicts'][0]['path'], 'content.title__i18n__vi')

    def test_published_story_stops(self):
        self.current['stories'][0]['published'] = True
        merged, report = self.run_guard()
        self.assertFalse(report['ok'])
        self.assertIsNone(merged)
        self.assertIn('published', report['stops'][0]['reason'])
        self.current['stories'][0]['published'] = False
        self.current['stories'][0]['published_at'] = '2026-11-17T01:00:00Z'
        self.assertFalse(self.run_guard()[1]['ok'])
        self.current['stories'][0]['published_at'] = None
        self.base['stories'][0]['published'] = True
        _, report = self.run_guard()
        self.assertEqual(report['stops'][0]['reason'], 'published state differs from base')

    def test_editor_added_field_and_blok_stay(self):
        content(self.current)['seo_note'] = 'Editor note'
        content(self.current)['metrics'].append({'component': 'metric', '_uid': 'm3', 'label_override': 'New'})
        content(self.candidate)['title'] = 'New'
        merged, report = self.run_guard()
        self.assertTrue(report['ok'])
        self.assertEqual(content(merged)['seo_note'], 'Editor note')
        self.assertEqual([m['_uid'] for m in content(merged)['metrics']], ['m1', 'm2', 'm3'])

    def test_missing_or_new_story_stops(self):
        extra = copy.deepcopy(self.candidate['stories'][0]); extra['id'] = 2
        self.candidate['stories'].append(extra)
        _, report = self.run_guard()
        self.assertEqual(report['stops'][0]['reason'], 'story is not in the fresh current read')

    def test_merged_metadata_comes_from_current(self):
        self.current['stories'][0]['current_version_id'] = 11
        content(self.candidate)['title'] = 'New'
        merged, _ = self.run_guard()
        self.assertEqual(merged['stories'][0]['current_version_id'], 11)

    def test_inputs_are_not_changed(self):
        content(self.current)['title'] = 'Editor'
        before = json.dumps([self.base, self.current, self.candidate], sort_keys=True)
        self.run_guard()
        self.assertEqual(json.dumps([self.base, self.current, self.candidate], sort_keys=True), before)

    def test_real_handoff_snapshot_against_itself(self):
        real = json.loads(REAL.read_text(encoding='utf-8'))
        merged, report = g.guard(real, copy.deepcopy(real), copy.deepcopy(real))
        self.assertTrue(report['ok'])
        for key in ('stops', 'conflicts', 'kept_editor_values', 'changed', 'editor_changed_stories', 'write_stories'):
            self.assertEqual(report[key], [], key)
        self.assertEqual(merged['stories'], real['stories'])

    def test_reference_refresh_on_real_readback_has_no_changes(self):
        from cms_reference_refresh import prepare
        real = json.loads(REAL.read_text(encoding='utf-8'))
        _, report = g.guard(real, real, prepare(real))
        self.assertTrue(report['ok'])
        self.assertEqual(report['changed'], [])


class RefreshUidTests(unittest.TestCase):
    """cms_refresh reuses stored _uid values for unchanged bloks."""
    SOURCE = HERE.parent / json.loads((HERE / 'config.json').read_text(encoding='utf-8'))['source']

    def refresh(self, export):
        import contextlib, io
        from cms_refresh import prepare
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'export.json'; out = Path(folder) / 'out.json'
            path.write_text(json.dumps(export, ensure_ascii=False), encoding='utf-8')
            with contextlib.redirect_stderr(io.StringIO()):
                prepare(path, self.SOURCE, out)
            return json.loads(out.read_text(encoding='utf-8'))

    def setUp(self):
        self.real = json.loads(REAL.read_text(encoding='utf-8'))

    def product(self, snap):
        return next(s for s in snap['stories'] if s['content'].get('content_id') == 'decarb22')

    def test_unchanged_source_gives_no_changes(self):
        _, report = g.guard(self.real, self.real, self.refresh(self.real))
        self.assertTrue(report['ok'], report)
        self.assertEqual(report['changed'], [])
        self.assertEqual(report['write_stories'], [])

    def test_changed_value_still_produces_a_change(self):
        # The CMS blok differs from the website source, so the refresh restores the source value.
        export = copy.deepcopy(self.real)
        self.product(export)['content']['metrics'][0]['label_override'] = 'Old CMS label'
        _, report = g.guard(export, export, self.refresh(export))
        self.assertTrue(report['ok'], report)
        self.assertTrue(report['changed'])
        self.assertTrue(all(x['path'].startswith('content.metrics[') for x in report['changed']))

    def test_editor_edited_blok_with_different_source_is_conflict(self):
        current = copy.deepcopy(self.real)
        self.product(current)['content']['metrics'][0]['label_override'] = 'Editor label'
        merged, report = g.guard(self.real, current, self.refresh(current))
        self.assertFalse(report['ok'])
        self.assertIsNone(merged)
        uid = self.product(current)['content']['metrics'][0]['_uid']
        self.assertIn('content.metrics[_uid=' + uid + ']', [x['path'] for x in report['conflicts']])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.inputs = tempfile.TemporaryDirectory()
        self.out = HERE / 'checks' / ('guard-test-' + uuid.uuid4().hex)
        self.addCleanup(self.inputs.cleanup)
        self.addCleanup(self._remove_out)

    def _remove_out(self):
        for path in sorted(self.out.glob('*')):
            path.unlink()
        if self.out.exists():
            self.out.rmdir()

    def cli(self, base, current, candidate, output=None):
        paths = []
        for name, data in (('base', base), ('current', current), ('candidate', candidate)):
            path = Path(self.inputs.name) / (name + '.json')
            path.write_text(json.dumps(data), encoding='utf-8'); paths.append(str(path))
        output = output or str(self.out / 'merged.json')
        return subprocess.run([sys.executable, str(HERE / 'cms_refresh_guard.py'), *paths, '--output', output,
                               '--report', str(self.out / 'report.json')], capture_output=True, text=True)

    def test_exit_codes_and_outputs(self):
        base = snapshot(); candidate = copy.deepcopy(base); content(candidate)['title'] = 'New'
        done = self.cli(base, base, candidate)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(content(json.loads((self.out / 'merged.json').read_text(encoding='utf-8')))['title'], 'New')
        self._remove_out()
        current = copy.deepcopy(base); content(current)['title'] = 'Editor'
        done = self.cli(base, current, candidate)
        self.assertEqual(done.returncode, 1)
        self.assertFalse((self.out / 'merged.json').exists())
        self.assertFalse(json.loads((self.out / 'report.json').read_text(encoding='utf-8'))['ok'])

    def test_output_outside_allowed_folders_is_refused(self):
        base = snapshot()
        done = self.cli(base, base, base, output=str(Path(self.inputs.name) / 'merged.json'))
        self.assertEqual(done.returncode, 2)
        self.assertIn('staging/checks or handoff', done.stderr)

    def test_existing_output_is_not_overwritten(self):
        base = snapshot()
        self.assertEqual(self.cli(base, base, base).returncode, 0)
        self.assertEqual(self.cli(base, base, base).returncode, 2)


if __name__ == '__main__':
    unittest.main()
