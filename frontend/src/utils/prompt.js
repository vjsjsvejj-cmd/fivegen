const ESCAPE_MAP = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#x27;'
}

const escapeHtml = (str) => {
  return str.replace(/[&<>"']/g, (ch) => ESCAPE_MAP[ch])
}

export const formatPrompt = (text) => {
  if (!text) return ''
  const escaped = escapeHtml(text)
  return escaped
    .replace(/@图片(\d+)/g, '<span style="color: #00d4ff; font-weight: bold;">@图片$1</span>')
    .replace(/@视频(\d+)/g, '<span style="color: #ff4444; font-weight: bold;">@视频$1</span>')
    .replace(/@音频(\d+)/g, '<span style="color: #00ff88; font-weight: bold;">@音频$1</span>')
    .replace(/@首帧/g, '<span style="color: #00d4ff; font-weight: bold;">@首帧</span>')
    .replace(/@尾帧/g, '<span style="color: #ff4444; font-weight: bold;">@尾帧</span>')
}
