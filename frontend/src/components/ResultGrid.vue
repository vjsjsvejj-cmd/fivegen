<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import Modal from './Modal.vue'
import { API_BASE_URL } from '../utils/config.js'
import { ANIMATION_MODE } from '../config/animation.js'

const props = defineProps({
  results: {
    type: Array,
    default: () => []
  },
  progressList: {
    type: Array,
    default: () => []
  },
  favorites: {
    type: Array,
    default: () => []
  },
  isFavorite: {
    type: Function,
    default: () => false
  }
})

const emit = defineEmits(['re-edit', 'download', 'toggle-favorite', 'cancel-task'])

// 跟踪新结果项，用于动画
const newResultIds = ref(new Set())
const previousResultsLength = ref(0)
const previousResults = ref([])

// 监听 results 变化，标记新结果
const isInitialized = ref(false)
watch(() => props.results, (newResults, oldResults) => {
  if (!isInitialized.value) {
    // 初始化时，不标记任何结果为新结果
    isInitialized.value = true
    previousResults.value = [...newResults]
    return
  }
  
  if (newResults.length > previousResults.value.length) {
    // 找出新添加的结果
    const oldIds = new Set(previousResults.value.map(i => i?.task_id))
    const newItems = newResults.filter(item => !oldIds.has(item?.task_id))
    
    newItems.forEach(item => {
      if (item && item.task_id) {
        newResultIds.value.add(item.task_id)
        // 5秒后移除新标记
        setTimeout(() => {
          newResultIds.value.delete(item.task_id)
        }, 5000)
      }
    })
  }
  
  previousResults.value = [...newResults]
}, { deep: true })

// 检查是否是新结果
const isNewResult = (item) => {
  return newResultIds.value.has(item.task_id)
}

// 获取动画类
const getAnimationClass = (item) => {
  if (!isNewResult(item) || ANIMATION_MODE === 'none') {
    return '';
  }
  return ANIMATION_MODE;
}

// 拖拽结果卡片
const handleResultDragStart = (e, item) => {
  e.dataTransfer.setData('text/plain', JSON.stringify(item));
  e.dataTransfer.effectAllowed = 'copy';
}

// 计时器，存储每个任务的开始时间
const taskStartTimes = ref(new Map())
const currentTime = ref(Date.now())
let timerInterval = null

// 格式化时间显示：X小时X分钟X秒
const formatElapsedTime = (startTime) => {
  const elapsed = Math.floor((currentTime.value - startTime) / 1000)
  const hours = Math.floor(elapsed / 3600)
  const minutes = Math.floor((elapsed % 3600) / 60)
  const seconds = elapsed % 60
  
  let result = ''
  if (hours > 0) {
    result += `${hours}小时`
  }
  if (minutes > 0 || hours > 0) {
    result += `${minutes}分钟`
  }
  result += `${seconds}秒`
  return result
}

