import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router';
import { Button } from '../../components/Button';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { LoadingState } from '../../components/States';
import { request } from '../../lib/api';
import { getSession } from '../auth/session';
import { failureMessage, parseAccount, readAccount } from './api';
import type { UserAccount } from './api';

export default function ProfilePage() {
  const [user, setUser] = useState<UserAccount | null>(null);
  const [name, setName] = useState(''); const [error, setError] = useState('');
  const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0); const status = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    getSession(controller.signal).then(() => readAccount('/api/profile', controller.signal)).then((value) => { setUser(value); setName(value.display_name); })
      .catch((failure: unknown) => { if (!controller.signal.aborted) setError(failureMessage(failure)); });
    return () => controller.abort();
  }, [reload]);
  useEffect(() => { if (error || message) status.current?.focus(); }, [error, message]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('');
    try { const value = parseAccount(await request('/api/profile', { method: 'PATCH', json: { display_name: name.trim() } })); setUser(value); setName(value.display_name); setMessage('Profile saved.'); }
    catch (failure) { setUser(null); setError(failureMessage(failure)); }
    finally { setBusy(false); }
  }
  return <section className="intro-page"><PageHeading eyebrow="Your account" title="Your profile."><p>Update the name shown on your profile. Identity and account permissions are managed by your institution.</p></PageHeading>
    <div className="panel auth-panel">
      {(error || message) && <div ref={status} tabIndex={-1} role={error ? 'alert' : 'status'}>{error || message}</div>}
      {user ? <form onSubmit={(event) => void submit(event)} aria-busy={busy}>
        <dl className="account-details"><dt>Email</dt><dd>{user.email}</dd><dt>Student ID</dt><dd>{user.student_id || 'Not assigned'}</dd><dt>Roles</dt><dd>{user.roles.join(', ')}</dd></dl>
        <FormField label="Display name" name="display_name" required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} disabled={busy} />
        <Button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</Button>
      </form> : error ? <Button onClick={() => { setError(''); setReload((value) => value + 1); }}>Try again</Button> : <LoadingState label="Loading profile…" />}
      <p><Link className="text-link" to="/account">Back to account</Link></p>
    </div>
  </section>;
}
