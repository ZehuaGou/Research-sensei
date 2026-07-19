import { computed, onBeforeUnmount, ref } from 'vue'
import { ApiClientError, apiErrorMessage, researchApi, workspaceApi } from '../api/client'
import type {
  FormulaCard,
  PaperWorkspaceStatus,
  TeachingCard,
  UnderstandingStatus,
  WorkspaceCards,
} from '../types/workspace'
import type { ReparseResponse } from '../types/workspace'
import { isUsableFormulaCard } from '../utils/workspaceCards'

export function useWorkspaceData(jobId: string) {
  const understandingStatus = ref<UnderstandingStatus | null>(null)
  const paperWorkspaceStatus = ref<PaperWorkspaceStatus>({})
  const cards = ref<WorkspaceCards | null>(null)
  const degraded = ref(false)
  const missingComponents = ref<string[]>([])
  const isLoading = ref(true)
  const isReparsing = ref(false)
  const reparseProgress = ref(0)
  const reparseStage = ref('')
  const error = ref('')
  let loadController: AbortController | null = null
  let reparseController: AbortController | null = null
  const reparseTaskKey = `researchsensei.reparseTask.${jobId}`

  const status = computed(() => understandingStatus.value?.status || '')
  const canShowCards = computed(() => ['SUCCESS', 'DEGRADED_STRUCTURAL'].includes(status.value))
  const paperCard = computed(() => cards.value?.paper_card || null)
  const teachingCards = computed<TeachingCard[]>(() => cards.value?.teaching_cards?.teaching_cards || [])
  const allFormulaCards = computed<FormulaCard[]>(() => {
    const bundle = cards.value?.formula_cards
    if (!bundle) return []
    if (Array.isArray(bundle)) return bundle
    return bundle.formula_cards || []
  })
  const formulaCards = computed(() => allFormulaCards.value.filter(isUsableFormulaCard))
  const hiddenRawFormulaCount = computed(() => allFormulaCards.value.length - formulaCards.value.length)

  async function loadWorkspace() {
    loadController?.abort()
    const controller = new AbortController()
    loadController = controller
    isLoading.value = true
    error.value = ''
    cards.value = null
    degraded.value = false
    missingComponents.value = []
    try {
      const statusData = await workspaceApi.getUnderstandingStatus(jobId, controller.signal)
      if (controller.signal.aborted) return
      understandingStatus.value = statusData.understanding_status
      paperWorkspaceStatus.value = statusData.paper_workspace_status || {}
      if (!canShowCards.value) return

      try {
        const cardsData = await workspaceApi.getCards(jobId, controller.signal)
        if (controller.signal.aborted) return
        cards.value = cardsData.cards
        paperWorkspaceStatus.value = {
          ...paperWorkspaceStatus.value,
          ...(cardsData.paper_workspace_status || {}),
        }
        degraded.value = Boolean(cardsData.degraded)
        missingComponents.value = cardsData.missing_components || []
      } catch (cardsError) {
        if (cardsError instanceof ApiClientError && cardsError.code === 'FORBIDDEN') {
          understandingStatus.value = {
            ...understandingStatus.value,
            status: cardsError.detail?.status || understandingStatus.value.status,
            blocking_reason: cardsError.detail?.blocking_reason || understandingStatus.value.blocking_reason,
            warnings: cardsError.detail?.warnings || understandingStatus.value.warnings,
          }
          return
        }
        error.value = apiErrorMessage(cardsError, '卡片加载失败。')
      }
    } catch (loadError) {
      if (loadError instanceof ApiClientError && loadError.code === 'CANCELLED') return
      if (loadError instanceof ApiClientError && loadError.code === 'NOT_FOUND') {
        error.value = '没有找到这个深读任务。'
      } else {
        error.value = apiErrorMessage(loadError, '理解状态加载失败。')
      }
    } finally {
      if (loadController === controller) {
        isLoading.value = false
        loadController = null
      }
    }
  }

  async function reparseCurrentPaper() {
    if (isReparsing.value) return null
    reparseController?.abort()
    const controller = new AbortController()
    reparseController = controller
    isReparsing.value = true
    error.value = ''
    try {
      const result = await workspaceApi.reparse(jobId, controller.signal, task => {
        reparseProgress.value = task.progress
        reparseStage.value = task.stage
        window.localStorage.setItem(reparseTaskKey, task.task_id)
      })
      window.localStorage.removeItem(reparseTaskKey)
      return result.job_id
    } catch (reparseError) {
      if (!(reparseError instanceof ApiClientError && reparseError.code === 'CANCELLED')) {
        error.value = apiErrorMessage(reparseError, '重新解析任务创建失败。')
      }
      if (!isRecoverableTaskError(reparseError)) window.localStorage.removeItem(reparseTaskKey)
      return null
    } finally {
      if (reparseController === controller) {
        isReparsing.value = false
        reparseController = null
      }
    }
  }

  async function resumeReparseTask() {
    const taskId = window.localStorage.getItem(reparseTaskKey)
    if (!taskId || isReparsing.value) return null
    isReparsing.value = true
    try {
      const result = await researchApi.resumeDocumentTask<ReparseResponse>(taskId, task => {
        reparseProgress.value = task.progress
        reparseStage.value = task.stage
      })
      window.localStorage.removeItem(reparseTaskKey)
      return result.job_id
    } catch (resumeError) {
      if (!isRecoverableTaskError(resumeError)) window.localStorage.removeItem(reparseTaskKey)
      error.value = apiErrorMessage(resumeError, '之前的重新解析任务无法恢复。')
      return null
    } finally {
      isReparsing.value = false
    }
  }

  function isRecoverableTaskError(value: unknown) {
    return value instanceof ApiClientError
      && ['TIMEOUT', 'NETWORK_ERROR', 'CANCELLED'].includes(value.code)
  }

  onBeforeUnmount(() => {
    loadController?.abort()
    reparseController?.abort()
  })

  return {
    understandingStatus,
    paperWorkspaceStatus,
    cards,
    degraded,
    missingComponents,
    isLoading,
    isReparsing,
    reparseProgress,
    reparseStage,
    error,
    status,
    canShowCards,
    paperCard,
    teachingCards,
    allFormulaCards,
    formulaCards,
    hiddenRawFormulaCount,
    loadWorkspace,
    reparseCurrentPaper,
    resumeReparseTask,
  }
}
