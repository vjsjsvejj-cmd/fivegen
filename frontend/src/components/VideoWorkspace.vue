<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, inject } from 'vue'
import UploadArea from './UploadArea.vue'
import Modal from './Modal.vue'
import PromptHelper from './PromptHelper.vue'

const promptTextarea = ref(null)

// 增强模式彩蛋功能
let promptClickCount = 0
let promptClickTimer = null
const showEnhancedMode = ref(false)

const handlePromptLabelClick = () => {
  promptClickCount++
  
  // 清除之前的计时器
  if (promptClickTimer) {
    clearTimeout(promptClickTimer)
  }
  
  // 如果点击了5次，触发彩蛋
  if (promptClickCount >= 5) {
    showEnhancedMode.value = !showEnhancedMode.value
    promptClickCount = 0
    if (promptClickTimer) {
      clearTimeout(promptClickTimer)
      promptClickTimer = null
    }
  } else {
    // 1秒内未达到5次，重置计数
    promptClickTimer = setTimeout(() => {
      promptClickCount = 0
    }, 1000)
  }
}

// 注入模板数据
const templates = inject('templates', ref([]))
const showTemplateSuggestions = ref(false)
const templateSearchTerm = ref('')

// 过滤后的模板列表
const filteredTemplates = computed(() => {
  if (!templateSearchTerm.value) {
    return templates.value
  }
  const searchTerm = templateSearchTerm.value.toLowerCase()
  return templates.value.filter(template => 
    template.name.toLowerCase().includes(searchTerm) || 
    template.content.toLowerCase().includes(searchTerm)
  )
})

const props = defineProps({
  roomId: { type: String, default: '' },
  userId: { type: String, default: '' },
  isConnected: { type: Boolean, default: false }
})

const emit = defineEmits(['generate'])

const VIDEO_MODELS = {
  "seedance-2-0": { 
    name: "Seedance 2.0", 
    resolutions: ["480p", "720p", "1080p"],
    default_resolution: "720p",
    durations: ["4s", "5s", "6s", "7s", "8s", "9s", "10s", "11s", "12s", "13s", "14s", "15s"]
  }
}

const ASPECT_RATIOS = ["16:9", "9:16", "1:1", "3:4", "4:3", "21:9"]

const VIDEO_RESOLUTION_CONFIG = {
  "480p": {
    "16:9": { width: 864, height: 496 },
    "4:3": { width: 752, height: 560 },
    "1:1": { width: 640, height: 640 },
    "3:4": { width: 560, height: 752 },
    "9:16": { width: 496, height: 864 },
    "21:9": { width: 992, height: 432 }
  },
  "720p": {
    "16:9": { width: 1280, height: 720 },
    "4:3": { width: 1112, height: 834 },
    "1:1": { width: 960, height: 960 },
    "3:4": { width: 834, height: 1112 },
    "9:16": { width: 720, height: 1280 },
    "21:9": { width: 1470, height: 630 }
  },
  "1080p": {
    "16:9": { width: 1920, height: 1080 },
    "4:3": { width: 1664, height: 1248 },
    "1:1": { width: 1440, height: 1440 },
    "3:4": { width: 1248, height: 1664 },
    "9:16": { width: 1080, height: 1920 },
    "21:9": { width: 2206, height: 946 }
  }
}

const FRAME_RATE = 24

const calculateVideoTokens = () => {
  const outputDuration = parseInt(duration.value.replace('s', ''))
  const resolutionConfig = VIDEO_RESOLUTION_CONFIG[resolution.value]?.[aspectRatio.value]
  
  if (!resolutionConfig) return null
  
  const { width, height } = resolutionConfig
  
  const referenceVideo = multimodalFiles.value.find(f => f.type?.startsWith('video/'))
  const inputDuration = referenceVideo?.duration || 0
  
  const totalDuration = inputDuration + outputDuration
  const tokenCount = (totalDuration * width * height * FRAME_RATE) / 1024
  
  return {
    value: tokenCount,
    inputDuration,
    outputDuration,
    width,
    height
  }
}

const formatVideoCostDisplay = () => {
  const tokens = calculateVideoTokens()
  if (!tokens) return ''
  const formatted = tokens.value.toFixed(2)
  return `💎 ${formatted} Token`
}

