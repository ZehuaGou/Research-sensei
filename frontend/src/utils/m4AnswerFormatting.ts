export type AnswerTone = 'lead' | 'concept' | 'evidence' | 'caution' | 'followup' | 'plain'

export type AnswerBlock = {
  text: string
  tone: AnswerTone
  label: string
}

export type AnswerSegment = {
  text: string
  highlighted: boolean
}

const toneLabels: Record<AnswerTone, string> = {
  lead: '回答',
  concept: '',
  evidence: '依据',
  caution: '注意',
  followup: '继续',
  plain: '',
}

const highlightTerms = [
  '核心问题', '核心方法', '关键机制', '关键', '直觉', '机制', '证据', '依据',
  '结论', '限制', '公式', '变量', '实验', '消融', '结果', '注意力', 'attention',
  'embedding', 'loss', 'reward',
]

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
    .replace(/\n{3,}/g, '\n\n')
    .replace(/([A-Za-z])\n(?=[A-Za-z])/g, '$1 ')
    .trim()
}

function splitAnswerText(content: string) {
  return content
    .replace(/\r\n/g, '\n')
    .replace(/^\s{0,3}[-*_]{3,}\s*$/gm, '')
    .replace(/^\s{0,3}#{1,6}\s+(.+)$/gm, '\n\n$1\n\n')
    .replace(/^\s*\|?(?:\s*:?-+:?\s*\|)+\s*$/gm, '')
    .replace(/^\s*\|(.+)\|\s*$/gm, (_line, cells: string) => {
      const values = cells.split('|').map(value => value.trim()).filter(Boolean)
      return values.length ? `• ${values.join(' · ')}` : ''
    })
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^\s{0,3}[-*+]\s+/gm, '• ')
    .split(/\n\s*\n|\n(?=\s*(?:\d+[.、]|[-*•]\s|[（(]?\d+[）)]))/)
    .map(part => part.replace(/\s*\n\s*/g, ' ').trim())
    .filter(Boolean)
}

function answerTone(text: string, index: number): AnswerTone {
  const compact = text.replace(/\s+/g, '')
  if (/^(?:注意|提醒|限制|局限|不确定|证据不足|没有足够|没有给出|无法|不能硬编|暂时|缺少|不足以|失败)/.test(compact)) return 'caution'
  if (/组会追问|下一问|追问|你可以|继续问|可以继续|直接问|直接回我|试着回答|补一句/.test(compact)) return 'followup'
  if (index === 0) return 'lead'
  if (/能追到|证据是|依据是|正文|实验|结果|消融|评估|对比|支撑|显示|表明|观察到/.test(compact)) return 'evidence'
  if (/直觉|可以理解为|换句话说|意思是|机制|方法|公式|变量|模型|训练|推理|注意力|attention|embedding|向量|loss|reward|算法|理论|定理|证明/.test(compact)) return 'concept'
  if (/证据|依据/.test(compact)) return 'evidence'
  return 'plain'
}

export function answerBlocks(content: string): AnswerBlock[] {
  return splitAnswerText(content).map((text, index) => {
    const tone = answerTone(text, index)
    return { text, tone, label: toneLabels[tone] }
  })
}

export function highlightSegments(text: string): AnswerSegment[] {
  const segments: AnswerSegment[] = []
  const lowerText = text.toLowerCase()
  const terms = [...highlightTerms].sort((a, b) => b.length - a.length)
  let cursor = 0

  while (cursor < text.length) {
    let bestIndex = -1
    let bestTerm = ''
    for (const term of terms) {
      const index = lowerText.indexOf(term.toLowerCase(), cursor)
      if (index === -1) continue
      if (bestIndex === -1 || index < bestIndex || (index === bestIndex && term.length > bestTerm.length)) {
        bestIndex = index
        bestTerm = term
      }
    }
    if (bestIndex === -1) {
      segments.push({ text: text.slice(cursor), highlighted: false })
      break
    }
    if (bestIndex > cursor) segments.push({ text: text.slice(cursor, bestIndex), highlighted: false })
    segments.push({ text: text.slice(bestIndex, bestIndex + bestTerm.length), highlighted: true })
    cursor = bestIndex + bestTerm.length
  }

  return segments.length ? segments : [{ text, highlighted: false }]
}

export function contextSizeLabel(chars = 0) {
  if (chars >= 10000) return `${(chars / 10000).toFixed(chars >= 100000 ? 0 : 1)} 万字全文`
  if (chars > 0) return `${chars} 字全文`
  return '整篇论文'
}
