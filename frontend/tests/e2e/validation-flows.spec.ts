/**
 * E2E Tests for Main User Flows
 * 
 * This file contains comprehensive end-to-end tests for the main user flows
 * including CSV import, batch validation, provider review, and report export.
 */

import { test, expect, Page } from '@playwright/test'

// Test data
const testProviders = [
  {
    provider_id: 'PROV_E2E_001',
    npi_number: '1234567890',
    given_name: 'John',
    family_name: 'Smith',
    phone_primary: '+1-555-123-4567',
    email: 'john.smith@example.com',
    address_street: '123 Main St',
    address_city: 'San Francisco',
    address_state: 'CA',
    address_zip: '94102',
    license_number: 'A12345',
    license_state: 'CA'
  },
  {
    provider_id: 'PROV_E2E_002',
    npi_number: '2345678901',
    given_name: 'Jane',
    family_name: 'Doe',
    phone_primary: '+1-555-234-5678',
    email: 'jane.doe@example.com',
    address_street: '456 Oak Ave',
    address_city: 'Los Angeles',
    address_state: 'CA',
    address_zip: '90210',
    license_number: 'B67890',
    license_state: 'CA'
  }
]

// Helper functions
async function loginAsReviewer(page: Page) {
  await page.goto('/login')
  await page.fill('[data-testid="username"]', 'reviewer@example.com')
  await page.fill('[data-testid="password"]', 'password123')
  await page.click('[data-testid="login-button"]')
  await expect(page).toHaveURL('/dashboard')
}

async function loginAsAdmin(page: Page) {
  await page.goto('/login')
  await page.fill('[data-testid="username"]', 'admin@example.com')
  await page.fill('[data-testid="password"]', 'password123')
  await page.click('[data-testid="login-button"]')
  await expect(page).toHaveURL('/dashboard')
}

async function createTestCSV() {
  const csvContent = [
    'provider_id,npi_number,given_name,family_name,phone_primary,email,address_street,address_city,address_state,address_zip,license_number,license_state',
    ...testProviders.map(p => Object.values(p).join(','))
  ].join('\n')
  
  return new Blob([csvContent], { type: 'text/csv' })
}

