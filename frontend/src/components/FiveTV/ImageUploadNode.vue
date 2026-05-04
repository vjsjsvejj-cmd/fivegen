<script setup>
import { ref, watch, inject, nextTick, onUnmounted } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { API_BASE_URL } from '../../utils/config'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:data'])

const { updateNode } = useVueFlow()
const nodeDataChangeCounter = inject('nodeDataChangeCounter', ref(0))

const imageUrl = ref(props.data.imageUrl || '')
const publicUrl = ref(props.data.publicUrl || '')
const imageName = ref(props.data.imageName || '')
const isDragging = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const previewBlobUrl = ref('')

let currentBlobUrl = ''
const cleanupBlobUrl = () => {
  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl)
    currentBlobUrl = ''
  }
}

const uploadToServer = async (file) => {
  uploading.value = true
  uploadError.value = ''

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error(`上传失败: ${response.status} ${response.statusText}`)
    }

    const result = await response.json()

    if (!result.success) {
      throw new Error(result.error || '上传失败')
    }

    return {
      url: result.url,
      displayName: result.displayName,
      shortCode: result.shortCode
    }
  } catch (error) {
    uploadError.value = error.message
    throw error
  } finally {
    uploading.value = false
  }
}

const handleFile = async (file) => {
  if (!file.type.startsWith('image/')) {
    uploadError.value = '请选择图片文件'
    return
  }

  cleanupBlobUrl()
  previewBlobUrl.value = URL.createObjectURL(file)
  currentBlobUrl = previewBlobUrl.value
  imageName.value = file.name

  try {
    const serverResult = await uploadToServer(file)

    const dataPayload = {
      ...props.data,
      imageUrl: serverResult.url,
      publicUrl: serverResult.url,
      imageName: serverResult.displayName,
      shortCode: serverResult.shortCode
    }

    imageUrl.value = serverResult.url
    publicUrl.value = serverResult.url

    emit('update:data', dataPayload)
  } catch (error) {
    console.error('图片上传失败:', error)
  }
}

const handleDrop = (e) => {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) handleFile(file)
}

