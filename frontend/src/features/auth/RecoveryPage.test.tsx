import { screen, render, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import RecoveryPage from './RecoveryPage';

const account = { id: 'synthetic-id', email: 'member@iut.example', display_name: 'Member', state: 'ACTIVE', roles: ['STUDENT'] };
const bootstrap = (signedIn = false) => new Response(JSON.stringify({ user: signedIn ? account : null }));
afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'csrftoken=; Max-Age=0; path=/'; window.history.replaceState(null, '', '/'); });
function ready() { document.cookie = 'csrftoken=synthetic-csrf; path=/'; }

it('requests a reset with email only and presents a generic status', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(bootstrap()).mockResolvedValueOnce(new Response(JSON.stringify({ message: 'If this account is eligible, a password reset email will arrive.' }), { status: 202 }));
  vi.stubGlobal('fetch', fetcher); ready();
  render(<MemoryRouter><RecoveryPage mode="request" /></MemoryRouter>);
  await userEvent.type(await screen.findByLabelText(/Account email/), 'member@iut.example');
  await userEvent.click(screen.getByRole('button', { name: 'Send reset link' }));
  expect(await screen.findByRole('status')).toHaveTextContent('If this account is eligible');
  await waitFor(() => expect(screen.getByRole('status')).toHaveFocus());
  expect(JSON.parse((fetcher.mock.calls[1]?.[1] as RequestInit).body as string)).toEqual({ email: 'member@iut.example' });
});

it('reset links require explicit submission and clear passwords on rejection', async () => {
  const token = 'a'.repeat(43); window.history.replaceState(null, '', `/reset-password#token=${token}`);
  const fetcher = vi.fn().mockResolvedValueOnce(bootstrap()).mockResolvedValueOnce(new Response(JSON.stringify({ code: 'recovery_invalid', message: 'Request a new reset link.' }), { status: 400 }));
  vi.stubGlobal('fetch', fetcher); ready();
  render(<MemoryRouter><RecoveryPage mode="confirm" /></MemoryRouter>);
  await userEvent.type(await screen.findByLabelText(/New password/), 'synthetic-new-password');
  expect(window.location.hash).toBe(''); expect(fetcher).toHaveBeenCalledTimes(1);
  await userEvent.click(screen.getByRole('button', { name: 'Reset password' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Request a new reset link');
  await waitFor(() => expect(screen.getByRole('alert')).toHaveFocus());
  expect(screen.getByLabelText(/New password/)).toHaveValue('');
  expect(JSON.parse((fetcher.mock.calls[1]?.[1] as RequestInit).body as string)).toEqual({ token, password: 'synthetic-new-password' });
});

it('requires a session for change and gives anonymous users a reset route', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(bootstrap()));
  render(<MemoryRouter><RecoveryPage mode="change" /></MemoryRouter>);
  expect(await screen.findByText('Sign in to change your password, or request a reset link.')).toBeVisible();
  expect(screen.queryByLabelText(/Current password/)).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Request a new reset link' })).toHaveAttribute('href', '/forgot-password');
});

it('changes passwords, clears credentials and directs the user to sign in again', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(bootstrap(true)).mockResolvedValueOnce(new Response(JSON.stringify({ message: 'Password updated. All sessions have ended. Sign in with your new password.' })));
  vi.stubGlobal('fetch', fetcher); ready();
  render(<MemoryRouter><RecoveryPage mode="change" /></MemoryRouter>);
  await userEvent.type(await screen.findByLabelText(/Current password/), 'synthetic-old-password');
  await userEvent.type(screen.getByLabelText(/New password/), 'synthetic-new-password');
  await userEvent.click(screen.getByRole('button', { name: 'Change password' }));
  expect(await screen.findByRole('status')).toHaveTextContent('All sessions have ended');
  expect(screen.queryByLabelText(/Current password/)).not.toBeInTheDocument();
  expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0);
});

it('retries bootstrap and handles missing tokens', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new TypeError('offline')).mockResolvedValueOnce(bootstrap()));
  render(<MemoryRouter><RecoveryPage mode="confirm" /></MemoryRouter>);
  await userEvent.click(await screen.findByRole('button', { name: 'Try again' }));
  expect(await screen.findByText(/This link is missing/)).toBeVisible();
});
