"""Private, full-shell CMS candidate generation. Never publishes or selects a release.

Install cms-requirements.txt explicitly. Outputs stay under ignored staging/checks.
The selected byte-preserving public builder does not import this module.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup, NavigableString
from rjsmin import jsmin
import cms_generate as legacy
from cms_spec_refs import chapter_values

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent

def field(node, en, vi, *, prop=None, story=None, path=None):
    """Bind one CMS-owned EN/VI value.

    Visual Editor contract: `story` is the content_id, `asset:<uuid>` or
    `technology:<uuid>`. `path` is the dotted path to ONE raw text field of
    that story (VI: the same path with the final key + `__i18n__vi`). An
    element with a story and no path holds a derived value and is marked
    `data-cms-derived`; it changes only after the next build.
    """
    if not isinstance(en, str) or not en.strip() or not isinstance(vi, str) or not vi.strip():
        raise ValueError('CMS text needs explicit nonblank EN and VI values')
    node['data-i18n-skip'] = ''
    node['data-cms-en'], node['data-cms-vi'] = en, vi
    if story is not None:
        node['data-cms-story'] = story
        if path:
            node['data-cms-path'] = path; node.attrs.pop('data-cms-derived', None)
        else:
            node['data-cms-derived'] = ''; node.attrs.pop('data-cms-path', None)
    if prop:
        node['data-cms-property'] = prop
        node[prop] = en
    else:
        node.clear()
        node.append(en)

def label(node, en, vi, **source):
    """Bind the one text part of a control and keep its decoration (arrows)."""
    parts = [t for t in node.find_all(string=True, recursive=False) if t.strip()]
    if len(parts) != 1:
        raise ValueError('A label slot needs exactly one text part')
    text = str(parts[0])
    wrapper = BeautifulSoup('', 'html.parser').new_tag('cms-text')
    field(wrapper, en, vi, **source)
    parts[0].replace_with(wrapper)
    lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
    if lead:
        wrapper.insert_before(lead)
    if trail:
        wrapper.insert_after(trail)

def pair(content, key):
    return content.get(key, ''), content.get(key + '__i18n__vi', '')

def metric_value(row, metric, language):
    value = legacy.specification_value(row, language)
    if metric.get('label_override', '').endswith(', no load'):
        match = re.fullmatch(r'(?:No load|Không tải):\s*([^;]+);.*', value)
        if not match:
            raise ValueError('No-load metric has no explicit source condition')
        value = match[1]
    if metric.get('label_override') == 'Mapping coverage per flight':
        value = re.sub(r'\s*\((?:mapping|lập bản đồ)\)$', '', value)
    return value

def asset_url(asset):
    url = legacy.asset_url(asset)
    parts = urlsplit(url)
    if parts.netloc not in {'a.storyblok.com', 'a2.storyblok.com'} or parts.username or parts.query or parts.fragment:
        raise ValueError('Unexpected asset URL')
    return url

def image(node, asset, placement=None, *, story=None, path=None):
    """Bind an image. `story`/`path` name the alt source (see field)."""
    if asset.get('media_type') != 'image':
        raise ValueError('Image requires an image asset')
    url = asset_url(asset)
    node['src'] = url
    # Storyblok variants derive from the same original, never an old local UAV.
    node['srcset'] = ', '.join(f'{url}/m/{w}x0 {w}w' for w in (480, 800, 1600))
    node['sizes'] = '100vw' if 'hero-section__image' in node.get('class', []) else '(max-width: 700px) 100vw, 50vw'
    placement = placement or {}
    alt = pair(placement, 'alt_override') if placement.get('alt_override') else pair(asset, 'alt')
    field(node, *alt, prop='alt', story=story, path=path)

def asset_alt(uuid):
    """Alt source of a reusable creative asset."""
    return {'story': 'asset:' + uuid, 'path': 'alt'}

HERO_ACTION_DECISION = ('Hero actions need a layout decision: the accepted page has {slots} hero link slot(s) '
                        '(an in-page section link such as "View specifications") and the record has {actions}')

def bind_hero_actions(soup, product):
    """Map hero actions to the accepted hero link slots (.hero-actions a.hero-cta).

    Only a navigate action to an existing in-page section (#id) has a slot. A
    missing or empty list keeps the template link (record not migrated).
    """
    actions = product['hero'][0].get('actions') or []
    if not actions:
        return
    slots = soup.select('.hero-actions a.hero-cta')
    if len(slots) != len(actions):
        raise ValueError(HERO_ACTION_DECISION.format(slots=len(slots), actions=len(actions)))
    for i, (node, action) in enumerate(zip(slots, actions)):
        destination = action.get('destination') or {}
        url = destination.get('url', '') if destination.get('linktype', 'url') == 'url' else ''
        if (action.get('component') != 'action' or action.get('behaviour') != 'navigate'
                or not re.fullmatch(r'#[A-Za-z][A-Za-z0-9_-]*', url) or soup.find(id=url[1:]) is None):
            raise ValueError('Hero action needs a layout decision: only a navigate link to an existing '
                             'section of the same page (#id) has an accepted hero slot')
        node['href'] = url
        label(node, *pair(action, 'label'), story=product['content_id'], path=f'hero.0.actions.{i}.label')

def validate(product, assets):
    legacy.validate(product, assets, preview=True)
    if product.get('documents') or product.get('related_products'):
        raise ValueError('Documents/related products need an accepted section mapping first')
    if len(product.get('technologies', [])) > 1:
        raise ValueError('Multiple technology sections need an accepted mapping first')
    if len(product.get('sales_action', [])) != 1 or product['sales_action'][0].get('destination', {}).get('url') != '/contact/':
        raise ValueError('Unsupported sales destination')
    if product['hero'][0].get('phone_media') and product['hero'][0]['kind'] == 'image':
        raise ValueError('Separate phone image mapping is not enabled yet')
    for key in ('title', 'model_code', 'route'):
        if not str(product.get(key, '')).strip():
            raise ValueError('Missing product identity: ' + key)
    if not re.fullmatch(r'/products/[a-z0-9-]+/', product['route']):
        raise ValueError('Invalid canonical product route')
    routes = {'decarb22':'/products/decarb-22/', 'decarb54':'/products/decarb-54/',
              'ct-crova-254':'/products/ct-crova-254/', 'ct-pegas-230':'/products/ct-pegas-230/'}
    if product['route'] != routes[product['content_id']]:
        raise ValueError('Changing an accepted product URL needs an explicit route migration')
    for action in product['hero'][0].get('actions') or []:
        en, vi = pair(action, 'label')
        if not en.strip() or not vi.strip():
            raise ValueError('Hero action needs explicit EN and VI labels')
    # The schema key is sharing_image; share_image is checked as an old alias.
    if product['seo'][0].get('sharing_image') or product['seo'][0].get('share_image'):
        raise ValueError('SEO sharing image needs a layout decision: the accepted page templates have no '
                         'og:image or twitter:image metadata slot')
    for feature in product.get('applications', []):
        if feature.get('specification_keys'):
            raise ValueError('Feature specification references need a layout decision: the accepted '
                             'application item has a title and one description, with no figure slot')
    media = {f['media'] for f in product.get('applications', []) if f.get('media')}
    if len(media) > 1:
        raise ValueError('Contextual application media needs a layout decision: the accepted application '
                         'layout shows one shared image (.application-image)')
    spec_keys = {r['spec_key'] for r in product['specifications']}
    for row in product['specifications']:
        field(BeautifulSoup('<span></span>', 'html.parser').span, *pair(row, 'label'))
        for lang in ('en', 'vi'):
            legacy.specification_value(row, lang)
    for metric in product.get('metrics', []):
        if metric['spec_key'] not in spec_keys:
            raise ValueError('Metric references missing specification')
    for chapter in product.get('story_sections', []):
        if not isinstance(chapter.get('body__i18n__vi'), dict) or not chapter['body__i18n__vi'].get('content'):
            raise ValueError('Chapter needs an explicit Vietnamese body')
        vi_paragraphs = legacy.chapter_body(chapter, 'vi')
        if not vi_paragraphs or any(not value.strip() for value in vi_paragraphs):
            raise ValueError('Chapter has blank Vietnamese paragraphs')
        for ref in chapter.get('specification_keys', []):
            if ref.get('spec_key') not in spec_keys:
                raise ValueError('Chapter references missing specification')
        for lang in ('en', 'vi'):
            chapter_values(chapter, {r['spec_key']:r for r in product['specifications']}, lang)
    hero = product['hero'][0]
    for key in ('focal_x', 'focal_y'):
        if not 0 <= float(hero.get(key, .5)) <= 1:
            raise ValueError('Invalid focal position')
    for ref in product.get('gallery', []):
        if ref['asset'] not in assets:
            raise ValueError('Gallery reference is missing')
    if product.get('model'):
        model = product['model'][0]
        if not math.isfinite(float(model.get('scale', 1))) or float(model.get('scale', 1)) <= 0:
            raise ValueError('Invalid model scale')
        if not math.isfinite(float(model.get('front_degrees', 0))):
            raise ValueError('Invalid model orientation')
        if assets.get(model.get('poster'), {}).get('media_type') != 'image':
            raise ValueError('Model needs an image poster')
    for chapter in product.get('story_sections', []):
        if chapter.get('image') and assets.get(chapter['image'], {}).get('media_type') != 'image':
            raise ValueError('Chapter fallback needs an image')

def render(template, product, assets, technologies, dictionary):
    validate(product, assets)
    soup = BeautifulSoup(template, 'html.parser')
    for script in soup.select('script[src*="decarb22-storyblok"]'):
        script.decompose()
    soup.html['lang'] = 'en'
    cid = product['content_id']
    field(soup.title, *pair(product['seo'][0], 'title'), story=cid, path='seo.0.title')
    description = soup.find('meta', attrs={'name': 'description'})
    if description is None:
        description = soup.new_tag('meta', attrs={'name': 'description'}); soup.head.append(description)
    field(description, *pair(product['seo'][0], 'description'), prop='content', story=cid, path='seo.0.description')
    heading = product['hero'][0]['heading']
    vi_heading = product['hero'][0].get('heading__i18n__vi', heading if heading == product['title'] else '')
    # A blank VI heading falls back to EN only when it equals the shared title.
    field(soup.select_one('#product-title'), heading, vi_heading, story=cid, path='hero.0.heading')
    field(soup.select_one('.hero-role'), *pair(product['hero'][0], 'description'), story=cid, path='hero.0.description')
    field(soup.select_one('.product-bar__identity strong'), product['title'], product['title'], story=cid, path='title')
    bind_hero_actions(soup, product)
    for button in soup.select('[data-cart-id]'):
        button['data-cart-id'] = 'uav:' + product['content_id']
        button['data-cart-name'] = product['title']
    hero = product['hero'][0]
    media = assets[hero['media']]
    if hero['kind'] == 'image':
        image(soup.select_one('.hero-section__image'), media, **asset_alt(hero['media']))
        soup.select_one('.hero-section__image')['style'] = f"object-position:{float(hero.get('focal_x', .5))*100}% {float(hero.get('focal_y', .5))*100}%"
    else:
        video = soup.select_one('#overview video')
        if video is None:
            raise ValueError('Video mode requires the accepted video template')
        video.attrs.pop('src', None)
        video['data-video-src'] = asset_url(media)
        video['poster'] = asset_url(assets[media['poster']])
        video['preload'] = 'none'
        video['style'] = f"object-position:{float(hero.get('focal_x', .5))*100}% {float(hero.get('focal_y', .5))*100}%"
        phone = hero.get('phone_media') or media.get('mobile_variant')
        video.attrs.pop('data-video-src-small', None)
        if phone:
            if assets[phone]['media_type'] != 'video':
                raise ValueError('Phone video type mismatch')
            video['data-video-src-small'] = asset_url(assets[phone])
    rows = {r['spec_key']: r for r in product['specifications']}
    metric_nodes = soup.select('.metric')
    if len(metric_nodes) != len(product.get('metrics', [])):
        raise ValueError('Metric count differs from accepted layout')
    for index, (node, metric) in enumerate(zip(metric_nodes, product.get('metrics', []))):
        row = rows[metric['spec_key']]
        field(node.strong, *(metric_value(row, metric, lang) for lang in ('en', 'vi')), story=cid)
        node.strong['data-cms-property'] = 'metric'
        en, vi, source = label_source(product, metric, f'metrics.{index}')
        field(node.p, en, vi, **source)
    table = soup.select_one('#specifications tbody')
    table.clear()
    for index, row in enumerate(product['specifications']):
        tr = soup.new_tag('tr'); th = soup.new_tag('th', scope='row'); td = soup.new_tag('td')
        field(th, *pair(row, 'label'), story=cid, path=f'specifications.{index}.label')
        field(td, *(legacy.specification_value(row, lang) for lang in ('en', 'vi')), story=cid)
        tr.extend([th, td]); table.append(tr)
    intro = soup.select_one('#applications .section-heading > p:last-child')
    if not intro and (product.get('applications') or product.get('applications_intro') or product.get('technologies')):
        raise ValueError('Applications/technology content needs a layout decision: this accepted page has no applications section')
    if intro:
        field(intro, *pair(product, 'applications_intro'), story=cid, path='applications_intro')
        container = soup.select_one('.application-list')
        prototype = copy.deepcopy(container.select_one('.application-item'))
        container.clear()
        for i, feature in enumerate(product.get('applications', []), 1):
            node = copy.deepcopy(prototype); node.select_one('span').string = f'{i:02}'
            field(node.h3, *pair(feature, 'title'), story=cid, path=f'applications.{i - 1}.title')
            field(node.p, *pair(feature, 'description'), story=cid, path=f'applications.{i - 1}.description')
            container.append(node)
        for ref in product.get('technologies', []):
            tech = technologies[ref]
            field(soup.select_one('#technology-title'), *pair(tech, 'title'), story='technology:' + ref, path='title')
            en, vi = pair(tech, 'summary')
            if len(en.splitlines()) != len(vi.splitlines()):
                raise ValueError('Technology language item count differs')
            ul = soup.select_one('.technology-list'); ul.clear()
            for a, b in zip(en.splitlines(), vi.splitlines()):
                li = soup.new_tag('li'); field(li, a, b, story='technology:' + ref); ul.append(li)
    application_image = soup.select_one('.application-image img')
    application_asset = next((f['media'] for f in product.get('applications', []) if f.get('media')), None)
    if application_asset and not application_image:
        raise ValueError('Application media needs a layout decision: this accepted page has no application image slot')
    if application_image and application_asset:
        image(application_image, assets[application_asset], **asset_alt(application_asset))
    chapters = soup.select('article.ps-chapter')
    if len(chapters) != len(product.get('story_sections', [])):
        raise ValueError('Chapter count differs from accepted layout')
    for index, (node, chapter) in enumerate(zip(chapters, product.get('story_sections', []))):
        field(node.h2, *pair(chapter, 'heading'), story=cid, path=f'story_sections.{index}.heading')
        leaves = [x for x in node.find_all(string=True) if x.strip() and x.parent.name != 'h2' and not x.find_parent('h2')]
        en, vi = chapter_values(chapter, rows, 'en'), chapter_values(chapter, rows, 'vi')
        if not len(leaves) == len(en) == len(vi):
            raise ValueError('Chapter body structure differs from accepted layout')
        for leaf, a, b in zip(leaves, en, vi):
            span = soup.new_tag('cms-text'); field(span, a, b, story=cid); leaf.replace_with(span)
        node['data-ps-cam'] = ','.join(str(chapter[k]) for k in ('azimuth', 'elevation', 'zoom', 'target_x', 'target_y', 'target_z'))
        if chapter.get('image'):
            node['data-cms-fallback-src'] = asset_url(assets[chapter['image']])
            node['data-cms-fallback-en'], node['data-cms-fallback-vi'] = pair(assets[chapter['image']], 'alt')
    stage = soup.select_one('[data-ps-stage]')
    if stage:
        models = product.get('model', [])
        if models:
            model = models[0]
            stage['data-cms-model-front'] = str(float(model.get('front_degrees', 0)))
            stage['data-cms-model-scale'] = str(float(model.get('scale', 1)))
            image(stage.select_one('.ps-fallback'), assets[model['poster']], **asset_alt(model['poster']))
        else:
            stage['data-cms-static-story'] = ''
            stage['class'] = list(dict.fromkeys(stage.get('class', []) + ['is-fallback']))
            stage.select_one('canvas')['hidden'] = ''
            fallback = stage.select_one('.ps-fallback')
            # cms-fields.js swaps this image and alt per chapter: derived.
            image(fallback, assets[product['story_sections'][0]['image']], story=cid); fallback.attrs.pop('hidden', None)
            for node in stage.select('.ps-reveal'): node['class'] = list(dict.fromkeys(node.get('class', []) + ['is-in']))
            if stage.select_one('.ps-status'): stage.select_one('.ps-status')['hidden'] = ''
            for script in soup.select('script[data-deferred-3d]'): script.decompose()
    gallery = soup.select_one('.gallery-grid')
    prototype = copy.deepcopy(gallery.figure)
    gallery.clear()
    for index, placement in enumerate(product.get('gallery', [])):
        node = copy.deepcopy(prototype)
        alt = {'story': cid, 'path': f'gallery.{index}.alt_override'} if placement.get('alt_override') else asset_alt(placement['asset'])
        image(node.img, assets[placement['asset']], placement, **alt)
        if node.figcaption:
            if placement.get('caption_override'):
                caption, source = pair(placement, 'caption_override'), {'story': cid, 'path': f'gallery.{index}.caption_override'}
            else:
                caption, source = pair(assets[placement['asset']], 'caption'), {'story': 'asset:' + placement['asset'], 'path': 'caption'}
            field(node.figcaption.span, *caption, **source)
        node.img['loading'] = 'lazy'
        gallery.append(node)
    options = soup.select('.payload-option')
    if len(options) != len(product.get('payload_options', [])):
        raise ValueError('Payload count differs from accepted layout')
    for index, (node, option) in enumerate(zip(options, product.get('payload_options', []))):
        field(node.h3, *pair(option, 'title'), story=cid, path=f'payload_options.{index}.title')
        field(node.p, *pair(option, 'description'), story=cid, path=f'payload_options.{index}.description')
    # Only the approved sales action is used; unknown destinations fail closed.
    action = product['sales_action'][0]
    if action.get('behaviour') != 'enquiry':
        raise ValueError('Unsupported sales action')
    # Every enquiry button (contact section and payload dialog) shows the
    # sales-action label. Cart, payload-open and dialog copy are interface text.
    buttons = soup.select('[data-contact]')
    if not buttons:
        raise ValueError('Sales action needs a layout decision: the accepted page has no enquiry button')
    for button in buttons:
        label(button, *pair(action, 'label'), story=cid, path='sales_action.0.label')
    script = soup.new_tag('script', src='../assets/js/cms-fields.js'); soup.body.append(script)
    return str(soup)

def label_source(product, metric, metric_path):
    """Return a metric label and its raw source: the override, else the row label."""
    if metric.get('label_override'):
        return (*pair(metric, 'label_override'), {'story': product['content_id'], 'path': metric_path + '.label_override'})
    index = next(i for i, r in enumerate(product['specifications']) if r['spec_key'] == metric['spec_key'])
    return (*pair(product['specifications'][index], 'label'), {'story': product['content_id'], 'path': f'specifications.{index}.label'})

def bind_shared_cards(soup, product, dictionary=None):
    """Bind repeated product cards by route identity.

    Card titles, summaries, cart names, slider labels and identity alt text
    follow the CMS product. Home grid taglines and figures follow card_tagline
    and card_metrics (bind_card_extras). Shortened line labels and contextual
    cutouts stay template-owned: the product schema has no card-label or
    card-image field.
    """
    key, title, changed = product['content_id'], product['title'], False
    containers = []
    for button in soup.select('[data-route="' + key + '"]'):
        if 'hp-card' in button.get('class', []):
            container = button
        else:
            container = button.find_parent(class_='slide-copy') or button.find_parent(class_='pl-model')
        if container and container not in containers:
            containers.append(container)
    for container in containers:
        heading = container.select_one('h1, h2, h3, .hp-title')
        summary = container.select_one('.descriptor, .pl-model__description')
        old_title = heading.get_text(' ', strip=True) if heading else None
        if heading:
            field(heading, title, title, story=key, path='title'); changed = True
        if summary:
            field(summary, *pair(product, 'summary'), story=key, path='summary'); changed = True
        picture = container.select_one('.pl-model__media img, .hp-media img')
        # Only an identity alt (the old product title) follows the CMS title.
        if picture and picture.get('data-cms-en') is None and picture.get('alt', '').strip() == old_title:
            field(picture, title, title, prop='alt', story=key); changed = True
        if 'slide-copy' in container.get('class', []) and old_title:
            changed = bind_slide_choice(soup, old_title, title, dictionary or {}, product) or changed
        if 'hp-card' in container.get('class', []):
            changed = bind_card_extras(soup, container, product) or changed
    for button in soup.select('[data-cart-id="uav:' + key + '"]'):
        if button.get('data-cart-name') != title:
            button['data-cart-name'] = title; changed = True
    for button in soup.select('[data-route="' + key + '"][data-product]'):
        if button['data-product'] != title:
            button['data-product'] = title; changed = True
    return changed

FIGURE_UNIT = re.compile(r'^(.*\S)\s+(kg|km|ha|m/s|minutes|min|phút)$')

def split_figure(value):
    match = FIGURE_UNIT.match(value)
    return (match[1], match[2]) if match else (value, '')

def bind_card_extras(soup, card, product):
    """Bind the Home grid tagline and key figures when the draft owns them.

    A missing field key keeps the template (record not migrated). An empty
    value removes the element. Figures read specification rows by spec_key.
    """
    changed = False
    if 'card_tagline' in product:
        tagline = card.select_one('.hp-tagline')
        en, vi = pair(product, 'card_tagline')
        if not en.strip() and not vi.strip():
            if tagline:
                tagline.decompose(); changed = True
        else:
            if tagline is None:
                tagline = soup.new_tag('span', attrs={'class': 'hp-tagline'})
                anchor = card.select_one('.hp-title')
                if anchor is None:
                    raise ValueError('Card tagline needs an .hp-title slot')
                anchor.insert_after(tagline)
            field(tagline, en, vi, story=product['content_id'], path='card_tagline'); changed = True
    if 'card_metrics' in product:
        figures = card.select_one('.hp-figures')
        metrics = product.get('card_metrics') or []
        if not metrics:
            if figures:
                figures.decompose(); changed = True
            return changed
        rows = {r['spec_key']: r for r in product['specifications']}
        if figures is None:
            figures = soup.new_tag('span', attrs={'class': 'hp-figures', 'aria-label': 'Key figures'})
            anchor = card.select_one('.hp-more')
            if anchor is None:
                raise ValueError('Card figures need an .hp-more slot')
            anchor.insert_before(figures)
        figures.clear()
        for index, metric in enumerate(metrics):
            if metric.get('component') != 'metric' or metric.get('spec_key') not in rows:
                raise ValueError('Card figure references missing specification')
            row = rows[metric['spec_key']]
            values = [metric_value(row, metric, lang) for lang in ('en', 'vi')]
            item = soup.new_tag('span'); bold = soup.new_tag('b')
            field(bold, *values, prop=None, story=product['content_id'])
            bold['data-cms-property'] = 'figure'
            number, unit = split_figure(values[0])
            bold.clear(); bold.append(number + (' ' if unit else ''))
            if unit:
                small = soup.new_tag('small'); small.string = unit; bold.append(small)
            text = soup.new_tag('cms-text')
            en, vi, source = label_source(product, metric, f'card_metrics.{index}')
            field(text, en, vi, **source)
            item.extend([bold, text]); figures.append(item)
        changed = True
    return changed

def bind_slide_choice(soup, old_title, title, dictionary, product):
    """Bind the Home slider label and its accessible name for one product."""
    choices = [c for c in soup.select('.slide-choice') if c.select_one('.slide-label') and c.select_one('.slide-label').get_text(strip=True) == old_title]
    if len(choices) > 1:
        raise ValueError('Slider label is not unique: ' + old_title)
    if not choices:
        return False
    choice = choices[0]
    en_label = 'Show ' + old_title
    if choice.get('aria-label') != en_label:
        raise ValueError('Unexpected slider accessible name: ' + str(choice.get('aria-label')))
    # The VI accessible-name prefix comes from the existing slider entries.
    prefixes = set()
    for other in soup.select('.slide-choice[aria-label^="Show "]'):
        name = other['aria-label'][len('Show '):]
        value = dictionary.get('Show ' + name, '')
        if value.endswith(' ' + name):
            prefixes.add(value[:-len(name)])
    if len(prefixes) != 1:
        raise ValueError('Slider labels have no single Vietnamese pattern')
    vi_prefix = prefixes.pop()
    field(choice.select_one('.slide-label'), title, title, story=product['content_id'], path='title')
    choice['data-cms-aria-en'], choice['data-cms-aria-vi'] = 'Show ' + title, vi_prefix + title
    # The "Show X" name is derived from the title.
    choice['data-cms-story'], choice['data-cms-derived'] = product['content_id'], ''
    choice['aria-label'] = 'Show ' + title
    # CMS owns this accessible name; the legacy dictionary must not rewrite it.
    choice['data-i18n-skip'] = ''
    return True

def bind_document(soup, products, assets, dictionary):
    """Bind model descriptors and shared product cards in one copied document."""
    changed = False
    for product in products:
        if product.get('model'):
            descriptor = soup.find(id='uav3dModel-' + product['content_id'])
            if descriptor:
                descriptor['data-resource'] = asset_url(assets[product['model'][0]['asset']])
                descriptor['data-cms-front'] = str(product['model'][0].get('front_degrees', 0))
                descriptor['data-cms-scale'] = str(product['model'][0].get('scale', 1))
                changed = True
        elif product.get('story_sections'):
            descriptor = soup.find(id='uav3dModel-' + product['content_id'])
            if descriptor:
                descriptor.decompose(); changed = True
        changed = bind_shared_cards(soup, product, dictionary) or changed
    return changed

def generate(snapshot_path, output, source):
    output, source = Path(output).resolve(), Path(source).resolve()
    if not output.is_relative_to((HERE / 'checks').resolve()) or output == (HERE / 'checks').resolve():
        raise ValueError('Private output must be below staging/checks')
    if source.parent != PROJECT.resolve() or not (source / 'index.html').is_file():
        raise ValueError('Source must be an existing multi-file version')
    snapshot = json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    assets = {x['uuid']: x['content'] for x in snapshot['stories'] if x['content']['component'] == 'creative_asset'}
    technologies = {x['uuid']: x['content'] for x in snapshot['stories'] if x['content']['component'] == 'technology'}
    products = [x['content'] for x in snapshot['stories'] if x['content']['component'] == 'uav_product']
    if {x['content_id'] for x in products} != legacy.KEYS:
        raise ValueError('Representative product set is incomplete')
    dictionary = json.loads((source / 'assets/i18n/vi.json').read_text(encoding='utf-8'))
    rendered = {}
    for product in products:
        template = (source / 'pages' / (product['content_id'] + '.html')).read_text(encoding='utf-8')
        rendered[product['content_id']] = render(template, product, assets, technologies, dictionary)
    # Validate every product before writing any candidate file.
    output.mkdir(parents=True, exist_ok=True)
    for name in ('assets', 'pages', 'products', 'applications', 'about', 'contact', 'news', 'partnerships', 'components'):
        if (source / name).exists():
            shutil.copytree(source / name, output / name, dirs_exist_ok=True)
    shutil.copy2(source / 'index.html', output / 'index.html')
    (output / 'source-code').mkdir(exist_ok=True)
    fields_source = (HERE / 'cms_fields.js').read_text(encoding='utf-8')
    (output / 'source-code/cms-fields.js').write_text(fields_source, encoding='utf-8', newline='\n')
    (output / 'assets/js/cms-fields.js').write_text(jsmin(fields_source), encoding='utf-8', newline='\n')
    for product in products:
        (output / 'pages' / (product['content_id'] + '.html')).write_text(rendered[product['content_id']], encoding='utf-8')
    # A private derived renderer reads CMS view settings. The accepted renderer
    # and its material/identity rules stay unchanged in the selected source.
    engines = [p for p in (source / 'source-code').glob('*.js') if 'const config = MODELS[block.dataset.psModel];' in p.read_text(encoding='utf-8')]
    if len(engines) != 1:
        raise ValueError('Expected one accepted product model renderer')
    engine = engines[0].read_text(encoding='utf-8')
    engine = engine.replace('const config = MODELS[block.dataset.psModel];', 'const baseConfig = MODELS[block.dataset.psModel];\n    const config = baseConfig ? {...baseConfig, front:Number(block.dataset.cmsModelFront ?? baseConfig.front), scale:Number(block.dataset.cmsModelScale ?? 1)} : null;')
    engine = engine.replace('const scale = 2.6 / Math.max(size.x, size.y, size.z);', 'const scale = 2.6 / Math.max(size.x, size.y, size.z) * config.scale;')
    minified = jsmin(engine)
    engine_name = 'cms-product-3d-' + hashlib.sha256(minified.encode()).hexdigest()[:12] + '.js'
    (output / 'source-code').mkdir(exist_ok=True)
    (output / 'source-code/cms-product-3d.js').write_text(engine, encoding='utf-8', newline='\n')
    (output / 'assets/js' / engine_name).write_text(minified, encoding='utf-8', newline='\n')
    # Route entries contain their own shell. Direct entry and refresh need the
    # same deferred CMS model URL as the root shell.
    for path in output.rglob('*.html'):
        if path.is_relative_to(output / 'assets'):
            continue
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        if bind_document(soup, products, assets, dictionary):
            if soup.select('[data-cms-en]') and not soup.select_one('script[src$="cms-fields.js"]'):
                script = soup.new_tag('script', src=('../' if path.parent.name == 'pages' else '') + 'assets/js/cms-fields.js')
                soup.body.append(script)
            path.write_text(str(soup), encoding='utf-8')
    for product in products:
        page = output / 'pages' / (product['content_id'] + '.html')
        html = page.read_text(encoding='utf-8')
        html = html.replace('../assets/js/' + engines[0].name, '../assets/js/' + engine_name)
        page.write_text(html, encoding='utf-8')
    return {'source': source.name, 'products': len(products), 'private_only': True,
            'output': str(output), 'languages': ['en', 'vi']}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot'); parser.add_argument('--output', required=True)
    parser.add_argument('--source', default=str(PROJECT / json.loads((HERE / 'config.json').read_text(encoding='utf-8'))['source']))
    args = parser.parse_args()
    print(json.dumps(generate(args.snapshot, args.output, args.source)))
