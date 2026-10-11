import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Button } from '../../components/Button';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { LoadingState } from '../../components/States';
import { ApiError, request } from '../../lib/api';
import { getSession } from '../auth/session';
import { failureMessage, listAccounts, parseAccount, readAccount, roles, states } from './api';
import type { UserAccount } from './api';

function Notice({ error, message }: { error: string; message?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { if (error || message) ref.current?.focus(); }, [error, message]);
  return error || message ? <div className={error ? 'error-summary' : ''} ref={ref} role={error ? 'alert' : 'status'} tabIndex={-1}>{error || message}</div> : null;
}
function RoleChoices({ value, onChange, disabled }: { value: string[]; onChange: (value: string[]) => void; disabled: boolean }) {
  return <fieldset disabled={disabled}><legend>Platform roles</legend>{roles.map((role) => <label className="role-choice" key={role}>
    <input type="checkbox" checked={value.includes(role)} onChange={(event) => onChange(event.target.checked ? [...value, role] : value.filter((item) => item !== role))} />{role.charAt(0) + role.slice(1).toLowerCase()}
  </label>)}</fieldset>;
}
async function requireAdmin(signal?: AbortSignal) {
  const user = await getSession(signal);
  if (!user?.roles.includes('ADMINISTRATOR')) throw new ApiError('forbidden', 'Administrator access is required.');
}

export function AdminAccountList() {
  const [url, setUrl] = useState('/api/users');
  const [page, setPage] = useState<Awaited<ReturnType<typeof listAccounts>> | null>(null);
  const [error, setError] = useState(''); const [role, setRole] = useState(''); const [state, setState] = useState(''); const [query, setQuery] = useState('');
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    requireAdmin(controller.signal).then(() => listAccounts(url, controller.signal)).then(setPage)
      .catch((failure: unknown) => { if (!controller.signal.aborted) setError(failureMessage(failure)); });
    return () => controller.abort();
  }, [url, reload]);
  function go(next: string) { setPage(null); setError(''); setUrl(next); setReload((value) => value + 1); }
  function filter(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const params = new URLSearchParams(); if (role) params.set('role', role); if (state) params.set('state', state); if (query.trim()) params.set('q', query.trim()); go(`/api/users?${params}`); }
  return <section className="intro-page"><PageHeading eyebrow="Administration" title="Accounts."><p>Find students and teachers, invite new members, and review account access.</p></PageHeading>
    <Notice error={error} />
    {error ? <><Button onClick={() => go(url)}>Try again</Button><p><Link to="/account">Back to account</Link></p></> : <>
      {page && <><Link className="text-link" to="/admin/users/new">Create an account</Link>
        <form className="account-filters panel" onSubmit={filter}>
          <FormField label="Search accounts" name="query" maxLength={100} value={query} onChange={(event) => setQuery(event.target.value)} />
          <label>Role<select value={role} onChange={(event) => setRole(event.target.value)}><option value="">All roles</option>{roles.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>State<select value={state} onChange={(event) => setState(event.target.value)}><option value="">All states</option>{states.map((item) => <option key={item}>{item}</option>)}</select></label>
          <Button type="submit">Apply filters</Button>
        </form>
        <p>{page.results.length} accounts on this page</p>
        {page.results.length ? <ul className="account-list">{page.results.map((user) => <li className="panel" key={user.id}>
          <Link className="text-link" to={`/admin/users/${user.id}`}>{user.display_name || user.email}</Link>
          <p>{user.email}</p><p>{user.roles.join(', ')} · {user.state}</p><p>Student ID: {user.student_id || 'Not assigned'}</p>
        </li>)}</ul> : <p>No accounts match these filters.</p>}
        <div className="form-actions"><Button disabled={!page.previous} onClick={() => { if (page.previous) go(page.previous); }}>Previous page</Button><Button disabled={!page.next} onClick={() => { if (page.next) go(page.next); }}>Next page</Button></div>
      </>}
      {!page && <LoadingState label="Loading accounts…" />}
    </>}
  </section>;
}

