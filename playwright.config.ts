import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',
  /* One shared authenticated session (see e2e/global-setup.ts), reused by
     every project below instead of logging in per-test/per-browser. */
  globalSetup: require.resolve('./e2e/global-setup'),
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Single worker always, not just on CI: concurrent requests against the
     app's SQLite dev database (StaticPool, a single shared connection)
     intermittently throw "IndexError: tuple index out of range" deep in
     SQLAlchemy's cursor row-processing under parallel load - confirmed via
     repeated local runs (flaky with parallel workers, 100% reliable at
     workers: 1). Production uses Postgres and wouldn't hit this exact
     failure mode, but this suite runs against SQLite, so staying
     sequential here is the correct fix for the test suite, not a
     workaround for a bug worth chasing in this task's scope. */
  workers: 1,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:5000',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Reuse the logged-in session from global-setup. */
    storageState: 'e2e/.auth/user.json',
  },

  /* Configure projects: 3 desktop browser engines + 4 device viewports */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'iPhone SE',
      use: { ...devices['iPhone SE'] },
    },
    {
      name: 'iPhone 14',
      use: { ...devices['iPhone 14'] },
    },
    {
      name: 'iPad Pro 11',
      use: { ...devices['iPad Pro 11'] },
    },
    {
      name: 'Pixel 7',
      use: { ...devices['Pixel 7'] },
    },
  ],

  /* Boot the Flask app before running tests (CI and local alike). Uses the
     venv's python directly rather than RUN_LOCAL.bat/.ps1, which are
     interactive dev-convenience scripts, not meant for a subprocess.
     --no-reload is required: Flask's auto-reloader spawns a child process
     that does not reliably inherit env vars set inline for the parent
     command, so DATABASE_URL silently fell back to .env's real dev
     database without it - confirmed the hard way while wiring this up. */
  webServer: {
    command:
      process.platform === 'win32'
        ? 'venv\\Scripts\\python.exe -m flask --app deployment.flask_app run --host=0.0.0.0 --port=5000 --no-reload'
        : 'python -m flask --app deployment.flask_app run --host=0.0.0.0 --port=5000 --no-reload',
    url: 'http://localhost:5000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    env: {
      DATABASE_URL: 'sqlite:///e2e_test.db',
      FLASK_SECRET_KEY: 'e2e-test-secret-key',
    },
  },
});
