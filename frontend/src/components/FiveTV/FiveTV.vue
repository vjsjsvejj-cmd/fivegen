<script setup>
import { ref, reactive, markRaw, onMounted, onUnmounted, provide, computed, watch, nextTick } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import MiniMapView from './MiniMapView.vue'

import PromptNode from './PromptNode.vue'
import ImageUploadNode from './ImageUploadNode.vue'
import VideoUploadNode from './VideoUploadNode.vue'
import OutputNode from './OutputNode.vue'

const GhostTargetNode = {
  name: 'GhostTarget',
  template: '<div style="width:0;height:0;pointer-events:none;position:absolute"></div>'
}

import { NODE_COLORS, THEME } from './fivetv-theme'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

const props = defineProps({
  onBack: {
    type: Function,
    default: () => {}
  }
})

const { addNodes, addEdges, project, fitView, getNode, updateNode, removeNodes, getNodes, getEdges, setNodes, setEdges, applyNodeChanges, applyEdgeChanges } = useVueFlow()

const nodeDataChangeCounter = ref(0)
provide('nodeDataChangeCounter', nodeDataChangeCounter)

const nodeTypes = reactive({
  prompt: markRaw(PromptNode),
  imageUpload: markRaw(ImageUploadNode),
  videoUpload: markRaw(VideoUploadNode),
  output: markRaw(OutputNode),
  ghostTarget: markRaw(GhostTargetNode)
})

const nodes = ref([])
const edges = ref([])

const activeOutputPanelId = ref(null)
provide('activeOutputPanelId', activeOutputPanelId)

const showPalette = ref(false)
const showContextMenu = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const showConnectMenu = ref(false)
const connectMenuPosition = ref({ x: 0, y: 0 })
const currentConnectSource = ref(null)
const connectSourceNodeType = ref(null)
const ghostEdgeVisible = ref(false)
const ghostEdgeSource = ref(null)
const ghostEdgeTargetPos = ref({ x: 0, y: 0 })
let lastMousePosition = { x: 0, y: 0 }
let savedConnectSourceId = null
let connectEndedAt = 0
let connectionMade = false

let nodeIdCounter = 0
const generateNodeId = () => `node-${Date.now()}-${++nodeIdCounter}`

const selectedNodes = ref(new Set())

const undoStack = ref([])
const redoStack = ref([])
const isUndoRedoAction = ref(false)
const maxUndoSteps = 50

const showSaveDialog = ref(false)
const saveProjectName = ref('')
const showLoadDialog = ref(false)
const savedProjects = ref([])
const showDeleteConfirm = ref(false)

const projectName = ref('未命名项目')

const saveSnapshot = () => {
  if (isUndoRedoAction.value) return
  const snapshot = {
    nodes: JSON.parse(JSON.stringify(nodes.value)),
    edges: JSON.parse(JSON.stringify(edges.value)),
    timestamp: Date.now()
  }
  undoStack.value.push(snapshot)
  if (undoStack.value.length > maxUndoSteps) {
    undoStack.value.shift()
  }
  redoStack.value = []
}

const undo = () => {
  if (undoStack.value.length === 0) return
  isUndoRedoAction.value = true
  const currentSnapshot = {
    nodes: JSON.parse(JSON.stringify(nodes.value)),
    edges: JSON.parse(JSON.stringify(edges.value)),
    timestamp: Date.now()
  }
  redoStack.value.push(currentSnapshot)
  const prevSnapshot = undoStack.value.pop()
  setNodes(prevSnapshot.nodes)
  setEdges(prevSnapshot.edges)
  nextTick(() => {
    isUndoRedoAction.value = false
  })
}

const redo = () => {
  if (redoStack.value.length === 0) return
  isUndoRedoAction.value = true
  const currentSnapshot = {
    nodes: JSON.parse(JSON.stringify(nodes.value)),
    edges: JSON.parse(JSON.stringify(edges.value)),
    timestamp: Date.now()
  }
  undoStack.value.push(currentSnapshot)
  const nextSnapshot = redoStack.value.pop()
  setNodes(nextSnapshot.nodes)
  setEdges(nextSnapshot.edges)
  nextTick(() => {
    isUndoRedoAction.value = false
  })
}

const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