// 格式化创建时间：显示为本地时间
const formatCreatedAt = (timestamp) => {
  if (!timestamp) return ''
  let date
  if (typeof timestamp === 'number') {
    // 时间戳格式（秒）
    date = new Date(timestamp * 1000)
  } else {
    // ISO 格式字符串
    date = new Date(timestamp)
  }
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 监听 progressList，记录开始时间
const updateStartTimes = () => {
  const now = Date.now()
  props.progressList.forEach(item => {
    if (!taskStartTimes.value.has(item.task_id)) {
      taskStartTimes.value.set(item.task_id, now)
    }
  })
  // 清理已完成任务的时间记录
  const completedTaskIds = new Set(props.results.map(r => r.task_id))
  taskStartTimes.value.forEach((_, taskId) => {
    if (!props.progressList.find(p => p.task_id === taskId)) {
      taskStartTimes.value.delete(taskId)
    }
  })
}

const formatPrompt = (text) => {
  if (!text) return ''
  let escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  escaped = escaped.replace(/@图片(\d+)/g, '<span style="color: #00d4ff; font-weight: bold;">@图片$1</span>')
  escaped = escaped.replace(/@视频(\d+)/g, '<span style="color: #ff4444; font-weight: bold;">@视频$1</span>')
  escaped = escaped.replace(/@音频(\d+)/g, '<span style="color: #00ff88; font-weight: bold;">@音频$1</span>')
  escaped = escaped.replace(/@首帧/g, '<span style="color: #00d4ff; font-weight: bold;">@首帧</span>')
  escaped = escaped.replace(/@尾帧/g, '<span style="color: #ff4444; font-weight: bold;">@尾帧</span>')
  return escaped
}

const getDisplayPrompt = (result) => {
  // 优先使用用户友好的 displayPrompt
  return result.params.displayPrompt || result.params.prompt || ''
}

// 获取模型显示名称
const getModelDisplayName = (modelKey) => {
  if (!modelKey) return ''
  const modelNames = {
    'gpt-image-2': 'GPT Image 2',
    'nano-banana-2': 'Nano Banana 2',
    'nano-banana-2-cl': 'Nano Banana 2 CL',
    'nano-banana-2-4k-cl': 'Nano Banana 2 4K CL',
    'nano-banana-pro': 'Nano Banana Pro',
    'nano-banana-pro-cl': 'Nano Banana Pro CL',
    'nano-banana-pro-4k-vip': 'Nano Banana Pro 4K VIP',
    'seedream-5-0-lite': 'Seedream 5.0 Lite',
    'seedance-2-0': 'Seedance 2.0'
  }
  return modelNames[modelKey] || modelKey
}

// 合并显示列表：先显示进度项（最新的在前），再显示结果项
const displayList = computed(() => {
  updateStartTimes()
  // 进度项反转顺序，最新的在最前面
  const reversedProgress = [...props.progressList].reverse()
  return [...reversedProgress, ...props.results]
})

const modalVisible = ref(false)
const modalType = ref('image')
const modalUrl = ref('')

const handleReEdit = (result) => {
  emit('re-edit', result)
}

const handleDragStart = (e, result) => {
  // 优先用远程URL
  const dragUrl = result.remote_url || result.url
  const dragData = {
    task_id: result.task_id,
    type: result.type,
    url: dragUrl,
    params: {
      model: result.params.model,
      aspect_ratio: result.params.aspect_ratio,
      resolution: result.params.resolution,
      prompt: result.params.prompt,
      reference_images: result.params.reference_images,
      mode: result.params.mode,
      duration: result.params.duration,
      first_frame: result.params.first_frame,
      last_frame: result.params.last_frame,
      multimodal_files: result.params.multimodal_files
    }
  }
  e.dataTransfer.setData('text/plain', JSON.stringify(dragData))
}

const openPreview = (result) => {
  modalType.value = result.type === 'video' ? 'video' : 'image'
  // 优先用远程URL，没有才用本地URL
  const previewUrl = result.remote_url || result.url
  modalUrl.value = previewUrl.startsWith('/') ? `${API_BASE_URL}${previewUrl}` : previewUrl
  modalVisible.value = true
}

const closeModal = () => {
  modalVisible.value = false
}

const handleImageError = (event, result) => {
  // 如果本地图片加载失败，尝试使用远程URL
  if (result.remote_url && event.target.src !== result.remote_url) {
    event.target.src = result.remote_url
  }
}

const getDisplayUrl = (result) => {
  if (result.type === 'video') {
    return result.thumbnail || result.url
  }
  // 图片：优先用本地URL，失败时自动回退到远程URL
  // 注意：result.url 通常是本地路径，result.remote_url 是TOS路径
  const displayUrl = result.url || result.remote_url
  return displayUrl.startsWith('/') ? `${API_BASE_URL}${displayUrl}` : displayUrl
}

const handleDownload = async (result) => {
  if (result.type === 'image') {
    // 图片下载：优先用本地URL，否则用远程URL
    const downloadUrl = result.url || result.remote_url
    const finalDownloadUrl = downloadUrl.startsWith('/') ? `${API_BASE_URL}${downloadUrl}` : downloadUrl
    const fileName = result.displayName || `fivetv-${result.task_id.substring(0, 8)}.png`
    
    try {
      // 方法1：尝试 blob 方式下载（解决跨域问题）
      const response = await fetch(finalDownloadUrl)
      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = fileName
        a.click()
        URL.revokeObjectURL(url)
        return
      }
    } catch (error) {
      console.warn('Blob下载失败，尝试备用方式:', error)
    }
    
    // 方法2：备用方式 - 直接打开
    try {
      const a = document.createElement('a')
      a.href = finalDownloadUrl
      a.download = fileName
      a.target = '_blank'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (error) {
      console.error('备用下载方式也失败:', error)
      alert('下载失败，请右键点击图片 -> 另存为')
    }
  } else {
    // 视频下载
    try {
      const videoUrl = result.url.startsWith('/') 
        ? `${API_BASE_URL}${result.url}` 
        : result.url
      
      const response = await fetch(videoUrl, { method: 'HEAD' })
      
      if (response.ok) {
        const a = document.createElement('a')
        a.href = videoUrl
        a.download = result.displayName || `video-${result.task_id.substring(0, 6)}.mp4`
        a.click()
      } else {
        alert('⚠️ 示例视频文件暂不可用！\n\n请在 backend/static/ 目录中放置 sample.mp4 文件\n\n详情请查看 backend/static/README.md')
      }
    } catch (error) {
      console.error('下载视频失败:', error)
      alert('⚠️ 视频下载失败，请右键点击视频 -> 另存为')
    }
  }
}

// 启动计时器
const startTimer = () => {
  timerInterval = setInterval(() => {
    currentTime.value = Date.now()
  }, 1000)
}

// 停止计时器
const stopTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

// 生命周期钩子
onMounted(() => {
  startTimer()
})

onUnmounted(() => {
  stopTimer()
})
</script>

<template>
  <div class="result-grid">
    <!-- 显示进度项和结果项，进度项最新的在最上面 -->
    <div 
      v-for="(item, index) in displayList" 
      :key="item?.task_id || `progress-${item.type}-${index}`" 
      :class="['grid-card', { 
        'progress-card': item.progress !== undefined, 
        'result-card': item.progress === undefined 
      }, getAnimationClass(item)]"
      :draggable="item.progress === undefined"
      @dragstart="item.progress === undefined && handleDragStart($event, item)"
    >
      <!-- 进度卡片 -->
      <div v-if="item.progress !== undefined" class="progress-card-content">
        <div class="spinner"></div>
        <div class="progress-text">{{ item.type === 'video' ? '生成视频中...' : '生成图片中...' }}</div>
        <div class="elapsed-time">⏱️ {{ formatElapsedTime(taskStartTimes.get(item.task_id) || Date.now()) }}</div>
        <button @click="emit('cancel-task', item)" class="cancel-btn">🚫 取消</button>
      </div>

      <!-- 结果卡片 -->
          <template v-else>
            <div 
              class="result-media" 
              @click="openPreview(item)"
              :draggable="true"
              @dragstart="handleResultDragStart($event, item)"
            >
              <button 
                class="favorite-btn" 
                @click.stop="emit('toggle-favorite', item)"
                :class="{ 'favorited': props.isFavorite(item) }"
              >
                {{ props.isFavorite(item) ? '⭐' : '☆' }}
              </button>
              <img 
                :src="getDisplayUrl(item)" 
                :alt="item.params.prompt"
                @error="(e) => handleImageError(e, item)"
              />
              <div v-if="item.type === 'video'" class="video-badge">🎬</div>
            </div>
            <div class="result-info">
              <div v-if="item.displayName" class="result-name" :title="item.displayName">{{ item.displayName }}</div>
              <div 
                class="result-prompt" 
                :title="getDisplayPrompt(item)"
                v-html="formatPrompt(getDisplayPrompt(item))"
              ></div>
              <div class="result-meta">
                <div class="meta-row">
                  <span class="result-type">{{ item.type === 'video' ? '视频' : '图片' }}</span>
                  <span class="created-time">{{ formatCreatedAt(item.created_at) }}</span>
                </div>
                <div class="meta-row details">
                  <!-- 图片显示：模型、耗时、画面比例、清晰度 -->
                  <template v-if="item.type === 'image'">
                    <span v-if="item.params.model">{{ getModelDisplayName(item.params.model) }}</span>
                    <span v-if="item.duration">⏱️ {{ item.duration }}s</span>
                    <span v-if="item.params.aspect_ratio">{{ item.params.aspect_ratio }}</span>
                    <span v-if="item.params.resolution">{{ item.params.resolution }}</span>
                  </template>
                  <!-- 视频显示：模型、画面比例、清晰度、随机种子、耗时、token数 -->
                  <template v-else>
                    <span v-if="item.params.model">{{ getModelDisplayName(item.params.model) }}</span>
                    <span v-if="item.params.aspect_ratio">{{ item.params.aspect_ratio }}</span>
                    <span v-if="item.params.resolution">{{ item.params.resolution }}</span>
                    <span v-if="item.seed">🎲 {{ item.seed }}</span>
                    <span v-if="item.duration">⏱️ {{ item.duration }}s</span>
                    <span v-if="item.total_tokens">💎 {{ item.total_tokens }}</span>
                  </template>
                </div>
              </div>
              <div class="result-actions">
                <button @click.stop="handleDownload(item)" class="download-btn">⬇️ 下载</button>
                <button @click.stop="handleReEdit(item)" class="re-edit-btn">🔄 重编辑</button>
              </div>
            </div>
          </template>
    </div>

    <!-- 空状态 -->
    <div v-if="results.length === 0 && progressList.length === 0" class="empty-state">
      <div class="empty-icon">🎨</div>
      <div class="empty-text">还没有生成结果</div>
      <div class="empty-hint">在左侧工作台开始创作吧！</div>
    </div>

    <Modal 
      :visible="modalVisible" 
      :type="modalType" 
      :url="modalUrl" 
      @close="closeModal"
    />
  </div>
