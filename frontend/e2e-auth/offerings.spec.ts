import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function signIn(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel('Institutional email').fill(email);
  await page.getByLabel('Password', { exact: false }).fill('synthetic-browser-password-123');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Course offerings', exact: true })).toBeVisible();
}
async function write(page: Page, path: string, data: unknown, method = 'POST') {
  const token = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')!.value;
  return page.request.fetch(path, { method, data, headers: { 'X-CSRFToken': token } });
}

test('offering creator and co-teacher rights survive assignment history changes', async ({ page, browser }, info) => {
  const project = info.project.name;
  await signIn(page, `lifecycle-admin-${project}@iut.example`);
  async function create(path: string, data: unknown) {
    const result = await write(page, path, data); expect(result.status()).toBe(201); return result.json();
  }
  const department = await create('/api/departments', { label: `OFFER-${project}`, name: 'Offering department' });
  const batch = await create('/api/batches', { department_id: department.id, label: '2026', name: 'Test cohort' });
  const term = await create('/api/terms', { batch_id: batch.id, label: '1', name: 'First term' });
  const course = await create('/api/courses', { department_id: department.id, code: 'CS101', title: 'Computing', credits: '3.00', description: '' });
  const contexts = [await browser.newContext({ baseURL: process.env.AUTH_E2E_BASE_URL!, viewport: info.project.use.viewport ?? null }), await browser.newContext({ baseURL: process.env.AUTH_E2E_BASE_URL!, viewport: info.project.use.viewport ?? null })];
  try {
    const teacher = await contexts[0]!.newPage(); const colleague = await contexts[1]!.newPage();
    await signIn(teacher, `offering-teacher-${project}@iut.example`);
    await teacher.getByRole('link', { name: 'Course offerings', exact: true }).click();
    await teacher.getByRole('combobox', { name: 'Department', exact: true }).selectOption(department.id);
    await teacher.getByRole('combobox', { name: 'Course', exact: true }).selectOption(course.id);
    await teacher.getByRole('combobox', { name: 'Batch', exact: true }).selectOption(batch.id);
    await teacher.getByRole('combobox', { name: 'Term', exact: true }).selectOption(term.id);
    await teacher.getByRole('combobox', { name: 'Section', exact: true }).selectOption({ label: 'ALL — Whole batch' });
    await teacher.getByLabel('Offering name', { exact: false }).fill(`Programming ${project}`);
    expect((await new AxeBuilder({ page: teacher }).analyze()).violations).toEqual([]);
    await teacher.getByRole('button', { name: 'Create offering', exact: true }).click();
    await expect(teacher.getByRole('button', { name: 'Save offering' })).toBeVisible();
    const detailPath = new URL(teacher.url()).pathname;
    await page.goto(detailPath);
    await page.getByRole('combobox', { name: 'Staff member', exact: true }).selectOption({ label: `offering-colleague-${project}@iut.example — offering-colleague` });
    await page.getByRole('button', { name: 'Review assignment' }).click();
    await expect(page.getByRole('heading', { name: 'Review teacher assignment' })).toBeFocused();
    await page.getByRole('button', { name: 'Confirm change' }).click();
    await expect(page.getByRole('button', { name: 'Remove offering-colleague', exact: true })).toBeVisible();
    await signIn(colleague, `offering-colleague-${project}@iut.example`);
    await colleague.goto(detailPath);
    await colleague.getByLabel('Offering name', { exact: false }).fill(`Co-taught ${project}`);
    await colleague.getByRole('button', { name: 'Save offering' }).click();
    await expect(colleague.getByRole('heading', { name: `Co-taught ${project}`, exact: true })).toBeVisible();
    await page.reload();
    await page.getByRole('button', { name: 'Remove offering-teacher', exact: true }).click();
    await page.getByRole('button', { name: 'Confirm change' }).click();
    await expect(page.getByText('offering-teacher · Ended', { exact: true })).toBeVisible();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.screenshot({ path: `test-results/offerings-${project}.png`, fullPage: true });
    await teacher.reload();
    await expect(teacher.getByRole('alert')).toBeVisible();
    await expect(teacher.getByRole('button', { name: 'Save offering' })).toHaveCount(0);
    const denied = await write(teacher, '/api/course-offerings/' + detailPath.split('/').at(-1), { name: 'Forbidden', expected_revision: 4 }, 'PATCH');
    expect(denied.status()).toBe(403);
    await colleague.reload();
    await expect(colleague.getByRole('button', { name: 'Save offering' })).toBeEnabled();
    await page.getByRole('button', { name: 'Archive offering', exact: true }).click();
    await page.getByRole('button', { name: 'Confirm change' }).click();
    await expect(page.getByText('Archived', { exact: true })).toBeVisible();
    await colleague.reload();
    await expect(colleague.getByText('Archived', { exact: true })).toBeVisible();
    await expect(colleague.getByRole('button', { name: 'Save offering' })).toHaveCount(0);
  } finally { for (const context of contexts) await context.close(); }
});
