import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "../tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://127.0.0.1:5173", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        process.platform === "win32"
          ? ".venv\\Scripts\\python.exe -m uvicorn tests.e2e_server:app --host 127.0.0.1 --port 8001"
          : ".venv/bin/python -m uvicorn tests.e2e_server:app --host 127.0.0.1 --port 8001",
      cwd: "../backend",
      url: "http://127.0.0.1:8001/health/live",
      timeout: 120000,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5173",
      env: { VITE_API_PROXY: "http://127.0.0.1:8001" },
      url: "http://127.0.0.1:5173",
      timeout: 120000,
      reuseExistingServer: false,
    },
  ],
});
