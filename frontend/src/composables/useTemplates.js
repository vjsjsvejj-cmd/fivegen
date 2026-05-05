import { ref, computed } from 'vue'
import socketManager from '../utils/socket'

export const defaultTemplates = [
  { id: 'template_1', name: 'Slogan', content: '「文字内容」+「出现时机」+「出现位置」+「出现方式」，「文字特征（颜色、风格）」', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_2', name: '字幕', content: '画面底部出现字幕，字幕内容为"……"，字幕需与音频节奏完全同步。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_3', name: '气泡台词', content: '「角色」说："……"，角色话说时周围出现气泡，气泡里写着台词。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_4', name: '主体多视角图参考', content: '参考/提取/结合+「图片 n」中的「主体」，生成「画面描述」，保持「主体」特征一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_5', name: '多图参考', content: '参考/提取/结合/按照/生成+「图片n」中的「被参考元素描述」，生成「画面描述」，保持「被参考元素」特征一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_6', name: '视频参考', content: '参考「视频n」的「动作描述」，生成「画面描述」，保持动作细节一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_7', name: '运镜参考', content: '参考「视频n」的「运镜描述」，生成「画面描述」，保持运镜一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_8', name: '特效参考', content: '参考「视频n」的「特效描述」，生成「画面描述」，保持特效一致。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_9', name: '增加元素', content: '在「视频n」的「时间位置」+「空间位置」，增加「理想元素描述」。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_10', name: '删除元素', content: '删除「视频n」中的「被删除元素」，视频其他内容保持不变。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_11', name: '修改元素', content: '将「视频n」中的「被更换元素描述」，替换为「理想元素描述」。', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_12', name: '视频延长', content: '向前/向后延长「视频n」+「需延长的视频描述」\n生成「视频n」之前/之后的内容+「需延长的视频描述」', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
  { id: 'template_13', name: '轨道补齐', content: '「视频1」+「过渡画面描述」+接「视频2」+「过渡画面描述」+接「视频3」', fullWidth: false, created_at: Date.now(), updated_at: Date.now() },
]

export function useTemplates({ toast, confirmDialog }) {
  const templates = ref([...defaultTemplates])
  const showTemplateEditor = ref(false)
  const isAddingTemplate = ref(false)
  const editingTemplate = ref(null)
  const newTemplate = ref({ name: '', content: '', fullWidth: false })
  const templatePanelSearch = ref('')

  const filteredTemplatesForPanel = computed(() => {
    if (!templatePanelSearch.value) {
      return templates.value
    }
    const searchTerm = templatePanelSearch.value.toLowerCase()
    return templates.value.filter(template =>
      template.name.toLowerCase().includes(searchTerm) ||
      template.content.toLowerCase().includes(searchTerm)
    )
  })

  const currentEditingTemplate = computed({
    get: () => isAddingTemplate.value ? newTemplate.value : (editingTemplate.value || newTemplate.value),
    set: (val) => {
      if (isAddingTemplate.value) {
        newTemplate.value = val
      } else if (editingTemplate.value) {
        editingTemplate.value = val
      }
    }
  })

  const getTemplates = () => {
    socketManager.getTemplates()
  }

  const openAddTemplate = () => {
    isAddingTemplate.value = true
    newTemplate.value = { name: '', content: '', fullWidth: false }
    showTemplateEditor.value = true
  }

  const addTemplate = () => {
    if (!newTemplate.value.name.trim() || !newTemplate.value.content.trim()) {
      toast.warning('模版名称和内容不能为空！')
      return
    }
    socketManager.addTemplate(newTemplate.value)
    showTemplateEditor.value = false
    isAddingTemplate.value = false
    newTemplate.value = { name: '', content: '', fullWidth: false }
  }

  const editTemplate = (template) => {
    isAddingTemplate.value = false
    editingTemplate.value = { ...template }
    showTemplateEditor.value = true
  }

  const saveTemplateEdit = () => {
    if (isAddingTemplate.value) {
      addTemplate()
    } else {
      if (!editingTemplate.value.name.trim() || !editingTemplate.value.content.trim()) {
        toast.warning('模版名称和内容不能为空！')
        return
      }
      socketManager.updateTemplate(editingTemplate.value.id, editingTemplate.value)
      showTemplateEditor.value = false
      editingTemplate.value = null
    }
  }

  const deleteTemplate = async (templateId) => {
    const confirmed = await confirmDialog.value?.show('确定要删除这个模版吗？')
    if (confirmed) {
      socketManager.deleteTemplate(templateId)
    }
  }

  const cancelTemplateEdit = () => {
    showTemplateEditor.value = false
    editingTemplate.value = null
  }

  const _handleTemplatesList = (data) => {
    templates.value = data.templates || []
  }
  const _handleTemplateError = (data) => {
    toast.error('模版操作失败: ' + data.error)
  }

  const registerSocketEvents = () => {
    socketManager.on('templates_list', _handleTemplatesList)
    socketManager.on('template_error', _handleTemplateError)
  }

  const unregisterSocketEvents = () => {
    socketManager.off('templates_list', _handleTemplatesList)
    socketManager.off('template_error', _handleTemplateError)
  }

  return {
    templates,
    showTemplateEditor,
    isAddingTemplate,
    editingTemplate,
    newTemplate,
    templatePanelSearch,
    filteredTemplatesForPanel,
    currentEditingTemplate,
    getTemplates,
    openAddTemplate,
    addTemplate,
    editTemplate,
    saveTemplateEdit,
    deleteTemplate,
    cancelTemplateEdit,
    registerSocketEvents,
    unregisterSocketEvents,
  }
}
