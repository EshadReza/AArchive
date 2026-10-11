import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

function invitation(email: string): string | undefined {
  const directory = process.env.AARCHIVE_TEST_MAIL_DIRECTORY!;
  for (const file of readdirSync(directory)) {
    const content = readFileSync(join(directory, file), 'utf8');
    if (content.includes(`To: ${email}`)) return content.match(/http:\/\/127\.0\.0\.1:\d+\/accept-invitation#token=[A-Za-z0-9_-]{43}/)?.[0];
  }
}

test('admin invites, approves and reviews access; invited member edits only own profile', async ({ page, browser, baseURL }, info) => {
  test.setTimeout(60000);
  if (!baseURL) throw new Error('Isolated server required');
  const email = `invited-${info.project.name}@iut.example`;
  await page.goto('/login');
  await page.getByLabel('Institutional email').fill(`lifecycle-admin-${info.project.name}@iut.example`);
  await page.getByLabel('Password', { exact: false }).fill('synthetic-browser-password-123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('link', { name: 'Manage accounts' }).click();
  await expect(page.getByRole('link', { name: 'Create an account' })).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({ path: `test-results/admin-accounts-${info.project.name}.png`, fullPage: true });
  await page.getByRole('link', { name: 'Create an account' }).click();
  await page.getByLabel('Email', { exact: false }).fill(email);
  await page.getByLabel('Display name').fill('Invited Teacher');
  await page.getByLabel('Student ID', { exact: false }).fill(`S011-${info.project.name}`);
  await page.getByRole('checkbox', { name: 'Student', exact: true }).uncheck();
  await page.getByRole('checkbox', { name: 'Teacher', exact: true }).check();
  await page.getByRole('button', { name: 'Review account' }).click();
  await expect(page.getByRole('heading', { name: 'Review account invitation' })).toBeFocused();
  await page.getByRole('button', { name: 'Confirm and invite' }).click();
  await expect(page.getByRole('heading', { name: 'Invited Teacher' })).toBeVisible();
  await expect.poll(() => invitation(email)).toBeTruthy();
  const inviteContext = await browser.newContext({ baseURL });
  try {
    const member = await inviteContext.newPage();
    const link = invitation(email)!;
    await member.goto(link);
    await member.getByLabel('New password').fill('synthetic-invited-password-123');
    expect(new URL(member.url()).hash).toBe('');
    await member.getByRole('button', { name: 'Accept invitation' }).click();
    await expect(member.getByRole('status')).toContainText('Invitation accepted');
    await page.getByLabel('Lifecycle command').selectOption('approve');
    await page.getByRole('button', { name: 'Review lifecycle change' }).click();
    await page.getByRole('button', { name: 'Confirm change' }).click();
    await expect(page.getByText('ACTIVE', { exact: true })).toBeVisible();
    await member.goto('/login');
    await member.getByLabel('Institutional email').fill(email);
    await member.getByLabel('Password', { exact: false }).fill('synthetic-invited-password-123');
    await member.getByRole('button', { name: 'Sign in' }).click();
    await member.getByRole('link', { name: 'Edit profile' }).click();
    await member.getByLabel('Display name').fill('Updated Teacher');
    await member.getByRole('button', { name: 'Save profile' }).click();
    await expect(member.getByRole('status')).toHaveText('Profile saved.');
    expect((await member.request.get('/api/users')).status()).toBe(403);
    await member.goto('/admin/users');
    await expect(member.getByRole('alert')).toHaveText('Administrator access is required.');
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Updated Teacher' })).toBeVisible();
    await page.getByRole('checkbox', { name: 'Student', exact: true }).check();
    await page.getByRole('checkbox', { name: 'Teacher', exact: true }).uncheck();
    await page.getByRole('button', { name: 'Review roles' }).click();
    await expect(page.getByText('From: TEACHER')).toBeVisible();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.screenshot({ path: `test-results/admin-review-${info.project.name}.png`, fullPage: true });
    await page.getByRole('button', { name: 'Cancel' }).click();
    await page.getByRole('button', { name: 'Review roles' }).click();
    await page.getByRole('button', { name: 'Confirm change' }).click();
    await expect(page.getByRole('checkbox', { name: 'Student', exact: true })).toBeChecked();
    await expect(page.getByRole('checkbox', { name: 'Teacher', exact: true })).not.toBeChecked();
    await page.getByLabel('Lifecycle command').selectOption('suspend');
    await page.getByRole('button', { name: 'Review lifecycle change' }).click();
    await expect(page.getByText(/All active sessions will end/)).toBeVisible();
    await page.getByRole('button', { name: 'Confirm change' }).click();
    await expect(page.getByText('SUSPENDED', { exact: true })).toBeVisible();
    await member.goto('/account');
    await expect(member.getByRole('button', { name: 'Sign in' })).toBeVisible();
  } finally { await inviteContext.close(); }
});
