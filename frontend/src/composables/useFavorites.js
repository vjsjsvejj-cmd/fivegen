import { ref, watch } from 'vue'
import { resolveUrl, getDisplayUrl, handleImageError } from '../utils/media.js'

const STORAGE_KEY = 'fivegen_favorites'

function loadFromStorage() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveToStorage(favorites) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites))
  } catch (e) {
    console.warn('Failed to save favorites to localStorage:', e)
  }
}

export function useFavorites() {
  const favorites = ref(loadFromStorage())
  const favoriteModalVisible = ref(false)
  const favoriteModalType = ref('image')
  const favoriteModalUrl = ref('')

  watch(favorites, (newVal) => {
    saveToStorage(newVal)
  }, { deep: true })

  const toggleFavorite = (item) => {
    if (!item?.task_id) return
    const index = favorites.value.findIndex(f => f.task_id === item.task_id)
    if (index === -1) {
      favorites.value.push({ ...item, favoriteTime: Date.now() })
    } else {
      favorites.value.splice(index, 1)
    }
  }

  const isFavorite = (item) => {
    if (!item?.task_id) return false
    return favorites.value.some(f => f.task_id === item.task_id)
  }

  const getFavoriteDisplayUrl = getDisplayUrl

  const handleFavoriteImageError = handleImageError

  const openFavoritePreview = (item) => {
    favoriteModalType.value = item.type === 'video' ? 'video' : 'image'
    favoriteModalUrl.value = resolveUrl(item.remote_url || item.url)
    favoriteModalVisible.value = true
  }

  const closeFavoriteModal = () => {
    favoriteModalVisible.value = false
  }

  return {
    favorites,
    favoriteModalVisible,
    favoriteModalType,
    favoriteModalUrl,
    toggleFavorite,
    isFavorite,
    getFavoriteDisplayUrl,
    handleFavoriteImageError,
    openFavoritePreview,
    closeFavoriteModal,
  }
}
