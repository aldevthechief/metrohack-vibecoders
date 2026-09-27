import demo from '../data/demo.json'

const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const demoMode = import.meta.env.VITE_DATA_MODE === 'demo'

/**
 * API is the default source. Demo data is available with VITE_DATA_MODE=demo.
 */
export const dataSource = {
  mode: demoMode ? 'demo' : 'api',
  async load(signal) {
    if (demoMode) return demo
    const response = await fetch(`${apiBase}/api/dashboard`, { signal, cache: 'no-store' })
    if (!response.ok) throw new Error(`API: HTTP ${response.status}`)
    const payload = await response.json()
    if (!Array.isArray(payload.records)) throw new Error('API: нет массива records')
    return payload
  },
}
