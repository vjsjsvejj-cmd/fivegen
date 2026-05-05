<script setup>
import { ref, computed, watch, onMounted, nextTick, inject } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import socketManager from '../../utils/socket'
import { API_BASE_URL } from '../../utils/config'
import { NODE_COLORS, getOutputNodeAccent, getOutputNodeGlow, getOutputModeKey, TASK_TYPE_LABELS, TASK_TYPE_ICONS } from './fivetv-theme'
import { IMAGE_MODELS, VIDEO_MODELS, FIVETV_ASPECT_RATIOS as ASPECT_RATIOS, VIDEO_RESOLUTION_CONFIG, FRAME_RATE } from '../../config/models.js'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:data'])

const { findNode, onConnect, onEdgesChange, getEdges, updateNode } = useVueFlow()
const nodeDataChangeCounter = inject('nodeDataChangeCounter', ref(0))
const activeOutputPanelId = inject('activeOutputPanelId', ref(null))

const promptRef = ref(null)
const promptWrapperRef = ref(null)

const outputMode = ref(props.data.outputMode || 'image')
const videoMode = ref(props.data.videoMode || 'reference')
const imageMode = ref(props.data.imageMode || 'text-to-image')
const selectedModel = ref(props.data.selectedModel || 'nano-banana-2')
const aspectRatio = ref(props.data.aspectRatio || 'auto')
const resolution = ref(props.data.resolution || '1K')
const duration = ref(props.data.duration || '5s')
const prompt = ref(props.data.prompt || '')
const portraitAuth = ref(props.data.portraitAuth || false)

const toggleOutputMode = () => {
  const newMode = outputMode.value === 'image' ? 'video' : 'image'
  outputMode.value = newMode
  
  const models = newMode === 'image' ? IMAGE_MODELS : VIDEO_MODELS
  const firstKey = Object.keys(models)[0]
  if (firstKey) {
    selectedModel.value = firstKey
    resolution.value = models[firstKey].default_resolution
  }
}

const isGenerating = ref(false)
const generatedResult = ref(props.data.result || null)
const showPanel = ref(false)
const currentTaskId = ref(null)
const generateProgress = ref(0)

const showAtPopup = ref(false)
const atPopupPosition = ref({ top: 0, left: 0 })
const atSearchText = ref('')
const selectedAtIndex = ref(0)

const showSlashPopup = ref(false)
const slashPopupPosition = ref({ top: 0, left: 0 })
const slashSearchText = ref('')
const selectedSlashIndex = ref(0)

const slashCommands = [
  { key: 'style', label: '风格', desc: '设置图片风格', value: '--style ' },
  { key: 'seed', label: '随机种子', desc: '固定随机种子', value: '--seed ' },
  { key: 'quality', label: '质量', desc: '设置输出质量', value: '--quality ' },
  { key: 'negative', label: '负面提示词', desc: '不想要出现的内容', value: '--no ' },
  { key: 'strength', label: '重绘幅度', desc: '图生图重绘强度0-1', value: '--strength ' },
]

const sourceData = computed(() => {
  const edges = getEdges.value
  void nodeDataChangeCounter.value

  const ids = edges
    .filter(e => e.target === props.id)
    .map(e => e.source)

  const data = {
    prompts: [],
    imageUrls: [],
    images: [],
    videoUrl: null,
    videos: []
  }

  ids.forEach(sourceId => {
    const node = findNode(sourceId)
    if (!node?.data) return

    if (node.data.prompt) {
      data.prompts.push(node.data.prompt)
    }
    if (node.data.imageUrl) {
      data.imageUrls.push(node.data.imageUrl)
      data.images.push({
        url: node.data.imageUrl,
        name: node.data.imageName || '图片',
        tag: `图${data.images.length + 1}`
      })
    }
    if (node.data.videoUrl) {
      data.videoUrl = node.data.videoUrl
      data.videos.push({
        url: node.data.videoUrl,
        name: node.data.videoName || '视频',
        tag: '视频'
      })
    }
  })

  return data
})

const mentionSources = computed(() => {
  const items = []
  sourceData.value.images.forEach((img) => {
    items.push({ type: 'image', label: img.tag, name: img.name, url: img.url, tag: img.tag })
  })
  sourceData.value.videos.forEach((vid) => {
    items.push({ type: 'video', label: '视频', name: vid.name, url: vid.url, tag: '视频' })
  })
  if (atSearchText.value) {
    return items.filter(i => i.label.includes(atSearchText.value) || i.name.includes(atSearchText.value))
  }
  return items
})

const filteredCommands = computed(() => {
  if (!slashSearchText.value) return slashCommands
  return slashCommands.filter(c =>
    c.label.includes(slashSearchText.value) || c.key.includes(slashSearchText.value)
  )
})

const combinedPrompt = computed(() => {
  return [...sourceData.value.prompts, prompt.value].filter(Boolean).join('\n')
})

const availableResolutions = computed(() => {
  const models = outputMode.value === 'image' ? IMAGE_MODELS : VIDEO_MODELS
  const model = models[selectedModel.value]
  return model ? model.resolutions : []
})