const currentMode = ref('text-to-video')
const selectedModel = ref('seedance-2-0')
const aspectRatio = ref('16:9')
const resolution = ref('720p')
const duration = ref('5s')
const generateAudio = ref(true)
const prompt = ref('')
const seed = ref(Math.floor(Math.random() * 2147483647))
const firstFrameImages = ref([])
const lastFrameImages = ref([])
const multimodalFiles = ref([])
const modalVisible = ref(false)
const modalType = ref('video')
const modalUrl = ref('')
const showAtSuggestions = ref(false)

const availableResolutions = computed(() => {
  const model = VIDEO_MODELS[selectedModel.value]
  return model ? model.resolutions : []
})

const availableDurations = computed(() => {
  const model = VIDEO_MODELS[selectedModel.value]
  return model ? model.durations : []
})

const isGenerateDisabled = computed(() => {
  if (!prompt.value.trim()) return true
  if (currentMode.value === 'frame') {
    // 首尾帧模式：要么只有首帧，要么首尾帧都有，不能只有尾帧
    if (firstFrameImages.value.length === 0 && lastFrameImages.value.length === 0) {
      return true
    }
    if (firstFrameImages.value.length === 0 && lastFrameImages.value.length > 0) {
      return true
    }
  }
  return false
})

// 用于@功能的文件列表 - 包含所有上传的文件
const atFilesList = computed(() => {
  let allFiles = []
  
  if (currentMode.value === 'frame') {
    allFiles = [...firstFrameImages.value, ...lastFrameImages.value]
  } else if (currentMode.value === 'reference') {
    allFiles = [...multimodalFiles.value]
  }
  
  return allFiles.map(f => ({
    ...f,
    fileType: f.type?.startsWith('video/') ? 'video' : 
              f.type?.startsWith('audio/') ? 'audio' : 'image'
  }))
})

const handlePromptInput = (e) => {
  const value = e.target.value
  // 检查是否以@结尾
  const hasAt = value.endsWith('@')
  if (hasAt && atFilesList.value.length > 0) {
    showAtSuggestions.value = true
    showTemplateSuggestions.value = false
    templateSearchTerm.value = ''
  } else {
    showAtSuggestions.value = false
  }
  
  // 检查 # 号和搜索词
  const lastHashIndex = value.lastIndexOf('#')
  if (lastHashIndex !== -1) {
    // 有 # 号，提取搜索词
    const searchTerm = value.substring(lastHashIndex + 1).trim()
    templateSearchTerm.value = searchTerm
    showTemplateSuggestions.value = templates.value.length > 0
    showAtSuggestions.value = false
  } else if (!hasAt) {
    // 没有 # 号，关闭模板建议
    showTemplateSuggestions.value = false
    templateSearchTerm.value = ''
  }
}

const handleKeydown = (e) => {
  // 按ESC键关闭建议框
  if (e.key === 'Escape') {
    showAtSuggestions.value = false
    showTemplateSuggestions.value = false
  }
  // 按Enter键关闭建议框（如果有显示）
  if (e.key === 'Enter' && (showAtSuggestions.value || showTemplateSuggestions.value)) {
    showAtSuggestions.value = false
    showTemplateSuggestions.value = false
  }
  // 检查是否按下了@键
  if (e.key === '@' && atFilesList.value.length > 0) {
    setTimeout(() => {
      showAtSuggestions.value = true
      showTemplateSuggestions.value = false
    }, 10)
  }
  // 检查是否按下了#键
  if (e.key === '#' && templates.value.length > 0) {
    setTimeout(() => {
      showTemplateSuggestions.value = true
      showAtSuggestions.value = false
    }, 10)
  }
}

