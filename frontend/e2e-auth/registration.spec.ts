import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

function linksFor(email: string): string[] {
  const directory = process.env.AARCHIVE_TEST_MAIL_DIRECTORY;
  if (!directory) throw new Error('Isolated test mailbox is required.');
  return readdirSync(directory).flatMap((name) => {
    const content = readFileSync(join(directory, name), 'utf8');
    if (!content.includes(`To: ${email}`)) return [];
    return content.match(/http:\/\/127\.0\.0\.1:\d+\/verify-email#token=[A-Za-z0-9_-]{43}/g) ?? [];
  });
}

test('register, resend, verify once and sign in through real email delivery', async ({ page }, info) => {
  const email = `registration-${info.project.name}@iut.example`;
  const password = 'synthetic-registration-password-123';
  await page.goto('/register');
  await page.getByLabel('Institutional email').fill(email);
  await page.getByLabel('Display name').fill('New Student');
  await page.getByLabel('Password', { exact: false }).fill(password);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: `test-results/registration-${info.project.name}.png`, fullPage: true });
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('status')).toContainText('If this address is eligible');
  await expect.poll(() => linksFor(email).length).toBe(1);
  const first = linksFor(email)[0]!;
  await page.goto('/login');
  await page.getByLabel('Institutional email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toContainText('Unable to sign in');
  await page.goto('/resend-verification');
  await page.getByLabel('Institutional email').fill(email);
  await page.getByRole('button', { name: 'Send verification link' }).click();
  await expect(page.getByRole('status')).toContainText('If this address is eligible');
  await expect.poll(() => linksFor(email).length).toBe(2);
  const fresh = linksFor(email).find((link) => link !== first)!;
  await page.goto(first);
  await page.getByRole('button', { name: 'Verify email' }).click();
  await expect(page.getByRole('alert')).toContainText('invalid or expired');
  await page.goto(fresh);
  await expect(page.getByRole('button', { name: 'Verify email' })).toBeVisible();
  expect(new URL(page.url()).hash).toBe('');
  await page.getByRole('button', { name: 'Verify email' }).click();
  await expect(page.getByRole('status')).toContainText('Email verified');
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({ path: `test-results/verified-${info.project.name}.png`, fullPage: true });
  await page.goto(fresh);
  await page.getByRole('button', { name: 'Verify email' }).click();
  await expect(page.getByRole('alert')).toContainText('invalid or expired');
  await page.goto('/login');
  await page.getByLabel('Institutional email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'You’re signed in.' })).toBeVisible();
  await expect(page.getByText(email, { exact: true })).toBeVisible();
});
