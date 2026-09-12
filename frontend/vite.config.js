import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import process from 'node:process'

const tauriDevHost = process.env.TAURI_DEV_HOST

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    // WebKit resuelve localhost a IPv4 en macOS; Vite, en cambio, puede
    // escuchar solo en ::1. Fijamos loopback IPv4 para que la ventana Tauri
    // siempre pueda cargar el frontend durante el desarrollo.
    host: tauriDevHost || '127.0.0.1',
    port: 5173,
    strictPort: true,
    watch: {
      ignored: ['**/src-tauri/**'],
    },
  },
})
