
<script setup>
import { ref, watch, inject } from 'vue'
import Modal from './Modal.vue'
import { API_BASE_URL } from '../utils/config.js'

const toast = inject('toast', { error: (msg) => console.error(msg) })

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  maxFiles: {
    type: Number,
    default: 12
  },
  accept: {
    type: String,
    default: 'image/*'
  },
  label: {
    type: String,
    default: '拖拽或点击上传文件'
  },
  showRoleSelector: {
    type: Boolean,
    default: false
  },
  isFirstLastFrame: {
    type: Boolean,
    default: false
  },
  framePosition: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const files = ref([...props.modelValue])
const isDragging = ref(false)
const uploading = ref(false)
const modalVisible = ref(false)
const modalType = ref('image')
const modalUrl = ref('')

watch(() => props.modelValue, (newVal) => {
  files.value = [...newVal]
}, { deep: true })

const updateFiles = () => {
  emit('update:modelValue', files.value)
}

const uploadFile = async (file, index, retries = 3) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('index', index)

  let lastError = null
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`上传失败: ${response.status}`)
      }

      const result = await response.json()
      return result
    } catch (error) {
      lastError = error
      console.warn(`上传尝试 ${i + 1}/${retries} 失败:`, error)
      if (i < retries - 1) {
        // 等待一段时间后重试（指数退避）
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
      }
    }
  }
  throw lastError || new Error('上传失败')
}

const handleDrop = (e) => {
  e.preventDefault()
  isDragging.value = false
  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

const handleDragOver = (e) => {
  e.preventDefault()
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleFileInput = (e) => {
  const selectedFiles = Array.from(e.target.files)
  addFiles(selectedFiles)
  e.target.value = ''
}

const getVideoDuration = (file) => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video')
    video.preload = 'metadata'
    
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(video.src)
      resolve(video.duration)
    }
    
    video.onerror = () => {
      URL.revokeObjectURL(video.src)
      reject(new Error('无法获取视频时长'))
    }
    
    video.src = URL.createObjectURL(file)
  })
}

const addFiles = async (newFiles) => {
  const remainingSlots = props.maxFiles - files.value.length
  const filesToAdd = newFiles.slice(0, remainingSlots)

  for (const file of filesToAdd) {
    try {
      uploading.value = true
      const previewUrl = URL.createObjectURL(file)
      const nextIndex = files.value.length + 1
      
      let duration = null
      if (file.type?.startsWith('video/')) {
        try {
          duration = await getVideoDuration(file)
        } catch (e) {
          console.warn('获取视频时长失败:', e)
        }
      }
      
      const tempFileObj = {
        id: Date.now() + Math.random(),
        file,
        url: previewUrl,
        name: file.name,
        originalName: file.name,
        displayName: file.name,
        shortCode: null,
        type: file.type,
        duration: duration,
        uploading: true
      }
      files.value.push(tempFileObj)
      updateFiles()

      const uploadResult = await uploadFile(file, nextIndex)

      const fileIndex = files.value.findIndex(f => f.id === tempFileObj.id)
      if (fileIndex !== -1) {
        let displayName = uploadResult.displayName || file.name
        let shortCode = uploadResult.shortCode
        
        if (props.isFirstLastFrame) {
          if (props.framePosition === 'first') {
            displayName = '首帧'
            shortCode = '首帧'
          } else if (props.framePosition === 'last') {
            displayName = '尾帧'
            shortCode = '尾帧'
          }
        }
        
        files.value[fileIndex] = {
          ...tempFileObj,
          url: uploadResult.url,
          publicUrl: uploadResult.url,
          size: uploadResult.size,
          originalName: uploadResult.originalName || file.name,
          displayName: displayName,
          shortCode: shortCode,
          uploading: false
        }
        updateFiles()
      }
    } catch (error) {
      console.error('上传失败:', error)
      toast.error('文件上传失败: ' + error.message)
    } finally {
      uploading.value = false
    }
  }
}

const removeFile = (index) => {
  if (files.value[index].url && files.value[index].file) {
    URL.revokeObjectURL(files.value[index].url)
  }
  files.value.splice(index, 1)
  updateFiles()
}

const openPreview = (file) => {
  modalType.value = file.type?.startsWith('video/') ? 'video' : 'image'
  modalUrl.value = file.url
  modalVisible.value = true
}

const closeModal = () => {
  modalVisible.value = false
}

const getFileTypeIcon = (type) => {
  if (type.startsWith('image/')) return '🖼️'
  if (type.startsWith('video/')) return '🎬'
  if (type.startsWith('audio/')) return '🎵'
  return '📄'
}

