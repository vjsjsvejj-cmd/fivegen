import { ref } from 'vue'
import socketManager from '../utils/socket'

export function useSidePanel({ templatePanelSearch, unreadMessages }) {
  const showSidePanel = ref(false)
  const activeSidePanel = ref('favorites')

  const toggleSidePanel = (panel) => {
    if (showSidePanel.value && activeSidePanel.value === panel) {
      showSidePanel.value = false
    } else {
      showSidePanel.value = true
      activeSidePanel.value = panel
      if (panel === 'chat') {
        socketManager.getChatHistory()
        unreadMessages.value = 0
      }
      if (panel === 'templates') {
        templatePanelSearch.value = ''
      }
    }
  }

  return {
    showSidePanel,
    activeSidePanel,
    toggleSidePanel,
  }
}