const saveProject = () => {
  if (!saveProjectName.value.trim()) return
  const projectData = {
    name: saveProjectName.value.trim(),
    nodes: JSON.parse(JSON.stringify(nodes.value)),
    edges: JSON.parse(JSON.stringify(edges.value)),
    savedAt: new Date().toISOString(),
    version: '2.4.3'
  }
  const projects = getStoredProjects()
  const existingIndex = projects.findIndex(p => p.name === projectData.name)
  if (existingIndex >= 0) {
    projects[existingIndex] = projectData
  } else {
    projects.push(projectData)
  }
  localStorage.setItem('fivetv_projects', JSON.stringify(projects))
  projectName.value = projectData.name
  showSaveDialog.value = false
  saveProjectName.value = ''
}

const getStoredProjects = () => {
  try {
    return JSON.parse(localStorage.getItem('fivetv_projects') || '[]')
  } catch {
    return []
  }
}

const loadProjectsList = () => {
  savedProjects.value = getStoredProjects()
  showLoadDialog.value = true
}

const loadProject = (project) => {
  saveSnapshot()
  setNodes(project.nodes || [])
  setEdges(project.edges || [])
  projectName.value = project.name
  showLoadDialog.value = false
  nextTick(() => {
    fitView({ padding: 0.2 })
  })
}

const deleteProject = (project) => {
  const projects = getStoredProjects()
  const filtered = projects.filter(p => p.name !== project.name)
  localStorage.setItem('fivetv_projects', JSON.stringify(filtered))
  savedProjects.value = filtered
}

const deleteSelectedNodes = () => {
  const currentNodes = getNodes.value
  const selected = currentNodes.filter(n => n.selected)
  if (selected.length === 0) return
  saveSnapshot()
  const selectedIds = new Set(selected.map(n => n.id))
  const nodeIdsToRemove = selected.map(n => n.id)
  removeNodes(nodeIdsToRemove)
}

const handleKeyDown = (event) => {
  if (event.ctrlKey || event.metaKey) {
    if (event.key === 'z' && !event.shiftKey) {
      event.preventDefault()
      undo()
    } else if ((event.key === 'z' && event.shiftKey) || event.key === 'y') {
      event.preventDefault()
      redo()
    } else if (event.key === 's') {
      event.preventDefault()
      saveProjectName.value = projectName.value
      showSaveDialog.value = true
    } else if (event.key === 'Delete' || event.key === 'Backspace') {
      event.preventDefault()
      deleteSelectedNodes()
    }
  }
  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return
    deleteSelectedNodes()
  }
}

const createNodeData = (type) => {
  switch(type) {
    case 'prompt':
      return { prompt: '' }
    case 'imageUpload':
      return { imageUrl: '' }
    case 'videoUpload':
      return { videoUrl: '' }
    case 'output':
      return {
        result: null,
        outputMode: 'image',
        selectedModel: 'nano-banana-2',
        resolution: '1K',
        aspectRatio: 'auto',
        prompt: ''
      }
    default:
      return {}
  }
}

const addNodeFromMenu = (type) => {
  saveSnapshot()
  const { x, y } = project({
    x: contextMenuPosition.value.x,
    y: contextMenuPosition.value.y
  })

  const newNode = {
    id: generateNodeId(),
    type,
    position: { x: x - 100, y: y - 50 },
    data: createNodeData(type)
  }

  addNodes([newNode])
  showContextMenu.value = false
}

const addNodeFromPalette = (type) => {
  saveSnapshot()
  const newNode = {
    id: generateNodeId(),
    type,
    position: { x: 300 + Math.random() * 200, y: 200 + Math.random() * 200 },
    data: createNodeData(type)
  }

  addNodes([newNode])
  showPalette.value = false
}

const clearGhostEdge = () => {
  const ghostNode = getNodes.value.find(n => n.id === '__ghost_target__')
  if (ghostNode) {
    removeNodes(['__ghost_target__'])
  }
  const ghostEdge = getEdges.value.find(e => e.id.startsWith('ghost-'))
  if (ghostEdge) {
    setEdges(getEdges.value.filter(e => !e.id.startsWith('ghost-')))
  }
  ghostEdgeVisible.value = false
  ghostEdgeSource.value = null
}

