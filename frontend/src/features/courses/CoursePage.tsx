import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router';
import { Button } from '../../components/Button';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { LoadingState } from '../../components/States';
import { ApiError, request } from '../../lib/api';
import { getSession } from '../auth/session';
import { ParentPicker } from '../academics/StructurePage';
import type { Structure } from '../academics/api';
import { listCourses } from './api';
import type { Course } from './api';

export default function CoursePage() {
  const [page, setPage] = useState<Awaited<ReturnType<typeof listCourses>> | null>(null);
  const [url, setUrl] = useState('/api/courses'); const [reload, setReload] = useState(0);
  const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const [department, setDepartment] = useState<Structure | null>(null); const [limitDepartment, setLimitDepartment] = useState(false);
  const [query, setQuery] = useState(''); const [archiveFilter, setArchiveFilter] = useState('');
  const [editing, setEditing] = useState<Course | null>(null); const [archiving, setArchiving] = useState<Course | null>(null);
  const [code, setCode] = useState(''); const [title, setTitle] = useState(''); const [credits, setCredits] = useState(''); const [description, setDescription] = useState('');
  const notice = useRef<HTMLDivElement>(null); const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      const user = await getSession(controller.signal);
      if (!user?.roles.includes('ADMINISTRATOR')) throw new ApiError('forbidden', 'Administrator access is required.');
      const result = await listCourses(url, controller.signal);
      if (!controller.signal.aborted) setPage(result);
    }
    void load().catch((failure: unknown) => { if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : 'Could not load courses. Try again.'); });
    return () => controller.abort();
  }, [url, reload]);
  useEffect(() => { if (error || message) notice.current?.focus(); }, [error, message]);
  useEffect(() => { if (editing || archiving) heading.current?.focus(); }, [editing, archiving]);
  function load(path = url) { setPage(null); setError(''); setUrl(path); setReload((n) => n + 1); }
  function clear() { setEditing(null); setArchiving(null); setCode(''); setTitle(''); setCredits(''); setDescription(''); }
  async function mutate(archive = false) {
    if (busy) return; setBusy(true); setError(''); setMessage('');
    const target = archive ? archiving : editing;
    const json = archive ? { expected_revision: target!.revision } : { code, title, credits, description, ...(target ? { expected_revision: target.revision } : { department_id: department?.id }) };
    try {
      await request(`/api/courses${target ? `/${target.id}` : ''}${archive ? '/archive' : ''}`, { method: archive || !target ? 'POST' : 'PATCH', json });
      clear(); setMessage(archive ? 'Course archived. Historical course data is retained.' : 'Course saved.'); load();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'Could not save. Reload and try again.');
      setPage(null); clear();
    } finally { setBusy(false); }
  }
  function filter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const params = new URLSearchParams();
    if (limitDepartment && department) params.set('department_id', department.id);
    if (query.trim()) params.set('q', query.trim()); if (archiveFilter) params.set('archived', archiveFilter);
    load(`/api/courses?${params}`);
  }
  return <section className="intro-page"><PageHeading eyebrow="Administration" title="Course catalog."><p>Maintain reusable department courses. Each course can be used across batches and terms when offerings are added.</p></PageHeading>
    {(error || message) && <div ref={notice} role={error ? 'alert' : 'status'} tabIndex={-1} className={error ? 'error-summary' : ''}>{error || message}</div>}
    {error ? <Button onClick={() => load()}>Reload courses</Button> : !page ? <LoadingState label="Loading courses…" /> : <>
      <ParentPicker kind="departments" selected={department} onSelect={setDepartment} disabled={busy} />
      <form className="account-filters panel" onSubmit={filter}>
        <FormField label="Search courses" name="query" maxLength={100} value={query} onChange={(event) => setQuery(event.target.value)} />
        <label className="role-choice"><input type="checkbox" checked={limitDepartment} disabled={!department} onChange={(event) => setLimitDepartment(event.target.checked)} />Limit to selected department</label>
        <label>Archive filter<select value={archiveFilter} onChange={(event) => setArchiveFilter(event.target.value)}><option value="">All records</option><option value="false">Not archived directly</option><option value="true">Archived directly</option></select></label>
        <Button type="submit" disabled={busy}>Apply filters</Button>
      </form>
      {!page.results.length && <p>No courses match these filters.</p>}
      <ul className="account-list">{page.results.map((row) => <li className="panel" key={row.id}>
        <p className="eyebrow">{row.department_label} — {row.department_name}</p><h2>{row.code} — {row.title}</h2>
        <p>{row.credits} credits · {row.archived ? 'Archived' : row.available ? 'Available' : 'Department archived'}</p>
        <p className="course-description">{row.description || 'No description provided.'}</p>
        <div className="form-actions"><Button disabled={busy || !row.available} variant="secondary" onClick={() => { setEditing(row); setArchiving(null); setCode(row.code); setTitle(row.title); setCredits(row.credits); setDescription(row.description); }}>Edit {row.code}</Button><Button disabled={busy || row.archived} variant="secondary" onClick={() => { clear(); setArchiving(row); }}>Archive {row.code}</Button></div>
      </li>)}</ul>
      <div className="form-actions"><Button disabled={busy || !page.previous} onClick={() => { if (page.previous) load(page.previous); }}>Previous page</Button><Button disabled={busy || !page.next} onClick={() => { if (page.next) load(page.next); }}>Next page</Button></div>
      <div className="panel auth-panel">{archiving ? <>
        <h2 ref={heading} tabIndex={-1}>Review course archive</h2><p>{archiving.department_label}: {archiving.code} — {archiving.title}</p>
        <p>Archiving blocks new offerings and catalog edits. Historical course data stays readable to administrators. This screen does not restore archived courses.</p>
        <Button disabled={busy} onClick={() => void mutate(true)}>Confirm archive</Button> <Button disabled={busy} variant="secondary" onClick={clear}>Cancel</Button>
      </> : <>
        <h2 ref={heading} tabIndex={-1}>{editing ? `Edit ${editing.code}` : 'Create course'}</h2>
        <p>Department: {editing ? `${editing.department_label} — ${editing.department_name} (fixed after creation)` : department ? `${department.label} — ${department.name}` : 'Choose a department above.'}</p>
        <form onSubmit={(event) => { event.preventDefault(); void mutate(); }}>
          <FormField label="Course code" name="code" required maxLength={64} value={code} onChange={(event) => setCode(event.target.value)} disabled={busy} hint="Stored in uppercase; unique within its department." />
          <FormField label="Course title" name="title" required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} disabled={busy} />
          <FormField label="Credits" name="credits" required inputMode="decimal" pattern="[0-9]{1,2}(\.[0-9]{1,2})?" value={credits} onChange={(event) => setCredits(event.target.value)} disabled={busy} hint="0 to 99.99, with up to two decimal places." />
          <div className="form-field"><label htmlFor="course-description">Description</label><textarea id="course-description" maxLength={4000} rows={5} value={description} onChange={(event) => setDescription(event.target.value)} disabled={busy} /></div>
          <Button type="submit" disabled={busy || (!editing && !department?.available)}>Save course</Button>
          {editing && <Button variant="secondary" disabled={busy} onClick={clear}>Cancel edit</Button>}
        </form>
      </>}</div>
    </>}
    <p><Link to="/account">Back to account</Link></p>
  </section>;
}