const selectAtFile = (file) => {
  showAtSuggestions.value = false
  // 获取当前光标位置（这才是正确的@位置）
  const currentCursorPos = promptTextarea.value?.selectionStart || prompt.value.length
  const atIndex = prompt.value.lastIndexOf('@', currentCursorPos)
  
  // 获取该文件在列表中的 index
  const fileIndex = atFilesList.value.findIndex(f => f.id === file.id)
  let shortCode = file.shortCode
  if (!shortCode) {
    if (file.fileType === 'video') {
      shortCode = `视频${fileIndex + 1}`
    } else if (file.fileType === 'audio') {
      shortCode = `音频${fileIndex + 1}`
    } else {
      shortCode = `图片${fileIndex + 1}`
    }
  }
  
  // 保留@前面的内容、替换@部分、保留@后面的内容
  const before = prompt.value.substring(0, atIndex)
  const after = prompt.value.substring(currentCursorPos) // 保留光标后面的内容
  prompt.value = before + '@' + shortCode + ' ' + after
  
  // 在下一帧聚焦到 textarea 并设置光标位置到插入的位置后面
  nextTick(() => {
    if (promptTextarea.value) {
      promptTextarea.value.focus()
      const newPos = before.length + 1 + shortCode.length + 1
      promptTextarea.value.selectionStart = newPos
      promptTextarea.value.selectionEnd = newPos
    }
  })
}

const selectTemplate = (template) => {
  showTemplateSuggestions.value = false
  templateSearchTerm.value = ''
  const hashIndex = prompt.value.lastIndexOf('#')
  prompt.value = prompt.value.substring(0, hashIndex) + template.content + ' '
  
  // 在下一帧聚焦到 textarea 并设置光标位置
  nextTick(() => {
    if (promptTextarea.value) {
      promptTextarea.value.focus()
      // 设置光标到末尾
      promptTextarea.value.selectionStart = promptTextarea.value.value.length
      promptTextarea.value.selectionEnd = promptTextarea.value.value.length
    }
  })
}

const formatPrompt = (text) => {
  let escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  escaped = escaped.replace(/@图片(\d+)/g, '<span style="color: #00d4ff; font-weight: bold;">@图片$1</span>')
  escaped = escaped.replace(/@视频(\d+)/g, '<span style="color: #ff4444; font-weight: bold;">@视频$1</span>')
  escaped = escaped.replace(/@音频(\d+)/g, '<span style="color: #00ff88; font-weight: bold;">@音频$1</span>')
  escaped = escaped.replace(/@首帧/g, '<span style="color: #00d4ff; font-weight: bold;">@首帧</span>')
  escaped = escaped.replace(/@尾帧/g, '<span style="color: #ff4444; font-weight: bold;">@尾帧</span>')
  return escaped
}

// 构建提示词的映射表
const buildPromptMapping = () => {
  const mapping = {}
  const files = atFilesList.value
  files.forEach((file, index) => {
    const shortCode = file.shortCode || (
      file.fileType === 'video' ? `视频${index + 1}` : 
      file.fileType === 'audio' ? `音频${index + 1}` : 
      `图片${index + 1}`
    )
    mapping[`@${shortCode}`] = file.url
  })
  return mapping
}

// 将用户输入的提示词替换为实际的 URL
const replacePromptCodes = (text) => {
  const mapping = buildPromptMapping()
  let result = text
  for (const [code, url] of Object.entries(mapping)) {
    result = result.replace(new RegExp(code.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), url)
  }
  return result
}

const handleModelChange = (e) => {
  const modelKey = e.target.value
  selectedModel.value = modelKey
  const modelConfig = VIDEO_MODELS[modelKey]
  if (modelConfig) {
    resolution.value = modelConfig.default_resolution || '720p'
  }
}

const randomizeSeed = () => {
  seed.value = Math.floor(Math.random() * 2147483647)
}

const quickSeeds = [-1, 20, 2026, 5188, 6699, 8866, 9527]

const setQuickSeed = (quickSeed) => {
  seed.value = quickSeed
}

