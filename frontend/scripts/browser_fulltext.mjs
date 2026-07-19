import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'
import { existsSync } from 'node:fs'
import { mkdir, readFile, unlink, writeFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { dirname, join, resolve } from 'node:path'
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

async function tryContextPdfRequest(context, url, targetPath, timeoutMs) {
  try {
    const response = await context.request.get(url, {
      failOnStatusCode: false,
      timeout: timeoutMs,
    })
    if (!response.ok()) return null
    const body = await response.body()
    if (!body || !body.subarray(0, 4).equals(PDF_MAGIC)) return null
    await mkdir(dirname(targetPath), { recursive: true })
    await writeFile(targetPath, body)
    return {
      success: true,
      finalUrl: response.url(),
      contentType: response.headers()['content-type'] || 'application/pdf',
    }
  } catch {
    return null
  }
}

function uniqueHttpUrls(values) {
  return [...new Set(values.map(value => String(value || '').trim()).filter(value => /^https?:\/\//i.test(value)))]
}

function installedChromePath() {
  const candidates = process.platform === 'win32'
    ? [
        join(process.env.PROGRAMFILES || '', 'Google', 'Chrome', 'Application', 'chrome.exe'),
        join(process.env['PROGRAMFILES(X86)'] || '', 'Google', 'Chrome', 'Application', 'chrome.exe'),
        join(process.env.LOCALAPPDATA || '', 'Google', 'Chrome', 'Application', 'chrome.exe'),
      ]
    : process.platform === 'darwin'
      ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
      : ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium']
  const executable = candidates.find(candidate => candidate && existsSync(candidate))
  if (!executable) throw new Error('没有找到已安装的 Google Chrome。')
  return executable
}

function dedicatedProfilePath(statePath) {
  return resolve(dirname(resolve(statePath)), 'browser-profile')
}

async function availablePort() {
  const server = createServer()
  await new Promise((resolveListen, rejectListen) => {
    server.once('error', rejectListen)
    server.listen(0, '127.0.0.1', resolveListen)
  })
  const address = server.address()
  const port = typeof address === 'object' && address ? address.port : 0
  await new Promise(resolveClose => server.close(resolveClose))
  if (!port) throw new Error('无法为专用 Chrome 分配本地调试端口。')
  return port
}

async function startDedicatedChrome({ statePath, startUrl, headless }) {
  const profilePath = dedicatedProfilePath(statePath)
  await mkdir(profilePath, { recursive: true })
  const port = await availablePort()
  const args = [
    `--remote-debugging-port=${port}`,
    '--remote-debugging-address=127.0.0.1',
    '--remote-allow-origins=*',
    `--user-data-dir=${profilePath}`,
    '--no-first-run',
    '--no-default-browser-check',
  ]
  if (headless) args.push('--headless=new')
  args.push(startUrl || 'about:blank')
  let launchError = null
  const child = spawn(installedChromePath(), args, {
    stdio: 'ignore',
    windowsHide: Boolean(headless),
  })
  child.once('error', error => { launchError = error })
  const endpoint = `http://127.0.0.1:${port}`
  const deadline = Date.now() + 20000
  while (Date.now() < deadline) {
    if (launchError) throw launchError
    try {
      const response = await fetch(`${endpoint}/json/version`)
      if (response.ok) return { child, endpoint, profilePath }
    } catch {}
    await new Promise(resolveDelay => setTimeout(resolveDelay, 250))
  }
  child.kill()
  throw new Error('专用 Chrome 启动超时。请确认没有安全软件阻止本地调试端口。')
}

async function closeDedicatedChrome(browser, child) {
  if (browser) await browser.close().catch(() => {})
  if (!child) return
  await waitForChildExit(child, 2000)
  if (child.exitCode === null && !child.killed) child.kill()
  await waitForChildExit(child, 2000)
}

async function waitForChildExit(child, timeoutMs) {
  if (!child || child.exitCode !== null) return
  await new Promise(resolveExit => {
    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      child.removeListener('exit', finish)
      resolveExit()
    }
    const timer = setTimeout(finish, timeoutMs)
    child.once('exit', finish)
  })
}

async function tryPdfNavigation(page, context, url, targetPath, timeoutMs) {
  try {
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: timeoutMs })
    const navigated = await savePdfResponse(response, targetPath)
    if (navigated) return navigated
  } catch {
    // Chrome's built-in PDF viewer may abort the page navigation even though
    // the authenticated browser context can retrieve the PDF bytes.
  }
  return await tryContextPdfRequest(context, url, targetPath, timeoutMs)
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
  if (!existsSync(dedicatedProfilePath(statePath))) {
    throw new Error('专用 Chrome 配置不存在，请先重新运行 capture-session。')
  }
  const session = await startDedicatedChrome({
    statePath,
    startUrl: 'about:blank',
    headless: request.headless === true,
  })
  let browser = null
  try {
    browser = await chromium.connectOverCDP(session.endpoint)
    const context = browser.contexts()[0]
    if (!context) throw new Error('专用 Chrome 没有可用的浏览上下文。')
    const page = context.pages()[0] || await context.newPage()
    const timeoutMs = Math.max(Number(request.timeoutMs) || 90000, 1000)

    for (const url of uniqueHttpUrls(request.pdfUrls || [])) {
      const result = await tryPdfNavigation(page, context, url, targetPath, timeoutMs)
      if (result) return result
    }

    if (request.landingUrl) {
      try {
        await page.goto(request.landingUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs })
      } catch {
        // Some challenge and publisher pages continue navigating after the
        // initial document response. Continue with bounded best-effort probes.
      }
      await page.waitForTimeout(1500).catch(() => {})
      // Preserve candidate links before a real click can navigate away and
      // destroy the landing page's JavaScript execution context.
      let extractedLinks = []
      try {
        extractedLinks = uniqueHttpUrls(await landingPdfLinks(page))
      } catch {}
      let clicked = null
      try {
        clicked = await tryLandingPdfClicks(page, targetPath, timeoutMs)
      } catch {}
      if (clicked) return clicked
      for (const url of extractedLinks) {
        const result = await tryPdfNavigation(page, context, url, targetPath, timeoutMs)
        if (result) return result
      }
    }
    return {
      success: false,
      errorCode: 'BROWSER_PDF_NOT_FOUND',
      error: 'The authorized browser session did not expose a validated PDF response.',
    }
  } finally {
    await closeDedicatedChrome(browser, session.child)
  }
}

