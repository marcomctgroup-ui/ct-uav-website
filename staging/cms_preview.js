/* Protected Storyblok draft preview for /cms-preview/. Server code only.
   Entry: a Storyblok signed preview URL (_storyblok_tk). The worker then sets a
   short session cookie for child frames, scripts, assets and navigation.
   The cookie holds an expiry and an HMAC; it never holds the Preview token.
   Cloudflare does not apply _headers to worker responses, so every preview
   response gets its headers here. Top-level names use a preview prefix because
   the build bundles all worker modules into one scope. */
import {verifyStoryblokPreview} from './cms_preview_auth.js';

const PREVIEW_ROOT = '/cms-preview';
const PREVIEW_COOKIE = 'ctuav_cms_preview';
const PREVIEW_SESSION_SECONDS = 3600;
const PREVIEW_KEY_LABEL = 'ctuav-cms-preview-session-v1';
const PREVIEW_PRODUCT_ROUTES = {
  decarb22: '/products/decarb-22/', decarb54: '/products/decarb-54/',
  'ct-crova-254': '/products/ct-crova-254/', 'ct-pegas-230': '/products/ct-pegas-230/',
};
// Copied exactly from refactor-v15/_headers (/* rule). cms_preview_test.mjs checks it.
export const PREVIEW_PUBLIC_CSP = "default-src 'self'; script-src 'self' 'wasm-unsafe-eval' 'sha256-ibzu5Vi75bPc4ljisfUA3lD50AQnZUdz/gq17UabAoo=' 'sha256-4wHLTijcGNyTIavtc2NwO0zkNxpP274ytjpr/4sD23M=' 'sha256-icqFHUYysojK3yzgxBC5PGfDF5UblPr82K9156ENyBE='; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; media-src 'self'; connect-src 'self' blob: data: https://api.storyblok.com; worker-src 'self' blob:; frame-src 'self'; frame-ancestors 'self'; object-src 'none'; base-uri 'self'; form-action 'self'";
const PREVIEW_CSP_ADDITIONS = {
  'script-src': ' https://app.storyblok.com',
  'img-src': ' https://a.storyblok.com https://a2.storyblok.com',
  'media-src': ' https://a.storyblok.com https://a2.storyblok.com',
  'connect-src': ' https://a2.storyblok.com',
  'frame-ancestors': ' https://app.storyblok.com'
};
export const PREVIEW_CSP = PREVIEW_PUBLIC_CSP.split('; ').map(directive => {
  const name = directive.split(' ')[0];
  return directive + (PREVIEW_CSP_ADDITIONS[name] || '');
}).join('; ');
const PREVIEW_FIXED_HEADERS = {
  'Content-Security-Policy': PREVIEW_CSP,
  'Cache-Control': 'no-store',
  'X-Robots-Tag': 'noindex, nofollow',
  'Referrer-Policy': 'no-referrer',
  'X-Content-Type-Options': 'nosniff',
  'Permissions-Policy': 'camera=(), microphone=(self), geolocation=(), payment=(), usb=()'
};

function previewText(message, status, extra = {}) {
  const headers = new Headers({...PREVIEW_FIXED_HEADERS, 'Content-Type': 'text/plain; charset=utf-8', ...extra});
  return new Response(message, {status, headers});
}

