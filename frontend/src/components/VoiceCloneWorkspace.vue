<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { API_BASE_URL } from '../utils/config.js'

const toast = inject('toast', { warning: (msg) => console.warn(msg), error: (msg) => console.error(msg) })

const props = defineProps({
  roomId: { type: String, default: '' },
  userId: { type: String, default: '' },
  isConnected: { type: Boolean, default: false }
})

const emit = defineEmits(['generate'])

const activeSubTab = ref('voice-clone')

const voiceCloneText = ref('')
const voiceCloneRefText = ref('')
const voiceCloneRefAudio = ref(null)
const voiceCloneRefAudioName = ref('')
const voiceCloneRefFileId = ref('')
const voiceCloneResult = ref(null)
const voiceCloneLoading = ref(false)
const voiceCloneProgress = ref(0)

const dhImageUrl = ref('')
const dhImageName = ref('')
const dhAudioUrl = ref('')
const dhAudioName = ref('')
const dhResult = ref(null)
const dhLoading = ref(false)
const dhProgress = ref(0)

const results = ref([])

const isVoiceCloneDisabled = computed(() => {
  return !voiceCloneText.value.trim() || !voiceCloneRefFileId.value || voiceCloneLoading.value
})

const isDHDisabled = computed(() => {
  return !dhImageUrl.value || !dhAudioUrl.value || dhLoading.value
})

const handleVoiceCloneAudioUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  if (file.size > 10 * 1024 * 1024) {
    toast.warning('音频文件大小不能超过10MB')
    return
  }

  voiceCloneRefAudioName.value = file.name
  voiceCloneLoading.value = true
  voiceCloneProgress.value = 5

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/api/voice-clone/upload-audio`, {
      method: 'POST',
      body: formData
    })

    const data = await response.json()
    if (data.success) {
      voiceCloneRefFileId.value = data.file_id
      voiceCloneRefAudio.value = URL.createObjectURL(file)
      voiceCloneProgress.value = 10
    } else {
      throw new Error(data.detail || '上传失败')
    }
  } catch (error) {
    console.error('上传参考音频失败:', error)
    toast.error('上传参考音频失败: ' + error.message)
    voiceCloneRefAudioName.value = ''
    voiceCloneRefAudio.value = null
  } finally {
    voiceCloneLoading.value = false
  }
}

const removeVoiceCloneAudio = () => {
  if (voiceCloneRefAudio.value && voiceCloneRefAudio.value.startsWith('blob:')) {
    URL.revokeObjectURL(voiceCloneRefAudio.value)
  }
  voiceCloneRefAudio.value = null
  voiceCloneRefAudioName.value = ''
  voiceCloneRefFileId.value = ''
}

const handleVoiceCloneGenerate = async () => {
  if (isVoiceCloneDisabled.value) return

  voiceCloneLoading.value = true
  voiceCloneProgress.value = 15
  voiceCloneResult.value = null

  try {
    const response = await fetch(`${API_BASE_URL}/api/voice-clone/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_text: voiceCloneText.value,
        file_id: voiceCloneRefFileId.value,
        reference_text: voiceCloneRefText.value
      })
    })

    const data = await response.json()
    voiceCloneProgress.value = 90

    if (data.success) {
      voiceCloneProgress.value = 100
      const audioUrl = data.audio_url
        ? (data.audio_url.startsWith('/') ? `${API_BASE_URL}${data.audio_url}` : data.audio_url)
        : null

      voiceCloneResult.value = {
        type: 'audio',
        audio_url: audioUrl,
        voice: data.voice,
        file_id: data.file_id,
        text: voiceCloneText.value,
        created_at: Date.now()
      }

      results.value.unshift(voiceCloneResult.value)
    } else {
      throw new Error(data.detail || '声音克隆失败')
    }
  } catch (error) {
    console.error('声音克隆失败:', error)
    let msg = error.message || '未知错误'
    if (msg.includes('429') || msg.includes('频率超限') || msg.includes('Too Many')) {
      msg = 'API调用频率超限，请等待1-2分钟后重试。如持续出现，请在智谱开放平台检查账户速率限制。'
    } else if (msg.includes('1302')) {
      msg = '账户并发数已达上限，请稍后再试或提升账户权益等级。'
    } else if (msg.includes('1305')) {
      msg = '智谱平台服务过载，请稍后再试。'
    }
    toast.error('声音克隆失败: ' + msg)
  } finally {
    voiceCloneLoading.value = false
    voiceCloneProgress.value = 0
  }
}

const handleDHImageUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  dhImageName.value = file.name
  dhLoading.value = true

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/api/digital-human/upload-image`, {
      method: 'POST',
      body: formData
    })

    const data = await response.json()
    if (data.success) {
      dhImageUrl.value = data.url
    } else {
      throw new Error(data.detail || '上传失败')
    }
  } catch (error) {
    console.error('上传数字人图片失败:', error)
    toast.error('上传图片失败: ' + error.message)
    dhImageName.value = ''
    dhImageUrl.value = ''
  } finally {
    dhLoading.value = false
  }
}

const removeDHImage = () => {
  dhImageUrl.value = ''
  dhImageName.value = ''
}

const handleDHAudioUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  dhAudioName.value = file.name
  dhLoading.value = true

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/api/digital-human/upload-audio`, {
      method: 'POST',
      body: formData
    })

    const data = await response.json()
    if (data.success) {
      dhAudioUrl.value = data.url
    } else {
      throw new Error(data.detail || '上传失败')
    }
  } catch (error) {
    console.error('上传数字人音频失败:', error)
    toast.error('上传音频失败: ' + error.message)
    dhAudioName.value = ''
    dhAudioUrl.value = ''
  } finally {
    dhLoading.value = false
  }
}

const removeDHAudio = () => {
  dhAudioUrl.value = ''
  dhAudioName.value = ''
}

