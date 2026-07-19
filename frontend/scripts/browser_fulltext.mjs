import { createInterface } from 'node:readline'
import { mkdir, readFile, unlink, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { chromium } from '@playwright/test'

const PDF_MAGIC = Buffer.from('%PDF')

async function savePdfResponse(response, targetPath) {
  if (!response) return null
  const body = await response.body().catch(() => null)
  if (!body || !body.subarray(0, 4).equals(PDF_MAGIC)) return null
  await mkdir(dirname(targetPath), { recursive: true })
  await writeFile(targetPath, body)
  return {
    success: true,
    finalUrl: response.url(),
    contentType: response.headers()['content-type'] || 'application/pdf',
  }
}

function uniqueHttpUrls(values) {
  return [...new Set(values.map(value => String(value || '').trim()).filter(value => /^https?:\/\//i.test(value)))]
}

async function tryPdfNavigation(page, url, targetPath, timeoutMs) {
  try {
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: timeoutMs })
    return await savePdfResponse(response, targetPath)
  } catch {
    return null
  }
}

async function landingPdfLinks(page) {
  return page.evaluate(() => {
    const values = []
    for (const selector of [
      'meta[name="citation_pdf_url"]',
      'meta[name="wkhealth_pdf_url"]',
      'meta[property="og:pdf"]',
    ]) {
      const value = document.querySelector(selector)?.getAttribute('content')
      if (value) values.push(value)
    }
    for (const anchor of Array.from(document.querySelectorAll('a[href]')).slice(0, 500)) {
      const href = anchor.getAttribute('href') || ''
      const text = (anchor.textContent || '').toLowerCase()
      if (/\.pdf(?:$|[?#])|\/pdf(?:$|[/?#])|\/article\/download\//i.test(href) || /download pdf|view pdf|full text pdf/.test(text)) {
        values.push(href)
      }
    }
    return values.map(value => {
      try { return new URL(value, document.baseURI).href } catch { return '' }
    }).filter(Boolean).slice(0, 30)
  })
}

async function saveBrowserDownload(download, targetPath) {
  await mkdir(dirname(targetPath), { recursive: true })
  await download.saveAs(targetPath)
  const body = await readFile(targetPath).catch(() => null)
  if (!body || !body.subarray(0, 4).equals(PDF_MAGIC)) {
    await unlink(targetPath).catch(() => {})
    return null
  }
  return {
    success: true,
    finalUrl: download.url(),
    contentType: 'application/pdf',
  }
}

async function tryLandingPdfClicks(page, targetPath, timeoutMs) {
  await page.evaluate(() => {
    let tagged = 0
    for (const element of Array.from(document.querySelectorAll('a, button, [role="button"]')).slice(0, 500)) {
      const href = element.getAttribute('href') || ''
      const label = [
        element.textContent || '',
        element.getAttribute('aria-label') || '',
        element.getAttribute('title') || '',
      ].join(' ').toLowerCase()
      if (/\.pdf(?:$|[?#])|\/pdf(?:$|[/?#])|\/article\/download\//i.test(href)
        || /download\s*pdf|view\s*pdf|full\s*text\s*pdf|pdf\s*download/.test(label)) {
        element.setAttribute('data-researchsensei-pdf-click', String(tagged++))
      }
      if (tagged >= 4) break
    }
  })
  const candidates = page.locator('[data-researchsensei-pdf-click]')
  const count = Math.min(await candidates.count(), 4)
  const eventTimeout = Math.min(Math.max(Math.floor(timeoutMs / 6), 2500), 5000)
  for (let index = 0; index < count; index += 1) {
    const element = candidates.nth(index)
    const downloadPromise = page.waitForEvent('download', { timeout: eventTimeout }).catch(() => null)
    const responsePromise = page.waitForResponse(response => (
      String(response.headers()['content-type'] || '').toLowerCase().includes('pdf')
    ), { timeout: eventTimeout }).catch(() => null)
    try {
      await element.click({ timeout: eventTimeout })
    } catch {
      await Promise.all([downloadPromise, responsePromise])
      continue
    }
    const [download, response] = await Promise.all([downloadPromise, responsePromise])
    const downloaded = download ? await saveBrowserDownload(download, targetPath) : null
    if (downloaded) return downloaded
    const responded = response ? await savePdfResponse(response, targetPath) : null
    if (responded) return responded
  }
  return null
}

async function downloadWithSession(request) {
  const statePath = resolve(request.storageStatePath)
  const targetPath = resolve(request.targetPath)
  await readFile(statePath)
  const browser = await chromium.launch({ channel: 'chrome', headless: request.headless !== false })
  try {
    const context = await browser.newContext({ storageState: statePath, acceptDownloads: true })
    const page = await context.newPage()
    const timeoutMs = Math.max(Number(request.timeoutMs) || 90000, 1000)

    for (const url of uniqueHttpUrls(request.pdfUrls || [])) {
      const result = await tryPdfNavigation(page, url, targetPath, timeoutMs)
      if (result) return result
    }

    if (request.landingUrl) {
      await page.goto(request.landingUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs })
      await page.waitForTimeout(1500)
      const clicked = await tryLandingPdfClicks(page, targetPath, timeoutMs)
      if (clicked) return clicked
      for (const url of uniqueHttpUrls(await landingPdfLinks(page))) {
        const result = await tryPdfNavigation(page, url, targetPath, timeoutMs)
        if (result) return result
      }
    }
    return {
      success: false,
      errorCode: 'BROWSER_PDF_NOT_FOUND',
      error: 'The authorized browser session did not expose a validated PDF response.',
    }
  } finally {
    await browser.close()
  }
}

async function captureSession(statePath, startUrl) {
  const browser = await chromium.launch({ channel: 'chrome', headless: false })
  const context = await browser.newContext()
  const page = await context.newPage()
  await page.goto(startUrl, { waitUntil: 'domcontentloaded' })
  process.stderr.write('请在打开的 Chrome 中完成登录或安全验证，然后回到终端按 Enter。\n')
  const readline = createInterface({ input: process.stdin, output: process.stderr })
  await new Promise(resolveLine => readline.question('', () => resolveLine()))
  readline.close()
  const resolvedState = resolve(statePath)
  await mkdir(dirname(resolvedState), { recursive: true })
  await context.storageState({ path: resolvedState })
  await browser.close()
  process.stdout.write(JSON.stringify({ success: true, storageStatePath: resolvedState }))
}

const [mode, ...args] = process.argv.slice(2)
try {
  if (mode === 'capture-session') {
    await captureSession(args[0] || 'workspace/browser-session.json', args[1] || 'https://dl.acm.org/')
  } else if (mode === 'download') {
    const chunks = []
    for await (const chunk of process.stdin) chunks.push(chunk)
    const request = JSON.parse(chunks.join(''))
    process.stdout.write(JSON.stringify(await downloadWithSession(request)))
  } else {
    throw new Error('Usage: browser_fulltext.mjs capture-session <state> <url> | download')
  }
} catch (error) {
  process.stdout.write(JSON.stringify({
    success: false,
    errorCode: 'BROWSER_SESSION_FAILED',
    error: String(error?.message || error).slice(0, 500),
  }))
  process.exitCode = 1
}
