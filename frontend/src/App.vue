<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick, provide } from 'vue'
import socketManager from './utils/socket'
import ImageWorkspace from './components/ImageWorkspace.vue'
import VideoWorkspace from './components/VideoWorkspace.vue'
import ResultGrid from './components/ResultGrid.vue'
import Modal from './components/Modal.vue'
import ComparisonPanel from './components/ComparisonPanel.vue'
import ComparisonFullscreen from './components/ComparisonFullscreen.vue'
import InversionModal from './components/InversionModal.vue'
import FiveTV from './components/FiveTV/FiveTV.vue'
import VoiceCloneWorkspace from './components/VoiceCloneWorkspace.vue'

const activeTab = ref('image')
const showFiveTV = ref(false)
let fiveTVClickCount = 0
let fiveTVClickTimer = null
const isConnected = ref(false)
const roomId = ref(socketManager.roomId)
const userId = ref('')
const roomMembers = ref([])
const copySuccess = ref(false)
const joinRoomInput = ref('')
const showSidePanel = ref(false)
const activeSidePanel = ref('favorites')  // 'favorites' | 'templates' | 'chat' | 'comparison'

// 对比功能
const comparisonFullscreenVisible = ref(false)
const comparisonItem1 = ref(null)
const comparisonItem2 = ref(null)

// 逆向解析弹窗
const showInversionModal = ref(false)

const startComparison = (data) => {
  comparisonItem1.value = data.item1
  comparisonItem2.value = data.item2
  comparisonFullscreenVisible.value = true
}

const closeComparisonFullscreen = () => {
  comparisonFullscreenVisible.value = false
}

// 处理逆向解析结果应用
const handleInversionApply = (result) => {
  // 应用到当前激活的工作区
  const currentWorkspace = activeTab.value === 'image' ? imageWorkspaceRef : videoWorkspaceRef
  if (currentWorkspace && currentWorkspace.value && currentWorkspace.value.setPrompt) {
    currentWorkspace.value.setPrompt(result.positive)
  }
}

const results = ref([])
const historyItems = ref([])
const progressList = ref([])
const chatMessages = ref([])
const chatInput = ref('')
const unreadMessages = ref(0)

// 收藏状态
const favorites = ref([])

// 切换收藏
const toggleFavorite = (item) => {
  const index = favorites.value.findIndex(f => f.task_id === item.task_id)
  if (index === -1) {
    favorites.value.push({
      ...item,
      favoriteTime: Date.now()
    })
  } else {
    favorites.value.splice(index, 1)
  }
}

// 检查是否已收藏
const isFavorite = (item) => {
  return favorites.value.some(f => f.task_id === item.task_id)
}

