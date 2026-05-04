<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  item1: {
    type: Object,
    default: null
  },
  item2: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// 布局：'vertical' 上下 | 'horizontal' 左右
const layout = ref('vertical')

// 图片缩放和位移
const zoom1 = ref(1)
const pan1 = ref({ x: 0, y: 0 })
const zoom2 = ref(1)
const pan2 = ref({ x: 0, y: 0 })

// 视频状态
const video1Ref = ref(null)
const video2Ref = ref(null)
const isPlaying1 = ref(false)
const isPlaying2 = ref(false)
const volume1 = ref(1)
const volume2 = ref(1)

// 切换布局
const toggleLayout = () => {
  layout.value = layout.value === 'vertical' ? 'horizontal' : 'vertical'
}

// 获取显示URL
const getDisplayUrl = (item) => {
  if (!item) return ''
  if (item.type === 'video') {
    const url = item.url
    return url.startsWith('/') ? `${API_BASE_URL}${url}` : url
  }
  const url = item.url || item.remote_url
  return url.startsWith('/') ? `${API_BASE_URL}${url}` : url
}

// 图片缩放控制
const zoomIn = (index) => {
  if (index === 1) {
    zoom1.value = Math.min(zoom1.value + 0.25, 5)
  } else {
    zoom2.value = Math.min(zoom2.value + 0.25, 5)
  }
}

const zoomOut = (index) => {
  if (index === 1) {
    zoom1.value = Math.max(zoom1.value - 0.25, 0.5)
    pan1.value = { x: 0, y: 0 }
  } else {
    zoom2.value = Math.max(zoom2.value - 0.25, 0.5)
    pan2.value = { x: 0, y: 0 }
  }
}

const resetZoom = (index) => {
  if (index === 1) {
    zoom1.value = 1
    pan1.value = { x: 0, y: 0 }
  } else {
    zoom2.value = 1
    pan2.value = { x: 0, y: 0 }
  }
}

// 视频控制
const togglePlay = (index) => {
  if (index === 1 && video1Ref.value) {
    if (isPlaying1.value) {
      video1Ref.value.pause()
    } else {
      video1Ref.value.play()
    }
    isPlaying1.value = !isPlaying1.value
  }
  if (index === 2 && video2Ref.value) {
    if (isPlaying2.value) {
      video2Ref.value.pause()
    } else {
      video2Ref.value.play()
    }
    isPlaying2.value = !isPlaying2.value
  }
}

const setVolume = (index, value) => {
  if (index === 1) {
    volume1.value = value
    if (video1Ref.value) {
      video1Ref.value.volume = value
    }
  } else {
    volume2.value = value
    if (video2Ref.value) {
      video2Ref.value.volume = value
    }
  }
}

// 保存截图
const saveScreenshot = async () => {
  try {
    const container = document.createElement('canvas')
    const ctx = container.getContext('2d')
    
    const isVertical = layout.value === 'vertical'
    const containerWidth = window.innerWidth
    const containerHeight = window.innerHeight - 80 // 减去标题栏
    
    if (isVertical) {
      container.width = containerWidth
      container.height = containerHeight
    } else {
      container.width = containerWidth
      container.height = containerHeight
    }
    
    // 填充背景
    ctx.fillStyle = '#0f0f23'
    ctx.fillRect(0, 0, container.width, container.height)
    
    // 获取两个媒体元素
    const media1 = document.getElementById('comparison-media-1')
    const media2 = document.getElementById('comparison-media-2')
    
    if (media1 && media2) {
      // 简单的截图实现 - 实际项目中可以用 html2canvas
      alert('💡 截图功能需要安装 html2canvas 库才能完美实现！\n当前已为你标记截图区域，请使用系统截图工具进行截图。')
      
      // 临时高亮一下
      const items = document.querySelectorAll('.comparison-item')
      items.forEach(el => {
        el.style.boxShadow = '0 0 0 3px #00d4ff'
        setTimeout(() => {
          el.style.boxShadow = ''
        }, 2000)
      })
    }
  } catch (e) {
    console.error('截图失败', e)
    alert('截图失败，请使用浏览器自带的截图功能')
  }
}

// 图片拖拽平移
let isDragging = false
let dragStartX = 0
let dragStartY = 0
let startPanX = 0
let startPanY = 0
let activeItem = 0

const startPan = (index, e) => {
  isDragging = true
  activeItem = index
  dragStartX = e.clientX
  dragStartY = e.clientY
  if (index === 1) {
    startPanX = pan1.value.x
    startPanY = pan1.value.y
  } else {
    startPanX = pan2.value.x
    startPanY = pan2.value.y
  }
}

const doPan = (e) => {
  if (!isDragging) return
  const dx = e.clientX - dragStartX
  const dy = e.clientY - dragStartY
  
  if (activeItem === 1) {
    pan1.value = {
      x: startPanX + dx,
      y: startPanY + dy
    }
  } else {
    pan2.value = {
      x: startPanX + dx,
      y: startPanY + dy
    }
  }
}

const endPan = () => {
  isDragging = false
  activeItem = 0
}
</script>

