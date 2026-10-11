import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router';
import { Button } from '../../components/Button';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { LoadingState } from '../../components/States';
import { ApiError, request } from '../../lib/api';
import { getSession } from './session';

type Mode = 'request' | 'confirm' | 'change' | 'invite';
const titles = { invite: 'Accept your invitation.', request: 'Reset your password.', confirm: 'Choose a new password.', change: 'Change your password.' };
const labels = { invite: 'Accept invitation', request: 'Send reset link', confirm: 'Reset password', change: 'Change password' };
const endpoints = { invite: 'invitation/accept', request: 'password-reset', confirm: 'password-reset/confirm', change: 'password-change' };

export default function RecoveryPage({ mode }: { mode: Mode }) {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [reload, setReload] = useState(0);
  const [token, setToken] = useState(() => (mode === 'confirm' || mode === 'invite') ? new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '' : '');
  const alert = useRef<HTMLDivElement>(null);
  const status = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function clearFragment() { window.history.replaceState(window.history.state, '', window.location.pathname); }
    function receiveLink() {
      setToken(new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '');
      setMessage(''); setError(''); setPassword(''); clearFragment();
    }
    if ((mode === 'confirm' || mode === 'invite')) {
      if (window.location.hash) clearFragment();
      window.addEventListener('hashchange', receiveLink);
    }
    const controller = new AbortController();
    getSession(controller.signal).then((user) => { setSignedIn(user !== null); setReady(true); }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : 'Could not connect. Try again.');
    });
    return () => { controller.abort(); window.removeEventListener('hashchange', receiveLink); };
  }, [mode, reload]);
  useEffect(() => { if (error) alert.current?.focus(); }, [error]);
  useEffect(() => { if (message) status.current?.focus(); }, [message]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready || busy) return;
    setBusy(true); setError(''); setMessage('');
    const json = mode === 'request' ? { email: email.trim() } : (mode === 'confirm' || mode === 'invite') ? { token, password }
      : { current_password: currentPassword, password };
    setPassword(''); setCurrentPassword('');
    try {
      const result = await request<unknown>(`/api/auth/${endpoints[mode]}`, { method: 'POST', json });
      if (!result || typeof result !== 'object' || !('message' in result) || typeof result.message !== 'string') throw new Error('Unexpected response');
      setMessage(result.message);
      if (mode !== 'request') { setToken(''); setSignedIn(false); }
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'Could not complete the request. Try again.');
      if (failure instanceof ApiError && failure.status === 403) {
        try { setSignedIn((await getSession()) !== null); } catch { setReady(false); }
      }
    } finally { setBusy(false); }
  }

  return <section className="intro-page auth-page">
    <PageHeading eyebrow="Account security" title={titles[mode]}>
      <p>{mode === 'request' ? 'Enter your account email. Eligible accounts receive a link to choose a new password.'
        : mode === 'invite' ? 'Confirm your email and choose your password. Administrator approval may still be required.' : 'Updating your password signs you out on every device. You will need to sign in again.'}</p>
    </PageHeading>
    <div className="panel auth-panel">
      {error && <div className="error-summary" role="alert" tabIndex={-1} ref={alert}>{error}</div>}
      {message && <div role="status" tabIndex={-1} ref={status}>{message}</div>}
      {!ready ? <>{!error && <LoadingState label="Checking your session…" />}
        {error && <Button onClick={() => { setError(''); setReload((value) => value + 1); }}>Try again</Button>}</>
        : !message && (mode === 'change' && !signedIn ? <p>Sign in to change your password, or request a reset link.</p>
          : (mode === 'confirm' || mode === 'invite') && !/^[A-Za-z0-9_-]{43}$/.test(token) ? <p>This link is missing or invalid. Request a new link from its sender.</p>
            : <form onSubmit={(event) => void submit(event)} aria-busy={busy}>
              {mode === 'request' && <FormField label="Account email" name="email" type="email" autoComplete="email" required maxLength={254}
                value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} />}
              {mode === 'change' && <FormField label="Current password" name="current_password" type="password" autoComplete="current-password" required maxLength={1024}
                value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} disabled={busy} />}
              {mode !== 'request' && <FormField label="New password" name="password" type="password" autoComplete="new-password" required minLength={12} maxLength={1024}
                hint="Use at least 12 characters and a different password. Avoid common passwords, only numbers, or your email."
                value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} />}
              <Button type="submit" disabled={busy}>{busy ? 'Please wait…' : labels[mode]}</Button>
            </form>)}
      <div className="form-actions">
        <Link className="text-link" to="/login">Back to sign in</Link>
        {mode !== 'request' && mode !== 'invite' && <Link className="text-link" to="/forgot-password">Request a new reset link</Link>}
      </div>
      {mode === 'invite' && <p className="component-note">Ask your administrator to resend an expired invitation.</p>}
      {mode === 'request' && <p className="component-note">Email verification and any required approval must be complete. A reset does not reactivate a restricted account.</p>}
    </div>
  </section>;
}
