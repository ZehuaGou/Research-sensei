import { expect, test } from '@playwright/test'

test('@live validates an explicitly configured live backend', async ({ request }) => {
  const enabled = process.env.RUN_LIVE_E2E === '1'
  const baseUrl = process.env.RESEARCHSENSEI_LIVE_BASE_URL?.replace(/\/$/, '')
  test.skip(!enabled || !baseUrl, 'Set RUN_LIVE_E2E=1 and RESEARCHSENSEI_LIVE_BASE_URL to opt in.')

  const response = await request.get(`${baseUrl}/api/v1/settings`)
  expect(response.ok()).toBe(true)
  const payload = await response.json()
  expect(payload).toEqual(expect.objectContaining({ active_provider: expect.any(String) }))
})
