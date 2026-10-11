import { useId } from 'react';
import type { InputHTMLAttributes } from 'react';

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
};

export function FormField({ label, hint, error, id, required, ...props }: Props) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const descriptionIds = [props['aria-describedby'], hint && `${fieldId}-hint`, error && `${fieldId}-error`]
    .filter(Boolean).join(' ') || undefined;
  return <div className="form-field">
    <label htmlFor={fieldId}>{label}{required && <span className="label-note" aria-hidden="true"> (required)</span>}</label>
    {hint && <p className="field-hint" id={`${fieldId}-hint`}>{hint}</p>}
    <input {...props} id={fieldId} required={required} aria-describedby={descriptionIds}
      aria-invalid={error ? true : props['aria-invalid']} />
    {error && <p className="field-error" id={`${fieldId}-error`}>{error}</p>}
  </div>;
}
