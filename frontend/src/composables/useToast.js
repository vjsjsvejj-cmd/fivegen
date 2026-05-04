import { ref } from 'vue'

const toasts = ref([])
let toastId = 0

const showToast = (message, type = 'info', duration = 3000) => {
  const id = ++toastId
  toasts.value.push({ id, message, type, duration })
  if (duration > 0) {
    setTimeout(() => {
      removeToast(id)
    }, duration)
  }
  return id
}

const removeToast = (id) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index !== -1) {
    toasts.value.splice(index, 1)
  }
}

const success = (message, duration) => showToast(message, 'success', duration)
const error = (message, duration) => showToast(message, 'error', duration ?? 5000)
const warning = (message, duration) => showToast(message, 'warning', duration ?? 4000)
const info = (message, duration) => showToast(message, 'info', duration)

export function useToast() {
  return {
    toasts,
    showToast,
    removeToast,
    success,
    error,
    warning,
    info,
  }
}
