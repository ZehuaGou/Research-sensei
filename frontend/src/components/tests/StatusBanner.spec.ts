import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusBanner from '../StatusBanner.vue'

describe('StatusBanner', () => {
  it('shows baseline message for BASELINE_ONLY', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'BASELINE_ONLY' },
    })

    expect(wrapper.text()).toContain('基线模式')
    expect(wrapper.text()).toContain('不是最终导师级理解')
  })

  it('shows blocking_reason for BLOCKED_UNDERSTANDING', () => {
    const wrapper = mount(StatusBanner, {
      props: {
        status: 'BLOCKED_UNDERSTANDING',
        blockingReason: 'MISSING_METHOD_EVIDENCE',
      },
    })

    expect(wrapper.text()).toContain('理解被阻断')
    expect(wrapper.text()).toContain('MISSING_METHOD_EVIDENCE')
  })

  it('shows warnings for BLOCKED_UNDERSTANDING', () => {
    const wrapper = mount(StatusBanner, {
      props: {
        status: 'BLOCKED_UNDERSTANDING',
        warnings: [
          { code: 'W1', message: 'warning text' },
          { code: 'W2', message: 'another warning' },
        ],
      },
    })

    expect(wrapper.text()).toContain('warning text')
    expect(wrapper.text()).toContain('another warning')
  })

  it('shows degraded message for DEGRADED_STRUCTURAL', () => {
    const wrapper = mount(StatusBanner, {
      props: {
        status: 'DEGRADED_STRUCTURAL',
        missingComponents: ['teaching_cards'],
      },
    })

    expect(wrapper.text()).toContain('部分讲解不可用')
    expect(wrapper.text()).toContain('teaching_cards')
  })

  it('shows system error for FAILED', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'FAILED' },
    })

    expect(wrapper.text()).toContain('系统错误')
  })

  it('renders nothing for SUCCESS', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'SUCCESS' },
    })

    expect(wrapper.text()).toBe('')
  })

  it('renders nothing for unknown status', () => {
    const wrapper = mount(StatusBanner, {
      props: { status: 'UNKNOWN' },
    })

    expect(wrapper.text()).toBe('')
  })
})
