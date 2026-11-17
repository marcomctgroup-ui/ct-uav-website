"""Three-way editor-safety guard for prepared Storyblok draft content.

No network calls and no Storyblok writes. The guard compares, per story and per
field path:

- base: the last complete snapshot that the tools wrote or read back;
- current: a fresh complete read from Storyblok just before a write;
- candidate: the prepared content from a refresh script.

A field takes the candidate value only when the editor did not change it
(current == base). If the editor changed it and the candidate keeps the base
value, the editor value stays ("kept editor value"). If the editor changed it
and the candidate has a different value, the field is a CONFLICT. Any conflict
or stop gives ok == False, and the CLI writes no merged output.

Nested bloks in lists are matched by `_uid`. Other lists are matched by
position. Translation keys such as `title__i18n__vi` are separate fields.
Published stories, and stories whose published state differs from base, stop
the write. Published content is out of scope for this tool.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALLOWED_OUTPUT_ROOTS = (HERE / 'checks', HERE.parent / 'handoff')
METADATA_KEYS = ('updated_at', 'current_version_id', 'published', 'published_at')


class _Missing:
    def __repr__(self):
        return 'MISSING'


MISSING = _Missing()


def _canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _eq(a, b):
    if a is MISSING or b is MISSING:
        return a is b
    # Canonical JSON keeps True and 1 different, unlike Python ==.
    return _canon(a) == _canon(b)


def _report_value(value):
    return '<missing>' if value is MISSING else value


def _keyed(items):
    """Return the _uid list when every item is a blok with a unique _uid."""
    if not isinstance(items, list):
        return None
    uids = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('_uid'), str) or not item['_uid']:
            return None
        uids.append(item['_uid'])
    return uids if len(set(uids)) == len(uids) else None


class _Merge:
    def __init__(self, story_id):
        self.story_id = story_id
        self.changed = []
        self.kept = []
        self.conflicts = []

    def _entry(self, path, **values):
        return {'story_id': self.story_id, 'path': path,
                **{k: _report_value(v) for k, v in values.items()}}

    def leaf(self, path, b, c, k):
        if _eq(c, b):
            if not _eq(k, c):
                self.changed.append(self._entry(path, current=c, candidate=k))
            return k
        if _eq(k, c):
            return c
        if _eq(k, b):
            self.kept.append(self._entry(path, base=b, current=c, candidate=k))
            return c
        self.conflicts.append(self._entry(path, base=b, current=c, candidate=k))
        return c

    def merge(self, path, b, c, k):
        if _eq(b, c) and _eq(c, k):
            return c
        if isinstance(c, dict) and isinstance(k, dict) and (b is MISSING or isinstance(b, dict)):
            return self._merge_dict(path, {} if b is MISSING else b, c, k)
        if isinstance(c, list) and isinstance(k, list) and (b is MISSING or isinstance(b, list)):
            base = [] if b is MISSING else b
            if all(x is not None for x in (_keyed(base), _keyed(c), _keyed(k))):
                return self._merge_keyed(path, base, c, k)
            if len(base) == len(c) == len(k):
                return [self.merge(f'{path}[{i}]', base[i], c[i], k[i]) for i in range(len(c))]
        return self.leaf(path, b, c, k)

    def _merge_dict(self, path, b, c, k):
        result = {}
        keys = list(c) + [x for x in k if x not in c] + [x for x in b if x not in c and x not in k]
        for key in keys:
            value = self.merge(f'{path}.{key}', b.get(key, MISSING), c.get(key, MISSING), k.get(key, MISSING))
            if value is not MISSING:
                result[key] = value
        return result

    def _merge_keyed(self, path, b, c, k):
        bm, cm, km = ({x['_uid']: x for x in items} for items in (b, c, k))
        ob, oc, ok = ([x['_uid'] for x in items] for items in (b, c, k))
        merged = {}
        for uid in oc + [x for x in ok if x not in cm] + [x for x in ob if x not in cm and x not in km]:
            value = self.merge(f'{path}[_uid={uid}]', bm.get(uid, MISSING), cm.get(uid, MISSING), km.get(uid, MISSING))
            if value is not MISSING:
                merged[uid] = value
        # Order: compare the relative order of bloks present in all three lists.
        common = [x for x in ob if x in cm and x in km]
        rb = common
        rc = [x for x in oc if x in common]
        rk = [x for x in ok if x in common]
        order_path = path + '#order'
        if rc == rb:
            primary, secondary = ok, oc
            if rk != rb:
                self.changed.append(self._entry(order_path, current=rc, candidate=rk))
        else:
            primary, secondary = oc, ok
            if rk == rb:
                self.kept.append(self._entry(order_path, base=rb, current=rc, candidate=rk))
            elif rk != rc:
                self.conflicts.append(self._entry(order_path, base=rb, current=rc, candidate=rk))
        order = [x for x in primary if x in merged]
        for source in (secondary, oc, ok):
            for index, uid in enumerate(source):
                if uid in order or uid not in merged:
                    continue
                previous = next((x for x in reversed(source[:index]) if x in order), None)
                order.insert(0 if previous is None else order.index(previous) + 1, uid)
        return [merged[x] for x in order]


def _stories(snapshot, name):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('stories'), list):
        raise ValueError(name + ' is not a complete snapshot with a stories list')
    result = {}
    for story in snapshot['stories']:
        if not isinstance(story, dict) or 'id' not in story:
            raise ValueError(name + ' has a story without an id')
        if story['id'] in result:
            raise ValueError(name + ' has a duplicate story id: ' + str(story['id']))
        result[story['id']] = story
    return result


def _is_published(story):
    return bool(story.get('published')) or bool(story.get('published_at'))


def guard(base, current, candidate):
    """Return (merged_snapshot_or_None, report). Inputs are not changed."""
    bs, cs, ks = _stories(base, 'base'), _stories(current, 'current'), _stories(candidate, 'candidate')
    report = {'ok': True, 'stops': [], 'conflicts': [], 'kept_editor_values': [], 'changed': [],
              'editor_changed_stories': [], 'write_stories': [], 'not_in_candidate': []}
    merged_stories = []

    def stop(story_id, reason):
        report['stops'].append({'story_id': story_id, 'reason': reason})

    for story_id, k in ks.items():
        b, c = bs.get(story_id), cs.get(story_id)
        if c is None:
            stop(story_id, 'story is not in the fresh current read'); continue
        if b is None:
            stop(story_id, 'story is not in the base snapshot'); continue
        if not all(isinstance(s.get('content'), dict) and s['content'].get('component') for s in (b, c, k)):
            stop(story_id, 'story content is incomplete in base, current or candidate'); continue
        if not (b.get('uuid') == c.get('uuid') == k.get('uuid')):
            stop(story_id, 'story uuid differs between base, current and candidate'); continue
        if len({b['content']['component'], c['content']['component'], k['content']['component']}) != 1:
            stop(story_id, 'content component differs between base, current and candidate'); continue
        if _is_published(c) or _is_published(k):
            stop(story_id, 'story is published; published content is out of scope'); continue
        if bool(b.get('published')) != bool(c.get('published')) or b.get('published_at') != c.get('published_at'):
            stop(story_id, 'published state differs from base'); continue
        if not _eq(b['content'], c['content']):
            report['editor_changed_stories'].append(story_id)
        m = _Merge(story_id)
        content = m.merge('content', b['content'], c['content'], k['content'])
        report['changed'] += m.changed
        report['kept_editor_values'] += m.kept
        report['conflicts'] += m.conflicts
        story = copy.deepcopy(k)
        story['content'] = content
        # The merged record is "current + safe changes"; the writer must find
        # this exact version again just before the save.
        for key in METADATA_KEYS:
            if key in c:
                story[key] = c[key]
            else:
                story.pop(key, None)
        merged_stories.append(story)
        if not _eq(content, c['content']):
            report['write_stories'].append({'story_id': story_id, 'name': c.get('name'),
                                            'expected_updated_at': c.get('updated_at'),
                                            'expected_current_version_id': c.get('current_version_id')})
    report['not_in_candidate'] = [x for x in cs if x not in ks]
    report['ok'] = not report['stops'] and not report['conflicts']
    if not report['ok']:
        return None, report
    merged = copy.deepcopy({key: value for key, value in candidate.items() if key != 'stories'})
    merged['stories'] = merged_stories
    return merged, report


def check_output_path(path):
    """Allow guarded outputs only below staging/checks or handoff."""
    resolved = Path(path).resolve()
    for root in ALLOWED_OUTPUT_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            pass
    raise ValueError('Guarded output must be below staging/checks or handoff: ' + str(path))


def _load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def summary(report):
    return {'ok': report['ok'], 'stops': len(report['stops']), 'conflicts': len(report['conflicts']),
            'kept_editor_values': len(report['kept_editor_values']), 'changed': len(report['changed']),
            'write_stories': [x['story_id'] for x in report['write_stories']]}


def run_guarded(base, current, candidate, output, report_path):
    """Check paths, guard, write the report always and the merge only when ok."""
    output, report_path = check_output_path(output), check_output_path(report_path)
    if output == report_path:
        raise ValueError('Output and report must be different files')
    for path in (output, report_path):
        # No stale merge can remain beside a failed report, and no record is overwritten.
        if path.exists():
            raise ValueError('Output file already exists; use a new versioned name: ' + str(path))
    merged, report = guard(base, current, candidate)
    _write(report_path, report)
    if report['ok']:
        _write(output, merged)
    return report


def warn_not_editor_safe(stream=None):
    print('WARNING: output is NOT editor-safe. It can replace editor changes in Storyblok. '
          'Give --base (last read-back snapshot) and --current (fresh complete read) to run '
          'cms_refresh_guard before any draft write.', file=stream or sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('base'); parser.add_argument('current'); parser.add_argument('candidate')
    parser.add_argument('--output', required=True); parser.add_argument('--report', required=True)
    args = parser.parse_args(argv)
    try:
        report = run_guarded(_load(args.base), _load(args.current), _load(args.candidate), args.output, args.report)
    except ValueError as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(summary(report), ensure_ascii=True))
    if not report['ok']:
        print('STOP: no merged output was written. Read the report.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
