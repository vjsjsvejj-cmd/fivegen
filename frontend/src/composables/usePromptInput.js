import { ref, computed, nextTick } from 'vue'

export function usePromptInput({ prompt, promptTextarea, atFilesList, templates }) {
  const showAtSuggestions = ref(false)
  const showTemplateSuggestions = ref(false)
  const templateSearchTerm = ref('')

  const filteredTemplates = computed(() => {
    if (!templateSearchTerm.value) {
      return templates.value
    }
    const searchTerm = templateSearchTerm.value.toLowerCase()
    return templates.value.filter(template =>
      template.name.toLowerCase().includes(searchTerm) ||
      template.content.toLowerCase().includes(searchTerm)
    )
  })

  const handlePromptInput = (e) => {
    const value = e.target.value
    const hasAt = value.endsWith('@')
    if (hasAt && atFilesList.value.length > 0) {
      showAtSuggestions.value = true
      showTemplateSuggestions.value = false
      templateSearchTerm.value = ''
    } else {
      showAtSuggestions.value = false
    }

    const lastHashIndex = value.lastIndexOf('#')
    if (lastHashIndex !== -1) {
      const searchTerm = value.substring(lastHashIndex + 1).trim()
      templateSearchTerm.value = searchTerm
      showTemplateSuggestions.value = templates.value.length > 0
      showAtSuggestions.value = false
    } else if (!hasAt) {
      showTemplateSuggestions.value = false
      templateSearchTerm.value = ''
    }
  }

  const handleKeydown = (e) => {
    if (e.key === 'Escape') {
      showAtSuggestions.value = false
      showTemplateSuggestions.value = false
    }
    if (e.key === 'Enter' && (showAtSuggestions.value || showTemplateSuggestions.value)) {
      showAtSuggestions.value = false
      showTemplateSuggestions.value = false
    }
    if (e.key === '@' && atFilesList.value.length > 0) {
      setTimeout(() => {
        showAtSuggestions.value = true
        showTemplateSuggestions.value = false
      }, 10)
    }
    if (e.key === '#' && templates.value.length > 0) {
      setTimeout(() => {
        showTemplateSuggestions.value = true
        showAtSuggestions.value = false
      }, 10)
    }
  }

  const selectAtFile = (file) => {
    showAtSuggestions.value = false
    const currentCursorPos = promptTextarea.value?.selectionStart || prompt.value.length
    const atIndex = prompt.value.lastIndexOf('@', currentCursorPos)

    const fileIndex = atFilesList.value.findIndex(f => f.id === file.id)
    let shortCode = file.shortCode
    if (!shortCode) {
      if (file.fileType === 'video') {
        shortCode = `视频${fileIndex + 1}`
      } else if (file.fileType === 'audio') {
        shortCode = `音频${fileIndex + 1}`
      } else {
        shortCode = `图片${fileIndex + 1}`
      }
    }

    const before = prompt.value.substring(0, atIndex)
    const after = prompt.value.substring(currentCursorPos)
    prompt.value = before + '@' + shortCode + ' ' + after

    nextTick(() => {
      if (promptTextarea.value) {
        promptTextarea.value.focus()
        const newPos = before.length + 1 + shortCode.length + 1
        promptTextarea.value.selectionStart = newPos
        promptTextarea.value.selectionEnd = newPos
      }
    })
  }

  const selectTemplate = (template) => {
    showTemplateSuggestions.value = false
    templateSearchTerm.value = ''
    const hashIndex = prompt.value.lastIndexOf('#')
    prompt.value = prompt.value.substring(0, hashIndex) + template.content + ' '

    nextTick(() => {
      if (promptTextarea.value) {
        promptTextarea.value.focus()
        promptTextarea.value.selectionStart = promptTextarea.value.value.length
        promptTextarea.value.selectionEnd = promptTextarea.value.value.length
      }
    })
  }

  const buildPromptMapping = () => {
    const mapping = {}
    const files = atFilesList.value
    files.forEach((file, index) => {
      let shortCode = file.shortCode
      if (!shortCode) {
        if (file.fileType === 'video') {
          shortCode = `视频${index + 1}`
        } else if (file.fileType === 'audio') {
          shortCode = `音频${index + 1}`
        } else {
          shortCode = `图片${index + 1}`
        }
      }
      mapping[`@${shortCode}`] = file.url
    })
    return mapping
  }

  const replacePromptCodes = (text) => {
    const mapping = buildPromptMapping()
    let result = text
    for (const [code, url] of Object.entries(mapping)) {
      result = result.replace(new RegExp(code.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), url)
    }
    return result
  }

  return {
    showAtSuggestions,
    showTemplateSuggestions,
    templateSearchTerm,
    filteredTemplates,
    handlePromptInput,
    handleKeydown,
    selectAtFile,
    selectTemplate,
    buildPromptMapping,
    replacePromptCodes,
  }
}