async function captureSession(statePath, startUrl) {
  const resolvedState = resolve(statePath)
  const session = await startDedicatedChrome({
    statePath: resolvedState,
    startUrl,
    headless: false,
  })
  process.stderr.write(
    '这是不带 Playwright 启动标记的专用 Chrome。请完成安全验证并手动确认 PDF 可以下载，然后回到终端按 Enter。\n',
  )
  const readline = createInterface({ input: process.stdin, output: process.stderr })
  const stopCapture = () => {
    readline.close()
    if (!session.child.killed) session.child.kill()
    process.exit(130)
  }
  process.once('SIGINT', stopCapture)
  await new Promise(resolveLine => readline.question('', () => resolveLine()))
  process.removeListener('SIGINT', stopCapture)
  readline.close()
  let browser = null
  try {
    browser = await chromium.connectOverCDP(session.endpoint)
    const context = browser.contexts()[0]
    if (!context) throw new Error('专用 Chrome 没有可保存的浏览上下文。')
    await mkdir(dirname(resolvedState), { recursive: true })
    await context.storageState({ path: resolvedState })
    process.stdout.write(JSON.stringify({
      success: true,
      storageStatePath: resolvedState,
      profilePath: session.profilePath,
    }))
  } finally {
    await closeDedicatedChrome(browser, session.child)
  }
}

const [mode, ...args] = process.argv.slice(2)
try {
  if (mode === 'capture-session') {
    await captureSession(args[0] || 'workspace/browser-session.json', args[1] || 'https://dl.acm.org/')
  } else if (mode === 'download') {
    const chunks = []
    for await (const chunk of process.stdin) chunks.push(chunk)
    const request = JSON.parse(chunks.join(''))
    const result = await downloadWithSession(request)
    process.stdout.write(JSON.stringify({ ...result, browserMode: 'native_chrome_cdp' }))
  } else {
    throw new Error('Usage: browser_fulltext.mjs capture-session <state> <url> | download')
  }
} catch (error) {
  process.stdout.write(JSON.stringify({
    success: false,
    browserMode: 'native_chrome_cdp',
    errorCode: 'BROWSER_SESSION_FAILED',
    error: String(error?.message || error).slice(0, 500),
  }))
  process.exitCode = 1
}
