import { defineComponent, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useWorkspaceTabs } from './useWorkspaceTabs'

function harness(jobId: string) {
  return defineComponent({
    template: '<div ref="reader"></div>',
    setup() {
      const reader = ref<HTMLElement | null>(null)
      return { reader, ...useWorkspaceTabs(jobId, reader) }
    },
  })
}

describe('workspace tab scroll memory', () => {
  afterEach(() => {
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })

  it('restores route-return scroll from session storage after rendering', async () => {
    sessionStorage.setItem('researchsensei.learningWorkspace.scroll.job-route', JSON.stringify({ paper: 77, formulas: 12, teaching: 0 }))
    const wrapper = mount(harness('job-route'))
    await wrapper.vm.restoreCurrentScroll()
    expect((wrapper.vm.reader as HTMLElement).scrollTop).toBe(77)
  })

  it('uses a render token so rapid tab switches cannot apply stale scroll', async () => {
    const frames: FrameRequestCallback[] = []
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      frames.push(callback)
      return frames.length
    })
    const wrapper = mount(harness('job-rapid'))
    const pane = wrapper.vm.reader as HTMLElement
    pane.scrollTop = 120

    const first = wrapper.vm.switchTab('formulas')
    const second = wrapper.vm.switchTab('teaching')
    await nextTick()
    frames.splice(0).forEach(callback => callback(performance.now()))
    await Promise.all([first, second])

    expect(wrapper.vm.activeTab).toBe('teaching')
    expect(pane.scrollTop).toBe(0)
    expect(wrapper.vm.scrollPositions.paper).toBe(120)
    expect(wrapper.vm.scrollPositions.formulas).toBe(0)
  })

  it('restores the last stable tab after rapid switching without leaking scroll', async () => {
    const frames: FrameRequestCallback[] = []
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      frames.push(callback)
      return frames.length
    })
    sessionStorage.setItem('researchsensei.learningWorkspace.scroll.job-stable', JSON.stringify({ paper: 90, formulas: 35, teaching: 12 }))
    const wrapper = mount(harness('job-stable'))
    const pane = wrapper.vm.reader as HTMLElement
    pane.scrollTop = 90

    const first = wrapper.vm.switchTab('formulas')
    const second = wrapper.vm.switchTab('teaching')
    await nextTick()
    frames.splice(0).forEach(callback => callback(performance.now()))
    await Promise.all([first, second])
    expect(pane.scrollTop).toBe(12)

    const back = wrapper.vm.switchTab('formulas')
    await nextTick()
    frames.splice(0).forEach(callback => callback(performance.now()))
    await back
    expect(pane.scrollTop).toBe(35)
  })
})
