import { test, expect } from '@playwright/test';

/**
 * Visual regression suite for the 4 key pages. Runs against every project
 * defined in playwright.config.ts (chromium/firefox/webkit desktop +
 * iPhone SE/iPhone 14/iPad Pro 11/Pixel 7), so a rendering bug specific to
 * one engine or viewport (like the Firefox-only white-block bug, B58)
 * fails here automatically instead of needing a human to spot it.
 *
 * Baseline screenshots are committed to e2e/visual-regression.spec.ts-snapshots/.
 * To intentionally update a baseline after a real design change, run:
 *   npx playwright test --update-snapshots
 */

const pages = [
  { name: 'dashboard', path: '/' },
  { name: 'shopping-list', path: '/shopping' },
  { name: 'all-recipes', path: '/all-recipes' },
  { name: 'add-recipe', path: '/add-recipe' },
];

for (const { name, path } of pages) {
  test(`${name} renders without visual regressions`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot(`${name}.png`, {
      fullPage: true,
      // Small anti-aliasing/font-hinting differences are expected across
      // engines; this only catches real layout/rendering breaks.
      maxDiffPixelRatio: 0.02,
    });
  });
}
