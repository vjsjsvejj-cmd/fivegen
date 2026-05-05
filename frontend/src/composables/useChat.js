import { ref, nextTick } from 'vue'
import socketManager from '../utils/socket'

export function useChat({ userId, showSidePanel, activeSidePanel, unreadMessages: externalUnreadMessages }) {
  const chatMessages = ref([])
  const chatInput = ref('')
  const unreadMessages = externalUnreadMessages || ref(0)
  const chatMessagesRef = ref(null)

  const handleSendChatMessage = () => {
    const message = chatInput.value.trim()
    if (message) {
      socketManager.sendChatMessage(message)
      chatInput.value = ''
    }
  }

  const handleChatMessage = (message) => {
    chatMessages.value.push(message)
    if (message.user_id !== userId.value &&
        !(showSidePanel.value && activeSidePanel.value === 'chat')) {
      unreadMessages.value++
    }
    nextTick(() => {
      if (chatMessagesRef.value) {
        chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
      }
    })
  }

  const handleChatHistory = (data) => {
    chatMessages.value = data.chat || []
    nextTick(() => {
      if (chatMessagesRef.value) {
        chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
      }
    })
  }

  const formatTime = (isoString) => {
    const date = new Date(isoString)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  const registerSocketEvents = () => {
    socketManager.on('chat_message', handleChatMessage)
    socketManager.on('chat_history', handleChatHistory)
  }

  const unregisterSocketEvents = () => {
    socketManager.off('chat_message', handleChatMessage)
    socketManager.off('chat_history', handleChatHistory)
  }

  return {
    chatMessages,
    chatInput,
    unreadMessages,
    chatMessagesRef,
    handleSendChatMessage,
    handleChatMessage,
    handleChatHistory,
    formatTime,
    registerSocketEvents,
    unregisterSocketEvents,
  }
}
