import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusBanner from '../StatusBanner.vue'

describe('StatusBanner', () => {
  it('shows baseline message for BASELINE_ONLY', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'BASELINE_ONLY' },
    })

    expect(wrapper.text()).toContain('Baseline only')
    expect(wrapper.text()).toContain('Diagnostic cards are hidden')
  })

  it('shows blocking_reason and warnings for BLOCKED_UNDERSTANDING', () => {
    const wrapper = mount(StatusBanner, {
      props: {
        status: 'BLOCKED_UNDERSTANDING',
        blockingReason: 'MISSING_METHOD_EVIDENCE',
        warnings: [{ code: 'W1', message: 'warning text' }],
      },
    })

    expect(wrapper.text()).toContain('Understanding blocked')
    expect(wrapper.text()).toContain('MISSING_METHOD_EVIDENCE')
    expect(wrapper.text()).toContain('W1: warning text')
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

    expect(wrapper.text()).toContain('Degraded understanding')
    expect(wrapper.text()).toContain('missing_components: teaching_cards')
    expect(wrapper.text()).toContain('CARD_BUILDER_FAILED: teaching cards failed')
    expect(wrapper.text()).toContain('canonicalization_status')
    expect(wrapper.text()).toContain('degradation_reason')
    expect(wrapper.text()).toContain('formula_origin')
    expect(wrapper.text()).toContain('formula_ocr_status')
    expect(wrapper.text()).toContain('evidence_status')
  })

  it('shows system error for FAILED', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'FAILED' },
    })

    expect(wrapper.text()).toContain('Pipeline failed')
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
          advisor_questions: true,
        },
      },
    })

    expect(wrapper.text()).toContain('Understanding ready')
    expect(wrapper.text()).toContain('source_type')
    expect(wrapper.text()).toContain('upload')
    expect(wrapper.text()).toContain('canonicalization_status')
    expect(wrapper.text()).toContain('m2_ready')
    expect(wrapper.text()).toContain('formula_origin')
    expect(wrapper.text()).toContain('mineru_latex')
    expect(wrapper.text()).toContain('formula_ocr_status')
    expect(wrapper.text()).toContain('evidence_status')
    expect(wrapper.text()).toContain('component_status.paper_card')
    expect(wrapper.text()).toContain('allowed_downstream.reading_display')
    expect(wrapper.text()).toContain('quality_status')
  })

  it('shows success state', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'SUCCESS' },
    })

    expect(wrapper.text()).toContain('Understanding ready')
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

    expect(wrapper.text()).toContain('Degraded understanding')
    expect(wrapper.text()).toContain('missing_components: formula_cards')
    expect(wrapper.text()).toContain('FORMULA_DERIVATION_BLOCKED')
    expect(wrapper.text()).toContain('degradation_reason')
    expect(wrapper.text()).toContain('formula_origin')
    expect(wrapper.text()).toContain('raw_formula_text')
    expect(wrapper.text()).toContain('formula_ocr_status')
    expect(wrapper.text()).toContain('not_available')
    expect(wrapper.text()).toContain('component_status.formula_cards')
    expect(wrapper.text()).toContain('FAILED')
    expect(wrapper.text()).toContain('allowed_downstream.advisor_questions')
    expect(wrapper.text()).toContain('false')
    expect(wrapper.text()).toContain('FORMULA_BLOCKED')
  })
})