const handleGenerate = () => {
  // 替换提示词中的 @代码为实际的 URL
  const processedPrompt = replacePromptCodes(prompt.value)

  // 准备参数
  let params = {
    type: 'video',
    model: selectedModel.value,
    aspect_ratio: aspectRatio.value,
    resolution: resolution.value,
    duration: duration.value,
    prompt: processedPrompt,
    displayPrompt: prompt.value, // 保存用户友好的显示版本
    mode: currentMode.value,
    generate_audio: generateAudio.value,
    seed: seed.value,
    first_frame: null,
    last_frame: null,
    multimodal_files: []
  }

  // 根据模式处理不同的文件
  if (currentMode.value === 'frame') {
    if (firstFrameImages.value.length > 0) {
      params.first_frame = firstFrameImages.value[0].url
      params.multimodal_files.push({
        id: firstFrameImages.value[0].id,
        url: firstFrameImages.value[0].url,
        name: firstFrameImages.value[0].name,
        originalName: firstFrameImages.value[0].originalName,
        displayName: firstFrameImages.value[0].displayName,
        shortCode: firstFrameImages.value[0].shortCode,
        type: firstFrameImages.value[0].type || 'image',
        role: 'first_frame'
      })
    }
    if (lastFrameImages.value.length > 0) {
      params.last_frame = lastFrameImages.value[0].url
      params.multimodal_files.push({
        id: lastFrameImages.value[0].id,
        url: lastFrameImages.value[0].url,
        name: lastFrameImages.value[0].name,
        originalName: lastFrameImages.value[0].originalName,
        displayName: lastFrameImages.value[0].displayName,
        shortCode: lastFrameImages.value[0].shortCode,
        type: lastFrameImages.value[0].type || 'image',
        role: 'last_frame'
      })
    }
  } else if (currentMode.value === 'reference') {
    params.multimodal_files = multimodalFiles.value.map(f => ({
      id: f.id,
      url: f.url,
      name: f.name,
      originalName: f.originalName,
      displayName: f.displayName,
      shortCode: f.shortCode,
      type: f.type,
      role: f.role || 'reference_image'
    }))
  }

  emit('generate', params)
}



const handleDropToFirstFrame = (e) => {
  e.preventDefault()
  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'))
    if (data.url && data.type === 'image') {
      firstFrameImages.value.push({
        id: Date.now() + Math.random(),
        url: data.url,
        name: `drag-${data.task_id?.substring(0, 6) || 'first-frame'}.jpg`,
        type: 'image/jpeg'
      })
    }
  } catch (err) {
    // Drag data parse error
  }
}

const handleDropToLastFrame = (e) => {
  e.preventDefault()
  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'))
    if (data.url && data.type === 'image') {
      lastFrameImages.value.push({
        id: Date.now() + Math.random(),
        url: data.url,
        name: `drag-${data.task_id?.substring(0, 6) || 'last-frame'}.jpg`,
        type: 'image/jpeg'
      })
    }
  } catch (err) {
    // Drag data parse error
  }
}

const handleDropToMultimodal = (e) => {
  e.preventDefault()
  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'))
    if (data.url) {
      const fileType = data.type
      multimodalFiles.value.push({
        id: Date.now() + Math.random(),
        url: data.url,
        name: `drag-${data.task_id?.substring(0, 6) || 'multimodal'}.${fileType === 'video' ? 'mp4' : fileType === 'audio' ? 'mp3' : 'jpg'}`,
        type: fileType === 'video' ? 'video/mp4' : fileType === 'audio' ? 'audio/mp3' : 'image/jpeg',
        role: fileType === 'video' ? 'reference_video' : fileType === 'audio' ? 'reference_audio' : 'reference_image'
      })
    }
  } catch (err) {
    // Drag data parse error
  }
}

const handleReEdit = (result) => {
  const params = result.params
  currentMode.value = params.mode || 'text-to-video'
  selectedModel.value = params.model
  aspectRatio.value = params.aspect_ratio
  resolution.value = params.resolution
  duration.value = params.duration
  // 优先使用用户友好的 displayPrompt，如果没有才用 prompt
  prompt.value = params.displayPrompt || params.prompt
  generateAudio.value = params.generate_audio || true
  seed.value = params.seed || Math.floor(Math.random() * 2147483647)

  // 清空所有上传
  firstFrameImages.value = []
  lastFrameImages.value = []
  multimodalFiles.value = []

  // 恢复上传的文件
  if (params.multimodal_files && params.multimodal_files.length > 0) {
    for (const file of params.multimodal_files) {
      // 根据角色判断默认类型
      let defaultType = 'image/jpeg'
      if (file.role === 'reference_video') defaultType = 'video/mp4'
      else if (file.role === 'reference_audio') defaultType = 'audio/mp3'
      
      let displayName = file.displayName || file.name
      let shortCode = file.shortCode
      
      // 确保首尾帧的显示名称正确
      if (file.role === 'first_frame') {
        displayName = '首帧'
        shortCode = '首帧'
      } else if (file.role === 'last_frame') {
        displayName = '尾帧'
        shortCode = '尾帧'
      }
      
      const fileData = {
        id: file.id,
        url: file.url,
        name: file.name,
        originalName: file.originalName || file.name,
        displayName: displayName,
        shortCode: shortCode,
        type: file.type || defaultType,
        role: file.role
      }
      
      if (file.role === 'first_frame') {
        firstFrameImages.value.push(fileData)
      } else if (file.role === 'last_frame') {
        lastFrameImages.value.push(fileData)
      } else {
        multimodalFiles.value.push(fileData)
      }
    }
  }
}

