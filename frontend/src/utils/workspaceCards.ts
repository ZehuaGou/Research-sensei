import type {
  FormulaCard,
  FormulaEntry,
  PaperCard,
  PaperWorkspaceStatus,
} from '../types/workspace'

export function normalizePaperCard(card: PaperCard, workspaceStatus: PaperWorkspaceStatus): PaperCard {
  return {
    ...card,
    thirty_second: card.one_sentence_summary || card.thirty_second || '',
    five_minute: [card.problem?.text, card.core_idea?.text, card.method_overview?.text].filter(Boolean).join(' '),
    deep_dive: card.experiment_summary?.text || '',
    evidence_status: card.evidence_status || String(workspaceStatus.evidence_status || 'UNKNOWN'),
  }
}

export function normalizePaperSkeleton(card: PaperCard) {
  return {
    problem: { plain: card?.problem?.text || '' },
    mechanism: { plain: card?.method_overview?.text || '' },
  }
}

export function isUsableFormulaCard(card: FormulaCard) {
  const origin = String(card.formula_origin || '').trim()
  const derivation = String(card.derivation_status || '').trim()
  const coverage = String(card.coverage_status || '').trim()
  if (derivation === 'llm_failed' || coverage === 'LLM_FAILED') return false
  if (origin === 'raw_formula_text' && (derivation === 'blocked' || coverage === 'BLOCKED_RAW_ONLY')) return false
  return !(isNoisyFormulaText(card.purpose) && isNoisyFormulaText(card.plain_summary) && origin !== 'source_latex')
}

export function normalizeFormulaCard(card: FormulaCard, index = 0): FormulaCard {
  const displayTitle = formulaDisplayTitle(card, index)
  const purpose = safeFormulaCopy(card.purpose)
  const problem = safeFormulaCopy(card.problem)
  const plainSummary = safeFormulaCopy(card.plain_summary)
  const intuition = safeFormulaCopy(card.intuition)
  return {
    ...card,
    display_title: displayTitle,
    formula_latex: card.formula_latex || card.formula_raw || '',
    purpose: purpose || displayTitle,
    problem: problem || displayTitle,
    formula_ref: card.formula_ref || card.location || card.formula_id || '',
    remove_effect: card.remove_effect || card.what_if_removed || '',
    weight_change_effect: card.weight_change_effect || card.weight_sensitivity || '',
    plain_summary: plainSummary || intuition || '',
    intuition: intuition || '',
  }
}

export function formulaAnchor(formula: FormulaCard, index: number) {
  const raw = String(formula.formula_id || formula.formula_ref || formula.evidence_ref || index + 1)
  const safe = raw.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '')
  return `formula-${index + 1}-${safe || 'item'}`
}

export function formulaEntries(cards: FormulaCard[]): FormulaEntry[] {
  const ordered = [...cards].sort(compareFormulaLocation)
  return ordered.map((formula, index) => {
    const equationIndex = Number.parseInt(String(formula.equation_number || ''), 10)
    const displayIndex = Number.isFinite(equationIndex) ? equationIndex : index + 1
    const card = normalizeFormulaCard(formula, displayIndex - 1)
    return {
      id: formulaAnchor(formula, index),
      index: displayIndex,
      card,
      title: clipLabel(card.display_title || card.purpose || card.problem || `公式 ${index + 1}`, 72),
    }
  })
}

function compareFormulaLocation(left: FormulaCard, right: FormulaCard) {
  const leftPage = Number(left.formula_page || Number.MAX_SAFE_INTEGER)
  const rightPage = Number(right.formula_page || Number.MAX_SAFE_INTEGER)
  if (leftPage !== rightPage) return leftPage - rightPage
  const leftEquation = Number.parseFloat(String(left.equation_number || Number.MAX_SAFE_INTEGER))
  const rightEquation = Number.parseFloat(String(right.equation_number || Number.MAX_SAFE_INTEGER))
  if (leftEquation !== rightEquation) return leftEquation - rightEquation
  return Number(left.group_order || 0) - Number(right.group_order || 0)
}

export function clipLabel(value: unknown, maxLength: number) {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  return text.length > maxLength ? `${text.slice(0, maxLength).trim()}...` : text
}

export function isNoisyFormulaText(value: unknown) {
  const text = String(value || '').trim()
  return !text
    || /^INSUFFICIENT_EVIDENCE\b/i.test(text)
    || /^UNKNOWN$/i.test(text)
    || /Formula evidence preserved from literature discovery context/i.test(text)
    || /paper analysis preserved this formula slot/i.test(text)
    || /blocked detailed derivation/i.test(text)
    || /raw\/unknown formula text/i.test(text)
    || /\\begin\{(?:cases|aligned|matrix|bmatrix|pmatrix|equation|align)/.test(text)
    || /\\(?:frac|overline|underline|label|text|tau|sum|prod|int)\b/.test(text)
}

function formulaDisplayTitle(card: FormulaCard, index: number) {
  const candidates = [card.purpose, card.problem, card.plain_summary, card.formula_ref]
    .map(value => String(value || '').replace(/\s+/g, ' ').trim())
  return candidates.find(value => value && !isNoisyFormulaText(value)) || fallbackFormulaTitle(card, index)
}

function safeFormulaCopy(value: unknown) {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  return text && !isNoisyFormulaText(text) ? text : ''
}

function fallbackFormulaTitle(card: FormulaCard, index: number) {
  const raw = String(card.formula_latex || card.formula_raw || '').replace(/\s+/g, ' ').trim()
  if (/\\begin\{cases\}/.test(raw) || /otherwise/i.test(raw)) return `公式 ${index + 1}：分段判定规则`
  if (/\\frac/.test(raw) || /\\overline/.test(raw)) return `公式 ${index + 1}：比例与阈值关系`
  if (/\\sum|\\prod|\\int/.test(raw)) return `公式 ${index + 1}：聚合计算关系`
  return `公式 ${index + 1}：公式卡片`
}
