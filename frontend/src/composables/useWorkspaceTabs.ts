import { nextTick, ref, type Ref } from 'vue'
import type { WorkspaceTab } from '../types/workspace'
import { useWorkspaceScrollMemory } from './useWorkspaceScrollMemory'

export function useWorkspaceTabs(jobId: string, readerPane: Ref<HTMLElement | null>) {
  const activeTab = ref<WorkspaceTab>('paper')
  const scrollMemory = useWorkspaceScrollMemory(jobId, readerPane)
  let renderedTab: WorkspaceTab = activeTab.value
  let renderToken = 0

  async function switchTab(tab: WorkspaceTab) {
    if (tab === activeTab.value) return
    // A second switch can arrive before Vue has rendered/restored the first
    // target.  The pane still contains the last rendered tab in that window,
    // so saving it under activeTab would copy a stale scroll offset.
    scrollMemory.save(renderedTab)
    activeTab.value = tab
    const token = ++renderToken
    await nextTick()
    await renderedFrame()
    if (token !== renderToken) return
    scrollMemory.restore(tab)
    renderedTab = tab
  }

  function activate(tab: WorkspaceTab) {
    activeTab.value = tab
  }

  function saveCurrentScroll() {
    scrollMemory.save(renderedTab)
  }

  async function restoreCurrentScroll() {
    const token = ++renderToken
    await nextTick()
    await renderedFrame()
    if (token === renderToken) {
      scrollMemory.restore(activeTab.value)
      renderedTab = activeTab.value
    }
  }

  return {
    activeTab,
    scrollPositions: scrollMemory.positions,
    switchTab,
    activate,
    saveCurrentScroll,
    restoreCurrentScroll,
  }
}

function renderedFrame() {
  return new Promise<void>(resolve => {
    if (typeof requestAnimationFrame === 'undefined') {
      resolve()
      return
    }
    requestAnimationFrame(() => resolve())
  })
}
