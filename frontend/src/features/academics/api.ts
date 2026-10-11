import { getPage } from '../../lib/api';

export const kinds = ['departments', 'batches', 'terms', 'sections'] as const;
export type Kind = typeof kinds[number];
export type Structure = { id: string; label: string; name: string; archived: boolean; available: boolean; revision: number; parent_label?: string; department_id?: string; batch_id?: string };
export const parentKind = (kind: Kind): Kind | null => kind === 'departments' ? null : kind === 'batches' ? 'departments' : 'batches';
export const parentKey = (kind: Kind) => kind === 'batches' ? 'department_id' : 'batch_id';
export function parseStructure(value: unknown, kind: Kind): Structure {
  if (!value || typeof value !== 'object') throw new Error('Invalid structure response');
  const row = value as Structure;
  if (typeof row.id !== 'string' || typeof row.label !== 'string' || typeof row.name !== 'string' || typeof row.archived !== 'boolean' || typeof row.available !== 'boolean' || !Number.isSafeInteger(row.revision) || row.revision < 1 || (parentKind(kind) && (typeof row[parentKey(kind)] !== 'string' || typeof row.parent_label !== 'string'))) throw new Error('Invalid structure response');
  return row;
}
export async function listStructure(path: string, kind: Kind, signal?: AbortSignal) {
  const page = await getPage<unknown>(path, signal ? { signal } : {});
  return { ...page, results: page.results.map((row) => parseStructure(row, kind)) };
}
