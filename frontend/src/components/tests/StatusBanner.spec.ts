import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusBanner from '../StatusBanner.vue'

describe('StatusBanner', () => {
  it('shows baseline message for BASELINE_ONLY', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'BASELINE_ONLY' },
    })

    expect(wrapper.text()).toContain('仅基础解析')
    expect(wrapper.text()).toContain('后端没有启用实时大模型')
  })

  it('explains NO_LLM_CLIENT baseline runs are not upgradeable in place', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'BASELINE_ONLY', blockingReason: 'NO_LLM_CLIENT' },
    })

    expect(wrapper.text()).toContain('RESEARCHSENSEI_ENABLE_API_LLM=1')
    expect(wrapper.text()).toContain('重新跑论文')
  })

  it('shows blocking_reason and warnings for BLOCKED_UNDERSTANDING', () => {
    const wrapper = mount(StatusBanner, {
      props: {
        status: 'BLOCKED_UNDERSTANDING',
        blockingReason: 'MISSING_METHOD_EVIDENCE',
        warnings: [{ code: 'W1', message: 'warning text' }],
      },
    })

    expect(wrapper.text()).toContain('理解被阻断')
    expect(wrapper.text()).toContain('缺少方法证据')
    expect(wrapper.text()).toContain('W1：warning text')
  })

  it('shows degraded missing components', () => {
    const wrapper = mount(StatusBanner, {
      props: {
        status: 'DEGRADED_STRUCTURAL',
        blockingReason: 'TEACHING_CARDS_FAILED',
        warnings: [{ code: 'CARD_BUILDER_FAILED', message: 'teaching cards failed' }],
        missingComponents: ['teaching_cards'],
        paperWorkspaceStatus: {
          canonicalization_status: 'success',
          m2_ready: true,
          degradation_reason: 'TEACHING_CARDS_FAILED',
          formula_origin: 'mineru_latex',
          formula_ocr_status: 'not_required',
          evidence_status: 'SUCCESS',
        },
      },
    })

    expect(wrapper.text()).toContain('结构不完整')
    expect(wrapper.text()).toContain('缺少：教学卡片')
    expect(wrapper.text()).toContain('CARD_BUILDER_FAILED：teaching cards failed')
    expect(wrapper.text()).toContain('教学卡片失败')
    expect(wrapper.text()).toContain('MinerU LaTeX')
    expect(wrapper.text()).toContain('无需 OCR')
    expect(wrapper.text()).toContain('成功')
  })

  it('shows system error for FAILED', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'FAILED' },
    })

    expect(wrapper.text()).toContain('流水线失败')
  })

  it('shows PaperWorkspace status details', () => {
    const wrapper = mount(StatusBanner, {
      props: {
        status: 'SUCCESS',
        paperWorkspaceStatus: {
          source_type: 'upload',
          verification_status: 'verified',
          pdf_metadata_check: 'passed',
          pdf_title_match: 'match',
          can_enter_m2: true,
          source_confidence: 1,
          canonicalization_status: 'success',
          m2_ready: true,
          formula_origin: 'mineru_latex',
          formula_ocr_status: 'not_required',
          evidence_status: 'SUCCESS',
          quality_status: 'pass',
        },
        componentStatus: {
          paper_card: 'SUCCESS',
          formula_cards: 'SUCCESS',
          teaching_cards: 'SUCCESS',
        },
        allowedDownstream: {
          reading_display: true,
          advisor_questions: false,
        },
      },
    })

    expect(wrapper.text()).toContain('理解完成')
    expect(wrapper.text()).toContain('来源')
    expect(wrapper.text()).toContain('上传文件')
    expect(wrapper.text()).toContain('公式来源')
    expect(wrapper.text()).toContain('MinerU LaTeX')
    expect(wrapper.text()).toContain('公式 OCR')
    expect(wrapper.text()).toContain('证据')
    expect(wrapper.text()).toContain('质量')
  })

  it('shows success state', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'SUCCESS' },
    })

    expect(wrapper.text()).toContain('理解完成')
  })

  it('renders nothing for unknown status', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'UNKNOWN' },
    })

    expect(wrapper.text()).toBe('')
  })

  it('shows formula derivation degradation for raw input DEGRADED_STRUCTURAL', () => {
    const wrapper = mount(StatusBanner, {
      props: {
        status: 'DEGRADED_STRUCTURAL',
        blockingReason: 'FORMULA_DERIVATION_BLOCKED',
        warnings: [{ code: 'FORMULA_BLOCKED', message: '9 blocked formulas, formula_origins: raw_formula_text' }],
        missingComponents: ['formula_cards'],
        paperWorkspaceStatus: {
          source_type: 'm1_canonical_bundle',
          canonicalization_status: 'success',
          m2_ready: true,
          degradation_reason: 'FORMULA_DERIVATION_BLOCKED',
          formula_origin: 'raw_formula_text',
          formula_ocr_status: 'not_available',
          evidence_status: 'SUCCESS',
        },
        componentStatus: {
          paper_card: 'SUCCESS',
          formula_cards: 'FAILED',
          teaching_cards: 'SUCCESS',
        },
        allowedDownstream: {
          reading_display: true,
          advisor_questions: false,
        },
      },
    })

    expect(wrapper.text()).toContain('结构不完整')
    expect(wrapper.text()).toContain('缺少：公式卡片')
    expect(wrapper.text()).toContain('公式推导被阻断')
    expect(wrapper.text()).toContain('公式来源')
    expect(wrapper.text()).toContain('原始公式文本')
    expect(wrapper.text()).toContain('未提供')
    expect(wrapper.text()).toContain('FORMULA_BLOCKED')
  })
})
