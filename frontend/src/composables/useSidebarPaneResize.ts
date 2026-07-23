import { computed, onBeforeUnmount, ref } from 'vue'

const STORAGE_KEY = 'researchsensei.workbench.sidebarWidth'
const DEFAULT_WIDTH = 292
const MIN_WIDTH = 240
const MAX_WIDTH = 420

interface ResizeState {
  pointerId: number
  startX: number
  startWidth: number
  target: HTMLElement
}

export function useSidebarPaneResize() {
  const width = ref(loadWidth())
  let resizeState: ResizeState | null = null

  const shellStyle = computed<Record<string, string>>(() => ({
    '--sidebar-pane-width': `${width.value}px`,
  }))

  function startResize(event: PointerEvent) {
    if (event.button !== 0) return
    const target = event.currentTarget as HTMLElement | null
    if (!target) return
    event.preventDefault()
    resizeState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startWidth: width.value,
      target,
    }
    target.setPointerCapture?.(event.pointerId)
    target.addEventListener('lostpointercapture', stopResize)
    window.addEventListener('pointermove', moveResize)
    window.addEventListener('pointerup', stopResize)
    window.addEventListener('pointercancel', stopResize)
    window.addEventListener('blur', stopResize)
  }

  function moveResize(event: PointerEvent) {
    if (!resizeState || event.pointerId !== resizeState.pointerId) return
    width.value = clampWidth(resizeState.startWidth + event.clientX - resizeState.startX)
  }

  function stopResize() {
    if (!resizeState) return
    const state = resizeState
    resizeState = null
    state.target.removeEventListener('lostpointercapture', stopResize)
    if (state.target.hasPointerCapture?.(state.pointerId)) state.target.releasePointerCapture(state.pointerId)
    window.removeEventListener('pointermove', moveResize)
    window.removeEventListener('pointerup', stopResize)
    window.removeEventListener('pointercancel', stopResize)
    window.removeEventListener('blur', stopResize)
    saveWidth()
  }

  function handleSeparatorKeydown(event: KeyboardEvent) {
    if (!['ArrowLeft', 'ArrowRight', 'Home'].includes(event.key)) return
    event.preventDefault()
    if (event.key === 'Home') width.value = DEFAULT_WIDTH
    if (event.key === 'ArrowLeft') width.value = clampWidth(width.value - (event.shiftKey ? 40 : 20))
    if (event.key === 'ArrowRight') width.value = clampWidth(width.value + (event.shiftKey ? 40 : 20))
    saveWidth()
  }

  function resetWidth() {
    width.value = DEFAULT_WIDTH
    saveWidth()
  }

  function saveWidth() {
    if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, String(Math.round(width.value)))
  }

  onBeforeUnmount(stopResize)

  return {
    width,
    shellStyle,
    startResize,
    stopResize,
    handleSeparatorKeydown,
    resetWidth,
  }
}

function loadWidth() {
  if (typeof localStorage === 'undefined') return DEFAULT_WIDTH
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === null || !raw.trim()) return DEFAULT_WIDTH
  const saved = Number(raw)
  return Number.isFinite(saved) ? clampWidth(saved) : DEFAULT_WIDTH
}

function clampWidth(value: number) {
  return Math.min(Math.max(value, MIN_WIDTH), MAX_WIDTH)
}
