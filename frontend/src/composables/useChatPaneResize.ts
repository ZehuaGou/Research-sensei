import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const STORAGE_KEY = 'researchsensei.learningWorkspace.chatWidth'
const MIN_WIDTH = 320
const MAX_WIDTH = 540

interface ResizeState {
  pointerId: number
  startX: number
  startWidth: number
  target: HTMLElement
}

export function useChatPaneResize() {
  const width = ref(380)
  const compactViewport = ref(false)
  let resizeState: ResizeState | null = null

  const shellStyle = computed<Record<string, string>>(() => ({ '--chat-pane-width': `${width.value}px` }))

  function loadWidth() {
    if (typeof localStorage === 'undefined') return
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === null || !raw.trim()) return
    const saved = Number(raw)
    if (Number.isFinite(saved)) width.value = clampWidth(saved)
  }

  function saveWidth() {
    if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, String(Math.round(width.value)))
  }

  function updateViewportMode() {
    compactViewport.value = viewportWidth() <= 1120
    width.value = clampWidth(width.value)
  }

  function startResize(event: PointerEvent) {
    if (event.button !== 0 || compactViewport.value) return
    const target = event.currentTarget as HTMLElement | null
    if (!target) return
    event.preventDefault()
    resizeState = { pointerId: event.pointerId, startX: event.clientX, startWidth: width.value, target }
    target.setPointerCapture?.(event.pointerId)
    target.addEventListener('lostpointercapture', stopResize)
    window.addEventListener('pointermove', moveResize)
    window.addEventListener('pointerup', stopResize)
    window.addEventListener('pointercancel', stopResize)
    window.addEventListener('blur', stopResize)
  }

  function moveResize(event: PointerEvent) {
    if (!resizeState || event.pointerId !== resizeState.pointerId) return
    width.value = clampWidth(resizeState.startWidth + resizeState.startX - event.clientX)
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
    if (event.key === 'Home') width.value = 380
    if (event.key === 'ArrowLeft') width.value = clampWidth(width.value + (event.shiftKey ? 40 : 20))
    if (event.key === 'ArrowRight') width.value = clampWidth(width.value - (event.shiftKey ? 40 : 20))
    saveWidth()
  }

  onMounted(() => {
    loadWidth()
    updateViewportMode()
    window.addEventListener('resize', updateViewportMode)
    window.visualViewport?.addEventListener('resize', updateViewportMode)
  })

  onBeforeUnmount(() => {
    stopResize()
    window.removeEventListener('resize', updateViewportMode)
    window.visualViewport?.removeEventListener('resize', updateViewportMode)
  })

  return { width, compactViewport, shellStyle, startResize, stopResize, handleSeparatorKeydown }
}

function clampWidth(value: number) {
  const viewportMax = Math.max(MIN_WIDTH, viewportWidth() - 420)
  return Math.min(Math.max(value, MIN_WIDTH), Math.min(MAX_WIDTH, viewportMax))
}

function viewportWidth() {
  return typeof window === 'undefined' ? 1280 : window.visualViewport?.width || window.innerWidth
}
