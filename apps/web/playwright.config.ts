// Playwright config. Runs the three priority flows from
// phase8_design.md §16.3 across mobile + tablet + desktop viewports.

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "list" : "html",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "Pixel 5", use: { ...devices["Pixel 5"] } },
    { name: "iPhone 13", use: { ...devices["iPhone 13"] } },
    { name: "iPad Mini", use: { ...devices["iPad Mini"] } },
    { name: "Desktop 1280", use: { viewport: { width: 1280, height: 800 } } },
  ],
  webServer: {
    command: "pnpm dev",
    port: 3000,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
