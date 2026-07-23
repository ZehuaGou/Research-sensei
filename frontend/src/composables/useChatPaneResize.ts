import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const STORAGE_KEY = 'researchsensei.learningWorkspace.chatWidth.v2'
const DEFAULT_WIDTH = 560
const MIN_WIDTH = 360
const MAX_WIDTH = 1280
const MIN_VISIBLE_WORKSPACE_RESERVE = 460

type PaneSide = 'left' | 'right'

interface ResizeState {
  pointerId: number
  startX: number
  startWidth: number
  target: HTMLElement
}

export function useChatPaneResize() {
  const width = ref(DEFAULT_WIDTH)
  const compactViewport = ref(false)
  let resizeState: ResizeState | null = null
  let resizeSide: PaneSide = 'right'

  const shellStyle = computed<Record<string, string>>(() => ({ '--chat-pane-width': `${width.value}px` }))
  const maxWidth = computed(() => maximumAllowedWidth())

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
    if (!compactViewport.value) width.value = clampWidth(width.value)
  }

  function startResize(event: PointerEvent, side: PaneSide = 'right') {
    if (event.button !== 0 || compactViewport.value) return
    const target = event.currentTarget as HTMLElement | null
    if (!target) return
    event.preventDefault()
    resizeState = { pointerId: event.pointerId, startX: event.clientX, startWidth: width.value, target }
    resizeSide = side
    target.setPointerCapture?.(event.pointerId)
    target.addEventListener('lostpointercapture', stopResize)
    window.addEventListener('pointermove', moveResize)
    window.addEventListener('pointerup', stopResize)
    window.addEventListener('pointercancel', stopResize)
    window.addEventListener('blur', stopResize)
  }

  function moveResize(event: PointerEvent) {
    if (!resizeState || event.pointerId !== resizeState.pointerId) return
    const delta = event.clientX - resizeState.startX
    width.value = clampWidth(resizeState.startWidth + (resizeSide === 'left' ? delta : -delta))
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

  function handleSeparatorKeydown(event: KeyboardEvent, side: PaneSide = 'right') {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    if (event.key === 'Home') width.value = DEFAULT_WIDTH
    if (event.key === 'End') width.value = maximumAllowedWidth()
    const movement = event.shiftKey ? 40 : 20
    if (event.key === 'ArrowLeft') width.value = clampWidth(width.value + (side === 'right' ? movement : -movement))
    if (event.key === 'ArrowRight') width.value = clampWidth(width.value + (side === 'left' ? movement : -movement))
    saveWidth()
  }

  function toggleWide() {
    const widest = maximumAllowedWidth()
    width.value = width.value >= widest - 40 ? clampWidth(DEFAULT_WIDTH) : widest
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

  return {
    width,
    maxWidth,
    compactViewport,
    shellStyle,
    startResize,
    stopResize,
    handleSeparatorKeydown,
    toggleWide,
  }
}

function clampWidth(value: number) {
  return Math.min(Math.max(value, MIN_WIDTH), maximumAllowedWidth())
}

function maximumAllowedWidth() {
  const viewportMax = Math.max(MIN_WIDTH, viewportWidth() - MIN_VISIBLE_WORKSPACE_RESERVE)
  return Math.min(MAX_WIDTH, viewportMax)
}

function viewportWidth() {
  return typeof window === 'undefined' ? 1280 : window.visualViewport?.width || window.innerWidth
}