const handleDHGenerate = async () => {
  if (isDHDisabled.value) return

  dhLoading.value = true
  dhProgress.value = 15
  dhResult.value = null

  try {
    const response = await fetch(`${API_BASE_URL}/api/digital-human/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_url: dhImageUrl.value,
        audio_url: dhAudioUrl.value
      })
    })

    const data = await response.json()
    dhProgress.value = 90

    if (data.success) {
      dhProgress.value = 100
      const videoUrl = data.video_url
        ? (data.video_url.startsWith('/') ? `${API_BASE_URL}${data.video_url}` : data.video_url)
        : null

      dhResult.value = {
        type: 'video',
        video_url: videoUrl,
        created_at: Date.now()
      }

      results.value.unshift(dhResult.value)
    } else {
      throw new Error(data.error || data.detail || '数字人生成失败')
    }
  } catch (error) {
    console.error('数字人生成失败:', error)
    toast.error('数字人生成失败: ' + error.message)
  } finally {
    dhLoading.value = false
    dhProgress.value = 0
  }
}

const getAudioUrl = (item) => {
  if (!item || !item.audio_url) return ''
  return item.audio_url.startsWith('/') ? `${API_BASE_URL}${item.audio_url}` : item.audio_url
}

const getVideoUrl = (item) => {
  if (!item || !item.video_url) return ''
  return item.video_url.startsWith('/') ? `${API_BASE_URL}${item.video_url}` : item.video_url
}

const downloadFile = async (url, filename) => {
  try {
    const response = await fetch(url)
    if (response.ok) {
      const blob = await response.blob()
      const blobUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = filename
      a.click()
      URL.revokeObjectURL(blobUrl)
    }
  } catch (error) {
    console.error('下载失败:', error)
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<template>
  <div class="voice-workspace">
    <div class="panel-header">
      <h2>🎙️ 声音 & 数字人</h2>
    </div>

    <div class="mode-section">
      <h3>功能选择</h3>
      <div class="mode-tabs">
        <button
          :class="['mode-tab', { active: activeSubTab === 'voice-clone' }]"
          @click="activeSubTab = 'voice-clone'"
        >
          🎤 声音克隆
        </button>
        <button
          :class="['mode-tab', { active: activeSubTab === 'digital-human' }]"
          @click="activeSubTab = 'digital-human'"
        >
          🧑 数字人
        </button>
      </div>
    </div>

    <!-- 声音克隆 -->
    <div v-if="activeSubTab === 'voice-clone'" class="params-section">
      <h3>声音克隆</h3>
      <div class="feature-desc">文字 + 参考音色 = 新声音</div>

      <div class="param-item">
        <label>目标文本</label>
        <textarea
          v-model="voiceCloneText"
          placeholder="输入想要生成的文字内容..."
          rows="4"
          class="prompt-input"
        ></textarea>
      </div>

      <div class="param-item">
        <label>参考音频文本（可选）</label>
        <textarea
          v-model="voiceCloneRefText"
          placeholder="输入参考音频对应的文字内容，可提高克隆质量..."
          rows="2"
          class="prompt-input"
        ></textarea>
      </div>

      <div class="param-item">
        <label>参考音频</label>
        <div class="upload-area" v-if="!voiceCloneRefAudio">
          <input
            type="file"
            accept="audio/mp3,audio/wav,audio/mpeg,audio/wave,audio/*"
            @change="handleVoiceCloneAudioUpload"
            class="file-input"
            id="vc-audio-input"
          />
          <label for="vc-audio-input" class="upload-label">
            <span class="upload-icon">🎵</span>
            <span class="upload-text">点击上传参考音频</span>
            <span class="upload-hint">支持 mp3、wav 格式，不超过 10MB，建议 3-30 秒</span>
          </label>
        </div>
        <div v-else class="uploaded-file">
          <div class="file-info">
            <span class="file-icon">🎵</span>
            <span class="file-name">{{ voiceCloneRefAudioName }}</span>
          </div>
          <audio :src="voiceCloneRefAudio" controls class="audio-preview"></audio>
          <button @click="removeVoiceCloneAudio" class="remove-btn">✕</button>
        </div>
      </div>

      <div class="generate-section">
        <button
          @click="handleVoiceCloneGenerate"
          class="btn btn-generate"
          :disabled="isVoiceCloneDisabled"
        >
          {{ voiceCloneLoading ? '生成中...' : '🎤 开始克隆' }}
        </button>
        <div v-if="voiceCloneLoading" class="progress-bar-wrapper">
          <div class="progress-bar" :style="{ width: voiceCloneProgress + '%' }"></div>
          <span class="progress-text">{{ voiceCloneProgress }}%</span>
        </div>
      </div>

      <div v-if="voiceCloneResult" class="result-section">
        <h3>克隆结果</h3>
        <div class="audio-result-card">
          <div class="audio-result-info">
            <span class="result-type-badge">音频</span>
            <span class="result-time">{{ formatTime(voiceCloneResult.created_at) }}</span>
          </div>
          <audio :src="getAudioUrl(voiceCloneResult)" controls class="audio-player"></audio>
          <button @click="downloadFile(getAudioUrl(voiceCloneResult), `voice-clone-${Date.now()}.wav`)" class="download-btn">
            ⬇️ 下载音频
          </button>
        </div>
      </div>
    </div>

    <!-- 数字人 -->
    <div v-if="activeSubTab === 'digital-human'" class="params-section">
      <h3>数字人（视频口型）</h3>
      <div class="feature-desc">图片 + 音频 = 数字人</div>

      <div class="upload-grid">
        <div class="param-item">
          <label>数字人图片</label>
          <div class="upload-area" v-if="!dhImageUrl">
            <input
              type="file"
              accept="image/*"
              @change="handleDHImageUpload"
              class="file-input"
              id="dh-image-input"
            />
            <label for="dh-image-input" class="upload-label">
              <span class="upload-icon">🖼️</span>
              <span class="upload-text">点击上传图片</span>
              <span class="upload-hint">正面人脸照片效果最佳</span>
            </label>
          </div>
          <div v-else class="uploaded-file uploaded-image">
            <img :src="dhImageUrl.startsWith('/') ? `${API_BASE_URL}${dhImageUrl}` : dhImageUrl" class="image-preview" />
            <button @click="removeDHImage" class="remove-btn">✕</button>
          </div>
        </div>

        <div class="param-item">
          <label>音频文件</label>
          <div class="upload-area" v-if="!dhAudioUrl">
            <input
              type="file"
              accept="audio/*"
              @change="handleDHAudioUpload"
              class="file-input"
              id="dh-audio-input"
            />
            <label for="dh-audio-input" class="upload-label">
              <span class="upload-icon">🎵</span>
              <span class="upload-text">点击上传音频</span>
              <span class="upload-hint">语音音频文件</span>
            </label>
          </div>
          <div v-else class="uploaded-file">
            <div class="file-info">
              <span class="file-icon">🎵</span>
              <span class="file-name">{{ dhAudioName }}</span>
            </div>
            <audio :src="dhAudioUrl.startsWith('/') ? `${API_BASE_URL}${dhAudioUrl}` : dhAudioUrl" controls class="audio-preview"></audio>
            <button @click="removeDHAudio" class="remove-btn">✕</button>
          </div>
        </div>
      </div>

      <div class="generate-section">
        <button
          @click="handleDHGenerate"
          class="btn btn-generate"
          :disabled="isDHDisabled"
        >
          {{ dhLoading ? '制作中...' : '🧑 开始制作' }}
        </button>
        <div v-if="dhLoading" class="progress-bar-wrapper">
          <div class="progress-bar" :style="{ width: dhProgress + '%' }"></div>
          <span class="progress-text">{{ dhProgress }}%</span>
        </div>
      </div>

      <div v-if="dhResult" class="result-section">
        <h3>数字人结果</h3>
        <div class="video-result-card">
          <div class="video-result-info">
            <span class="result-type-badge">视频</span>
            <span class="result-time">{{ formatTime(dhResult.created_at) }}</span>
          </div>
          <video :src="getVideoUrl(dhResult)" controls class="video-player"></video>
          <button @click="downloadFile(getVideoUrl(dhResult), `digital-human-${Date.now()}.mp4`)" class="download-btn">
            ⬇️ 下载视频
          </button>
        </div>
      </div>
    </div>

    <!-- 历史结果 -->
    <div v-if="results.length > 0" class="history-section">
      <h3>历史结果</h3>
      <div class="history-list">
        <div v-for="(item, index) in results" :key="index" class="history-item">
          <template v-if="item.type === 'audio'">
            <div class="history-item-info">
              <span class="result-type-badge small">音频</span>
              <span class="history-text">{{ item.text?.substring(0, 30) }}{{ item.text?.length > 30 ? '...' : '' }}</span>
            </div>
            <audio :src="getAudioUrl(item)" controls class="audio-player-small"></audio>
          </template>
          <template v-else-if="item.type === 'video'">
            <div class="history-item-info">
              <span class="result-type-badge small">视频</span>
              <span class="history-text">数字人视频</span>
            </div>
            <video :src="getVideoUrl(item)" controls class="video-player-small"></video>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.voice-workspace {
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
.generate-section,
.history-section {
  padding: 20px;
  border-bottom: 1px solid #333;
}

.mode-section h3,
.params-section h3,
.history-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1rem;
  color: #00d4ff;
}

.feature-desc {
  color: #888;
  font-size: 0.85rem;
  margin-bottom: 15px;
  padding: 8px 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(0, 212, 255, 0.15);
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

.param-item label {
  display: block;
  margin-bottom: 8px;
  color: #ccc;
  font-size: 0.9rem;
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
  box-sizing: border-box;
}

.prompt-input:focus {
  outline: none;
  border-color: #00d4ff;
}

.upload-area {
  position: relative;
  border: 2px dashed #4a4a6a;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  transition: all 0.2s;
  cursor: pointer;
}

.upload-area:hover {
  border-color: #00d4ff;
  background: rgba(0, 212, 255, 0.05);
}

.file-input {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  opacity: 0;
  cursor: pointer;
}

.upload-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.upload-icon {
  font-size: 2rem;
}

.upload-text {
  color: #ccc;
  font-size: 0.9rem;
}

.upload-hint {
  color: #666;
  font-size: 0.75rem;
}

.uploaded-file {
  position: relative;
  background: #2a2a4a;
  border: 1px solid #3a3a5a;
  border-radius: 8px;
  padding: 12px;
}

.uploaded-image {
  padding: 0;
  overflow: hidden;
}

.image-preview {
  width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: 8px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.file-icon {
  font-size: 1.2rem;
}

.file-name {
  color: #ccc;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.remove-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 68, 68, 0.2);
  color: #ff4444;
  cursor: pointer;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: rgba(255, 68, 68, 0.4);
}

.audio-preview {
  width: 100%;
  height: 36px;
  border-radius: 4px;
}

.audio-preview::-webkit-media-controls-panel {
  background: #1a1a2e;
}

.upload-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
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

.progress-bar-wrapper {
  position: relative;
  height: 24px;
  background: #1a1a2e;
  border-radius: 12px;
  margin-top: 12px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  border-radius: 12px;
  transition: width 0.3s ease;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.75rem;
  font-weight: bold;
  color: #fff;
}

.result-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #333;
}

.result-section h3 {
  color: #00ff88;
  margin-bottom: 12px;
}

.audio-result-card,
.video-result-card {
  background: #2a2a4a;
  border: 1px solid #3a3a5a;
  border-radius: 8px;
  padding: 15px;
}

.audio-result-info,
.video-result-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.result-type-badge {
  background: #00d4ff;
  color: #000;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
}

.result-type-badge.small {
  font-size: 0.65rem;
  padding: 1px 6px;
}

.result-time {
  color: #888;
  font-size: 0.8rem;
}

.audio-player {
  width: 100%;
  margin-bottom: 12px;
}

.video-player {
  width: 100%;
  border-radius: 6px;
  margin-bottom: 12px;
}

.download-btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 6px;
  background: #1a6b1a;
  color: #fff;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.download-btn:hover {
  background: #2a8b2a;
}

.history-section h3 {
  color: #aaa;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-item {
  background: #2a2a4a;
  border: 1px solid #3a3a5a;
  border-radius: 8px;
  padding: 12px;
}

.history-item-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.history-text {
  color: #ccc;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.audio-player-small {
  width: 100%;
  height: 32px;
}

.video-player-small {
  width: 100%;
  border-radius: 4px;
  max-height: 180px;
}

@media (max-width: 700px) {
  .upload-grid {
    grid-template-columns: 1fr;
  }
}
</style>