// 模版数据 - 默认模版列表
const defaultTemplates = [
  { id: 'template_1', name: 'Slogan', content: '「文字内容」+「出现时机」+「出现位置」+「出现方式」，「文字特征（颜色、风格）」', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_2', name: '字幕', content: '画面底部出现字幕，字幕内容为"……"，字幕需与音频节奏完全同步。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_3', name: '气泡台词', content: '「角色」说："……"，角色话说时周围出现气泡，气泡里写着台词。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_4', name: '主体多视角图参考', content: '参考/提取/结合+「图片 n」中的「主体」，生成「画面描述」，保持「主体」特征一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_5', name: '多图参考', content: '参考/提取/结合/按照/生成+「图片n」中的「被参考元素描述」，生成「画面描述」，保持「被参考元素」特征一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_6', name: '视频参考', content: '参考「视频n」的「动作描述」，生成「画面描述」，保持动作细节一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_7', name: '运镜参考', content: '参考「视频n」的「运镜描述」，生成「画面描述」，保持运镜一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_8', name: '特效参考', content: '参考「视频n」的「特效描述」，生成「画面描述」，保持特效一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_9', name: '增加元素', content: '在「视频n」的「时间位置」+「空间位置」，增加「理想元素描述」。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_10', name: '删除元素', content: '删除「视频n」中的「被删除元素」，视频其他内容保持不变。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_11', name: '修改元素', content: '将「视频n」中的「被更换元素描述」，替换为「理想元素描述」。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_12', name: '视频延长', content: '向前/向后延长「视频n」+「需延长的视频描述」\n生成「视频n」之前/之后的内容+「需延长的视频描述」', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_13', name: '轨道补齐', content: '「视频1」+「过渡画面描述」+接「视频2」+「过渡画面描述」+接「视频3」', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
]

const templates = ref([...defaultTemplates])

// 提供模板数据给子组件
provide('templates', templates)

// 模版编辑相关
const showTemplateEditor = ref(false)
const isAddingTemplate = ref(false)
const editingTemplate = ref(null)
const newTemplate = ref({
  name: '',
  content: '',
  fullWidth: false
})

// 模板面板搜索
const templatePanelSearch = ref('')

// 过滤后的模板列表
const filteredTemplatesForPanel = computed(() => {
  if (!templatePanelSearch.value) {
    return templates.value
  }
  const searchTerm = templatePanelSearch.value.toLowerCase()
  return templates.value.filter(template => 
    template.name.toLowerCase().includes(searchTerm) || 
    template.content.toLowerCase().includes(searchTerm)
  )
})

// 当前编辑的模版（计算属性，用于v-model）
const currentEditingTemplate = computed({
  get: () => isAddingTemplate.value ? newTemplate.value : (editingTemplate.value || newTemplate.value),
  set: (val) => {
    if (isAddingTemplate.value) {
      newTemplate.value = val
    } else if (editingTemplate.value) {
      editingTemplate.value = val
    }
  }
})

// 获取模版列表
const getTemplates = () => {
  socketManager.getTemplates()
}

// 打开新增模版弹窗
const openAddTemplate = () => {
  isAddingTemplate.value = true
  newTemplate.value = { name: '', content: '', fullWidth: false }
  showTemplateEditor.value = true
}

// 添加模版
const addTemplate = () => {
  if (!newTemplate.value.name.trim() || !newTemplate.value.content.trim()) {
    alert('模版名称和内容不能为空！')
    return
  }
  socketManager.addTemplate(newTemplate.value)
  showTemplateEditor.value = false
  isAddingTemplate.value = false
  newTemplate.value = { name: '', content: '', fullWidth: false }
}

// 编辑模版
const editTemplate = (template) => {
  isAddingTemplate.value = false
  editingTemplate.value = { ...template }
  showTemplateEditor.value = true
}

// 保存编辑
const saveTemplateEdit = () => {
  if (isAddingTemplate.value) {
    // 保存新增
    addTemplate()
  } else {
    // 保存编辑
    if (!editingTemplate.value.name.trim() || !editingTemplate.value.content.trim()) {
      alert('模版名称和内容不能为空！')
      return
    }
    socketManager.updateTemplate(editingTemplate.value.id, editingTemplate.value)
    showTemplateEditor.value = false
    editingTemplate.value = null
  }
}

// 删除模版
const deleteTemplate = (templateId) => {
  if (confirm('确定要删除这个模版吗？')) {
    socketManager.deleteTemplate(templateId)
  }
}

// 取消编辑
const cancelTemplateEdit = () => {
  showTemplateEditor.value = false
  editingTemplate.value = null
}

const leftPanelWidth = ref(720)
const minLeftWidth = 400
const maxLeftWidth = 900
const isResizing = ref(false)

const imageWorkspaceRef = ref(null)
const videoWorkspaceRef = ref(null)
const chatMessagesRef = ref(null)

// 收藏预览相关
const favoriteModalVisible = ref(false)
const favoriteModalType = ref('image')
const favoriteModalUrl = ref('')

// 导入 API_BASE_URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const getFavoriteDisplayUrl = (item) => {
  if (item.type === 'video') {
    const thumbnailUrl = item.thumbnail || item.url
    return thumbnailUrl.startsWith('/') ? `${API_BASE_URL}${thumbnailUrl}` : thumbnailUrl
  }
  const displayUrl = item.url || item.remote_url
  return displayUrl.startsWith('/') ? `${API_BASE_URL}${displayUrl}` : displayUrl
}

const handleFavoriteImageError = (event, item) => {
  if (item.remote_url && event.target.src !== item.remote_url) {
    event.target.src = item.remote_url
  }
}

const openFavoritePreview = (item) => {
  favoriteModalType.value = item.type === 'video' ? 'video' : 'image'
  const previewUrl = item.remote_url || item.url
  favoriteModalUrl.value = previewUrl.startsWith('/') ? `${API_BASE_URL}${previewUrl}` : previewUrl
  favoriteModalVisible.value = true
}

const closeFavoriteModal = () => {
  favoriteModalVisible.value = false
}

const currentWorkspaceRef = computed(() => {
  return activeTab.value === 'image' ? imageWorkspaceRef : videoWorkspaceRef
})

const switchTab = (tab) => {
  activeTab.value = tab
}

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
    // 尝试使用现代剪贴板 API
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(shareUrl)
    } else {
      // 备用方案：使用传统的 textarea 方式
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
    alert('复制失败，请手动复制链接')
  }
}

