/* Cloudflare Pages advanced-mode worker. Only /api/transcribe invokes this worker.
   OPENAI_API_KEY stays in Cloudflare's encrypted server environment.
   VOICE_DB is a Pages D1 binding for atomic request limits; missing setup fails closed. */
const MAX_BODY = 4 * 1024 * 1024 + 16384;
const json = (data, status = 200) => Response.json(data, {status, headers: {
  'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
  'X-Robots-Tag': 'noindex, nofollow', 'Referrer-Policy': 'no-referrer'
}});
export async function transcribe(request, env) {
  if (!['GET', 'POST'].includes(request.method)) return json({error: 'Method not allowed'}, 405);
  if (!env.OPENAI_API_KEY || !env.VOICE_DB) return json({error: 'Voice input is not connected'}, 503);
  if (request.method === 'GET') return json({available: true});
  if (request.headers.get('Origin') !== new URL(request.url).origin) return json({error: 'Origin not allowed'}, 403);
  const ip = request.headers.get('CF-Connecting-IP');
  if (!ip) return json({error: 'Request unavailable'}, 403);
  try {
    await env.VOICE_DB.prepare('CREATE TABLE IF NOT EXISTS voice_limits (key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL)').run();
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ip));
    const key = [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
    const now = Math.floor(Date.now() / 1000);
    await env.VOICE_DB.prepare('DELETE FROM voice_limits WHERE expires <= ?').bind(now).run();
    const limit = await env.VOICE_DB.prepare('INSERT INTO voice_limits (key, count, expires) VALUES (?, 1, ?) ON CONFLICT(key) DO UPDATE SET count = count + 1 WHERE count < 6 RETURNING count').bind(key, now + 60).first();
    if (!limit) return json({error: 'Please type your question or try later'}, 429);
  } catch { return json({error: 'Voice input unavailable'}, 503); }
  if (!request.headers.get('Content-Type')?.startsWith('multipart/form-data')) return json({error: 'Audio form required'}, 415);
  if (Number(request.headers.get('Content-Length')) > MAX_BODY) return json({error: 'Recording too large'}, 413);
  const reader = request.body?.getReader(); if (!reader) return json({error: 'Audio required'}, 400);
  const pieces = []; let bytes = 0;
  try {
    while (true) {
      const {done, value} = await reader.read(); if (done) break;
      bytes += value.length;
      if (bytes > MAX_BODY) { await reader.cancel(); return json({error: 'Recording too large'}, 413); }
      pieces.push(value);
    }
    const form = await new Response(new Blob(pieces), {headers: {'Content-Type': request.headers.get('Content-Type')}}).formData();
    const audio = form.get('audio');
    if (!audio || typeof audio === 'string' || !audio.size || audio.size > 4 * 1024 * 1024) return json({error: 'Invalid audio'}, 400);
    const type = audio.type.split(';')[0];
    if (!['audio/webm', 'video/webm', 'audio/mp4', 'video/mp4'].includes(type)) return json({error: 'Unsupported recording format'}, 415);
    const upstream = new FormData();
    upstream.append('file', audio, type.includes('mp4') ? 'question.mp4' : 'question.webm');
    upstream.append('model', env.OPENAI_TRANSCRIBE_MODEL || 'gpt-transcribe');
    const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
      method: 'POST', headers: {Authorization: 'Bearer ' + env.OPENAI_API_KEY},
      body: upstream, signal: AbortSignal.timeout(30000)
    });
    if (!response.ok) return json({error: 'Speech conversion unavailable'}, 502);
    const result = await response.json();
    return json({text: typeof result.text === 'string' ? result.text.slice(0, 500) : ''});
  } catch { return json({error: 'Speech conversion unavailable'}, 502); }
}
export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname !== '/api/transcribe') return env.ASSETS.fetch(request);
    return transcribe(request, env);
  }
};
