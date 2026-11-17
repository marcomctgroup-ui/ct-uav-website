"""Read CMS stories from the Storyblok Content Delivery API (read-only).

The token is a function argument only. It is never logged, returned, written
to a file, or included in an exception message. Uses urllib only.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

API = 'https://api.storyblok.com/v2/cdn/stories'
VERSIONS = {'draft', 'published'}
COMPONENTS = ('uav_product', 'creative_asset', 'technology', 'product_line')
# The original published pilot stays outside the CMS site generation.
PILOT_STORY_ID = 240403768382651
PILOT_COMPONENT = 'product_page'
PER_PAGE = 100
MAX_PAGES = 50
TIMEOUT = 20


class DeliveryError(RuntimeError):
    """A redacted delivery failure. The message never contains the token."""


def redact(text, token=None):
    text = re.sub(r'(token=)[^&\s\'"]+', r'\1REDACTED', str(text))
    if token:
        text = text.replace(token, 'REDACTED')
    return text


# Field-level translations: the CDN returns one language per request. The
# generator expects the Management API shape (key + key__i18n__vi).
LANGUAGES = ('vi',)
SKIP_KEYS = {'_uid', 'component', '_editable'}


def _page_url(version, token, page, per_page, language=None):
    params = {
        'token': token, 'version': version, 'per_page': per_page, 'page': page,
        'filter_query[component][in]': ','.join(COMPONENTS),
        'sort_by': 'id:asc',
    }
    if language:
        params['language'] = language
    return API + '?' + urllib.parse.urlencode(params)


def merge_language(default, translated, language):
    """Add key__i18n__<language> values from a translated CDN copy.

    Text and rich-text values only; nested bloks match by _uid. Storyblok
    returns the default text for an untranslated field, so a missing
    translation reads as the default text in this shape.
    """
    if isinstance(default, dict) and isinstance(translated, dict):
        for key in list(default):
            if key in SKIP_KEYS or '__i18n__' in key or key not in translated:
                continue
            ours, theirs = default[key], translated[key]
            if isinstance(ours, str) and isinstance(theirs, str):
                default[key + '__i18n__' + language] = theirs
            elif isinstance(ours, dict) and ours.get('type') == 'doc' and isinstance(theirs, dict):
                default[key + '__i18n__' + language] = theirs
            else:
                merge_language(ours, theirs, language)
    elif isinstance(default, list) and isinstance(translated, list):
        by_uid = {x.get('_uid'): x for x in translated if isinstance(x, dict) and x.get('_uid')}
        for index, item in enumerate(default):
            if isinstance(item, dict) and item.get('_uid'):
                other = by_uid.get(item['_uid'])
            else:
                other = translated[index] if index < len(translated) else None
            if other is not None:
                merge_language(item, other, language)
    return default


def fetch_snapshot(version, token, *, opener=None, per_page=PER_PAGE, timeout=TIMEOUT, languages=LANGUAGES):
    """Return {'stories': [...], 'version': ..., 'cv': ...} for the CMS components."""
    if version not in VERSIONS:
        raise ValueError('Unsupported Storyblok version; use draft or published')
    if not isinstance(token, str) or not token.strip():
        raise DeliveryError('Storyblok delivery token is not configured')
    opener = opener or urllib.request.urlopen
    result = _fetch(version, token, opener, per_page, timeout, None)
    for language in languages:
        copy = {x['uuid']: x for x in _fetch(version, token, opener, per_page, timeout, language)['stories']}
        for story in result['stories']:
            if story['uuid'] not in copy:
                raise DeliveryError('Storyblok CDN language copy is missing a story')
            merge_language(story['content'], copy[story['uuid']]['content'], language)
    return result


def _fetch(version, token, opener, per_page, timeout, language):
    stories, seen, cv, total = [], set(), None, None
    for page in range(1, MAX_PAGES + 1):
        url = _page_url(version, token, page, per_page, language)
        request = urllib.request.Request(url, headers={'Accept': 'application/json',
                                                       'User-Agent': 'ct-uav-staging-build'})
        try:
            with opener(request, timeout=timeout) as response:
                status = getattr(response, 'status', 200)
                if status != 200:
                    raise DeliveryError(f'Storyblok CDN request failed: HTTP {status} ({redact(url, token)})')
                headers = getattr(response, 'headers', {}) or {}
                body = response.read()
        except DeliveryError:
            raise
        except urllib.error.HTTPError as error:
            raise DeliveryError(f'Storyblok CDN request failed: HTTP {error.code} ({redact(url, token)})') from None
        except (urllib.error.URLError, OSError, ValueError) as error:
            reason = getattr(error, 'reason', None) or type(error).__name__
            raise DeliveryError(f'Storyblok CDN request failed: {redact(reason, token)} ({redact(url, token)})') from None
        try:
            data = json.loads(body.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            raise DeliveryError(f'Storyblok CDN returned invalid JSON ({redact(url, token)})') from None
        page_stories = data.get('stories') if isinstance(data, dict) else None
        if not isinstance(page_stories, list):
            raise DeliveryError('Storyblok CDN response has no story list')
        cv = data.get('cv', cv)
        if total is None:
            try:
                total = int(headers.get('Total'))
            except (TypeError, ValueError):
                total = None
        for story in page_stories:
            content = story.get('content') if isinstance(story, dict) else None
            if not isinstance(content, dict) or 'uuid' not in story or 'id' not in story:
                raise DeliveryError('Storyblok CDN story has an unexpected shape')
            if story['id'] == PILOT_STORY_ID or content.get('component') == PILOT_COMPONENT:
                continue
            if content.get('component') not in COMPONENTS:
                continue
            if story['uuid'] in seen:
                raise DeliveryError('Storyblok CDN returned a duplicate story')
            seen.add(story['uuid'])
            stories.append(story)
        fetched = page * per_page
        if len(page_stories) < per_page or (total is not None and fetched >= total):
            break
    else:
        raise DeliveryError('Storyblok CDN pagination exceeded the page limit')
    return {'version': version, 'cv': cv, 'stories': stories}


def summary(snapshot):
    """Story identity and version data only. No content and no token."""
    rows = []
    for story in snapshot['stories']:
        content = story['content']
        row = {'id': story['id'], 'uuid': story['uuid'], 'component': content.get('component')}
        if content.get('content_id'):
            row['content_id'] = content['content_id']
        for key in ('published_at', 'first_published_at', 'updated_at', 'current_version_id'):
            if story.get(key) is not None:
                row[key] = story[key]
        rows.append(row)
    return {'version': snapshot.get('version'), 'cv': snapshot.get('cv'), 'stories': rows}
