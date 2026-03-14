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

  test('login → subject list → subject timeline (requires backend and E2E credentials)', async ({ page }) => {
    const tenant = process.env.E2E_TENANT_CODE
    const email = process.env.E2E_LOGIN_EMAIL
    const password = process.env.E2E_LOGIN_PASSWORD
    if (!tenant || !email || !password) {
      test.skip()
      return
    }

    await page.goto('/login')
    await page.getByLabel(/organisation|workspace|tenant/i).fill(tenant)
    await page.getByLabel(/email/i).fill(email)
    await page.getByLabel(/password/i).fill(password)
    await page.getByRole('button', { name: /sign in|log in/i }).click()

    await expect(page).not.toHaveURL(/\/login/, { timeout: 15000 })
    await page.goto('/subjects')
    await expect(page).toHaveURL(/\/subjects/)

    const firstSubjectLink = page.getByRole('link', { name: /.+/ }).first()
    if (await firstSubjectLink.isVisible()) {
      await firstSubjectLink.click()
      await expect(page).toHaveURL(/\/subjects\/[^/]+/)
    }
  })
})
