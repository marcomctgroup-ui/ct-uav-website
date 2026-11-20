/*
 * CT UAV inquiry cart v01 - refactor v07, 6 November 2026. Readable source.
 * Delivery copy: assets/js/inquiry-cart-<sha256-12>.js (built by 20261106-batch7-sales-build.py).
 *
 * Higher-up feedback (6 Nov 2026): an "Add to Cart" button next to every product,
 * a cart that is always visible, and a form for a purchase inquiry.
 * Haykal's decisions: "Add to Cart" with one cart list; the form checks the fields
 * only and sends nothing until Batch 5B (host, recipient, privacy text) is decided.
 *
 * - Buttons: any element with [data-cart-add] (data-cart-id, data-cart-name). Click
 *   handling uses delegation, so buttons that the components catalogue renders later work too.
 * - State: localStorage, shared by all page frames of the same site. A "storage" event
 *   keeps other open frames in step. If storage is blocked, the cart stays in memory.
 * - Language: follows <html lang>, which the existing page scripts set (EN | VI switch).
 * - Vietnamese text is PENDING CONFIRMATION by a native speaker.
 */
(() => {
  'use strict';
  if (window.ctuavCart) return;

  const KEY = 'ctuav-inquiry-cart-v1';
  const MAX_QTY = 999;
  const CONTACTS = [
    ['Domestic trade', 'Thương mại nội địa', '(+84) 938 602 962', 'tel:+84938602962'],
    ['International trade', 'Thương mại quốc tế', '(+84) 906 804 601', 'tel:+84906804601'],
    ['General enquiries', 'Liên hệ chung', 'info@ctuav.global', 'mailto:info@ctuav.global']
  ];
  const TEXT = {
    en: {
      add: 'Add to Cart', added: 'Added to cart', addTo: name => `Add to Cart: ${name}`,
      cart: 'Cart', openCart: count => `Open cart, ${count} ${count === 1 ? 'product' : 'products'}`,
      title: 'Your cart', intro: 'Check the products. Then give your contact details. CT UAV uses them to answer your purchase inquiry.',
      empty: 'Your cart is empty. Use the Add to Cart button next to a product.',
      qty: 'Quantity', less: 'Less', more: 'More', remove: 'Remove', close: 'Close cart',
      details: 'Your contact details', name: 'Full name', company: 'Company', email: 'Email',
      phone: 'Phone', country: 'Country or region', message: 'Message', optional: 'optional',
      submit: 'Send purchase inquiry', required: 'Fill in this field.',
      emailBad: 'Enter a valid email address.', phoneBad: 'Enter a valid phone number.',
      needItem: 'Add at least one product to the cart.',
      note: 'Preview version: this form checks your details. It does not send them yet.',
      doneTitle: 'Your inquiry is ready',
      doneText: 'Preview version: this form does not send data yet. To order now, contact CT UAV:',
      back: 'Back to cart', done: 'Close',
      inCart: name => `${name} is in your cart.`, removed: name => `${name} is removed from your cart.`
    },
    vi: {
      add: 'Thêm vào giỏ hàng', added: 'Đã thêm vào giỏ hàng', addTo: name => `Thêm vào giỏ hàng: ${name}`,
      cart: 'Giỏ hàng', openCart: count => `Mở giỏ hàng, ${count} sản phẩm`,
      title: 'Giỏ hàng của bạn', intro: 'Kiểm tra sản phẩm, sau đó điền thông tin liên hệ. CT UAV dùng thông tin này để trả lời yêu cầu mua hàng của bạn.',
      empty: 'Giỏ hàng đang trống. Hãy bấm nút Thêm vào giỏ hàng bên cạnh sản phẩm.',
      qty: 'Số lượng', less: 'Giảm', more: 'Tăng', remove: 'Xóa', close: 'Đóng giỏ hàng',
      details: 'Thông tin liên hệ', name: 'Họ và tên', company: 'Công ty', email: 'Email',
      phone: 'Số điện thoại', country: 'Quốc gia hoặc khu vực', message: 'Lời nhắn', optional: 'không bắt buộc',
      submit: 'Gửi yêu cầu mua hàng', required: 'Vui lòng điền thông tin này.',
      emailBad: 'Vui lòng nhập email hợp lệ.', phoneBad: 'Vui lòng nhập số điện thoại hợp lệ.',
      needItem: 'Vui lòng thêm ít nhất một sản phẩm vào giỏ.',
      note: 'Bản xem trước: biểu mẫu kiểm tra thông tin nhưng chưa gửi đi.',
      doneTitle: 'Yêu cầu của bạn đã sẵn sàng',
      doneText: 'Bản xem trước: biểu mẫu này chưa gửi dữ liệu. Để đặt hàng ngay, vui lòng liên hệ CT UAV:',
      back: 'Quay lại giỏ hàng', done: 'Đóng',
      inCart: name => `${name} đã có trong giỏ hàng.`, removed: name => `Đã xóa ${name} khỏi giỏ hàng.`
    }
  };
  const FIELDS = [
    { id: 'name', type: 'text', auto: 'name', required: true },
    { id: 'company', type: 'text', auto: 'organization', required: false },
    { id: 'email', type: 'email', auto: 'email', required: true },
    { id: 'phone', type: 'tel', auto: 'tel', required: true },
    { id: 'country', type: 'text', auto: 'country-name', required: false },
    { id: 'message', type: 'textarea', auto: 'off', required: false }
  ];
  const CART_ICON = '<svg class="cart-icon" aria-hidden="true" viewBox="0 0 24 24" focusable="false"><path d="M3 4h2.2l2.3 10.2a1.6 1.6 0 0 0 1.6 1.3h8.6a1.6 1.6 0 0 0 1.6-1.2L21 8H6.4" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9.5" cy="19.6" r="1.5" fill="currentColor"/><circle cx="17.3" cy="19.6" r="1.5" fill="currentColor"/></svg>';
  const CHECK_ICON = '<svg class="cart-icon" aria-hidden="true" viewBox="0 0 24 24" focusable="false"><path d="m5 12.5 4.3 4.3L19 7.2" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
  let memory = [];
  let view = 'cart';
  let fab = null;
  let dialog = null;
  let live = null;
  const draft = {};

  const lang = () => (document.documentElement.lang === 'vi' ? 'vi' : 'en');
  const t = () => TEXT[lang()];
  const esc = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw === null) return memory.slice();
      const list = JSON.parse(raw);
      if (!Array.isArray(list)) return [];
      return list.filter(item => item && typeof item.id === 'string' && typeof item.name === 'string')
        .map(item => ({ id: item.id, name: item.name, qty: Math.min(MAX_QTY, Math.max(1, parseInt(item.qty, 10) || 1)) }));
    } catch (error) {
      return memory.slice();
    }
  }
  function save(list) {
    memory = list.slice();
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (error) { /* memory only */ }
    paint();
  }
  const count = list => list.reduce((sum, item) => sum + item.qty, 0);

  function add(id, name) {
    const list = load();
    const found = list.find(item => item.id === id);
    if (found) found.qty = Math.min(MAX_QTY, found.qty + 1);
    else list.push({ id, name, qty: 1 });
    save(list);
    announce(t().inCart(name));
    bump();
  }
  function setQty(id, qty) {
    const list = load();
    const found = list.find(item => item.id === id);
    if (!found) return;
    found.qty = Math.min(MAX_QTY, Math.max(1, qty));
    save(list);
  }
  function remove(id) {
    const list = load();
    const found = list.find(item => item.id === id);
    save(list.filter(item => item.id !== id));
    if (found) announce(t().removed(found.name));
  }

  /* While the cart window is open, content outside it is hidden from screen readers. Use the status line inside the window then. */
  function announce(message) {
    const target = () => (dialog && dialog.open && dialog.querySelector('.cart-dialog-live')) || live;
    if (!target()) return;
    target().textContent = '';
    setTimeout(() => { const node = target(); if (node) node.textContent = message; }, 40);
  }

  /* The window opens inside the page frame. Make the parent page (Navbar, CT Ency, other frames) inert while it is open,
     so that keyboard focus stays in the window. */
  let inertNodes = [];
  function setParentInert(on) {
    try {
      if (!on) {
        inertNodes.forEach(node => { node.inert = false; });
        inertNodes = [];
        return;
      }
      if (parent === window || !window.frameElement) return;
      let node = window.frameElement;
      while (node && node.parentElement) {
        [...node.parentElement.children].forEach(sibling => {
          if (sibling !== node && !sibling.inert && !['SCRIPT', 'STYLE', 'TEMPLATE', 'LINK'].includes(sibling.tagName)) {
            sibling.inert = true;
            inertNodes.push(sibling);
          }
        });
        node = node.parentElement;
        if (node === node.ownerDocument.body) break;
      }
    } catch (error) {
      inertNodes = [];
    }
  }
  function bump() {
    if (!fab || reduceMotion.matches || !fab.animate) return;
    fab.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.08)' }, { transform: 'scale(1)' }], { duration: 520, easing: 'ease-out' });
  }

  /* Add to Cart buttons: label, accessible name and a short "added" state. */
  function paintButton(button) {
    const label = button.querySelector('[data-cart-label]');
    const added = button.classList.contains('is-added');
    if (label) label.textContent = added ? t().added : t().add;
    button.setAttribute('aria-label', t().addTo(button.dataset.cartName || ''));
    const state = added ? 'check' : 'cart';
    if (button.dataset.cartIcon !== state) {
      const icon = button.querySelector('.cart-icon');
      if (icon) icon.remove();
      button.insertAdjacentHTML('afterbegin', added ? CHECK_ICON : CART_ICON);
      button.dataset.cartIcon = state;
    }
  }
  function paintButtons() {
    document.querySelectorAll('[data-cart-add]').forEach(paintButton);
  }

  function buildFab() {
    fab = document.createElement('button');
    fab.type = 'button';
    fab.className = 'cart-fab';
    fab.setAttribute('aria-haspopup', 'dialog');
    fab.setAttribute('data-i18n-skip', '');
    fab.innerHTML = `${CART_ICON}<span class="cart-fab__label"></span><span class="cart-fab__count" aria-hidden="true"></span>`;
    fab.addEventListener('click', () => open());
    document.body.appendChild(fab);
    live = document.createElement('p');
    live.className = 'cart-live';
    live.setAttribute('role', 'status');
    live.setAttribute('data-i18n-skip', '');
    document.body.appendChild(live);
  }
  function paintFab() {
    if (!fab) return;
    const total = count(load());
    fab.querySelector('.cart-fab__label').textContent = t().cart;
    const badge = fab.querySelector('.cart-fab__count');
    badge.textContent = total > 99 ? '99+' : String(total);
    badge.hidden = total === 0;
    fab.setAttribute('aria-label', t().openCart(total));
  }

  function buildDialog() {
    dialog = document.createElement('dialog');
    dialog.className = 'cart-dialog';
    dialog.setAttribute('aria-labelledby', 'cartDialogTitle');
    dialog.setAttribute('data-i18n-skip', '');
    document.body.appendChild(dialog);
    dialog.addEventListener('click', event => {
      if (event.target === dialog) { dialog.close(); return; }
      const action = event.target.closest('[data-cart-action]');
      if (!action) return;
      const id = action.dataset.id;
      const item = load().find(entry => entry.id === id);
      if (action.dataset.cartAction === 'close') dialog.close();
      if (action.dataset.cartAction === 'back') { view = 'cart'; render(); }
      if (action.dataset.cartAction === 'less' && item) setQty(id, item.qty - 1);
      if (action.dataset.cartAction === 'more' && item) setQty(id, item.qty + 1);
      if (action.dataset.cartAction === 'remove') remove(id);
    });
    dialog.addEventListener('change', event => {
      const input = event.target.closest('[data-cart-qty]');
      if (input) setQty(input.dataset.cartQty, parseInt(input.value, 10) || 1);
    });
    dialog.addEventListener('input', event => {
      const field = event.target.closest('[data-field]');
      if (!field) return;
      draft[field.dataset.field] = field.value;
      if (field.getAttribute('aria-invalid') === 'true') check(field);
    });
    dialog.addEventListener('submit', event => {
      event.preventDefault();
      submit();
    });
    dialog.addEventListener('close', () => {
      setParentInert(false);
      view = 'cart';
      if (fab) fab.focus({ preventScroll: true });
    });
  }

  function itemsMarkup(list) {
    const text = t();
    if (!list.length) return `<p class="cart-empty">${esc(text.empty)}</p>`;
    return `<ul class="cart-items">${list.map(item => `
      <li class="cart-item">
        <span class="cart-item__name">${esc(item.name)}</span>
        <span class="cart-qty" role="group" aria-label="${esc(text.qty)}: ${esc(item.name)}">
          <button type="button" class="cart-qty__step" data-cart-action="less" data-id="${esc(item.id)}" aria-label="${esc(text.less)}" ${item.qty <= 1 ? 'disabled' : ''}>−</button>
          <input type="number" inputmode="numeric" min="1" max="${MAX_QTY}" value="${item.qty}" data-cart-qty="${esc(item.id)}" aria-label="${esc(text.qty)}">
          <button type="button" class="cart-qty__step" data-cart-action="more" data-id="${esc(item.id)}" aria-label="${esc(text.more)}">+</button>
        </span>
        <button type="button" class="cart-item__remove" data-cart-action="remove" data-id="${esc(item.id)}">${esc(text.remove)}<span class="cart-sr"> ${esc(item.name)}</span></button>
      </li>`).join('')}</ul>`;
  }
  function fieldMarkup(field) {
    const text = t();
    const value = esc(draft[field.id] || '');
    const label = `${esc(text[field.id])}${field.required ? ' <span aria-hidden="true">*</span>' : ` <span class="cart-optional">(${esc(text.optional)})</span>`}`;
    const common = `id="cart-${field.id}" name="${field.id}" data-field="${field.id}" autocomplete="${field.auto}" aria-describedby="cart-${field.id}-error"${field.required ? ' required aria-required="true"' : ''}`;
    const control = field.type === 'textarea'
      ? `<textarea ${common} rows="3" maxlength="1000">${value}</textarea>`
      : `<input type="${field.type}" ${common} value="${value}" maxlength="160">`;
    return `<div class="cart-field cart-field--${field.id}"><label for="cart-${field.id}">${label}</label>${control}<p class="cart-field__error" id="cart-${field.id}-error"></p></div>`;
  }
  function render() {
    if (!dialog) return;
    const text = t();
    const list = load();
    if (view === 'done') {
      dialog.innerHTML = `
        <div class="cart-panel">
          <header class="cart-head"><h2 id="cartDialogTitle">${esc(text.doneTitle)}</h2>
            <button type="button" class="cart-close" data-cart-action="close" aria-label="${esc(text.close)}">×</button></header>
          <p class="cart-copy">${esc(text.doneText)}</p>
          <ul class="cart-contacts">${CONTACTS.map(c => `<li><span>${esc(lang() === 'vi' ? c[1] : c[0])}</span><a href="${c[3]}">${esc(c[2])}</a></li>`).join('')}</ul>
          <div class="cart-actions"><button type="button" class="cart-secondary" data-cart-action="back">${esc(text.back)}</button>
            <button type="button" class="cart-primary" data-cart-action="close">${esc(text.done)}</button></div>
        </div>`;
      addDialogLive();
      return;
    }
    dialog.innerHTML = `
      <form class="cart-panel" novalidate>
        <header class="cart-head"><h2 id="cartDialogTitle">${esc(text.title)}</h2>
          <button type="button" class="cart-close" data-cart-action="close" aria-label="${esc(text.close)}">×</button></header>
        <p class="cart-copy">${esc(text.intro)}</p>
        ${itemsMarkup(list)}
        <p class="cart-field__error cart-items-error" id="cart-items-error" tabindex="-1" role="alert"></p>
        <fieldset class="cart-fields"><legend>${esc(text.details)}</legend>${FIELDS.map(fieldMarkup).join('')}</fieldset>
        <p class="cart-note">${esc(text.note)}</p>
        <div class="cart-actions"><button type="submit" class="cart-primary">${CART_ICON}<span>${esc(text.submit)}</span></button></div>
      </form>`;
    addDialogLive();
  }
  function addDialogLive() {
    dialog.insertAdjacentHTML('beforeend', '<p class="cart-live cart-dialog-live" role="status"></p>');
  }

  function check(field) {
    const text = t();
    const value = field.value.trim();
    let message = '';
    if (field.required && !value) message = text.required;
    else if (value && field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) message = text.emailBad;
    else if (value && field.type === 'tel' && (!/^[+()\d\s.-]{7,24}$/.test(value) || value.replace(/\D/g, '').length < 7)) message = text.phoneBad;
    const error = dialog.querySelector(`#${field.id}-error`);
    if (error) error.textContent = message;
    field.setAttribute('aria-invalid', message ? 'true' : 'false');
    return !message;
  }
  function submit() {
    const text = t();
    const itemsError = dialog.querySelector('#cart-items-error');
    const noItems = !load().length;
    itemsError.textContent = noItems ? text.needItem : '';
    const bad = [...dialog.querySelectorAll('[data-field]')].filter(field => !check(field));
    if (noItems) {
      itemsError.focus();
      return;
    }
    if (bad.length) {
      bad[0].focus();
      return;
    }
    /* Batch 5B is not decided: nothing is sent. Keep the cart, clear the draft. */
    Object.keys(draft).forEach(key => { delete draft[key]; });
    view = 'done';
    render();
    dialog.querySelector('.cart-primary')?.focus();
  }

  /* The page frame runs under the site Navbar of the parent page. Start the window below the Navbar. */
  function headerOverlap() {
    try {
      if (parent === window || !window.frameElement) return 0;
      const header = parent.document.getElementById('globalHeader');
      if (!header) return 0;
      const box = header.getBoundingClientRect();
      const style = parent.getComputedStyle(header);
      if (style.visibility === 'hidden' || style.display === 'none' || box.bottom <= 0) return 0;
      return Math.max(0, Math.round(box.bottom - window.frameElement.getBoundingClientRect().top));
    } catch (error) {
      return 0;
    }
  }

  function open() {
    if (!dialog) return;
    view = 'cart';
    dialog.style.setProperty('--cart-top', `${headerOverlap()}px`);
    render();
    if (!dialog.open) {
      dialog.showModal();
      setParentInert(true);
    }
    dialog.querySelector('.cart-close')?.focus();
  }

  function paint() {
    paintFab();
    paintButtons();
    if (dialog && dialog.open) {
      const active = document.activeElement;
      const key = active && (active.dataset.field || active.dataset.cartQty);
      const action = active && active.dataset.cartAction;
      const id = active && active.dataset.id;
      render();
      if (key) dialog.querySelector(`[data-field="${key}"], [data-cart-qty="${key}"]`)?.focus();
      else if (action && id) (dialog.querySelector(`[data-cart-action="${action}"][data-id="${id}"]:not([disabled])`) || dialog.querySelector('.cart-close'))?.focus();
    }
  }

  document.addEventListener('click', event => {
    const button = event.target.closest('[data-cart-add]');
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    add(button.dataset.cartId, button.dataset.cartName);
    button.classList.add('is-added');
    paintButton(button);
    clearTimeout(button.cartTimer);
    button.cartTimer = setTimeout(() => { button.classList.remove('is-added'); paintButton(button); }, 2400);
  }, true);

  addEventListener('storage', event => { if (event.key === KEY) paint(); });
  addEventListener('message', event => {
    if (event.source !== parent || event.data?.namespace !== 'ctuav-demo') return;
    if (event.data.type === 'view-active' && !event.data.active && dialog?.open) dialog.close();
  });
  new MutationObserver(() => paint()).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

  function start() {
    memory = load();
    buildFab();
    buildDialog();
    paint();
    /* The components catalogue renders its cards again after each filter or page change. */
    new MutationObserver(records => records.forEach(entry => entry.addedNodes.forEach(node => {
      if (node.nodeType !== 1 || node.closest('.cart-dialog')) return;
      if (node.matches('[data-cart-add]')) paintButton(node);
      node.querySelectorAll('[data-cart-add]').forEach(paintButton);
    }))).observe(document.body, { childList: true, subtree: true });
    if (location.hash === '#cart') open();
  }
  window.ctuavCart = { open, add, count: () => count(load()) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
