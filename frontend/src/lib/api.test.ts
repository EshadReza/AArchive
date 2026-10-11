import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, getPage, request } from './api';

const fetchMock = vi.fn<typeof fetch>();
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json' },
});

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  document.cookie = 'csrftoken=; Max-Age=0; path=/';
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });

describe('session request boundary', () => {
  it('uses same-origin sessions, no redirects or caching, and no CSRF on reads', async () => {
    fetchMock.mockResolvedValue(json({ status: 'ok' }));
    expect(await request('/api/health')).toEqual({ status: 'ok' });
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init).toMatchObject({ method: 'GET', credentials: 'same-origin', mode: 'same-origin', redirect: 'error', cache: 'no-store' });
    expect(new Headers(init?.headers).has('X-CSRFToken')).toBe(false);
  });
  it('reads the current CSRF cookie on each mutation, including token rotation', async () => {
    fetchMock.mockImplementation(async () => json({ ok: true }));
    document.cookie = 'csrftoken=first-token; path=/';
    await request('/api/example', { method: 'POST', json: { name: 'example' } });
    document.cookie = 'csrftoken=second-token; path=/';
    await request('/api/example', { method: 'DELETE' });
    const first = fetchMock.mock.calls[0]![1]!;
    const second = fetchMock.mock.calls[1]![1]!;
    expect(new Headers(first.headers).get('X-CSRFToken')).toBe('first-token');
    expect(new Headers(second.headers).get('X-CSRFToken')).toBe('second-token');
    expect(first.body).toBe('{"name":"example"}');
    expect(new Headers(first.headers).get('Content-Type')).toBe('application/json');
  });
  it('rejects mutations without a CSRF token before sending anything', async () => {
    await expect(request('/api/example', { method: 'POST' })).rejects.toMatchObject({ code: 'csrf_missing' });
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it.each(['https://untrusted.invalid/api/marks', '//untrusted.invalid/api/test', '/other', '/api/../private', '/api/test#fragment'])('rejects untrusted target %s', async (path) => {
    await expect(request(path)).rejects.toMatchObject({ code: 'invalid_url' });
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it('preserves cancellation instead of reporting a network failure', async () => {
    const controller = new AbortController();
    const abort = new DOMException('Cancelled', 'AbortError');
    fetchMock.mockRejectedValue(abort);
    controller.abort();
    await expect(request('/api/example', { signal: controller.signal })).rejects.toBe(abort);
    expect(fetchMock.mock.calls[0]![1]?.signal).toBe(controller.signal);
  });
  it('represents network failures safely', async () => {
    fetchMock.mockRejectedValue(new TypeError('internal network detail'));
    await expect(request('/api/example')).rejects.toMatchObject({ code: 'network_error', status: 0 });
  });
});

describe('response contracts', () => {
  it('retains structured errors and request IDs for form feedback', async () => {
    fetchMock.mockResolvedValue(json({ code: 'invalid', message: 'Check the form.', field_errors: { name: ['Required'] }, request_id: 'request-1' }, 400));
    await expect(request('/api/example')).rejects.toMatchObject({ name: 'ApiError', code: 'invalid', status: 400, fieldErrors: { name: ['Required'] }, requestId: 'request-1' });
  });
  it('does not expose proxy HTML or internal exception text', async () => {
    fetchMock.mockResolvedValue(new Response('<h1>secret proxy detail</h1>', { status: 502 }));
    try { await request('/api/example'); }
    catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).code).toBe('http_502');
      expect((error as ApiError).message).not.toContain('secret');
      return;
    }
    throw new Error('Expected rejection');
  });
  it('accepts an empty 204 response', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    expect(await request<void>('/api/example')).toBeUndefined();
  });
  it('rejects malformed successful JSON', async () => {
    fetchMock.mockResolvedValue(new Response('not-json'));
    await expect(request('/api/example')).rejects.toMatchObject({ code: 'invalid_response' });
  });
  it('accepts paginated responses with a count or a cursor without count', async () => {
    const next = `${window.location.origin}/api/examples?cursor=next`;
    fetchMock.mockResolvedValueOnce(json({ results: [{ id: 'example' }], next, previous: null, count: 2 }));
    const page = await getPage<{ id: string }>('/api/examples');
    expect(page.results[0]?.id).toBe('example');
    fetchMock.mockResolvedValueOnce(json({ results: [], next: null, previous: '/api/examples' }));
    expect((await getPage(next)).next).toBeNull();
  });
  it('rejects malformed page envelopes and foreign pagination links', async () => {
    fetchMock.mockResolvedValueOnce(json({ results: 'invalid', next: null, previous: null }));
    await expect(getPage('/api/example')).rejects.toMatchObject({ code: 'invalid_response' });
    fetchMock.mockResolvedValueOnce(json({ results: [], next: 'https://untrusted.invalid/api/test', previous: null }));
    await expect(getPage('/api/example')).rejects.toMatchObject({ code: 'invalid_url' });
  });
});