function previewBase64Url(bytes) {
  let text = '';
  for (const byte of new Uint8Array(bytes)) text += String.fromCharCode(byte);
  return btoa(text).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function previewFromBase64Url(text) {
  const padded = text.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((text.length + 3) % 4);
  return Uint8Array.from(atob(padded), char => char.charCodeAt(0));
}

async function previewSessionKey(env) {
  const encoder = new TextEncoder();
  const root = await crypto.subtle.importKey('raw', encoder.encode(env.STORYBLOK_PREVIEW_TOKEN),
    {name: 'HMAC', hash: 'SHA-256'}, false, ['sign']);
  const derived = await crypto.subtle.sign('HMAC', root, encoder.encode(PREVIEW_KEY_LABEL));
  return crypto.subtle.importKey('raw', derived, {name: 'HMAC', hash: 'SHA-256'}, false, ['sign', 'verify']);
}

function previewSessionMessage(expiry) {
  return new TextEncoder().encode(`${PREVIEW_KEY_LABEL}:${expiry}`);
}

export async function createPreviewSession(env, expiry) {
  const signature = await crypto.subtle.sign('HMAC', await previewSessionKey(env), previewSessionMessage(expiry));
  return `${expiry}.${previewBase64Url(signature)}`;
}

function previewCookieValue(request) {
  const values = (request.headers.get('Cookie') || '').split(';')
    .map(part => part.trim()).filter(part => part.startsWith(PREVIEW_COOKIE + '='))
    .map(part => part.slice(PREVIEW_COOKIE.length + 1));
  return values.length === 1 ? values[0] : null;
}

async function previewSessionValid(request, env, nowSeconds) {
  const value = previewCookieValue(request);
  const match = /^(\d{10})\.([A-Za-z0-9_-]{43})$/.exec(value || '');
  if (!match) return false;
  const expiry = Number(match[1]);
  if (expiry <= nowSeconds || expiry > nowSeconds + PREVIEW_SESSION_SECONDS) return false;
  try {
    // crypto.subtle.verify compares the MAC in constant time.
    return await crypto.subtle.verify('HMAC', await previewSessionKey(env), previewFromBase64Url(match[2]), previewSessionMessage(expiry));
  } catch { return false; }
}

function previewSafePath(pathname) {
  if (pathname !== PREVIEW_ROOT && !pathname.startsWith(PREVIEW_ROOT + '/')) return null;
  if (/%(2e|2f|5c|00)/i.test(pathname) || pathname.includes('\\') || pathname.includes('//')) return null;
  let decoded;
  try { decoded = decodeURIComponent(pathname); } catch { return null; }
  if (decoded.split('/').some(segment => segment === '..' || segment === '.') || /[\u0000-\u001f]/.test(decoded)) return null;
  return pathname;
}

function previewWrap(response, cookie) {
  const headers = new Headers(response.headers);
  for (const name of ['X-Frame-Options', 'Content-Security-Policy-Report-Only', 'Set-Cookie']) headers.delete(name);
  for (const [name, value] of Object.entries(PREVIEW_FIXED_HEADERS)) headers.set(name, value);
  if (cookie) headers.append('Set-Cookie', cookie);
  return new Response(response.body, {status: response.status, statusText: response.statusText, headers});
}

function previewAssetMissing(response, path) {
  if (response.status === 404) return true;
  // Pages without a 404.html can answer unknown paths with the root HTML (single-page fallback).
  const type = response.headers.get('Content-Type') || '';
  return response.ok && type.startsWith('text/html') && !/\.html?$/i.test(path);
}

export async function servePreview(request, env, now = Date.now()) {
  if (request.method !== 'GET' && request.method !== 'HEAD') return previewText('Method not allowed', 405, {Allow: 'GET, HEAD'});
  if (!env || !env.STORYBLOK_PREVIEW_TOKEN || !env.ASSETS) return previewText('Preview is not connected', 503);
  const url = new URL(request.url);
  const path = previewSafePath(url.pathname);
  if (!path) return previewText('Invalid preview path', 400);
  const nowSeconds = Math.floor(now / 1000);
  let cookie = null;
  if (url.searchParams.has('_storyblok_tk[token]') && await verifyStoryblokPreview(request, env, now)) {
    const expiry = Number(url.searchParams.get('_storyblok_tk[timestamp]')) + PREVIEW_SESSION_SECONDS;
    cookie = `${PREVIEW_COOKIE}=${await createPreviewSession(env, expiry)}; Path=${PREVIEW_ROOT}; Max-Age=${expiry - nowSeconds}; Secure; HttpOnly; SameSite=None; Partitioned`;
  } else if (!await previewSessionValid(request, env, nowSeconds)) {
    return previewText('Preview access needs a signed Storyblok link.', 401);
  }
  if (path === PREVIEW_ROOT) {
    return previewWrap(new Response(null, {status: 308, headers: {Location: PREVIEW_ROOT + '/' + url.search}}), cookie);
  }
  // The Visual Editor opens location + story full_slug. Product records live in
  // library/uav-products/<slug>; send them to the accepted product route.
  const storyMatch = /^\/cms-preview\/library\/uav-products\/([a-z0-9-]+)\/?$/.exec(path);
  if (storyMatch) {
    const route = PREVIEW_PRODUCT_ROUTES[storyMatch[1]];
    if (!route) return previewText('This record has no preview page.', 404);
    return previewWrap(new Response(null, {status: 307, headers: {Location: PREVIEW_ROOT + route + url.search}}), cookie);
  }
  const assetRequest = target => env.ASSETS.fetch(new Request(new URL(target, url.origin), {method: request.method, headers: request.headers}));
  let response = await assetRequest(path);
  if (path.startsWith(PREVIEW_ROOT + '/assets/') && previewAssetMissing(response, path)) {
    response = await assetRequest(path.slice(PREVIEW_ROOT.length));
  }
  return previewWrap(response, cookie);
}
