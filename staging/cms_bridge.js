/* Storyblok Visual Editor live text bridge for the protected /cms-preview/ site.
   Readable source; the build minifies it. Runs in the preview root shell and in
   child pages. It does nothing outside /cms-preview/ or outside the editor.
   Only the top preview document loads the Storyblok bridge. It updates
   data-cms-en / data-cms-vi in its own document and in every same-origin child
   frame, then asks that window's cms_fields.js (ctuavCmsApply) to show them.
   Text only: no innerHTML. Derived values cannot update live; a notice says so.
   Bridge API: https://www.storyblok.com/docs/libraries/js/preview-bridge */
(function () {
  'use strict';
  var BRIDGE_URL = 'https://app.storyblok.com/f/storyblok-v2-latest.js';
  var NOTICE_ID = 'ctuav-cms-bridge-notice';
  var NOTICE_TEXT = 'Saved values update after the next build';

  /* Value at a dotted path in story.content. Numeric segments index arrays.
     VI uses the same path with "__i18n__vi" on the last key. Strings only. */
  function resolvePath(content, path, lang) {
    if (!content || typeof content !== 'object' || typeof path !== 'string' || !path) return undefined;
    var keys = path.split('.');
    if (lang === 'vi') {
      if (/^\d+$/.test(keys[keys.length - 1])) return undefined;
      keys[keys.length - 1] += '__i18n__vi';
    }
    var value = content;
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      if (value === null || typeof value !== 'object' || !key) return undefined;
      if (Array.isArray(value)) {
        if (!/^\d+$/.test(key)) return undefined;
        value = value[Number(key)];
      } else {
        if (!Object.prototype.hasOwnProperty.call(value, key)) return undefined;
        value = value[key];
      }
    }
    return typeof value === 'string' ? value : undefined;
  }

  /* data-cms-story values that belong to one story. */
  function storyKeys(story) {
    var keys = [];
    if (!story || !story.content) return keys;
    if (typeof story.content.content_id === 'string' && story.content.content_id) keys.push(story.content.content_id);
    if (typeof story.uuid === 'string' && story.uuid) keys.push('asset:' + story.uuid, 'technology:' + story.uuid);
    return keys;
  }

  if (typeof module === 'object' && module && module.exports) module.exports = {resolvePath: resolvePath, storyKeys: storyKeys};
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (location.pathname.indexOf('/cms-preview/') !== 0) return;
  var inFrame = window.top !== window;
  var hasEditorQuery = false;
  try { hasEditorQuery = new URLSearchParams(location.search).has('_storyblok'); } catch (e) {}
  if (!inFrame && !hasEditorQuery) return;
  // A same-origin preview parent owns the bridge; this child page waits for updates.
  try {
    if (window.parent !== window && window.parent.location.pathname.indexOf('/cms-preview/') === 0) return;
  } catch (e) { /* Cross-origin parent: this is the top preview document. */ }

  var stories = {};
  var watched = typeof WeakSet === 'function' ? new WeakSet() : null;

  function frameDocuments(doc, list) {
    list.push(doc);
    watchDocument(doc);
    var frames = doc.querySelectorAll('iframe');
    for (var i = 0; i < frames.length; i++) {
      var child = null;
      try { child = frames[i].contentDocument; } catch (e) { child = null; }
      if (child && child.documentElement) frameDocuments(child, list);
    }
    return list;
  }

  function watchDocument(doc) {
    if (!watched || watched.has(doc)) return;
    watched.add(doc);
    // Capture phase receives the non-bubbling load event of each child frame.
    doc.addEventListener('load', function (event) {
      if (event.target && event.target.tagName === 'IFRAME') applyAll();
    }, true);
  }

  function applyToDocument(doc, story, keys) {
    var result = {changed: 0, derived: 0};
    var nodes = doc.querySelectorAll('[data-cms-story]');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (keys.indexOf(el.getAttribute('data-cms-story')) < 0) continue;
      if (el.hasAttribute('data-cms-path')) {
        var path = el.getAttribute('data-cms-path');
        var en = resolvePath(story.content, path, 'en');
        var vi = resolvePath(story.content, path, 'vi');
        // A blank value would make the build fall back or stop: keep the current
        // text and show the build notice instead of a live blank or EN-in-VI text.
        if (en !== undefined && !en.trim()) { en = undefined; result.derived++; }
        // Shared fields (title) and unchanged names have no VI key: VI follows EN.
        if (vi === undefined && en !== undefined) vi = en;
        else if (vi !== undefined && !vi.trim()) { vi = undefined; result.derived++; }
        if (en !== undefined) { el.setAttribute('data-cms-en', en); result.changed++; }
        if (vi !== undefined) { el.setAttribute('data-cms-vi', vi); result.changed++; }
      } else if (el.hasAttribute('data-cms-derived')) {
        result.derived++;
      }
    }
    if (result.changed) {
      var view = doc.defaultView;
      try { if (view && typeof view.ctuavCmsApply === 'function') view.ctuavCmsApply(); } catch (e) {}
    }
    return result;
  }

  function applyStory(story) {
    var keys = storyKeys(story), derived = 0;
    if (!keys.length) return 0;
    var docs = frameDocuments(document, []);
    for (var i = 0; i < docs.length; i++) derived += applyToDocument(docs[i], story, keys).derived;
    return derived;
  }

  function applyAll() {
    for (var key in stories) if (Object.prototype.hasOwnProperty.call(stories, key)) applyStory(stories[key]);
  }

  var noticeClosed = false;
  // Preview-only editor tool: fixed light colours, not a website component palette.
  function showNotice() {
    if (noticeClosed || document.getElementById(NOTICE_ID) || !document.body) return;
    var box = document.createElement('div');
    box.id = NOTICE_ID;
    box.setAttribute('role', 'status');
    box.setAttribute('aria-live', 'polite');
    box.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483000;display:flex;align-items:center;gap:8px;' +
      'max-width:calc(100vw - 32px);box-sizing:border-box;padding:8px 8px 8px 16px;background:#ffffff;color:#1f2937;' +
      'border:1px solid #d1d5db;border-radius:8px;box-shadow:0 4px 16px rgba(17,24,39,.12);' +
      'font:500 14px/1.4 Montserrat,system-ui,sans-serif;';
    var text = document.createElement('span');
    text.textContent = NOTICE_TEXT;
    var close = document.createElement('button');
    close.type = 'button';
    close.textContent = 'Close';
    close.setAttribute('aria-label', 'Close notice');
    close.style.cssText = 'min-width:44px;min-height:44px;padding:0 12px;background:#f5f5f5;color:#1f2937;' +
      'border:1px solid #d1d5db;border-radius:6px;font:600 14px/1 Montserrat,system-ui,sans-serif;cursor:pointer;';
    close.addEventListener('click', function () { noticeClosed = true; box.remove(); });
    box.appendChild(text);
    box.appendChild(close);
    document.body.appendChild(box);
  }

  function start() {
    if (typeof window.StoryblokBridge !== 'function') return;
    var bridge = new window.StoryblokBridge();
    bridge.on('input', function (payload) {
      var story = payload && payload.story;
      if (!story || !story.content || typeof story.content !== 'object') return;
      var keys = storyKeys(story);
      if (!keys.length) return;
      stories[keys[0]] = story;
      if (applyStory(story)) showNotice();
    });
    // Saved or published: values in derived and generated output need a build. No reload loop.
    bridge.on(['change', 'published'], showNotice);
  }

  var script = document.createElement('script');
  script.src = BRIDGE_URL;
  script.async = true;
  script.onload = start;
  (document.head || document.documentElement).appendChild(script);
})();
