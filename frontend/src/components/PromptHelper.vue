<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch, inject } from 'vue'
import { API_BASE_URL } from '../utils/config.js'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  isEnhanced: {
    type: Boolean,
    default: false
  },
  referenceImages: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const toast = inject('toast', { error: (msg) => console.error(msg) })

const buildPromptMapping = () => {
  const mapping = {}
  const files = atFilesList.value
  files.forEach((file, index) => {
    const shortCode = file.shortCode || (file.fileType === 'video' ? `视频${index + 1}` : `图片${index + 1}`)
    const key = '@' + shortCode
    mapping[key] = file.url
  })
  return mapping
}

const atFilesList = computed(() => {
  return props.referenceImages.map(f => ({
    ...f,
    fileType: f.type?.startsWith('video/') ? 'video' : 'image'
  }))
})

// 替换提示词中的 @代码为实际的 URL
const replacePromptCodes = (text) => {
  const mapping = buildPromptMapping()
  let result = text
  for (const [code, url] of Object.entries(mapping)) {
    // 正则转义特殊字符
    const escapedCode = code.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    result = result.replace(new RegExp(escapedCode, 'g'), url)
  }
  return result
}

// 把 URL 换回 @代码
const restorePromptCodes = (text) => {
  const mapping = buildPromptMapping()
  let result = text
  for (const [code, url] of Object.entries(mapping)) {
    // 正则转义特殊字符
    const escapedUrl = url.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&')
    result = result.replace(new RegExp(escapedUrl, 'g'), code)
  }
  return result
}

const isLoading = ref(false)
const quickPresets = ref({})
const showPresetPanel = ref(false)
const selectedPresetCategory = ref('style')
const showSuggestionPanel = ref(false)
const suggestionOptions = ref([])
const selectedText = ref('')
const selectionStart = ref(0)
const selectionEnd = ref(0)
const currentActionType = ref(null) // 'complete', 'replace', 'reference'
const expandedOptions = ref({}) // 存储展开状态的对象

// 切换展开状态
const toggleExpand = (index) => {
  expandedOptions.value[index] = !expandedOptions.value[index]
}

const helperWrapperRef = ref(null)
let activeTextarea = null
let lastCursorPos = 0

const getCatName = (cat) => {
  const names = {
    'lens': '镜头',
    'style': '风格',
    'quality': '画质',
    'lighting': '光影',
    'composition': '构图',
    'direction': '朝向',
    'angle': '角度',
    'mood': '氛围',
    'environment': '环境'
  }
  return names[cat] || cat
}

const fetchQuickPresets = async () => {
  try {
    const res = await fetch(API_BASE_URL + '/api/quick-presets')
    const data = await res.json()
    if (data.success) {
      quickPresets.value = data.data
    }
  } catch (e) {
    console.error('获取快捷预设失败', e)
  }
}

const currentButtonType = computed(() => {
  if (!props.isEnhanced) return null
  
  const text = props.modelValue || ''
  if (!text.trim()) return null
  
  const start = selectionStart.value
  const end = selectionEnd.value
  
  if (start !== end) {
    if (start === 0 && end === text.length) {
      return 'masterpiece'
    } else {
      return 'local'
    }
  }
  
  return 'optimize'
})

const currentButtonText = computed(() => {
  const type = currentButtonType.value
  if (type === 'optimize') return '优化'
  if (type === 'local') return '局部调优'
  if (type === 'masterpiece') return '一键封神'
  return ''
})

const currentButtonClass = computed(() => {
  const type = currentButtonType.value
  if (type === 'optimize') return 'optimize'
  if (type === 'local') return 'local-optimize'
  if (type === 'masterpiece') return 'masterpiece'
  return ''
})

const findAndBindTextarea = () => {
  if (!helperWrapperRef.value) return

  unbindTextarea()

  let textarea = null
  let parent = helperWrapperRef.value.parentElement
  let count = 0
  while (parent && !textarea && count < 10) {
    textarea = parent.querySelector('textarea')
    if (!textarea) {
      parent = parent.parentElement
    }
    count++
  }

  if (textarea) {
    activeTextarea = textarea
    textarea.addEventListener('mouseup', updateSelection)
    textarea.addEventListener('keyup', updateSelection)
    textarea.addEventListener('input', handleInput)
    textarea.addEventListener('click', updateSelection)
    textarea.addEventListener('select', updateSelection)
  }
}

