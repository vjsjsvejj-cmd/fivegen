<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { getNodeColor } from './fivetv-theme'

const { getNodes, getEdges, viewport, dimensions, setViewport, zoomIn, zoomOut, fitView } = useVueFlow()

const minimapRef = ref(null)
const MINI_W = 200
const MINI_H = 140

const isDragging = ref(false)
const dragStart = ref({ mx: 0, my: 0, vx: 0, vy: 0 })

const NODE_SIZES = {
  prompt: { w: 260, h: 120 },
  imageUpload: { w: 280, h: 180 },
  videoUpload: { w: 280, h: 180 },
  output: { w: 340, h: 200 },
}

const bounds = computed(() => {
  const ns = getNodes.value
  if (ns.length === 0) return { x1: -100, y1: -50, x2: 500, y2: 300 }

  let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity
  for (const n of ns) {
    const size = NODE_SIZES[n.type] || { w: 300, h: 200 }
    x1 = Math.min(x1, n.position.x)
    y1 = Math.min(y1, n.position.y)
    x2 = Math.max(x2, n.position.x + size.w)
    y2 = Math.max(y2, n.position.y + size.h)
  }

  const pad = 40
  return { x1: x1 - pad, y1: y1 - pad, x2: x2 + pad, y2: y2 + pad }
})

const contentW = computed(() => bounds.value.x2 - bounds.value.x1)
const contentH = computed(() => bounds.value.y2 - bounds.value.y1)

const miniScale = computed(() => {
  const cw = contentW.value
  const ch = contentH.value
  if (cw <= 0 || ch <= 0) return 1
  return Math.min(MINI_W / cw, MINI_H / ch)
})

const miniNodes = computed(() => {
  const s = miniScale.value
  const bx = bounds.value.x1
  const by = bounds.value.y1
  const cw = contentW.value
  const ch = contentH.value
  const renderedW = cw * s
  const renderedH = ch * s
  const ox = (MINI_W - renderedW) / 2
  const oy = (MINI_H - renderedH) / 2

  return getNodes.value.map(n => {
    const size = NODE_SIZES[n.type] || { w: 300, h: 200 }
    const nx = (n.position.x - bx) * s + ox
    const ny = (n.position.y - by) * s + oy
    const nw = Math.max(size.w * s, 3)
    const nh = Math.max(size.h * s, 2)
    if (isNaN(nx) || isNaN(ny) || isNaN(nw) || isNaN(nh)) return null
    return {
      id: n.id,
      x: nx,
      y: ny,
      w: nw,
      h: nh,
      fill: getNodeColor(n, getEdges.value)
    }
  }).filter(Boolean)
})

const vpRect = computed(() => {
  const v = viewport.value
  const d = dimensions.value
  if (!d?.width || !d?.height) return null

  const s = miniScale.value
  const bx = bounds.value.x1
  const by = bounds.value.y1
  const cw = contentW.value
  const ch = contentH.value
  const renderedW = cw * s
  const renderedH = ch * s
  const ox = (MINI_W - renderedW) / 2
  const oy = (MINI_H - renderedH) / 2

  const viewLeft = -v.x / v.zoom
  const viewTop = -v.y / v.zoom
  const viewRight = (d.width - v.x) / v.zoom
  const viewBottom = (d.height - v.y) / v.zoom

  const vx = (viewLeft - bx) * s + ox
  const vy = (viewTop - by) * s + oy
  const vw = (viewRight - viewLeft) * s
  const vh = (viewBottom - viewTop) * s
  if (isNaN(vx) || isNaN(vy) || isNaN(vw) || isNaN(vh)) return null

  return {
    x: vx,
    y: vy,
    w: vw,
    h: vh
  }
})

const zoomPct = computed(() => Math.round(viewport.value.zoom * 100))

const toFlow = (mx, my) => {
  const r = minimapRef.value?.getBoundingClientRect()
  if (!r) return { x: 0, y: 0 }

  const s = miniScale.value
  const bx = bounds.value.x1
  const by = bounds.value.y1
  const cw = contentW.value
  const ch = contentH.value
  const renderedW = cw * s
  const renderedH = ch * s
  const ox = (MINI_W - renderedW) / 2
  const oy = (MINI_H - renderedH) / 2

  const relX = mx - r.left - ox
  const relY = my - r.top - oy
  return { x: relX / s + bx, y: relY / s + by }
}

const onClick = (e) => {
  if (isDragging.value) return
  const fp = toFlow(e.clientX, e.clientY)
  const v = viewport.value
  const d = dimensions.value
  setViewport({ x: d.width / 2 - fp.x * v.zoom, y: d.height / 2 - fp.y * v.zoom, zoom: v.zoom })
}

const onWheel = (e) => {
  e.preventDefault()
  e.stopPropagation()
  e.deltaY < 0 ? zoomIn({ duration: 200 }) : zoomOut({ duration: 200 })
}

const onVpDown = (e) => {
  e.stopPropagation()
  e.preventDefault()
  isDragging.value = true
  dragStart.value = { mx: e.clientX, my: e.clientY, vx: viewport.value.x, vy: viewport.value.y }
}

const onGlobalMove = (e) => {
  if (!isDragging.value) return
  const dx = (e.clientX - dragStart.value.mx) / miniScale.value
  const dy = (e.clientY - dragStart.value.my) / miniScale.value
  setViewport({
    x: dragStart.value.vx - dx * viewport.value.zoom,
    y: dragStart.value.vy - dy * viewport.value.zoom,
    zoom: viewport.value.zoom
  })
}

const onGlobalUp = () => { isDragging.value = false }

const onDblClick = () => fitView({ duration: 300, padding: 0.2 })

onMounted(() => {
  document.addEventListener('mousemove', onGlobalMove)
  document.addEventListener('mouseup', onGlobalUp)
})
onUnmounted(() => {
  document.removeEventListener('mousemove', onGlobalMove)
  document.removeEventListener('mouseup', onGlobalUp)
})
</script>

<template>
  <div ref="minimapRef" class="mini-map" @click="onClick" @wheel.prevent.stop="onWheel" @dblclick="onDblClick">
    <svg :width="MINI_W" :height="MINI_H">
      <rect v-for="n in miniNodes" :key="n.id"
        :x="n.x" :y="n.y" :width="n.w" :height="n.h"
        :fill="n.fill" rx="1.5" opacity="0.85"
      />
      <rect v-if="vpRect"
        :x="vpRect.x" :y="vpRect.y" :width="vpRect.w" :height="vpRect.h"
        fill="none" stroke="#8890a8" stroke-width="1" rx="1"
        class="vp-border" @mousedown="onVpDown"
      />
    </svg>
    <div class="zoom-tag">{{ zoomPct }}%</div>
  </div>
</template>

<style scoped>
.mini-map {
  position: absolute;
  bottom: 12px;
  left: 12px;
  border-radius: 6px;
  border: 1px solid var(--tv-border, #353550);
  background: rgba(20, 20, 28, 0.88);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  z-index: 100;
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: border-color 0.15s ease;
}
.mini-map:hover { border-color: var(--tv-border-hover, #585878); }
.vp-border { cursor: grab; }
.vp-border:active { cursor: grabbing; }
.zoom-tag {
  position: absolute; top: 3px; right: 5px;
  font-size: 9px; color: var(--tv-text-muted, #585878);
  pointer-events: none; font-family: monospace;
}
</style>