const openModal = (url) => {
  modalUrl.value = url
  modalType.value = 'video'
  modalVisible.value = true
}

const closeModal = () => {
  modalVisible.value = false
}

const setPrompt = (text) => {
  prompt.value = text
}

const handleOutsideClick = (e) => {
  if (!e.target.closest('.prompt-wrapper')) {
    showAtSuggestions.value = false
    showTemplateSuggestions.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
  const modelConfig = VIDEO_MODELS[selectedModel.value]
  if (modelConfig) {
    resolution.value = modelConfig.default_resolution || '720p'
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick)
})

defineExpose({ handleReEdit, setPrompt })
</script>

<template>
  <div class="video-workspace">
    <div class="panel-header">
      <h2>🎬 视频制作</h2>
    </div>

    <div class="mode-section">
      <h3>模式</h3>
      <div class="mode-tabs">
        <button 
          v-for="mode in [
            { id: 'text-to-video', name: '文生视频' },
            { id: 'frame', name: '首尾帧' },
            { id: 'reference', name: '多模态' }
          ]" 
          :key="mode.id"
          :class="['mode-tab', { active: currentMode === mode.id }]"
          @click="currentMode = mode.id"
        >
          {{ mode.name }}
        </button>
      </div>
    </div>

    <div class="params-section">
      <h3>参数配置</h3>

      <div class="param-row">
        <div class="param-item param-item-flex">
          <label>模型</label>
          <select :value="selectedModel" @change="handleModelChange">
            <option v-for="(model, key) in VIDEO_MODELS" :key="key" :value="key">
              {{ model.name }}
            </option>
          </select>
        </div>

        <div class="param-item param-item-flex">
          <label>清晰度</label>
          <div class="button-group">
            <button 
              v-for="res in availableResolutions" 
              :key="res" 
              :class="['opt-btn', { active: resolution === res }]"
              @click="resolution = res"
            >
              {{ res }}
            </button>
          </div>
        </div>
       
                <div class="param-item param-item-flex switch-item">
           
          <div class="switch-wrapper">
          <label>音频</label>
            <label class="switch">
            
              <input type="checkbox" v-model="generateAudio" />
              <span class="slider"></span>
            </label>
            <span class="switch-label">{{ generateAudio ? '已开启' : '已关闭' }}</span>
          </div>
        </div>
      </div>

      <div class="param-row">
        <div class="param-item param-item-flex">
          <label>画面比例</label>
          <div class="button-group">
            <button 
              v-for="ratio in ASPECT_RATIOS" 
              :key="ratio" 
              :class="['opt-btn', { active: aspectRatio === ratio }]"
              @click="aspectRatio = ratio"
            >
              {{ ratio }}
            </button>
          </div>
        </div>


      </div>

      <div class="param-item">
        <label>时长</label>
        <div class="button-group">
          <button 
            v-for="d in availableDurations" 
            :key="d" 
            :class="['opt-btn opt-btn-small', { active: duration === d }]"
            @click="duration = d"
          >
            {{ d }}
          </button>
        </div>
      </div>

      <div class="param-item seed-item">
        <label>随机种子</label>
        <div class="seed-input-wrapper">
          <input type="number" v-model.number="seed" class="seed-input" :min="-1" :max="2147483647" />
          <button @click="randomizeSeed" class="randomize-btn" title="随机化种子">🎲</button>
        </div>
        <div class="quick-seeds">
          <button 
            v-for="quickSeed in quickSeeds" 
            :key="quickSeed" 
            :class="['quick-seed-btn', { active: seed === quickSeed }]"
            @click="setQuickSeed(quickSeed)"
          >
            {{ quickSeed }}
          </button>
        </div>
      </div>

      <!-- 首尾帧模式的上传区 - 同一行显示 -->
      <div class="upload-section" v-if="currentMode === 'frame'">
        <div class="frame-mode-tip" :class="{ 'error': firstFrameImages.length === 0 && lastFrameImages.length > 0 }">
          <span v-if="firstFrameImages.length === 0 && lastFrameImages.length === 0">
            💡 请上传首帧图片，或同时上传首尾帧图片
          </span>
          <span v-else-if="firstFrameImages.length === 0 && lastFrameImages.length > 0">
            ❌ 不能只使用尾帧，请同时上传首帧或只使用首帧
          </span>
          <span v-else-if="firstFrameImages.length > 0 && lastFrameImages.length > 0">
            ✅ 首尾帧模式：视频将从首帧过渡到尾帧
          </span>
          <span v-else>
            ✅ 首帧模式：视频将从首帧开始生成
          </span>
        </div>
        <div class="frame-uploads">
          <div class="frame-upload-item">
            <h3>首帧图片 {{ firstFrameImages.length > 0 ? '(已上传)' : '(必填)' }}</h3>
            <div class="drop-target" @drop="handleDropToFirstFrame" @dragover.prevent>
              <UploadArea v-model="firstFrameImages" :max-files="1" label="拖拽或点击上传首帧图片" :is-first-last-frame="true" frame-position="first" />
            </div>
          </div>

          <div class="frame-upload-item">
            <h3>尾帧图片 (可选)</h3>
            <div class="drop-target" @drop="handleDropToLastFrame" @dragover.prevent>
              <UploadArea v-model="lastFrameImages" :max-files="1" label="拖拽或点击上传尾帧图片" :is-first-last-frame="true" frame-position="last" />
            </div>
          </div>
        </div>
      </div>

      <!-- 多模态模式的上传区 -->
      <div class="upload-section" v-if="currentMode === 'reference'">
        <h3>多模态素材</h3>
        <div class="drop-target" @drop="handleDropToMultimodal" @dragover.prevent>
          <UploadArea 
            v-model="multimodalFiles" 
            :max-files="10" 
            :show-role-selector="true"
            accept="image/*,video/*,audio/*"
            label="拖拽或点击上传图片/视频/音频" 
          />
        </div>
      </div>

      <div class="param-item prompt-item">
        <div class="prompt-label-row">
          <label @click="handlePromptLabelClick">提示词</label>
          <PromptHelper v-model="prompt" :is-enhanced="showEnhancedMode" :reference-images="atFilesList" />
        </div>
        <div class="prompt-wrapper">
          <div class="prompt-display" v-html="formatPrompt(prompt)"></div>
          <textarea 
            ref="promptTextarea"
            v-model="prompt" 
            placeholder="输入描述... (输入 @ 唤起已上传素材，输入 # 唤起模板)"
            rows="4"
            @input="handlePromptInput"
            @keydown="handleKeydown"
            class="prompt-input"
          ></textarea>
          <div v-if="showAtSuggestions" class="at-suggestions">
            <div 
              v-for="(file, index) in atFilesList" 
              :key="file.id" 
              class="at-suggestion"
              @click="selectAtFile(file)"
            >
              <div class="thumb">
                <img v-if="file.fileType === 'image'" :src="file.url" :alt="file.displayName" />
                <span v-else-if="file.fileType === 'video'" class="video-thumb">🎬</span>
                <span v-else class="audio-thumb">🎵</span>
              </div>
              <span class="name">
                {{ file.shortCode || (file.fileType === 'video' ? `视频${index + 1}` : file.fileType === 'audio' ? `音频${index + 1}` : `图片${index + 1}`) }}
              </span>
            </div>
          </div>
          <div v-if="showTemplateSuggestions" class="template-suggestions">
            <div 
              v-for="(template, index) in filteredTemplates" 
              :key="template.id" 
              class="template-suggestion"
              @click="selectTemplate(template)"
            >
              <div class="template-name">{{ template.name }}</div>
              <div class="template-preview">{{ template.content }}</div>
            </div>
            <div v-if="filteredTemplates.length === 0" class="template-empty">
              没有匹配的模板
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="generate-section">
      <div class="btn-wrapper">
        <button @click="handleGenerate" class="btn btn-generate" :disabled="isGenerateDisabled">
          🚀 生成视频
        </button>
        <div v-if="!isGenerateDisabled" class="cost-tooltip">
          <div class="cost-tooltip-content">
            <div class="cost-title">预估消耗</div>
            <div class="cost-value">{{ formatVideoCostDisplay() }}</div>
            <div class="cost-details">
              <span v-if="calculateVideoTokens()?.inputDuration > 0">输入: {{ calculateVideoTokens()?.inputDuration }}s</span>
              <span v-if="calculateVideoTokens()?.inputDuration > 0"> + </span>
              <span>输出: {{ calculateVideoTokens()?.outputDuration }}s</span>
              <span> | {{ calculateVideoTokens()?.width }}×{{ calculateVideoTokens()?.height }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Modal :visible="modalVisible" :type="modalType" :url="modalUrl" @close="closeModal" />
  </div>
</template>

<style scoped>
.video-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.panel-header {
  padding: 20px;
  border-bottom: 1px solid #333;
  background: #0f0f23;
  position: sticky;
  top: 0;
  z-index: 10;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.3rem;
}

.mode-section,
.params-section,
.upload-section,
.generate-section {
  padding: 20px;
  border-bottom: 1px solid #333;
}

.mode-section h3,
.params-section h3,
.upload-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1rem;
  color: #00d4ff;
}

