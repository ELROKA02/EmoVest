import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import DesktopBootstrapError from './components/DesktopBootstrapError.jsx'
import { initializeApiRuntime } from './config.js'
import { invoke } from '@tauri-apps/api/core'

const root = createRoot(document.getElementById('root'))

const renderApp = () => {
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

const bootstrap = async () => {
  try {
    await initializeApiRuntime()
    renderApp()
  } catch (error) {
    root.render(
      <StrictMode>
        <DesktopBootstrapError
          error={error}
          onRetry={async () => {
            try {
              await invoke('restart_desktop_backend')
            } finally {
              window.location.reload()
            }
          }}
        />
      </StrictMode>,
    )
  }
}

void bootstrap()