const availableDurations = computed(() => {
  if (outputMode.value === 'video') {
    const model = VIDEO_MODELS[selectedModel.value]
    return model ? model.durations : []
  }
  return []
})

const calculateVideoTokens = () => {
  const outputDuration = parseInt(duration.value.replace('s', ''))
  const resolutionConfig = VIDEO_RESOLUTION_CONFIG[resolution.value]?.[aspectRatio.value]
  
  if (!resolutionConfig) return null
  
  const { width, height } = resolutionConfig
  
  // 检查是否有参考视频
  let inputDuration = 0
  if (sourceData.value.videos.length > 0) {
    // 这里暂时用 0，实际可以从视频数据获取
    inputDuration = 0
  }
  
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
  return formatted
}

const currentCost = computed(() => {
  if (outputMode.value === 'video') {
    const tokens = calculateVideoTokens()
    if (tokens) {
      return tokens.value.toFixed(2)
    }
    return 0
  }
  
  const models = IMAGE_MODELS
  const model = models[selectedModel.value]
  return model?.cost || 0
})

const costType = computed(() => {
  const models = outputMode.value === 'image' ? IMAGE_MODELS : VIDEO_MODELS
  const model = models[selectedModel.value]
  return model?.costType || (outputMode.value === 'video' ? 'token' : 'points')
})

const currentModelInfo = computed(() => {
  const models = outputMode.value === 'image' ? IMAGE_MODELS : VIDEO_MODELS
  return models[selectedModel.value]
})

const taskType = computed(() => {
  const d = sourceData.value
  const hasPrompt = !!combinedPrompt.value.trim()
  const hasImage = d.imageUrls.length > 0
  const hasMultipleImages = d.imageUrls.length >= 2
  const hasVideo = d.videos.length > 0

  if (outputMode.value === 'video') {
    if (videoMode.value === 'text-to-video') return '文生视频'
    if (videoMode.value === 'frame') return '首尾帧'
    if (videoMode.value === 'reference') return '多模态'
    return '视频生成'
  }

  if (imageMode.value === 'text-to-image') return '文生图'
  if (imageMode.value === 'image-to-image') return '图生图'
  return '图片生成'
})

const canGenerate = computed(() => {
  if (outputMode.value === 'video') {
    return !!combinedPrompt.value.trim() || sourceData.value.videoUrl || sourceData.value.imageUrls.length > 0
  }
  return !!combinedPrompt.value.trim() || sourceData.value.imageUrls.length > 0
})

const updateSourceNodes = () => {
  const edges = getEdges.value
  const newSourceIds = edges
    .filter(e => e.target === props.id)
    .map(e => e.source)

  const hasImageInput = newSourceIds.some(newId => {
    const node = findNode(newId)
    return node?.type === 'imageUpload' || (node?.type === 'output' && node?.data?.outputMode === 'image')
  })

  const hasVideoInput = newSourceIds.some(newId => {
    const node = findNode(newId)
    return node?.type === 'videoUpload' || (node?.type === 'output' && node?.data?.outputMode === 'video')
  })

  const hasVideo = newSourceIds.some(newId => {
    const node = findNode(newId)
    return node?.data?.videoUrl
  })

  if (hasVideo && outputMode.value !== 'video') {
    outputMode.value = 'video'
    selectedModel.value = Object.keys(VIDEO_MODELS)[0]
  }

  updateNode(props.id, {
    data: {
      ...props.data,
      hasImageInput,
      hasVideoInput
    }
  })
}

const accentColor = computed(() => {
  const edges = getEdges.value
  const node = { id: props.id, type: 'output', data: { ...props.data, outputMode: outputMode.value } }
  return getOutputNodeAccent(node, edges)
})

const accentGlow = computed(() => {
  const edges = getEdges.value
  const node = { id: props.id, type: 'output', data: { ...props.data, outputMode: outputMode.value } }
  return getOutputNodeGlow(node, edges)
})

const taskTypeLabel = computed(() => {
  const node = { id: props.id, type: 'output', data: { ...props.data, outputMode: outputMode.value } }
  const modeKey = getOutputModeKey(node)
  return TASK_TYPE_LABELS[modeKey] || taskType.value
})

const taskTypeIcon = computed(() => {
  const node = { id: props.id, type: 'output', data: { ...props.data, outputMode: outputMode.value } }
  const modeKey = getOutputModeKey(node)
  return TASK_TYPE_ICONS[modeKey] || (outputMode.value === 'image' ? '🎨' : '🎬')
})

const handleModelChange = (e) => {
  const modelKey = e.target.value
  selectedModel.value = modelKey
  const models = outputMode.value === 'image' ? IMAGE_MODELS : VIDEO_MODELS
  const modelConfig = models[modelKey]
  if (modelConfig) resolution.value = modelConfig.default_resolution
}