const handleDragOver = (e) => {
  e.preventDefault()
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleInputChange = (e) => {
  const file = e.target.files[0]
  if (file) handleFile(file)
}

watch(() => props.data, (newData) => {
  if (newData && newData.imageUrl) {
    imageUrl.value = newData.imageUrl
    imageName.value = newData.imageName || ''
    if (newData.publicUrl) {
      publicUrl.value = newData.publicUrl
    }
  }
}, { deep: true })

watch([imageUrl, publicUrl, imageName], () => {
  updateNode(props.id, {
    data: {
      ...props.data,
      imageUrl: imageUrl.value,
      publicUrl: publicUrl.value,
      imageName: imageName.value
    }
  })
  if (typeof nodeDataChangeCounter.value === 'number') {
    nodeDataChangeCounter.value++
  }
}, { deep: true })

onUnmounted(() => {
  cleanupBlobUrl()
})
</script>

<template>
  <div class="upload-node">
    <Handle type="source" :position="Position.Right" id="output" class="handle-right" :connectable="true" />

    <div class="node-header">
      <span class="icon">🖼️</span>
      <span class="title">图片源</span>
    </div>

    <div
      class="upload-area"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      :class="{ dragging: isDragging }"
    >
      <div v-if="!imageUrl" class="upload-placeholder">
        <span class="upload-icon">📁</span>
        <span class="upload-text">拖放图片 或 点击上传</span>
        <label class="upload-btn" :class="{ disabled: uploading }">
          <span v-if="uploading">上传中...</span>
          <span v-else>选择图片</span>
          <input type="file" accept="image/*" @change="handleInputChange" hidden :disabled="uploading" />
        </label>
        <div v-if="uploadError" class="error-msg">{{ uploadError }}</div>
      </div>

      <div v-else class="image-preview">
        <img :src="previewBlobUrl || imageUrl" :alt="imageName" />
        <div class="image-info">
          <span class="image-name">{{ imageName }}</span>
          <span v-if="publicUrl" class="status-badge uploaded">✓ 已上传</span>
          <span v-else-if="uploading" class="status-badge uploading">上传中</span>
        </div>
        <div class="image-overlay">
          <label class="change-btn" :class="{ disabled: uploading }">
            <span v-if="uploading">上传中...</span>
            <span v-else>更换图片</span>
            <input type="file" accept="image/*" @change="handleInputChange" hidden :disabled="uploading" />
          </label>
        </div>
      </div>

      <div v-if="uploading && !imageUrl" class="uploading-indicator">
        <div class="spinner"></div>
        <span>正在上传到服务器...</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-node {
  min-width: 260px;
  background: var(--tv-surface, #1e1e30);
  border: 2px solid var(--tv-image-src, #4a9eff);
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.12s ease, box-shadow 0.12s ease;
}

.upload-node:hover {
  border-color: var(--tv-image-src, #4a9eff);
  box-shadow: 0 0 16px var(--tv-image-src-glow, rgba(74, 158, 255, 0.25));
}

.node-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--tv-surface-alt, #222238);
  border-bottom: 1px solid var(--tv-border, #353550);
}

.node-header .icon { 
  font-size: 0.85rem; 
}
.node-header .title { 
  color: var(--tv-image-src, #4a9eff); 
  font-weight: 600; 
  font-size: 0.78rem;
}

.upload-area {
  padding: 14px;
  min-height: 146px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.12s ease;
  position: relative;
}

.upload-area.dragging {
  background: rgba(74, 158, 255, 0.06);
}

.upload-placeholder {
  text-align: center;
  color: var(--tv-text-muted, #585878);
}

.upload-icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 0.8rem;
  display: block;
  margin-bottom: 12px;
}

.upload-btn {
  display: inline-block;
  padding: 7px 16px;
  background: rgba(74, 158, 255, 0.1);
  border-radius: 6px;
  color: var(--tv-image-src, #4a9eff);
  font-weight: 500;
  font-size: 0.78rem;
  cursor: pointer;
  transition: background 0.12s ease;
  border: 1px solid rgba(74, 158, 255, 0.2);
}

.upload-btn:hover:not(.disabled) { 
  background: rgba(74, 158, 255, 0.18); 
}
.upload-btn.disabled { opacity: 0.5; cursor: not-allowed; }

.error-msg {
  margin-top: 10px;
  color: var(--tv-error, #c06060);
  font-size: 0.75rem;
  font-weight: 500;
}

.uploading-indicator {
  position: absolute;
  inset: 0;
  background: rgba(28, 28, 40, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--tv-image-src, #4a9eff);
  font-size: 0.8rem;
  font-weight: 500;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(74, 158, 255, 0.15);
  border-top-color: var(--tv-image-src, #4a9eff);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.image-preview {
  position: relative;
  width: 100%;
  border-radius: 6px;
  overflow: hidden;
}

.image-preview img {
  width: 100%;
  max-height: 146px;
  object-fit: cover;
  display: block;
  aspect-ratio: 16/9;
}

.image-info {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 6px 10px;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.7), transparent);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.image-name {
  color: var(--tv-text, #d0d4dc);
  font-size: 0.7rem;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 400;
}

.status-badge {
  font-size: 0.6rem;
  padding: 2px 7px;
  border-radius: 4px;
  font-weight: 500;
}

.status-badge.uploaded {
  background: rgba(88, 184, 128, 0.15);
  color: var(--tv-success, #58b880);
  border: 1px solid rgba(88, 184, 128, 0.25);
}

.status-badge.uploading {
  background: rgba(74, 158, 255, 0.15);
  color: var(--tv-image-src, #4a9eff);
  border: 1px solid rgba(74, 158, 255, 0.25);
}

.image-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s;
}

.image-preview:hover .image-overlay { opacity: 1; }

.change-btn {
  padding: 7px 16px;
  background: rgba(74, 158, 255, 0.1);
  border-radius: 6px;
  color: var(--tv-image-src, #4a9eff);
  font-weight: 500;
  font-size: 0.78rem;
  cursor: pointer;
  transition: background 0.12s ease;
  border: 1px solid rgba(74, 158, 255, 0.2);
}

.change-btn:hover:not(.disabled) {
  background: rgba(74, 158, 255, 0.18);
}

.change-btn.disabled { opacity: 0.5; cursor: not-allowed; }

.handle-right {
  width: 14px !important;
  height: 14px !important;
  border: 2px solid var(--tv-image-src, #4a9eff) !important;
  border-radius: 50%;
  background: var(--tv-image-src, #4a9eff) !important;
  z-index: 10;
}
</style>