<template>
  <div v-if="visible" class="comparison-modal" @mousemove="doPan" @mouseup="endPan" @mouseleave="endPan">
    <div class="modal-header">
      <h2>🔍 对比工具</h2>
      <div class="header-controls">
        <button class="layout-btn" @click="toggleLayout" :title="layout === 'vertical' ? '切换为左右布局' : '切换为上下布局'">
          {{ layout === 'vertical' ? '↕️ 上下' : '↔️ 左右' }}
        </button>
        <button class="screenshot-btn" @click="saveScreenshot" title="保存对比截图">📸 截图</button>
        <button class="close-btn" @click="$emit('close')">✕ 关闭</button>
      </div>
    </div>
    
    <div class="modal-content" :class="layout">
      <!-- 第一个对比项 -->
      <div class="comparison-item">
        <div class="item-header">
          <span class="item-label">1</span>
          <span class="item-info">
            {{ item1?.type === 'video' ? '视频' : '图片' }}
            {{ item1?.displayName || (item1?.params?.prompt ? item1.params.prompt.substring(0, 15) + '...' : '') }}
          </span>
        </div>
        
        <div class="item-media-container" 
             @mousedown="item1?.type === 'image' ? startPan(1, $event) : null"
             :style="{ cursor: item1?.type === 'image' ? 'grab' : 'default' }"
        >
          <!-- 图片 -->
          <template v-if="item1?.type === 'image'">
            <img 
              id="comparison-media-1"
              :src="getDisplayUrl(item1)" 
              :style="{
                transform: `scale(${zoom1}) translate(${pan1.x/zoom1}px, ${pan1.y/zoom1}px)`,
                transformOrigin: 'center center'
              }"
              draggable="false"
            />
          </template>
          
          <!-- 视频 -->
          <template v-else-if="item1?.type === 'video'">
            <video 
              id="comparison-media-1"
              ref="video1Ref"
              :src="getDisplayUrl(item1)"
              controls
              :style="{ maxHeight: 'calc(100vh - 200px)' }"
              @play="isPlaying1 = true"
              @pause="isPlaying1 = false"
            ></video>
          </template>
        </div>
        
        <!-- 图片控制栏 -->
        <div v-if="item1?.type === 'image'" class="item-controls">
          <button @click="zoomOut(1)" title="缩小">➖</button>
          <span class="zoom-level">{{ Math.round(zoom1 * 100) }}%</span>
          <button @click="zoomIn(1)" title="放大">➕</button>
          <button @click="resetZoom(1)" title="重置">🔄 重置</button>
        </div>
      </div>
      
      <!-- 分割线 -->
      <div class="divider-line"></div>
      
      <!-- 第二个对比项 -->
      <div class="comparison-item">
        <div class="item-header">
          <span class="item-label">2</span>
          <span class="item-info">
            {{ item2?.type === 'video' ? '视频' : '图片' }}
            {{ item2?.displayName || (item2?.params?.prompt ? item2.params.prompt.substring(0, 15) + '...' : '') }}
          </span>
        </div>
        
        <div class="item-media-container" 
             @mousedown="item2?.type === 'image' ? startPan(2, $event) : null"
             :style="{ cursor: item2?.type === 'image' ? 'grab' : 'default' }"
        >
          <!-- 图片 -->
          <template v-if="item2?.type === 'image'">
            <img 
              id="comparison-media-2"
              :src="getDisplayUrl(item2)" 
              :style="{
                transform: `scale(${zoom2}) translate(${pan2.x/zoom2}px, ${pan2.y/zoom2}px)`,
                transformOrigin: 'center center'
              }"
              draggable="false"
            />
          </template>
          
          <!-- 视频 -->
          <template v-else-if="item2?.type === 'video'">
            <video 
              id="comparison-media-2"
              ref="video2Ref"
              :src="getDisplayUrl(item2)"
              controls
              :style="{ maxHeight: 'calc(100vh - 200px)' }"
              @play="isPlaying2 = true"
              @pause="isPlaying2 = false"
            ></video>
          </template>
        </div>
        
        <!-- 图片控制栏 -->
        <div v-if="item2?.type === 'image'" class="item-controls">
          <button @click="zoomOut(2)" title="缩小">➖</button>
          <span class="zoom-level">{{ Math.round(zoom2 * 100) }}%</span>
          <button @click="zoomIn(2)" title="放大">➕</button>
          <button @click="resetZoom(2)" title="重置">🔄 重置</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.comparison-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #0f0f23;
  z-index: 9999;
  display: flex;
  flex-direction: column;
}

.modal-header {
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  border-bottom: 1px solid #2a2a4a;
  background: #1a1a2e;
}

.modal-header h2 {
  margin: 0;
  color: #fff;
  font-size: 1.3rem;
}

.header-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.layout-btn,
.screenshot-btn,
.close-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.layout-btn {
  background: #2a2a4a;
  color: #fff;
}

.layout-btn:hover {
  background: #3a3a5a;
}

.screenshot-btn {
  background: linear-gradient(90deg, #00d4ff, #c44dff);
  color: #fff;
}

.screenshot-btn:hover {
  transform: scale(1.05);
}

.close-btn {
  background: #ff6b6b;
  color: #fff;
}

.close-btn:hover {
  background: #ff5252;
}

.modal-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.modal-content.vertical {
  flex-direction: column;
}

.modal-content.horizontal {
  flex-direction: row;
}

.comparison-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.item-header {
  padding: 15px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #2a2a4a;
}

.item-label {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #00d4ff, #c44dff);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.item-info {
  color: #aaa;
  font-size: 0.95rem;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-media-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #1a1a2e;
}

.item-media-container img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.item-media-container video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.item-controls {
  padding: 12px 20px;
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: center;
  border-top: 1px solid #2a2a4a;
  background: #1a1a2e;
}

.item-controls button {
  padding: 6px 12px;
  background: #2a2a4a;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}

.item-controls button:hover {
  background: #3a3a5a;
}

.zoom-level {
  color: #888;
  font-size: 0.9rem;
  min-width: 50px;
  text-align: center;
}

.divider-line {
  background: #2a2a4a;
}

.modal-content.vertical .divider-line {
  height: 2px;
  width: 100%;
}

.modal-content.horizontal .divider-line {
  width: 2px;
  height: 100%;
}
</style>