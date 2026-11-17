/* Preview worker checks. Bundles the worker modules in build order, as one scope,
   and imports the result. Test-only fixture values; no network. */
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const read = name => readFile(new URL('./' + name, import.meta.url), 'utf8');
const order = ['voice-worker.js', 'cms_published.js', 'cms_preview_auth.js', 'cms_preview.js', 'cms_worker.js'];
let bundle = '';
for (const name of order) {
  let code = (await read(name)).replace(/\r\n/g, '\n').replace(/^import [^\n]* from '\.\/[^']+\.js';\n/gm, '');
  if (name === 'voice-worker.js') code = code.replace('export default {', 'const voiceWorker = {');
  assert(!/^import /m.test(code), name + ' keeps an import the bundler does not remove');
  bundle += code + '\n';
}
const worker = await import('data:text/javascript;base64,' + Buffer.from(bundle).toString('base64'));
const {servePreview, PREVIEW_PUBLIC_CSP, PREVIEW_CSP} = worker;
let checks = 0;
const ok = (value, message) => { assert(value, message); checks++; };
const eq = (a, b, message) => { assert.equal(a, b, message); checks++; };

// 1. Public CSP constant matches the selected source _headers /* rule.
const headersFile = (await readFile(new URL('../refactor-v15/_headers', import.meta.url), 'utf8')).replace(/\r\n/g, '\n');
const star = headersFile.split('\n/*\n')[1];
const sourceCsp = star.split('\n').find(line => line.trim().startsWith('Content-Security-Policy:')).split(':').slice(1).join(':').trim();
eq(PREVIEW_PUBLIC_CSP, sourceCsp, 'public CSP constant differs from refactor-v15/_headers');
const directive = name => PREVIEW_CSP.split('; ').find(item => item.startsWith(name + ' '));
eq(directive('frame-ancestors'), "frame-ancestors 'self' https://app.storyblok.com");
ok(directive('script-src').endsWith(' https://app.storyblok.com') && (directive('script-src').match(/'sha256-/g) || []).length === 3, 'script-src');
eq(directive('img-src'), "img-src 'self' data: blob: https://a.storyblok.com https://a2.storyblok.com");
eq(directive('default-src'), "default-src 'self'");

// Fixtures.
const now = 1794542400000, seconds = now / 1000;
const token = 'test-fixture-only', space = '296496301258837';
const files = {
  '/cms-preview/index.html': ['<!doctype html><p>draft</p>', 'text/html'],
  '/cms-preview/': ['<!doctype html><p>draft</p>', 'text/html'],
  '/cms-preview/assets/js/cms_fields.js': ['/* draft js */', 'text/javascript'],
  '/assets/img/a.webp': ['IMG', 'image/webp'],
  '/assets/js/site.js': ['/* public js */', 'text/javascript']
};
let calls = [];
const assets = (spa = false) => ({async fetch(request) {
  const path = new URL(request.url).pathname; calls.push(path);
  const file = files[path];
  if (file) return new Response(file[0], {headers: {'Content-Type': file[1], 'X-Frame-Options': 'SAMEORIGIN', 'Content-Security-Policy': "frame-ancestors 'self'"}});
  return spa ? new Response('<!doctype html>root', {headers: {'Content-Type': 'text/html'}}) : new Response('nf', {status: 404});
}});
const env = {STORYBLOK_PREVIEW_TOKEN: token, ASSETS: assets()};
const signed = (path = '/cms-preview/', time = String(seconds - 60), sig) => 'https://staging.example.test' + path + '?' + new URLSearchParams({
  '_storyblok': '1', '_storyblok_tk[space_id]': space, '_storyblok_tk[timestamp]': time,
  '_storyblok_tk[token]': sig || createHash('sha1').update(`${space}:${token}:${time}`).digest('hex')});
const get = (url, headers = {}, method = 'GET') => new Request(url, {method, headers});

// 2. Unsigned request: 401, no preview bytes, ASSETS not called.
calls = [];
let response = await servePreview(get('https://staging.example.test/cms-preview/'), env, now);
eq(response.status, 401); eq(calls.length, 0, 'ASSETS called for unsigned request');
ok(!(await response.text()).includes('draft')); eq(response.headers.get('Cache-Control'), 'no-store');
// Tampered signature without cookie.
response = await servePreview(get(signed('/cms-preview/', String(seconds - 60), 'a'.repeat(40))), env, now);
eq(response.status, 401); eq(calls.length, 0);

// 3. Valid signature: 200 + session cookie with attributes; headers replaced.
response = await servePreview(get(signed()), env, now);
eq(response.status, 200); eq(await response.text(), '<!doctype html><p>draft</p>');
const setCookie = response.headers.get('Set-Cookie');
ok(/^ctuav_cms_preview=\d{10}\.[A-Za-z0-9_-]{43}; /.test(setCookie), 'cookie value');
for (const part of ['Path=/cms-preview', 'Max-Age=3540', 'Secure', 'HttpOnly', 'SameSite=None', 'Partitioned']) ok(setCookie.split('; ').includes(part), 'cookie attribute ' + part);
ok(!setCookie.includes(token), 'token in cookie');
eq(response.headers.get('X-Frame-Options'), null, 'X-Frame-Options not removed');
eq(response.headers.get('Content-Security-Policy'), PREVIEW_CSP);
eq(response.headers.get('X-Robots-Tag'), 'noindex, nofollow');
eq(response.headers.get('Referrer-Policy'), 'no-referrer');
eq(response.headers.get('X-Content-Type-Options'), 'nosniff');
eq(response.headers.get('Cache-Control'), 'no-store');
const cookie = setCookie.split(';')[0];
const expiry = Number(cookie.split('=')[1].split('.')[0]);
eq(expiry, seconds - 60 + 3600, 'expiry = signature timestamp + 3600');

// 4. Valid cookie: 200 without a new cookie.
response = await servePreview(get('https://staging.example.test/cms-preview/assets/js/cms_fields.js', {Cookie: 'other=1; ' + cookie}), env, now);
eq(response.status, 200); eq(await response.text(), '/* draft js */'); eq(response.headers.get('Set-Cookie'), null);

// 5. Expired, tampered, duplicated or foreign-key cookies: 401.
response = await servePreview(get('https://staging.example.test/cms-preview/', {Cookie: cookie}), env, (expiry + 1) * 1000);
eq(response.status, 401, 'expired cookie');
const [expiryText, mac] = cookie.split('=')[1].split('.');
const flipped = mac.slice(0, -2) + (mac.at(-2) === 'A' ? 'B' : 'A') + mac.at(-1);
for (const bad of [`ctuav_cms_preview=${expiryText}.${flipped}`, `ctuav_cms_preview=${expiry + 10}.${mac}`, `${cookie}; ${cookie}`, 'ctuav_cms_preview=' + expiryText]) {
  eq((await servePreview(get('https://staging.example.test/cms-preview/', {Cookie: bad}), env, now)).status, 401, 'bad cookie ' + bad);
}
eq((await servePreview(get('https://staging.example.test/cms-preview/', {Cookie: cookie}), {...env, STORYBLOK_PREVIEW_TOKEN: 'other-fixture'}, now)).status, 401, 'cookie under another key');
// Cookie expiry above the one-hour cap is rejected.
const far = await worker.createPreviewSession(env, seconds + 7200);
eq((await servePreview(get('https://staging.example.test/cms-preview/', {Cookie: 'ctuav_cms_preview=' + far}), env, now)).status, 401);

// 6. Methods.
for (const method of ['POST', 'PUT', 'DELETE']) {
  response = await servePreview(get('https://staging.example.test/cms-preview/', {Cookie: cookie}, method), env, now);
  eq(response.status, 405); eq(response.headers.get('Allow'), 'GET, HEAD');
}
eq((await servePreview(get('https://staging.example.test/cms-preview/', {Cookie: cookie}, 'HEAD'), env, now)).status, 200);

// 7. Traversal and paths outside /cms-preview/.
calls = [];
for (const path of ['/cms-preview/%2e%2e/index.html', '/cms-preview/assets/..%2fsecret', '/cms-preview/a%5c..%5cb', '/cms-preview//assets/x', '/cms-preview-other/x', '/assets/js/site.js', '/cms-preview/%00']) {
  response = await servePreview(new Request('https://staging.example.test' + path, {headers: {Cookie: cookie}}), env, now);
  ok([400].includes(response.status), 'traversal accepted: ' + path + ' ' + response.status);
}
eq(calls.length, 0, 'ASSETS called for a rejected path');

// 8. Asset fallback to public /assets/ (404 mode and single-page fallback mode).
for (const mode of [false, true]) {
  calls = [];
  response = await servePreview(get('https://staging.example.test/cms-preview/assets/img/a.webp', {Cookie: cookie}), {...env, ASSETS: assets(mode)}, now);
  eq(response.status, 200); eq(await response.text(), 'IMG');
  assert.deepEqual(calls, ['/cms-preview/assets/img/a.webp', '/assets/img/a.webp']); checks++;
  eq(response.headers.get('X-Frame-Options'), null);
}
// No fallback outside assets; missing page stays 404 with preview headers.
calls = [];
response = await servePreview(get('https://staging.example.test/cms-preview/pages/missing.html', {Cookie: cookie}), env, now);
eq(response.status, 404); assert.deepEqual(calls, ['/cms-preview/pages/missing.html']); checks++;
eq(response.headers.get('Cache-Control'), 'no-store');

// 9. /cms-preview redirects to /cms-preview/ after auth (query kept, same origin).
response = await servePreview(get(signed('/cms-preview')), env, now);
eq(response.status, 308); ok(response.headers.get('Location').startsWith('/cms-preview/?_storyblok=1'));
ok(response.headers.get('Set-Cookie')?.startsWith('ctuav_cms_preview='));
eq((await servePreview(get('https://staging.example.test/cms-preview'), env, now)).status, 401);

// 9b. Visual Editor story slugs redirect to the accepted product route (query kept).
response = await servePreview(get(signed('/cms-preview/library/uav-products/decarb54')), env, now);
eq(response.status, 307); ok(response.headers.get('Location').startsWith('/cms-preview/products/decarb-54/?_storyblok=1'));
ok(response.headers.get('Set-Cookie')?.startsWith('ctuav_cms_preview='));
eq((await servePreview(get(signed('/cms-preview/library/uav-products/unknown-model/')), env, now)).status, 404);
eq((await servePreview(get('https://staging.example.test/cms-preview/library/uav-products/decarb54'), env, now)).status, 401);

// 10. Missing configuration fails closed.
calls = [];
eq((await servePreview(get(signed()), {ASSETS: assets()}, now)).status, 503);
eq((await servePreview(get(signed()), {STORYBLOK_PREVIEW_TOKEN: token}, now)).status, 503);
eq(calls.length, 0);

// 11. Space id: constant fallback, env override still applies.
eq((await servePreview(get(signed()), {...env, STORYBLOK_SPACE_ID: '296496301258837'}, now)).status, 200);
eq((await servePreview(get(signed()), {...env, STORYBLOK_SPACE_ID: 'other-space'}, now)).status, 401);

// 12. Router: preview, CMS API and voice fallback in the bundled default export.
const router = worker.default;
calls = [];
eq((await router.fetch(get('https://staging.example.test/cms-preview/'), env, {})).status, 401);
eq((await router.fetch(get('https://staging.example.test/api/cms/decarb22'), {}, {})).status, 503);
eq((await router.fetch(get('https://staging.example.test/api/transcribe'), {}, {})).status, 503);
response = await router.fetch(get('https://staging.example.test/assets/js/site.js'), env, {});
eq(response.status, 200); eq(await response.text(), '/* public js */');
eq((await router.fetch(get('https://staging.example.test/cms-previewx'), env, {})).status, 404, 'non-preview path served as preview');
assert.deepEqual(calls, ['/assets/js/site.js', '/cms-previewx']); checks++;
// 13. Bridge path resolver (cms_bridge.js) in a plain context: no DOM, so no side effects.
const vm = await import('node:vm');
const bridgeModule = {exports: {}};
vm.runInNewContext(await read('cms_bridge.js'), {module: bridgeModule});
const {resolvePath, storyKeys} = bridgeModule.exports;
const content = {content_id: 'decarb-22', title: 'DECARB 22', title__i18n__vi: 'DECARB 22 VI', count: 3,
  body: [{headline: 'First', headline__i18n__vi: 'Thu nhat'}, {headline: 'Second'}], tags: ['a', 'b']};
eq(resolvePath(content, 'title', 'en'), 'DECARB 22');
eq(resolvePath(content, 'title', 'vi'), 'DECARB 22 VI');
eq(resolvePath(content, 'body.0.headline', 'en'), 'First');
eq(resolvePath(content, 'body.0.headline', 'vi'), 'Thu nhat');
eq(resolvePath(content, 'body.1.headline', 'vi'), undefined, 'missing VI');
eq(resolvePath(content, 'body.5.headline', 'en'), undefined, 'missing index');
eq(resolvePath(content, 'body.x.headline', 'en'), undefined, 'non-numeric array key');
eq(resolvePath(content, 'tags.1', 'en'), 'b');
eq(resolvePath(content, 'tags.1', 'vi'), undefined);
eq(resolvePath(content, 'count', 'en'), undefined, 'non-string ignored');
eq(resolvePath(content, 'body', 'en'), undefined);
eq(resolvePath(content, 'title.length', 'en'), undefined);
eq(resolvePath(content, 'constructor', 'en'), undefined, 'prototype key');
eq(resolvePath(content, '', 'en'), undefined);
eq(resolvePath(null, 'title', 'en'), undefined);
assert.deepEqual([...storyKeys({uuid: 'u-1', content})], ['decarb-22', 'asset:u-1', 'technology:u-1']); checks++;
assert.deepEqual([...storyKeys({content: {}})], []); checks++;
console.log(`${checks} preview worker checks passed (bundle of ${order.length} modules parsed). Test fixtures only; no network.`);