const unbindTextarea = () => {
  if (activeTextarea) {
    activeTextarea.removeEventListener('mouseup', updateSelection)
    activeTextarea.removeEventListener('keyup', updateSelection)
    activeTextarea.removeEventListener('input', handleInput)
    activeTextarea.removeEventListener('click', updateSelection)
    activeTextarea.removeEventListener('select', updateSelection)
    activeTextarea = null
  }
}

const updateSelection = () => {
  if (activeTextarea) {
    const text = props.modelValue || ''
    const start = activeTextarea.selectionStart
    const end = activeTextarea.selectionEnd
    selectedText.value = text.substring(start, end)
    selectionStart.value = start
    selectionEnd.value = end
  }
}

const handleInput = (e) => {
  const text = e.target.value
  const cursorPos = e.target.selectionStart
  lastCursorPos = cursorPos

  if (cursorPos > 0 && text[cursorPos - 1] === '&') {
    showPresetPanel.value = true
    selectedPresetCategory.value = 'style'
  }
  
  updateSelection()
}

const handleButtonClick = () => {
  const type = currentButtonType.value
  if (type === 'optimize') {
    handleAutoComplete()
  } else if (type === 'local') {
    handleLocalOptimize()
  } else if (type === 'masterpiece') {
    handleMasterpiece()
  }
}

const handleAutoComplete = async () => {
  if (!props.modelValue.trim()) return

  isLoading.value = true
  try {
    const mapping = buildPromptMapping()
    // 先替换 @代码为真实 URL
    const userInputWithUrls = replacePromptCodes(props.modelValue)
    
    const res = await fetch(API_BASE_URL + '/api/prompt-helper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_input: userInputWithUrls,
        action_type: 'complete',
        reference_mapping: mapping
      })
    })
    const data = await res.json()
    if (data.success && data.data) {
      // 把结果中的 URL 换回 @代码
      const rawOptions = data.data.options || []
      suggestionOptions.value = rawOptions.map(opt => restorePromptCodes(opt))
      currentActionType.value = 'complete'
      showSuggestionPanel.value = true
    }
  } catch (e) {
    console.error('自动补全失败', e)
    toast.error('自动补全失败，请重试')
  } finally {
    isLoading.value = false
  }
}

const handleLocalOptimize = async () => {
  if (!selectedText.value || !props.modelValue.trim()) return

  isLoading.value = true
  try {
    const mapping = buildPromptMapping()
    const userInputWithUrls = replacePromptCodes(props.modelValue)
    const selectedTextWithUrls = replacePromptCodes(selectedText.value)
    
    const res = await fetch(API_BASE_URL + '/api/prompt-helper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_input: userInputWithUrls,
        action_type: 'replace',
        selected_text: selectedTextWithUrls,
        reference_mapping: mapping
      })
    })
    const data = await res.json()
    if (data.success && data.data) {
      const rawOptions = data.data.options || []
      suggestionOptions.value = rawOptions.map(opt => restorePromptCodes(opt))
      currentActionType.value = 'replace'
      showSuggestionPanel.value = true
    }
  } catch (e) {
    console.error('局部调优失败', e)
    toast.error('局部调优失败，请重试')
  } finally {
    isLoading.value = false
  }
}

const handleMasterpiece = async () => {
  if (!props.modelValue.trim()) return

  isLoading.value = true
  try {
    const mapping = buildPromptMapping()
    const userInputWithUrls = replacePromptCodes(props.modelValue)
    
    const res = await fetch(API_BASE_URL + '/api/prompt-helper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_input: userInputWithUrls,
        action_type: 'reference',
        reference_mapping: mapping
      })
    })
    const data = await res.json()
    
    if (data.success && data.data) {
      const rawOptions = data.data.options || []
      suggestionOptions.value = rawOptions.map(opt => restorePromptCodes(opt))
      currentActionType.value = 'reference'
      showSuggestionPanel.value = true
    }
  } catch (e) {
    console.error('一键封神失败', e)
    toast.error('一键封神失败，请重试')
  } finally {
    isLoading.value = false
  }
}

