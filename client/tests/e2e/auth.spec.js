import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should show validation error when submitting empty login form', async ({ page }) => {
    await page.goto('/login');

    // Make sure we are on the login page
    await expect(page.locator('.auth-card-title')).toContainText('Welcome');

    // Click the submit button without filling in fields
    const submitButton = page.getByRole('button', { name: 'Sign In →' });
    await submitButton.click();

    // HTML5 validation will trigger. Playwright evaluates the form validity
    const emailInput = page.getByLabel(/Email address/i);
    const isValid = await emailInput.evaluate((input) => input.checkValidity());
    expect(isValid).toBe(false);
  });

  test('should display backend error for invalid credentials', async ({ page }) => {
    // We mock the backend response to test the error UI without hitting the real DB
    await page.route('**/api/auth/login', async route => {
      const json = { detail: "Incorrect email or password" };
      await route.fulfill({ status: 401, json });
    });

    await page.goto('/login');

    // Fill in fake credentials
    await page.getByLabel(/Email address/i).fill('fake@ayura.ai');
    await page.getByLabel(/Password/i).fill('wrongpassword');

    // Submit form
    await page.getByRole('button', { name: 'Sign In →' }).click();

    // Wait for the error message to appear in the UI
    const errorMessage = page.locator('.auth-error');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('Incorrect email or password');
  });

  test('should navigate to register page from login', async ({ page }) => {
    await page.goto('/login');

    const createAccountLink = page.getByRole('link', { name: /Create account/i });
    await expect(createAccountLink).toBeVisible();
    await createAccountLink.click();

    await expect(page).toHaveURL(/.*\/register/);
    await expect(page.locator('.auth-card-title')).toContainText('Begin your journey');
  });
});
