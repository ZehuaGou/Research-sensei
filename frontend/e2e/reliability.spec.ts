import { expect, test, type Locator, type Page } from '@playwright/test'
import { fixtureJobPath, mockDirectionTaskApi, mockWorkspaceApi } from './fixtures/workspace'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
})

test('loads a fixed paper and exposes status-gated cards and formula tabs', async ({ page }) => {
  await mockWorkspaceApi(page, 'success')
  await page.goto(fixtureJobPath.success)

  await expect(page.getByTestId('status-banner')).toContainText('理解完成')
  await expect(page.getByTestId('paper-card')).toContainText('Fixture: Reliable Multivariate Time-Series Anomaly Detection')
  await expect(page.getByTestId('reader-metrics')).toContainText('论文卡片')

  await page.getByRole('tab', { name: /公式拆解/ }).click()
  await expect(page.getByRole('tabpanel', { name: /公式拆解/ })).toBeVisible()
  await expect(page.getByTestId('formula-board-card')).toHaveCount(3)
  await expect(page.getByTestId('formula-dock')).toBeVisible()

  await page.getByRole('tab', { name: /教学卡片/ }).click()
  await expect(page.getByTestId('teaching-cards')).toContainText('Fixture teaching card 8')
})

test('uses persistent async direction jobs for search and deep-read handoff', async ({ page }) => {
  const taskState = await mockDirectionTaskApi(page)
  await page.goto('/directions/new')

  await page.getByTestId('direction-query').fill('offline reliability fixture')
  await page.getByRole('button', { name: '检索方向' }).click()
  await expect(page.getByTestId('direction-task-progress')).toContainText('后台任务')
  await expect(page.getByTestId('direction-status')).toContainText('检索完成')
  await expect(page.getByTestId('candidate-card')).toContainText('Synthetic Offline Reliability Paper')
  expect(taskState.searchCreates).toBe(1)
  expect(taskState.searchPolls).toBeGreaterThanOrEqual(2)
  expect(taskState.synchronousCalls).toBe(0)

  await page.getByTestId('deep-read-button').click()
  await expect(page.getByTestId('deep-read-progress')).toContainText('正在生成公式卡片（3/11 批）')
  await expect(page.getByTestId('deep-read-progress')).toContainText('61%')
  await expect(page).toHaveURL(/\/learn\/fixture-deep-read$/)
  await expect(page.getByTestId('status-banner')).toContainText('仅基础解析')
  expect(taskState.deepReadCreates).toBe(1)
  expect(taskState.deepReadPolls).toBeGreaterThanOrEqual(2)
  expect(taskState.synchronousCalls).toBe(0)
})

test('keeps direction navigation and composer reachable while results scroll', async ({ page }) => {
  await mockDirectionTaskApi(page)
  await page.setViewportSize({ width: 1440, height: 620 })
  await page.goto('/directions/new')

  await page.getByTestId('direction-query').fill('offline reliability fixture')
  await page.getByRole('button', { name: '检索方向' }).click()
  await expect(page.getByTestId('direction-status')).toContainText('检索完成')

  const scrollRegion = page.getByTestId('direction-scroll-region')
  const composer = page.locator('.codex-composer')
  const researchPanel = page.locator('.research-panel')
  await expect(scrollRegion).toBeVisible()
  await expect(composer).toBeVisible()
  await expect(researchPanel).toBeVisible()
  await expectInsideViewport(composer, page)
  await expectInsideViewport(researchPanel, page)

  await scrollRegion.evaluate(element => { element.scrollTop = element.scrollHeight })
  await expect.poll(() => scrollRegion.evaluate(element => element.scrollTop)).toBeGreaterThan(0)
  await expectInsideViewport(composer, page)
  await expectInsideViewport(researchPanel, page)

  const pageScroll = await page.evaluate(() => ({
    clientHeight: document.scrollingElement?.clientHeight || 0,
    scrollHeight: document.scrollingElement?.scrollHeight || 0,
  }))
  expect(pageScroll.scrollHeight).toBeLessThanOrEqual(pageScroll.clientHeight + 1)
})

test('clamps migrated and dragged formula dock positions inside the viewport', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('researchsensei.learningWorkspace.formulaDock', JSON.stringify({ x: 90_000, y: 90_000, collapsed: false }))
  })
  await mockWorkspaceApi(page, 'success')
  await page.setViewportSize({ width: 1280, height: 760 })
  await page.goto(fixtureJobPath.success)
  await page.getByRole('tab', { name: /公式拆解/ }).click()

  const dock = page.getByTestId('formula-dock')
  await expect(dock).toBeVisible()
  await expectInsideViewport(dock, page)

  const handle = page.getByTestId('formula-dock-handle')
  const handleBox = await handle.boundingBox()
  expect(handleBox).not.toBeNull()
  await page.mouse.move(handleBox!.x + 30, handleBox!.y + 20)
  await page.mouse.down()
  await page.mouse.move(1278, 758, { steps: 5 })
  await page.mouse.up()
  await expectInsideViewport(dock, page)

  await page.setViewportSize({ width: 900, height: 600 })
  await expectInsideViewport(dock, page)
  await handle.focus()
  await handle.press('Home')
  await handle.press('Shift+ArrowLeft')
  await expectInsideViewport(dock, page)

  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('researchsensei.learningWorkspace.formulaDock') || '{}'))
  expect(saved.version).toBe(2)
  expect(saved.position.x).toBeLessThan(900)
  expect(saved.position.y).toBeLessThan(600)
})

