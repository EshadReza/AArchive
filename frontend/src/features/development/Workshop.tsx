import { useState } from 'react';
import type { FormEvent } from 'react';
import { Button } from '../../components/Button';
import { ErrorSummary } from '../../components/ErrorSummary';
import type { FieldError } from '../../components/ErrorSummary';
import { FormField } from '../../components/FormField';
import { PageHeading } from '../../components/PageHeading';
import { EmptyState, LoadingState } from '../../components/States';

export default function Workshop() {
  const [name, setName] = useState('');
  const [errors, setErrors] = useState<FieldError[]>([]);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuccess(false);
    const next = name.trim() ? [] : [{ id: 'example-name', message: 'Enter a name for this example.' }];
    setErrors(next);
    if (!next.length) setSuccess(true);
  }
  function reset() { setName(''); setErrors([]); setSuccess(false); }
  return <>
    <div className="workshop-topline"><span className="section-code">FOUNDATION / 003</span><span className="outline-badge">Development only</span></div>
    <PageHeading eyebrow="The interface workshop" title="Small parts. A shared language.">
      <p>A working collection of the patterns that will shape AArchive.</p>
    </PageHeading>
    <aside className="demo-notice"><span className="notice-dot" aria-hidden="true" />
      <p><strong>Synthetic examples.</strong> Everything on this page stays in memory. Nothing is sent or saved.</p>
    </aside>
    <div className="workshop-grid">
      <section className="panel form-panel" aria-labelledby="forms-title">
        <div className="panel-heading"><span className="component-number">01</span><div><h2 id="forms-title">Clear, considered forms</h2><p>Labels, guidance, and errors that lead somewhere.</p></div></div>
        <form noValidate onSubmit={submit}>
          <ErrorSummary errors={errors} />
          <FormField id="example-name" label="Example name" placeholder="e.g. Practice collection" required
            hint="A synthetic label for trying this form." value={name} error={errors[0]?.message ?? ''}
            onChange={(event) => { setName(event.target.value); setSuccess(false); }} />
          <div className="form-actions"><Button type="submit">Validate example <span aria-hidden="true">→</span></Button><Button variant="secondary" onClick={reset}>Reset</Button></div>
          {success && <p className="success-message" role="status">Example validated. Nothing was saved.</p>}
        </form>
        <p className="component-note">Try submitting an empty field, then follow the error link.</p>
      </section>
      <section className="panel" aria-labelledby="states-title">
        <div className="panel-heading"><span className="component-number">02</span><div><h2 id="states-title">Every state has a place</h2><p>Useful feedback, even before there is content.</p></div></div>
        <div className="state-preview">
          {loading ? <LoadingState label="Loading example content…" /> : <EmptyState title="A little room for what’s next.">This empty state is a demonstration, not a live collection.</EmptyState>}
        </div>
        <Button variant="secondary" aria-pressed={loading} onClick={() => setLoading(!loading)}>{loading ? 'Show empty state' : 'Show loading state'}</Button>
      </section>
    </div>
    <section className="principles" aria-label="Interface principles">
      <div><span className="component-number">A</span><h2>Find your way</h2><p>Visible focus, keyboard navigation, and a shortcut to the content.</p></div>
      <div><span className="component-number">B</span><h2>Keep it legible</h2><p>Room to read, clear hierarchy, and a layout that adapts.</p></div>
      <div><span className="component-number">C</span><h2>Make it explicit</h2><p>Helpful labels and honest feedback at every step.</p></div>
    </section>
  </>;
}
