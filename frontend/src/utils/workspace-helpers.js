export function createModelChangeHandler(selectedModelRef, resolutionRef, models) {
  return (e) => {
    const modelKey = e.target.value
    selectedModelRef.value = modelKey
    const modelConfig = models[modelKey]
    if (modelConfig) {
      resolutionRef.value = modelConfig.default_resolution || ''
    }
  }
}
