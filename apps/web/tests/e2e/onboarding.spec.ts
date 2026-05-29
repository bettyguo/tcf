// Onboarding happy path: goals → diagnostic → plan-preview → today.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("user completes onboarding and lands on Today", async ({ page }) => {
  await page.goto("/onboarding/goals");
  await expect(page.getByRole("heading", { name: /goal/i })).toBeVisible();
  await page.getByRole("spinbutton").fill("9");
  await page.getByRole("button", { name: /continue/i }).click();

  await expect(page).toHaveURL(/\/onboarding\/diagnostic/);
  await page.getByRole("button", { name: /start/i }).click();

  // The DrillPlayer auto-advances PRESENTED → ANSWERING.
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: /submit/i }).click();
  await page.getByRole("button", { name: /next/i }).click();

  await expect(page).toHaveURL(/\/onboarding\/plan-preview/);
  await page.getByRole("button", { name: /start today/i }).click();
  await expect(page).toHaveURL(/\/today/);
});

test("Today has no axe violations", async ({ page }) => {
  // Set the cookies the middleware expects so /today renders.
  await page.context().addCookies([
    { name: "tcf_auth", value: "1", url: "http://localhost:3000" },
    { name: "tcf_onboarded", value: "1", url: "http://localhost:3000" },
  ]);
  await page.goto("/today");
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