const joinNewRoom = () => {
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

const currentTaskId = ref(null)

const handleGenerate = (params) => {
  // 记录当前任务ID，用于取消
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
    // 从进度列表中移除
    progressList.value = progressList.value.filter(p => p.task_id !== currentTaskId.value)
    currentTaskId.value = null
  }
}

const handleCancelTask = (item) => {
  console.log('取消任务:', item)
  // 调用真正的取消 API
  socketManager.cancelTask(item.task_id, item.type)
  // 从进度列表中移除
  progressList.value = progressList.value.filter(p => p.task_id !== item.task_id)
  if (currentTaskId.value === item.task_id) {
    currentTaskId.value = null
  }
}

const handleReEdit = (result) => {
  // 第一步：先切换标签页
  activeTab.value = result.type === 'video' ? 'video' : 'image'
  // 第二步：等待 DOM 更新后调用对应的 handleReEdit
  setTimeout(() => {
    const workspace = result.type === 'video' ? videoWorkspaceRef : imageWorkspaceRef
    if (workspace?.value?.handleReEdit) {
      workspace.value.handleReEdit(result)
    }
  }, 100)
}

const handleMouseDown = (e) => {
  isResizing.value = true
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

const handleMouseMove = (e) => {
  if (isResizing.value) {
    const newWidth = e.clientX
    if (newWidth >= minLeftWidth && newWidth <= maxLeftWidth) {
      leftPanelWidth.value = newWidth
    }
  }
}

const handleMouseUp = () => {
  isResizing.value = false
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
}

const handleConnect = () => {
  isConnected.value = true
  // 等待一小会儿，确保joined房间后再获取历史记录
  setTimeout(() => {
    socketManager.getHistory()
  }, 300)
}

const handleDisconnect = () => {
  isConnected.value = false
}

const handleUserJoined = (data) => {
}

const handleUserLeft = (data) => {
}

const handleRoomMembers = (data) => {
  roomMembers.value = data.members
}

const handleProgress = (data) => {
  // 查找是否已有这个任务的进度
  const existingIndex = progressList.value.findIndex(p => p.task_id === data.task_id)
  if (existingIndex !== -1) {
    // 更新已有进度
    progressList.value[existingIndex] = { ...data }
  } else {
    // 添加新进度
    progressList.value.push({ ...data })
  }
}

const handleImageCompleted = (data) => {
  results.value.unshift(data)
  // 从进度列表中移除已完成的任务
  progressList.value = progressList.value.filter(p => p.task_id !== data.task_id)
  socketManager.getHistory()
}

const handleVideoCompleted = (data) => {
  results.value.unshift(data)
  // 从进度列表中移除已完成的任务
  progressList.value = progressList.value.filter(p => p.task_id !== data.task_id)
  socketManager.getHistory()
}

const handleHistoryData = (data) => {
  historyItems.value = data.history
  // 同时也把历史数据加载到结果展示区
  if (data.history.length > 0) {
    results.value = [...data.history]
  }
}

const getHistoryDisplayUrl = (item) => {
  // 历史记录：优先用本地URL，失败时浏览器会自动显示错误，然后我们可以通过 onerror 处理
  const displayUrl = item.url || item.remote_url
  return displayUrl.startsWith('/') ? `${window.location.origin}${displayUrl}` : displayUrl
}

const handleHistoryImageError = (event, item) => {
  // 如果本地图片加载失败，尝试使用远程URL
  if (item.remote_url && event.target.src !== item.remote_url) {
    event.target.src = item.remote_url
  }
}

const handleTaskCancelled = (data) => {
  console.log('任务已取消:', data)
  // 从进度列表中移除已取消的任务
  progressList.value = progressList.value.filter(p => p.task_id !== data.task_id)
  if (data.task_id === currentTaskId.value) {
    currentTaskId.value = null
  }
}

const toggleSidePanel = (panel) => {
  if (showSidePanel.value && activeSidePanel.value === panel) {
    showSidePanel.value = false
  } else {
    showSidePanel.value = true
    activeSidePanel.value = panel
    // 如果打开聊天面板，获取聊天历史并清除未读
    if (panel === 'chat') {
      socketManager.getChatHistory()
      unreadMessages.value = 0
    }
    // 如果打开模板面板，清空搜索词
    if (panel === 'templates') {
      templatePanelSearch.value = ''
    }
  }
}

const handleSendChatMessage = () => {
  const message = chatInput.value.trim()
  if (message) {
    socketManager.sendChatMessage(message)
    chatInput.value = ''
  }
}

const handleChatMessage = (message) => {
  chatMessages.value.push(message)
  // 如果不是自己的消息，并且聊天面板未打开，则增加未读计数
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

const handleSelectTemplate = (template) => {
  // 选择当前激活的工作区
  const currentWorkspace = activeTab.value === 'image' ? imageWorkspaceRef.value : videoWorkspaceRef.value
  if (currentWorkspace && currentWorkspace.setPrompt) {
    currentWorkspace.setPrompt(template.content)
  }
}

const handleFiveTVClick = () => {
  // 直接进入Five TV
  showFiveTV.value = true
}

const handleExitFiveTV = () => {
  showFiveTV.value = false
}

onMounted(() => {
  // 先注册所有监听器
  socketManager.on('connected', (data) => {
    userId.value = data.user_id
    // 连接成功后获取模版列表
    getTemplates()
  })
  socketManager.on('user_joined', handleUserJoined)
  socketManager.on('user_left', handleUserLeft)
  socketManager.on('room_members', handleRoomMembers)
  socketManager.on('pong', () => {})
  socketManager.on('test_message', () => {})
  socketManager.on('generation_progress', handleProgress)
  socketManager.on('image_completed', handleImageCompleted)
  socketManager.on('video_completed', handleVideoCompleted)
  socketManager.on('history_data', handleHistoryData)
  socketManager.on('task_cancelled', handleTaskCancelled)
  socketManager.on('connect', handleConnect)
  socketManager.on('disconnect', handleDisconnect)
  socketManager.on('chat_message', handleChatMessage)
  socketManager.on('chat_history', handleChatHistory)
  
  // 模版相关事件
  socketManager.on('templates_list', (data) => {
    templates.value = data.templates || []
  })
  socketManager.on('template_error', (data) => {
    alert('模版操作失败: ' + data.error)
  })
  
  // 然后再连接
  socketManager.connect()
})

onUnmounted(() => {
  socketManager.disconnect()
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
})
</script>

<template>
  <div class="app">
    <!-- Five TV页面 -->
    <FiveTV v-if="showFiveTV" :on-back="handleExitFiveTV" />
    
    <!-- 主界面 -->
    <template v-else>
      <header class="app-header">
        <div class="header-left">
          <h1 class="logo">🎨 Five Gen 2.4.1</h1>
          <div class="tab-bar">
            <button 
              :class="['tab-btn', { active: activeTab === 'image' }]"
              @click="switchTab('image')"
            >
              🖼️ 图片生成
            </button>
            <button 
              :class="['tab-btn', { active: activeTab === 'video' }]"
              @click="switchTab('video')"
            >
              🎬 视频制作
            </button>
            <button 
              :class="['tab-btn', 'inversion-btn', { active: showInversionModal }]"
              @click="showInversionModal = true"
            >
              🔍 逆向解析
            </button>
            <button 
              :class="['tab-btn', 'five-tv-btn']"
              @click="handleFiveTVClick"
            >
              📺 Five TV
            </button>
            <button 
              :class="['tab-btn', { active: activeTab === 'voice-clone' }]"
              @click="switchTab('voice-clone')"
            >
              🎙️ 声音 & 数字人
            </button>
          </div>
        </div>
      <div class="header-right">
        <div class="room-info">
          <div 
            :class="['status-dot', isConnected ? 'online' : 'offline']"
            :title="isConnected ? '已连接' : '未连接'"
          ></div>
          <span class="status-label">{{ isConnected ? '已连接' : '未连接' }}</span>
          <div class="room-id-wrapper">
            <span class="room-id">{{ roomId }}</span>
            <button @click="copyRoomId" class="btn btn-small btn-icon" :class="{ success: copySuccess }">
              {{ copySuccess ? '✓' : '📋' }}
            </button>
          </div>
          <span class="members-count">{{ roomMembers.length }}人在线</span>
          <button @click="copyShareLink" class="btn btn-small btn-secondary">
            复制链接
          </button>
        </div>
        <div class="join-room">
          <input 
            v-model="joinRoomInput" 
            type="text" 
            placeholder="输入房间ID..."
            @keyup.enter="joinNewRoom"
            class="join-input"
          />
          <button @click="joinNewRoom" class="btn btn-small btn-primary">
            加入
          </button>
        </div>
      </div>
    </header>

    <div class="main-content">
      <aside 
        class="left-panel" 
        :style="{ width: leftPanelWidth + 'px' }"
      >
        <ImageWorkspace 
          v-if="activeTab === 'image'"
          ref="imageWorkspaceRef"
          :room-id="roomId"
          :user-id="userId"
          :is-connected="isConnected"
          @generate="handleGenerate"
        />
        <VideoWorkspace 
          v-else-if="activeTab === 'video'"
          ref="videoWorkspaceRef"
          :room-id="roomId"
          :user-id="userId"
          :is-connected="isConnected"
          @generate="handleGenerate"
        />
        <VoiceCloneWorkspace
          v-else-if="activeTab === 'voice-clone'"
          :room-id="roomId"
          :user-id="userId"
          :is-connected="isConnected"
          @generate="handleGenerate"
        />
      </aside>

      <div 
        :class="['resizer', { active: isResizing }]"
        @mousedown="handleMouseDown"
        :title="isResizing ? '调整中...' : '拖拽调整左侧宽度'"
      ></div>

      <main class="right-panel">
        <div class="panel-header">
          <div class="header-left">
            <h2>📦 结果展示</h2>
          </div>
          <div class="header-right">
            <div class="sidepanel-buttons">
              <button 
                class="btn btn-small"
                :class="{ active: showSidePanel && activeSidePanel === 'comparison' }"
                @click="toggleSidePanel('comparison')"
              >
                🔍 对比
              </button>
              <button 
                class="btn btn-small"
                :class="{ active: showSidePanel && activeSidePanel === 'favorites' }"
                @click="toggleSidePanel('favorites')"
              >
                💖 收藏
              </button>
              <button 
                class="btn btn-small"
                :class="{ active: showSidePanel && activeSidePanel === 'templates' }"
                @click="toggleSidePanel('templates')"
              >
                🗃️ 模版
              </button>
              <button 
                class="btn btn-small"
                :class="['chat-btn', { active: showSidePanel && activeSidePanel === 'chat' }]"
                @click="toggleSidePanel('chat')"
              >
                💬 聊天
                <span v-if="unreadMessages > 0" class="unread-badge">{{ unreadMessages }}</span>
              </button>
            </div>
          </div>
        </div>
        
        <div class="panel-content">
          <div v-if="showSidePanel" class="history-panel">
            <div class="history-header">
              <h3 v-if="activeSidePanel === 'comparison'">🔍 对比</h3>
              <h3 v-else-if="activeSidePanel === 'favorites'">💖 收藏</h3>
              <h3 v-else-if="activeSidePanel === 'templates'">🗃️ 模版</h3>
              <h3 v-else-if="activeSidePanel === 'chat'">💬 聊天</h3>
            </div>
            <div class="history-list">
              <!-- 对比面板 -->
              <div v-if="activeSidePanel === 'comparison'" class="comparison-panel-wrapper">
                <ComparisonPanel 
                  @close="showSidePanel = false"
                  @start-comparison="startComparison"
                />
              </div>
              
              <!-- 收藏面板 -->
              <div v-if="activeSidePanel === 'favorites'" class="favorites-panel">
                <div class="favorites-list">
                  <div 
                    v-for="item in favorites" 
                    :key="item.task_id"
                    class="favorite-item"
                  >
                    <div class="favorite-media" @click="openFavoritePreview(item)">
                      <img 
                        :src="getFavoriteDisplayUrl(item)" 
                        :alt="item.params.prompt"
                        @error="(e) => handleFavoriteImageError(e, item)"
                      />
                      <div v-if="item.type === 'video'" class="video-badge">🎬</div>
                    </div>
                    <div class="favorite-info">
                      <div class="favorite-type">{{ item.type === 'video' ? '视频' : '图片' }}</div>
                      <div 
                        class="favorite-prompt"
                        :title="item.params.displayPrompt || item.params.prompt"
                      >{{ item.params.displayPrompt || item.params.prompt }}</div>
                    </div>
                    <button 
                      class="favorite-remove-btn" 
                      @click.stop="toggleFavorite(item)"
                    >❌</button>
                  </div>
                  <div v-if="favorites.length === 0" class="favorites-empty">
                    还没有收藏内容
                  </div>
                </div>
              </div>
              
              <!-- 模版面板 -->
              <div v-if="activeSidePanel === 'templates'" class="template-panel">
                <!-- 新增模版按钮 -->
                <div class="template-panel-header">
                  <button @click="openAddTemplate" class="btn btn-small btn-primary add-template-btn">
                    ➕ 新增模版
                  </button>
                </div>
                
                <!-- 搜索框 -->
                <div class="template-search-wrapper">
                  <input
                    v-model="templatePanelSearch"
                    type="text"
                    placeholder="搜索模板..."
                    class="template-search-input"
                  />
                </div>
                
                <!-- 模版列表 -->
                <div class="template-list">
                  <div
                    v-for="template in filteredTemplatesForPanel"
                    :key="template.id"
                    class="template-item"
                  >
                    <button
                      :class="['template-btn', { 'template-btn-full': template.fullWidth }]"
                      @click="handleSelectTemplate(template)"
                    >
                      {{ template.name }}
                    </button>
                    <div class="template-actions">
                      <button @click="editTemplate(template)" class="template-action-btn" title="编辑">
                        ✏️
                      </button>
                      <button @click="deleteTemplate(template.id)" class="template-action-btn template-action-btn-delete" title="删除">
                        🗑️
                      </button>
                    </div>
                  </div>
                  <div v-if="filteredTemplatesForPanel.length === 0" class="templates-empty">
                    {{ templatePanelSearch ? '没有匹配的模板' : '还没有模版，快来添加一个吧！' }}
                  </div>
                </div>
              </div>
              
              <!-- 模版编辑弹窗 -->
              <div v-if="showTemplateEditor" class="template-editor-modal">
                <div class="template-editor-content">
                  <div class="template-editor-header">
                    <h3>{{ isAddingTemplate ? '➕ 新增模版' : '✏️ 编辑模版' }}</h3>
                    <button @click="cancelTemplateEdit" class="btn btn-small btn-icon">❌</button>
                  </div>
                  <div class="template-editor-form">
                    <label>模版名称:</label>
                    <input
                      v-model="currentEditingTemplate.name"
                      type="text"
                      placeholder="模版名称"
                      class="template-input"
                    />
                    <label>模版内容:</label>
                    <textarea
                      v-model="currentEditingTemplate.content"
                      placeholder="模版内容"
                      class="template-textarea"
                      rows="5"
                    />
                    <div class="template-options">
                      <label class="template-option-label">
                        <input
                          type="checkbox"
                          v-model="currentEditingTemplate.fullWidth"
                        />
                        全宽显示
                      </label>
                    </div>
                    <div class="template-editor-buttons">
                      <button @click="saveTemplateEdit" class="btn btn-primary">
                        保存
                      </button>
                      <button @click="cancelTemplateEdit" class="btn btn-secondary">
                        取消
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 聊天面板 -->
              <div v-if="activeSidePanel === 'chat'" class="chat-panel">
                <div class="chat-messages" ref="chatMessagesRef">
                  <div 
                    v-for="msg in chatMessages" 
                    :key="msg.id"
                    :class="['chat-message', { 'own': msg.user_id === userId }]"
                  >
                    <div class="message-header">
                      <span class="user-id">
                        {{ msg.user_id === userId ? '我' : `用户${msg.user_id.slice(0, 6)}` }}
                      </span>
                      <span class="time">{{ formatTime(msg.created_at) }}</span>
                    </div>
                    <div class="message-content">{{ msg.message }}</div>
                  </div>
                  <div v-if="chatMessages.length === 0" class="chat-empty">
                    还没有消息，开始聊天吧！
                  </div>
                </div>
                <div class="chat-input-area">
                  <input 
                    v-model="chatInput" 
                    type="text" 
                    placeholder="输入消息..." 
                    @keyup.enter="handleSendChatMessage"
                    class="chat-input"
                  />
                  <button @click="handleSendChatMessage" class="btn btn-small">发送</button>
                </div>
              </div>
            </div>
          </div>
          
          <div class="results-container">
      <ResultGrid 
      :results="results" 
      :progressList="progressList"
      :favorites="favorites"
      :isFavorite="isFavorite"
      @re-edit="handleReEdit"
      @toggle-favorite="toggleFavorite"
      @cancel-task="handleCancelTask"
    />
    </div>
        </div>
      </main>
      
      <Modal 
        :visible="favoriteModalVisible" 
        :type="favoriteModalType" 
        :url="favoriteModalUrl" 
        @close="closeFavoriteModal"
      />
      
      <ComparisonFullscreen 
        :visible="comparisonFullscreenVisible"
        :item1="comparisonItem1"
        :item2="comparisonItem2"
        @close="closeComparisonFullscreen"
      />
      
      <InversionModal 
        :visible="showInversionModal"
        @close="showInversionModal = false"
        @apply="handleInversionApply"
      />
    </div>
    </template>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #1a1a2e;
  color: #eee;
  font-family: Arial, sans-serif;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: #0f0f23;
  border-bottom: 1px solid #333;
  flex-shrink: 0;
  gap: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 30px;
}

.logo {
  margin: 0;
  font-size: 1.3rem;
}

.tab-bar {
  display: flex;
  gap: 10px;
}

.tab-btn {
  padding: 10px 20px;
  border: 1px solid #4a4a6a;
  border-radius: 8px;
  background: #2a2a4a;
  color: #ccc;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}

.tab-btn:hover {
  border-color: #00d4ff;
}

.tab-btn.active {
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  color: #000;
  border-color: transparent;
  font-weight: 600;
}

.tab-btn.inversion-btn {
  background: #2a2a4a;
  border-color: #6c3483;
  color: #ccc;
}

.tab-btn.inversion-btn:hover {
  background: #3a3a5a;
  border-color: #8e44ad;
  color: #fff;
}

.tab-btn.inversion-btn.active {
  background: linear-gradient(135deg, #9b59b6, #8e44ad);
  border-color: transparent;
  color: #fff;
  font-weight: 600;
  box-shadow: 0 4px 15px rgba(155, 89, 182, 0.3);
}

/* Five TV 按钮样式 - 和逆向解析一样，永远不点亮 */
.tab-btn.five-tv-btn {
  background: #2a2a4a;
  border-color: #6c3483;
  color: #ccc;
}

.tab-btn.five-tv-btn:hover {
  background: #3a3a5a;
  border-color: #8e44ad;
  color: #fff;
}

/* 强制确保 Five TV 按钮永远不会有点亮状态 */
.tab-btn.five-tv-btn.active {
  background: #2a2a4a !important;
  border-color: #6c3483 !important;
  color: #ccc !important;
  box-shadow: none !important;
  font-weight: normal !important;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.room-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #f87171;
}

.status-dot.online {
  background: #4ade80;
}

.status-label {
  font-size: 0.9rem;
  color: #aaa;
}

.room-id-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #2a2a4a;
  padding: 6px 10px;
  border-radius: 6px;
}

.room-id {
  font-family: monospace;
  font-size: 0.8rem;
  color: #ccc;
}

.members-count {
  font-size: 0.85rem;
  color: #aaa;
}

.join-room {
  display: flex;
  gap: 8px;
}

.join-input {
  padding: 8px 12px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #2a2a4a;
  color: #fff;
  font-size: 0.9rem;
  width: 150px;
}

.join-input:focus {
  outline: none;
  border-color: #00d4ff;
}

.btn {
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-small {
  padding: 8px 14px;
  font-size: 0.85rem;
}

.btn-icon {
  padding: 6px 10px;
  background: #4a4a6a;
  color: #fff;
}

.btn-icon:hover {
  background: #5a5a7a;
}

.btn-icon.success {
  background: #4ade80;
  color: #000;
}

.btn-primary {
  background: #00d4ff;
  color: #000;
}

.btn-primary:hover {
  background: #00b4d8;
}

.btn-secondary {
  background: #4a4a6a;
  color: #fff;
}

.btn-secondary:hover {
  background: #5a5a7a;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.left-panel {
  background: #16213e;
  border-right: 1px solid #333;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.resizer {
  width: 6px;
  background: #333;
  cursor: col-resize;
  transition: all 0.2s;
  flex-shrink: 0;
}

.resizer:hover {
  background: #00d4ff;
}

.resizer.active {
  background: #00ff88;
}

.right-panel {
  flex: 1;
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 15px 20px;
  border-bottom: 1px solid #333;
  background: #0f0f23;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.sidepanel-buttons {
  display: flex;
  gap: 8px;
}

.panel-placeholder {
  text-align: center;
  padding: 60px 20px;
  color: #666;
  font-size: 0.95rem;
}

.panel-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.history-panel {
  width: 320px;
  background: #16213e;
  border-right: 1px solid #333;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex-shrink: 0;
}

.history-header {
  padding: 15px 20px;
  border-bottom: 1px solid #333;
  background: #0f0f23;
  flex-shrink: 0;
}

.history-header h3 {
  margin: 0;
  color: #00d4ff;
  font-size: 1rem;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.history-item {
  display: flex;
  gap: 12px;
  padding: 10px;
  background: #2a2a4a;
  border-radius: 8px;
  margin-bottom: 10px;
  align-items: flex-start;
}

.history-thumb {
  width: 70px;
  height: 45px;
  border-radius: 4px;
  overflow: hidden;
  background: #1a1a2e;
  flex-shrink: 0;
}

.history-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.history-info {
  flex: 1;
  min-width: 0;
}

.history-prompt {
  font-size: 0.85rem;
  color: #eee;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 6px;
}

.history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.75rem;
  color: #888;
}

.history-meta .type {
  color: #00d4ff;
}

.history-empty {
  text-align: center;
  padding: 40px 20px;
  color: #666;
}

.results-container {
  flex: 1;
  overflow-y: auto;
}

.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-empty {
  text-align: center;
  padding: 60px 20px;
  color: #666;
  font-size: 0.95rem;
}

.chat-message {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  background: #2a2a4a;
  align-self: flex-start;
}

.chat-message.own {
  background: #0066ff;
  align-self: flex-end;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 10px;
}

.chat-message.own .message-header {
  flex-direction: row-reverse;
}

.user-id {
  font-size: 0.75rem;
  font-weight: 600;
  color: #aaa;
}

.chat-message.own .user-id {
  color: #cce0ff;
}

.time {
  font-size: 0.7rem;
  color: #777;
}

.chat-message.own .time {
  color: #bbd8ff;
}

.message-content {
  font-size: 0.9rem;
  line-height: 1.4;
  word-break: break-word;
}

.chat-input-area {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #333;
  background: #0f0f23;
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #333;
  border-radius: 8px;
  background: #1a1a2e;
  color: #fff;
  font-size: 0.9rem;
}

.chat-input:focus {
  outline: none;
  border-color: #00d4ff;
}

.chat-btn {
  position: relative;
}

.unread-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #ff4757;
  color: white;
  font-size: 0.7rem;
  font-weight: 700;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(255, 71, 87, 0.4);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.15);
    opacity: 0.9;
  }
}

