import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import CoursePage from './CoursePage';
import { parseCourse } from './api';

const course = { id: 'course-id', department_id: 'dept-id', department_label: 'CSE', department_name: 'Computing', code: 'CSE101', title: 'Introduction', credits: '3.50', description: '<script>not executable</script>', archived: false, available: true, revision: 1 };
const department = { id: 'dept-id', label: 'CSE', name: 'Computing', available: true, archived: false, revision: 1 };
const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
const session = (role = 'ADMINISTRATOR') => response({ user: { id: 'user-id', email: 'admin@iut.example', display_name: 'Admin', roles: [role], state: 'ACTIVE' } });
const page = (rows: unknown[]) => response({ count: rows.length, results: rows, next: null, previous: null });
function start(fetcher: ReturnType<typeof vi.fn>) { vi.stubGlobal('fetch', fetcher); document.cookie = 'csrftoken=synthetic-csrf; path=/'; render(<MemoryRouter><CoursePage /></MemoryRouter>); }
afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'csrftoken=; Max-Age=0; path=/'; });

it('denies the management screen to ordinary users before fetching catalog or parents', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session('STUDENT')); start(fetcher);
  expect(await screen.findByRole('alert')).toHaveTextContent('Administrator access');
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it('creates within the selected department and sends credits as a decimal string', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(page([])).mockResolvedValueOnce(page([department])).mockResolvedValueOnce(response(course, 201)).mockResolvedValueOnce(session()).mockResolvedValueOnce(page([course])).mockResolvedValueOnce(page([department])); start(fetcher);
  expect(await screen.findByText('No courses match these filters.')).toBeVisible();
  await userEvent.click(await screen.findByRole('radio', { name: 'CSE — Computing' }));
  await userEvent.type(screen.getByLabelText('Course code', { exact: false }), 'CSE101');
  await userEvent.type(screen.getByLabelText('Course title', { exact: false }), 'Introduction');
  await userEvent.type(screen.getByLabelText('Credits', { exact: false }), '3.50');
  await userEvent.click(screen.getByRole('button', { name: 'Save course' }));
  await waitFor(() => expect(fetcher.mock.calls.some((call) => (call[1] as RequestInit)?.method === 'POST')).toBe(true));
  const mutation = fetcher.mock.calls.find((call) => (call[1] as RequestInit)?.method === 'POST')!;
  expect(JSON.parse((mutation[1] as RequestInit).body as string)).toEqual({ department_id: 'dept-id', code: 'CSE101', title: 'Introduction', credits: '3.50', description: '' });
});

it('renders descriptions as text and requires archive review before writing', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(page([course])).mockResolvedValueOnce(page([department])); start(fetcher);
  expect(await screen.findByText(course.description)).toBeVisible();
  expect(document.querySelector('script')).toBeNull();
  await userEvent.click(screen.getByRole('button', { name: 'Archive CSE101' }));
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Review course archive' })).toHaveFocus());
  expect(screen.getByText(/Historical course data stays readable/)).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(fetcher.mock.calls.every((call) => !(call[1] as RequestInit)?.method || (call[1] as RequestInit).method === 'GET')).toBe(true);
});

it('stale edits require reload and preserve fixed department in request allowlist', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(page([course])).mockResolvedValueOnce(page([department])).mockResolvedValueOnce(response({ code: 'course_conflict', message: 'Reload and review again.' }, 409)); start(fetcher);
  await userEvent.click(await screen.findByRole('button', { name: 'Edit CSE101' }));
  expect(screen.getByText(/fixed after creation/)).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Save course' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Reload');
  expect(screen.getByRole('button', { name: 'Reload courses' })).toBeVisible();
  const call = fetcher.mock.calls.find((call) => (call[1] as RequestInit)?.method === 'PATCH')!;
  const data = JSON.parse((call[1] as RequestInit).body as string) as Record<string, unknown>;
  expect(data.expected_revision).toBe(1); expect(data).not.toHaveProperty('department_id');
});

it('validates API credits, availability and revisions', () => {
  expect(parseCourse(course).credits).toBe('3.50');
  expect(() => parseCourse({ ...course, credits: 3.5 })).toThrow();
  expect(() => parseCourse({ ...course, credits: 'NaN' })).toThrow();
  expect(() => parseCourse({ ...course, revision: 0 })).toThrow();
  expect(() => parseCourse({ ...course, available: 'false' })).toThrow();
});
