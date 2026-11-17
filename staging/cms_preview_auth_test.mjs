import { readFile } from 'node:fs/promises';
import { webcrypto, createHash } from 'node:crypto';
import assert from 'node:assert/strict';
if (!globalThis.crypto) Object.defineProperty(globalThis, 'crypto', { value: webcrypto });
const source = await readFile(new URL('./cms_preview_auth.js', import.meta.url), 'utf8');
const { verifyStoryblokPreview: verify } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const now = 1794542400000, timestamp = String(now / 1000);
const env = { STORYBLOK_SPACE_ID: 'test-space', STORYBLOK_PREVIEW_TOKEN: 'test-fixture-only' };
const url = (time = timestamp) => {
  const query = new URLSearchParams({ '_storyblok_tk[space_id]': env.STORYBLOK_SPACE_ID,
    '_storyblok_tk[timestamp]': time,
    '_storyblok_tk[token]': createHash('sha1').update(`${env.STORYBLOK_SPACE_ID}:${env.STORYBLOK_PREVIEW_TOKEN}:${time}`).digest('hex') });
  return 'https://preview.example.test/?' + query;
};
assert.equal(await verify(new Request(url()), env, now), true);
assert.equal(await verify(new Request(url()), {}, now), false);
assert.equal(await verify(new Request(url(String(now / 1000 - 3600))), env, now), false);
assert.equal(await verify(new Request(url(String(now / 1000 + 1))), env, now), false);
assert.equal(await verify(new Request(url().replace('test-space', 'other-space')), env, now), false);
assert.equal(await verify(new Request(url() + '&_storyblok_tk%5Btimestamp%5D=' + timestamp), env, now), false);
assert.equal(await verify(new Request('https://preview.example.test/'), env, now), false);
assert.equal(await verify(new Request(url()), { ...env, STORYBLOK_PREVIEW_TOKEN: 'wrong-test-fixture' }, now), false);
const fallbackEnv = { STORYBLOK_PREVIEW_TOKEN: env.STORYBLOK_PREVIEW_TOKEN };
const fallbackUrl = (space) => 'https://preview.example.test/?' + new URLSearchParams({ '_storyblok_tk[space_id]': space,
  '_storyblok_tk[timestamp]': timestamp,
  '_storyblok_tk[token]': createHash('sha1').update(`${space}:${env.STORYBLOK_PREVIEW_TOKEN}:${timestamp}`).digest('hex') });
assert.equal(await verify(new Request(fallbackUrl('296496301258837')), fallbackEnv, now), true);
assert.equal(await verify(new Request(fallbackUrl('test-space')), fallbackEnv, now), false);
console.log('10 server preview validation checks passed. No production credential used.');
