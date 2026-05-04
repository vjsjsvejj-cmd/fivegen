<script setup>
import { ref, watch, inject } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:data'])

const { updateNode } = useVueFlow()
const nodeDataChangeCounter = inject('nodeDataChangeCounter', ref(0))

const prompt = ref(props.data.prompt || '')

watch(() => prompt.value, (newVal) => {
  updateNode(props.id, {
    data: {
      ...props.data,
      prompt: newVal
    }
  })
  if (typeof nodeDataChangeCounter.value === 'number') {
    nodeDataChangeCounter.value++
  }
})

watch(() => props.data, (newData) => {
  if (newData && newData.prompt !== undefined) {
    prompt.value = newData.prompt
  }
}, { deep: true })
</script>

<template>
  <div class="prompt-node">
    <Handle type="source" :position="Position.Right" id="output" class="handle-right" :connectable="true" />

    <div class="node-header">
      <span class="icon">💬</span>
      <span class="title">提示词</span>
    </div>

    <div class="prompt-content">
      <textarea
        v-model="prompt"
        placeholder="输入提示词..."
        rows="3"
        class="prompt-input"
      ></textarea>
    </div>
  </div>
</template>

<style scoped>
.prompt-node {
  min-width: 240px;
  background: var(--tv-surface, #1e1e30);
  border: 2px solid var(--tv-prompt, #e89840);
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.12s ease, box-shadow 0.12s ease;
}

.prompt-node:hover {
  border-color: var(--tv-prompt, #e89840);
  box-shadow: 0 0 16px var(--tv-prompt-glow, rgba(232, 152, 64, 0.25));
}

.node-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--tv-surface-alt, #222238);
  border-bottom: 1px solid var(--tv-border, #353550);
}

.node-header .icon { 
  font-size: 0.85rem; 
}
.node-header .title { 
  color: var(--tv-prompt, #e89840); 
  font-weight: 600; 
  font-size: 0.78rem;
}

.prompt-content { padding: 10px 12px 12px; }

.prompt-input {
  width: 100%;
  padding: 8px 10px;
  background: var(--tv-surface-deep, #181820);
  border: 1px solid var(--tv-border, #353550);
  border-radius: 6px;
  color: var(--tv-text, #d0d4dc);
  font-size: 0.82rem;
  resize: vertical;
  box-sizing: border-box;
  font-family: inherit;
  line-height: 1.5;
  transition: border-color 0.12s ease;
}

.prompt-input:focus {
  outline: none;
  border-color: var(--tv-prompt, #e89840);
  background: var(--tv-bg, #14141c);
}

.prompt-input::placeholder { color: var(--tv-text-muted, #585878); }

.handle-right {
  width: 14px !important;
  height: 14px !important;
  border: 2px solid var(--tv-prompt, #e89840) !important;
  border-radius: 50%;
  background: var(--tv-prompt, #e89840) !important;
  z-index: 10;
}
</style>
