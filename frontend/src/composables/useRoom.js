import { ref } from 'vue'
import socketManager from '../utils/socket'

export function useRoom({ toast }) {
  const isConnected = ref(false)
  const roomId = ref(socketManager.roomId)
  const roomMembers = ref([])
  const copySuccess = ref(false)
  const joinRoomInput = ref('')

  const copyRoomId = async () => {
    try {
      await navigator.clipboard.writeText(roomId.value)
      copySuccess.value = true
      setTimeout(() => { copySuccess.value = false }, 2000)
    } catch (err) {
      console.error('Copy failed:', err)
    }
  }

  const copyShareLink = async () => {
    try {
      const shareUrl = `${window.location.origin}${window.location.pathname}?room=${roomId.value}`
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(shareUrl)
      } else {
        const textArea = document.createElement('textarea')
        textArea.value = shareUrl
        textArea.style.position = 'fixed'
        textArea.style.left = '-999999px'
        textArea.style.top = '-999999px'
        document.body.appendChild(textArea)
        textArea.focus()
        textArea.select()
        try {
          document.execCommand('copy')
        } catch (fallbackErr) {
          console.error('Fallback copy failed:', fallbackErr)
        }
        document.body.removeChild(textArea)
      }
      copySuccess.value = true
      setTimeout(() => { copySuccess.value = false }, 2000)
    } catch (err) {
      console.error('Copy failed:', err)
      toast.error('复制失败，请手动复制链接')
    }
  }

  const joinNewRoom = ({ results, historyItems }) => {
    const newRoomId = joinRoomInput.value.trim()
    if (newRoomId && newRoomId !== roomId.value) {
      socketManager.joinRoom(newRoomId)
      roomId.value = newRoomId
      joinRoomInput.value = ''
      results.value = []
      historyItems.value = []
      setTimeout(() => {
        socketManager.getHistory()
      }, 500)
    }
  }

  const handleUserJoined = () => {}
  const handleUserLeft = () => {}
  const handleRoomMembers = (data) => {
    roomMembers.value = data.members
  }

  const handleConnect = () => {
    isConnected.value = true
    setTimeout(() => {
      socketManager.getHistory()
    }, 300)
  }

  const handleDisconnect = () => {
    isConnected.value = false
  }

  return {
    isConnected,
    roomId,
    roomMembers,
    copySuccess,
    joinRoomInput,
    copyRoomId,
    copyShareLink,
    joinNewRoom,
    handleUserJoined,
    handleUserLeft,
    handleRoomMembers,
    handleConnect,
    handleDisconnect,
  }
}