.mode-tabs {
  display: flex;
  gap: 8px;
}

.mode-tab {
  padding: 8px 14px;
  border: 1px solid #4a4a6a;
  border-radius: 6px;
  background: #2a2a4a;
  color: #ccc;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.mode-tab:hover {
  border-color: #00d4ff;
}

.mode-tab.active {
  background: #00d4ff;
  color: #000;
  border-color: #00d4ff;
}

.param-item {
  margin-bottom: 15px;
}

.param-row {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.param-item-flex {
  flex: 1;
  margin-bottom: 0;
}

.params-section .upload-section {
  border-bottom: none;
  padding: 0;
  margin-bottom: 15px;
}

.param-item label {
  display: block;
  margin-bottom: 8px;
  color: #ccc;
  font-size: 0.9rem;
}

.param-item select {
  width: 100%;
  padding: 10px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #2a2a4a;
  color: #fff;
  font-size: 0.95rem;
}

.param-item select:focus {
  outline: none;
  border-color: #00d4ff;
}

.button-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.opt-btn {
  padding: 8px 14px;
  border: 1px solid #4a4a6a;
  border-radius: 6px;
  background: #2a2a4a;
  color: #ccc;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.opt-btn:hover {
  border-color: #00d4ff;
}

.opt-btn.active {
  background: #00d4ff;
  color: #000;
  border-color: #00d4ff;
}

.opt-btn-small {
  padding: 6px 10px;
  font-size: 0.8rem;
}

.switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.switch-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #4a4a6a;
  transition: 0.3s;
  border-radius: 26px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #00d4ff;
}

