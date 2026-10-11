import { screen, render, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AccountPage from './AccountPage';
import { parseSession } from './session';

const account = { id: 'synthetic-id', email: 'member@iut.example', display_name: 'Test Member', state: 'ACTIVE', roles: ['STUDENT'] };

function response(user: typeof account | null) {
  return new Response(JSON.stringify({ user }), { status: 200, headers: { 'Content-Type': 'application/json' } });
}

afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'csrftoken=; Max-Age=0; path=/'; });

describe('account flow', () => {
  it('bootstraps CSRF, logs in without browser storage, and confirms logout', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(null)).mockResolvedValueOnce(response(account))
      .mockResolvedValueOnce(new Response(null, { status: 204 })).mockResolvedValueOnce(response(null));
    vi.stubGlobal('fetch', fetcher);
    document.cookie = 'csrftoken=synthetic-csrf; path=/';
    render(<MemoryRouter><AccountPage /></MemoryRouter>);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/Institutional email/), account.email);
    await user.type(screen.getByLabelText(/Password/), 'synthetic-password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('heading', { name: 'You’re signed in.' })).toBeVisible();
    expect(screen.getByText(account.email)).toBeVisible();
    const options = fetcher.mock.calls[1]?.[1] as RequestInit;
    expect(options.credentials).toBe('same-origin');
    expect(new Headers(options.headers).get('X-CSRFToken')).toBe('synthetic-csrf');
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    await user.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeVisible();
    expect(screen.queryByText(account.email)).not.toBeInTheDocument();
  });

  it('clears passwords and focuses generic login failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response(null)).mockResolvedValueOnce(
      new Response(JSON.stringify({ code: 'invalid_credentials', message: 'Unable to sign in with those details.' }), { status: 401 })));
    document.cookie = 'csrftoken=synthetic-csrf; path=/';
    render(<MemoryRouter><AccountPage /></MemoryRouter>);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/Institutional email/), account.email);
    await user.type(screen.getByLabelText(/Password/), 'synthetic-wrong');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to sign in with those details.');
    await waitFor(() => expect(screen.getByRole('alert')).toHaveFocus());
    expect(screen.getByLabelText(/Password/)).toHaveValue('');
  });

  it('shows a retry for an unavailable backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new TypeError('offline')).mockResolvedValueOnce(response(null)));
    render(<MemoryRouter><AccountPage /></MemoryRouter>);
    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeVisible();
  });

  it('does not render an unexpected or closed-state account response', () => {
    expect(() => parseSession({ user: { ...account, state: 'SUSPENDED' } })).toThrow();
    expect(() => parseSession({ user: { ...account, roles: ['SOURCE_ADMIN'] } })).toThrow();
    expect(parseSession({ user: null })).toBeNull();
  });
});
