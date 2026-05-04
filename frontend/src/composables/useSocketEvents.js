import socketManager from '../utils/socket'

export function useSocketEvents({
  handleUserJoined,
  handleUserLeft,
  handleRoomMembers,
  handleConnect,
  handleDisconnect,
  handleProgress,
  handleImageCompleted,
  handleVideoCompleted,
  handleHistoryData,
  handleTaskCancelled,
  registerTemplateEvents,
  registerChatEvents,
  unregisterTemplateEvents,
  unregisterChatEvents,
}) {
  let _connectedHandler = null

  const registerSocketListeners = (userIdCallback, getTemplatesCallback) => {
    _connectedHandler = (data) => {
      userIdCallback(data.user_id)
      getTemplatesCallback()
    }

    socketManager.on('connected', _connectedHandler)
    socketManager.on('user_joined', handleUserJoined)
    socketManager.on('user_left', handleUserLeft)
    socketManager.on('room_members', handleRoomMembers)
    socketManager.on('generation_progress', handleProgress)
    socketManager.on('image_completed', handleImageCompleted)
    socketManager.on('video_completed', handleVideoCompleted)
    socketManager.on('history_data', handleHistoryData)
    socketManager.on('task_cancelled', handleTaskCancelled)
    socketManager.on('connect', handleConnect)
    socketManager.on('disconnect', handleDisconnect)

    registerTemplateEvents()
    registerChatEvents()

    socketManager.connect()
  }

  const unregisterSocketListeners = () => {
    socketManager.off('connected', _connectedHandler)
    socketManager.off('user_joined', handleUserJoined)
    socketManager.off('user_left', handleUserLeft)
    socketManager.off('room_members', handleRoomMembers)
    socketManager.off('generation_progress', handleProgress)
    socketManager.off('image_completed', handleImageCompleted)
    socketManager.off('video_completed', handleVideoCompleted)
    socketManager.off('history_data', handleHistoryData)
    socketManager.off('task_cancelled', handleTaskCancelled)
    socketManager.off('connect', handleConnect)
    socketManager.off('disconnect', handleDisconnect)

    if (unregisterTemplateEvents) unregisterTemplateEvents()
    if (unregisterChatEvents) unregisterChatEvents()

    socketManager.disconnect()
  }

  return {
    registerSocketListeners,
    unregisterSocketListeners,
  }
}
