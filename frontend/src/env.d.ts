/// <reference types="vite/client" />

declare const __TAURI_ENV__: boolean | undefined

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
