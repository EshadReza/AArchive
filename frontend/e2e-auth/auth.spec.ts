import { execFileSync } from 'node:child_process';
import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('real login, persistent account, CSRF, logout and suspended-session rejection', async ({ page, context }, info) => {
  const email = `browser-${info.project.name}@iut.example`;
  await page.goto('/login');
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({ path: `test-results/login-${info.project.name}.png`, fullPage: true });
  const initialToken = (await context.cookies()).find((cookie) => cookie.name === 'csrftoken')?.value;
  await page.getByLabel('Institutional email', { exact: false }).fill(email);
  await page.getByLabel('Password', { exact: false }).fill('wrong-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toHaveText('Unable to sign in with those details.');
  await expect(page.getByRole('alert')).toBeFocused();
  await expect(page.getByLabel('Password', { exact: false })).toHaveValue('');
  await page.getByLabel('Password', { exact: false }).fill('synthetic-browser-password-123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'You’re signed in.' })).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();
  const cookies = await context.cookies();
  const session = cookies.find((cookie) => cookie.name === 'sessionid');
  expect(session?.httpOnly).toBe(true);
  expect(session?.sameSite).toBe('Lax');
  expect(cookies.find((cookie) => cookie.name === 'csrftoken')?.value).not.toBe(initialToken);
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  expect(await page.evaluate(() => document.cookie.includes('sessionid='))).toBe(false);
  expect((await page.request.post('/api/auth/logout', { data: {} })).status()).toBe(403);
  expect((await page.request.post('/api/auth/logout', { data: {}, headers: {
    Origin: 'https://hostile.invalid', 'X-CSRFToken': cookies.find((cookie) => cookie.name === 'csrftoken')?.value ?? '',
  } })).status()).toBe(403);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'You’re signed in.' })).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: `test-results/account-${info.project.name}.png`, fullPage: true });
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  await page.getByLabel('Institutional email', { exact: false }).fill(email);
  await page.getByLabel('Password', { exact: false }).fill('synthetic-browser-password-123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'You’re signed in.' })).toBeVisible();
  execFileSync(process.env.AUTH_E2E_PYTHON!, ['../scripts/auth_browser_fixture.py', 'suspend', info.project.name]);
  await page.getByRole('button', { name: 'Refresh session' }).click();
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  execFileSync(process.env.AUTH_E2E_PYTHON!, ['../scripts/auth_browser_fixture.py', 'restore', info.project.name]);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
});

test('lockout has a generic error and recovers after its window', async ({ page }, info) => {
  await page.goto('/login');
  await page.getByLabel('Institutional email', { exact: false }).fill(`unknown-${info.project.name}@iut.example`);
  for (let index = 0; index < 4; index += 1) {
    await page.getByLabel('Password', { exact: false }).fill('synthetic-wrong-password');
    const response = page.waitForResponse((value) => value.url().endsWith('/api/auth/login'));
    await page.getByRole('button', { name: 'Sign in' }).click();
    expect((await response).status()).toBe(index === 3 ? 429 : 401);
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeEnabled();
  }
  await expect(page.getByRole('alert')).toHaveText('Too many sign-in attempts. Try again later.');
  await expect.poll(async () => {
    const token = (await page.context().cookies()).find((cookie) => cookie.name === 'csrftoken')?.value ?? '';
    return (await page.request.post('/api/auth/login', { data: { email: `unknown-${info.project.name}@iut.example`, password: 'synthetic-wrong-password' }, headers: { 'X-CSRFToken': token } })).status();
  }, { timeout: 12000, intervals: [500] }).toBe(401);
});