const addNodeFromConnect = (outputMode) => {
  saveSnapshot()
  const { x, y } = project({
    x: connectMenuPosition.value.x,
    y: connectMenuPosition.value.y
  })

  const sourceId = currentConnectSource.value

  const newNodeId = generateNodeId()
  const newNode = {
    id: newNodeId,
    type: 'output',
    position: { x: x - 100, y: y - 50 },
    data: {
      result: null,
      outputMode: outputMode,
      selectedModel: outputMode === 'image' ? 'nano-banana-2' : 'seedance-2-0',
      resolution: outputMode === 'image' ? '1K' : '720p',
      aspectRatio: 'auto',
      prompt: ''
    }
  }

  addNodes([newNode])

  if (sourceId) {
    addEdges([{
      id: `e-${sourceId}-${newNodeId}`,
      source: sourceId,
      target: newNodeId
    }])
  }

  showConnectMenu.value = false
  currentConnectSource.value = null
  connectSourceNodeType.value = null
  clearGhostEdge()
}

const dismissConnectMenu = () => {
  showConnectMenu.value = false
  currentConnectSource.value = null
  connectSourceNodeType.value = null
  clearGhostEdge()
}

const onPaneContextMenu = (event) => {
  event.preventDefault()
  contextMenuPosition.value = { x: event.clientX, y: event.clientY }
  showContextMenu.value = true
}

const onPaneClick = () => {
  activeOutputPanelId.value = null
  showContextMenu.value = false
  if (Date.now() - connectEndedAt > 300) {
    showConnectMenu.value = false
  }
}

const onPaneMouseMove = (event) => {
  lastMousePosition = { x: event.clientX, y: event.clientY }
}

const onConnectStart = (event) => {
  savedConnectSourceId = event.nodeId || null
  connectEndedAt = 0
  showConnectMenu.value = false
  connectionMade = false

  const sourceNode = nodes.value.find(n => n.id === event.nodeId)
  if (sourceNode) {
    connectSourceNodeType.value = sourceNode.type === 'videoUpload' ? 'video' : 'image'
  }
}

const onConnectEnd = (event) => {
  connectEndedAt = Date.now()
  const sourceId = savedConnectSourceId
  const sourceType = connectSourceNodeType.value

  setTimeout(() => {
    if (!connectionMade && sourceId) {
      connectMenuPosition.value = { x: lastMousePosition.x, y: lastMousePosition.y }
      currentConnectSource.value = sourceId
      connectSourceNodeType.value = sourceType
      showConnectMenu.value = true
      ghostEdgeVisible.value = true
      ghostEdgeSource.value = sourceId

      const sourceNode = getNodes.value.find(n => n.id === sourceId)
      if (sourceNode) {
        const ghostTargetId = '__ghost_target__'
        const ghostPos = project({ x: lastMousePosition.x, y: lastMousePosition.y + 30 })
        addNodes([{
          id: ghostTargetId,
          type: 'ghostTarget',
          position: ghostPos,
          data: {},
          draggable: false,
          selectable: false,
          connectable: true
        }])
        addEdges([{
          id: `ghost-${sourceId}`,
          source: sourceId,
          target: ghostTargetId,
          animated: true,
          style: { stroke: '#8890a8', strokeWidth: 2, strokeDasharray: '6 4' }
        }])
      }
    }
    savedConnectSourceId = null
    connectionMade = false
  }, 20)
}

const onConnect = (params) => {
  saveSnapshot()
  connectionMade = true
  showConnectMenu.value = false
  savedConnectSourceId = null
  connectEndedAt = 0
}

const onNodeDataChange = (event) => {
  const { id, data } = event
  updateNode(id, { data })
}

const isValidConnectionFn = () => true

