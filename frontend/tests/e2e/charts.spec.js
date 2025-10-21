import { test, expect } from '@playwright/test'

/**
 * E2E Tests for Charts Page
 *
 * Tests the K-line chart functionality including:
 * - Chart rendering
 * - Zoom controls
 * - Timeframe switching
 * - Technical indicator switching
 * - Data loading from different sources (Redis, Database, API)
 */

// Test user credentials (ensure these exist in your test database)
const TEST_USER = {
  username: 'test_user',
  password: 'test_password'
}

test.describe('Charts Page', () => {
  test.beforeEach(async ({ page }) => {
    // Monitor console for errors
    const consoleErrors = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })
    page.consoleErrors = consoleErrors

    // Monitor page errors
    const pageErrors = []
    page.on('pageerror', error => {
      pageErrors.push(error.message)
    })
    page.pageErrors = pageErrors

    // Login before each test
    await page.goto('/login')
    await page.fill('input[placeholder="用户名"]', TEST_USER.username)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button:has-text("登录")')

    // Wait for login to complete and redirect
    await page.waitForURL('**/', { timeout: 10000 })
  })

  test('should load chart page without errors', async ({ page }) => {
    // Navigate to Charts page
    await page.goto('/charts')

    // Wait for chart container to be visible
    await expect(page.locator('.charts-view')).toBeVisible({ timeout: 10000 })

    // Wait for chart to load (check for ECharts canvas)
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 })

    // Check for console errors
    const echartErrors = page.consoleErrors.filter(err =>
      err.includes('ECharts') || err.includes('setOption') || err.includes('resize')
    )

    if (echartErrors.length > 0) {
      console.error('ECharts errors detected:', echartErrors)
    }

    expect(echartErrors).toHaveLength(0)

    // Check for page errors
    expect(page.pageErrors).toHaveLength(0)
  })

  test('should display pair list and allow selection', async ({ page }) => {
    await page.goto('/charts')

    // Wait for pair list to load
    await expect(page.locator('.pair-list')).toBeVisible()

    // Check that multiple pairs are displayed
    const pairItems = page.locator('.pair-item')
    await expect(pairItems).toHaveCount(5, { timeout: 10000 })

    // Click on a different pair (e.g., ETH/USDT)
    await pairItems.filter({ hasText: 'ETH/USDT' }).click()

    // Verify the chart title updated
    await expect(page.locator('.chart-title')).toHaveText('ETH/USDT', { timeout: 5000 })

    // Wait for new chart data to load
    await page.waitForTimeout(2000)

    // Check for errors after switching pairs
    const echartErrors = page.consoleErrors.filter(err =>
      err.includes('ECharts') || err.includes('setOption')
    )
    expect(echartErrors).toHaveLength(0)
  })

  test('should display and operate zoom controls', async ({ page }) => {
    await page.goto('/charts')

    // Wait for chart to load
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 })

    // Wait a bit for chart to fully render
    await page.waitForTimeout(2000)

    // Try to interact with zoom - use mouse wheel on chart
    const chartCanvas = page.locator('canvas').first()
    const chartBox = await chartCanvas.boundingBox()

    if (chartBox) {
      // Scroll to zoom in
      await page.mouse.move(chartBox.x + chartBox.width / 2, chartBox.y + chartBox.height / 2)
      await page.mouse.wheel(0, -100)

      await page.waitForTimeout(1000)

      // Check for dataZoom-related errors
      const dataZoomErrors = page.consoleErrors.filter(err =>
        err.includes('setOption') && err.includes('main process')
      )

      if (dataZoomErrors.length > 0) {
        console.error('DataZoom errors detected:', dataZoomErrors)
      }

      expect(dataZoomErrors).toHaveLength(0)

      // Scroll to zoom out
      await page.mouse.wheel(0, 100)
      await page.waitForTimeout(1000)

      // Check for errors again
      const moreErrors = page.consoleErrors.filter(err =>
        err.includes('setOption') && err.includes('main process')
      )
      expect(moreErrors).toHaveLength(0)

      // Verify chart is still responsive (canvas still visible)
      await expect(chartCanvas).toBeVisible()
    }
  })

  test('should switch timeframes without errors', async ({ page }) => {
    await page.goto('/charts')

    // Wait for chart to load
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 })

    // Clear previous errors
    page.consoleErrors.length = 0

    // Click on different timeframe buttons and verify no ECharts errors
    const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']

    for (const tf of timeframes) {
      // Click timeframe button
      await page.click(`label.el-radio-button:has-text("${tf}")`)

      // Wait for chart to update
      await page.waitForTimeout(2000)

      // Check for ECharts errors after switching (the main goal of this test)
      const errors = page.consoleErrors.filter(err =>
        err.includes('ECharts') || err.includes('setOption') || err.includes('resize')
      )

      if (errors.length > 0) {
        console.error(`Errors after switching to ${tf}:`, errors)
      }

      // This is the critical assertion - no ECharts errors
      expect(errors).toHaveLength(0)
      page.consoleErrors.length = 0
    }

    // Verify chart is still visible and responsive
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('should toggle technical indicators without errors', async ({ page }) => {
    await page.goto('/charts')

    // Wait for chart to load
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 })

    // Clear previous errors
    page.consoleErrors.length = 0
    page.pageErrors.length = 0

    const indicators = ['MACD', 'RSI', 'BOLL']

    for (const indicator of indicators) {
      // Toggle indicator on
      await page.click(`label.el-checkbox-button:has-text("${indicator}")`)
      await page.waitForTimeout(2000)

      // Check for ECharts-specific errors only
      const echartErrors = page.consoleErrors.filter(err =>
        err.includes('ECharts') || err.includes('setOption') || err.includes('resize') || err.includes('assert')
      )

      if (echartErrors.length > 0) {
        console.error(`ECharts errors after enabling ${indicator}:`, echartErrors)
      }

      expect(echartErrors).toHaveLength(0)

      // Check for critical page errors (ECharts assertion failures)
      const criticalErrors = page.pageErrors.filter(err =>
        err.includes('ECharts') || err.includes('assert') || err.includes('setOption')
      )

      if (criticalErrors.length > 0) {
        console.error(`Critical errors after enabling ${indicator}:`, criticalErrors)
      }

      expect(criticalErrors).toHaveLength(0)

      // Toggle indicator off
      await page.click(`label.el-checkbox-button:has-text("${indicator}")`)
      await page.waitForTimeout(2000)

      // Clear errors for next iteration
      page.consoleErrors.length = 0
      page.pageErrors.length = 0
    }
  })

  test('should display data source indicator', async ({ page }) => {
    await page.goto('/charts')

    // Wait for chart to load
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 })

    // Check for data source tag (should be one of: 缓存, 数据库, API)
    const sourceTag = page.locator('.chart-toolbar .el-tag').nth(1)
    await expect(sourceTag).toBeVisible()

    const sourceText = await sourceTag.textContent()
    expect(['缓存', '数据库', 'API']).toContain(sourceText)
  })

  test('should handle rapid interactions without crashing', async ({ page }) => {
    await page.goto('/charts')

    // Wait for chart to load
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 })

    // Clear previous errors
    page.consoleErrors.length = 0
    page.pageErrors.length = 0

    // Rapidly switch timeframes
    await page.click('label.el-radio-button:has-text("1m")')
    await page.waitForTimeout(500)
    await page.click('label.el-radio-button:has-text("5m")')
    await page.waitForTimeout(500)
    await page.click('label.el-radio-button:has-text("15m")')
    await page.waitForTimeout(500)
    await page.click('label.el-radio-button:has-text("1h")')

    // Wait for all updates to settle
    await page.waitForTimeout(3000)

    // Rapidly toggle indicators
    await page.click('label.el-checkbox-button:has-text("MACD")')
    await page.waitForTimeout(500)
    await page.click('label.el-checkbox-button:has-text("RSI")')
    await page.waitForTimeout(500)
    await page.click('label.el-checkbox-button:has-text("MACD")')
    await page.waitForTimeout(500)
    await page.click('label.el-checkbox-button:has-text("RSI")')

    // Wait for all updates to settle
    await page.waitForTimeout(3000)

    // Check for ECharts-specific errors only
    const echartErrors = page.consoleErrors.filter(err =>
      err.includes('ECharts') || err.includes('setOption') || err.includes('resize') || err.includes('assert')
    )

    if (echartErrors.length > 0) {
      console.error('ECharts errors after rapid interactions:', echartErrors)
    }

    expect(echartErrors).toHaveLength(0)

    // Check for critical page errors
    const criticalErrors = page.pageErrors.filter(err =>
      err.includes('ECharts') || err.includes('assert') || err.includes('setOption')
    )

    if (criticalErrors.length > 0) {
      console.error('Critical errors after rapid interactions:', criticalErrors)
    }

    expect(criticalErrors).toHaveLength(0)

    // Verify chart is still responsive
    await expect(page.locator('canvas').first()).toBeVisible()
  })

  test('should search and filter pairs', async ({ page }) => {
    await page.goto('/charts')

    // Wait for pair list to load
    await expect(page.locator('.pair-list')).toBeVisible()

    // Type in search box
    await page.fill('.search-box input', 'BTC')

    // Should only show BTC pairs
    const pairItems = page.locator('.pair-item')
    await expect(pairItems).toHaveCount(1)
    await expect(pairItems.first()).toContainText('BTC/USDT')

    // Clear search
    await page.fill('.search-box input', '')

    // Should show all pairs again
    await expect(pairItems).toHaveCount(5)
  })

  test('should display signal list when available', async ({ page }) => {
    await page.goto('/charts')

    // Wait for charts view to load
    await expect(page.locator('.charts-view')).toBeVisible({ timeout: 10000 })

    // Right panel should be visible
    await expect(page.locator('.right-panel')).toBeVisible({ timeout: 10000 })

    // Signal list should be visible (may be empty)
    await expect(page.locator('.signal-list')).toBeVisible({ timeout: 5000 })

    // If there are signals, verify they display correctly
    const signalItems = page.locator('.signal-item')
    const signalCount = await signalItems.count()

    if (signalCount > 0) {
      // Check first signal has required elements
      const firstSignal = signalItems.first()
      await expect(firstSignal.locator('.signal-header')).toBeVisible()
      await expect(firstSignal.locator('.signal-body')).toBeVisible()
    }
  })
})

