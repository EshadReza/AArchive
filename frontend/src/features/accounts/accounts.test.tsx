import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import { AdminAccountCreate, AdminAccountDetail, AdminAccountList } from './AdminAccounts';
import ProfilePage from './ProfilePage';
import { parseAccount } from './api';

const account = { id: 'test-id', email: 'member@iut.example', display_name: 'Member', roles: ['STUDENT'], state: 'ACTIVE', student_id: '001', approval_required: false, approved: false, email_verified: true, date_joined: '2026-10-09T00:00:00Z', invitation_pending: false };
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
const session = (admin = true) => response({ user: { ...account, roles: admin ? ['ADMINISTRATOR'] : ['STUDENT'] } });
afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'csrftoken=; Max-Age=0; path=/'; });

it('ordinary users do not request or display the administrator list', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session(false)); vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter><AdminAccountList /></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Administrator access is required');
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(account.email)).not.toBeInTheDocument();
});

it('filters accounts through the API and supports empty results', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(response({ results: [account], next: null, previous: null, count: 1 }))
    .mockResolvedValueOnce(session()).mockResolvedValueOnce(response({ results: [], next: null, previous: null, count: 0 }));
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter><AdminAccountList /></MemoryRouter>);
  expect(await screen.findByText(account.email)).toBeVisible();
  await userEvent.selectOptions(screen.getByLabelText('Role', { exact: true }), 'TEACHER');
  await userEvent.click(screen.getByRole('button', { name: 'Apply filters' }));
  expect(await screen.findByText('No accounts match these filters.')).toBeVisible();
  expect(String(fetcher.mock.calls[3]?.[0])).toContain('role=TEACHER');
});

it('creation requires explicit review and does not submit before confirmation', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(response(account, 201));
  vi.stubGlobal('fetch', fetcher); document.cookie = 'csrftoken=synthetic-csrf; path=/';
  render(<MemoryRouter><AdminAccountCreate /></MemoryRouter>);
  await userEvent.type(await screen.findByLabelText(/^Email/), 'invited@iut.example');
  await userEvent.type(screen.getByLabelText(/Display name/), 'Invited');
  await userEvent.click(screen.getByRole('button', { name: 'Review account' }));
  const heading = await screen.findByRole('heading', { name: 'Review account invitation' });
  await waitFor(() => expect(heading).toHaveFocus());
  expect(fetcher).toHaveBeenCalledTimes(1);
  await userEvent.click(screen.getByRole('button', { name: 'Confirm and invite' }));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(JSON.parse((fetcher.mock.calls[1]?.[1] as RequestInit).body as string)).toEqual({ email: 'invited@iut.example', display_name: 'Invited', student_id: null, roles: ['STUDENT'], approval_required: true });
});

it('role changes show previous/new roles and cancel sends no mutation', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(response(account));
  vi.stubGlobal('fetch', fetcher);
  render(<MemoryRouter initialEntries={['/admin/users/test-id']}><Routes><Route path="/admin/users/:id" element={<AdminAccountDetail />} /></Routes></MemoryRouter>);
  await userEvent.click(await screen.findByRole('checkbox', { name: 'Teacher' }));
  await userEvent.click(screen.getByRole('button', { name: 'Review roles' }));
  expect(await screen.findByText('From: STUDENT')).toBeVisible();
  expect(screen.getByText('To: STUDENT, TEACHER')).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it('profile submits only display_name and preserves identity as read-only text', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session(false)).mockResolvedValueOnce(response(account)).mockResolvedValueOnce(response({ ...account, display_name: 'New name' }));
  vi.stubGlobal('fetch', fetcher); document.cookie = 'csrftoken=synthetic-csrf; path=/';
  render(<MemoryRouter><ProfilePage /></MemoryRouter>);
  const field = await screen.findByLabelText(/Display name/);
  await userEvent.clear(field); await userEvent.type(field, 'New name');
  await userEvent.click(screen.getByRole('button', { name: 'Save profile' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Profile saved');
  expect(JSON.parse((fetcher.mock.calls[2]?.[1] as RequestInit).body as string)).toEqual({ display_name: 'New name' });
  expect(screen.queryByRole('textbox', { name: 'Email' })).not.toBeInTheDocument();
});

it('validates admin account shapes and permits closed states for admin reads', () => {
  expect(parseAccount({ ...account, state: 'SUSPENDED' }).state).toBe('SUSPENDED');
  expect(() => parseAccount({ ...account, roles: ['ROOT'] })).toThrow();
  expect(() => parseAccount({ ...account, approved: 'true' })).toThrow();
});
