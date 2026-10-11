import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import StructurePage from './StructurePage';
import { parseStructure } from './api';

const row = { id: 'department-id', label: 'CSE', name: 'Computing', archived: false, available: true, revision: 1 };
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
const session = (admin = true) => response({ user: { id: 'user-id', email: 'member@iut.example', display_name: 'Member', roles: admin ? ['ADMINISTRATOR'] : ['STUDENT'], state: 'ACTIVE' } });
const page = (rows: unknown[] = [row]) => response({ results: rows, count: rows.length, next: null, previous: null });
afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'csrftoken=; Max-Age=0; path=/'; });
function renderPage() { document.cookie = 'csrftoken=synthetic-csrf; path=/'; render(<MemoryRouter><StructurePage /></MemoryRouter>); }

it('denies ordinary users before requesting academic structure', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session(false)); vi.stubGlobal('fetch', fetcher); renderPage();
  expect(await screen.findByRole('alert')).toHaveTextContent('Administrator access');
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it('shows empty state and creates a department without client-controlled state', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(page([])).mockResolvedValueOnce(response(row, 201)).mockResolvedValueOnce(session()).mockResolvedValueOnce(page());
  vi.stubGlobal('fetch', fetcher); renderPage();
  expect(await screen.findByText('No records match these filters.')).toBeVisible();
  await userEvent.type(screen.getByLabelText('Label', { exact: false }), 'CSE');
  await userEvent.type(screen.getByLabelText('Name', { exact: false }), 'Computing');
  await userEvent.click(screen.getByRole('button', { name: 'Save record' }));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(5));
  expect(JSON.parse((fetcher.mock.calls[2]?.[1] as RequestInit).body as string)).toEqual({ label: 'CSE', name: 'Computing' });
});

it('archive review focuses consequences and cancel performs no write', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(page()); vi.stubGlobal('fetch', fetcher); renderPage();
  await userEvent.click(await screen.findByRole('button', { name: 'Archive CSE' }));
  const heading = screen.getByRole('heading', { name: 'Review archive' });
  await waitFor(() => expect(heading).toHaveFocus());
  expect(screen.getByText(/Existing records and references remain readable/)).toBeVisible();
  expect(fetcher).toHaveBeenCalledTimes(2);
  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(screen.queryByRole('button', { name: 'Confirm archive' })).not.toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it('stale edits show safe conflict and require reloading', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(page()).mockResolvedValueOnce(response({ code: 'structure_conflict', message: 'This record changed. Reload and review again.' }, 409));
  vi.stubGlobal('fetch', fetcher); renderPage();
  await userEvent.click(await screen.findByRole('button', { name: 'Edit CSE' }));
  await userEvent.click(screen.getByRole('button', { name: 'Save record' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Reload and review');
  expect(screen.getByRole('button', { name: 'Reload structure' })).toBeVisible();
  expect(JSON.parse((fetcher.mock.calls[2]?.[1] as RequestInit).body as string)).toEqual({ label: 'CSE', name: 'Computing', expected_revision: 1 });
});

it('unavailable rows cannot be edited and invalid response shapes fail closed', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(session()).mockResolvedValueOnce(page([{ ...row, archived: true, available: false }])); vi.stubGlobal('fetch', fetcher); renderPage();
  expect(await screen.findByRole('button', { name: 'Edit CSE' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Archive CSE' })).toBeDisabled();
  expect(() => parseStructure({ ...row, revision: '1' }, 'departments')).toThrow();
  expect(() => parseStructure(row, 'terms')).toThrow();
});
