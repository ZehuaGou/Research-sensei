import { defineComponent, nextTick, onMounted, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useFormulaDock } from './useFormulaDock'
import type { WorkspaceTab } from '../types/workspace'

const Harness = defineComponent({
  template: '<aside ref="dockElement" :style="style"></aside>',
  setup() {
    const activeTab = ref<WorkspaceTab>('formulas')
    const open = ref(false)
    const canShowCards = ref(true)
    const chatPaneWidth = ref(380)
    const dockElement = ref<HTMLElement | null>(null)
    const dock = useFormulaDock({ activeTab, isPaperTutorPanelOpen: open, canShowCards, chatPaneWidth })
    onMounted(() => {
      if (dockElement.value) {
        vi.spyOn(dockElement.value, 'getBoundingClientRect').mockReturnValue({
          x: 0,
          y: 0,
          top: 0,
          right: 300,
          bottom: 400,
          left: 0,
          width: 300,
          height: 400,
          toJSON: () => ({}),
        })
      }
      dock.registerDock(dockElement.value)
    })
    return { activeTab, open, canShowCards, chatPaneWidth, dockElement, ...dock }
  },
})

describe('useFormulaDock', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('migrates legacy coordinates and clamps them inside the viewport', async () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 800 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 600 })
    localStorage.setItem('researchsensei.learningWorkspace.formulaDock', JSON.stringify({ x: 5_000, y: -200, collapsed: false }))

    const wrapper = mount(Harness)
    await nextTick()
    await nextTick()

    expect(wrapper.vm.position.x).toBeGreaterThanOrEqual(12)
    expect(wrapper.vm.position.x).toBeLessThanOrEqual(488)
    expect(wrapper.vm.position.y).toBeGreaterThanOrEqual(78)
    expect(wrapper.vm.position.y).toBeLessThanOrEqual(188)
    const saved = JSON.parse(localStorage.getItem('researchsensei.learningWorkspace.formulaDock') || '{}')
    expect(saved).toMatchObject({ version: 2, collapsed: false })
    expect(saved.position.x).toBeLessThanOrEqual(488)
  })

  it('reserves desktop 论文助教 space and supports keyboard reset', async () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1_400 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 700 })
    const wrapper = mount(Harness)
    await nextTick()

    wrapper.vm.open = true
    await nextTick()
    expect(wrapper.vm.position.x).toBeLessThanOrEqual(894)

    wrapper.vm.handleKeyboardMove(new KeyboardEvent('keydown', { key: 'ArrowLeft' }))
    const movedX = wrapper.vm.position.x
    wrapper.vm.handleKeyboardMove(new KeyboardEvent('keydown', { key: 'Home' }))
    await nextTick()
    expect(wrapper.vm.position.x).toBeGreaterThanOrEqual(movedX)
    expect(wrapper.vm.position.x).toBeLessThanOrEqual(894)
  })

  it('ends dragging on pointer cancellation so capture loss cannot leave a stuck dock', async () => {
    const wrapper = mount(Harness)
    await nextTick()
    const target = wrapper.get('aside').element as HTMLElement
    const preventDefault = vi.fn()
    wrapper.vm.startDrag({
      button: 0,
      pointerId: 7,
      clientX: 100,
      clientY: 100,
      target,
      currentTarget: target,
      preventDefault,
    } as unknown as PointerEvent)

    expect(wrapper.vm.dragging).toBe(true)
    expect(preventDefault).toHaveBeenCalled()
    window.dispatchEvent(new Event('pointercancel'))
    expect(wrapper.vm.dragging).toBe(false)
  })

  it('clamps to the panned visual viewport after browser zoom', async () => {
    const listeners = new Map<string, EventListener>()
    vi.stubGlobal('visualViewport', {
      width: 620,
      height: 500,
      offsetLeft: 140,
      offsetTop: 90,
      addEventListener: vi.fn((name: string, listener: EventListener) => listeners.set(name, listener)),
      removeEventListener: vi.fn((name: string) => listeners.delete(name)),
    })
    localStorage.setItem('researchsensei.learningWorkspace.formulaDock', JSON.stringify({ x: 0, y: 0, collapsed: false }))

    const wrapper = mount(Harness)
    await nextTick()
    await nextTick()

    expect(wrapper.vm.position.x).toBeGreaterThanOrEqual(152)
    expect(wrapper.vm.position.x).toBeLessThanOrEqual(448)
    expect(wrapper.vm.position.y).toBeGreaterThanOrEqual(102)
    expect(wrapper.vm.position.y).toBeLessThanOrEqual(178)

    const viewport = window.visualViewport as VisualViewport
    Object.defineProperties(viewport, {
      offsetLeft: { configurable: true, value: 220 },
      offsetTop: { configurable: true, value: 120 },
    })
    listeners.get('scroll')?.(new Event('scroll'))
    expect(wrapper.vm.position.x).toBeGreaterThanOrEqual(232)
    expect(wrapper.vm.position.y).toBeGreaterThanOrEqual(132)
  })
})
