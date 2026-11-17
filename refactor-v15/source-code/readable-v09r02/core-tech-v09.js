/* CT UAV main website refactor-v09 r02 (10 Nov 2026): Home "Master 6 core technologies" cards.
   One card is open at a time. Click, Enter or Space opens a card. On wide screens, mouse hover
   movement (after a short pause) and keyboard focus also open a card. Arrow keys, Home and End move focus. */
(() => {
  'use strict';
  const init = () => {
    document.querySelectorAll('[data-ct6]').forEach((list) => {
      if (list.dataset.ct6Ready) return;
      list.dataset.ct6Ready = '1';
      const cards = [...list.querySelectorAll('[data-ct6-card]')];
      const toggles = cards.map((card) => card.querySelector('.ct6-card__toggle'));
      if (!cards.length || toggles.some((toggle) => !toggle)) return;
      const wide = matchMedia('(min-width: 701px)');
      let timer = 0;
      const open = (card) => {
        clearTimeout(timer);
        cards.forEach((item, index) => {
          const on = item === card;
          item.classList.toggle('is-open', on);
          toggles[index].setAttribute('aria-expanded', String(on));
        });
      };
      cards.forEach((card, index) => {
        const toggle = toggles[index];
        toggle.addEventListener('click', () => open(card));
        // Open on hover only after a real mouse move. A layout change under a still
        // mouse must not open another card (no chain of width changes).
        card.addEventListener('pointermove', (event) => {
          if (event.pointerType !== 'mouse' || !wide.matches || card.classList.contains('is-open')) return;
          if (!event.movementX && !event.movementY) return;
          clearTimeout(timer);
          timer = setTimeout(() => open(card), 240);
        });
        card.addEventListener('pointerleave', () => clearTimeout(timer));
        toggle.addEventListener('focus', () => {
          let keyboard = true;
          try { keyboard = toggle.matches(':focus-visible'); } catch (error) { keyboard = true; }
          if (wide.matches && keyboard) open(card);
        });
        toggle.addEventListener('keydown', (event) => {
          const last = cards.length - 1;
          let next = -1;
          if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = index === last ? 0 : index + 1;
          else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = index === 0 ? last : index - 1;
          else if (event.key === 'Home') next = 0;
          else if (event.key === 'End') next = last;
          if (next < 0) return;
          event.preventDefault();
          toggles[next].focus();
          if (wide.matches) open(cards[next]);
        });
      });
    });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
