"""Validate a CMS snapshot and render product fields into existing templates.

This does not fetch credentials, publish records, select a staging version, or deploy.
Private snapshot previews are written only into the ignored staging/checks folder.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
KEYS = {'decarb22', 'decarb54', 'ct-crova-254', 'ct-pegas-230'}


class ChapterLeaves(HTMLParser):
    """Find editable text leaves while preserving the original card structure."""
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.heading_depth = 0
        self.leaves = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.heading_depth += 1

    def handle_endtag(self, tag):
        if tag == 'h2':
            self.heading_depth -= 1

    def handle_data(self, data):
        if not data.strip() or self.heading_depth:
            return
        line, column = self.getpos()
        start = sum(len(line) for line in self.source.splitlines(keepends=True)[:line - 1]) + column
        end = self.source.find('<', start)
        self.leaves.append((start, len(self.source) if end < 0 else end))


def chapter_body(chapter, language):
    rich = chapter.get('body__i18n__' + language) if language != 'en' else None
    rich = rich or chapter.get('body')
    if not isinstance(rich, dict) or rich.get('type') != 'doc':
        raise ValueError('Invalid chapter body')
    values = []
    for paragraph in rich.get('content', []):
        if paragraph.get('type') != 'paragraph':
            raise ValueError('Chapter template accepts text paragraphs only')
        values.append(''.join(node.get('text', '') for node in paragraph.get('content', [])
                              if node.get('type') == 'text'))
    return values


def text(content, key, language):
    value = content.get(f'{key}__i18n__{language}') if language != 'en' else None
    value = value if value is not None else content.get(key, '')
    if not isinstance(value, str):
        raise ValueError(f'{key}: expected text')
    return value


def specification_value(row, language):
    """Use the reviewed display, or literal shared value/unit without conversion."""
    if row.get('display_value'):
        key = 'display_value' if language == 'en' else 'display_value__i18n__' + language
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Specification display needs an explicit translation')
        return value
    value = row.get('value')
    unit = row.get('unit', '')
    if not isinstance(value, str) or not value.strip() or not isinstance(unit, str):
        raise ValueError('Specification needs a literal value and unit')
    result = ' '.join(x for x in (value.strip(), unit.strip()) if x)
    if row.get('qualifier'):
        qualifier = row.get('qualifier' if language == 'en' else 'qualifier__i18n__' + language)
        if not isinstance(qualifier, str) or not qualifier.strip():
            raise ValueError('Specification qualifier needs an explicit translation')
        result += ' ' + qualifier.strip()
    return result


def validate(product, assets, *, preview):
    if product.get('component') != 'uav_product' or product.get('content_id') not in KEYS:
        raise ValueError('Unsupported product template')
    if not preview and (product.get('review_state') != 'ready' or
                        not {'en', 'vi'} <= set(product.get('ready_languages', []))):
        raise ValueError('Unreviewed product cannot enter published generation')
    rows = product.get('specifications', [])
    keys = [row.get('spec_key') for row in rows]
    if not rows or len(set(keys)) != len(keys) or not all(keys):
        raise ValueError('Missing or duplicate specifications')
    for row in rows:
        for language in ('en', 'vi'):
            if not text(row, 'label', language).strip() or not specification_value(row, language).strip():
                raise ValueError(f'Blank specification cell: {language}')
    hero = product.get('hero', [])
    if len(hero) != 1 or hero[0].get('kind') not in {'image', 'video'}:
        raise ValueError('Invalid hero')
    media = assets.get(hero[0].get('media'))
    if not media or media.get('media_type') != hero[0]['kind']:
        raise ValueError('Hero reference/type mismatch')
    asset_url(media)
    if media['media_type'] == 'video':
        poster = assets.get(media.get('poster'))
        if not poster or poster.get('media_type') != 'image':
            raise ValueError('Video needs an image poster')
        asset_url(poster)
    if product.get('presentation') == '3d_story':
        models = product.get('model', [])
        if models:
            if len(models) != 1 or assets.get(models[0].get('asset'), {}).get('media_type') != 'model':
                raise ValueError('3D presentation needs one valid model')
        elif not product.get('story_sections') or any(assets.get(ch.get('image'), {}).get('media_type') != 'image' for ch in product['story_sections']):
            raise ValueError('No-model story needs an image for every chapter')
        for chapter in product.get('story_sections', []):
            for field in ('azimuth', 'elevation', 'zoom', 'target_x', 'target_y', 'target_z'):
                number = float(chapter[field])
                if not -1e8 < number < 1e8 or (field == 'zoom' and number <= 0):
                    raise ValueError('Invalid camera value')


def asset_url(asset):
    url = asset['file']['filename']
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc not in {'a.storyblok.com', 'a2.storyblok.com'}
            or parts.username or not parts.path.startswith('/f/') or parts.query or parts.fragment):
        raise ValueError('Unexpected asset origin')
    if asset.get('media_type') == 'model':
        return parts._replace(netloc='a2.storyblok.com').geturl()
    return url


def render(template, product, assets, language):
    """Initial HTML uses CMS text; preserve all unrelated template sections."""
    esc = lambda value: html.escape(value, quote=True)
    # These are intermediate private preview fragments. The old published pilot
    # must never replace the draft data when a preview server later serves them.
    template = re.sub(r'<script\b[^>]*src="[^"]*decarb22-storyblok[^"]*"[^>]*>\s*</script>',
                      '', template)
    role = esc(text(product['hero'][0], 'description', language))
    template, count = re.subn(r'(<p\b[^>]*class="hero-role"[^>]*>).*?(</p>)',
                              lambda m: m[1] + role + m[2], template, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Hero role target not found')
    rows = ''.join('<tr><th scope="row">' + esc(text(row, 'label', language)) +
                   '</th><td>' + esc(text(row, 'display_value', language)) + '</td></tr>'
                   for row in product['specifications'])
    pattern = r'(<section\b[^>]*class="specifications-section[^>]*>.*?<tbody\b[^>]*>).*?(</tbody>)'
    template, count = re.subn(pattern, lambda m: m[1] + rows + m[2], template,
                              count=1, flags=re.S)
    if count != 1:
        raise ValueError('Specification target not found')
    if product.get('applications_intro'):
        pattern = r'(<section\b[^>]*class="applications-section[^>]*>.*?<div class="section-heading">.*?</h2>\s*<p\b[^>]*>).*?(</p>)'
        template, count = re.subn(pattern, lambda m: m[1] + esc(text(product, 'applications_intro', language)) + m[2],
                                  template, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Applications intro target not found')
    features = iter(product.get('applications', []))
    if product.get('applications'):
        def feature(match):
            value = next(features, None)
            if value is None:
                raise ValueError('Application count differs from template')
            return match[1] + esc(text(value, 'title', language)) + match[2] + esc(text(value, 'description', language)) + match[3]
        template, count = re.subn(r'(<div class="application-item">.*?<h3>).*?(</h3><p>).*?(</p>)',
                                  feature, template, flags=re.S)
        if count != len(product['applications']):
            raise ValueError('Application count differs from template')
    for technology in product.get('_resolved_technologies', []):
        title = esc(text(technology, 'title', language))
        template, count = re.subn(r'(<h2\b[^>]*id="technology-title"[^>]*>).*?(</h2>)',
                          lambda m: m[1] + title + m[2], template, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Technology heading target not found')
        items = ''.join('<li>' + esc(line) + '</li>' for line in text(technology, 'summary', language).splitlines())
        template, count = re.subn(r'(<ul class="technology-list">).*?(</ul>)',
                          lambda m: m[1] + items + m[2], template, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Technology list target not found')
    chapters = product.get('story_sections', [])
    if chapters:
        index = 0
        def chapter(match):
            nonlocal index
            if index >= len(chapters):
                raise ValueError('Chapter count differs from template')
            content = chapters[index]
            index += 1
            markup = match[0]
            parsed = ChapterLeaves(markup)
            values = chapter_body(content, language)
            if len(values) != len(parsed.leaves):
                raise ValueError('Chapter text structure changed; update template mapping first')
            for (start, end), value in reversed(list(zip(parsed.leaves, values))):
                markup = markup[:start] + esc(value) + markup[end:]
            markup = re.sub(r'(<h2\b[^>]*>).*?(</h2>)',
                            lambda m: m[1] + esc(text(content, 'heading', language)) + m[2],
                            markup, count=1, flags=re.S)
            camera = ','.join(str(content[k]) for k in ('azimuth', 'elevation', 'zoom', 'target_x', 'target_y', 'target_z'))
            return re.sub(r'data-ps-cam="[^"]+"', lambda m: 'data-ps-cam="' + esc(camera) + '"', markup)
        template, count = re.subn(r'<article\b[^>]*class="ps-chapter"[^>]*>.*?</article>',
                                  chapter, template, flags=re.S)
        if count != len(chapters):
            raise ValueError('Chapter count differs from template')
    # Media stays a separate asset; retain the existing deferred playback loader.
    media = assets[product['hero'][0]['media']]
    if media['media_type'] == 'video':
        template, count = re.subn(r'(data-video-src=")[^"]+', lambda m: m[1] + esc(asset_url(media)),
                                 template, count=1)
        if count != 1:
            raise ValueError('Video hero target not found; template conversion is not enabled')
        template, count = re.subn(r'(poster=")[^"]+', lambda m: m[1] + esc(asset_url(assets[media['poster']])),
                                 template, count=1)
        if count != 1:
            raise ValueError('Video poster target not found')
    else:
        def image(match):
            tag = re.sub(r'\s+srcset="[^"]*"', '', match[0])
            return re.sub(r'(\ssrc=")[^"]+', lambda m: m[1] + esc(asset_url(media)), tag)
        template, count = re.subn(r'<img\b[^>]*class="hero-section__image"[^>]*>', image,
                                  template, count=1)
        if count != 1:
            raise ValueError('Image hero target not found')
    # Reuse original source bytes by filename across gallery/application placements.
    # Asset metadata and gallery context remain structured CMS fields.
    for asset in assets.values():
        if asset.get('media_type') != 'image':
            continue
        filename = asset['file']['filename'].rsplit('/', 1)[-1]
        original = '../assets/img/' + filename
        if original not in template:
            continue
        url = esc(asset_url(asset))
        template = template.replace(original, url)
        def strip_old_variants(match):
            return re.sub(r'\s+srcset="[^"]*"', '', match[0])
        template = re.sub(r'<img\b[^>]*src="' + re.escape(url) + r'"[^>]*>',
                          strip_old_variants, template)
    return template


def generate(snapshot_path, output, *, preview=False):
    snapshot = json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    assets = {item['uuid']: item['content'] for item in snapshot['assets'].values()}
    output = Path(output).resolve()
    if not output.is_relative_to((HERE / 'checks').resolve()):
        raise ValueError('Output must remain in ignored staging/checks until release integration')
    products = [item['content'] for item in snapshot['records']
                if item['content'].get('component') == 'uav_product']
    if not products:
        raise ValueError('No managed products; do not silently restore static content')
    if not preview:
        raise ValueError('Published generation needs independent published CDN snapshots; not enabled yet')
    for product in products:
        product = dict(product)
        technologies = {item['uuid']: item['content'] for item in snapshot.get('technologies', [])}
        product['_resolved_technologies'] = [technologies[key] for key in product.get('technologies', [])]
        validate(product, assets, preview=preview)
        template = (PROJECT / json.loads((HERE / 'config.json').read_text(encoding='utf-8'))['source'] / 'pages' / (product['content_id'] + '.html')).read_text(encoding='utf-8')
        for language in ('en', 'vi'):
            target = output / language / 'pages' / (product['content_id'] + '.html')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render(template, product, assets, language), encoding='utf-8', newline='\n')
    return {'products': len(products), 'languages': ['en', 'vi'], 'preview_only': preview,
            'scope': 'intermediate EN/VI product fragments; protected server, shell model binding and publication build remain pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot')
    parser.add_argument('--output', required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    print(json.dumps(generate(args.snapshot, args.output, preview=args.preview)))
