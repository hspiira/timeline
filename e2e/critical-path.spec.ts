import { test, expect } from '@playwright/test'

test.describe('Critical path', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: /sign in|login|timeline/i })).toBeVisible({ timeout: 10000 })
  })

  test('unauthenticated user is redirected to login from subjects', async ({ page }) => {
    await page.goto('/subjects')
    await expect(page).toHaveURL(/\/login/)
  })
})