/* 模版面板样式 */
.template-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.template-panel-header {
  padding: 12px;
  border-bottom: 1px solid #333;
}

.add-template-btn {
  width: 100%;
}

.template-search-wrapper {
  padding: 12px;
  border-bottom: 1px solid #333;
}

.template-search-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #2a2a4a;
  color: #fff;
  font-size: 0.9rem;
  box-sizing: border-box;
}

.template-search-input:focus {
  outline: none;
  border-color: #00d4ff;
}

.template-list {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  flex: 1;
}

.template-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(42, 42, 74, 0.5);
  border: 1px solid #333;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.template-item:hover {
  border-color: #00d4ff;
  background: rgba(42, 42, 74, 0.8);
}

.template-btn {
  flex: 1;
  padding: 10px 16px;
  background: #2a2a4a;
  border: 1px solid #3a3a5a;
  border-radius: 6px;
  color: #ffffff;
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-btn:hover {
  background: #3a3a5a;
  border-color: #00d4ff;
}

.template-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.template-action-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: #2a2a4a;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s ease;
}

.template-action-btn:hover {
  background: #3a3a5a;
}

.template-action-btn-delete:hover {
  background: rgba(255, 100, 100, 0.3);
}

.template-btn:hover {
  background: #3a3a5a;
  border-color: #00d4ff;
  transform: translateX(2px);
}