const getRoleOptions = (file) => {
  if (file.type?.startsWith('image/')) {
    return [
      { value: 'reference_image', label: '参考图片' },
      { value: 'first_frame', label: '首帧' },
      { value: 'last_frame', label: '尾帧' }
    ]
  } else if (file.type?.startsWith('video/')) {
    return [
      { value: 'reference_video', label: '参考视频' }
    ]
  } else if (file.type?.startsWith('audio/')) {
    return [
      { value: 'reference_audio', label: '参考音频' }
    ]
  }
  return []
}

const setFileRole = (file, role) => {
  const index = files.value.findIndex(f => f.id === file.id)
  if (index !== -1) {
    files.value[index].role = role
    updateFiles()
  }
}

defineExpose({})
</script>

<template>
  <div class="upload-area">
    <div
      class="drop-zone"
      :class="{ dragging: isDragging, uploading: uploading }"
      role="button"
      tabindex="0"
      :aria-label="uploading ? '上传中' : label"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @click="!uploading && $refs.fileInput.click()"
      @keydown.enter="!uploading && $refs.fileInput.click()"
    >
      <div class="drop-icon">{{ uploading ? '⏳' : '📁' }}</div>
      <div class="drop-text">{{ uploading ? '上传中...' : label }}</div>
      <div class="drop-hint">最多 {{ maxFiles }} 个</div>
      <input
        ref="fileInput"
        type="file"
        :accept="accept"
        multiple
        @change="handleFileInput"
        style="display: none"
      />
    </div>

    <div class="file-preview" v-if="files.length > 0">
      <div
        v-for="(file, index) in files"
        :key="file.id"
        class="file-item"
      >
        <div
          class="file-preview-inner"
          @click.stop="!file.uploading && openPreview(file)"
        >
          <img v-if="file.type?.startsWith('image/')" :src="file.url" :alt="file.displayName" />
          <div v-else-if="file.type?.startsWith('video/')" class="video-thumb">
            <span class="video-icon">🎬</span>
          </div>
          <div v-else class="file-placeholder">
            <span class="icon">{{ getFileTypeIcon(file.type) }}</span>
            <span class="ext">{{ file.displayName.split('.').pop() }}</span>
          </div>
          <div v-if="file.uploading" class="upload-overlay">
            <div class="spinner"></div>
          </div>
        </div>
        <div class="file-name" :title="file.originalName">{{ file.displayName }}</div>
        <select 
          v-if="showRoleSelector && !file.uploading"
          :value="file.role || getRoleOptions(file)[0]?.value"
          @change="setFileRole(file, $event.target.value)"
          class="role-select"
        >
          <option v-for="option in getRoleOptions(file)" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <button @click.stop="removeFile(index)" class="remove-btn">×</button>
      </div>
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
.upload-area {
  width: 100%;
}

.drop-zone {
  border: 2px dashed #4a4a6a;
  border-radius: 12px;
  padding: 30px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #2a2a4a;
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: #00d4ff;
  background: #3a3a5a;
}

.drop-zone.uploading {
  cursor: not-allowed;
  opacity: 0.7;
}

.drop-icon {
  font-size: 3rem;
  margin-bottom: 10px;
}

.drop-text {
  color: #ccc;
  font-size: 1rem;
  margin-bottom: 5px;
}

.drop-hint {
  color: #666;
  font-size: 0.85rem;
}

.file-preview {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 10px;
  margin-top: 15px;
}

.file-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  aspect-ratio: 1;
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
}

.file-preview-inner {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
  position: relative;
}

.file-preview-inner:hover {
  background: #3a3a5a;
}

.file-preview-inner img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #4a4a6a;
  border-top-color: #00d4ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.video-thumb {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2a2a4a;
}

.video-icon {
  font-size: 1.8rem;
}

.file-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: #2a2a4a;
}

.file-placeholder .icon {
  font-size: 1.8rem;
  margin-bottom: 4px;
}

.file-placeholder .ext {
  font-size: 0.7rem;
  color: #888;
  text-transform: uppercase;
}

.file-name {
  font-size: 0.65rem;
  color: #aaa;
  padding: 4px 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-top: 1px solid #333;
}

.remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-btn:hover {
  background: #f87171;
}

.role-select {
  position: absolute;
  bottom: 30px;
  left: 4px;
  right: 4px;
  padding: 4px 6px;
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 4px;
  color: #fff;
  font-size: 0.65rem;
  z-index: 5;
}

.role-select:focus {
  outline: none;
  border-color: #00d4ff;
}
</style>