test.describe('Charts Page - Error Scenarios', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    // Intercept API calls and return error
    await page.route('**/api/v1/market/klines*', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Internal Server Error' })
      })
    })

    await page.goto('/login')
    await page.fill('input[placeholder="用户名"]', TEST_USER.username)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button:has-text("登录")')
    await page.waitForURL('**/')

    await page.goto('/charts')

    // Should show error message (there may be multiple, so use .first())
    await expect(page.locator('.el-message--error').first()).toBeVisible({ timeout: 10000 })

    // Chart should still render (with empty state or loading state)
    await expect(page.locator('.charts-view')).toBeVisible()

    // Clean up routes
    await page.unrouteAll({ behavior: 'ignoreErrors' })
  })

  test('should handle network timeout', async ({ page }) => {
    // Intercept API calls and delay response
    let requestIntercepted = false
    await page.route('**/api/v1/market/klines*', async route => {
      requestIntercepted = true
      // Delay then abort to simulate timeout
      await new Promise(resolve => setTimeout(resolve, 5000))
      await route.abort()
    })

    await page.goto('/login')
    await page.fill('input[placeholder="用户名"]', TEST_USER.username)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button:has-text("登录")')
    await page.waitForURL('**/')

    await page.goto('/charts')

    // Should show loading state
    await expect(page.locator('.loading-placeholder')).toBeVisible({ timeout: 5000 })

    // Verify request was intercepted
    expect(requestIntercepted).toBe(true)

    // Clean up routes
    await page.unrouteAll({ behavior: 'ignoreErrors' })
  })
})
