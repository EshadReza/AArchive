import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Button } from '../../components/Button';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { LoadingState } from '../../components/States';
import { ApiError, getPage, request } from '../../lib/api';
import type { Page } from '../../lib/api';
import { getSession } from '../auth/session';

type Offering = { id: string; name: string; course_code: string; course_title: string; department_label: string; batch_label: string; term_label: string; section_label: string; archived: boolean; revision: number; can_manage: boolean; can_assign: boolean };
type Assignment = { id: string; teacher_id: string; display_name: string; assigned_at: string; ended_at: string | null };
type Option = { id: string; label?: string; name?: string; code?: string; title?: string };
const base = '/api/course-offerings';
const message = (failure: unknown) => failure instanceof ApiError ? failure.message : 'Could not complete this request. Reload and try again.';

function Pages({ page, change, disabled = false }: { page: Page<unknown>; change: (url: string) => void; disabled?: boolean }) {
  return <div className="form-actions"><Button type="button" disabled={disabled || !page.previous} onClick={() => page.previous && change(page.previous)}>Previous page</Button><Button type="button" disabled={disabled || !page.next} onClick={() => page.next && change(page.next)}>Next page</Button></div>;
}

function Picker({ path, label, selected, choose, disabled }: { path: string; label: string; selected: string; choose: (id: string, label?: string) => void; disabled: boolean }) {
  const [url, setUrl] = useState(path); const [page, setPage] = useState<Page<Option> | null>(null); const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void getPage<Option>(url, { signal: controller.signal }).then(setPage).catch((failure: unknown) => { if (!controller.signal.aborted) setError(message(failure)); });
    return () => controller.abort();
  }, [url, retry]);
  function change(next: string) { setPage(null); setError(''); setUrl(next); setRetry((n) => n + 1); choose(''); }
  return <fieldset className="offering-picker" disabled={disabled}><legend>{label}</legend>{error ? <><p role="alert">{error}</p><Button type="button" onClick={() => change(url)}>Retry {label.toLowerCase()}</Button></> : !page ? <LoadingState label={`Loading ${label.toLowerCase()}…`} /> : <>
    <label>{label}<select value={selected} onChange={(event) => { const option = page.results.find((item) => item.id === event.target.value); choose(event.target.value, option ? `${option.label ?? option.code} — ${option.name ?? option.title}` : ''); }} required><option value="">Choose {label.toLowerCase()}</option>{page.results.map((row) => <option key={row.id} value={row.id}>{row.label ?? row.code} — {row.name ?? row.title}</option>)}</select></label>
    {!page.results.length && <p>No available choices.</p>}<Pages page={page} change={change} disabled={disabled} />
  </>}</fieldset>;
}

