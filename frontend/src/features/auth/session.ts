import { ApiError, request } from '../../lib/api';

export type Account = { id: string; email: string; display_name: string; state: string; roles: string[] };
const roles = ['ADMINISTRATOR', 'TEACHER', 'STUDENT'];
const states = ['ACTIVE', 'INACTIVE', 'GRADUATED', 'ALUMNI'];

export function parseSession(value: unknown): Account | null {
  if (typeof value === 'object' && value !== null && 'user' in value) {
    const user = value.user;
    if (user === null) return null;
    if (typeof user === 'object' && 'id' in user && typeof user.id === 'string' &&
        'email' in user && typeof user.email === 'string' &&
        'display_name' in user && typeof user.display_name === 'string' &&
        'state' in user && typeof user.state === 'string' && states.includes(user.state) &&
        'roles' in user && Array.isArray(user.roles) && user.roles.every((role: unknown) =>
          typeof role === 'string' && roles.includes(role))) return user as Account;
  }
  throw new ApiError('invalid_response', 'The server returned an unexpected account response.');
}

export async function getSession(signal?: AbortSignal) {
  return parseSession(await request<unknown>('/api/auth/session', signal ? { signal } : {}));
}

export async function login(email: string, password: string) {
  const user = parseSession(await request<unknown>('/api/auth/login', { method: 'POST', json: { email, password } }));
  if (!user) throw new ApiError('invalid_response', 'Sign-in could not be confirmed.');
  return user;
}

export async function logout() {
  await request<void>('/api/auth/logout', { method: 'POST' });
}
