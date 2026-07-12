import type { Ref } from 'vue'
import { ref } from 'vue'
import type { WorkspaceTab } from '../types/workspace'

type ScrollPositions = Record<WorkspaceTab, number>

const emptyPositions = (): ScrollPositions => ({ paper: 0, formulas: 0, teaching: 0 })

export function useWorkspaceScrollMemory(jobId: string, readerPane: Ref<HTMLElement | null>) {
  const storageKey = `researchsensei.learningWorkspace.scroll.${jobId}`
  const positions = ref<ScrollPositions>(loadPositions())

  function loadPositions(): ScrollPositions {
    if (typeof sessionStorage === 'undefined') return emptyPositions()
    try {
      const value = JSON.parse(sessionStorage.getItem(storageKey) || '{}') as Partial<ScrollPositions>
      return {
        paper: validScroll(value.paper),
        formulas: validScroll(value.formulas),
        teaching: validScroll(value.teaching),
      }
    } catch {
      return emptyPositions()
    }
  }

  function save(tab: WorkspaceTab) {
    if (!readerPane.value) return
    positions.value[tab] = Math.max(0, readerPane.value.scrollTop)
    persist()
  }

  function restore(tab: WorkspaceTab) {
    if (!readerPane.value) return
    readerPane.value.scrollTop = positions.value[tab]
  }

  function persist() {
    if (typeof sessionStorage === 'undefined') return
    sessionStorage.setItem(storageKey, JSON.stringify(positions.value))
  }

  return { positions, save, restore, persist }
}

function validScroll(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : 0
}