export function AdminAccountCreate() {
  const [ready, setReady] = useState(false); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState(''); const [name, setName] = useState(''); const [studentId, setStudentId] = useState('');
  const [selected, setSelected] = useState(['STUDENT']); const [approval, setApproval] = useState(true); const [review, setReview] = useState(false);
  const navigate = useNavigate(); const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { const controller = new AbortController(); requireAdmin(controller.signal).then(() => setReady(true)).catch((failure: unknown) => { if (!controller.signal.aborted) setError(failureMessage(failure)); }); return () => controller.abort(); }, []);
  useEffect(() => { if (review) heading.current?.focus(); }, [review]);
  async function create() {
    setBusy(true); setError('');
    try { const user = parseAccount(await request('/api/users', { method: 'POST', json: { email: email.trim(), display_name: name.trim(), student_id: studentId.trim() || null, roles: selected, approval_required: approval } })); navigate(`/admin/users/${user.id}`, { replace: true }); }
    catch (failure) { setError(failureMessage(failure)); setReview(false); }
    finally { setBusy(false); }
  }
  return <section className="intro-page"><PageHeading eyebrow="Administration" title="Invite an account."><p>The recipient verifies email ownership and sets their own password. No initial password is assigned.</p></PageHeading>
    <div className="panel auth-panel"><Notice error={error} />
      {!ready ? !error && <LoadingState label="Checking access…" /> : review ? <>
        <h2 tabIndex={-1} ref={heading}>Review account invitation</h2><p>{name} — {email}</p><p>Student ID: {studentId || 'Not assigned'}</p><p>Roles: {selected.join(', ')}</p><p>{approval ? 'Separate administrator approval is required before activation.' : 'Email acceptance will activate this account without a separate approval.'}</p>
        <Button disabled={busy} onClick={() => void create()}>Confirm and invite</Button> <Button variant="secondary" disabled={busy} onClick={() => setReview(false)}>Back to edit</Button>
      </> : <form onSubmit={(event) => { event.preventDefault(); if (!selected.length) { setError('Select at least one role.'); return; } setError(''); setReview(true); }}>
        <FormField label="Email" name="email" type="email" required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} />
        <FormField label="Display name" name="display_name" required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} />
        <FormField label="Student ID" name="student_id" maxLength={64} value={studentId} onChange={(event) => setStudentId(event.target.value)} />
        <RoleChoices value={selected} onChange={setSelected} disabled={busy} />
        <label className="role-choice"><input type="checkbox" checked={approval} onChange={(event) => setApproval(event.target.checked)} />Require separate administrator approval</label>
        <Button type="submit">Review account</Button>
      </form>}
      <p><Link to="/admin/users">Back to accounts</Link></p>
    </div>
  </section>;
}

