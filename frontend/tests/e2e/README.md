# E2E Testing with Playwright

This directory contains end-to-end tests for the BTC Watcher frontend application using Playwright.

## Prerequisites

1. **Test User**: You need a test user in the database with the following credentials:
   - Username: `test_user`
   - Password: `test_password`

   Create the test user by running:
   ```bash
   cd ../../backend
   python -c "
   from database.session import SessionLocal
   from models.user import User
   from core.security import get_password_hash

   db = SessionLocal()
   test_user = User(
       username='test_user',
       email='test@example.com',
       hashed_password=get_password_hash('test_password')
   )
   db.add(test_user)
   db.commit()
   print('Test user created successfully')
   "
   ```

2. **Running Services**: Make sure the following services are running:
   - PostgreSQL database
   - Redis
   - Backend API (http://localhost:8000)
   - Frontend dev server (will be started automatically by Playwright)

## Installation

Playwright is already installed as a dev dependency. If you need to install it manually:

```bash
npm install -D @playwright/test
npx playwright install chromium
```

## Running Tests

### Run all E2E tests
```bash
npm run test:e2e
```

### Run tests in UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Run tests in debug mode
```bash
npm run test:e2e:debug
```

### View test report (after running tests)
```bash
npm run test:e2e:report
```

### Run specific test file
```bash
npx playwright test tests/e2e/charts.spec.js
```

### Run specific test
```bash
npx playwright test tests/e2e/charts.spec.js -g "should load chart page without errors"
```

## Test Structure

### charts.spec.js

Tests for the Charts page functionality:

#### Main Test Suite
- **should load chart page without errors**: Verifies the chart loads without console or page errors
- **should display pair list and allow selection**: Tests currency pair selection
- **should display and operate zoom controls**: Tests chart zoom functionality (critical for debugging ECharts issues)
- **should switch timeframes without errors**: Tests timeframe switching (1m, 5m, 15m, 4h, 1d)
- **should toggle technical indicators without errors**: Tests indicator toggling (MA, MACD, RSI, BOLL, VOL)
- **should display data source indicator**: Verifies data source tag (缓存/数据库/API)
- **should handle rapid interactions without crashing**: Stress test with rapid UI changes
- **should search and filter pairs**: Tests pair search functionality
- **should display signal list when available**: Tests signal display

#### Error Scenario Tests
- **should handle API errors gracefully**: Tests error handling when API returns 500
- **should handle network timeout**: Tests behavior with delayed API responses

## Key Features Tested

### ECharts Error Detection

All tests monitor for ECharts-specific errors:
- `setOption` during main process errors
- `resize` during main process errors
- Assertion errors in ECharts
- Internal ECharts errors (`__ec_inner_*`)

### Console and Page Error Tracking

Each test automatically collects:
- Console errors via `page.on('console')`
- Page errors via `page.on('pageerror')`

These are checked after each interaction to ensure no errors occurred.

## Debugging ECharts Issues

The E2E tests are specifically designed to catch the ECharts recursive call errors:

1. **Zoom Control Test**: The `should display and operate zoom controls` test simulates mouse wheel zoom operations and checks for dataZoom-related errors.

2. **Rapid Interaction Test**: The `should handle rapid interactions without crashing` test rapidly toggles timeframes and indicators to stress-test the chart update logic.

3. **Indicator Toggle Test**: Tests each indicator individually and checks for errors after enabling/disabling.

If tests fail with ECharts errors, you can:
- Run in debug mode: `npm run test:e2e:debug`
- Run in UI mode to see visual feedback: `npm run test:e2e:ui`
- Check the test report for screenshots and videos: `npm run test:e2e:report`

## CI/CD Integration

The tests are configured to:
- Run in headless mode on CI
- Retry failed tests 2 times
- Capture screenshots on failure
- Record videos on failure
- Generate HTML reports

## Troubleshooting

### Frontend dev server doesn't start

Make sure port 3000 is available:
```bash
lsof -i :3000
```

### Backend API is not accessible

Verify the backend is running:
```bash
curl http://localhost:8000/health
```

### Tests timeout during login

Check that the test user exists in the database and credentials are correct.

### Chart doesn't load

Verify that:
1. Redis is running and accessible
2. Database has market data (or API calls work)
3. Backend market data endpoints are functional

## Writing New Tests

When adding new E2E tests:

1. Import helpers:
   ```javascript
   import { test, expect } from '@playwright/test'
   import { login, waitForChartLoaded, getEChartsErrors } from './helpers'
   ```

2. Use the `beforeEach` hook for authentication:
   ```javascript
   test.beforeEach(async ({ page }) => {
     await login(page, 'test_user', 'test_password')
   })
   ```

3. Monitor for errors:
   ```javascript
   const consoleErrors = []
   page.on('console', msg => {
     if (msg.type() === 'error') {
       consoleErrors.push(msg.text())
     }
   })
   ```

4. Check for specific errors:
   ```javascript
   const echartErrors = getEChartsErrors(consoleErrors)
   expect(echartErrors).toHaveLength(0)
   ```

## Configuration

See `playwright.config.js` for configuration options:
- Test directory: `./tests/e2e`
- Base URL: `http://localhost:3000`
- Browser: Chromium (Desktop Chrome)
- Screenshots: On failure only
- Videos: On failure only
- Trace: On first retry