input:checked + .slider:before {
  transform: translateX(22px);
}

.switch-label {
  font-size: 0.85rem;
  color: #aaa;
}

.prompt-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.prompt-wrapper {
  position: relative;
}

.prompt-display {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 10px;
  min-height: 80px;
  pointer-events: none;
  color: transparent;
  word-wrap: break-word;
  white-space: pre-wrap;
  line-height: 1.5;
  font-size: 0.95rem;
}

.prompt-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #2a2a4a;
  color: #fff;
  font-size: 0.95rem;
  line-height: 1.5;
  resize: vertical;
  position: relative;
  z-index: 1;
}

.prompt-input:focus {
  outline: none;
  border-color: #00d4ff;
}

.at-suggestions {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  background: #2a2a4a;
  border: 1px solid #333;
  border-radius: 6px;
  margin-bottom: 5px;
  display: flex;
  gap: 10px;
  padding: 10px;
  z-index: 9999;
  overflow-x: auto;
}

.at-suggestion {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 5px;
  border-radius: 4px;
  flex-shrink: 0;
  width: 70px;
}

.at-suggestion:hover {
  background: #3a3a5a;
}

.thumb {
  width: 50px;
  height: 50px;
  border-radius: 4px;
  overflow: hidden;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-thumb,
.audio-thumb {
  font-size: 1.5rem;
}

.at-suggestion .name {
  font-size: 0.65rem;
  color: #888;
  margin-top: 4px;
  word-break: break-all;
  text-align: center;
}

.template-suggestions {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  background: #2a2a4a;
  border: 1px solid #333;
  border-radius: 6px;
  margin-bottom: 5px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 9999;
}

.template-suggestion {
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #333;
}

.template-suggestion:last-child {
  border-bottom: none;
}

.template-suggestion:hover {
  background: #3a3a5a;
}

.template-name {
  font-size: 0.9rem;
  font-weight: bold;
  color: #00d4ff;
  margin-bottom: 4px;
}

.template-preview {
  font-size: 0.75rem;
  color: #888;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-empty {
  padding: 20px;
  text-align: center;
  color: #888;
  font-size: 0.85rem;
}

.upload-wrapper {
  margin-bottom: 10px;
}

.file-list {
  margin-top: 15px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: #2a2a4a;
  border-radius: 6px;
  margin-bottom: 8px;
}

.file-item img {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
}

.file-icon {
  font-size: 1.5rem;
}

.file-name {
  flex: 1;
  color: #ccc;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-select {
  padding: 5px 8px;
  border: 1px solid #333;
  border-radius: 4px;
  background: #1a1a2e;
  color: #fff;
  font-size: 0.8rem;
}

.role-select:focus {
  outline: none;
  border-color: #00d4ff;
}

.generate-section {
  padding-top: 25px;
}

.btn-generate {
  width: 100%;
  padding: 14px;
  font-size: 1.05rem;
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  color: #000;
  font-weight: bold;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-generate:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(0, 212, 255, 0.3);
}

.btn-generate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-wrapper {
  position: relative;
  display: inline-block;
  width: 100%;
}

.cost-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 10px;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
  z-index: 100;
}

