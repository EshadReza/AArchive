import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router';
import { App } from '../app/App';
import Workshop from '../features/development/Workshop';
import { FormField } from './FormField';
import { EmptyState, LoadingState } from './States';

describe('form primitives', () => {
  it('associates a generated label, hint and error with the input', () => {
    render(<FormField label="Example" hint="Helpful hint" error="Enter a value" required />);
    const input = screen.getByRole('textbox', { name: 'Example' });
    expect(input).toBeRequired();
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAccessibleDescription('Helpful hint Enter a value');
  });

  it('focuses the error summary, then the invalid field, and can recover', async () => {
    const user = userEvent.setup();
    render(<Workshop />);
    await user.click(screen.getByRole('button', { name: 'Validate example' }));
    expect(screen.getByRole('alert')).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('link', { name: 'Enter a name for this example.' })).toHaveFocus();
    await user.keyboard('{Enter}');
    const input = screen.getByRole('textbox', { name: 'Example name' });
    expect(input).toHaveFocus();
    await user.type(input, 'Synthetic collection');
    await user.click(screen.getByRole('button', { name: 'Validate example' }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Nothing was saved');
    expect(input).not.toHaveAttribute('aria-invalid');
    await user.click(screen.getByRole('button', { name: 'Reset' }));
    expect(input).toHaveValue('');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});

describe('state primitives', () => {
  it('announces a loading label', () => {
    render(<LoadingState label="Loading example…" />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading example…');
  });
  it('renders an empty state and caller-supplied action', () => {
    render(<EmptyState title="No examples" action={<button>Try again</button>}>Nothing here yet.</EmptyState>);
    expect(screen.getByRole('heading', { name: 'No examples' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
  it('switches the workshop preview with an accessible toggle', async () => {
    const user = userEvent.setup();
    render(<Workshop />);
    await user.click(screen.getByRole('button', { name: 'Show loading state' }));
    expect(screen.getByRole('status')).toHaveTextContent('Loading example content');
    expect(screen.getByRole('button', { name: 'Show empty state' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(screen.getByRole('button', { name: 'Show empty state' }));
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});

describe('routing and shell', () => {
  it('has a skip link, semantic landmarks and a real navigation destination', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#main-content');
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: 'Interface workshop' }));
    expect(await screen.findByRole('heading', { name: 'Small parts. A shared language.' })).toBeInTheDocument();
    expect(screen.getByRole('main')).toHaveFocus();
  });
  it('renders a useful missing-page route', () => {
    render(<MemoryRouter initialEntries={['/missing']}><App /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: 'This page isn’t here.' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Return to overview' })).toHaveAttribute('href', '/');
  });
});