export function OfferingList() {
  const [page, setPage] = useState<Page<Offering> | null>(null); const [url, setUrl] = useState(base); const [reload, setReload] = useState(0);
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [department, setDepartment] = useState(''); const [course, setCourse] = useState(''); const [batch, setBatch] = useState(''); const [term, setTerm] = useState(''); const [section, setSection] = useState(''); const [name, setName] = useState('');
  const navigate = useNavigate(); const notice = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      const user = await getSession(controller.signal);
      if (!user?.roles.some((role) => ['TEACHER', 'ADMINISTRATOR'].includes(role))) throw new ApiError('forbidden', 'Teacher or administrator access is required.');
      const result = await getPage<Offering>(url, { signal: controller.signal });
      if (!controller.signal.aborted) setPage(result);
    }
    void load().catch((failure: unknown) => { if (!controller.signal.aborted) setError(message(failure)); });
    return () => controller.abort();
  }, [url, reload]);
  useEffect(() => { if (error) notice.current?.focus(); }, [error]);
  function change(path = url) { setPage(null); setError(''); setUrl(path); setReload((n) => n + 1); }
  async function create() {
    if (busy) return; setBusy(true); setError('');
    try {
      const row = await request<Offering>(base, { method: 'POST', json: { name, course_id: course, batch_id: batch, term_id: term, section_id: section } });
      navigate(`/offerings/${row.id}`);
    } catch (failure) { setPage(null); setError(message(failure)); } finally { setBusy(false); }
  }
  return <section className="intro-page"><PageHeading eyebrow="Academics" title="Course offerings."><p>A course’s run for one batch, term and section. Teachers see their assignments; administrators see all offerings.</p></PageHeading>
    {error ? <><div className="error-summary" role="alert" tabIndex={-1} ref={notice}>{error}</div><Button onClick={() => change()}>Reload offerings</Button></> : !page ? <LoadingState label="Loading offerings…" /> : <>
      {!page.results.length && <p>No offerings yet.</p>}<ul className="account-list">{page.results.map((row) => <li className="panel" key={row.id}><h2><Link to={`/offerings/${row.id}`}>{row.name}</Link></h2><p>{row.department_label} · {row.course_code} · {row.batch_label} / {row.term_label} / {row.section_label}</p><p>{row.archived ? 'Archived' : 'Active'}</p></li>)}</ul><Pages page={page} change={change} disabled={busy} />
      <div className="panel auth-panel"><h2>Create offering</h2><p>You will be attached as its creator. An administrator manages additional teacher assignments. Course, batch, term and section are fixed after creation.</p>
        <form onSubmit={(event) => { event.preventDefault(); void create(); }}>
          <Picker path="/api/course-offering-options/departments" label="Department" selected={department} disabled={busy} choose={(id) => { setDepartment(id); setCourse(''); setBatch(''); setTerm(''); setSection(''); }} />
          {department && <><Picker key={`course-${department}`} path={`/api/courses?department_id=${department}&archived=false`} label="Course" selected={course} choose={setCourse} disabled={busy} /><Picker key={`batch-${department}`} path={`/api/course-offering-options/batches?department_id=${department}`} label="Batch" selected={batch} choose={(id) => { setBatch(id); setTerm(''); setSection(''); }} disabled={busy} /></>}
          {batch && <><Picker key={`term-${batch}`} path={`/api/course-offering-options/terms?batch_id=${batch}`} label="Term" selected={term} choose={setTerm} disabled={busy} /><Picker key={`section-${batch}`} path={`/api/course-offering-options/sections?batch_id=${batch}`} label="Section" selected={section} choose={setSection} disabled={busy} /></>}
          <FormField label="Offering name" name="name" required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} disabled={busy} />
          <Button type="submit" disabled={busy || !course || !batch || !term || !section}>Create offering</Button>
        </form>
      </div>
    </>}<p><Link to="/account">Back to account</Link></p>
  </section>;
}

