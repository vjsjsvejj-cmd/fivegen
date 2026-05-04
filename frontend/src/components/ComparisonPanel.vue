<script setup>
import { ref, computed } from 'vue'
import { getDisplayUrl, handleImageError } from '../utils/media.js'

const emit = defineEmits(['close', 'startComparison'])

const item1 = ref(null)
const item2 = ref(null)

// 拖拽状态
const dragOver1 = ref(false)
const dragOver2 = ref(false)

const isReady = computed(() => item1.value && item2.value)

// 处理拖拽开始（从结果网格拖过来）
const handleDragStart = (e, item) => {
  e.dataTransfer.setData('text/plain', JSON.stringify(item))
}

// 处理拖拽到区域1
const handleDragOver1 = (e) => {
  e.preventDefault()
  dragOver1.value = true
}

const handleDragLeave1 = () => {
  dragOver1.value = false
}

const handleDrop1 = (e) => {
  e.preventDefault()
  dragOver1.value = false
  const data = e.dataTransfer.getData('text/plain')
  if (data) {
    try {
      item1.value = JSON.parse(data)
    } catch (e) {
      console.error('解析失败', e)
    }
  }
}

// 处理拖拽到区域2
const handleDragOver2 = (e) => {
  e.preventDefault()
  dragOver2.value = true
}

const handleDragLeave2 = () => {
  dragOver2.value = false
}

const handleDrop2 = (e) => {
  e.preventDefault()
  dragOver2.value = false
  const data = e.dataTransfer.getData('text/plain')
  if (data) {
    try {
      item2.value = JSON.parse(data)
    } catch (e) {
      console.error('解析失败', e)
    }
  }
}

// 清除
const clearItem1 = () => {
  item1.value = null
}

const clearItem2 = () => {
  item2.value = null
}

// 开始对比
const startComparison = () => {
  if (item1.value && item2.value) {
    emit('startComparison', {
      item1: item1.value,
      item2: item2.value
    })
    emit('close')
  }
}
</script>

<template>
  <div class="comparison-panel">
    <div class="panel-header">
      <h3>🔍 对比工具</h3>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>
    
    <div class="panel-content">
      <div class="drop-zone" 
           :class="{ 'drag-over': dragOver1, 'has-content': item1 }"
           @dragover="handleDragOver1"
           @dragleave="handleDragLeave1"
           @drop="handleDrop1"
      >
        <template v-if="!item1">
          <div class="drop-icon">📥</div>
          <div class="drop-text">请拖拽到这里</div>
          <div class="drop-hint">从结果网格中拖入第1张图/视频</div>
        </template>
        <template v-else>
          <div class="item-preview">
            <div class="preview-media">
              <img :src="getDisplayUrl(item1)" alt="" />
              <div v-if="item1.type === 'video'" class="video-badge">🎬</div>
            </div>
            <div class="preview-info">
              <span class="item-type">{{ item1.type === 'video' ? '视频' : '图片' }}</span>
              <span class="item-name" :title="item1.displayName || item1.params?.prompt">{{ item1.displayName || (item1.params?.prompt ? item1.params.prompt.substring(0, 20) + '...' : '未命名') }}</span>
            </div>
            <button class="clear-btn" @click.stop="clearItem1">×</button>
          </div>
        </template>
      </div>

      <div class="divider">
        <span>VS</span>
      </div>

      <div class="drop-zone" 
           :class="{ 'drag-over': dragOver2, 'has-content': item2 }"
           @dragover="handleDragOver2"
           @dragleave="handleDragLeave2"
           @drop="handleDrop2"
      >
        <template v-if="!item2">
          <div class="drop-icon">📥</div>
          <div class="drop-text">请拖拽到这里</div>
          <div class="drop-hint">从结果网格中拖入第2张图/视频</div>
        </template>
        <template v-else>
          <div class="item-preview">
            <div class="preview-media">
              <img :src="getDisplayUrl(item2)" alt="" />
              <div v-if="item2.type === 'video'" class="video-badge">🎬</div>
            </div>
            <div class="preview-info">
              <span class="item-type">{{ item2.type === 'video' ? '视频' : '图片' }}</span>
              <span class="item-name" :title="item2.displayName || item2.params?.prompt">{{ item2.displayName || (item2.params?.prompt ? item2.params.prompt.substring(0, 20) + '...' : '未命名') }}</span>
            </div>
            <button class="clear-btn" @click.stop="clearItem2">×</button>
          </div>
        </template>
      </div>
    </div>

    <div class="panel-footer">
      <button 
        class="start-btn" 
        :disabled="!isReady"
        @click="startComparison"
      >
        🚀 开始对比
      </button>
    </div>
  </div>
</template>

<style scoped>
.comparison-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1a1a2e;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #2a2a4a;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #fff;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #888;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #2a2a4a;
  color: #fff;
}

.panel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow-y: auto;
}

.drop-zone {
  flex: 1;
  min-height: 180px;
  border: 2px dashed #3a3a5a;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  background: #2a2a4a;
}

.drop-zone.drag-over {
  border-color: #00d4ff;
  background: rgba(0, 212, 255, 0.1);
}

.drop-zone.has-content {
  border-style: solid;
  border-color: #3a3a5a;
}

.drop-icon {
  font-size: 2.5rem;
  margin-bottom: 10px;
}

.drop-text {
  color: #888;
  font-size: 1rem;
  margin-bottom: 5px;
}

.drop-hint {
  color: #666;
  font-size: 0.85rem;
}

.item-preview {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
}

.preview-media {
  flex: 1;
  aspect-ratio: 16/9;
  overflow: hidden;
  border-radius: 8px 8px 0 0;
  position: relative;
}

.preview-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.7);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9rem;
}

.preview-info {
  padding: 10px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.item-type {
  background: #00d4ff;
  color: #000;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
  flex-shrink: 0;
}

.item-name {
  color: #aaa;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.clear-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #ff6b6b;
  transform: scale(1.1);
}

.divider {
  text-align: center;
  padding: 15px 0;
  color: #555;
  font-weight: bold;
  font-size: 1.1rem;
}

.panel-footer {
  padding: 15px 20px;
  border-top: 1px solid #2a2a4a;
}

.start-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(90deg, #00d4ff, #c44dff);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
}

.start-btn:hover:not(:disabled) {
  transform: scale(1.02);
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.4);
}

.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>