export function AdminAccountDetail() {
  const { id } = useParams(); const [user, setUser] = useState<UserAccount | null>(null); const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false); const [reload, setReload] = useState(0);
  const [command, setCommand] = useState(''); const [reason, setReason] = useState('administrative_change'); const [review, setReview] = useState<'roles' | 'lifecycle' | ''>(''); const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const controller = new AbortController(); requireAdmin(controller.signal).then(() => readAccount(`/api/users/${id}`, controller.signal)).then((value) => { setUser(value); setSelected(value.roles); })
      .catch((failure: unknown) => { if (!controller.signal.aborted) setError(failureMessage(failure)); }); return () => controller.abort();
  }, [id, reload]);
  useEffect(() => { if (review) heading.current?.focus(); }, [review]);
  async function mutate(kind: 'roles' | 'lifecycle' | 'invitation') {
    if (!user) return; setBusy(true); setError(''); setMessage('');
    const json = kind === 'roles' ? { roles: selected, expected_roles: user.roles, reason } : kind === 'lifecycle' ? { command, expected_state: user.state, reason } : {};
    try {
      await request(`/api/users/${user.id}/${kind}`, { method: 'POST', json });
      setReview(''); setMessage(kind === 'invitation' ? 'Invitation requested. Check delivery before resending.' : 'Account updated.');
      const updated = await readAccount(`/api/users/${user.id}`); setUser(updated); setSelected(updated.roles);
    } catch (failure) { setReview(''); setUser(null); setError(failureMessage(failure)); }
    finally { setBusy(false); }
  }
  const commands = user ? [
    ...(user.state === 'PENDING' && user.approval_required && !user.approved ? ['approve'] : []),
    ...(user.state === 'ACTIVE' ? ['inactivate', 'graduate', 'alumni'] : []),
    ...(user.state === 'INACTIVE' ? ['activate', 'graduate', 'alumni'] : []),
    ...(user.state === 'GRADUATED' ? ['alumni'] : []),
    ...(!['ANONYMIZED', 'SUSPENDED'].includes(user.state) ? ['suspend'] : []),
    ...(!['ANONYMIZED', 'ARCHIVED'].includes(user.state) ? ['archive'] : []),
    ...(['SUSPENDED', 'ARCHIVED'].includes(user.state) ? ['restore'] : []),
  ] : [];
  return <section className="intro-page"><PageHeading eyebrow="Administration" title="Account details."><p>Review the account before changing access. Every successful change is audited.</p></PageHeading>
    <div className="panel auth-panel"><Notice error={error} message={message} />
      {user ? <>
        <h2>{user.display_name || user.email}</h2><dl className="account-details"><dt>Email</dt><dd>{user.email}</dd><dt>Student ID</dt><dd>{user.student_id || 'Not assigned'}</dd><dt>State</dt><dd>{user.state}</dd><dt>Email verified</dt><dd>{user.email_verified ? 'Yes' : 'No'}</dd><dt>Approval</dt><dd>{user.approval_required ? user.approved ? 'Approved' : 'Required' : 'Not required'}</dd></dl>
        {review ? <section aria-label="Review account change">
          <h2 tabIndex={-1} ref={heading}>Review {review === 'roles' ? 'role change' : command}</h2><p>Account: {user.email}</p>
          {review === 'roles' ? <><p>From: {user.roles.join(', ')}</p><p>To: {selected.join(', ')}</p><p>Removing Teacher revokes delegated grants. Changing Administrator access may end your ability to manage accounts.</p></>
            : <><p>Current state: {user.state}. Command: {command}.</p><p>{['suspend', 'archive'].includes(command) ? 'All active sessions will end and pending invitation/recovery links will expire.' : command === 'restore' ? 'Only the recorded prior state can be restored. Old sessions and links stay invalid.' : 'Verification and required approval remain enforced.'}</p></>}
          <p>Reason: {reason}</p><Button disabled={busy} onClick={() => void mutate(review)}>Confirm change</Button> <Button disabled={busy} variant="secondary" onClick={() => setReview('')}>Cancel</Button>
        </section> : <>
          <RoleChoices value={selected} onChange={setSelected} disabled={busy || user.state === 'ANONYMIZED'} />
          <label>Reason<select value={reason} onChange={(event) => setReason(event.target.value)} disabled={busy}><option value="administrative_change">Administrative change</option><option value="user_request">User request</option><option value="security_response">Security response</option></select></label>
          <div className="form-actions"><Button disabled={busy || !selected.length || user.state === 'ANONYMIZED'} onClick={() => setReview('roles')}>Review roles</Button></div>
          <label>Lifecycle command<select value={command} onChange={(event) => setCommand(event.target.value)} disabled={busy}><option value="">Select a command</option>{commands.map((item) => <option key={item}>{item}</option>)}</select></label>
          <div className="form-actions"><Button disabled={busy || !commands.includes(command)} onClick={() => setReview('lifecycle')}>Review lifecycle change</Button></div>
          {user.invitation_pending && <Button disabled={busy} variant="secondary" onClick={() => void mutate('invitation')}>Resend invitation</Button>}
        </>}
      </> : error ? <Button onClick={() => { setError(''); setMessage(''); setReload((value) => value + 1); }}>Reload account</Button> : <LoadingState label="Loading account…" />}
      <p><Link to="/admin/users">Back to accounts</Link></p>
    </div>
  </section>;
}
