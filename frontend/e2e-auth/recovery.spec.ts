import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const original = 'synthetic-browser-password-123';
function linksFor(email: string): string[] {
  const directory = process.env.AARCHIVE_TEST_MAIL_DIRECTORY;
  if (!directory) throw new Error('Isolated mailbox required');
  return readdirSync(directory).flatMap((name) => {
    const content = readFileSync(join(directory, name), 'utf8');
    return content.includes(`To: ${email}`) ? content.match(/http:\/\/127\.0\.0\.1:\d+\/reset-password#token=[A-Za-z0-9_-]{43}/g) ?? [] : [];
  });
}
async function signIn(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('Institutional email').fill(email);
  await page.getByLabel('Password', { exact: false }).fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'You’re signed in.' })).toBeVisible();
}

test('reset/change revokes all sessions and lifecycle restoration cannot revive them', async ({ page, browser, baseURL }, info) => {
  test.setTimeout(60000);
  if (!baseURL) throw new Error('Isolated test server required');
  const email = `recovery-${info.project.name}@iut.example`;
  const replacement = 'synthetic-replacement-password-456';
  const changed = 'synthetic-changed-password-789';
  const otherContext = await browser.newContext({ baseURL });
  const adminContext = await browser.newContext({ baseURL });
  try {
    const other = await otherContext.newPage();
    const admin = await adminContext.newPage();
    await signIn(page, email, original);
    const target = (await (await page.request.get('/api/auth/session')).json()).user.id as string;
    await signIn(other, email, original);
    await page.goto('/forgot-password');
    await page.getByLabel('Account email').fill(email);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await page.getByRole('button', { name: 'Send reset link' }).click();
    await expect(page.getByRole('status')).toContainText('If this account is eligible');
    await expect.poll(() => linksFor(email).length).toBe(1);
    const link = linksFor(email)[0]!;
    await page.goto(link);
    await page.getByLabel('New password').fill(replacement);
    expect(new URL(page.url()).hash).toBe('');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await page.screenshot({ path: `test-results/reset-${info.project.name}.png`, fullPage: true });
    await page.getByRole('button', { name: 'Reset password' }).click();
    await expect(page.getByRole('status')).toContainText('All sessions have ended');
    await other.reload();
    await expect(other.getByRole('button', { name: 'Sign in' })).toBeVisible();
    await page.goto(link);
    await page.getByLabel('New password').fill(changed);
    await page.getByRole('button', { name: 'Reset password' }).click();
    await expect(page.getByRole('alert')).toContainText('Unable to complete');
    await signIn(page, email, replacement);
    await page.getByRole('link', { name: 'Change password', exact: true }).click();
    await page.getByLabel('Current password').fill(replacement);
    await page.getByLabel('New password').fill(changed);
    await page.getByRole('button', { name: 'Change password' }).click();
    await expect(page.getByRole('status')).toContainText('All sessions have ended');
    await signIn(page, email, changed);
    await signIn(admin, `lifecycle-admin-${info.project.name}@iut.example`, original);
    const csrf = (await adminContext.cookies()).find((cookie) => cookie.name === 'csrftoken')!.value;
    async function transition(command: string, expected_state: string) {
      const result = await admin.request.post(`/api/users/${target}/lifecycle`, {
        data: { command, expected_state, reason: 'administrative_change' }, headers: { 'X-CSRFToken': csrf },
      });
      expect(result.status()).toBe(200);
    }
    await transition('graduate', 'ACTIVE');
    await page.reload();
    await expect(page.getByText('Graduated', { exact: true })).toBeVisible();
    await transition('suspend', 'GRADUATED');
    await transition('restore', 'SUSPENDED');
    // No request was needed while suspended: the old session must already be gone.
    await page.reload();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
    await signIn(page, email, changed);
    await expect(page.getByText('Graduated', { exact: true })).toBeVisible();
    await page.screenshot({ path: `test-results/recovered-${info.project.name}.png`, fullPage: true });
  } finally { await otherContext.close(); await adminContext.close(); }
});