test.describe('Provider Validation E2E Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses for consistent testing
    await page.route('**/api/**', async (route) => {
      const url = route.request().url()
      
      if (url.includes('/api/auth/login')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            access_token: 'mock-jwt-token',
            refresh_token: 'mock-refresh-token',
            expires_in: 900
          })
        })
      } else if (url.includes('/api/providers')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            providers: testProviders.map(p => ({
              ...p,
              overall_confidence: 0.85,
              validation_status: 'valid',
              flags: [],
              last_validated_at: new Date().toISOString()
            })),
            total_count: testProviders.length
          })
        })
      } else if (url.includes('/api/validate/batch')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            job_id: 'test-job-123',
            status: 'started'
          })
        })
      } else if (url.includes('/api/validate/job/test-job-123/status')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            job_id: 'test-job-123',
            status: 'completed',
            progress: 100,
            results: testProviders.map(p => ({
              provider_id: p.provider_id,
              overall_confidence: 0.85,
              validation_status: 'valid',
              flags: []
            }))
          })
        })
      } else {
        await route.continue()
      }
    })
  })

  test('CSV Import and Batch Validation Flow', async ({ page }) => {
    await loginAsAdmin(page)

    // Navigate to providers page
    await page.click('[data-testid="nav-providers"]')
    await expect(page).toHaveURL('/providers')

    // Click import CSV button
    await page.click('[data-testid="import-csv-button"]')

    // Upload test CSV file
    const csvFile = await createTestCSV()
    await page.setInputFiles('[data-testid="csv-file-input"]', {
      name: 'test-providers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(await csvFile.text())
    })

    // Verify file is selected
    await expect(page.locator('[data-testid="file-name"]')).toContainText('test-providers.csv')

    // Start batch validation
    await page.click('[data-testid="start-validation-button"]')

    // Verify validation job started
    await expect(page.locator('[data-testid="validation-status"]')).toContainText('Processing')

    // Wait for validation to complete (mock will return completed status)
    await page.waitForTimeout(1000)

    // Verify validation completed
    await expect(page.locator('[data-testid="validation-status"]')).toContainText('Completed')

    // Verify providers are displayed in the table
    for (const provider of testProviders) {
      await expect(page.locator(`[data-testid="provider-${provider.provider_id}"]`)).toBeVisible()
    }
  })

  test('Provider Review and Accept Flow', async ({ page }) => {
    await loginAsReviewer(page)

    // Navigate to providers page
    await page.click('[data-testid="nav-providers"]')
    await expect(page).toHaveURL('/providers')

    // Find a provider with warning status
    const warningProvider = page.locator('[data-testid="provider-PROV_E2E_001"]')
    await expect(warningProvider).toBeVisible()

    // Click review button
    await warningProvider.locator('[data-testid="review-button"]').click()

    // Verify review modal opens
    await expect(page.locator('[data-testid="review-modal"]')).toBeVisible()

    // Verify provider details are displayed
    await expect(page.locator('[data-testid="provider-name"]')).toContainText('John Smith')
    await expect(page.locator('[data-testid="npi-number"]')).toContainText('1234567890')

    // Review field confidence scores
    await expect(page.locator('[data-testid="confidence-npi"]')).toContainText('90%')
    await expect(page.locator('[data-testid="confidence-address"]')).toContainText('85%')

    // Accept the provider
    await page.click('[data-testid="accept-button"]')

    // Verify success message
    await expect(page.locator('[data-testid="success-message"]')).toContainText('Provider accepted')

    // Verify modal closes
    await expect(page.locator('[data-testid="review-modal"]')).not.toBeVisible()

    // Verify provider status updated in table
    await expect(warningProvider.locator('[data-testid="status-badge"]')).toContainText('Valid')
  })

  test('Provider Reject with Note Flow', async ({ page }) => {
    await loginAsReviewer(page)

    // Navigate to providers page
    await page.click('[data-testid="nav-providers"]')

    // Find a provider
    const provider = page.locator('[data-testid="provider-PROV_E2E_002"]')
    await expect(provider).toBeVisible()

    // Click review button
    await provider.locator('[data-testid="review-button"]').click()

    // Verify review modal opens
    await expect(page.locator('[data-testid="review-modal"]')).toBeVisible()

    // Click reject button
    await page.click('[data-testid="reject-button"]')

    // Verify rejection modal opens
    await expect(page.locator('[data-testid="rejection-modal"]')).toBeVisible()

    // Add rejection note
    await page.fill('[data-testid="rejection-note"]', 'Invalid license information provided')

    // Confirm rejection
    await page.click('[data-testid="confirm-reject-button"]')

    // Verify success message
    await expect(page.locator('[data-testid="success-message"]')).toContainText('Provider rejected')

    // Verify modals close
    await expect(page.locator('[data-testid="rejection-modal"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="review-modal"]')).not.toBeVisible()

    // Verify provider status updated
    await expect(provider.locator('[data-testid="status-badge"]')).toContainText('Rejected')
  })

  test('Manual Review Queue Flow', async ({ page }) => {
    await loginAsReviewer(page)

    // Navigate to review queue
    await page.click('[data-testid="nav-review"]')
    await expect(page).toHaveURL('/review')

    // Verify review queue loads
    await expect(page.locator('[data-testid="review-queue"]')).toBeVisible()

    // Check assigned providers count
    await expect(page.locator('[data-testid="assigned-count"]')).toContainText('2')

    // Find a provider in the queue
    const queuedProvider = page.locator('[data-testid="queued-provider-PROV_E2E_001"]')
    await expect(queuedProvider).toBeVisible()

    // Click review button
    await queuedProvider.locator('[data-testid="review-button"]').click()

    // Verify review modal opens
    await expect(page.locator('[data-testid="review-modal"]')).toBeVisible()

    // Request manual verification
    await page.click('[data-testid="request-verification-button"]')

    // Verify verification modal opens
    await expect(page.locator('[data-testid="verification-modal"]')).toBeVisible()

    // Assign to reviewer
    await page.selectOption('[data-testid="reviewer-select"]', 'alice.johnson@example.com')

    // Add verification note
    await page.fill('[data-testid="verification-note"]', 'Need to verify address with provider')

    // Submit verification request
    await page.click('[data-testid="submit-verification-button"]')

    // Verify success message
    await expect(page.locator('[data-testid="success-message"]')).toContainText('Verification requested')

    // Verify provider is removed from queue
    await expect(queuedProvider).not.toBeVisible()
  })

  test('Export Report Flow', async ({ page }) => {
    await loginAsAdmin(page)

    // Navigate to providers page
    await page.click('[data-testid="nav-providers"]')

    // Select all providers
    await page.click('[data-testid="select-all-checkbox"]')

    // Verify bulk actions toolbar appears
    await expect(page.locator('[data-testid="bulk-actions-toolbar"]')).toBeVisible()

    // Click export CSV button
    await page.click('[data-testid="export-csv-button"]')

    // Verify download starts
    const downloadPromise = page.waitForEvent('download')
    const download = await downloadPromise

    // Verify download filename
    expect(download.suggestedFilename()).toContain('providers-export')

    // Test PDF export
    await page.click('[data-testid="export-pdf-button"]')

    // Verify PDF download
    const pdfDownloadPromise = page.waitForEvent('download')
    const pdfDownload = await pdfDownloadPromise

    expect(pdfDownload.suggestedFilename()).toContain('providers-report.pdf')
  })

  test('Dashboard KPI Display', async ({ page }) => {
    await loginAsAdmin(page)

    // Verify dashboard loads
    await expect(page).toHaveURL('/dashboard')

    // Check KPI cards
    await expect(page.locator('[data-testid="total-providers"]')).toContainText('200')
    await expect(page.locator('[data-testid="validation-accuracy"]')).toContainText('85%')
    await expect(page.locator('[data-testid="flagged-providers"]')).toContainText('15')
    await expect(page.locator('[data-testid="avg-validation-time"]')).toContainText('2.5m')

    // Check recent validation runs
    await expect(page.locator('[data-testid="recent-runs"]')).toBeVisible()
    
    const recentRun = page.locator('[data-testid="recent-run-0"]')
    await expect(recentRun).toBeVisible()
    await expect(recentRun.locator('[data-testid="run-status"]')).toContainText('Completed')
  })

  test('Provider Detail Page Flow', async ({ page }) => {
    await loginAsReviewer(page)

    // Navigate to providers page
    await page.click('[data-testid="nav-providers"]')

    // Click on a provider to view details
    await page.click('[data-testid="provider-PROV_E2E_001"]')
    await expect(page).toHaveURL('/providers/PROV_E2E_001')

    // Verify provider details are displayed
    await expect(page.locator('[data-testid="provider-name"]')).toContainText('John Smith')
    await expect(page.locator('[data-testid="provider-npi"]')).toContainText('1234567890')

    // Check field confidence displays
    await expect(page.locator('[data-testid="field-confidence-npi"]')).toBeVisible()
    await expect(page.locator('[data-testid="field-confidence-address"]')).toBeVisible()
    await expect(page.locator('[data-testid="field-confidence-license"]')).toBeVisible()

    // Check validation timeline
    await expect(page.locator('[data-testid="validation-timeline"]')).toBeVisible()
    
    const timelineItem = page.locator('[data-testid="timeline-item-0"]')
    await expect(timelineItem).toBeVisible()
    await expect(timelineItem.locator('[data-testid="timeline-action"]')).toContainText('Validated')

    // Test actions
    await page.click('[data-testid="accept-action"]')
    await expect(page.locator('[data-testid="success-message"]')).toContainText('Provider accepted')
  })

  test('Bulk Actions Flow', async ({ page }) => {
    await loginAsAdmin(page)

    // Navigate to providers page
    await page.click('[data-testid="nav-providers"]')

    // Select multiple providers
    await page.check('[data-testid="provider-checkbox-PROV_E2E_001"]')
    await page.check('[data-testid="provider-checkbox-PROV_E2E_002"]')

    // Verify bulk actions toolbar appears
    await expect(page.locator('[data-testid="bulk-actions-toolbar"]')).toBeVisible()
    await expect(page.locator('[data-testid="selected-count"]')).toContainText('2 of 200')

    // Test bulk accept
    await page.click('[data-testid="bulk-accept-button"]')

    // Verify confirmation modal
    await expect(page.locator('[data-testid="confirmation-modal"]')).toBeVisible()
    await expect(page.locator('[data-testid="confirmation-message"]')).toContainText('accept all selected providers')

    // Confirm action
    await page.click('[data-testid="confirm-button"]')

    // Verify success message
    await expect(page.locator('[data-testid="success-message"]')).toContainText('2 providers accepted')

    // Verify selection cleared
    await expect(page.locator('[data-testid="bulk-actions-toolbar"]')).not.toBeVisible()
  })

  test('Search and Filter Flow', async ({ page }) => {
    await loginAsReviewer(page)

    // Navigate to providers page
    await page.click('[data-testid="nav-providers"]')

    // Test search functionality
    await page.fill('[data-testid="search-input"]', 'John Smith')
    await page.press('[data-testid="search-input"]', 'Enter')

    // Verify search results
    await expect(page.locator('[data-testid="search-results"]')).toContainText('1 result')

    // Test confidence filter
    await page.click('[data-testid="filters-button"]')
    await page.fill('[data-testid="confidence-min"]', '0.8')
    await page.fill('[data-testid="confidence-max"]', '1.0')

    // Apply filters
    await page.click('[data-testid="apply-filters-button"]')

    // Verify filtered results
    await expect(page.locator('[data-testid="filtered-results"]')).toContainText('Filtered results')

    // Test status filter
    await page.selectOption('[data-testid="status-filter"]', 'warning')

    // Verify status filter applied
    const providerRows = page.locator('[data-testid="provider-row"]')
    await expect(providerRows).toHaveCount(1)
    await expect(providerRows.locator('[data-testid="status-badge"]')).toContainText('Warning')

    // Clear filters
    await page.click('[data-testid="clear-filters-button"]')

    // Verify filters cleared
    await expect(page.locator('[data-testid="search-input"]')).toHaveValue('')
  })

  test('Error Handling and Loading States', async ({ page }) => {
    await loginAsReviewer(page)

    // Test network error handling
    await page.route('**/api/providers', route => route.abort())

    // Navigate to providers page
    await page.click('[data-testid="nav-providers"]')

    // Verify error message is displayed
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Failed to load providers')

    // Test retry functionality
    await page.click('[data-testid="retry-button"]')

    // Restore network
    await page.unroute('**/api/providers')

    // Verify providers load after retry
    await expect(page.locator('[data-testid="provider-table"]')).toBeVisible()

    // Test loading states
    await page.route('**/api/validate/batch', route => {
      // Simulate slow response
      setTimeout(() => route.continue(), 2000)
    })

    await page.click('[data-testid="start-validation-button"]')

    // Verify loading indicator
    await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible()
    await expect(page.locator('[data-testid="validation-status"]')).toContainText('Processing')
  })

  test('Accessibility and Keyboard Navigation', async ({ page }) => {
    await loginAsReviewer(page)

    // Test keyboard navigation
    await page.press('body', 'Tab')
    await expect(page.locator(':focus')).toHaveAttribute('data-testid', 'nav-dashboard')

    await page.press(':focus', 'Tab')
    await expect(page.locator(':focus')).toHaveAttribute('data-testid', 'nav-providers')

    await page.press(':focus', 'Enter')
    await expect(page).toHaveURL('/providers')

    // Test ARIA labels
    await expect(page.locator('[data-testid="search-input"]')).toHaveAttribute('aria-label', 'Search providers')
    await expect(page.locator('[data-testid="select-all-checkbox"]')).toHaveAttribute('aria-label', 'Select all providers')

    // Test screen reader support
    const confidenceBadge = page.locator('[data-testid="confidence-badge"]').first()
    await expect(confidenceBadge).toHaveAttribute('aria-label', /Confidence score/)

    // Test focus management in modals
    await page.click('[data-testid="review-button"]')
    await expect(page.locator('[data-testid="review-modal"]')).toBeVisible()

    // Verify focus is trapped in modal
    await page.press(':focus', 'Tab')
    await expect(page.locator(':focus')).toBeVisible()

    // Test escape key closes modal
    await page.press('body', 'Escape')
    await expect(page.locator('[data-testid="review-modal"]')).not.toBeVisible()
  })
})

test.describe('Mobile Responsiveness', () => {
  test('Mobile Layout and Touch Interactions', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    await loginAsReviewer(page)

    // Verify mobile navigation
    await expect(page.locator('[data-testid="mobile-menu-button"]')).toBeVisible()
    await page.click('[data-testid="mobile-menu-button"]')
    await expect(page.locator('[data-testid="mobile-nav-menu"]')).toBeVisible()

    // Navigate to providers
    await page.click('[data-testid="mobile-nav-providers"]')

    // Verify mobile table layout
    await expect(page.locator('[data-testid="mobile-provider-card"]')).toBeVisible()

    // Test touch interactions
    await page.tap('[data-testid="provider-card-0"]')
    await expect(page.locator('[data-testid="provider-detail-modal"]')).toBeVisible()

    // Test swipe gestures (if implemented)
    await page.touchscreen.tap(200, 300)
    await page.touchscreen.tap(100, 300) // Swipe left
  })
})
