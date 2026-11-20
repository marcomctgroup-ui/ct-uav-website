/* v09 r02 (10 Nov 2026). Carbon Credit UAV line video: scroll "pop-out" from an inset rounded card to the largest uncropped size.
   The video source loads only on the first play() (page-loader reads data-video-src). Autoplay waits for the first scroll and for the video to be half in view.
   No crop: the full state shows the whole 16:9 frame inside the visible area below the parent Navbar (contain). Leftover space shows the light page background.
   Pin mode (landscape, the full video fills 60% or more of the visible height): the section pins with position:sticky while the card grows and centres.
   Flow mode (portrait and narrow windows): no pin, so no blank screen around a short video; the full-width video grows from the card as it scrolls to the centre.
   Reduced motion: no scroll scaling; the uncropped video stays paused on its poster until the visitor presses Play. */
(() => {
 const section = document.querySelector('[data-pl-film]');
 if (!section) return;
 const track = section.querySelector('.pl-film__track');
 const sticky = section.querySelector('.pl-film__sticky');
 const frame = section.querySelector('.pl-film__frame');
 const video = section.querySelector('.pl-film__video');
 const button = section.querySelector('.pl-film__toggle');
 const shell = document.querySelector('.pl-hero .pl-shell');
 const reduce = matchMedia('(prefers-reduced-motion: reduce)');
 const RATIO = 9 / 16, RADIUS = 22, PIN_SHARE = 0.6;
 const START = 0.55, END = -0.55; // pin mode: track top, in window heights, where the expansion starts and ends
 video.muted = true;
 let pop = false, pin = false, userPaused = false, playing = false, scrolled = scrollY > 0, posterSet = false;
 let geo = null, target = 0, current = 0, frameId = 0;

 const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
 const ease = t => t * t * (3 - 2 * t);
 const lerp = (a, b, t) => a + (b - a) * t;

 // Poster: the smallest variant that covers the full-state width at the device pixel ratio.
 const posters = (video.dataset.posterSrcset || '').split(',').map(s => s.trim().split(/\s+/)).filter(p => p[0] && p[1])
  .map(([url, w]) => [url, parseInt(w, 10)]).sort((a, b) => a[1] - b[1]);
 const setPoster = cssWidth => {
  if (posterSet || !posters.length || !(cssWidth > 0)) return;
  posterSet = true;
  const need = cssWidth * (devicePixelRatio || 1) * 0.9;
  video.poster = (posters.find(p => p[1] >= need) || posters[posters.length - 1])[0];
 };

 // Height of the parent Navbar that covers the top of this page (0 when the page is opened on its own).
 const navOffset = H => {
  try {
   const host = frameElement, header = host && parent.document.getElementById('globalHeader');
   if (header) return clamp(header.getBoundingClientRect().bottom - host.getBoundingClientRect().top, 0, H / 2);
  } catch (e) { /* no parent access */ }
  return 0;
 };

 const label = () => {
  button.dataset.state = userPaused ? 'paused' : 'playing';
  button.setAttribute('aria-label', userPaused ? 'Play video' : 'Pause video');
 };
 const play = () => {
  if (playing) return;
  playing = true;
  setPoster(frame.clientWidth || innerWidth);
  const result = video.play();
  if (result && result.catch) result.catch(() => { playing = false; });
 };
 const stop = () => {
  if (!playing && video.paused) return;
  playing = false;
  video.pause();
 };

 const clearStyles = () => {
  ['position', 'left', 'top', 'width', 'height', 'transform', 'border-radius'].forEach(p => frame.style.removeProperty(p));
  button.style.removeProperty('transform');
 };

 const measure = () => {
  const W = sticky.clientWidth, H = innerHeight;
  if (!W || !H) return null;
  const nav = navOffset(H), A = H - nav;
  section.style.setProperty('--pl-film-top', nav + 'px');
  // Full state: the largest 16:9 box inside the visible area (W x A).
  const fw = Math.min(W, A / RATIO), fh = fw * RATIO;
  const isPin = fh >= PIN_SHARE * A;
  if (isPin !== pin) { pin = isPin; section.classList.toggle('is-pin', pin); }
  clearStyles();
  let fx, fy, cw;
  if (pin) {
   fx = (W - fw) / 2;
   fy = nav + (A - fh) / 2;
   frame.style.left = fx.toFixed(2) + 'px';
   frame.style.top = fy.toFixed(2) + 'px';
   frame.style.width = fw.toFixed(2) + 'px';
   frame.style.height = fh.toFixed(2) + 'px';
   cw = Math.min(W - 24, shell ? shell.clientWidth : W - 36, 0.72 * H / RATIO, fw);
  } else {
   fx = 0; fy = 0; // flow mode: the frame keeps its own layout box (full width)
   cw = Math.min(W - 24, shell ? shell.clientWidth : W - 36, frame.clientWidth);
  }
  const box = pin ? fw : frame.clientWidth;
  setPoster(box);
  return {W, H, nav, A, fx, fy, fw: box, fh: box * RATIO, cw, s0: cw / box};
 };

 // e = 0: inset card with rounded corners; e = 1: full uncropped video.
 const render = e => {
  if (!geo) return;
  const {fx, fy, fw, fh, cw, s0} = geo;
  const s = lerp(s0, 1, e);
  let dx, dy;
  if (pin) {
   // Card: centred just below the Navbar line (CSS pulls the track up by the Navbar height, so this is its place after the hero). Full: centred below the Navbar.
   const x = lerp((geo.W - cw) / 2, fx, e), y = lerp(geo.nav, fy, e);
   dx = x - fx; dy = y - fy;
  } else {
   dx = (1 - s) * fw / 2; dy = (1 - s) * fh / 2;
  }
  frame.style.transform = `translate(${dx.toFixed(2)}px, ${dy.toFixed(2)}px) scale(${s.toFixed(4)})`;
  frame.style.borderRadius = (lerp(RADIUS, 0, e) / s).toFixed(2) + 'px';
  button.style.transform = `scale(${(1 / s).toFixed(4)})`; // keep the button at 48 px
 };

 const progress = () => {
  if (!geo) return 0;
  const top = track.getBoundingClientRect().top;
  if (pin) return ease(clamp((START * geo.H - top) / ((START - END) * geo.H), 0, 1));
  // Flow: grow while the video centre moves from the window bottom to the centre of the visible area.
  const centre = top + geo.fh / 2, from = geo.H, to = geo.nav + geo.A / 2;
  return ease(clamp((from - centre) / Math.max(1, from - to), 0, 1));
 };

 // Share of the shown video that is inside the window.
 const visibleShare = () => {
  const H = innerHeight;
  if (!H || !innerWidth) return 0;
  const box = frame.getBoundingClientRect();
  if (box.height <= 0) return 0;
  return clamp((Math.min(box.bottom, H) - Math.max(box.top, 0)) / box.height, 0, 1);
 };

 const syncPlayback = () => {
  const share = visibleShare();
  if (share < 0.15 || userPaused) stop();
  else if (share >= 0.5 && scrolled) play();
 };

 const step = () => {
  frameId = 0;
  if (pop && geo) {
   target = progress();
   const diff = target - current;
   current = Math.abs(diff) < 0.0015 ? target : current + diff * 0.22;
   render(current);
   if (current !== target) frameId = requestAnimationFrame(step);
  }
  syncPlayback();
 };
 const schedule = () => { if (!frameId) frameId = requestAnimationFrame(step); };

 const layout = () => {
  geo = measure();
  if (geo) { current = target = progress(); render(current); }
 };

 const setMode = () => {
  pop = !reduce.matches;
  section.classList.toggle('is-pop', pop);
  if (pop) layout();
  else {
   geo = null;
   pin = false;
   section.classList.remove('is-pin');
   clearStyles();
   const H = innerHeight;
   if (H) section.style.setProperty('--pl-film-top', navOffset(H) + 'px');
   setPoster(frame.clientWidth);
   // Reduced motion: stop and wait for the visitor.
   userPaused = true;
   stop();
  }
  label();
  schedule();
 };

 button.addEventListener('click', () => {
  userPaused = !userPaused;
  label();
  if (userPaused) stop(); else play();
 });
 addEventListener('scroll', () => { scrolled = true; schedule(); }, {passive: true});
 video.addEventListener('playing', schedule);
 addEventListener('resize', () => {
  if (pop) layout();
  else { setPoster(frame.clientWidth); if (innerHeight) section.style.setProperty('--pl-film-top', navOffset(innerHeight) + 'px'); }
  schedule();
 }, {passive: true});
 document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); else schedule(); });
 if (reduce.addEventListener) reduce.addEventListener('change', setMode);
 setMode();
})();
