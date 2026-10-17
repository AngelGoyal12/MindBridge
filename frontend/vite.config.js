import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { fileURLToPath } from 'node:url'

function productionContentSecurityPolicy(apiBaseUrl) {
  const connectSources = ["'self'"]
  if (apiBaseUrl) {
    let apiUrl
    try {
      apiUrl = new URL(apiBaseUrl)
    } catch {
      throw new Error('VITE_API_BASE_URL must be a valid API origin.')
    }
    if (
      !['http:', 'https:'].includes(apiUrl.protocol) ||
      apiUrl.username ||
      apiUrl.password ||
      !['', '/'].includes(apiUrl.pathname) ||
      apiUrl.search ||
      apiUrl.hash ||
      (apiUrl.protocol !== 'https:' &&
        !['localhost', '127.0.0.1', '[::1]'].includes(apiUrl.hostname))
    ) {
      throw new Error(
        'VITE_API_BASE_URL must use HTTPS, except for a loopback development API.',
      )
    }
    connectSources.push(apiUrl.origin)
  }

  return [
    "default-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data: blob:",
    `connect-src ${connectSources.join(' ')}`,
  ].join('; ')
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const projectRoot = fileURLToPath(new URL('.', import.meta.url))
  const env = loadEnv(mode, projectRoot, 'VITE_')

  return {
    plugins: [
      react(),
      {
        name: 'mindbridge-production-csp',
        transformIndexHtml: {
          order: 'post',
          handler(html, context) {
            if (context.bundle) {
              const policy = productionContentSecurityPolicy(
                env.VITE_API_BASE_URL?.trim(),
              )
              return html.replace(
                /<head>/i,
                `<head>\n    <meta http-equiv="Content-Security-Policy" content="${policy}" />`,
              )
            }
            return html
          },
        },
      },
    ],
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
