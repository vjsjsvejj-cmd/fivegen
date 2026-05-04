import { io } from 'socket.io-client'
import { v4 as uuidv4 } from 'uuid'
import { SOCKET_URL } from './config.js'

class SocketManager {
  constructor() {
    this.socket = null
    this.roomId = this.getRoomIdFromUrl() || this.getRoomIdFromStorage() || '10086'
    this.userId = null
    this.isConnected = false
    this.listeners = new Map()
    // 保存房间ID到本地存储
    this.saveRoomIdToStorage(this.roomId)
  }

  getRoomIdFromUrl() {
    const urlParams = new URLSearchParams(window.location.search)
    return urlParams.get('room')
  }

  updateRoomIdInUrl(roomId) {
    const url = new URL(window.location)
    url.searchParams.set('room', roomId)
    window.history.replaceState({}, '', url)
  }

  getRoomIdFromStorage() {
    try {
      return localStorage.getItem('fivetv-room-id')
    } catch (e) {
      return null
    }
  }

  saveRoomIdToStorage(roomId) {
    try {
      localStorage.setItem('fivetv-room-id', roomId)
    } catch (e) {
      // 忽略存储错误
    }
  }

  connect() {
    if (this.socket) {
      return
    }

    this.socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    })

    this.socket.on('connect', () => {
      this.isConnected = true
      this.emit('connect')
    })

    this.socket.on('disconnect', () => {
      this.isConnected = false
      this.emit('disconnect')
    })

    this.socket.on('connected', (data) => {
      this.userId = data.user_id
      this.joinRoom(this.roomId)
      this.emit('connected', data)
    })

    this.socket.on('user_joined', (data) => {
      this.emit('user_joined', data)
    })

    this.socket.on('user_left', (data) => {
      this.emit('user_left', data)
    })

    this.socket.on('room_members', (data) => {
      this.emit('room_members', data)
    })

    this.socket.on('pong', (data) => {
      this.emit('pong', data)
    })

    this.socket.on('test_message', (data) => {
      this.emit('test_message', data)
    })

    this.socket.on('generation_progress', (data) => {
      this.emit('generation_progress', data)
    })

    this.socket.on('image_completed', (data) => {
      console.log('📡 socket.js 收到 image_completed:', data.task_id)
      this.emit('image_completed', data)
    })

    this.socket.on('video_completed', (data) => {
      console.log('📡 socket.js 收到 video_completed:', data.task_id)
      this.emit('video_completed', data)
    })
    
    this.socket.on('history_data', (data) => {
      this.emit('history_data', data)
    })

    this.socket.on('task_cancelled', (data) => {
      this.emit('task_cancelled', data)
    })

    this.socket.on('chat_message', (data) => {
      this.emit('chat_message', data)
    })

    this.socket.on('chat_history', (data) => {
      this.emit('chat_history', data)
    })

    // 模版相关事件
    this.socket.on('templates_list', (data) => {
      this.emit('templates_list', data)
    })

    this.socket.on('template_error', (data) => {
      this.emit('template_error', data)
    })

    this.socket.on('connect_error', (error) => {
      console.error('Connection error:', error)
      this.emit('connect_error', error)
    })
  }

  disconnect() {
    if (this.socket) {
      this.leaveRoom(this.roomId)
      this.socket.disconnect()
      this.socket = null
      this.isConnected = false
    }
  }

  joinRoom(roomId) {
    if (!this.socket) {
      this.connect()
    }
    
    if (this.socket && this.socket.connected) {
      if (this.roomId && this.roomId !== roomId) {
        this.leaveRoom(this.roomId)
      }
      this.roomId = roomId
      this.updateRoomIdInUrl(roomId)
      this.saveRoomIdToStorage(roomId)
      this.socket.emit('join_room', { room_id: roomId })
    } else if (this.socket) {
      // 如果还没连接，等待连接后再加入房间
      const joinWhenConnected = () => {
        if (this.roomId && this.roomId !== roomId) {
          this.leaveRoom(this.roomId)
        }
        this.roomId = roomId
        this.updateRoomIdInUrl(roomId)
        this.saveRoomIdToStorage(roomId)
        this.socket.emit('join_room', { room_id: roomId })
        this.socket.off('connect', joinWhenConnected)
      }
      this.socket.on('connect', joinWhenConnected)
    }
  }

  leaveRoom(roomId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('leave_room', { room_id: roomId })
    }
  }

  ping() {
    if (this.socket && this.socket.connected) {
      const timestamp = Date.now()
      this.socket.emit('ping', { timestamp })
    }
  }

  sendTestMessage(message, roomId = this.roomId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('test_message', { message, room_id: roomId })
    }
  }

  generateImage(params, roomId = this.roomId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('generate_image', { ...params, room_id: roomId })
    }
  }

  generateVideo(params, roomId = this.roomId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('generate_video', { ...params, room_id: roomId })
    }
  }

  getHistory(roomId = this.roomId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('get_history', { room_id: roomId })
    }
  }

  cancelTask(taskId, taskType = 'video', roomId = this.roomId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('cancel_task', { 
        task_id: taskId, 
        type: taskType,
        room_id: roomId 
      })
    }
  }

  sendChatMessage(message, roomId = this.roomId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('send_chat_message', { message, room_id: roomId })
    }
  }

  getChatHistory(roomId = this.roomId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('get_chat_history', { room_id: roomId })
    }
  }

  // 模版相关方法
  getTemplates() {
    if (this.socket && this.socket.connected) {
      this.socket.emit('get_templates', {})
    }
  }

  addTemplate(templateData) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('add_template', { template: templateData })
    }
  }

  updateTemplate(templateId, templateData) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('update_template', { template_id: templateId, template: templateData })
    }
  }

  deleteTemplate(templateId) {
    if (this.socket && this.socket.connected) {
      this.socket.emit('delete_template', { template_id: templateId })
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index !== -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in listener for event ${event}:`, error)
        }
      })
    }
  }
}

const socketManager = new SocketManager()
export default socketManager
