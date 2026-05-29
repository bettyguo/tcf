// Drill happy path: open a session, answer, reveal, next.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ context }) => {
  await context.addCookies([
    { name: "tcf_auth", value: "1", url: "http://localhost:3000" },
    { name: "tcf_onboarded", value: "1", url: "http://localhost:3000" },
  ]);
});

test("drill flow PRESENTED → REVEALED with axe-clean rationale", async ({ page }) => {
  await page.goto("/today/session?block=b3");
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: /submit/i }).click();
  await expect(page.getByText(/rationale/i)).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("keyboard-only: tab → submit answers and reveals", async ({ page }) => {
  await page.goto("/today/session?block=b3");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter"); // select first radio
  // The DrillPlayer listens for Enter to submit while in ANSWERING.
  await page.keyboard.press("Enter");
  await expect(page.getByText(/rationale/i)).toBeVisible();
});