.btn-wrapper:hover .cost-tooltip {
  opacity: 1;
  visibility: visible;
}

.cost-tooltip-content {
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border: 1px solid #00d4ff;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2);
  white-space: nowrap;
}

.cost-tooltip-content::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 8px solid transparent;
  border-top-color: #00d4ff;
}

.cost-title {
  color: #aaa;
  font-size: 0.75rem;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.cost-value {
  color: #00ff88;
  font-size: 1.1rem;
  font-weight: bold;
}

.cost-details {
  color: #888;
  font-size: 0.75rem;
  margin-top: 6px;
}

.seed-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.seed-input-wrapper {
  display: flex;
  gap: 8px;
  flex: 1;
}

.seed-input {
  flex: 1;
  padding: 8px 12px;
  background: #2a2a4a;
  border: 1px solid #333;
  border-radius: 6px;
  color: #fff;
  font-size: 0.9rem;
}

.seed-input:focus {
  outline: none;
  border-color: #00d4ff;
}

.randomize-btn {
  padding: 8px 16px;
  background: #2a2a4a;
  border: 1px solid #333;
  border-radius: 6px;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.randomize-btn:hover {
  background: #3a3a5a;
  border-color: #00d4ff;
}

.quick-seeds {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.quick-seed-btn {
  padding: 6px 12px;
  border: 1px solid #4a4a6a;
  border-radius: 6px;
  background: #2a2a4a;
  color: #ccc;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.quick-seed-btn:hover {
  border-color: #00d4ff;
  background: #3a3a5a;
}

.quick-seed-btn.active {
  background: #00d4ff;
  color: #000;
  border-color: #00d4ff;
}

.frame-mode-tip {
  padding: 12px 16px;
  margin-bottom: 15px;
  border-radius: 8px;
  font-size: 0.9rem;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.3);
  color: #00d4ff;
}

.frame-mode-tip.error {
  background: rgba(255, 68, 68, 0.1);
  border-color: rgba(255, 68, 68, 0.3);
  color: #ff4444;
}

.frame-uploads {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.frame-upload-item {
  display: flex;
  flex-direction: column;
}

.frame-upload-item h3 {
  margin-top: 0;
}

.drop-target {
  border: 2px dashed transparent;
  border-radius: 8px;
  transition: all 0.2s;
}

.drop-target:hover {
  border-color: #00d4ff;
}
</style>
