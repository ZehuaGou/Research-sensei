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

export function contextSizeLabel(chars = 0) {
  if (chars >= 10000) return `${(chars / 10000).toFixed(chars >= 100000 ? 0 : 1)} 万字全文`
  if (chars > 0) return `${chars} 字全文`
  return '整篇论文'
}