const formatSavedTime = (isoString) => {
  if (!isoString) return ''
  const d = new Date(isoString)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

let handleMouseMove

onMounted(() => {
  handleMouseMove = (event) => {
    lastMousePosition = { x: event.clientX, y: event.clientY }
  }
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  if (handleMouseMove) {
    document.removeEventListener('mousemove', handleMouseMove)
  }
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <div class="five-tv-container">
    <div class="top-bar">
      <div class="top-bar-left">
        <button @click="onBack" class="icon-btn back-btn" title="返回主界面">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <div class="divider-v"></div>
        <button @click="undo" class="icon-btn" :class="{ disabled: !canUndo }" title="撤销 (Ctrl+Z)" :disabled="!canUndo">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
          </svg>
        </button>
        <button @click="redo" class="icon-btn" :class="{ disabled: !canRedo }" title="重做 (Ctrl+Shift+Z)" :disabled="!canRedo">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.13-9.36L23 10"/>
          </svg>
        </button>
        <div class="divider-v"></div>
        <button @click="deleteSelectedNodes" class="icon-btn" title="删除选中 (Delete)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </div>

      <div class="top-bar-center">
        <div class="brand">
          <span class="brand-icon">📺</span>
          <span class="brand-text">Five TV</span>
        </div>
      </div>

      <div class="top-bar-right">
        <button @click="saveProjectName = projectName; showSaveDialog = true" class="icon-btn" title="保存项目 (Ctrl+S)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
        </button>
        <button @click="loadProjectsList" class="icon-btn" title="加载历史项目">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </button>
        <div class="divider-v"></div>
        <button @click="fitView({ padding: 0.2 })" class="icon-btn" title="适应视图">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="main-content">
      <div class="canvas-wrapper">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          class="flow-canvas"
          :min-zoom="0.01"
          :max-zoom="100"
          :nodes-connectable="true"
          connection-mode="loose"
          :auto-connect="true"
          :is-valid-connection="isValidConnectionFn"
          @pane-click="onPaneClick"
          @pane-context-menu="onPaneContextMenu"
          @pane-mousemove="onPaneMouseMove"
          @connect="onConnect"
          @connect-start="onConnectStart"
          @connect-end="onConnectEnd"
          @node-data-change="onNodeDataChange"
        >
          <Background gap="20" pattern-color="#3a3a4a" />
          <MiniMapView />

          <template #connection-line="{ sourceX, sourceY, targetX, targetY }">
            <g>
              <path
                :d="`M${sourceX},${sourceY} C${sourceX + 50},${sourceY} ${targetX - 50},${targetY} ${targetX},${targetY}`"
                fill="none"
                stroke="var(--tv-text-sec, #8890a8)"
                stroke-width="2"
                stroke-dasharray="6 4"
              />
            </g>
          </template>
        </VueFlow>

        <div class="canvas-controls">
          <Controls class="horizontal-controls" />
        </div>
      </div>
    </div>

    <div class="palette-wrapper" @mouseenter="showPalette = true" @mouseleave="showPalette = false">
      <div class="floating-palette-toggle">
        <span class="toggle-icon">+</span>
      </div>

      <div v-if="showPalette" class="floating-palette" @click.stop>
        <div class="palette-item palette-item-prompt" @click="addNodeFromPalette('prompt')">
          <span class="palette-icon">💬</span>
          <span class="palette-label">提示词</span>
        </div>
        <div class="palette-item palette-item-image" @click="addNodeFromPalette('imageUpload')">
          <span class="palette-icon">🖼️</span>
          <span class="palette-label">参考图</span>
        </div>
        <div class="palette-item palette-item-video" @click="addNodeFromPalette('videoUpload')">
          <span class="palette-icon">🎬</span>
          <span class="palette-label">视频源</span>
        </div>
      </div>
    </div>

    <div
      v-if="showContextMenu"
      class="context-menu"
      :style="{ left: contextMenuPosition.x + 'px', top: contextMenuPosition.y + 'px' }"
      @click.stop
    >
      <div class="menu-section-label">源数据节点</div>
      <div class="menu-item" @click="addNodeFromMenu('prompt')">
        <span class="menu-dot" :style="{ background: NODE_COLORS.prompt }"></span>
        <span>提示词</span>
      </div>
      <div class="menu-item" @click="addNodeFromMenu('imageUpload')">
        <span class="menu-dot" :style="{ background: NODE_COLORS.imageUpload }"></span>
        <span>参考图</span>
      </div>
      <div class="menu-item" @click="addNodeFromMenu('videoUpload')">
        <span class="menu-dot" :style="{ background: NODE_COLORS.videoUpload }"></span>
        <span>视频源</span>
      </div>
    </div>

    <div
      v-if="showConnectMenu"
      class="connect-menu"
      :style="{ left: connectMenuPosition.x + 'px', top: connectMenuPosition.y + 'px' }"
      @click.stop
    >
      <div class="menu-header">
        <span>选择输出类型</span>
        <button class="close-btn" @click="dismissConnectMenu">×</button>
      </div>
      <div class="menu-item" @click="addNodeFromConnect('image')">
        <span class="menu-dot" :style="{ background: NODE_COLORS.outputImage }"></span>
        <div class="menu-item-content">
          <span class="menu-item-title">图片</span>
          <span class="menu-item-desc">文生图 / 图生图</span>
        </div>
      </div>
      <div class="menu-item" @click="addNodeFromConnect('video')">
        <span class="menu-dot" :style="{ background: NODE_COLORS.outputVideo }"></span>
        <div class="menu-item-content">
          <span class="menu-item-title">视频</span>
          <span class="menu-item-desc">文生视频 / 首尾帧 / 多模态</span>
        </div>
      </div>
    </div>

    <!-- 保存对话框 -->
    <div v-if="showSaveDialog" class="dialog-overlay" @click.self="showSaveDialog = false">
      <div class="dialog">
        <div class="dialog-header">
          <h3>💾 保存项目</h3>
          <button class="close-btn" @click="showSaveDialog = false">×</button>
        </div>
        <div class="dialog-body">
          <label class="dialog-label">项目名称</label>
          <input
            v-model="saveProjectName"
            type="text"
            placeholder="输入项目名称..."
            class="dialog-input"
            @keyup.enter="saveProject"
            autofocus
          />
        </div>
        <div class="dialog-footer">
          <button @click="showSaveDialog = false" class="dialog-btn cancel">取消</button>
          <button @click="saveProject" class="dialog-btn confirm" :disabled="!saveProjectName.trim()">保存</button>
        </div>
      </div>
    </div>

    <!-- 加载历史项目对话框 -->
    <div v-if="showLoadDialog" class="dialog-overlay" @click.self="showLoadDialog = false">
      <div class="dialog dialog-wide">
        <div class="dialog-header">
          <h3>📂 历史项目</h3>
          <button class="close-btn" @click="showLoadDialog = false">×</button>
        </div>
        <div class="dialog-body">
          <div v-if="savedProjects.length === 0" class="empty-state">
            <span class="empty-icon">📭</span>
            <span class="empty-text">暂无保存的项目</span>
          </div>
          <div v-else class="project-list">
            <div v-for="project in savedProjects" :key="project.name" class="project-item">
              <div class="project-info">
                <span class="project-name">{{ project.name }}</span>
                <span class="project-meta">
                  {{ (project.nodes || []).length }} 个节点 · {{ formatSavedTime(project.savedAt) }}
                </span>
              </div>
              <div class="project-actions">
                <button @click="loadProject(project)" class="project-btn load">加载</button>
                <button @click="deleteProject(project)" class="project-btn delete">删除</button>
              </div>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button @click="showLoadDialog = false" class="dialog-btn cancel">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
.five-tv-container {
  --tv-prompt: #e89840;
  --tv-prompt-glow: rgba(232, 152, 64, 0.25);
  --tv-image-src: #4a9eff;
  --tv-image-src-glow: rgba(74, 158, 255, 0.25);
  --tv-video-src: #38c878;
  --tv-video-src-glow: rgba(56, 200, 120, 0.25);
  --tv-output-img: #f07088;
  --tv-output-img-glow: rgba(240, 112, 136, 0.25);
  --tv-output-vid: #a868e0;
  --tv-output-vid-glow: rgba(168, 104, 224, 0.25);

  --tv-bg: #14141c;
  --tv-surface: #1e1e30;
  --tv-surface-alt: #222238;
  --tv-surface-deep: #181820;
  --tv-surface-hover: #282840;
  --tv-border: #353550;
  --tv-border-hover: #585878;
  --tv-text: #d0d4dc;
  --tv-text-sec: #8890a8;
  --tv-text-muted: #585878;
  --tv-edge: #586080;
  --tv-edge-hover: #7888b0;
  --tv-success: #58b880;
  --tv-error: #c06060;
  --tv-cost: #e0c058;
}

.vue-flow__node {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  background: none !important;
}

.vue-flow__node.selected,
.vue-flow__node.vue-flow__node-selected {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  background: none !important;
}

.vue-flow__node:hover,
.vue-flow__node:focus,
.vue-flow__node:focus-visible {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  transition: none !important;
  background: none !important;
}

.vue-flow__node::before,
.vue-flow__node::after {
  display: none !important;
}

.vue-flow__node * {
  box-shadow: none !important;
}

.vue-flow__edge-path {
  stroke: var(--tv-edge) !important;
  stroke-width: 2px !important;
  fill: none;
  transition: stroke 0.15s ease;
}

.vue-flow__edge-path:hover {
  stroke: var(--tv-edge-hover) !important;
  stroke-width: 2.5px !important;
}

.vue-flow__edge-text {
  fill: var(--tv-text-sec);
  font-size: 11px;
}

.vue-flow__edge {
  pointer-events: all;
}

.vue-flow__connection-line path {
  stroke: var(--tv-text-sec) !important;
  stroke-width: 2px !important;
  stroke-dasharray: 6 4;
}
</style>

<style scoped>
.five-tv-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--tv-bg);
  color: var(--tv-text);
  overflow: hidden;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 48px;
  background: var(--tv-surface-alt);
  border-bottom: 1px solid var(--tv-border);
  z-index: 100;
}

.top-bar-left,
.top-bar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.top-bar-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 16px;
  background: linear-gradient(135deg, rgba(168, 104, 224, 0.15), rgba(74, 158, 255, 0.15));
  border: 1px solid rgba(168, 104, 224, 0.3);
  border-radius: 8px;
}

