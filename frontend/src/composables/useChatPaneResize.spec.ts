import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useChatPaneResize } from './useChatPaneResize'

const Harness = defineComponent({
  template: '<div><button ref="separator" /></div>',
  setup() {
    return useChatPaneResize()
  },
})

describe('useChatPaneResize', () => {
  afterEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
    Object.defineProperty(window, 'visualViewport', { configurable: true, value: undefined })
  })

  it('uses the visual viewport for compact mode after browser zoom', async () => {
    Object.defineProperty(window, 'visualViewport', { configurable: true, value: {
      width: 880,
      height: 600,
      offsetLeft: 0,
      offsetTop: 0,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } })
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1400 })

    const wrapper = mount(Harness)
    await nextTick()
    expect(wrapper.vm.compactViewport).toBe(true)
  })

  it('supports bounded keyboard resizing and reset', async () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1400 })
    Object.defineProperty(window, 'visualViewport', { configurable: true, value: undefined })
    const wrapper = mount(Harness)
    await nextTick()

    wrapper.vm.handleSeparatorKeydown(new KeyboardEvent('keydown', { key: 'ArrowLeft', shiftKey: true }))
    expect(wrapper.vm.width).toBe(600)
    wrapper.vm.handleSeparatorKeydown(new KeyboardEvent('keydown', { key: 'Home' }))
    expect(wrapper.vm.width).toBe(560)
    expect(localStorage.getItem('researchsensei.learningWorkspace.chatWidth.v2')).toBe('560')
  })

  it('resizes in the correct direction when M4 is placed on the left', async () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1600 })
    const wrapper = mount(Harness)
    await nextTick()

    wrapper.vm.handleSeparatorKeydown(new KeyboardEvent('keydown', { key: 'ArrowRight' }), 'left')
    expect(wrapper.vm.width).toBe(580)
    wrapper.vm.handleSeparatorKeydown(new KeyboardEvent('keydown', { key: 'End' }), 'left')
    expect(wrapper.vm.width).toBe(1140)
  })

  it('uses the full available width for the wide-pane shortcut', async () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1600 })
    const wrapper = mount(Harness)
    await nextTick()

    wrapper.vm.toggleWide()
    expect(wrapper.vm.width).toBe(1140)
    wrapper.vm.toggleWide()
    expect(wrapper.vm.width).toBe(560)
  })

  it('ends pointer resizing on cancellation', async () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1400 })
    const wrapper = mount(Harness)
    await nextTick()
    const target = wrapper.get('button').element as HTMLElement
    wrapper.vm.startResize({
      button: 0,
      pointerId: 3,
      clientX: 500,
      currentTarget: target,
      preventDefault: vi.fn(),
    } as unknown as PointerEvent)
    window.dispatchEvent(new Event('pointercancel'))
    expect(localStorage.getItem('researchsensei.learningWorkspace.chatWidth.v2')).toBe('560')
  })
})
