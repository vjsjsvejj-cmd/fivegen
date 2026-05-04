<template>
  <Teleport to="body">
    <Transition name="confirm">
      <div v-if="visible" class="confirm-overlay" @click.self="cancel">
        <div class="confirm-dialog" role="alertdialog" aria-modal="true">
          <div class="confirm-message">{{ message }}</div>
          <div class="confirm-actions">
            <button class="confirm-btn cancel-btn" @click="cancel">取消</button>
            <button class="confirm-btn ok-btn" @click="ok">确定</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const visible = ref(false)
const message = ref('')
let resolvePromise = null

const show = (msg) => {
  return new Promise((resolve) => {
    message.value = msg
    visible.value = true
    resolvePromise = resolve
  })
}

const ok = () => {
  visible.value = false
  if (resolvePromise) {
    resolvePromise(true)
    resolvePromise = null
  }
}

const cancel = () => {
  visible.value = false
  if (resolvePromise) {
    resolvePromise(false)
    resolvePromise = null
  }
}

defineExpose({ show })
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100000;
  backdrop-filter: blur(4px);
}

.confirm-dialog {
  background: #1e1e3a;
  border: 1px solid #333;
  border-radius: 12px;
  padding: 24px;
  min-width: 320px;
  max-width: 480px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.confirm-message {
  color: #e0e0e0;
  font-size: 15px;
  line-height: 1.6;
  margin-bottom: 20px;
  white-space: pre-line;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.confirm-btn {
  padding: 8px 20px;
  border-radius: 6px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background: #333;
  color: #aaa;
}
.cancel-btn:hover {
  background: #444;
  color: #ddd;
}

.ok-btn {
  background: #4a9eff;
  color: #fff;
}
.ok-btn:hover {
  background: #3a8eef;
}

.confirm-enter-active {
  transition: all 0.2s ease-out;
}
.confirm-leave-active {
  transition: all 0.15s ease-in;
}
.confirm-enter-from {
  opacity: 0;
}
.confirm-enter-from .confirm-dialog {
  transform: scale(0.9);
}
.confirm-leave-to {
  opacity: 0;
}
</style>
