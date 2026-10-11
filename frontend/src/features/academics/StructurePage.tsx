import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router';
import { Button } from '../../components/Button';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { LoadingState } from '../../components/States';
import { ApiError, request } from '../../lib/api';
import { getSession } from '../auth/session';
import { kinds, listStructure, parentKey, parentKind } from './api';
import type { Kind, Structure } from './api';

export default function StructurePage() {
  const [kind, setKind] = useState<Kind>('departments');
  return <section className="intro-page"><PageHeading eyebrow="Administration" title="Academic structure."><p>Manage departments, admission batches, terms and sections. Archived records preserve academic history.</p></PageHeading>
    <label>Record type<select value={kind} onChange={(event) => setKind(event.target.value as Kind)}>{kinds.map((item) => <option key={item} value={item}>{item.charAt(0).toUpperCase() + item.slice(1)}</option>)}</select></label>
    <StructurePanel key={kind} kind={kind} />
    <p><Link to="/account">Back to account</Link></p>
  </section>;
}

function StructurePanel({ kind }: { kind: Kind }) {
  const [page, setPage] = useState<Awaited<ReturnType<typeof listStructure>> | null>(null);
  const [url, setUrl] = useState(`/api/${kind}`); const [reload, setReload] = useState(0);
  const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const [parent, setParent] = useState<Structure | null>(null);
  const [filter, setFilter] = useState(false); const [archiveFilter, setArchiveFilter] = useState('');
  const [editing, setEditing] = useState<Structure | null>(null); const [archiving, setArchiving] = useState<Structure | null>(null);
  const [label, setLabel] = useState(''); const [name, setName] = useState('');
  const notice = useRef<HTMLDivElement>(null); const review = useRef<HTMLHeadingElement>(null); const editor = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      const actor = await getSession(controller.signal);
      if (!actor?.roles.includes('ADMINISTRATOR')) throw new ApiError('forbidden', 'Administrator access is required.');
      const result = await listStructure(url, kind, controller.signal);
      if (!controller.signal.aborted) setPage(result);
    }
    void load().catch((failure: unknown) => { if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure.message : 'Could not load structure. Try again.'); });
    return () => controller.abort();
  }, [kind, url, reload]);
  useEffect(() => { if (error || message) notice.current?.focus(); }, [error, message]);
  useEffect(() => { if (archiving) review.current?.focus(); }, [archiving]);
  useEffect(() => { if (editing) editor.current?.focus(); }, [editing]);
  function load(path = url) { setPage(null); setError(''); setUrl(path); setReload((n) => n + 1); }
  function clearEdit() { setEditing(null); setLabel(''); setName(''); }
  async function mutate(archive = false) {
    if (busy) return;
    setBusy(true); setError(''); setMessage('');
    const target = archive ? archiving : editing;
    const path = `/api/${kind}${target ? `/${target.id}` : ''}${archive ? '/archive' : ''}`;
    const json = archive ? { expected_revision: target!.revision } : target ? { label, name, expected_revision: target.revision } : { label, name, ...(parentKind(kind) ? { [parentKey(kind)]: parent?.id } : {}) };
    try {
      await request(path, { method: archive || !target ? 'POST' : 'PATCH', json });
      setMessage(archive ? 'Record archived. Historical references are retained.' : 'Record saved.');
      clearEdit(); setArchiving(null); load();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'Could not save. Reload and try again.');
      setPage(null); clearEdit(); setArchiving(null);
    } finally { setBusy(false); }
  }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); void mutate(); }
  return <>
    {(error || message) && <div ref={notice} tabIndex={-1} role={error ? 'alert' : 'status'} className={error ? 'error-summary' : ''}>{error || message}</div>}
    {error ? <Button onClick={() => load()}>Reload structure</Button> : !page ? <LoadingState label="Loading structure…" /> : <>
      {parentKind(kind) && <ParentPicker key={parentKind(kind)} kind={parentKind(kind)!} selected={parent} onSelect={setParent} disabled={busy} />}
      <form className="account-filters panel" onSubmit={(event) => { event.preventDefault(); const params = new URLSearchParams(); if (filter && parent && parentKind(kind)) params.set(parentKey(kind), parent.id); if (archiveFilter) params.set('archived', archiveFilter); load(`/api/${kind}?${params}`); }}>
        {parentKind(kind) && <label className="role-choice"><input type="checkbox" checked={filter} disabled={!parent} onChange={(event) => setFilter(event.target.checked)} />Limit to selected parent</label>}
        <label>Archive filter<select value={archiveFilter} onChange={(event) => setArchiveFilter(event.target.value)}><option value="">All records</option><option value="false">Not archived directly</option><option value="true">Archived directly</option></select></label>
        <Button type="submit" disabled={busy}>Apply filters</Button>
      </form>
      <p>{page.results.length} records on this page. Unavailable records or their parents are archived.</p>
      <div className="structure-table-wrap"><table className="structure-table"><caption>{kind.charAt(0).toUpperCase() + kind.slice(1)}</caption><thead><tr><th scope="col">Label and name</th><th scope="col">Status</th><th scope="col">Actions</th></tr></thead><tbody>
        {page.results.map((row) => <tr key={row.id}><th scope="row">{row.label}<span className="structure-name">{row.name}</span>{parentKind(kind) && <small>Parent: {row.parent_label}</small>}</th><td>{row.archived ? 'Archived' : row.available ? 'Available' : 'Parent archived'}</td><td><div className="form-actions">
          <Button disabled={busy || !row.available} variant="secondary" onClick={() => { setEditing(row); setLabel(row.label); setName(row.name); setArchiving(null); }}>Edit {row.label}</Button>
          <Button disabled={busy || row.archived || (kind === 'sections' && row.label === 'ALL')} variant="secondary" onClick={() => { clearEdit(); setArchiving(row); }}>Archive {row.label}</Button>
        </div></td></tr>)}
      </tbody></table></div>
      {!page.results.length && <p>No records match these filters.</p>}
      <div className="form-actions"><Button disabled={busy || !page.previous} onClick={() => { if (page.previous) load(page.previous); }}>Previous page</Button><Button disabled={busy || !page.next} onClick={() => { if (page.next) load(page.next); }}>Next page</Button></div>
      {archiving ? <div className="panel auth-panel"><h2 ref={review} tabIndex={-1}>Review archive</h2><p>Archive {archiving.label} — {archiving.name}?</p><p>New assignments and edits through this record and its descendants will be blocked. Existing records and references remain readable. This screen does not restore archived records.</p><Button disabled={busy} onClick={() => void mutate(true)}>Confirm archive</Button> <Button disabled={busy} variant="secondary" onClick={() => setArchiving(null)}>Cancel</Button></div> : <div className="panel auth-panel">
        <h2 ref={editor} tabIndex={-1}>{editing ? `Edit ${editing.label}` : 'Create record'}</h2>
        {editing && parentKind(kind) && <p>Parent: {editing.parent_label} (fixed after creation)</p>}
        {!editing && parentKind(kind) && <p>Parent: {parent ? `${parent.label} — ${parent.name}` : "Choose a parent above."}</p>}
        <form onSubmit={submit}>
          <FormField label="Label" name="label" required maxLength={64} value={label} disabled={busy || (kind === 'sections' && editing?.label === 'ALL')} onChange={(event) => setLabel(event.target.value)} hint="Labels are stored in uppercase and must be unique within their parent." />
          <FormField label="Name" name="name" required maxLength={200} value={name} disabled={busy} onChange={(event) => setName(event.target.value)} />
          {kind === 'batches' && !editing && <p>A reserved ALL section is created for the whole batch.</p>}
          <Button type="submit" disabled={busy || (!editing && !!parentKind(kind) && !parent?.available)}>Save record</Button>
          {editing && <Button variant="secondary" disabled={busy} onClick={clearEdit}>Cancel edit</Button>}
        </form>
      </div>}
    </>}
  </>;
}

