import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const code = await readFile(new URL('./voice-worker.js', import.meta.url), 'utf8');
const {transcribe} = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const env = {OPENAI_API_KEY: 'test-placeholder', VOICE_DB: {
  prepare() { return {run: async () => ({}), bind() {return this}, first: async () => ({count: 1})}; }
}};
const request = (body, origin = 'https://example.test', headers = {}) => new Request('https://example.test/api/transcribe', {
  method: 'POST', body, headers: {Origin: origin, 'CF-Connecting-IP': '192.0.2.1', ...headers}
});
const audio = type => { const form = new FormData(); form.append('audio', new Blob(['sample'], {type}), 'question.webm'); return form; };
assert.equal((await transcribe(new Request('https://example.test/api/transcribe'), {})).status, 503);
assert.equal((await transcribe(request(audio('audio/webm'), 'https://other.test'), env)).status, 403);
assert.equal((await transcribe(request('bad'), env)).status, 415);
assert.equal((await transcribe(request(audio('audio/webm'), undefined, {'Content-Length': '99999999'}), env)).status, 413);
assert.equal((await transcribe(request(audio('text/plain')), env)).status, 415);
assert.equal((await transcribe(request(new FormData()), env)).status, 400);
const limited = {...env, VOICE_DB: {prepare() {return {run: async () => ({}), bind() {return this}, first: async () => null}}}};
assert.equal((await transcribe(request(audio('audio/webm')), limited)).status, 429);
let calls = 0;
globalThis.fetch = async (url, options) => {
  calls++; assert.equal(url, 'https://api.openai.com/v1/audio/transcriptions');
  assert.equal(options.headers.Authorization, 'Bearer test-placeholder');
  assert.equal(options.body.get('model'), 'gpt-transcribe');
  return Response.json({text: 'Please show the cargo UAV.'});
};
const response = await transcribe(request(audio('audio/webm')), env);
assert.equal(response.status, 200); assert.deepEqual(await response.json(), {text: 'Please show the cargo UAV.'});
assert.equal(response.headers.get('Cache-Control'), 'no-store'); assert.equal(calls, 1);
globalThis.fetch = async () => Response.json({error: 'private upstream error'}, {status: 401});
const failed = await transcribe(request(audio('audio/mp4')), env);
assert.equal(failed.status, 502); assert.ok(!(await failed.text()).includes('private'));
console.log('9 endpoint cases passed with a mocked upstream. No live API call.');
