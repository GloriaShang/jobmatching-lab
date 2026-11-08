import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';
import classify from './api/classify.js';

const envKeys = ['APP_SECRET', 'GEMINI_API_KEY', 'GEMINI_MODEL'];
const originalEnv = Object.fromEntries(envKeys.map(key => [key, process.env[key]]));

beforeEach(() => {
  for (const key of envKeys) delete process.env[key];
});

afterEach(() => {
  for (const key of envKeys) {
    if (originalEnv[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnv[key];
  }
});

async function request(method, body, headers = {}) {
  const result = { headers: {} };
  const res = {
    setHeader(name, value) { result.headers[name] = value; },
    status(code) { result.status = code; return this; },
    json(payload) { result.body = payload; },
    end() {},
  };
  await classify({ method, body, headers }, res);
  return result;
}

test('health check and CORS preflight work without credentials', async () => {
  const health = await request('GET');
  assert.equal(health.status, 200);
  assert.equal(health.body.status, 'ok');
  const preflight = await request('OPTIONS');
  assert.equal(preflight.status, 200);
  assert.equal(preflight.headers['Access-Control-Allow-Methods'], 'GET, POST, OPTIONS');
  assert.equal((await request('DELETE')).status, 405);
});

test('validates the caller, input and configuration before contacting Gemini', async () => {
  process.env.APP_SECRET = 'mock-token';
  const headers = { 'x-app-token': 'mock-token' };
  assert.equal((await request('POST', { majorName: 'Physics' })).status, 401);
  assert.equal((await request('POST', { majorName: '   ' }, headers)).status, 400);
  assert.equal((await request('POST', { majorName: 123 }, headers)).status, 400);
  assert.equal((await request('POST', { majorName: 'Physics' }, headers)).status, 500);
});

test('classifies a trimmed name and sends credentials only in request headers', async t => {
  process.env.GEMINI_API_KEY = 'mock-key';
  const fetch = t.mock.method(globalThis, 'fetch', async () => Response.json({
    candidates: [{ content: { parts: [
      { thought: true, text: 'ignored' },
      { text: '{"category":"Engineering"}' },
    ] } }],
  }));
  const result = await request('POST', { majorName: ' 机电一体化技术 ' });
  assert.equal(result.status, 200);
  assert.deepEqual(result.body, { majorName: '机电一体化技术', category: 'Engineering' });
  assert.equal(fetch.mock.callCount(), 1);
  const [url, options] = fetch.mock.calls[0].arguments;
  assert.equal(url, 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent');
  assert.equal(options.headers['x-goog-api-key'], 'mock-key');
  const payload = JSON.parse(options.body);
  assert.equal(payload.contents[0].parts[0].text, '机电一体化技术');
  assert.deepEqual(payload.generationConfig.responseSchema.properties.category.enum,
    ['Engineering', 'Science', 'Business', 'Humanities', 'Agriculture', 'Other']);
});

test('reports missing or out-of-taxonomy model output as an upstream error', async t => {
  process.env.GEMINI_API_KEY = 'mock-key';
  const fetch = t.mock.method(globalThis, 'fetch', async () => Response.json({}));
  fetch.mock.mockImplementationOnce(async () => Response.json({
    candidates: [{ content: { parts: [{ text: '{"category":"Other fields"}' }] } }],
  }));
  assert.equal((await request('POST', { majorName: 'Unknown' })).status, 502);
  assert.equal((await request('POST', { majorName: 'Unknown' })).status, 502);
});

test('redacts upstream error details and respects the configured model', async t => {
  process.env.GEMINI_API_KEY = 'mock-key';
  process.env.GEMINI_MODEL = 'gemini-2.5-flash';
  const fetch = t.mock.method(globalThis, 'fetch',
    async () => new Response('internal provider error', { status: 429 }));
  const result = await request('POST', { majorName: 'Physics' });
  assert.equal(result.status, 429);
  assert.deepEqual(result.body, { error: 'Gemini API error' });
  assert.match(fetch.mock.calls[0].arguments[0], /gemini-2\.5-flash:generateContent$/);
});
