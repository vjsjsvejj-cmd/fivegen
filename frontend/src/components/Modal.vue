<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { API_BASE_URL } from '../utils/config.js'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  type: {
    type: String,
    default: 'image',
    validator: (v) => ['image', 'video'].includes(v)
  },
  url: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close'])

const mediaUrl = computed(() => {
  let url = props.url
  if (url.startsWith('/')) {
    url = `${API_BASE_URL}${url}`
  }
  return url
})

// 图片相关状态
const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const startX = ref(0)
const startY = ref(0)
const startTranslateX = ref(0)
const startTranslateY = ref(0)

// 缩放控制
const handleWheel = (e) => {
  if (props.type !== 'image') return
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(0.5, Math.min(10, scale.value + delta))
  scale.value = newScale
}

const zoomIn = () => {
  scale.value = Math.min(10, scale.value + 0.25)
}

const zoomOut = () => {
  scale.value = Math.max(0.5, scale.value - 0.25)
}

const reset = () => {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
}

// 拖拽控制
const handleMouseDown = (e) => {
  if (props.type !== 'image') return
  isDragging.value = true
  startX.value = e.clientX
  startY.value = e.clientY
  startTranslateX.value = translateX.value
  startTranslateY.value = translateY.value
}

const handleMouseMove = (e) => {
  if (!isDragging.value) return
  translateX.value = startTranslateX.value + (e.clientX - startX.value)
  translateY.value = startTranslateY.value + (e.clientY - startY.value)
}

const handleMouseUp = () => {
  isDragging.value = false
}

const handleMouseLeave = () => {
  isDragging.value = false
}

const close = () => {
  emit('close')
  // 关闭时重置状态
  setTimeout(() => {
    scale.value = 1
    translateX.value = 0
    translateY.value = 0
  }, 300)
}

const handleKeydown = (e) => {
  if (e.key === 'Escape' && props.visible) {
    close()
  }
}

const handleOverlayClick = (e) => {
  if (e.target === e.currentTarget) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
  document.addEventListener('mouseleave', handleMouseLeave)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
  document.removeEventListener('mouseleave', handleMouseLeave)
})
</script>

<template>
  <div 
    v-if="visible" 
    class="modal-overlay" 
    @click="handleOverlayClick"
  >
    <div class="modal-content">
      <button class="close-btn" @click="close">×</button>
      
      <!-- 图片控制按钮 -->
      <div v-if="type === 'image'" class="image-controls">
        <button class="control-btn" @click="zoomOut" title="缩小">−</button>
        <span class="scale-display">{{ Math.round(scale * 100) }}%</span>
        <button class="control-btn" @click="zoomIn" title="放大">+</button>
        <button class="control-btn reset-btn" @click="reset" title="重置">重置</button>
      </div>
      
      <div class="media-wrapper">
        <img 
          v-if="type === 'image'" 
          :src="mediaUrl" 
          alt="Preview"
          draggable="false"
          class="preview-image"
          :class="{ 'dragging': isDragging }"
          :style="{
            transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
            cursor: isDragging ? 'grabbing' : 'grab'
          }"
          @wheel="handleWheel"
          @mousedown="handleMouseDown"
        />
        <video 
          v-else
          :src="mediaUrl"
          controls
          autoplay
        ></video>
      </div>
      
      <!-- 图片操作提示 -->
      <div v-if="type === 'image'" class="hint-text">
        鼠标滚轮缩放 | 拖拽移动 | ESC 关闭
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 95vw;
  max-height: 95vh;
}

.close-btn {
  position: absolute;
  top: -50px;
  right: 0;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 10;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: rotate(90deg);
}

/* 图片控制按钮 */
.image-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  background: rgba(0, 0, 0, 0.6);
  padding: 8px 16px;
  border-radius: 30px;
}

.control-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.control-btn.reset-btn {
  font-size: 12px;
  width: auto;
  padding: 0 12px;
  border-radius: 16px;
}

.scale-display {
  color: #fff;
  font-size: 14px;
  font-weight: bold;
  min-width: 60px;
  text-align: center;
}

.media-wrapper {
  max-width: 95vw;
  max-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.preview-image {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 8px;
  transition: transform 0.1s ease-out;
  user-select: none;
}

.preview-image.dragging {
  transition: none;
}

.media-wrapper video {
  max-width: 100%;
  max-height: 80vh;
  border-radius: 8px;
}

.hint-text {
  margin-top: 15px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  text-align: center;
}
</style>
