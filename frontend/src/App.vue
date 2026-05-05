<script setup>
import { ref, onMounted, onUnmounted, provide } from 'vue'
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
import { useRoom } from './composables/useRoom'
import { useChat } from './composables/useChat'
import { useFavorites } from './composables/useFavorites'
import { useTemplates } from './composables/useTemplates'
import { useWorkspace } from './composables/useWorkspace'
import { useSidePanel } from './composables/useSidePanel'
import { useResize } from './composables/useResize'
import { useSocketEvents } from './composables/useSocketEvents'
import { useToast } from './composables/useToast'

const toast = useToast()
const confirmDialog = ref(null)
const userId = ref('')
const unreadMessages = ref(0)

const {
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
} = useRoom({ toast })

const {
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
} = useWorkspace({ toast })

const {
  templates,
  showTemplateEditor,
  isAddingTemplate,
  editingTemplate,
  newTemplate,
  templatePanelSearch,
  filteredTemplatesForPanel,
  currentEditingTemplate,
  getTemplates,
  openAddTemplate,
  addTemplate,
  editTemplate,
  saveTemplateEdit,
  deleteTemplate,
  cancelTemplateEdit,
  registerSocketEvents: registerTemplateSocketEvents,
  unregisterSocketEvents: unregisterTemplateSocketEvents,
} = useTemplates({ toast, confirmDialog })

provide('templates', templates)

const {
  showSidePanel,
  activeSidePanel,
  toggleSidePanel,
} = useSidePanel({ templatePanelSearch, unreadMessages })

const {
  chatMessages,
  chatInput,
  chatMessagesRef,
  handleSendChatMessage,
  handleChatMessage,
  handleChatHistory,
  formatTime,
  registerSocketEvents: registerChatSocketEvents,
  unregisterSocketEvents: unregisterChatSocketEvents,
} = useChat({ userId, showSidePanel, activeSidePanel, unreadMessages })

const {
  favorites,
  favoriteModalVisible,
  favoriteModalType,
  favoriteModalUrl,
  toggleFavorite,
  isFavorite,
  getFavoriteDisplayUrl,
  handleFavoriteImageError,
  openFavoritePreview,
  closeFavoriteModal,
} = useFavorites()

const {
  leftPanelWidth,
  isResizing,
  handleMouseDown,
  cleanup: cleanupResize,
} = useResize()

const showFiveTV = ref(false)
const comparisonFullscreenVisible = ref(false)
const comparisonItem1 = ref(null)
const comparisonItem2 = ref(null)
const showInversionModal = ref(false)

const startComparison = (data) => {
  comparisonItem1.value = data.item1
  comparisonItem2.value = data.item2
  comparisonFullscreenVisible.value = true
}

const closeComparisonFullscreen = () => {
  comparisonFullscreenVisible.value = false
}

const handleInversionApply = (result) => {
  const currentWorkspace = activeTab.value === 'image' ? imageWorkspaceRef : videoWorkspaceRef
  if (currentWorkspace && currentWorkspace.value && currentWorkspace.value.setPrompt) {
    currentWorkspace.value.setPrompt(result.positive)
  }
}

const handleFiveTVClick = () => {
  showFiveTV.value = true
}

const handleExitFiveTV = () => {
  showFiveTV.value = false
}

const handleSelectTemplate = (template) => {
  const currentWorkspace = activeTab.value === 'image' ? imageWorkspaceRef.value : videoWorkspaceRef.value
  if (currentWorkspace && currentWorkspace.setPrompt) {
    currentWorkspace.setPrompt(template.content)
  }
}

const onJoinNewRoom = () => {
  joinNewRoom({ results, historyItems })
}

const { registerSocketListeners, unregisterSocketListeners } = useSocketEvents({
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
  registerTemplateEvents: registerTemplateSocketEvents,
  registerChatEvents: registerChatSocketEvents,
  unregisterTemplateEvents: unregisterTemplateSocketEvents,
  unregisterChatEvents: unregisterChatSocketEvents,
})

onMounted(() => {
  registerSocketListeners(
    (id) => { userId.value = id },
    getTemplates
  )
})

onUnmounted(() => {
  unregisterSocketListeners()
  cleanupResize()
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
          <h1 class="logo">🎨 Five Gen 2.4.5</h1>
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
            @keyup.enter="onJoinNewRoom"
            class="join-input"
          />
          <button @click="onJoinNewRoom" class="btn btn-small btn-primary">
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
