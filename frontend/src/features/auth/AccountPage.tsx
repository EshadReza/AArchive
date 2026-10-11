import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { Button } from '../../components/Button';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { LoadingState } from '../../components/States';
import { ApiError } from '../../lib/api';
import { getSession, login, logout } from './session';
import type { Account } from './session';

export default function AccountPage() {
  const [user, setUser] = useState<Account | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const alert = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  useEffect(() => {
    const controller = new AbortController();
    getSession(controller.signal).then((account) => {
      setUser(account); setReady(true);
    }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : 'Could not load your account.');
    });
    return () => controller.abort();
  }, [reload]);
  useEffect(() => { if (error) alert.current?.focus(); }, [error]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    const suppliedPassword = password;
    setPassword('');
    try {
      setUser(await login(email.trim(), suppliedPassword));
      navigate('/account', { replace: true });
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'Unable to sign in. Please try again.');
      // Refresh rotated/stale CSRF cookies before another submission.
      if (failure instanceof ApiError && failure.status === 403) {
        try { setUser(await getSession()); } catch { setReady(false); }
      }
    } finally { setBusy(false); }
  }

  async function signOut() {
    setBusy(true); setError('');
    try {
      await logout(); setUser(null); setEmail(''); setReady(false);
      setReload((value) => value + 1);
      navigate('/login', { replace: true });
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'Sign-out could not be confirmed. Try again.');
      try { setUser(await getSession()); } catch { setReady(false); }
    } finally { setBusy(false); }
  }

  return <section className="intro-page auth-page">
    <PageHeading eyebrow="Your archive account" title={user ? 'You’re signed in.' : 'Welcome back.'}>
      <p>{user ? 'Your account is connected. Keep your work in context.' : 'Sign in with your institutional email and password.'}</p>
    </PageHeading>
    <div className="panel auth-panel">
      {error && <div className="error-summary" role="alert" tabIndex={-1} ref={alert}>{error}</div>}
      {!ready ? <>
        {!error && <LoadingState label="Checking your session…" />}
        {error && <Button onClick={() => { setError(''); setReload((value) => value + 1); }}>Try again</Button>}
      </> : user ? <>
        <h2>{user.display_name || 'Your account'}</h2>
        <dl className="account-details">
          <dt>Email</dt><dd>{user.email}</dd>
          <dt>Roles</dt><dd>{user.roles.map((role) => role.charAt(0) + role.slice(1).toLowerCase()).join(', ') || 'No roles assigned'}</dd>
          <dt>Account status</dt><dd>{user.state.charAt(0) + user.state.slice(1).toLowerCase()}</dd>
        </dl>
        <p><Link className="text-link" to="/profile">Edit profile</Link></p>
        {user.roles.includes("ADMINISTRATOR") && <p><Link className="text-link" to="/admin/users">Manage accounts</Link></p>}
        {user.roles.includes("ADMINISTRATOR") && <p><Link className="text-link" to="/admin/structure">Manage academic structure</Link></p>}
        {user.roles.includes("ADMINISTRATOR") && <p><Link className="text-link" to="/admin/courses">Manage course catalog</Link></p>}
        {user.roles.some((role) => ["TEACHER", "ADMINISTRATOR"].includes(role)) && <p><Link className="text-link" to="/offerings">Course offerings</Link></p>}
        <p><Link className="text-link" to="/change-password">Change password</Link></p>
        <p className="field-hint">Contest and academic pages are still being built.</p>
        <div className="form-actions">
          <Button disabled={busy} onClick={() => void signOut()}>{busy ? 'Signing out…' : 'Sign out'}</Button>
          <Button variant="secondary" disabled={busy} onClick={() => { setUser(null); setReady(false); setError(''); setReload((value) => value + 1); }}>Refresh session</Button>
        </div>
      </> : <form onSubmit={(event) => void submit(event)} aria-busy={busy}>
        <h2>Sign in</h2>
        <FormField label="Institutional email" name="email" type="email" autoComplete="username" required maxLength={254}
          value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} />
        <FormField label="Password" name="password" type="password" autoComplete="current-password" required maxLength={1024}
          value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} />
        <Button type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</Button>
        <p><Link className="text-link" to="/register">Create a Student account</Link></p>
        <p><Link className="text-link" to="/resend-verification">Request a verification link</Link></p>
        <p><Link className="text-link" to="/forgot-password">Forgot your password?</Link></p>
        <p className="component-note">Complete email verification and any required approval before signing in. Contact your administrator about restricted accounts.</p>
      </form>}
    </div>
  </section>;
}