const selectSuggestionOption = (option) => {
  // 根据操作类型进行不同的处理
  if (currentActionType.value === 'complete') {
    // 续写：直接使用返回的内容
    emit('update:modelValue', option)
  } else if (currentActionType.value === 'replace') {
    // 替换：用选中的选项替换之前选中的内容
    if (selectionStart.value >= 0 && selectionEnd.value > selectionStart.value) {
      const before = props.modelValue.substring(0, selectionStart.value)
      const after = props.modelValue.substring(selectionEnd.value)
      const newValue = before + option + after
      emit('update:modelValue', newValue)
    }
  } else if (currentActionType.value === 'reference') {
    // 参考：完全替换为新内容
    emit('update:modelValue', option)
  }
  
  showSuggestionPanel.value = false
}

const selectPreset = (preset) => {
  let newValue = ''
  const textarea = activeTextarea
  const cursorPos = lastCursorPos || 0
  if (textarea) {
    const before = props.modelValue.substring(0, cursorPos)
    const after = props.modelValue.substring(cursorPos)
    const needsComma = before.trim() && !before.trim().endsWith(',')
    newValue = before
    if (needsComma) newValue += ', '
    newValue += preset.value
    if (after.trim() && !after.trim().startsWith(',')) {
      newValue += ', '
    }
    newValue += after
    emit('update:modelValue', newValue)
    
    nextTick(() => {
      const newPos = cursorPos + (needsComma ? 2 : 0) + preset.value.length
      textarea.focus()
      textarea.selectionStart = textarea.selectionEnd = newPos
    })
  } else {
    newValue = props.modelValue.trim()
    if (newValue && !newValue.endsWith(',')) {
      newValue += ', '
    }
    newValue += preset.value
    emit('update:modelValue', newValue)
  }
  showPresetPanel.value = false
}

// 监听增强模式变化
watch(() => props.isEnhanced, (newVal) => {
  if (newVal) {
    nextTick(() => {
      findAndBindTextarea()
      setTimeout(() => updateSelection(), 50)
    })
  }
})

onMounted(() => {
  fetchQuickPresets()
})

onUnmounted(() => {
  unbindTextarea()
})
</script>

<template>
  <div class="prompt-helper-wrapper" ref="helperWrapperRef">
    <div v-if="props.isEnhanced" class="center-buttons">
      <button v-if="currentButtonType && !isLoading" class="action-btn dynamic-btn" :class="currentButtonClass" @click="handleButtonClick">
        {{ currentButtonText }}
      </button>
      <div v-if="isLoading" class="action-btn loading">生成中...</div>
      <button class="action-btn presets-btn" @click="showPresetPanel = true" title="快捷预设">快捷预设</button>
    </div>

    <div v-if="showPresetPanel" class="preset-panel-overlay" @click="showPresetPanel = false">
      <div class="preset-panel" @click.stop>
        <div class="panel-header">
          <span>快捷预设</span>
          <button @click="showPresetPanel = false" class="close-btn">X</button>
        </div>
        <div class="preset-categories">
          <button v-for="cat in Object.keys(quickPresets)" :key="cat" :class="['cat-btn', { active: selectedPresetCategory === cat }]" @click="selectedPresetCategory = cat">
            {{ getCatName(cat) }}
          </button>
        </div>
        <div class="preset-list">
          <div v-for="preset in quickPresets[selectedPresetCategory]" :key="preset.name" class="preset-item" @click="selectPreset(preset)">
            {{ preset.name }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="showSuggestionPanel" class="suggestion-panel-overlay" @click="showSuggestionPanel = false">
      <div class="suggestion-panel" @click.stop>
        <div class="panel-header">
          <span>选择方案</span>
          <button @click="showSuggestionPanel = false" class="close-btn">X</button>
        </div>
        <div class="suggestion-list">
          <div v-for="(option, index) in suggestionOptions" :key="index" class="suggestion-item" @click.stop="toggleExpand(index)">
            <div class="suggestion-title">
              方案 {{ index + 1 }}
              <span class="expand-btn">{{ expandedOptions[index] ? '收起' : '展开' }}</span>
            </div>
            <div class="suggestion-content" :class="{ expanded: expandedOptions[index] }">{{ option }}</div>
            <div class="use-btn" @click.stop="selectSuggestionOption(option)">使用此方案</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.prompt-helper-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.center-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  justify-content: center;
}

