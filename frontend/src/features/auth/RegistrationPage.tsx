import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router';
import { Button } from '../../components/Button';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { LoadingState } from '../../components/States';
import { ApiError, request } from '../../lib/api';
import { getSession } from './session';

type Mode = 'register' | 'verify' | 'resend';
const titles = { register: 'Create your account.', verify: 'Verify your email.', resend: 'Request a new link.' };
const labels = { register: 'Create account', verify: 'Verify email', resend: 'Send verification link' };

export default function RegistrationPage({ mode }: { mode: Mode }) {
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [reload, setReload] = useState(0);
  const [token, setToken] = useState(() => mode === 'verify' ? new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '' : '');
  const alert = useRef<HTMLDivElement>(null);
  const status = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // A second email link can navigate within this same document without remounting.
    function clearFragment() {
      window.history.replaceState(window.history.state, '', window.location.pathname);
    }
    function receiveLink() {
      setToken(new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '');
      setMessage(''); setError('');
      clearFragment();
    }
    if (mode === 'verify') {
      if (window.location.hash) clearFragment();
      window.addEventListener('hashchange', receiveLink);
    }
    const controller = new AbortController();
    getSession(controller.signal).then(() => setReady(true)).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : 'Could not connect. Try again.');
    });
    return () => { controller.abort(); window.removeEventListener('hashchange', receiveLink); };
  }, [mode, reload]);
  useEffect(() => { if (error) alert.current?.focus(); }, [error]);
  useEffect(() => { if (message) status.current?.focus(); }, [message]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !ready) return;
    setBusy(true); setError(''); setMessage('');
    const body = mode === 'register' ? { email: email.trim(), display_name: displayName.trim(), password }
      : mode === 'resend' ? { email: email.trim() } : { token };
    setPassword('');
    const endpoint = mode === 'resend' ? 'resend-verification' : mode;
    try {
      const result = await request<unknown>(`/api/auth/${endpoint}`, { method: 'POST', json: body });
      if (!result || typeof result !== 'object' || !('message' in result) || typeof result.message !== 'string') throw new Error('Unexpected response');
      setMessage(result.message);
      if (mode === 'verify') setToken('');
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'Could not complete the request. Try again.');
      if (failure instanceof ApiError && failure.status === 403) {
        try { await getSession(); } catch { setReady(false); }
      }
    } finally { setBusy(false); }
  }

  return <section className="intro-page auth-page">
    <PageHeading eyebrow="Your archive account" title={titles[mode]}>
      <p>{mode === 'register' ? 'Use your institutional email to join AArchive as a Student.'
        : mode === 'verify' ? 'Confirm only if you requested this account. Administrator approval may also be required.'
          : 'Enter your institutional email. A new link replaces any previous verification link.'}</p>
    </PageHeading>
    <div className="panel auth-panel">
      {error && <div className="error-summary" role="alert" tabIndex={-1} ref={alert}>{error}</div>}
      {message && <div role="status" tabIndex={-1} ref={status}>{message}</div>}
      {!ready ? <>{!error && <LoadingState label="Connecting securely…" />}
        {error && <Button onClick={() => { setError(''); setReload((value) => value + 1); }}>Try again</Button>}</>
        : !message && (mode === 'verify' && !/^[A-Za-z0-9_-]{43}$/.test(token)
          ? <p>This link is missing or invalid. Request a new verification link.</p>
          : <form onSubmit={(event) => void submit(event)} aria-busy={busy}>
            {mode !== 'verify' && <FormField label="Institutional email" name="email" type="email" autoComplete="email" required maxLength={254}
              value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} />}
            {mode === 'register' && <>
              <FormField label="Display name" name="display_name" autoComplete="name" required maxLength={200}
                value={displayName} onChange={(event) => setDisplayName(event.target.value)} disabled={busy} />
              <FormField label="Password" name="password" type="password" autoComplete="new-password" required minLength={12} maxLength={1024}
                hint="Use at least 12 characters. Avoid common passwords, only numbers, or your email."
                value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} />
              <p className="component-note">Verify your email before signing in. Your institution may also require administrator approval.</p>
            </>}
            <Button type="submit" disabled={busy}>{busy ? 'Please wait…' : labels[mode]}</Button>
          </form>)}
      <div className="form-actions">
        <Link className="text-link" to="/login">Back to sign in</Link>
        {mode !== 'resend' && <Link className="text-link" to="/resend-verification">Request a new verification link</Link>}
        {mode === 'resend' && <Link className="text-link" to="/register">Create an account</Link>}
      </div>
    </div>
  </section>;
}
