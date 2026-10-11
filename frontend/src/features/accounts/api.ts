import { ApiError, getPage, request } from '../../lib/api';
import { parseSession } from '../auth/session';
export const roles = ['STUDENT', 'TEACHER', 'ADMINISTRATOR'];
export const states = ['PENDING', 'ACTIVE', 'INACTIVE', 'GRADUATED', 'ALUMNI', 'SUSPENDED', 'ARCHIVED', 'ANONYMIZED'];
export type UserAccount = { id: string; email: string; display_name: string; student_id: string | null; roles: string[]; state: string; approval_required: boolean; approved: boolean; email_verified: boolean; date_joined: string; invitation_pending: boolean };
export function parseAccount(value: unknown): UserAccount {
  if (value && typeof value === 'object' && 'state' in value && typeof value.state === 'string' && states.includes(value.state)) {
    // Session validator enforces identity/role fields; admin reads also include closed states.
    parseSession({ user: { ...value, state: 'ACTIVE' } });
    if ('student_id' in value && (typeof value.student_id === 'string' || value.student_id === null) &&
      'approval_required' in value && typeof value.approval_required === 'boolean' &&
      'approved' in value && typeof value.approved === 'boolean' &&
      'email_verified' in value && typeof value.email_verified === 'boolean' &&
      'invitation_pending' in value && typeof value.invitation_pending === 'boolean' &&
      'date_joined' in value && typeof value.date_joined === 'string') return value as UserAccount;
  }
  throw new ApiError('invalid_response', 'The server returned an unexpected account response.');
}
export async function listAccounts(url: string, signal: AbortSignal) {
  const page = await getPage<unknown>(url, { signal });
  return { ...page, results: page.results.map(parseAccount) };
}
export async function readAccount(path: string, signal?: AbortSignal) {
  return parseAccount(await request<unknown>(path, signal ? { signal } : {}));
}
export const failureMessage = (error: unknown) => error instanceof ApiError ? error.message : 'Could not complete the request. Try again.';