const handlePromptInput = (e) => {
  const textarea = e.target
  const text = textarea.value
  const cursorPos = textarea.selectionStart

  const textBeforeCursor = text.substring(0, cursorPos)
  const atMatch = textBeforeCursor.match(/@(\S*)$/)
  if (atMatch !== null) {
    atSearchText.value = atMatch[1]
    selectedAtIndex.value = 0
    showAtPopup.value = mentionSources.value.length > 0
    showSlashPopup.value = false

    const lines = textBeforeCursor.split('\n')
    const lineIndex = lines.length - 1
    const lineHeight = 26

    atPopupPosition.value = {
      top: lineIndex * lineHeight + lineHeight + 4,
      left: 8
    }
  } else {
    showAtPopup.value = false
  }

  const slashMatch = textBeforeCursor.match(/\/(\S*)$/)
  if (slashMatch !== null && atMatch === null) {
    slashSearchText.value = slashMatch[1]
    selectedSlashIndex.value = 0
    showSlashPopup.value = filteredCommands.value.length > 0

    const lines = textBeforeCursor.split('\n')
    const lineIndex = lines.length - 1
    const lineHeight = 26

    slashPopupPosition.value = {
      top: lineIndex * lineHeight + lineHeight + 4,
      left: 8
    }
  } else if (slashMatch === null) {
    showSlashPopup.value = false
  }
}

const selectAtMention = (item) => {
  const textarea = promptRef.value
  if (!textarea) return

  const text = textarea.value
  const cursorPos = textarea.selectionStart
  const beforeAt = text.substring(0, cursorPos).replace(/@\S*$/, '')
  const afterAt = text.substring(cursorPos)

  prompt.value = beforeAt + `[@${item.tag}] ` + afterAt
  showAtPopup.value = false

  nextTick(() => {
    textarea.focus()
    const newPos = beforeAt.length + `[@${item.tag}] `.length
    textarea.setSelectionRange(newPos, newPos)
  })
}

const insertAtTag = (tag) => {
  const textarea = promptRef.value
  if (!textarea) return

  const cursorPos = textarea.selectionStart
  const text = prompt.value
  prompt.value = text.substring(0, cursorPos) + `[@${tag}] ` + text.substring(cursorPos)

  nextTick(() => {
    textarea.focus()
    const newPos = cursorPos + `[@${tag}] `.length
    textarea.setSelectionRange(newPos, newPos)
  })
}

const selectSlashCommand = (cmd) => {
  const textarea = promptRef.value
  if (!textarea) return

  const text = textarea.value
  const cursorPos = textarea.selectionStart
  const beforeSlash = text.substring(0, cursorPos).replace(/\/\S*$/, '')
  const afterSlash = text.substring(cursorPos)

  prompt.value = beforeSlash + cmd.value + afterSlash
  showSlashPopup.value = false

  nextTick(() => {
    textarea.focus()
    const newPos = beforeSlash.length + cmd.value.length
    textarea.setSelectionRange(newPos, newPos)
  })
}

const handlePromptKeydown = (e) => {
  if (showAtPopup.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedAtIndex.value = Math.min(selectedAtIndex.value + 1, mentionSources.value.length - 1)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedAtIndex.value = Math.max(selectedAtIndex.value - 1, 0)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const item = mentionSources.value[selectedAtIndex.value]
      if (item) selectAtMention(item)
    } else if (e.key === 'Escape') {
      showAtPopup.value = false
    }
  } else if (showSlashPopup.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedSlashIndex.value = Math.min(selectedSlashIndex.value + 1, filteredCommands.value.length - 1)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedSlashIndex.value = Math.max(selectedSlashIndex.value - 1, 0)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const cmd = filteredCommands.value[selectedSlashIndex.value]
      if (cmd) selectSlashCommand(cmd)
    } else if (e.key === 'Escape') {
      showSlashPopup.value = false
    }
  }
}

