import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test('should load the landing page successfully', async ({ page }) => {
    // Navigate to the root URL
    await page.goto('/');

    // Expect a title "to contain" a substring.
    await expect(page).toHaveTitle(/Ayura AI/);
  });

  test('should display the main hero headline', async ({ page }) => {
    await page.goto('/');

    // Look for the main headline. The visible hero is an <h2 class="lnd-hero-title">
    // (a keyword-rich <h1 class="sr-only"> exists separately for SEO).
    const headline = page.locator('.lnd-hero-title');
    await expect(headline).toBeVisible();
    await expect(headline).toContainText(/Your.*wellness/i);
  });

  test('should have a working Sign In link in the navigation', async ({ page }) => {
    await page.goto('/');

    // Find the Sign In link and click it
    const signInLink = page.getByRole('link', { name: /Sign In/i }).first();
    await expect(signInLink).toBeVisible();
    
    await signInLink.click();

    // Verify we navigated to the login page
    await expect(page).toHaveURL(/.*\/login/);
    await expect(page.locator('.auth-card-title')).toContainText('Welcome');
  });
});
