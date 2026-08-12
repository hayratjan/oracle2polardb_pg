import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
import 'bootstrap-icons/font/bootstrap-icons.css'
import './styles/global.css'
import './styles/desktop.css'
import { bootstrapDesktop, isTauriEnv } from './desktop'

async function main() {
  if (isTauriEnv()) {
    try {
      await bootstrapDesktop()
      console.info('[main] 桌面后端已就绪')
    } catch (err) {
      console.warn('[main] 桌面后端启动失败,前端仍将启动:', err)
    }
  }

  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.mount('#app')
}

main().catch((err) => {
  console.error('[main] 应用启动失败:', err)
})
