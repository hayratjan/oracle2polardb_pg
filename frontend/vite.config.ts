import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

const isTauri = process.env.TAURI_ENV === '1' || !!process.env.TAURI_PLATFORM

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: isTauri ? './' : '/',
  server: {
    port: isTauri ? 1420 : 5173,
    strictPort: isTauri,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: isTauri
      ? {
          output: {
            manualChunks: undefined,
            entryFileNames: 'assets/[name].js',
            chunkFileNames: 'assets/[name].js',
            assetFileNames: 'assets/[name].[ext]',
          },
        }
      : {},
    chunkSizeWarningLimit: 1500,
  },
  define: {
    __TAURI_ENV__: JSON.stringify(isTauri),
  },
})