.template-btn:active {
  transform: translateX(1px);
}

/* 收藏面板样式 */
.favorites-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.favorites-list {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
}

.favorite-item {
  display: flex;
  gap: 12px;
  padding: 10px;
  background: #2a2a4a;
  border-radius: 8px;
  border: 1px solid #3a3a5a;
}

.favorite-media {
  position: relative;
  width: 100px;
  height: 60px;
  aspect-ratio: 16/9;
  flex-shrink: 0;
  overflow: hidden;
  border-radius: 6px;
  background: #1a1a2e;
  cursor: pointer;
}

.favorite-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.favorite-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.favorite-type {
  display: inline-block;
  padding: 2px 8px;
  background: #00d4ff;
  color: #000;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
  width: fit-content;
}

.favorite-prompt {
  color: #eee;
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.favorite-remove-btn {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #888;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.favorite-remove-btn:hover {
  background: rgba(255, 0, 0, 0.2);
  color: #ff4444;
}

.favorites-empty {
  text-align: center;
  padding: 60px 20px;
  color: #666;
  font-size: 0.95rem;
}

/* 模版编辑弹窗样式需要的基础样式 */
.template-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #1a1a2e;
  color: #fff;
  font-size: 0.9rem;
  margin-bottom: 8px;
  box-sizing: border-box;
}

.template-input:focus {
  outline: none;
  border-color: #00d4ff;
}

.template-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #1a1a2e;
  color: #fff;
  font-size: 0.9rem;
  margin-bottom: 8px;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;
}

.template-textarea:focus {
  outline: none;
  border-color: #00d4ff;
}

.template-options {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.template-option-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #aaa;
  font-size: 0.85rem;
  cursor: pointer;
}

.templates-empty {
  text-align: center;
  padding: 60px 20px;
  color: #666;
  font-size: 0.95rem;
}

/* 模版编辑弹窗 */
.template-editor-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.template-editor-content {
  background: #16213e;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid #333;
}

.template-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #333;
}

.template-editor-header h3 {
  margin: 0;
  color: #00d4ff;
}

.template-editor-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-editor-form label {
  color: #aaa;
  font-size: 0.85rem;
  margin-bottom: 4px;
}

.template-editor-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