test('opens, resizes, and closes M4 without colliding with the formula dock', async ({ page }) => {
  await mockWorkspaceApi(page, 'success')
  await page.setViewportSize({ width: 1440, height: 800 })
  await page.goto(fixtureJobPath.success)

  await page.getByTestId('m4-open').first().click()
  const pane = page.getByTestId('m4-chat-pane')
  const separator = page.getByTestId('m4-resize-handle')
  await expect(pane).toBeVisible()
  const initialWidth = Number(await separator.getAttribute('aria-valuenow'))
  expect(initialWidth).toBeGreaterThanOrEqual(320)
  expect(initialWidth).toBeLessThanOrEqual(540)

  const separatorBox = await separator.boundingBox()
  expect(separatorBox).not.toBeNull()
  await page.mouse.move(separatorBox!.x + 2, separatorBox!.y + 30)
  await page.mouse.down()
  await page.mouse.move(separatorBox!.x - 80, separatorBox!.y + 30, { steps: 5 })
  await page.mouse.up()
  await expect.poll(async () => Number(await separator.getAttribute('aria-valuenow'))).toBeGreaterThan(initialWidth)

  await page.getByRole('tab', { name: /公式拆解/ }).click()
  const dock = page.getByTestId('formula-dock')
  await expect(dock).toBeVisible()
  const dockBox = await dock.boundingBox()
  const paneBox = await pane.boundingBox()
  expect(dockBox).not.toBeNull()
  expect(paneBox).not.toBeNull()
  expect(dockBox!.x + dockBox!.width).toBeLessThanOrEqual(paneBox!.x)

  await page.getByTestId('ask-panel-toggle').click()
  await expect(pane).toBeHidden()

  await page.setViewportSize({ width: 900, height: 700 })
  await page.getByTestId('m4-open').first().click()
  const compactPane = page.getByRole('dialog', { name: 'M4 论文助教' })
  await expect(compactPane).toBeVisible()
  await expect(page.getByTestId('formula-dock')).toBeHidden()
  await page.keyboard.press('Escape')
  await expect(compactPane).toBeHidden()
})

test('restores per-tab scroll after rapid switching and route return', async ({ page }) => {
  await mockWorkspaceApi(page, 'success')
  await page.setViewportSize({ width: 1100, height: 620 })
  await page.goto(fixtureJobPath.success)

  const reader = page.getByTestId('reader-pane')
  await reader.evaluate(element => { element.scrollTop = 240 })
  await page.getByRole('tab', { name: /公式拆解/ }).click()
  await reader.evaluate(element => { element.scrollTop = 180 })
  await page.getByRole('tab', { name: /教学卡片/ }).click()
  await page.getByRole('tab', { name: /论文概览/ }).click()
  await expect.poll(() => reader.evaluate(element => element.scrollTop)).toBeGreaterThan(150)

  await page.getByRole('link', { name: '本地论文库' }).click()
  await expect(page).toHaveURL(/\/papers\/library$/)
  await page.goBack()
  await expect(page.getByTestId('paper-card')).toBeVisible()
  await expect.poll(() => reader.evaluate(element => element.scrollTop)).toBeGreaterThan(150)
})

test('renders explicit degraded, blocked, and no-LLM states without leaking cards', async ({ page }) => {
  await mockWorkspaceApi(page, 'degraded')
  await page.goto(fixtureJobPath.degraded)
  await expect(page.getByTestId('status-banner')).toContainText('结构不完整')
  await page.getByRole('tab', { name: /公式拆解/ }).click()
  await expect(page.getByTestId('formula-degraded-message')).toContainText('公式拆解暂时不可用')
  await expect(page.getByTestId('formula-dock')).toHaveCount(0)

  await page.unroute('**/api/v1/**')
  await mockWorkspaceApi(page, 'blocked')
  await page.goto(fixtureJobPath.blocked)
  await expect(page.getByTestId('status-banner')).toContainText('理解被阻断')
  await expect(page.getByTestId('no-cards-state')).toBeVisible()
  await expect(page.getByTestId('paper-card')).toHaveCount(0)
  await expect(page.getByTestId('m4-open')).toHaveCount(0)

  await page.unroute('**/api/v1/**')
  await mockWorkspaceApi(page, 'no-llm')
  await page.goto(fixtureJobPath['no-llm'])
  await expect(page.getByTestId('status-banner')).toContainText('仅基础解析')
  await expect(page.getByTestId('no-cards-state')).toContainText('ccswitch')
  await expect(page.getByTestId('no-cards-state')).toContainText('没有接入实时大模型')
})

async function expectInsideViewport(locator: Locator, page: Page) {
  await expect.poll(async () => {
    const box = await locator.boundingBox()
    const viewport = page.viewportSize()
    if (!box || !viewport) return false
    return box.x >= 0
      && box.y >= 0
      && box.x + box.width <= viewport.width + 0.5
      && box.y + box.height <= viewport.height + 0.5
  }).toBe(true)
}
