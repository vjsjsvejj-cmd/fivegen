import { API_BASE_URL } from './config.js'

export const resolveUrl = (url) => {
  if (!url) return ''
  return url.startsWith('/') ? `${API_BASE_URL}${url}` : url
}

export const getDisplayUrl = (item) => {
  if (!item) return ''
  if (item.type === 'video') {
    return resolveUrl(item.thumbnail || item.url)
  }
  return resolveUrl(item.url || item.remote_url)
}

export const handleImageError = (event, item) => {
  if (item.remote_url && event.target.src !== item.remote_url) {
    event.target.src = item.remote_url
  }
}
