import { chromium, FullConfig } from '@playwright/test';

/**
 * Logs in once via a real browser as the seeded e2e test user (see
 * e2e/seed_test_data.py) and saves the authenticated session cookie to
 * e2e/.auth/user.json. Every test project reuses this storage state
 * instead of logging in per-test/per-browser.
 */
async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL ?? 'http://localhost:5000';

  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto(`${baseURL}/login-page`);
  await page.fill('#email', 'e2e-test@example.com');
  await page.fill('#password', 'E2ETestPass123');
  await page.click('button[type="submit"]');

  // Login redirects to /profile-picker, which (for a single-owner household
  // with no extra profiles) immediately redirects again to the dashboard.
  // Wait for that final landing, not just "away from /login".
  await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 });

  await page.context().storageState({ path: 'e2e/.auth/user.json' });
  await browser.close();
}

export default globalSetup;