</template>

<style scoped>
.result-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  padding: 20px;
}

/* 通用网格卡片 */
.grid-card {
  background: #2a2a4a;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
}

/* 进度卡片 */
.progress-card {
  border: 2px dashed #00d4ff;
  opacity: 0.8;
}

.progress-card-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 280px;
}

/* 旋转小圈圈 */
.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #1a1a2e;
  border-top: 4px solid #00d4ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.progress-text {
  color: #ccc;
  margin-bottom: 10px;
  font-size: 1rem;
}

.elapsed-time {
  color: #00d4ff;
  font-weight: bold;
  font-size: 0.95rem;
  margin-bottom: 15px;
}

.cancel-btn {
  padding: 10px 24px;
  font-size: 0.95rem;
  background: #4a4a6a;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn:hover {
  background: #5a5a7a;
}

/* 结果卡片 */
.result-card {
  border: 2px solid #3a3a5a;
  cursor: grab;
}

.result-card:hover {
  border-color: #00d4ff;
}

.result-card:active {
  cursor: grabbing;
}

.result-media {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  overflow: hidden;
  background: #1a1a2e;
  cursor: pointer;
}

.favorite-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.favorite-btn:hover {
  background: rgba(0, 0, 0, 0.8);
  transform: scale(1.1);
}

