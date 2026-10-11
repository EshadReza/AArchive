import { expect, test } from '@playwright/test';

test('production build excludes the development workshop', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Keep every effort in context.');
  await expect(page.getByRole('link', { name: 'Interface workshop', exact: true })).toHaveCount(0);
  await page.goto('/dev/primitives');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('This page isn’t here.');
  await expect(page.getByRole('textbox')).toHaveCount(0);
});
