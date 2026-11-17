/* Server-only Storyblok preview validation. No token is sent to a browser.
   cms_preview.js uses it for the signed /cms-preview/ entry request.
   The space id is not secret; STORYBLOK_SPACE_ID can override it. */
const STORYBLOK_PREVIEW_SPACE_DEFAULT = '296496301258837';
export async function verifyStoryblokPreview(request, env, now = Date.now()) {
  const previewToken = env.STORYBLOK_PREVIEW_TOKEN;
  const space = String(env.STORYBLOK_SPACE_ID || STORYBLOK_PREVIEW_SPACE_DEFAULT);
  if (!previewToken || !space) return false;
  const query = new URL(request.url).searchParams;
  const timestamp = query.get('_storyblok_tk[timestamp]');
  const supplied = query.get('_storyblok_tk[token]');
  if (query.get('_storyblok_tk[space_id]') !== space || !/^\d{10}$/.test(timestamp || '') || !/^[a-f0-9]{40}$/.test(supplied || '')) return false;
  for (const key of ['timestamp', 'token', 'space_id']) {
    if (query.getAll(`_storyblok_tk[${key}]`).length !== 1) return false;
  }
  const seconds = Math.floor(now / 1000);
  if (Number(timestamp) > seconds || Number(timestamp) <= seconds - 3600) return false;
  const digest = await crypto.subtle.digest('SHA-1', new TextEncoder().encode(`${space}:${previewToken}:${timestamp}`));
  const expected = [...new Uint8Array(digest)].map(n => n.toString(16).padStart(2, '0')).join('');
  let difference = 0;
  for (let i = 0; i < expected.length; i++) difference |= expected.charCodeAt(i) ^ supplied.charCodeAt(i);
  return difference === 0;
}