.favorite-btn.favorited {
  color: #ffd700;
  background: rgba(255, 215, 0, 0.2);
}

.result-media:hover {
  background: #3a3a5a;
}

.result-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-badge {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(0, 212, 255, 0.9);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9rem;
}

.result-info {
  padding: 15px;
}

.result-name {
  color: #00d4ff;
  font-size: 0.95rem;
  font-weight: bold;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-prompt {
  color: #eee;
  font-size: 0.9rem;
  margin-bottom: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.result-meta {
  margin-bottom: 12px;
}

.meta-row {
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
}

.meta-row.details {
  color: #888;
  font-size: 0.8rem;
  flex-wrap: wrap;
}

.meta-row.stats {
  color: #aaa;
  font-size: 0.75rem;
}

.task-id {
  color: #666;
  font-family: monospace;
  font-size: 0.75rem;
}

.result-type {
  background: #00d4ff;
  color: #000;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
}

.result-actions {
  display: flex;
  gap: 8px;
}

.download-btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: #1a6b1a;
  color: #fff;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.download-btn:hover {
  background: #2a8b2a;
}

.re-edit-btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: #4a4a6a;
  color: #eee;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.re-edit-btn:hover {
  background: #00d4ff;
  color: #000;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 15px;
}

.empty-text {
  color: #888;
  font-size: 1.2rem;
  margin-bottom: 8px;
}

