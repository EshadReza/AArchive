import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import { OfferingList, OfferingDetail } from './Offerings';

const row = { id: 'offering-id', name: 'Computing', course_code: 'CS101', course_title: 'Programming', department_label: 'CSE', batch_label: '2026', term_label: '1', section_label: 'ALL', archived: false, revision: 3, can_manage: true, can_assign: false };
const assignment = { id: 'link-id', teacher_id: 'teacher-id', display_name: 'Current teacher', assigned_at: '2026-10-11T01:00:00Z', ended_at: null };
const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
const session = (role = 'TEACHER') => response({ user: { id: 'user-id', email: 'teacher@iut.example', display_name: 'Teacher', roles: [role], state: 'ACTIVE' } });
const page = (rows: unknown[]) => response({ count: rows.length, results: rows, next: null, previous: null });
function start(fetcher: ReturnType<typeof vi.fn>, detail = false) {
  vi.stubGlobal('fetch', fetcher); document.cookie = 'csrftoken=synthetic-csrf; path=/';
  render(<MemoryRouter initialEntries={[detail ? '/offerings/offering-id' : '/offerings']}><Routes><Route path="/offerings" element={<OfferingList />} /><Route path="/offerings/:id" element={<OfferingDetail />} /></Routes></MemoryRouter>);
}
afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'csrftoken=; Max-Age=0; path=/'; });

it('does not load offerings or academic choices for a Student', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session('STUDENT')); start(fetcher);
  expect(await screen.findByRole('alert')).toHaveTextContent('Teacher or administrator');
  expect(fetcher).toHaveBeenCalledTimes(1);
});
it('clears dependent choices when the department changes', async () => {
  const fetcher = vi.fn().mockImplementation((url: URL) => {
    if (url.pathname === '/api/auth/session') return session();
    if (url.pathname === '/api/course-offerings') return page([]);
    if (url.pathname.endsWith('/departments')) return page([{ id: 'd1', label: 'D1', name: 'First' }, { id: 'd2', label: 'D2', name: 'Second' }]);
    if (url.pathname === '/api/courses') return page([{ id: 'c1', code: 'CS101', title: 'Course' }]);
    return page([{ id: 'b1', label: '2026', name: 'Batch' }]);
  }); start(fetcher);
  await userEvent.selectOptions(await screen.findByRole('combobox', { name: 'Department' }), 'd1');
  await userEvent.selectOptions(await screen.findByRole('combobox', { name: 'Course' }), 'c1');
  await userEvent.selectOptions(await screen.findByRole('combobox', { name: 'Batch' }), 'b1');
  expect(await screen.findByRole('combobox', { name: 'Term' })).toBeVisible();
  await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Department' }), 'd2');
  expect(screen.queryByRole('combobox', { name: 'Term' })).toBeNull();
  expect(await screen.findByRole('combobox', { name: 'Course' })).toHaveValue('');
  expect(screen.getByRole('button', { name: 'Create offering' })).toBeDisabled();
});
it('co-teacher settings use the current revision and hide administrator controls', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(response(row)).mockResolvedValueOnce(page([assignment])).mockResolvedValueOnce(response({ code: 'offering_conflict', message: 'Reload and review again.' }, 409)); start(fetcher, true);
  await userEvent.click(await screen.findByRole('button', { name: 'Save offering' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Reload');
  expect(screen.queryByRole('button', { name: 'Save offering' })).toBeNull();
  expect(screen.queryByRole('heading', { name: 'Manage staff' })).toBeNull();
  const mutation = fetcher.mock.calls.find((call) => (call[1] as RequestInit)?.method === 'PATCH')!;
  expect(JSON.parse((mutation[1] as RequestInit).body as string)).toEqual({ name: 'Computing', expected_revision: 3 });
});
it('requires focused review before teacher removal and retains ended history', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session('ADMINISTRATOR')).mockResolvedValueOnce(response({ ...row, can_assign: true })).mockResolvedValueOnce(page([assignment, { ...assignment, id: 'old-link', display_name: 'Previous teacher', ended_at: '2026-10-11T02:00:00Z' }])).mockResolvedValueOnce(page([])); start(fetcher, true);
  await userEvent.click(await screen.findByRole('button', { name: 'Remove Current teacher' }));
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Review teacher removal' })).toHaveFocus());
  expect(screen.getByText(/Authorship and assignment history remain/)).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Remove Previous teacher' })).toBeNull();
  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(fetcher.mock.calls.every((call) => (call[1] as RequestInit)?.method === 'GET')).toBe(true);
});
it('clears settings when offering access has been removed', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(response({ code: 'not_found', message: 'Not found.' }, 404)).mockResolvedValueOnce(page([])); start(fetcher, true);
  expect(await screen.findByRole('alert')).toHaveTextContent('Not found');
  expect(screen.queryByRole('button', { name: 'Save offering' })).toBeNull();
  expect(screen.queryByRole('heading', { name: 'Teacher assignment history' })).toBeNull();
});
