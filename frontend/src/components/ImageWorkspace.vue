<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, inject } from 'vue'
import UploadArea from './UploadArea.vue'
import Modal from './Modal.vue'
import PromptHelper from './PromptHelper.vue'
import { formatPrompt } from '../utils/prompt.js'
import { usePromptInput } from '../composables/usePromptInput.js'
import { IMAGE_MODELS, IMAGE_ASPECT_RATIOS as ASPECT_RATIOS } from '../config/models.js'
import { createModelChangeHandler } from '../utils/workspace-helpers.js'

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

const props = defineProps({
  roomId: { type: String, default: '' },
  userId: { type: String, default: '' },
  isConnected: { type: Boolean, default: false }
})

const emit = defineEmits(['generate'])

const calculateImageCost = () => {
  const model = IMAGE_MODELS[selectedModel.value]
  if (!model) return null
  return { value: model.cost, type: model.costType, modelName: model.name }
}

const formatImageCostDisplay = () => {
  const cost = calculateImageCost()
  if (!cost) return ''
  if (cost.type === 'yuan') {
    return `💰 ${cost.value} 元 / 张`
  }
  return `💰 ${cost.value} 积分 / 次`
}

const currentMode = ref('text-to-image')
const selectedModel = ref('nano-banana-2')
const aspectRatio = ref('auto')
const resolution = ref('')
const prompt = ref('')
const referenceImages = ref([])
const portraitAuth = ref(false)
const modalVisible = ref(false)
const modalType = ref('image')
const modalUrl = ref('')

const availableResolutions = computed(() => {
  const model = IMAGE_MODELS[selectedModel.value]
  return model ? model.resolutions : []
})

const showPortraitAuth = computed(() => {
  return selectedModel.value === 'seedream-5-0-lite'
})

const isGenerateDisabled = computed(() => {
  if (!prompt.value.trim()) return true
  if (currentMode.value === 'image-to-image' && referenceImages.value.length === 0) {
    return true
  }
  return false
})

// 使用计算属性而不是函数
const atFilesList = computed(() => {
  return referenceImages.value.map(f => ({
    ...f,
    fileType: f.type?.startsWith('video/') ? 'video' : 'image'
  }))
})

const {
  showAtSuggestions,
  showTemplateSuggestions,
  templateSearchTerm,
  filteredTemplates,
  handlePromptInput,
  handleKeydown,
  selectAtFile,
  selectTemplate,
  buildPromptMapping,
  replacePromptCodes,
} = usePromptInput({ prompt, promptTextarea, atFilesList, templates })

const handleDropToReference = (e) => {
  e.preventDefault()
  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'))
    if (data.url && data.type === 'image') {
      referenceImages.value.push({
        id: Date.now() + Math.random(),
        url: data.url,
        name: `drag-${data.task_id?.substring(0, 6) || 'image'}.jpg`,
        type: 'image/jpeg'
      })
    }
  } catch (err) {
    // Drag data parse error
  }
}

const handleModelChange = createModelChangeHandler(selectedModel, resolution, IMAGE_MODELS)

const handleGenerate = () => {
  // 替换提示词中的 @代码为实际的 URL
  const processedPrompt = replacePromptCodes(prompt.value)
  
  const params = {
    type: 'image',
    model: selectedModel.value,
    aspect_ratio: aspectRatio.value,
    resolution: resolution.value,
    prompt: processedPrompt,
    displayPrompt: prompt.value, // 保存用户友好的显示版本
    mode: currentMode.value,
    reference_images: referenceImages.value.map(f => ({
      id: f.id,
      url: f.url,
      name: f.name,
      originalName: f.originalName,
      displayName: f.displayName,
      shortCode: f.shortCode
    })),
    portrait_auth: portraitAuth.value
  }
  emit('generate', params)
}