.empty-hint {
  color: #555;
  font-size: 0.95rem;
}

@media (max-width: 1200px) {
  .result-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 800px) {
  .result-grid {
    grid-template-columns: 1fr;
  }
}

/* ==================== 动画效果 ==================== */

/* 方案1：弹出脉冲+渐变边框 */
.grid-card.pop-pulse {
  animation: popPulse 0.8s ease-out, gradientBorder 3s linear infinite;
  position: relative;
  z-index: 10;
}

@keyframes popPulse {
  0% {
    transform: scale(0.7);
    opacity: 0;
  }
  50% {
    transform: scale(1.08);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes gradientBorder {
  0%, 100% {
    box-shadow: 0 0 30px rgba(0, 212, 255, 0.8), 
                0 0 60px rgba(138, 43, 226, 0.6),
                inset 0 0 30px rgba(0, 212, 255, 0.3);
    border-color: #00d4ff;
  }
  33% {
    box-shadow: 0 0 30px rgba(138, 43, 226, 0.8), 
                0 0 60px rgba(255, 105, 180, 0.6),
                inset 0 0 30px rgba(138, 43, 226, 0.3);
    border-color: #8a2be2;
  }
  66% {
    box-shadow: 0 0 30px rgba(255, 105, 180, 0.8), 
                0 0 60px rgba(0, 212, 255, 0.6),
                inset 0 0 30px rgba(255, 105, 180, 0.3);
    border-color: #ff69b4;
  }
}

/* 方案2：飘带闪烁+跳动 */
.grid-card.streamer-bounce {
  animation: bounceGlow 1.5s ease-in-out infinite, streamerBorder 2s linear infinite;
  position: relative;
}

@keyframes bounceGlow {
  0%, 100% {
    transform: translateY(0) scale(1);
  }
  50% {
    transform: translateY(-5px) scale(1.02);
  }
}

@keyframes streamerBorder {
  0%, 100% {
    border-color: #00d4ff;
    box-shadow: 0 0 15px #00d4ff;
  }
  25% {
    border-color: #ff6b9d;
    box-shadow: 0 0 15px #ff6b9d;
  }
  50% {
    border-color: #c44dff;
    box-shadow: 0 0 15px #c44dff;
  }
  75% {
    border-color: #4dffb8;
    box-shadow: 0 0 15px #4dffb8;
  }
}

.grid-card.streamer-bounce::before,
.grid-card.streamer-bounce::after {
  content: '✨';
  position: absolute;
  font-size: 1.2rem;
  animation: sparkle 1s ease-in-out infinite;
}

.grid-card.streamer-bounce::before {
  top: -10px;
  left: -10px;
}

.grid-card.streamer-bounce::after {
  bottom: -10px;
  right: -10px;
  animation-delay: 0.5s;
}

@keyframes sparkle {
  0%, 100% {
    opacity: 0;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}

/* 方案3：优雅上浮 */
.grid-card.elegant-float {
  animation: floatUp 0.8s ease-out, elegantGlow 4s ease-in-out infinite;
}

@keyframes floatUp {
  0% {
    transform: translateY(20px);
    opacity: 0;
  }
  100% {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes elegantGlow {
  0%, 100% {
    box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
  }
  50% {
    box-shadow: 0 10px 40px rgba(0, 212, 255, 0.2);
  }
}

/* 方案4：霓虹跑马灯 */
.grid-card.neon-border {
  animation: neonPop 0.5s ease-out;
  position: relative;
  overflow: hidden;
}

@keyframes neonPop {
  0% {
    transform: scale(0.95);
    opacity: 0;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.grid-card.neon-border::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(90deg, #00d4ff, #ff6b9d, #c44dff, #4dffb8, #00d4ff);
  background-size: 400% 400%;
  z-index: -1;
  border-radius: 14px;
  animation: neonBorder 3s linear infinite;
}

@keyframes neonBorder {
  0% {
    background-position: 0% 50%;
  }
  100% {
    background-position: 400% 50%;
  }
}

.grid-card.neon-border::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  right: 2px;
  bottom: 2px;
  background: #2a2a4a;
  border-radius: 10px;
  z-index: -1;
}
</style>
