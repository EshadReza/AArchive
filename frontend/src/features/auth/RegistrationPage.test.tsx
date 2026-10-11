import { screen, render, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import RegistrationPage from './RegistrationPage';

const bootstrap = () => new Response(JSON.stringify({ user: null }));
const message = 'If this address is eligible, a verification email will arrive.';
afterEach(() => {
  vi.unstubAllGlobals(); document.cookie = 'csrftoken=; Max-Age=0; path=/';
  window.history.replaceState(null, '', '/');
});

it('submits only public fields and shows the generic result with focus', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(bootstrap()).mockResolvedValueOnce(new Response(JSON.stringify({ message }), { status: 202 }));
  vi.stubGlobal('fetch', fetcher); document.cookie = 'csrftoken=synthetic-csrf; path=/';
  render(<MemoryRouter><RegistrationPage mode="register" /></MemoryRouter>);
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText(/Institutional email/), 'new@iut.example');
  await user.type(screen.getByLabelText(/Display name/), 'New Student');
  await user.type(screen.getByLabelText(/^Password/), 'synthetic-registration-password');
  await user.click(screen.getByRole('button', { name: 'Create account' }));
  expect(await screen.findByRole('status')).toHaveTextContent(message);
  await waitFor(() => expect(screen.getByRole('status')).toHaveFocus());
  const options = fetcher.mock.calls[1]?.[1] as RequestInit;
  expect(JSON.parse(options.body as string)).toEqual({ email: 'new@iut.example', display_name: 'New Student', password: 'synthetic-registration-password' });
  expect(screen.queryByLabelText(/^Password/)).not.toBeInTheDocument();
});

it('clears the password on failure and focuses the error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(bootstrap()).mockResolvedValueOnce(
    new Response(JSON.stringify({ code: 'registration_limited', message: 'Too many attempts. Try again later.' }), { status: 429 })));
  document.cookie = 'csrftoken=synthetic-csrf; path=/';
  render(<MemoryRouter><RegistrationPage mode="register" /></MemoryRouter>);
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText(/Institutional email/), 'new@iut.example');
  await user.type(screen.getByLabelText(/Display name/), 'New Student');
  await user.type(screen.getByLabelText(/^Password/), 'synthetic-registration-password');
  await user.click(screen.getByRole('button', { name: 'Create account' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts');
  await waitFor(() => expect(screen.getByRole('alert')).toHaveFocus());
  expect(screen.getByLabelText(/^Password/)).toHaveValue('');
});

it('requires explicit verification and removes the fragment before submitting', async () => {
  const token = 'a'.repeat(43);
  window.history.replaceState(null, '', `/verify-email#token=${token}`);
  const fetcher = vi.fn().mockResolvedValueOnce(bootstrap()).mockResolvedValueOnce(new Response(JSON.stringify({ message: 'Email verified.' })));
  vi.stubGlobal('fetch', fetcher); document.cookie = 'csrftoken=synthetic-csrf; path=/';
  render(<MemoryRouter><RegistrationPage mode="verify" /></MemoryRouter>);
  const button = await screen.findByRole('button', { name: 'Verify email' });
  expect(window.location.hash).toBe(''); expect(fetcher).toHaveBeenCalledTimes(1);
  await userEvent.click(button);
  expect(await screen.findByRole('status')).toHaveTextContent('Email verified.');
  expect(JSON.parse((fetcher.mock.calls[1]?.[1] as RequestInit).body as string)).toEqual({ token });
  expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0);
});

it('offers resend for missing tokens and retries a failed bootstrap', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new TypeError('offline')).mockResolvedValueOnce(bootstrap()));
  render(<MemoryRouter><RegistrationPage mode="verify" /></MemoryRouter>);
  await userEvent.click(await screen.findByRole('button', { name: 'Try again' }));
  expect(await screen.findByText(/This link is missing/)).toBeVisible();
  expect(screen.getByRole('link', { name: 'Request a new verification link' })).toBeVisible();
});

it('resend submits email only and rejects malformed success responses', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(bootstrap()).mockResolvedValueOnce(new Response('{}', { status: 202 }));
  vi.stubGlobal('fetch', fetcher); document.cookie = 'csrftoken=synthetic-csrf; path=/';
  render(<MemoryRouter><RegistrationPage mode="resend" /></MemoryRouter>);
  await userEvent.type(await screen.findByLabelText(/Institutional email/), 'new@iut.example');
  await userEvent.click(screen.getByRole('button', { name: 'Send verification link' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not complete');
  expect(JSON.parse((fetcher.mock.calls[1]?.[1] as RequestInit).body as string)).toEqual({ email: 'new@iut.example' });
});
