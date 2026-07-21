import { describe, expect, it } from 'vitest'
import { formatTaskStage } from './taskStage'

describe('formatTaskStage', () => {
  it('renders deep-read stages in Chinese', () => {
    expect(formatTaskStage('indexing_evidence')).toBe('正在建立证据索引')
    expect(formatTaskStage('auditing_understanding')).toBe('正在核验卡片与证据')
  })

  it('renders formula batch progress', () => {
    expect(formatTaskStage('building_formula_cards:3/11')).toBe('正在生成公式卡片（3/11 批）')
    expect(formatTaskStage('building_formula_cards:0/0')).toBe('论文中没有可推导公式')
  })

  it('renders MinerU loading and formula-region progress', () => {
    expect(formatTaskStage('detecting_formula_regions')).toBe('正在定位 PDF 公式区域')
    expect(formatTaskStage('loading_formula_parser')).toBe('正在加载 GPU 公式解析器')
    expect(formatTaskStage('parsing_formula_regions:4/6')).toBe('正在识别公式区域（4/6 个）')
  })
})
