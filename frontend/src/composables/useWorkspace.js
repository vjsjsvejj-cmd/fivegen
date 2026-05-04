import { ref, computed, nextTick } from 'vue'
import socketManager from '../utils/socket'
import { resolveUrl, handleImageError } from '../utils/media.js'

export function useWorkspace({ toast }) {
  const activeTab = ref('image')
  const results = ref([])
  const historyItems = ref([])
  const progressList = ref([])
  const currentTaskId = ref(null)
  const imageWorkspaceRef = ref(null)
  const videoWorkspaceRef = ref(null)

  const currentWorkspaceRef = computed(() => {
    return activeTab.value === 'image' ? imageWorkspaceRef : videoWorkspaceRef
  })

  const switchTab = (tab) => {
    activeTab.value = tab
  }

  const handleGenerate = (params) => {
    currentTaskId.value = params.task_id || null
    if (params.type === 'video' || params.duration) {
      socketManager.generateVideo(params)
    } else {
      socketManager.generateImage(params)
    }
  }

  const handleCancel = () => {
    if (currentTaskId.value) {
      socketManager.cancelTask(currentTaskId.value, 'video')
      progressList.value = progressList.value.filter(p => p.task_id !== currentTaskId.value)
      currentTaskId.value = null
    }
  }

  const handleCancelTask = (item) => {
    socketManager.cancelTask(item.task_id, item.type)
    progressList.value = progressList.value.filter(p => p.task_id !== item.task_id)
    if (currentTaskId.value === item.task_id) {
      currentTaskId.value = null
    }
  }

  const handleReEdit = (result) => {
    activeTab.value = result.type === 'video' ? 'video' : 'image'
    nextTick(() => {
      const workspace = result.type === 'video' ? videoWorkspaceRef : imageWorkspaceRef
      if (workspace?.value?.handleReEdit) {
        workspace.value.handleReEdit(result)
      }
    })
  }

  const handleProgress = (data) => {
    const existingIndex = progressList.value.findIndex(p => p.task_id === data.task_id)
    if (existingIndex !== -1) {
      progressList.value[existingIndex] = { ...data }
    } else {
      progressList.value.push({ ...data })
    }
  }

  const handleImageCompleted = (data) => {
    results.value.unshift(data)
    progressList.value = progressList.value.filter(p => p.task_id !== data.task_id)
    socketManager.getHistory()
  }

  const handleVideoCompleted = (data) => {
    results.value.unshift(data)
    progressList.value = progressList.value.filter(p => p.task_id !== data.task_id)
    socketManager.getHistory()
  }

  const handleHistoryData = (data) => {
    historyItems.value = data.history
    const localTaskIds = new Set(results.value.map(r => r.task_id))
    const historyResults = data.history || []
    const newFromHistory = historyResults.filter(h => !localTaskIds.has(h.task_id))
    results.value = [...newFromHistory, ...results.value]
  }

  const handleTaskCancelled = (data) => {
    progressList.value = progressList.value.filter(p => p.task_id !== data.task_id)
    if (data.task_id === currentTaskId.value) {
      currentTaskId.value = null
    }
  }

  const getHistoryDisplayUrl = (item) => {
    return resolveUrl(item.url || item.remote_url)
  }

  const handleHistoryImageError = handleImageError

  return {
    activeTab,
    results,
    historyItems,
    progressList,
    currentTaskId,
    imageWorkspaceRef,
    videoWorkspaceRef,
    currentWorkspaceRef,
    switchTab,
    handleGenerate,
    handleCancel,
    handleCancelTask,
    handleReEdit,
    handleProgress,
    handleImageCompleted,
    handleVideoCompleted,
    handleHistoryData,
    handleTaskCancelled,
    getHistoryDisplayUrl,
    handleHistoryImageError,
  }
}
