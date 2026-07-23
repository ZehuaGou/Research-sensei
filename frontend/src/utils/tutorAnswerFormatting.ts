export function compactInlineText(value: string) {
  return value
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:，。；：、）\]\}])/g, '$1')
    .replace(/([（\[\{])\s+/g, '$1')
    .trim()
}

export function clipText(value: string, maxLength: number) {
  const compact = compactInlineText(value)
  return compact.length > maxLength ? `${compact.slice(0, maxLength)}...` : compact
}

export function normalizeMessageText(value: string) {
  return value
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function normalizeTutorMarkdown(value: string) {
  const normalized = normalizeMessageText(value)
    .replace(/\\n(?=(?:\\n|#{1,6}\s|[-*>]\s|\|))/g, '\n')
  if (!looksLikeCollapsedMarkdown(normalized)) return normalizeCjkStrongMarkers(normalized)

  let repaired = normalized
    .replace(/\s+(?=#{1,6}\s+)/g, '\n\n')
    .replace(/([：:])\s+(?=\|[^|\n]+\|)/g, '$1\n\n')
    .replace(/\|\s+\|/g, '|\n|')
    .replace(/\s+>\s+/g, '\n\n> ')
    .replace(/\s+-\s+(?=(?:\*\*|[A-Za-z0-9\u4e00-\u9fff]))/g, '\n- ')

  let fenceOpen = false
  repaired = repaired.replace(/\s*```([A-Za-z0-9_-]+)?\s*/g, (_match, language: string | undefined) => {
    if (!fenceOpen) {
      fenceOpen = true
      return `\n\n\`\`\`${language || ''}\n`
    }
    fenceOpen = false
    return '\n```\n\n'
  })

  const lines = repaired.split('\n').flatMap(splitCollapsedHeading)
  return normalizeCjkStrongMarkers(
    normalizeMessageText(splitTrailingTableText(lines).join('\n')),
  )
}

function looksLikeCollapsedMarkdown(value: string) {
  const inlineHeadings = value.match(/\s#{1,6}\s+/g)?.length ?? 0
  const collapsedTableRows = value.match(/\|\s+\|/g)?.length ?? 0
  const hasVeryLongMarkdownLine = value.split('\n').some(line => line.length > 240)
  const hasFewLineBreaks = (value.match(/\n/g)?.length ?? 0) < 2
  return (hasVeryLongMarkdownLine || hasFewLineBreaks)
    && (inlineHeadings > 0 || collapsedTableRows > 0)
}

function splitCollapsedHeading(line: string) {
  const match = line.match(/^(#{1,6})\s+(.+)$/)
  if (!match) return [line]
  const [, marker, content] = match
  const tokens = content.trim().split(/\s+/)
  if (tokens.length < 2) return [line]

  let titleTokenCount = 1
  if (/^\d+[.)、]$/.test(tokens[0])) {
    titleTokenCount = Math.min(2, tokens.length)
  } else if (!/[\u4e00-\u9fff]/.test(tokens[0])) {
    const firstChineseToken = tokens.findIndex(token => /[\u4e00-\u9fff]/.test(token))
    titleTokenCount = firstChineseToken >= 0 ? firstChineseToken + 1 : Math.min(5, tokens.length)
  }
  if (titleTokenCount >= tokens.length) return [line]
  return [
    `${marker} ${tokens.slice(0, titleTokenCount).join(' ')}`,
    '',
    tokens.slice(titleTokenCount).join(' '),
  ]
}

function splitTrailingTableText(lines: string[]) {
  return lines.flatMap((line) => {
    if (!line.trimStart().startsWith('|')) return [line]
    const lastPipe = line.lastIndexOf('|')
    if (lastPipe < 1 || !line.slice(lastPipe + 1).trim()) return [line]
    return [line.slice(0, lastPipe + 1), '', line.slice(lastPipe + 1).trim()]
  })
}

function normalizeCjkStrongMarkers(value: string) {
  return value.replace(
    /\*\*(?=\S)([^*\n]*?\S)\*\*/g,
    (marker: string, _content: string, offset: number, source: string) => {
      const before = source[offset - 1] || ''
      const after = source[offset + marker.length] || ''
      const leftSpace = /[\u4e00-\u9fff]/.test(before) ? ' ' : ''
      const rightSpace = /[\u4e00-\u9fff]/.test(after) ? ' ' : ''
      return `${leftSpace}${marker}${rightSpace}`
    },
  )
}

export function contextSizeLabel(chars = 0) {
  if (chars >= 10000) return `${(chars / 10000).toFixed(chars >= 100000 ? 0 : 1)} 万字全文`
  if (chars > 0) return `${chars} 字全文`
  return '整篇论文'
}
