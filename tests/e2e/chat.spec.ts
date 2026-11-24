import { expect, test } from '../../frontend/node_modules/@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.getByPlaceholder('Ask about IT, HR, or an existing ticket…')).toBeEnabled();
  await page.getByRole('button', { name: 'New conversation' }).click();
});

test('answers with sources and restores the conversation after refresh', async ({ page }) => {
  await page.getByRole('textbox', { name: 'Message' }).fill('Tell me about the VPN');
  await page.getByRole('button', { name: 'Send message' }).click();
  await expect(page.getByText('Company VPN supports managed macOS laptops. [1]')).toBeVisible();
  await page.locator('summary').click();
  await expect(page.getByText('Source: synthetic:test')).toBeVisible();
  await page.getByRole('textbox', { name: 'Message' }).fill('Does it work on Mac?');
  await page.getByRole('button', { name: 'Send message' }).click();
  await expect(page.getByText('Company VPN supports managed macOS laptops. [1]')).toHaveCount(2);
  await page.reload();
  await expect(page.getByText('Does it work on Mac?')).toBeVisible();
});

test('unknown question escalates, edited ticket requires confirmation, status is shown', async ({ page }) => {
  const box = page.getByRole('textbox', { name: 'Message' });
  await box.fill('Where is parking?'); await page.getByRole('button', { name: 'Send message' }).click();
  await expect(page.getByText(/Would you like me to prepare/)).toBeVisible();
  await box.fill('Create a ticket for my flickering monitor'); await page.getByRole('button', { name: 'Send message' }).click();
  await expect(page.getByRole('region', { name: 'Ticket preview' })).toBeVisible();
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  await page.getByLabel('Summary', { exact: true }).fill('Monitor needs inspection');
  await page.getByRole('button', { name: 'Save and review' }).click();
  await expect(page.getByRole('heading', { name: 'Monitor needs inspection' })).toBeVisible();
  await page.getByRole('button', { name: 'Confirm & create ticket' }).click();
  await expect(page.getByText(/Ticket IT-\d+ has been created/)).toBeVisible();
  await box.fill('Ticket status'); await page.getByRole('button', { name: 'Send message' }).click();
  await expect(page.getByText('Replacement ordered.')).toBeVisible();
});

test('cancelled ticket produces no creation success', async ({ page }) => {
  await page.getByRole('textbox', { name: 'Message' }).fill('Create a ticket');
  await page.getByRole('button', { name: 'Send message' }).click();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByText('Ticket creation cancelled.')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Ticket preview' })).toHaveCount(0);
});

test('mobile welcome fits the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: "Employee support" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: 'test-results/mobile-welcome.png', fullPage: true });
});


test('discarding ticket edits restores the approved draft', async ({ page }) => {
  await page.getByRole('textbox', { name: 'Message' }).fill('Create a ticket');
  await page.getByRole('button', { name: 'Send message' }).click();
  const preview = page.getByRole('region', { name: 'Ticket preview' });
  const summary = await preview.getByRole('heading').innerText();
  await preview.getByRole('button', { name: 'Edit', exact: true }).click();
  await page.getByLabel('Summary', { exact: true }).fill('Unsaved replacement summary');
  await page.getByRole('button', { name: 'Discard edits' }).click();
  await expect(preview.getByRole('heading')).toHaveText(summary);
  await preview.getByRole('button', { name: 'Edit', exact: true }).click();
  await expect(page.getByLabel('Summary', { exact: true })).toHaveValue(summary);
});

test('a stale saved conversation does not prevent starting a new chat', async ({ page }) => {
  await page.evaluate(() => localStorage.setItem('smartdesk-conversation', 'missing-conversation'));
  await page.reload();
  await expect(page.getByRole('textbox', { name: 'Message' })).toBeEnabled();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
