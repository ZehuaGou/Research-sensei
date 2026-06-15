import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SeedExpansionPanel from '../SeedExpansionPanel.vue'

describe('SeedExpansionPanel', () => {
  it('shows NOT_IMPLEMENTED without synthetic seeds', () => {
    const wrapper = mount(SeedExpansionPanel, {
      props: {
        status: 'NOT_IMPLEMENTED',
        warnings: [{ code: 'SEED_EXPANSION_NOT_IMPLEMENTED', message: 'No fake seeds.' }],
      },
    })

    expect(wrapper.text()).toContain('SeedExpansionPanel')
    expect(wrapper.text()).toContain('NOT_IMPLEMENTED')
    expect(wrapper.text()).toContain('SEED_EXPANSION_NOT_IMPLEMENTED')
    expect(wrapper.text()).toContain('No seed papers are synthesized or faked')
  })
})
