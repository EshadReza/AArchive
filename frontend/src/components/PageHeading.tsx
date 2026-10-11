import type { ReactNode } from 'react';

export function PageHeading({ eyebrow, title, children }: {
  eyebrow: string; title: string; children?: ReactNode;
}) {
  return <header className="page-heading">
    <p className="eyebrow">{eyebrow}</p>
    <h1>{title}</h1>
    {children && <div className="page-description">{children}</div>}
  </header>;
}
