const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
/**
 * The visitor chooses the data source before the dashboard starts.
 */
export const dataSource = {
  mode: null,
  setMode(mode) {
    if (mode !== 'demo' && mode !== 'api') throw new Error('Неизвестный источник данных')
    this.mode = mode
  },
  async load(signal) {
    if (this.mode === 'demo') {
      const [response, fleet] = await Promise.all([
        fetch(`${apiBase}/api/v1/replay`, { signal, cache: 'no-store' }),
        import('../data/demo_fleet.json'),
      ])
      if (!response.ok) throw new Error(`Исторический прогон: HTTP ${response.status}`)
      let replay = await response.json()
      if (replay.state === 'idle') {
        const started = await fetch(`${apiBase}/api/v1/replay/start`, { method: 'POST', signal })
        if (!started.ok) throw new Error(`Запуск исторического прогона: HTTP ${started.status}`)
        replay = await started.json()
      }
      if (replay.state === 'failed') throw new Error(`Исторический прогон: ${replay.error}`)
      return { ...replay, tracks: fleet.default.tracks }
    }
    if (this.mode !== 'api') throw new Error('Сначала выберите источник данных')
    const [response, fleetResponse, statusResponse] = await Promise.all([
      fetch(`${apiBase}/api/dashboard`, { signal, cache: 'no-store' }),
      fetch(`${apiBase}/api/v1/fleet`, { signal, cache: 'no-store' }),
      fetch(`${apiBase}/api/v1/ndtp/status`, { signal, cache: 'no-store' }),
    ])
    if (!response.ok || !fleetResponse.ok || !statusResponse.ok) throw new Error(`API: HTTP ${!response.ok ? response.status : !fleetResponse.ok ? fleetResponse.status : statusResponse.status}`)
    const [payload, fleet, ndtpStatus] = await Promise.all([response.json(), fleetResponse.json(), statusResponse.json()])
    if (!Array.isArray(payload.records)) throw new Error('API: нет массива records')
    if (!Array.isArray(fleet.vehicles)) throw new Error('API: нет массива vehicles')
    payload.vehicles = fleet.vehicles
    payload.fleetGeneratedAt = fleet.generatedAt
    payload.ndtpStatus = ndtpStatus
    return payload
  },
}
