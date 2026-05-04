<script setup>
import { ref, watch, inject } from 'vue'
import { API_BASE_URL } from '../utils/config.js'

const confirmDialog = inject('confirm', async (msg) => window.confirm(msg))

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'apply'])

const uploadedFile = ref(null)
const filePreviewUrl = ref(null)
const isAnalyzing = ref(false)
const analysisResult = ref(null)
const errorMessage = ref(null)
const developerMode = ref(false); // 开发者模式，用于修改提示词模板
const developerClickCount = ref(0); // 点击次数计数器，用于触发开发者模式
const savedTemplate = ref(''); // 保存成功提示
const originalTemplate = ref(''); // 原始模板备份

// 提示词模板初始值
const defaultPromptTemplate = `# 角色定位
你是专为Seedance 2.0模型服务的顶级文生图/文生视频提示词逆向工程师，唯一任务是：解析用户上传的图片/视频，输出可直接在Seedance 2.0中生成高度匹配内容的完整中文提示词，严格遵守所有规则，禁止任何偏离任务的输出。

# 核心拆解规则（必须全覆盖，无遗漏）
## 图片/视频通用规则
1. 核心主体：精准拆解核心对象、物种/人物特征、五官细节、姿态动作、表情神态、服饰穿搭、道具细节、毛发/皮肤/材质纹理，精准到可复现的颗粒度
2. 场景环境：完整描述背景环境、空间透视关系、场景层次、前后景关系、环境氛围、天气状态、时间时段、光线环境
3. 风格画质：精准定义艺术风格、所属AI模型流派、渲染器类型、画质等级、分辨率标准、画面精度、抗锯齿、细节丰富度
4. 光影色彩：精准拆解主光类型、辅光方向、光影硬度、光影氛围、画面主色调、配色体系、色彩饱和度、对比度、色偏风格
5. 构图镜头：精准描述画面构图方式、镜头焦段、拍摄视角、画面比例、景深效果、焦点位置、画面留白

## 视频专属补充规则（上传视频时必须执行）
1. 必须拆解视频的核心动作变化、时序逻辑、关键分镜要点、主体运动轨迹
2. 必须补充完整的运镜方式、镜头运动逻辑、镜头切换节奏、画面衔接方式
3. 必须给出适配Seedance 2.0的推荐时长、帧率、关键帧间隔参数
4. 输出的提示词必须是连贯的、可直接生成对应完整视频的内容，禁止碎片化描述

# 输出强制规范（100%严格执行，禁止任何修改）
1. 必须严格分为【正向提示词】【反向提示词】两个独立模块，禁止新增其他模块，禁止任何解释性、说明性文字
2. 正向提示词：
    - 必须使用Seedance 2.0适配的中文逗号分隔的关键词格式，按「核心主体>场景环境>风格画质>光影色彩>构图镜头>视频专属参数」的权重优先级排序，核心主体关键词放在最前
    - 优先使用中文，仅补充Seedance 2.0识别度更高的必要英文专业术语，禁止纯英文输出
    - 必须贴合Seedance 2.0的关键词偏好，使用该模型高响应度的画质、风格、光影、运镜关键词，禁止生僻词、无效词
3. 反向提示词：
    - 固定包含基础负面词：低画质，模糊，失焦，畸形，五官崩坏，肢体残缺，画面杂乱，逻辑混乱，水印，文字，签名，画面卡顿，动作不连贯，跳帧
    - 额外补充针对当前内容的专属负面词，排除与画面/视频不符的元素、风格、缺陷
4. 禁止输出任何规则解读、分析说明、客套话，仅输出两个模块的提示词内容`;

// 提示词模板
const promptTemplate = ref(defaultPromptTemplate);

// 弹窗打开时备份模板
watch(() => props.visible, (newVal) => {
  if (newVal) {
    originalTemplate.value = promptTemplate.value;
    savedTemplate.value = '';
  }
});

// 保存模板
const saveTemplate = () => {
  savedTemplate.value = 'saved';
  setTimeout(() => {
    savedTemplate.value = '';
  }, 2000);
};

// 重置模板
const resetTemplate = async () => {
  const confirmed = await confirmDialog('确定要重置为默认模板吗？')
  if (confirmed) {
    promptTemplate.value = defaultPromptTemplate;
    savedTemplate.value = 'reset';
    setTimeout(() => {
      savedTemplate.value = '';
    }, 2000);
  }
};

// 处理文件选择
const handleFileChange = (e) => {
  const file = e.target.files[0]
  if (file) {
    if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) {
      errorMessage.value = '请上传图片或视频文件'
      return
    }
    uploadedFile.value = file
    errorMessage.value = null
    analysisResult.value = null
    
    // 创建预览URL
    if (file.type.startsWith('image/')) {
      filePreviewUrl.value = URL.createObjectURL(file)
    } else {
      filePreviewUrl.value = null // 视频预览暂不处理
    }
  }
}