const handleGenerate = async () => {
  if (isGenerating.value || !canGenerate.value) return

  isGenerating.value = true
  generateProgress.value = 0
  const taskId = `five-tv-${props.id}-${Date.now()}`
  currentTaskId.value = taskId
  console.log('🚀 开始生成 - 任务ID:', taskId, '模式:', outputMode.value)

  const progressHandler = (data) => {
    if (data.task_id === taskId) {
      generateProgress.value = data.progress || 0
    }
  }

  socketManager.on('generation_progress', progressHandler)

  try {
    if (outputMode.value === 'image') {
      const params = {
        task_id: taskId,
        mode: getGenerationMode(),
        model: selectedModel.value,
        aspect_ratio: aspectRatio.value,
        resolution: resolution.value,
        prompt: combinedPrompt.value,
        displayPrompt: prompt.value,
        portrait_auth: portraitAuth.value
      }

      if (sourceData.value.imageUrls.length > 0) {
        params.reference_images = sourceData.value.images.map((img, idx) => ({
          id: `ref-${idx}-${Date.now()}`,
          url: img.url,
          name: img.name,
          displayName: img.name,
          shortCode: `图${idx + 1}`
        }))
      }

      console.log('📤 发送图片生成请求:', params)
      socketManager.generateImage(params)
    } else {
      const mode = getGenerationMode()

      const params = {
        task_id: taskId,
        mode: mode,
        model: selectedModel.value,
        aspect_ratio: aspectRatio.value,
        resolution: resolution.value,
        duration: duration.value,
        prompt: combinedPrompt.value,
        displayPrompt: prompt.value,
      }

      if (mode === 'frame' && sourceData.value.imageUrls.length >= 2) {
        params.first_frame_image = sourceData.value.images[0].url
        params.last_frame_image = sourceData.value.images[1].url
      } else if (mode === 'reference') {
        params.multimodal_files = []

        sourceData.value.images.forEach((img, idx) => {
          params.multimodal_files.push({
            id: `ref-${idx}-${Date.now()}`,
            url: img.url,
            name: img.name,
            displayName: img.name,
            shortCode: `图${idx + 1}`,
            type: 'image',
            role: sourceData.value.imageUrls.length === 1 ? 'reference_image' : (idx === 0 ? 'first_frame' : 'last_frame')
          })
        })

        sourceData.value.videos.forEach((vid) => {
          params.multimodal_files.push({
            id: `vid-${Date.now()}`,
            url: vid.url,
            name: vid.name,
            displayName: vid.name,
            shortCode: '视频',
            type: 'video',
            role: 'reference_video'
          })
        })
      }

      console.log('📤 发送视频生成请求:', params)
      socketManager.generateVideo(params)
    }

    console.log('⏳ 等待结果...', taskId)
    const result = await waitForResult(taskId)
    
    console.log('✅ 收到结果:', result)
    if (result) {
      generatedResult.value = result
      emit('update:data', {
        ...props.data,
        result: result,
        outputMode: outputMode.value,
        selectedModel: selectedModel.value,
        resolution: resolution.value,
        aspectRatio: aspectRatio.value,
        duration: duration.value,
        prompt: prompt.value,
        videoMode: videoMode.value,
        imageMode: imageMode.value
      })
    }
  } catch (error) {
    console.error('生成失败:', error)
  } finally {
    isGenerating.value = false
    generateProgress.value = 0
    currentTaskId.value = null
    socketManager.off('generation_progress', progressHandler)
  }
}

const getGenerationMode = () => {
  const d = sourceData.value
  const hasPrompt = !!combinedPrompt.value.trim()
  const hasImage = d.imageUrls.length > 0
  const hasMultipleImages = d.imageUrls.length >= 2
  const hasVideo = d.videos.length > 0

  if (outputMode.value === 'video') {
    if (videoMode.value) return videoMode.value
    if (hasMultipleImages && d.imageUrls.length === 2 && !hasVideo && !hasPrompt) return 'frame'
    if (hasVideo || hasImage) return 'reference'
    return 'text-to-video'
  }

  if (hasImage) return 'image-to-image'
  return 'text-to-image'
}

const getMediaUrl = (url) => {
  if (!url) return ''
  return url.startsWith('/') ? `${API_BASE_URL}${url}` : url
}

const waitForResult = (taskId) => {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup()
      reject(new Error('生成超时'))
    }, 300000)

    const onImageCompleted = (data) => {
      console.log('🎨 OutputNode 接收到 image_completed:', data.task_id, '=== 当前任务:', taskId)
      if (data.task_id === taskId) {
        cleanup()
        const result = {
          type: 'image',
          url: getMediaUrl(data.url || data.remote_url),
          remote_url: data.remote_url || data.url,
          displayName: data.displayName,
          duration: data.duration,
          cost: data.cost,
          params: data.params
        }
        console.log('✅ 解析后的结果:', result)
        resolve(result)
      }
    }

    const onVideoCompleted = (data) => {
      console.log('🎬 OutputNode 接收到 video_completed:', data.task_id, '=== 当前任务:', taskId)
      if (data.task_id === taskId) {
        cleanup()
        const result = {
          type: 'video',
          url: getMediaUrl(data.url || data.remote_url),
          remote_url: data.remote_url || data.url,
          thumbnail: getMediaUrl(data.thumbnail),
          displayName: data.displayName,
          duration: data.duration,
          cost: data.cost,
          params: data.params
        }
        console.log('✅ 解析后的结果:', result)
        resolve(result)
      }
    }

    socketManager.on('image_completed', onImageCompleted)
    socketManager.on('video_completed', onVideoCompleted)

    const cleanup = () => {
      clearTimeout(timeout)
      socketManager.off('image_completed', onImageCompleted)
      socketManager.off('video_completed', onVideoCompleted)
    }
  })
}

const handleClick = () => {
  const willShow = !showPanel.value
  showPanel.value = willShow
  if (willShow) {
    activeOutputPanelId.value = props.id
  }
}

const openResultUrl = () => {
  if (!generatedResult.value) return
  const url = generatedResult.value.remote_url || generatedResult.value.url
  if (url) window.open(url)
}

watch(() => activeOutputPanelId.value, (val) => {
  if (val !== props.id) {
    showPanel.value = false
  }
})

