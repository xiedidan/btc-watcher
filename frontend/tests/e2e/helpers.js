import { test as base } from '@playwright/test'

/**
 * Test helpers and fixtures
 */

/**
 * Login helper function
 * @param {Page} page - Playwright page object
 * @param {string} username - Username
 * @param {string} password - Password
 */
export async function login(page, username, password) {
  await page.goto('/login')
  await page.fill('input[placeholder="用户名"]', username)
  await page.fill('input[type="password"]', password)
  await page.click('button:has-text("登录")')
  await page.waitForURL('**/', { timeout: 10000 })
}

/**
 * Wait for chart to be fully loaded
 * @param {Page} page - Playwright page object
 * @param {number} timeout - Timeout in ms (default: 15000)
 */
export async function waitForChartLoaded(page, timeout = 15000) {
  // Wait for chart container
  await page.waitForSelector('.charts-view', { timeout })

  // Wait for canvas (ECharts renders to canvas)
  await page.waitForSelector('canvas', { timeout })

  // Wait a bit more for chart to fully render
  await page.waitForTimeout(1000)
}

/**
 * Get console errors related to ECharts
 * @param {Array<string>} consoleErrors - Array of console error messages
 * @returns {Array<string>} Filtered ECharts errors
 */
export function getEChartsErrors(consoleErrors) {
  return consoleErrors.filter(err =>
    err.includes('ECharts') ||
    err.includes('setOption') ||
    err.includes('resize') ||
    err.includes('__ec_inner')
  )
}

/**
 * Extended test with authenticated context
 */
export const test = base.extend({
  // Add authenticated page fixture
  authenticatedPage: async ({ page }, use) => {
    // Login before each test using this fixture
    await login(page, 'test_user', 'test_password')
    await use(page)
  }
})

export { expect } from '@playwright/test'
