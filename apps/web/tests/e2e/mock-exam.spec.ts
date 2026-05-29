// Mock-exam end-to-end (training mode): start → run → report.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ context }) => {
  await context.addCookies([
    { name: "tcf_auth", value: "1", url: "http://localhost:3000" },
    { name: "tcf_onboarded", value: "1", url: "http://localhost:3000" },
  ]);
});

test("training-mode mock end-to-end", async ({ page }) => {
  await page.goto("/mock-exam/start");
  await page.getByRole("radio", { name: /training/i }).check();
  await page.getByRole("button", { name: /start mock exam/i }).click();
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: /submit/i }).click();
  await page.getByRole("button", { name: /next/i }).click();
  await expect(page).toHaveURL(/mock-exam\/report/);
});

test("mock report has no axe violations and surfaces the κ footer", async ({ page }) => {
  await page.goto("/mock-exam/report/fixture");
  await expect(page.getByText(/Model κ/)).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
