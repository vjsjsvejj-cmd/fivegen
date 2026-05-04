import { ref } from 'vue'

export function useResize() {
  const leftPanelWidth = ref(720)
  const minLeftWidth = 400
  const maxLeftWidth = 900
  const isResizing = ref(false)

  const handleMouseMove = (e) => {
    if (isResizing.value) {
      const newWidth = e.clientX
      if (newWidth >= minLeftWidth && newWidth <= maxLeftWidth) {
        leftPanelWidth.value = newWidth
      }
    }
  }

  const handleMouseUp = () => {
    isResizing.value = false
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }

  const handleMouseDown = (e) => {
    isResizing.value = true
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  const cleanup = () => {
    if (isResizing.value) {
      isResizing.value = false
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }

  return {
    leftPanelWidth,
    minLeftWidth,
    maxLeftWidth,
    isResizing,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    cleanup,
  }
}