export function OfferingDetail() {
  const { id } = useParams();
  // A route change gets fresh form, revision, and assignment state.
  return <Detail key={id} id={id!} />;
}
function Detail({ id }: { id: string }) {
  const path = `${base}/${id}`;
  const [row, setRow] = useState<Offering | null>(null); const [history, setHistory] = useState<Page<Assignment> | null>(null);
  const [historyUrl, setHistoryUrl] = useState(`${path}/teachers`); const [reload, setReload] = useState(0);
  const [name, setName] = useState(''); const [teacher, setTeacher] = useState(''); const [teacherLabel, setTeacherLabel] = useState('');
  const [review, setReview] = useState<{ teacher_id: string; active: boolean; label: string } | 'archive' | null>(null);
  const [error, setError] = useState(''); const [success, setSuccess] = useState(''); const [busy, setBusy] = useState(false);
  const notice = useRef<HTMLDivElement>(null); const reviewHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      await getSession(controller.signal);
      const [detail, assignments] = await Promise.all([request<Offering>(path, { signal: controller.signal }), getPage<Assignment>(historyUrl, { signal: controller.signal })]);
      if (!controller.signal.aborted) { setRow(detail); setName(detail.name); setHistory(assignments); }
    }
    void load().catch((failure: unknown) => { if (!controller.signal.aborted) { setRow(null); setHistory(null); setError(message(failure)); } });
    return () => controller.abort();
  }, [path, historyUrl, reload]);
  useEffect(() => { if (error || success) notice.current?.focus(); }, [error, success]);
  useEffect(() => { if (review) reviewHeading.current?.focus(); }, [review]);
  function load(url = `${path}/teachers`) { setRow(null); setHistory(null); setReview(null); setTeacher(''); setError(''); setHistoryUrl(url); setReload((n) => n + 1); }
  async function save() {
    if (busy || !row) return; setBusy(true); setError(''); setSuccess('');
    const suffix = review === 'archive' ? '/archive' : review ? '/teachers' : '';
    const json = { expected_revision: row.revision, ...(review === 'archive' ? {} : review ? { teacher_id: review.teacher_id, active: review.active } : { name }) };
    try {
      await request(path + suffix, { method: review ? 'POST' : 'PATCH', json });
      setSuccess(review === 'archive' ? 'Offering archived. History is retained.' : review ? 'Teacher assignments updated.' : 'Offering saved.'); load();
    } catch (failure) { setRow(null); setHistory(null); setReview(null); setError(message(failure)); } finally { setBusy(false); }
  }
  return <section className="intro-page"><PageHeading eyebrow="Academics" title={row?.name ?? 'Offering details.'}><p>Current co-teachers share offering settings rights. Assignment changes are managed by administrators.</p></PageHeading>
    {(error || success) && <div ref={notice} tabIndex={-1} role={error ? 'alert' : 'status'} className={error ? 'error-summary' : ''}>{error || success}</div>}
    {error ? <Button onClick={() => load()}>Reload offering</Button> : !row || !history ? <LoadingState label="Loading offering…" /> : <>
      <div className="panel"><h2>Course and cohort</h2><p>{row.department_label} · {row.course_code} — {row.course_title}</p><p>Batch {row.batch_label} · Term {row.term_label} · Section {row.section_label}</p><p>{row.archived ? 'Archived' : row.can_manage ? 'Active' : 'Read only: an academic parent may be archived.'}</p></div>
      {row.can_manage && <form className="panel auth-panel" onSubmit={(event) => { event.preventDefault(); setReview(null); void save(); }}><h2>Offering settings</h2><FormField label="Offering name" name="name" value={name} required maxLength={200} onChange={(event) => setName(event.target.value)} disabled={busy || !!review} /><Button type="submit" disabled={busy || !!review}>Save offering</Button></form>}
      <div className="panel"><h2>Teacher assignment history</h2><ul className="account-list">{history.results.map((link) => <li key={link.id}><p>{link.display_name} · {link.ended_at ? 'Ended' : 'Current'}</p><p>Assigned {new Date(link.assigned_at).toLocaleString()}{link.ended_at && ` · Ended ${new Date(link.ended_at).toLocaleString()}`}</p>{row.can_assign && !link.ended_at && <Button disabled={busy || !!review} variant="secondary" onClick={() => setReview({ teacher_id: link.teacher_id, active: false, label: link.display_name })}>Remove {link.display_name}</Button>}</li>)}</ul><Pages page={history} change={load} disabled={busy || !!review} /></div>
      {row.can_assign && <div className="panel auth-panel"><h2>Manage staff</h2>{row.can_manage && <><Picker path={`${base}/staff-options`} label="Staff member" selected={teacher} choose={(id, label) => { setTeacher(id); setTeacherLabel(label ?? ''); }} disabled={busy || !!review} /><Button disabled={busy || !!review || !teacher} onClick={() => setReview({ teacher_id: teacher, active: true, label: teacherLabel })}>Review assignment</Button></>}{!row.archived && <Button variant="secondary" disabled={busy || !!review} onClick={() => setReview('archive')}>Archive offering</Button>}</div>}
      {review && <div className="panel"><h2 tabIndex={-1} ref={reviewHeading}>{review === 'archive' ? 'Review offering archive' : review.active ? 'Review teacher assignment' : 'Review teacher removal'}</h2><p>{review === 'archive' ? 'Archiving stops settings edits and new assignments. Assignment history is retained.' : review.active ? `Assign staff member ${review.label} to ${row.name}. Current Teachers will gain offering settings rights.` : `Remove ${review.label} from ${row.name}. Their offering access ends immediately unless they are an administrator. Authorship and assignment history remain. Existing delegated permissions are revoked.`}</p><Button disabled={busy} onClick={() => void save()}>Confirm change</Button> <Button variant="secondary" disabled={busy} onClick={() => setReview(null)}>Cancel</Button></div>}
    </>}<p><Link to="/offerings">Back to offerings</Link></p>
  </section>;
}