// 处理拖拽
const handleDrop = (e) => {
  e.preventDefault()
  const file = e.dataTransfer.files[0]
  if (file) {
    if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) {
      errorMessage.value = '请上传图片或视频文件'
      return
    }
    uploadedFile.value = file
    errorMessage.value = null
    analysisResult.value = null
    
    if (file.type.startsWith('image/')) {
      filePreviewUrl.value = URL.createObjectURL(file)
    } else {
      filePreviewUrl.value = null
    }
  }
}

// 触发开发者模式（点击标题5次）
const handleTitleClick = () => {
  developerClickCount.value++
  if (developerClickCount.value >= 5) {
    developerMode.value = !developerMode.value
    developerClickCount.value = 0
  }
}

// 执行解析
const handleAnalyze = async () => {
  if (!uploadedFile.value) {
    errorMessage.value = '请先上传文件'
    return
  }
  
  isAnalyzing.value = true
  errorMessage.value = null
  
  try {
    const formData = new FormData()
    formData.append('file', uploadedFile.value)
    if (developerMode.value) {
      formData.append('template', promptTemplate.value)
    }
    
    const response = await fetch(`${API_BASE_URL}/api/inversion/analyze`, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`)
    }
    
    const result = await response.json()
    if (result.success) {
      analysisResult.value = result.data
    } else {
      throw new Error('解析失败')
    }
  } catch (err) {
    console.error('Analysis error:', err)
    errorMessage.value = err.message || '解析过程中发生错误'
  } finally {
    isAnalyzing.value = false
  }
}

// 应用提示词
const handleApply = () => {
  if (analysisResult.value) {
    emit('apply', {
      positive: analysisResult.value.positive,
      negative: analysisResult.value.negative
    })
  }
  closeModal()
}

// 关闭弹窗
const revokePreviewUrl = () => {
  if (filePreviewUrl.value && filePreviewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(filePreviewUrl.value)
  }
}

const closeModal = () => {
  revokePreviewUrl()
  uploadedFile.value = null
  filePreviewUrl.value = null
  analysisResult.value = null
  errorMessage.value = null
  isAnalyzing.value = false
  emit('close')
}

// 清空文件
const clearFile = () => {
  revokePreviewUrl()
  uploadedFile.value = null
  filePreviewUrl.value = null
  analysisResult.value = null
  errorMessage.value = null
}
</script>

<template>
  <div v-if="visible" class="inversion-modal-overlay" @click.self="closeModal">
    <div class="inversion-modal" role="dialog" aria-modal="true" aria-label="逆向解析">
      <div class="modal-header">
        <h2 @click="handleTitleClick" class="modal-title">
          🔍 逆向解析
          <span v-if="developerMode" class="dev-badge">🔧 开发者模式</span>
        </h2>
        <button @click="closeModal" class="close-btn">✕</button>
      </div>
      
      <div class="modal-content">
        <!-- 开发者模式：模板编辑器 -->
        <div v-if="developerMode" class="developer-section">
          <h4 class="dev-section-title">📝 提示词模板</h4>
          <textarea 
            v-model="promptTemplate" 
            class="template-textarea"
            rows="15"
            placeholder="编辑提示词模板..."
          ></textarea>
          <div class="dev-buttons">
            <button @click="saveTemplate" class="dev-btn save-btn">
              {{ savedTemplate === 'saved' ? '✓ 已保存' : '💾 保存模板' }}
            </button>
            <button @click="resetTemplate" class="dev-btn reset-btn">
              {{ savedTemplate === 'reset' ? '✓ 已重置' : '🔄 重置默认' }}
            </button>
          </div>
          <p class="dev-hint">💡 此区域仅开发者可见，连续点击标题可切换</p>
        </div>
        
        <!-- 上传区域 -->
        <div v-if="!uploadedFile" class="upload-area">
          <div 
            class="drop-zone"
            @drop="handleDrop"
            @dragover.prevent
            @click="$refs.fileInput.click()"
          >
            <div class="upload-icon">📁</div>
            <p>点击或拖拽上传图片或视频</p>
            <p class="upload-hint">支持 jpg, png, mp4 等格式</p>
            <input 
              ref="fileInput"
              type="file"
              accept="image/*,video/*"
              @change="handleFileChange"
              style="display: none"
            />
          </div>
        </div>
        
        <!-- 文件预览 -->
        <div v-else class="file-preview">
          <div class="preview-container">
            <img v-if="filePreviewUrl" :src="filePreviewUrl" alt="预览" class="preview-image" />
            <div v-else class="video-placeholder">
              <span class="video-icon">🎬</span>
              <span class="file-name">{{ uploadedFile.name }}</span>
            </div>
          </div>
          <div class="file-info">
            <span class="file-name">{{ uploadedFile.name }}</span>
            <span class="file-size">{{ (uploadedFile.size / 1024 / 1024).toFixed(2) }} MB</span>
          </div>
          <button @click="clearFile" class="clear-btn">重新上传</button>
        </div>
        
        <!-- 错误信息 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
        
        <!-- 解析按钮 -->
        <div v-if="uploadedFile && !analysisResult" class="analyze-section">
          <button 
            @click="handleAnalyze" 
            class="analyze-btn"
            :disabled="isAnalyzing"
          >
            {{ isAnalyzing ? '⏳ 解析中...' : '🚀 一键解析' }}
          </button>
        </div>
        
        <!-- 解析结果 -->
        <div v-if="analysisResult" class="result-section">
          <h3 class="result-title">✅ 解析完成</h3>
          
          <div class="result-box">
            <h4>【正向提示词】</h4>
            <textarea 
              :value="analysisResult.positive" 
              readonly
              class="result-textarea"
              rows="6"
            ></textarea>
          </div>
          
          <div v-if="analysisResult.negative" class="result-box">
            <h4>【反向提示词】</h4>
            <textarea 
              :value="analysisResult.negative" 
              readonly
              class="result-textarea"
              rows="4"
            ></textarea>
          </div>
          
          <div class="result-actions">
            <button @click="clearFile" class="retry-btn">重新解析</button>
            <button @click="handleApply" class="apply-btn">✨ 应用到提示词</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inversion-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.inversion-modal {
  background: #16213e;
  border-radius: 12px;
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid #333;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #333;
}

.modal-title {
  margin: 0;
  font-size: 1.3rem;
  color: #00d4ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
}

.dev-badge {
  font-size: 0.85rem;
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
  color: #fff;
  padding: 3px 10px;
  border-radius: 20px;
}

.close-btn {
  background: none;
  border: none;
  color: #aaa;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 5px;
}

.close-btn:hover {
  color: #fff;
}

.modal-content {
  padding: 20px;
}

.developer-section {
  margin-bottom: 20px;
  padding: 15px;
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.3);
  border-radius: 8px;
}

.dev-section-title {
  margin: 0 0 10px 0;
  color: #ff6b6b;
  font-size: 0.95rem;
}

.template-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #1a1a2e;
  color: #fff;
  font-size: 0.85rem;
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;
}

.dev-buttons {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.dev-btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 500;
}

.save-btn {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: #000;
}

.save-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(74, 222, 128, 0.3);
}

.reset-btn {
  background: #4a4a6a;
  color: #fff;
}

.reset-btn:hover {
  background: #5a5a7a;
  transform: translateY(-2px);
}

.dev-hint {
  margin: 10px 0 0 0;
  font-size: 0.8rem;
  color: #888;
}

.upload-area {
  margin-bottom: 20px;
}

.drop-zone {
  border: 2px dashed #4a4a6a;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.drop-zone:hover {
  border-color: #00d4ff;
  background: rgba(0, 212, 255, 0.05);
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 10px;
}

.drop-zone p {
  margin: 5px 0;
  color: #ccc;
}

.upload-hint {
  font-size: 0.85rem;
  color: #888 !important;
}

.file-preview {
  text-align: center;
  margin-bottom: 20px;
}

.preview-container {
  margin-bottom: 15px;
}

.preview-image {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
}

.video-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  background: #2a2a4a;
  border-radius: 8px;
}

.video-icon {
  font-size: 3rem;
  margin-bottom: 10px;
}

.file-info {
  display: flex;
  justify-content: center;
  gap: 15px;
  color: #aaa;
  font-size: 0.9rem;
  margin-bottom: 15px;
}

.clear-btn {
  background: #4a4a6a;
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #5a5a7a;
}

.error-message {
  background: rgba(255, 71, 87, 0.1);
  border: 1px solid #ff4757;
  color: #ff4757;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.analyze-section {
  text-align: center;
}

.analyze-btn {
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

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(0, 212, 255, 0.3);
}

.analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-section {
  margin-top: 20px;
}

.result-title {
  color: #00ff88;
  margin-top: 0;
  margin-bottom: 15px;
}

.result-box {
  margin-bottom: 15px;
}

.result-box h4 {
  color: #00d4ff;
  margin: 0 0 10px 0;
  font-size: 0.95rem;
}

.result-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #2a2a4a;
  color: #fff;
  font-size: 0.9rem;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;
}

.result-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.retry-btn {
  flex: 1;
  padding: 12px;
  background: #4a4a6a;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn:hover {
  background: #5a5a7a;
}

.apply-btn {
  flex: 2;
  padding: 12px;
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  color: #000;
  font-weight: bold;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.apply-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(0, 212, 255, 0.3);
}
</style>