export function ParentPicker({ kind, selected, onSelect, disabled }: { kind: Kind; selected: Structure | null; onSelect: (row: Structure) => void; disabled: boolean }) {
  const [page, setPage] = useState<Awaited<ReturnType<typeof listStructure>> | null>(null); const [url, setUrl] = useState(`/api/${kind}?archived=false`); const [error, setError] = useState(''); const [retry, setRetry] = useState(0);
  useEffect(() => { const controller = new AbortController(); void listStructure(url, kind, controller.signal).then((value) => { if (!controller.signal.aborted) setPage(value); }).catch(() => { if (!controller.signal.aborted) setError('Could not load parents.'); }); return () => controller.abort(); }, [url, kind, retry]);
  function go(path: string) { setPage(null); setError(''); setUrl(path); setRetry((n) => n + 1); }
  return <fieldset disabled={disabled}><legend>Choose parent from {kind}</legend><p>{selected ? `Selected: ${selected.label} — ${selected.name}` : 'Select a parent before creating a record.'}</p>
    {error ? <><p role="alert">{error}</p><Button onClick={() => go(url)}>Retry parents</Button></> : !page ? <LoadingState label="Loading parents…" /> : <>
      {!page.results.length && <p>No parents available. Create one first.</p>}
      {page.results.map((row) => <label className="role-choice" key={row.id}><input type="radio" name="parent" value={row.id} checked={selected?.id === row.id} disabled={!row.available} onChange={() => onSelect(row)} />{row.label} — {row.name}{row.department_id && <small> (department {row.parent_label})</small>}{!row.available && ' (parent archived)'}</label>)}
      <div className="form-actions"><Button disabled={!page.previous} onClick={() => { if (page.previous) go(page.previous); }}>Previous parents</Button><Button disabled={!page.next} onClick={() => { if (page.next) go(page.next); }}>Next parents</Button></div>
    </>}
  </fieldset>;
}