.brand-icon {
  font-size: 1.2rem;
}

.brand-text {
  font-size: 1rem;
  font-weight: 700;
  background: linear-gradient(135deg, #a868e0, #4a9eff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.5px;
}

.icon-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--tv-text-sec);
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.icon-btn:hover:not(.disabled) {
  background: var(--tv-surface-hover);
  color: var(--tv-text);
  border-color: var(--tv-border);
}

.icon-btn.disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.back-btn:hover {
  color: #4a9eff !important;
  border-color: rgba(74, 158, 255, 0.3) !important;
  background: rgba(74, 158, 255, 0.08) !important;
}

.divider-v {
  width: 1px;
  height: 20px;
  background: var(--tv-border);
  margin: 0 4px;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.canvas-wrapper {
  flex: 1;
  position: relative;
}

.flow-canvas {
  width: 100%;
  height: 100%;
  background: var(--tv-bg);
}

.canvas-controls {
  position: absolute;
  bottom: 16px;
  right: 16px;
  z-index: 10;
}

.horizontal-controls {
  display: flex;
  flex-direction: row;
  gap: 0;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.horizontal-controls :deep(.vue-flow__controls) {
  display: flex;
  flex-direction: row;
  background: var(--tv-surface-alt) !important;
  border: 2px solid var(--tv-border) !important;
}

.horizontal-controls :deep(button) {
  border-left: 1px solid var(--tv-border);
  border-right: none;
  border-top: none;
  border-bottom: none;
  border-radius: 0;
  background: transparent !important;
  color: var(--tv-text-sec) !important;
  padding: 10px 12px !important;
  transition: color 0.1s ease, background 0.1s ease;
}

.horizontal-controls :deep(button:hover) {
  background: var(--tv-surface-hover) !important;
  color: var(--tv-text) !important;
}

.palette-wrapper {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 999;
  display: flex;
  align-items: center;
}

.floating-palette-toggle {
  width: 38px;
  height: 38px;
  background: var(--tv-surface-alt);
  border-radius: 8px;
  border: 2px solid var(--tv-prompt);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  margin-left: 16px;
  margin-right: 0;
  transition: border-color 0.12s ease, box-shadow 0.12s ease;
}

.floating-palette-toggle:hover {
  border-color: var(--tv-prompt);
  box-shadow: 0 0 12px var(--tv-prompt-glow);
}

.toggle-icon {
  font-size: 20px;
  font-weight: 300;
  color: var(--tv-prompt);
  transition: color 0.12s ease;
}

.floating-palette {
  padding: 2px;
  animation: fadeIn 0.1s ease;
  display: flex;
  flex-direction: column;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateX(-4px); }
  to { opacity: 1; transform: translateX(0); }
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  background: var(--tv-surface);
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.1s ease, background 0.1s ease;
  margin-bottom: 2px;
  white-space: nowrap;
}

.palette-item:last-child {
  margin-bottom: 0;
}

.palette-item-prompt { border-left: 3px solid var(--tv-prompt); }
.palette-item-prompt:hover { border-color: var(--tv-prompt); background: rgba(232, 152, 64, 0.08); }
.palette-item-image { border-left: 3px solid var(--tv-image-src); }
.palette-item-image:hover { border-color: var(--tv-image-src); background: rgba(74, 158, 255, 0.08); }
.palette-item-video { border-left: 3px solid var(--tv-video-src); }
.palette-item-video:hover { border-color: var(--tv-video-src); background: rgba(56, 200, 120, 0.08); }

.palette-icon {
  font-size: 1rem;
}

.palette-label {
  font-size: 0.82rem;
  color: var(--tv-text-sec);
}

.context-menu,
.connect-menu {
  position: fixed;
  padding: 3px;
  z-index: 99999;
  animation: slideIn 0.1s ease;
  background: var(--tv-surface);
  border: 1px solid var(--tv-border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(12px);
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-3px); }
  to { opacity: 1; transform: translateY(0); }
}

.menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  margin-bottom: 2px;
  border-bottom: 1px solid var(--tv-border);
  font-size: 0.75rem;
  color: var(--tv-text-sec);
  font-weight: 500;
  background: var(--tv-surface-alt);
  border-radius: 6px 6px 0 0;
}

.menu-section-label {
  padding: 6px 12px 4px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--tv-text);
  letter-spacing: 0.3px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  cursor: pointer;
  transition: background 0.08s ease;
  font-size: 0.82rem;
  color: var(--tv-text-sec);
  background: var(--tv-surface);
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  margin-bottom: 2px;
}

.menu-item:last-child {
  margin-bottom: 0;
}

.menu-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.menu-item-content {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.menu-item-title {
  font-size: 0.82rem;
  font-weight: 400;
}

.menu-item-desc {
  font-size: 0.68rem;
  color: var(--tv-text-muted);
}

.menu-item:hover {
  border-color: var(--tv-border-hover);
  background: var(--tv-surface-hover);
  color: var(--tv-text);
}

.menu-icon {
  font-size: 1rem;
}

.close-btn {
  background: none;
  border: none;
  color: var(--tv-text-muted);
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.12s ease;
}

.close-btn:hover {
  color: var(--tv-text-sec);
}

.palette-wrapper .palette-divider {
  display: none;
}

/* Dialog styles */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog {
  background: var(--tv-surface);
  border: 1px solid var(--tv-border);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  width: 400px;
  max-width: 90vw;
  animation: dialogIn 0.2s ease;
}

.dialog-wide {
  width: 560px;
}

@keyframes dialogIn {
  from { opacity: 0; transform: scale(0.95) translateY(-10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--tv-border);
}

.dialog-header h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--tv-text);
}

