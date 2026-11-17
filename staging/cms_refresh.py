"""Prepare reviewed draft-field additions from current source; no API writes."""
import copy
import json
import re
import uuid
from pathlib import Path
from bs4 import BeautifulSoup
from cms_refresh_guard import run_guarded, summary, warn_not_editor_safe

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent

def guarded_report_path(output):
    output = Path(output)
    return output.with_name(output.stem + '-guard-report.json')

def _without_uid(value):
    return json.dumps({k: v for k, v in value.items() if k != '_uid'}, sort_keys=True, ensure_ascii=False)

def reuse_uids(existing, prepared):
    # Keep the stored _uid when the blok at the same position has the same content.
    # A new or changed blok keeps its deterministic uuid5 _uid.
    for index, blok in enumerate(prepared):
        old = existing[index] if isinstance(existing, list) and index < len(existing) else None
        if isinstance(old, dict) and old.get('_uid') and _without_uid(old) == _without_uid(blok):
            blok['_uid'] = old['_uid']
    return prepared

REBUILT_LISTS = ('metrics', 'payload_options', 'sales_action')

def prepare(export, source, output, base=None, current=None, report=None):
    # Recommended: give base and current so that editor changes are protected.
    if (base is None) != (current is None):
        raise ValueError('Give both base and current, or neither')
    data = json.loads(Path(export).read_text(encoding='utf-8'))
    source = Path(source)
    dictionary = json.loads((source / 'assets/i18n/vi.json').read_text(encoding='utf-8'))
    missing = set()
    def translate(value):
        value = re.sub(r'\s+', ' ', value).strip()
        if value in {'CT-CROVA 254', 'CT-LiDAR-S1'}:
            return value
        if value not in dictionary:
            missing.add(value)
            return ''
        return dictionary[value]
    def block(component, **values):
        identity = component + ':' + json.dumps(values, sort_keys=True, ensure_ascii=True)
        return {'component': component, '_uid': str(uuid.uuid5(uuid.NAMESPACE_URL, identity)), **values}
    assets = {x['content']['file']['filename'].rsplit('/', 1)[-1]: x for x in data['stories']
              if x['content']['component'] == 'creative_asset'}
    for asset in assets.values():
        content = asset['content']
        if content['media_type'] == 'image':
            # Use the exact source alt for this file, never the file name as alt.
            for page in source.glob('pages/*.html'):
                soup = BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser')
                image = soup.find('img', src=lambda s: s and s.rsplit('/', 1)[-1] == content['title'])
                if image and image.get('alt'):
                    content['alt'] = image['alt']
                    content['alt__i18n__vi'] = translate(image['alt'])
                    break
    products = [x for x in data['stories'] if x['content']['component'] == 'uav_product']
    aliases = {'Mapping coverage per flight': 'Coverage per flight', 'Operating duration, no load': 'Operating duration'}
    for story in products:
        c = story['content']; existing = {key: copy.deepcopy(c.get(key)) for key in REBUILT_LISTS}; soup = BeautifulSoup((source / 'pages' / (c['content_id'] + '.html')).read_text(encoding='utf-8'), 'html.parser')
        c['metrics'] = []
        for metric in soup.select('.metric'):
            label = metric.p.get_text(' ', strip=True)
            spec_label = aliases.get(label, label)
            matches = [row for row in c['specifications'] if row['label'] == spec_label]
            if len(matches) != 1:
                raise ValueError('Metric specification is ambiguous: ' + label)
            c['metrics'].append(block('metric', spec_key=matches[0]['spec_key'], label_override=label,
                                      label_override__i18n__vi=translate(label)))
        c['payload_options'] = []
        for option in soup.select('.payload-option'):
            title, desc = option.h3.get_text(' ', strip=True), option.p.get_text(' ', strip=True)
            c['payload_options'].append(block('ct_feature', title=title, title__i18n__vi=translate(title),
                                              description=desc, description__i18n__vi=translate(desc)))
        c['sales_action'] = [block('action', key='contact-sales', label='Contact Sales',
                                   label__i18n__vi=translate('Contact Sales'), behaviour='enquiry',
                                   destination={'fieldtype': 'multilink', 'linktype': 'url', 'url': '/contact/'})]
        figures = soup.select('.gallery-grid figure')
        if len(c['gallery']) != len(figures):
            raise ValueError('CMS/source gallery count differs: ' + c['content_id'])
        for placement, figure in zip(c['gallery'], figures):
            caption = figure.select_one('figcaption span')
            if caption:
                value = caption.get_text(' ', strip=True)
                placement['caption_override'], placement['caption_override__i18n__vi'] = value, translate(value)
        app_image = soup.select_one('.application-image img')
        if app_image and c.get('applications'):
            ref = assets.get(app_image['src'].rsplit('/', 1)[-1])
            if ref:
                c['applications'][0]['media'] = ref['uuid']
        for key in REBUILT_LISTS:
            reuse_uids(existing[key], c[key])
        c['documents'] = c.get('documents', [])
        c['related_products'] = c.get('related_products', [])
        for seo in c.get('seo', []):
            seo['title__i18n__vi'] = seo['title']
            seo['description__i18n__vi'] = c['summary__i18n__vi']
        # Draft/review metadata remains unchanged. This is not approval.
    result = {'products': len(products), 'missing_translations': sorted(missing)}
    if base is None:
        warn_not_editor_safe()
        Path(output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    load = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
    guard_report = run_guarded(load(base), load(current), data, output, report or guarded_report_path(output))
    result['guard'] = summary(guard_report)
    return result

if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(); parser.add_argument('export'); parser.add_argument('--source', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--base', help='last complete read-back snapshot (recommended)')
    parser.add_argument('--current', help='fresh complete Storyblok read just before the write (recommended)')
    parser.add_argument('--report', help='guard report path; default: <output>-guard-report.json')
    parser.add_argument('--unguarded', action='store_true', help='local analysis only; output must never be written to Storyblok')
    args = parser.parse_args()
    if args.base is None and args.current is None and not args.unguarded:
        parser.error('give --base and --current (editor guard), or --unguarded for local analysis only')
    result = prepare(args.export, args.source, args.output, args.base, args.current, args.report)
    print(json.dumps(result, ensure_ascii=True))
    if 'guard' in result and not result['guard']['ok']:
        print('STOP: guard found conflicts or stops; no output was written. Read the report.', file=sys.stderr)
        sys.exit(1)
