import { useEffect, useId, useRef } from 'react';

export type FieldError = { id: string; message: string };

export function ErrorSummary({ errors }: { errors: FieldError[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const headingId = useId();
  useEffect(() => { if (errors.length) ref.current?.focus(); }, [errors]);
  if (!errors.length) return null;
  return <div className="error-summary" role="alert" tabIndex={-1} ref={ref} aria-labelledby={headingId}>
    <h3 id={headingId}>Check the following</h3>
    <ul>{errors.map(({ id, message }) => <li key={id}>
      <a href={`#${id}`} onClick={(event) => {
        event.preventDefault();
        document.getElementById(id)?.focus();
      }}>{message}</a>
    </li>)}</ul>
  </div>;
}
