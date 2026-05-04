export const NODE_COLORS = {
  prompt: '#e89840',
  imageUpload: '#4a9eff',
  videoUpload: '#38c878',
  textToImage: '#f07088',
  imageToImage: '#00c8c8',
  textToVideo: '#a868e0',
  frameToFrame: '#d4a030',
  multimodal: '#e050a0',
}

export const OUTPUT_MODE_COLORS = {
  'text-image': NODE_COLORS.textToImage,
  'image-image': NODE_COLORS.imageToImage,
  'text-video': NODE_COLORS.textToVideo,
  'frame-frame': NODE_COLORS.frameToFrame,
  'multimodal': NODE_COLORS.multimodal,
}

export const getOutputModeKey = (node) => {
  if (node.type !== 'output') return null
  const mode = node.data?.outputMode
  const hasImageInput = node.data?.hasImageInput
  const hasVideoInput = node.data?.hasVideoInput

  if (mode === 'image') {
    if (hasVideoInput) return 'multimodal'
    if (hasImageInput) return 'image-image'
    return 'text-image'
  }
  if (mode === 'video') {
    if (hasImageInput && hasVideoInput) return 'multimodal'
    if (hasImageInput) return 'frame-frame'
    return 'text-video'
  }
  return 'text-image'
}

export const getNodeColor = (node, edges = []) => {
  if (node.type === 'prompt') return NODE_COLORS.prompt
  if (node.type === 'imageUpload') return NODE_COLORS.imageUpload
  if (node.type === 'videoUpload') return NODE_COLORS.videoUpload

  if (node.type === 'output') {
    const isUsedAsInput = edges.some(e => e.source === node.id)
    if (isUsedAsInput) {
      return node.data?.outputMode === 'video' ? NODE_COLORS.videoUpload : NODE_COLORS.imageUpload
    }
    const modeKey = getOutputModeKey(node)
    return OUTPUT_MODE_COLORS[modeKey] || NODE_COLORS.textToImage
  }

  return '#8890a8'
}

export const getOutputNodeAccent = (node, edges = []) => {
  const isUsedAsInput = edges.some(e => e.source === node.id)
  if (isUsedAsInput) {
    return node.data?.outputMode === 'video' ? NODE_COLORS.videoUpload : NODE_COLORS.imageUpload
  }
  const modeKey = getOutputModeKey(node)
  return OUTPUT_MODE_COLORS[modeKey] || NODE_COLORS.textToImage
}

export const getOutputNodeGlow = (node, edges = []) => {
  const color = getOutputNodeAccent(node, edges)
  const r = parseInt(color.slice(1, 3), 16)
  const g = parseInt(color.slice(3, 5), 16)
  const b = parseInt(color.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, 0.25)`
}

export const TASK_TYPE_LABELS = {
  'text-image': '文生图',
  'image-image': '图生图',
  'text-video': '文生视频',
  'frame-frame': '首尾帧',
  'multimodal': '多模态',
}

export const TASK_TYPE_ICONS = {
  'text-image': '🖼️',
  'image-image': '🎨',
  'text-video': '🎬',
  'frame-frame': '🎞️',
  'multimodal': '🔮',
}

export const THEME = {
  bg: '#14141c',
  surface: '#1e1e30',
  surfaceAlt: '#222238',
  surfaceDeep: '#181820',
  surfaceHover: '#282840',
  border: '#353550',
  borderHover: '#585878',
  text: '#d0d4dc',
  textSecondary: '#8890a8',
  textMuted: '#585878',
  edge: '#586080',
  edgeHover: '#7888b0',
  success: '#58b880',
  error: '#c06060',
  cost: '#e0c058',
}
