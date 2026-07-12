import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import type { WorkspaceTab } from '../types/workspace'

interface FormulaDockOptions {
  activeTab: Ref<WorkspaceTab>
  isAskPanelOpen: Ref<boolean>
  canShowCards: Readonly<Ref<boolean>>
  chatPaneWidth: Ref<number>
}

interface DockPosition {
  x: number
  y: number
}

interface DockPrefsV2 {
  version: 2
  position: DockPosition
  collapsed: boolean
}

interface DragState {
  pointerId: number
  startX: number
  startY: number
  originX: number
  originY: number
  target: HTMLElement
}

const STORAGE_KEY = 'researchsensei.learningWorkspace.formulaDock'
const VIEWPORT_MARGIN = 12
const DEFAULT_TOP = 78

export function useFormulaDock(options: FormulaDockOptions) {
  const dockRef = ref<HTMLElement | null>(null)
  const position = ref<DockPosition>({ x: 24, y: DEFAULT_TOP })
  const customized = ref(false)
  const collapsed = ref(false)
  const dragging = ref(false)
  let dragState: DragState | null = null

  const style = computed<Record<string, string>>(() => ({
    left: `${position.value.x}px`,
    top: `${position.value.y}px`,
  }))

  const isCompactViewport = ref(viewportBounds().width <= 1120)
  const hiddenForCompactChat = computed(() => isCompactViewport.value && options.isAskPanelOpen.value)

  function loadPreferences() {
    if (typeof localStorage === 'undefined') return
    try {
      const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') as Partial<DockPrefsV2> & Partial<DockPosition> & { collapsed?: unknown }
      const saved = raw.version === 2 && raw.position ? raw.position : { x: raw.x, y: raw.y }
      if (isFinitePosition(saved)) {
        position.value = saved
        customized.value = true
      }
      if (typeof raw.collapsed === 'boolean') {
        collapsed.value = raw.collapsed
        customized.value = true
      }
      if (customized.value) savePreferences()
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  function savePreferences() {
    if (typeof localStorage === 'undefined') return
    const payload: DockPrefsV2 = {
      version: 2,
      position: { x: Math.round(position.value.x), y: Math.round(position.value.y) },
      collapsed: collapsed.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  function dockSize() {
    const rect = dockRef.value?.getBoundingClientRect()
    return {
      width: rect?.width || (collapsed.value ? 96 : 300),
      height: rect?.height || 44,
    }
  }

  function reservedRight() {
    return !isCompactViewport.value && options.isAskPanelOpen.value && options.canShowCards.value
      ? options.chatPaneWidth.value + 18
      : 0
  }

  function clampToViewport(candidate = position.value): DockPosition {
    const viewport = viewportBounds()
    const size = dockSize()
    const minX = viewport.left + VIEWPORT_MARGIN
    const preferredTop = Math.max(DEFAULT_TOP, viewport.top + VIEWPORT_MARGIN)
    const minY = Math.min(preferredTop, Math.max(viewport.top + VIEWPORT_MARGIN, viewport.top + viewport.height - size.height - VIEWPORT_MARGIN))
    const maxX = Math.max(minX, viewport.left + viewport.width - reservedRight() - size.width - VIEWPORT_MARGIN)
    const maxY = Math.max(minY, viewport.top + viewport.height - size.height - VIEWPORT_MARGIN)
    return {
      x: clamp(candidate.x, minX, maxX),
      y: clamp(candidate.y, minY, maxY),
    }
  }

  function defaultPosition(): DockPosition {
    const viewport = viewportBounds()
    const size = dockSize()
    return clampToViewport({
      x: viewport.left + viewport.width - reservedRight() - size.width - 18,
      y: Math.max(DEFAULT_TOP, viewport.top + VIEWPORT_MARGIN),
    })
  }

  async function clampPosition() {
    await nextTick()
    position.value = clampToViewport()
  }

  function registerDock(element: HTMLElement | null) {
    dockRef.value = element
    if (!element) return
    void nextTick(async () => {
      await clampPosition()
      savePreferences()
    })
  }

  async function resetPosition() {
    customized.value = false
    await nextTick()
    position.value = defaultPosition()
    savePreferences()
  }

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
    customized.value = true
    void nextTick(async () => {
      await clampPosition()
      savePreferences()
    })
  }

  function startDrag(event: PointerEvent) {
    if (event.button !== 0) return
    const origin = event.target as HTMLElement | null
    if (origin?.closest('button, a, input, textarea, select')) return
    const target = event.currentTarget as HTMLElement | null
    if (!target) return
    event.preventDefault()
    customized.value = true
    dragging.value = true
    dragState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: position.value.x,
      originY: position.value.y,
      target,
    }
    target.setPointerCapture?.(event.pointerId)
    target.addEventListener('lostpointercapture', stopDrag)
    window.addEventListener('pointermove', moveDrag)
    window.addEventListener('pointerup', stopDrag)
    window.addEventListener('pointercancel', stopDrag)
    window.addEventListener('blur', stopDrag)
  }

  function moveDrag(event: PointerEvent) {
    if (!dragState || event.pointerId !== dragState.pointerId) return
    position.value = clampToViewport({
      x: dragState.originX + event.clientX - dragState.startX,
      y: dragState.originY + event.clientY - dragState.startY,
    })
  }

  function stopDrag() {
    if (!dragState) return
    const state = dragState
    dragState = null
    dragging.value = false
    state.target.removeEventListener('lostpointercapture', stopDrag)
    if (state.target.hasPointerCapture?.(state.pointerId)) state.target.releasePointerCapture(state.pointerId)
    window.removeEventListener('pointermove', moveDrag)
    window.removeEventListener('pointerup', stopDrag)
    window.removeEventListener('pointercancel', stopDrag)
    window.removeEventListener('blur', stopDrag)
    position.value = clampToViewport(position.value)
    savePreferences()
  }

  function handleKeyboardMove(event: KeyboardEvent) {
    const delta = event.shiftKey ? 30 : 10
    const movement: Record<string, DockPosition> = {
      ArrowLeft: { x: -delta, y: 0 },
      ArrowRight: { x: delta, y: 0 },
      ArrowUp: { x: 0, y: -delta },
      ArrowDown: { x: 0, y: delta },
    }
    if (event.key === 'Home') {
      event.preventDefault()
      void resetPosition()
      return
    }
    const move = movement[event.key]
    if (!move) return
    event.preventDefault()
    customized.value = true
    position.value = clampToViewport({ x: position.value.x + move.x, y: position.value.y + move.y })
    savePreferences()
  }

  function handleViewportChange() {
    isCompactViewport.value = viewportBounds().width <= 1120
    position.value = customized.value ? clampToViewport(position.value) : defaultPosition()
    savePreferences()
  }

  function syncDefaultCollapse() {
    if (customized.value) {
      handleViewportChange()
      return
    }
    collapsed.value = options.activeTab.value === 'formulas' && options.isAskPanelOpen.value
    position.value = defaultPosition()
  }

  onMounted(() => {
    loadPreferences()
    void nextTick(() => {
      position.value = customized.value ? clampToViewport(position.value) : defaultPosition()
      savePreferences()
    })
    window.addEventListener('resize', handleViewportChange)
    window.visualViewport?.addEventListener('resize', handleViewportChange)
    window.visualViewport?.addEventListener('scroll', handleViewportChange)
  })

  watch([options.activeTab, options.isAskPanelOpen, options.canShowCards], syncDefaultCollapse, { flush: 'post' })
  watch(collapsed, () => void clampPosition(), { flush: 'post' })

  onBeforeUnmount(() => {
    stopDrag()
    window.removeEventListener('resize', handleViewportChange)
    window.visualViewport?.removeEventListener('resize', handleViewportChange)
    window.visualViewport?.removeEventListener('scroll', handleViewportChange)
  })

  return {
    dockRef,
    registerDock,
    position,
    collapsed,
    dragging,
    style,
    isCompactViewport,
    hiddenForCompactChat,
    startDrag,
    stopDrag,
    toggleCollapsed,
    resetPosition,
    clampPosition,
    handleKeyboardMove,
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function viewportBounds() {
  if (typeof window === 'undefined') return { left: 0, top: 0, width: 1280, height: 800 }
  const viewport = window.visualViewport
  return {
    left: viewport?.offsetLeft || 0,
    top: viewport?.offsetTop || 0,
    width: viewport?.width || window.innerWidth,
    height: viewport?.height || window.innerHeight,
  }
}

function isFinitePosition(value: Partial<DockPosition>): value is DockPosition {
  return typeof value.x === 'number' && Number.isFinite(value.x) && typeof value.y === 'number' && Number.isFinite(value.y)
}