watch([videoMode, imageMode, outputMode], () => {
  updateNode(props.id, {
    data: {
      ...props.data,
      videoMode: videoMode.value,
      imageMode: imageMode.value,
      outputMode: outputMode.value
    }
  })
})

onMounted(() => {
  updateSourceNodes()
  
  onConnect((params) => {
    if (params.target === props.id) {
      updateSourceNodes()
    }
  })
  
  onEdgesChange(() => {
    updateSourceNodes()
  })
})
</script>

<template>
  <div class="gen-node" :class="{ 'is-video': outputMode === 'video', 'is-generating': isGenerating }" :style="{ '--tv-accent': accentColor, '--tv-accent-glow': accentGlow }">
    <Handle type="target" :position="Position.Left" id="input" class="handle-left" :connectable="true" />

    <div class="node-header">
      <span class="header-icon">{{ taskTypeIcon }}</span>
      <span class="header-title">{{ taskTypeLabel }}</span>
      <span class="header-status" v-if="isGenerating">{{ generateProgress }}%</span>
    </div>

    <div class="render-area" @click="handleClick">
      <div v-if="!generatedResult && !isGenerating" class="render-placeholder">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <path d="M21 15l-5-5L5 21"/>
        </svg>
      </div>

      <div v-else-if="isGenerating" class="render-loading">
        <div class="loading-spinner"></div>
        <span class="loading-text">生成中...</span>
      </div>

      <div v-else-if="generatedResult" class="render-result">
        <img
          v-if="generatedResult.type === 'image'"
          :src="generatedResult.url"
          alt="Generated"
          @click.stop="openResultUrl"
        />
        <video
          v-else
          :src="generatedResult.url"
          controls
          :poster="generatedResult.thumbnail"
        />
      </div>

      <Handle type="source" :position="Position.Right" id="output" class="handle-right" :connectable="true" />
    </div>

    <!-- 浮动操作面板 -->
    <div v-if="showPanel" class="gen-panel" @click.stop>
      <!-- 顶部工具栏 -->
      <div class="panel-toolbar">
        <span class="mode-label">
          <span class="mode-dot"></span>
          {{ outputMode === 'image' ? '图片' : '视频' }}
        </span>
        <div class="mode-buttons">
          <template v-if="outputMode === 'video'">
            <button :class="['mode-btn', { active: videoMode === 'text-to-video' }]" @click="videoMode = 'text-to-video'">文生视频</button>
            <button :class="['mode-btn', { active: videoMode === 'frame' }]" @click="videoMode = 'frame'">首尾帧</button>
            <button :class="['mode-btn', { active: videoMode === 'reference' }]" @click="videoMode = 'reference'">多模态</button>
          </template>
          <template v-else>
            <button :class="['mode-btn', { active: imageMode === 'text-to-image' }]" @click="imageMode = 'text-to-image'">文生图</button>
            <button :class="['mode-btn', { active: imageMode === 'image-to-image' }]" @click="imageMode = 'image-to-image'">图生图</button>
          </template>
        </div>
        <button class="toolbar-toggle-mode-btn" @click="outputMode = outputMode === 'image' ? 'video' : 'image'" :title="outputMode === 'image' ? '切换到视频' : '切换到图片'">
          {{ outputMode === 'image' ? '→🎬' : '→🎨' }}
        </button>
      </div>

      <!-- 提示词输入区 -->
      <div class="panel-prompt" style="overflow: visible;">
        <div class="prompt-wrapper" style="overflow: visible;">
          <textarea
            ref="promptRef"
            v-model="prompt"
            placeholder="描述你想要生成的画面内容... 输入 @ 引用素材，输入 / 使用参数"
            class="prompt-textarea"
            rows="8"
            @input="handlePromptInput"
            @keydown="handlePromptKeydown"
          ></textarea>

          <!-- 引用素材标签 -->
          <div class="prompt-tags" v-if="sourceData.images.length > 0 || sourceData.videos.length > 0">
            <span class="tag-label">已引用：</span>
            <span
              v-for="(img, idx) in sourceData.images"
              :key="'tag-img-' + idx"
              class="ref-tag ref-tag-image"
              @click="insertAtTag(img.tag)"
            >
              {{ img.tag }}
            </span>
            <span
              v-for="(vid, idx) in sourceData.videos"
              :key="'tag-vid-' + idx"
              class="ref-tag ref-tag-video"
              @click="insertAtTag(vid.tag)"
            >
              {{ vid.tag }}
            </span>
          </div>
        </div>

        <!-- @ 引用弹出 - 浮动在面板上方 -->
        <div
          v-if="showAtPopup"
          class="at-popup"
          :style="{ top: atPopupPosition.top + 'px', left: atPopupPosition.left + 'px' }"
          @click.stop
        >
          <div class="popup-header">
            <span class="popup-icon">@</span>
            <span class="popup-title">引用素材</span>
          </div>
          <div class="popup-items">
            <div
              v-for="(item, idx) in mentionSources"
              :key="idx"
              :class="['popup-item', { selected: idx === selectedAtIndex }]"
              @click="selectAtMention(item)"
              @mouseenter="selectedAtIndex = idx"
            >
              <div class="item-thumb">
                <img v-if="item.type === 'image'" :src="item.url" />
                <video v-else :src="item.url" muted />
              </div>
              <div class="item-info">
                <span class="item-label">{{ item.label }}</span>
                <span class="item-name">{{ item.name }}</span>
              </div>
            </div>
            <div v-if="mentionSources.length === 0" class="popup-empty">
              暂无可用素材，请先连接数据源
            </div>
          </div>
        </div>

        <!-- / 指令弹出 -->
        <div
          v-if="showSlashPopup"
          class="slash-popup"
          :style="{ top: slashPopupPosition.top + 'px', left: slashPopupPosition.left + 'px' }"
          @click.stop
        >
          <div class="popup-header">
            <span class="popup-icon">/</span>
            <span class="popup-title">参数指令</span>
          </div>
          <div class="popup-items">
            <div
              v-for="(cmd, idx) in filteredCommands"
              :key="cmd.key"
              :class="['popup-item', { selected: idx === selectedSlashIndex }]"
              @click="selectSlashCommand(cmd)"
              @mouseenter="selectedSlashIndex = idx"
            >
              <div class="item-info full">
                <span class="item-label">{{ cmd.label }}</span>
                <span class="item-desc">{{ cmd.desc }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部控制栏 -->
      <div class="panel-controls">
        <div class="controls-left">
          <div class="model-group">
            <select :value="selectedModel" @change="handleModelChange" class="model-select-hidden">
              <template v-if="outputMode === 'image'">
                <option v-for="(model, key) in IMAGE_MODELS" :key="key" :value="key">{{ model.name }}</option>
              </template>
              <template v-else>
                <option v-for="(model, key) in VIDEO_MODELS" :key="key" :value="key">{{ model.name }}</option>
              </template>
            </select>
            <span class="model-label">{{ currentModelInfo?.shortName }}</span>
            <svg class="model-switch-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>
          <select v-model="aspectRatio" class="ratio-select">
            <option v-for="ratio in ASPECT_RATIOS" :key="ratio" :value="ratio">{{ ratio }}</option>
          </select>
          <select v-model="resolution" class="res-select">
            <option v-for="res in availableResolutions" :key="res" :value="res">{{ res }}</option>
          </select>
          <template v-if="outputMode === 'video'">
            <select v-model="duration" class="dur-select">
              <option v-for="d in availableDurations" :key="d" :value="d">{{ d }}</option>
            </select>
          </template>
        </div>
        <div class="controls-right">
          <span class="cost-label">{{ currentCost }}{{ costType === 'yuan' ? '元' : (costType === 'token' ? 'token' : '积分') }}</span>
          <button
            :class="['send-btn', { loading: isGenerating }]"
            :disabled="isGenerating || !canGenerate"
            @click.stop="handleGenerate"
            title="生成"
          >
            <svg v-if="!isGenerating" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            <div v-else class="send-spinner"></div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gen-node {
  min-width: 320px;
  width: 340px;
  background: var(--tv-surface, #1e1e30);
  border: 2px solid var(--tv-accent, #f07088);
  border-radius: 8px;
  overflow: visible;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  position: relative;
}

.gen-node:hover {
  box-shadow: 0 0 16px var(--tv-accent-glow, rgba(240, 112, 136, 0.25));
}

.gen-node.is-generating {
  animation: pulse-border 2s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { box-shadow: 0 0 8px var(--tv-accent-glow, rgba(240, 112, 136, 0.15)); }
  50% { box-shadow: 0 0 20px var(--tv-accent-glow, rgba(240, 112, 136, 0.35)); }
}

.handle-right {
  top: 50% !important;
  transform: translateY(-50%) !important;
}

.node-header {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--tv-border, #353550);
  min-height: 30px;
  background: var(--tv-surface-alt, #222238);
}

.header-icon { 
  font-size: 0.85rem; 
  width: 16px; 
  height: 16px; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
}
.header-title { 
  color: var(--tv-accent, #f07088); 
  font-weight: 600; 
  font-size: 0.78rem; 
  flex: 1; 
}
.header-status { 
  color: var(--tv-success, #58b880); 
  font-size: 0.65rem; 
  font-weight: 600; 
}

.render-area {
  min-height: 191px;
  display: flex; align-items: center; justify-content: center;
  background: var(--tv-surface-deep, #181820);
  cursor: pointer;
  border-radius: 0 0 8px 8px;
  transition: background 0.12s ease;
}
.render-area:hover { background: var(--tv-bg, #14141c); }

.render-placeholder { text-align: center; color: var(--tv-text-muted, #585878); }

.render-loading { text-align: center; color: var(--tv-accent, #f07088); }
.loading-spinner {
  width: 32px; height: 32px;
  border: 2px solid rgba(240, 112, 136, 0.15);
  border-top-color: var(--tv-accent, #f07088);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin: 0 auto 8px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { font-size: 0.7rem; font-weight: 500; }

.render-result { width: 100%; }
.render-result img, .render-result video {
  width: 100%; max-height: 320px;
  object-fit: contain; display: block;
  border-radius: 0 0 8px 8px;
}

.gen-panel {
  position: absolute;
  top: 100%;
  left: -220px; right: -220px;
  margin-top: 16px;
  background: var(--tv-surface-alt, #222238);
  border: 2px solid var(--tv-accent, #f07088);
  border-radius: 10px;
  z-index: 1000;
  overflow: visible;
  min-width: 800px;
  animation: panelFadeIn 0.12s ease;
}

@keyframes panelFadeIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.panel-toolbar {
  display: flex; align-items: center;
  padding: 4px 10px;
  border-bottom: 1px solid var(--tv-border, #353550);
  gap: 8px;
  background: var(--tv-surface-alt, #222238);
  border-radius: 10px 10px 0 0;
}

.mode-label {
  display: flex; align-items: center; gap: 6px;
  color: var(--tv-text, #d0d4dc);
  font-size: 0.78rem;
  font-weight: 600;
  flex-shrink: 0;
}
.mode-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--tv-accent, #f07088);
}

.mode-buttons {
  display: flex; align-items: center; gap: 4px;
  flex: 1;
}

.mode-btn {
  padding: 4px 14px;
  background: var(--tv-surface, #1e1e30);
  border: 1.5px solid var(--tv-border, #353550);
  border-radius: 6px;
  color: var(--tv-text-sec, #8890a8);
  font-size: 0.73rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.1s ease, background 0.1s ease, color 0.1s ease;
  white-space: nowrap;
}
.mode-btn:hover {
  border-color: var(--tv-border-hover, #585878);
  color: var(--tv-text, #d0d4dc);
}
.mode-btn.active {
  background: var(--tv-surface-hover, #282840);
  border-color: var(--tv-accent, #f07088);
  color: var(--tv-accent, #f07088);
  font-weight: 700;
}

.toolbar-toggle-mode-btn {
  padding: 5px 12px;
  background: transparent;
  border: 1px solid var(--tv-border, #353550);
  border-radius: 6px;
  color: var(--tv-text-sec, #8890a8);
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.1s ease;
  flex-shrink: 0;
}
.toolbar-toggle-mode-btn:hover {
  border-color: var(--tv-accent, #f07088);
  color: var(--tv-accent, #f07088);
}

.panel-prompt { padding: 12px; position: relative; overflow: visible; }

.prompt-wrapper { position: relative; overflow: visible; }

.prompt-textarea {
  width: 100%;
  min-height: 120px;
  padding: 14px 16px;
  background: var(--tv-surface-deep, #181820);
  border: 1px solid var(--tv-border, #353550);
  border-radius: 8px;
  color: var(--tv-text, #d0d4dc);
  font-size: 0.85rem;
  resize: none;
  box-sizing: border-box;
  font-family: inherit;
  line-height: 1.6;
  transition: border-color 0.12s ease;
}
.prompt-textarea:focus {
  outline: none;
  border-color: var(--tv-accent, #f07088);
  background: var(--tv-bg, #14141c);
}
.prompt-textarea::placeholder { color: var(--tv-text-muted, #585878); }

.prompt-tags {
  display: flex; align-items: center; gap: 5px;
  padding: 8px 2px 0;
  flex-wrap: wrap;
}
.tag-label { color: var(--tv-text-muted, #585878); font-size: 0.68rem; font-weight: 500; }
.ref-tag {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 4px 9px;
  border-radius: 5px;
  font-size: 0.7rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.1s ease;
}
.ref-tag-image {
  background: rgba(74, 158, 255, 0.1);
  color: var(--tv-image-src, #4a9eff);
  border: 1px solid rgba(74, 158, 255, 0.2);
}
.ref-tag-image:hover { background: rgba(74, 158, 255, 0.18); }
.ref-tag-video {
  background: rgba(56, 200, 120, 0.1);
  color: var(--tv-video-src, #38c878);
  border: 1px solid rgba(56, 200, 120, 0.2);
}
.ref-tag-video:hover { background: rgba(56, 200, 120, 0.18); }

.at-popup, .slash-popup {
  position: absolute;
  background: var(--tv-surface, #1e1e30);
  border: 1px solid var(--tv-border, #353550);
  border-radius: 8px;
  z-index: 2000;
  min-width: 220px;
  max-width: 280px;
  overflow: hidden;
  animation: popupFadeIn 0.12s ease;
}

@keyframes popupFadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.popup-header {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px;
  background: var(--tv-surface-alt, #222238);
  border-bottom: 1px solid var(--tv-border, #353550);
}
.popup-icon {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  border-radius: 5px;
  font-weight: 700; font-size: 0.8rem;
}
.at-popup .popup-icon { background: rgba(74, 158, 255, 0.15); color: var(--tv-image-src, #4a9eff); }
.slash-popup .popup-icon { background: rgba(168, 104, 224, 0.15); color: var(--tv-output-vid, #a868e0); }
.popup-title { color: var(--tv-text-sec, #8890a8); font-size: 0.72rem; font-weight: 500; }

.popup-items { max-height: 180px; overflow-y: auto; padding: 4px; }
.popup-items::-webkit-scrollbar { width: 4px; }
.popup-items::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }

.popup-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.08s ease;
}
.popup-item:hover, .popup-item.selected { background: rgba(255, 255, 255, 0.04); }

.popup-empty {
  padding: 12px;
  text-align: center;
  color: rgba(255, 255, 255, 0.2);
  font-size: 0.72rem;
}

.item-thumb {
  width: 32px; height: 32px;
  border-radius: 4px; overflow: hidden;
  border: 1px solid var(--tv-border, #353550);
  flex-shrink: 0;
}
.item-thumb img, .item-thumb video { width: 100%; height: 100%; object-fit: cover; }

.item-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.item-info.full { gap: 2px; }
.item-label { color: var(--tv-text, #d0d4dc); font-size: 0.75rem; font-weight: 500; }
.item-name { color: var(--tv-text-muted, #585878); font-size: 0.65rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-desc { color: var(--tv-text-muted, #585878); font-size: 0.65rem; }

.panel-controls {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 10px;
  border-top: 1px solid var(--tv-border, #353550);
  gap: 6px;
  background: var(--tv-surface-alt, #222238);
  border-radius: 0 0 10px 10px;
}

.controls-left { display: flex; align-items: center; gap: 5px; flex: 1; min-width: 0; flex-wrap: wrap; }
.controls-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

.cost-label {
  color: var(--tv-cost, #e0c058);
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
}

.model-group {
  display: flex; align-items: center; gap: 4px;
  position: relative;
  padding: 4px 8px;
  background: var(--tv-surface-deep, #181820);
  border: 1px solid var(--tv-border, #353550);
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.1s ease;
}
.model-group:hover { border-color: var(--tv-border-hover, #585878); }
.model-select-hidden {
  position: absolute;
  left: 0; top: 0;
  width: 100%; height: 100%;
  opacity: 0;
  cursor: pointer;
  z-index: 2;
}
.model-label {
  color: var(--tv-text, #d0d4dc);
  font-size: 0.72rem;
  font-weight: 500;
  white-space: nowrap;
}
.model-switch-icon {
  color: var(--tv-text-muted, #585878);
  flex-shrink: 0;
}

.ratio-select, .res-select, .dur-select {
  padding: 4px 22px 4px 8px;
  background: var(--tv-surface-deep, #181820);
  border: 1px solid var(--tv-border, #353550);
  border-radius: 6px;
  color: var(--tv-text, #d0d4dc);
  font-size: 0.7rem;
  font-weight: 500;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' fill='none' stroke='%236b7280' viewBox='0 0 10 10'%3e%3cpath d='M2 3.5L5 6.5L8 3.5'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 7px center;
  transition: border-color 0.1s ease;
}
.ratio-select:hover, .res-select:hover, .dur-select:hover { border-color: var(--tv-border-hover, #585878); }
.ratio-select:focus, .res-select:focus, .dur-select:focus {
  outline: none;
  border-color: var(--tv-accent, #f07088);
}

.send-btn {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(240, 112, 136, 0.12);
  border: 2px solid var(--tv-accent, #f07088);
  border-radius: 8px;
  color: var(--tv-text, #d0d4dc);
  cursor: pointer;
  transition: border-color 0.1s ease, box-shadow 0.1s ease;
}
.send-btn:hover:not(:disabled):not(.loading) {
  box-shadow: 0 0 12px var(--tv-accent-glow, rgba(240, 112, 136, 0.25));
}
.send-btn.loading { opacity: 0.5; cursor: wait; }
.send-btn:disabled { opacity: 0.25; cursor: not-allowed; }

.mode-select {
  padding: 7px 26px 7px 12px;
  background: rgba(168, 104, 224, 0.15);
  border: 1.5px solid rgba(168, 104, 224, 0.3);
  border-radius: 10px;
  color: var(--tv-output-vid, #a868e0);
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' fill='none' stroke='%23a868e0' viewBox='0 0 10 10'%3e%3cpath d='M2 3.5L5 6.5L8 3.5'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
.mode-select:focus {
  outline: none;
  border-color: rgba(168, 104, 224, 0.5);
  box-shadow: 0 0 0 4px rgba(168, 104, 224, 0.1);
}
.mode-select option, .ratio-select option, .res-select option, .dur-select option {
  background: var(--tv-surface-deep, #181820);
  color: var(--tv-text, #d0d4dc);
  padding: 6px 10px;
}

.send-spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-top-color: var(--tv-text, #d0d4dc);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.handle-left, .handle-right {
  width: 14px !important; height: 14px !important;
  border: 2px solid var(--tv-accent, #f07088) !important;
  border-radius: 50%;
  background: var(--tv-accent, #f07088) !important;
  z-index: 10;
}
</style>
