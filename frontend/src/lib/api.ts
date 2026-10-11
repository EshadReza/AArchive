export type FieldErrors = Record<string, string[]>;
export type Page<T> = { results: T[]; next: string | null; previous: string | null; count?: number };
type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  json?: unknown;
  signal?: AbortSignal;
};

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status = 0,
    public readonly fieldErrors: FieldErrors = {},
    public readonly requestId?: string,
  ) { super(message); this.name = 'ApiError'; }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function csrfToken(): string | undefined {
  const cookie = document.cookie.split(';').map((part) => part.trim())
    .find((part) => part.startsWith('csrftoken='));
  if (!cookie) return undefined;
  try { return decodeURIComponent(cookie.slice('csrftoken='.length)) || undefined; }
  catch { return undefined; }
}

// Resolve absolute pagination links, but never send cookies/tokens outside /api
// on this origin. Reject redirects too, including same-origin login HTML redirects.
function apiUrl(path: string): URL {
  const fail = () => new ApiError('invalid_url', 'The API address is not permitted.');
  let url: URL;
  try { url = new URL(path, window.location.origin); }
  catch { throw fail(); }
  if (url.origin !== window.location.origin || url.username || url.password || url.hash ||
      !(url.pathname === '/api' || url.pathname.startsWith('/api/'))) throw fail();
  return url;
}

function responseError(payload: unknown, status: number): ApiError {
  const fields: FieldErrors = {};
  if (isRecord(payload) && isRecord(payload.field_errors)) {
    for (const [name, values] of Object.entries(payload.field_errors)) {
      if (Array.isArray(values) && values.every((value) => typeof value === 'string')) {
        Object.defineProperty(fields, name, { value: values, enumerable: true });
      }
    }
  }
  const valid = isRecord(payload) && typeof payload.code === 'string' && typeof payload.message === 'string';
  return new ApiError(
    valid ? payload.code as string : `http_${status}`,
    valid ? payload.message as string : 'The request could not be completed. Please try again.',
    status, fields,
    isRecord(payload) && typeof payload.request_id === 'string' ? payload.request_id : undefined,
  );
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = apiUrl(path);
  const method = options.method ?? 'GET';
  const headers = new Headers({ Accept: 'application/json' });
  if (method !== 'GET') {
    const token = csrfToken();
    if (!token) throw new ApiError('csrf_missing', 'Refresh the page before submitting this request.');
    headers.set('X-CSRFToken', token);
  }
  const init: RequestInit = {
    method, headers, mode: 'same-origin', credentials: 'same-origin', redirect: 'error',
    cache: 'no-store',
  };
  if (options.signal) init.signal = options.signal;
  if (options.json !== undefined) {
    if (method === 'GET') throw new ApiError('invalid_request', 'GET requests cannot include a body.');
    headers.set('Content-Type', 'application/json');
    init.body = JSON.stringify(options.json);
  }
  let response: Response;
  try { response = await fetch(url, init); }
  catch (error) {
    if (options.signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw error;
    throw new ApiError('network_error', 'Could not reach the server. Please try again.');
  }
  if (response.status === 204) return undefined as T;
  let payload: unknown;
  try { payload = await response.json(); }
  catch (error) {
    if (options.signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw error;
    if (!response.ok) throw responseError(null, response.status);
    throw new ApiError('invalid_response', 'The server returned an unexpected response.', response.status);
  }
  if (!response.ok) throw responseError(payload, response.status);
  return payload as T;
}

export async function getPage<T>(path: string, options: Pick<RequestOptions, 'signal'> = {}): Promise<Page<T>> {
  const payload = await request<unknown>(path, options);
  if (!isRecord(payload) || !Array.isArray(payload.results) ||
      !(payload.next === null || typeof payload.next === 'string') ||
      !(payload.previous === null || typeof payload.previous === 'string') ||
      (payload.count !== undefined && (!Number.isSafeInteger(payload.count) || (payload.count as number) < 0))) {
    throw new ApiError('invalid_response', 'The server returned an unexpected page.');
  }
  if (typeof payload.next === 'string') apiUrl(payload.next);
  if (typeof payload.previous === 'string') apiUrl(payload.previous);
  return payload as Page<T>;
}
