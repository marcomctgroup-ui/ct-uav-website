(function () {
  'use strict';

  var API_URL = '/api/cms/decarb22';
  var TIMEOUT_MS = 5000;

  var fetchedContent = null;

  function isValidTable(table) {
    if (!table || !Array.isArray(table.tbody) || table.tbody.length === 0) return false;
    for (var i = 0; i < table.tbody.length; i++) {
      var row = table.tbody[i];
      if (!row || !Array.isArray(row.body) || row.body.length < 2) return false;
      if (typeof row.body[0].value !== 'string' || typeof row.body[1].value !== 'string') return false;
      if (row.body[0].value.trim() === '' || row.body[1].value.trim() === '') return false;
    }
    return true;
  }

  function isValidLang(content, heroKey, introKey, tableKey) {
    return !!content &&
      typeof content[heroKey] === 'string' && content[heroKey].trim() !== '' &&
      typeof content[introKey] === 'string' && content[introKey].trim() !== '' &&
      isValidTable(content[tableKey]);
  }

  function isValidContent(content) {
    return !!content && content.component === 'product_page';
  }

  function currentLang() {
    if (window.ctuavI18n && typeof window.ctuavI18n.lang === 'string') return window.ctuavI18n.lang;
    return document.documentElement.lang === 'vi' ? 'vi' : 'en';
  }

  function applyLanguage(lang) {
    if (!fetchedContent) return;
    var heroKey = lang === 'vi' ? 'hero_role_vi' : 'hero_role';
    var introKey = lang === 'vi' ? 'applications_intro_vi' : 'applications_intro';
    var tableKey = lang === 'vi' ? 'specifications_table_vi' : 'specifications_table';

    /* Fall back to English fields if this language's fields are missing or malformed,
       rather than leaving the page half-updated. */
    if (!isValidLang(fetchedContent, heroKey, introKey, tableKey)) {
      heroKey = 'hero_role';
      introKey = 'applications_intro';
      tableKey = 'specifications_table';
      if (!isValidLang(fetchedContent, heroKey, introKey, tableKey)) return;
    }

    var heroEl = document.querySelector('[data-cms-field="hero_role"]');
    if (heroEl) {
      heroEl.textContent = fetchedContent[heroKey];
      /* Only now take over from the page's generic translator: it has no entry for
         CMS-sourced text, so leaving this unset lets it keep translating the static
         fallback correctly whenever the Storyblok fetch itself failed. */
      heroEl.setAttribute('data-i18n-skip', '');
    }

    var introEl = document.querySelector('[data-cms-field="applications_intro"]');
    if (introEl) {
      introEl.textContent = fetchedContent[introKey];
      introEl.setAttribute('data-i18n-skip', '');
    }

    var tbodyEl = document.querySelector('[data-cms-field="specifications_table"]');
    if (tbodyEl) {
      tbodyEl.setAttribute('data-i18n-skip', '');
      var fragment = document.createDocumentFragment();
      var rows = fetchedContent[tableKey].tbody;
      for (var i = 0; i < rows.length; i++) {
        var cells = rows[i].body;
        var tr = document.createElement('tr');
        var th = document.createElement('th');
        th.setAttribute('scope', 'row');
        th.textContent = cells[0].value;
        var td = document.createElement('td');
        td.textContent = cells[1].value;
        tr.appendChild(th);
        tr.appendChild(td);
        fragment.appendChild(tr);
      }
      tbodyEl.textContent = '';
      tbodyEl.appendChild(fragment);
    }
  }

  function watchLanguageChanges() {
    if (typeof MutationObserver !== 'function') return;
    new MutationObserver(function () {
      applyLanguage(currentLang());
    }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  }

  function loadFromStoryblok() {
    if (typeof fetch !== 'function') return;
    var controller = (typeof AbortController === 'function') ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, TIMEOUT_MS) : null;
    fetch(API_URL, controller ? { signal: controller.signal } : {})
      .then(function (response) {
        if (!response.ok) throw new Error('Storyblok fetch failed: ' + response.status);
        return response.json();
      })
      .then(function (data) {
        var content = data && data.story && data.story.content;
        if (isValidContent(content)) {
          fetchedContent = content;
          applyLanguage(currentLang());
          watchLanguageChanges();
        }
      })
      .catch(function () {
        /* Fetch failed or shape was unexpected: keep the page's existing approved static copy. */
      })
      .then(function () {
        if (timer) clearTimeout(timer);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadFromStoryblok);
  } else {
    loadFromStoryblok();
  }
})();
