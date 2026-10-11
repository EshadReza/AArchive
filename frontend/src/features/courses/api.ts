import { getPage } from '../../lib/api';
export type Course = { id: string; department_id: string; department_label: string; department_name: string; code: string; title: string; credits: string; description: string; archived: boolean; available: boolean; revision: number };
export function parseCourse(value: unknown): Course {
  if (!value || typeof value !== 'object') throw new Error('Invalid course response');
  const row = value as Course;
  if (['id', 'department_id', 'department_label', 'department_name', 'code', 'title', 'credits', 'description'].some((key) => typeof (row as unknown as Record<string, unknown>)[key] !== 'string') || !/^[0-9]{1,2}\.[0-9]{2}$/.test(row.credits) || typeof row.archived !== 'boolean' || typeof row.available !== 'boolean' || !Number.isSafeInteger(row.revision) || row.revision < 1) throw new Error('Invalid course response');
  return row;
}
export async function listCourses(path: string, signal?: AbortSignal) {
  const page = await getPage<unknown>(path, signal ? { signal } : {});
  return { ...page, results: page.results.map(parseCourse) };
}
