import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { desktop, isTauriEnv, type BackendStatus } from './index'

function detectOS(): 'windows' | 'mac' | 'linux' | 'web' {
  if (!isTauriEnv()) return 'web'
  const ua = navigator.userAgent.toLowerCase()
  if (ua.includes('win')) return 'windows'
  if (ua.includes('mac')) return 'mac'
  return 'linux'
}

export function useDesktop() {
  const isDesktop = ref(false)
  const os = ref<'windows' | 'mac' | 'linux' | 'web'>('web')
  const backendStatus = ref<BackendStatus>({ running: false, url: 'http://localhost:8000' })
  const bootVisible = ref(false)
  const bootMessage = ref('正在启动迁移服务...')

  let unsub: (() => void) | null = null
  let blurHandler: (() => void) | null = null
  let focusHandler: (() => void) | null = null
  let resizeHandler: (() => void) | null = null

  const applyBodyClass = () => {
    const body = document.body
    if (isDesktop.value) {
      body.classList.add('desktop-app')
      body.classList.remove('os-windows', 'os-mac', 'os-linux')
      body.classList.add(`os-${os.value}`)
    } else {
      body.classList.remove('desktop-app', 'os-windows', 'os-mac', 'os-linux', 'window-inactive')
    }
  }

  onMounted(async () => {
    isDesktop.value = isTauriEnv()
    os.value = detectOS()
    applyBodyClass()

    if (!isDesktop.value) {
      bootVisible.value = false
      return
    }

    bootVisible.value = true
    bootMessage.value = '正在启动本地迁移服务...'

    unsub = desktop.subscribe((status) => {
      backendStatus.value = status
      if (status.running) {
        bootMessage.value = '服务就绪,正在加载界面...'
        setTimeout(() => {
          bootVisible.value = false
        }, 600)
      } else if (status.startedAt) {
        bootMessage.value = '服务已停止'
      }
    })

    blurHandler = () => document.body.classList.add('window-inactive')
    focusHandler = () => document.body.classList.remove('window-inactive')
    window.addEventListener('blur', blurHandler)
    window.addEventListener('focus', focusHandler)

    const checkSize = () => {
      if (window.innerWidth < 800) {
        document.body.classList.add('window-too-small')
      } else {
        document.body.classList.remove('window-too-small')
      }
    }
    resizeHandler = checkSize
    window.addEventListener('resize', resizeHandler)
    checkSize()

    try {
      bootMessage.value = '正在拉起后端进程...'
      await desktop.startBackend()
    } catch (err) {
      console.warn('[useDesktop] 后端启动失败:', err)
      bootMessage.value = '后端启动失败,请检查 Python 环境'
      setTimeout(() => {
        bootVisible.value = false
      }, 5000)
    }
  })

  onUnmounted(() => {
    unsub?.()
    if (blurHandler) window.removeEventListener('blur', blurHandler)
    if (focusHandler) window.removeEventListener('focus', focusHandler)
    if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  })

  return reactive({
    isDesktop,
    os,
    backendStatus,
    bootVisible,
    bootMessage,
  })
}
