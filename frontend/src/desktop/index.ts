/**
 * 桌面应用(Tauri)运行环境支持
 */

import type { invoke } from '@tauri-apps/api/core'

export const isTauriEnv = (): boolean => {
  return typeof (window as any).__TAURI_INTERNALS__ !== 'undefined'
    || (typeof (window as any).__TAURI__ !== 'undefined')
    || (typeof window !== 'undefined' && 'isTauri' in window && (window as any).isTauri === true)
    || (typeof __TAURI_ENV__ !== 'undefined' && __TAURI_ENV__ === true)
}

async function safeInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T | null> {
  if (!isTauriEnv()) return null
  try {
    const mod = await import('@tauri-apps/api/core')
    const fn: typeof invoke = mod.invoke
    return await fn<T>(cmd, args)
  } catch (err) {
    console.error(`[desktop] invoke ${cmd} 失败:`, err)
    return null
  }
}

export interface BackendStatus {
  running: boolean
  url: string
  pid?: number
  startedAt?: number
}

export interface SystemInfo {
  os: string
  arch: string
  backend_url: string
  version: string
}

type StatusListener = (status: BackendStatus) => void

class DesktopRuntime {
  private listeners = new Set<StatusListener>()
  private _current: BackendStatus = {
    running: false,
    url: 'http://localhost:8000',
  }
  private starting: Promise<BackendStatus> | null = null
  private pollTimer: number | null = null

  get current(): BackendStatus {
    return this._current
  }

  subscribe(listener: StatusListener): () => void {
    this.listeners.add(listener)
    listener(this.current)
    return () => this.listeners.delete(listener)
  }

  private emit(next: BackendStatus) {
    this._current = next
    this.listeners.forEach((l) => l(next))
  }

  async getBackendUrl(): Promise<string> {
    if (!isTauriEnv()) return 'http://localhost:8000'
    const url = await safeInvoke<string>('backend_url')
    return url || 'http://localhost:8000'
  }

  async startBackend(): Promise<BackendStatus> {
    if (!isTauriEnv()) {
      this.emit({ running: true, url: 'http://localhost:8000' })
      return this.current
    }
    if (this.starting) return this.starting

    this.starting = (async () => {
      try {
        const msg = await safeInvoke<string>('start_backend')
        const url = await this.getBackendUrl()
        const pidMatch = msg?.match(/PID:\s*(\d+)/)
        const pid = pidMatch ? Number(pidMatch[1]) : undefined
        this.emit({ running: true, url, pid, startedAt: Date.now() })
        this.startPolling()
        return this.current
      } catch (err) {
        console.error('[desktop] 启动后端失败:', err)
        this.emit({ ...this.current, running: false })
        throw err
      } finally {
        this.starting = null
      }
    })()
    return this.starting
  }

  async stopBackend(): Promise<void> {
    if (!isTauriEnv()) return
    await safeInvoke<string>('stop_backend')
    this.stopPolling()
    this.emit({ running: false, url: this.current.url })
  }

  async queryStatus(): Promise<boolean> {
    if (!isTauriEnv()) return true
    const running = await safeInvoke<boolean>('backend_status')
    const next = { ...this.current, running: running ?? false }
    this.emit(next)
    return next.running
  }

  async getSystemInfo(): Promise<SystemInfo | null> {
    if (!isTauriEnv()) return null
    return safeInvoke<SystemInfo>('system_info')
  }

  private startPolling() {
    if (this.pollTimer != null || !isTauriEnv()) return
    this.pollTimer = window.setInterval(() => {
      this.queryStatus().catch(() => {})
    }, 10000)
  }

  private stopPolling() {
    if (this.pollTimer != null) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
  }
}

export const desktop = new DesktopRuntime()

export async function bootstrapDesktop(): Promise<string> {
  if (!isTauriEnv()) {
    return 'http://localhost:8000'
  }
  try {
    await desktop.startBackend()
    return desktop.current.url
  } catch (err) {
    console.warn('[desktop] 后端启动失败,前端仍将以默认地址启动:', err)
    return 'http://localhost:8000'
  }
}
