import type { ReactNode } from 'react';

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return <div className="loading-state" role="status" aria-live="polite">
    <span className="spinner" aria-hidden="true" /><span>{label}</span>
  </div>;
}

export function EmptyState({ title, children, action }: {
  title: string; children: ReactNode; action?: ReactNode;
}) {
  return <div className="empty-state">
    <span className="empty-symbol" aria-hidden="true">—</span>
    <h3>{title}</h3><p>{children}</p>{action}
  </div>;
}
