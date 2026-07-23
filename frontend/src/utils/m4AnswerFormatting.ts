export type AnswerTone = 'lead' | 'concept' | 'evidence' | 'caution' | 'followup' | 'plain'
export type AnswerKind = 'heading' | 'paragraph' | 'list'

export type AnswerBlock = {
  text: string
  tone: AnswerTone
  label: string
  kind: AnswerKind
  items: string[]
}

const toneLabels: Record<AnswerTone, string> = {
  lead: '回答',
  concept: '',
  evidence: '依据',
  caution: '注意',
  followup: '继续',
  plain: '',
}

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

type ParsedBlock = {
  text: string
  kind: AnswerKind
  items: string[]
}

function splitAnswerText(content: string): ParsedBlock[] {
  const parts = content
    .replace(/\r\n/g, '\n')
    .replace(/^\s{0,3}[-*_]{3,}\s*$/gm, '')
    .replace(/^\s{0,3}#{1,6}\s+(.+)$/gm, '\n\n§heading§$1\n\n')
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
    .map((part): ParsedBlock => {
      if (part.startsWith('§heading§')) {
        return { text: part.slice('§heading§'.length).trim(), kind: 'heading', items: [] }
      }
      if (part.startsWith('• ')) {
        return { text: '', kind: 'list', items: [part.slice(2).trim()] }
      }
      return { text: part, kind: 'paragraph', items: [] }
    })

  return parts.reduce<ParsedBlock[]>((blocks, part) => {
    const previous = blocks.at(-1)
    if (part.kind === 'list' && previous?.kind === 'list') {
      previous.items.push(...part.items)
      return blocks
    }
    blocks.push(part)
    return blocks
  }, [])
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
  let paragraphIndex = 0
  return splitAnswerText(content).map((block) => {
    if (block.kind === 'heading') {
      return { ...block, tone: 'plain', label: '' }
    }
    if (block.kind === 'list') {
      return { ...block, tone: 'plain', label: '' }
    }
    const tone = answerTone(block.text, paragraphIndex++)
    return { ...block, tone, label: toneLabels[tone] }
  })
}

export function contextSizeLabel(chars = 0) {
  if (chars >= 10000) return `${(chars / 10000).toFixed(chars >= 100000 ? 0 : 1)} 万字全文`
  if (chars > 0) return `${chars} 字全文`
  return '整篇论文'
}
