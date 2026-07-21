import { describe, expect, it } from 'vitest'
import { formulaEntries, isUsableFormulaCard } from './workspaceCards'

describe('workspace formula cards', () => {
  it('hides explicit LLM failure cards from the usable formula reader', () => {
    expect(isUsableFormulaCard({
      formula_id: 'f4',
      formula_origin: 'mineru_latex',
      coverage_status: 'LLM_FAILED',
      derivation_status: 'llm_failed',
    })).toBe(false)
  })

  it('orders cards by page and equation number', () => {
    const entries = formulaEntries([
      { formula_id: 'f5', formula_page: 4, equation_number: '5', purpose: 'Fifth' },
      { formula_id: 'f1', formula_page: 4, equation_number: '1', purpose: 'First' },
      { formula_id: 'f6', formula_page: 5, equation_number: '6', purpose: 'Sixth' },
    ])

    expect(entries.map(entry => entry.card.formula_id)).toEqual(['f1', 'f5', 'f6'])
    expect(entries.map(entry => entry.index)).toEqual([1, 5, 6])
  })
})