.action-btn {
  padding: 6px 16px;
  border-radius: 16px;
  font-size: 0.85rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid rgba(0, 212, 255, 0.3);
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
  white-space: nowrap;
}

.dynamic-btn {
  padding: 6px 16px;
  font-size: 0.85rem;
}

.optimize {
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
  border-color: rgba(0, 212, 255, 0.3);
}

.optimize:hover {
  background: rgba(0, 212, 255, 0.3);
  transform: translateY(-1px);
}

.local-optimize {
  background: rgba(255, 165, 0, 0.2);
  color: #ffa500;
  border-color: rgba(255, 165, 0, 0.3);
}

.local-optimize:hover {
  background: rgba(255, 165, 0, 0.3);
  transform: translateY(-1px);
}

.masterpiece {
  background: rgba(255, 215, 0, 0.2);
  color: #ffd700;
  border-color: rgba(255, 215, 0, 0.3);
}

.masterpiece:hover {
  background: rgba(255, 215, 0, 0.3);
  transform: translateY(-1px);
}

.presets-btn {
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
  border-color: rgba(0, 212, 255, 0.3);
}

.presets-btn:hover {
  background: rgba(0, 212, 255, 0.3);
  transform: translateY(-1px);
}

.loading {
  background: rgba(150, 150, 150, 0.2);
  color: #aaa;
  border: 1px solid rgba(150, 150, 150, 0.3);
  cursor: not-allowed;
}

.preset-panel-overlay,
.suggestion-panel-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1001;
}

.preset-panel,
.suggestion-panel {
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 12px;
  width: 500px;
  max-height: 80vh;
  overflow-y: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #333;
  font-weight: bold;
  color: #00d4ff;
}

.close-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.close-btn:hover {
  background: #333;
  color: #fff;
}

.preset-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px 0;
}

.cat-btn {
  padding: 6px 12px;
  background: #2a2a4a;
  color: #aaa;
  border: none;
  border-radius: 16px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.cat-btn:hover {
  background: #3a3a5a;
  color: #fff;
}

.cat-btn.active {
  background: #00d4ff;
  color: #000;
}

.preset-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  padding: 12px 16px 16px;
}

.preset-item {
  padding: 10px 14px;
  background: #2a2a4a;
  color: #fff;
  border: 1px solid #333;
  border-radius: 8px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.preset-item:hover {
  background: #3a3a5a;
  border-color: #00d4ff;
}

.suggestion-list {
  padding: 12px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.suggestion-item {
  padding: 12px 14px;
  background: #2a2a4a;
  border: 1px solid #333;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-item:hover {
  background: #3a3a5a;
  border-color: #00d4ff;
}

.suggestion-title {
  font-weight: bold;
  color: #00d4ff;
  margin-bottom: 6px;
  font-size: 0.9rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.expand-btn {
  color: #888;
  font-size: 0.75rem;
  cursor: pointer;
  font-weight: normal;
}

.expand-btn:hover {
  color: #00d4ff;
}

.suggestion-content {
  color: #ccc;
  font-size: 0.8rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: all 0.3s ease;
}

.suggestion-content.expanded {
  display: block;
  -webkit-line-clamp: unset;
  max-height: 400px;
  overflow-y: auto;
}

.use-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 6px;
  text-align: center;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.use-btn:hover {
  background: rgba(0, 212, 255, 0.3);
  transform: translateY(-1px);
}
</style>