.dialog-body {
  padding: 20px;
}

.dialog-label {
  display: block;
  margin-bottom: 8px;
  font-size: 0.85rem;
  color: var(--tv-text-sec);
}

.dialog-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--tv-surface-deep);
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  color: var(--tv-text);
  font-size: 0.9rem;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s ease;
}

.dialog-input:focus {
  border-color: #4a9eff;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--tv-border);
}

.dialog-btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  border: 1px solid var(--tv-border);
  transition: all 0.15s ease;
}

.dialog-btn.cancel {
  background: var(--tv-surface-alt);
  color: var(--tv-text-sec);
}

.dialog-btn.cancel:hover {
  background: var(--tv-surface-hover);
  color: var(--tv-text);
}

.dialog-btn.confirm {
  background: linear-gradient(135deg, #4a9eff, #a868e0);
  color: #fff;
  border: none;
  font-weight: 600;
}

.dialog-btn.confirm:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.dialog-btn.confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
}

.empty-icon {
  font-size: 2rem;
}

.empty-text {
  color: var(--tv-text-muted);
  font-size: 0.9rem;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 360px;
  overflow-y: auto;
}

.project-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: var(--tv-surface-deep);
  border: 1px solid var(--tv-border);
  border-radius: 8px;
  transition: border-color 0.15s ease;
}

.project-item:hover {
  border-color: var(--tv-border-hover);
}

.project-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.project-name {
  font-size: 0.9rem;
  color: var(--tv-text);
  font-weight: 500;
}

.project-meta {
  font-size: 0.75rem;
  color: var(--tv-text-muted);
}

.project-actions {
  display: flex;
  gap: 6px;
}

.project-btn {
  padding: 5px 14px;
  border-radius: 5px;
  font-size: 0.78rem;
  cursor: pointer;
  border: 1px solid var(--tv-border);
  transition: all 0.15s ease;
}

.project-btn.load {
  background: rgba(74, 158, 255, 0.1);
  color: #4a9eff;
  border-color: rgba(74, 158, 255, 0.3);
}

.project-btn.load:hover {
  background: rgba(74, 158, 255, 0.2);
}

.project-btn.delete {
  background: rgba(192, 96, 96, 0.1);
  color: var(--tv-error);
  border-color: rgba(192, 96, 96, 0.3);
}

.project-btn.delete:hover {
  background: rgba(192, 96, 96, 0.2);
}
</style>