const handleReEdit = (result) => {
  const params = result.params
  currentMode.value = params.mode || 'text-to-image'
  selectedModel.value = params.model
  aspectRatio.value = params.aspect_ratio
  resolution.value = params.resolution
  // 优先使用用户友好的 displayPrompt，如果没有才用 prompt
  prompt.value = params.displayPrompt || params.prompt
  if (params.reference_images && params.reference_images.length > 0) {
    referenceImages.value = params.reference_images.map(f => ({
      ...f,
      type: 'image/jpeg'
    }))
  } else {
    referenceImages.value = []
  }
  portraitAuth.value = params.portrait_auth || false
}

const openModal = (url) => {
  modalUrl.value = url
  modalType.value = 'image'
  modalVisible.value = true
}

const closeModal = () => {
  modalVisible.value = false
}

const setPrompt = (text) => {
  prompt.value = text
}

// 添加点击外部关闭功能
const handleOutsideClick = (e) => {
  // 如果点击不在建议框或文本框内，则关闭
  if (!e.target.closest('.prompt-wrapper')) {
    showAtSuggestions.value = false
    showTemplateSuggestions.value = false
  }
}

// 组件挂载时添加全局事件监听
onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
  // 初始化默认清晰度
  const modelConfig = IMAGE_MODELS[selectedModel.value]
  if (modelConfig) {
    resolution.value = modelConfig.default_resolution || ''
  }
})

// 组件卸载时移除全局事件监听
onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick)
})

defineExpose({ handleReEdit, setPrompt })
</script>

<template>
  <div class="image-workspace">
    <div class="panel-header">
      <h2>🖼️ 图片生成</h2>
    </div>

    <div class="mode-section">
      <h3>模式</h3>
      <div class="mode-tabs">
        <button 
          v-for="mode in [{ id: 'text-to-image', name: '文生图' }, { id: 'image-to-image', name: '图生图' }]" 
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
            <option v-for="(model, key) in IMAGE_MODELS" :key="key" :value="key">
              {{ model.name }}
            </option>
          </select>
        </div>

        <div class="param-item param-item-flex" v-if="availableResolutions.length > 0">
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
      </div>

      <div class="param-item">
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

      <div class="param-item switch-item" v-if="showPortraitAuth">
        <label>人像授权</label>
        <div class="switch-wrapper">
          <label class="switch">
            <input type="checkbox" v-model="portraitAuth" />
            <span class="slider"></span>
          </label>
          <span class="switch-label">{{ portraitAuth ? '已开启' : '已关闭' }}</span>
        </div>
      </div>

      <div class="upload-section" v-if="currentMode === 'image-to-image'">
        <h3>参考图 (必需)</h3>
        <div class="drop-target" @drop="handleDropToReference" @dragover.prevent>
          <UploadArea v-model="referenceImages" :max-files="12" label="拖拽或点击上传参考图" />
        </div>
      </div>

      <div class="param-item prompt-item">
        <div class="prompt-label-row">
          <label @click="handlePromptLabelClick">提示词</label>
          <PromptHelper v-model="prompt" :is-enhanced="showEnhancedMode" :reference-images="referenceImages" />
        </div>
        <div class="prompt-wrapper">
          <div class="prompt-display" v-html="formatPrompt(prompt)"></div>
          <textarea 
            ref="promptTextarea"
            v-model="prompt" 
            placeholder="输入描述... (输入 @ 唤起已上传图片，输入 # 唤起模板)"
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
                <span v-else class="video-thumb">🎬</span>
              </div>
              <span class="name">{{ file.shortCode || `图片${index + 1}` }}</span>
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
          🚀 生成图片
        </button>
        <div v-if="!isGenerateDisabled" class="cost-tooltip">
          <div class="cost-tooltip-content">
            <div class="cost-value">{{ formatImageCostDisplay() }}</div>
          </div>
        </div>
      </div>
    </div>

    <Modal :visible="modalVisible" :type="modalType" :url="modalUrl" @close="closeModal" />
  </div>
</template>

<style scoped>
.image-workspace {
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

.params-section .upload-section {
  border-bottom: none;
  padding: 0;
  margin-bottom: 15px;
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
  gap: 15px;
  flex-wrap: nowrap;
}

.prompt-label-row label {
  flex-shrink: 0;
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

.video-thumb {
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
</style>