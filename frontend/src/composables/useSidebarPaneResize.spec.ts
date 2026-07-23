import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { useSidebarPaneResize } from './useSidebarPaneResize'

const Harness = defineComponent({
  template: '<div><button ref="separator" /></div>',
  setup() {
    return useSidebarPaneResize()
  },
})

describe('useSidebarPaneResize', () => {
  afterEach(() => localStorage.clear())

  it('supports bounded keyboard resizing and reset', () => {
    const wrapper = mount(Harness)

    expect(wrapper.vm.width).toBe(292)
    wrapper.vm.handleSeparatorKeydown(new KeyboardEvent('keydown', { key: 'ArrowRight', shiftKey: true }))
    expect(wrapper.vm.width).toBe(332)
    wrapper.vm.handleSeparatorKeydown(new KeyboardEvent('keydown', { key: 'Home' }))
    expect(wrapper.vm.width).toBe(292)
    expect(localStorage.getItem('researchsensei.workbench.sidebarWidth')).toBe('292')
  })

  it('restores and clamps a saved width', () => {
    localStorage.setItem('researchsensei.workbench.sidebarWidth', '900')
    const wrapper = mount(Harness)
    expect(wrapper.vm.width).toBe(420)
  })
})
