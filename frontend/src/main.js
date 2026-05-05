import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)

app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue Error]', info, err)
}

app.config.warnHandler = (msg, instance, trace) => {
  console.warn('[Vue Warn]', msg)
}

window.addEventListener('unhandledrejection', (event) => {
  console.error('[Unhandled Promise]', event.reason)
})

app.mount('#app')
