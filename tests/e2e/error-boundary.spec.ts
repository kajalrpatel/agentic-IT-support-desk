import { expect, test } from '../../frontend/node_modules/@playwright/test';

test('render failures show a safe fallback and reload recovers', async ({ page }) => {
  await page.route('**/src/App.tsx*', route => route.fulfill({
    contentType: 'application/javascript',
    body: 'export default function App() { throw new Error("private diagnostic detail"); }',
  }));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('Something went wrong');
  await expect(page.getByRole('alert')).not.toContainText('private diagnostic detail');
  await page.unroute('**/src/App.tsx*');
  await page.getByRole('button', { name: 'Reload workspace' }).click();
  await expect(page.getByRole('textbox', { name: 'Message' })).toBeEnabled();
});
