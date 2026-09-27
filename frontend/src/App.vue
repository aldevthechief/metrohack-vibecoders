<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  Activity, AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, Bell,
  Check, ChevronLeft, ChevronRight, Clock3, Download, Gauge, Info, Moon,
  MoreHorizontal, Pause, Play, Radio, RotateCcw, Search,
  SlidersHorizontal, Sun, X, Zap,
} from 'lucide-vue-next'
import { dataSource } from './services/dataSource'
import { secondsOfDay, vehiclesAtTime } from './services/demoFleet'
import TransportMap from './components/TransportMap.vue'

const payload = ref({ records: [] })
const selectedMode = ref(null)
const connection = ref('connecting')
const connectionError = ref('')
const page = ref('overview')
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)')
let followSystemTheme = !localStorage.getItem('metro-theme')
const theme = ref(localStorage.getItem('metro-theme') || (systemTheme.matches ? 'dark' : 'light'))
const search = ref('')
const riskFilter = ref('all')
const selectedId = ref(null)
const showScenario = ref(false)
const scenarioSeconds = ref(60)
const playing = ref(false)
const playbackRate = ref(0.25)
const playbackRates = [0.25, 0.5, 1, 2, 4]
const transportMap = ref(null)
const toast = ref('')
const timelinePosition = ref(0)
const hoveredChartPoint = ref(null)
let initialSelectionMade = false
let replayTimer
let replayFrame
let pollingTimer
let toastTimer

const allRecords = computed(() => payload.value.records || [])
const timestamps = computed(() => payload.value.timelineTimestamps?.length
  ? payload.value.timelineTimestamps
  : [...new Set(allRecords.value.map((item) => item.timestamp))].sort())
const currentIndex = computed(() => Math.min(Math.max(0, Math.floor(timelinePosition.value + 1e-6)), Math.max(0, timestamps.value.length - 1)))
const currentTime = computed(() => timestamps.value[currentIndex.value] || '')
const playbackSeconds = computed(() => {
  const start = secondsOfDay(currentTime.value)
  const next = timestamps.value[currentIndex.value + 1]
  return start + (next ? (secondsOfDay(next) - start) * (timelinePosition.value - currentIndex.value) : 0)
})
const fleetVehicles = computed(() => selectedMode.value === 'demo'
  ? vehiclesAtTime(payload.value.tracks, playbackSeconds.value)
  : payload.value.vehicles || [])
const hasEmulator = computed(() => fleetVehicles.value.some((vehicle) => vehicle.source === 'emulator'))
const hasRealNdtp = computed(() => fleetVehicles.value.some((vehicle) => vehicle.source === 'ndtp'))
const timeLabel = (value) => value ? value.slice(11, 16) : '—'
const fullTimeLabel = (value) => value ? value.slice(11, 19) : '—'
const secondsClock = (value) => {
  const seconds = Math.floor(value)
  return [Math.floor(seconds / 3600), Math.floor(seconds % 3600 / 60), seconds % 60].map((part) => String(part).padStart(2, '0')).join(':')
}
const gpsTimeLabel = (vehicle) => {
  if (selectedMode.value !== 'demo') return fullTimeLabel(vehicle.telemetryTime)
  if (vehicle.gpsTimeSeconds == null) return '—'
  return secondsClock(vehicle.gpsTimeSeconds)
}
const gpsReceivedLabel = (vehicle) => selectedMode.value === 'demo'
  ? vehicle.gpsReceivedSeconds == null ? '—' : secondsClock(vehicle.gpsReceivedSeconds)
  : fullTimeLabel(vehicle.gpsReceivedAt)
const gpsCoordinateLabel = (vehicle) => {
  const [longitude, latitude] = vehicle.gpsPosition || vehicle.position || []
  return longitude == null || latitude == null ? 'Нет координат' : `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`
}
const dateLabel = (value) => value ? new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(value.replace(' ', 'T'))) : '—'
const signedMinutes = (seconds) => {
  const value = Math.round(Math.abs(seconds) / 60)
  if (Math.abs(seconds) < 30) return 'по графику'
  return `${seconds < 0 ? '−' : '+'}${value} мин`
}
const preciseDelay = (seconds) => Math.abs(seconds) < 0.5 ? '0 с' : `${seconds > 0 ? '+' : '−'}${Math.round(Math.abs(seconds))} с`
const deviationLabel = (record) => record.currentDeviationSource === 'gps-estimate' ? 'Отклонение, оценка по GPS' : record.currentDeviationSource === 'configured' ? 'Начальное отклонение' : 'Текущее отклонение'
const riskOf = (record) => ['high', 'medium', 'low'].includes(record.riskLevel) ? record.riskLevel : record.predictionSec > 120 ? 'high' : record.predictionSec >= 60 ? 'medium' : 'low'
const probabilityLabel = (value) => value == null ? '—' : `${Math.round(value * 100)}%`
const riskText = { high: 'Высокий', medium: 'Внимание', low: 'В норме' }
const telemetryAge = (record) => {
  if (selectedMode.value === 'demo') {
    const vehicle = fleetVehicles.value.find((item) => item.vehicleId === record.vehicleId)
    if (vehicle) return vehicle.telemetryAgeSec
  }
  if (!record.telemetryTime) return record.telemetryAgeSec
  const reference = dataSource.mode === 'api' ? payload.value.fleetGeneratedAt : currentTime.value
  if (!reference) return record.telemetryAgeSec
  return Math.max(0, Math.round((new Date(reference.replace(' ', 'T')) - new Date(record.telemetryTime.replace(' ', 'T'))) / 1000))
}
const isFresh = (record) => telemetryAge(record) != null && telemetryAge(record) <= 120
const duration = (seconds) => seconds == null ? 'нет данных' : seconds < 60 ? `${Math.round(seconds)} с` : `${Math.round(seconds / 60)} мин`
const vehicleWord = (count) => count % 10 === 1 && count % 100 !== 11 ? 'машина' : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 12 || count % 100 > 14) ? 'машины' : 'машин'
const pageVehicleCount = computed(() => page.value === 'fleet' ? activeRecords.value.length : page.value === 'analytics' ? fleetVehicles.value.length : mapRecords.value.length)

const activeRecords = computed(() => {
  const latest = new Map()
  const referenceTime = dataSource.mode === 'api' && currentIndex.value === timestamps.value.length - 1
    ? payload.value.fleetGeneratedAt || currentTime.value
    : currentTime.value
  for (const record of allRecords.value) {
    if (record.timestamp > referenceTime || record.targetTime <= referenceTime) continue
    const age = (new Date(referenceTime.replace(' ', 'T')) - new Date(record.timestamp.replace(' ', 'T'))) / 1000
    if (age > 900) continue
    if (!latest.has(record.vehicleId) || latest.get(record.vehicleId).timestamp < record.timestamp) latest.set(record.vehicleId, record)
  }
  return [...latest.values()].sort((a, b) => b.predictionSec - a.predictionSec)
})
const visibleRecords = computed(() => activeRecords.value.filter((record) => {
  const query = search.value.trim().toLowerCase()
  const matches = !query || [record.vehicleId, record.targetAddress, record.sampleId].some((value) => String(value).toLowerCase().includes(query))
  return matches && (riskFilter.value === 'all' || riskOf(record) === riskFilter.value)
}))
const recentRecords = computed(() => allRecords.value.filter((record) => {
  if (!currentTime.value || record.timestamp > currentTime.value) return false
  const age = (new Date(currentTime.value.replace(' ', 'T')) - new Date(record.timestamp.replace(' ', 'T'))) / 1000
  return age <= 3600 && age >= 0
}).slice(-16).reverse())
const selectedRecord = computed(() => {
  const prediction = activeRecords.value.find((record) => record.vehicleId === selectedId.value)
  if (prediction) return prediction
  if (selectedId.value && fleetVehicles.value.some((vehicle) => vehicle.vehicleId === selectedId.value)) return null
  return visibleRecords.value[0] || activeRecords.value[0] || null
})
const activePredictionFor = (vehicleId) => activeRecords.value.find((record) => record.vehicleId === vehicleId)
const highCount = computed(() => activeRecords.value.filter((record) => riskOf(record) === 'high').length)
const mediumCount = computed(() => activeRecords.value.filter((record) => riskOf(record) === 'medium').length)
const freshCount = computed(() => activeRecords.value.filter(isFresh).length)
const maxRiskRecord = computed(() => activeRecords.value.find((record) => riskOf(record) === 'high') || activeRecords.value[0] || null)
const scenarioResult = computed(() => selectedRecord.value ? Math.max(-600, selectedRecord.value.predictionSec - Number(scenarioSeconds.value)) : 0)
const recommendation = computed(() => {
  const record = selectedRecord.value
  if (!record) return ''
  if (!isFresh(record)) return 'Проверьте связь с ТС и время последнего пакета.'
  if (riskOf(record) === 'high') return 'Проверьте интервал и возможность регулирования движения на участке.'
  if (riskOf(record) === 'medium') return 'Наблюдайте скорость и время простоя на ближайшем участке.'
  return 'Дополнительных действий пока не требуется.'
})

const mapRecords = computed(() => {
  const predictions = new Map(activeRecords.value.map((record) => [record.vehicleId, record]))
  return fleetVehicles.value.filter((vehicle) => vehicle.position).map((vehicle) => {
    const prediction = predictions.get(vehicle.vehicleId)
    return {
      ...prediction,
      ...vehicle,
      sampleId: prediction?.sampleId || `fleet:${vehicle.vehicleId}`,
      vehicleId: vehicle.vehicleId,
      fleetStatus: vehicle.status,
      telemetrySource: vehicle.source,
      predictionStatus: vehicle.predictionStatus,
      riskLevel: prediction?.riskLevel || 'unknown',
    }
  }).filter((record) => {
    const query = search.value.trim().toLowerCase()
    return (!query || [record.vehicleId, record.targetAddress, record.sampleId].some((value) => String(value || '').toLowerCase().includes(query)))
      && (riskFilter.value === 'all' || (record.riskLevel !== 'unknown' && riskOf(record) === riskFilter.value))
  })
})
const selectedFleetVehicle = computed(() => selectedId.value && !selectedRecord.value ? mapRecords.value.find((item) => item.vehicleId === selectedId.value) || null : null)
const selectedVehicle = computed(() => fleetVehicles.value.find((vehicle) => vehicle.vehicleId === (selectedId.value || selectedRecord.value?.vehicleId)) || null)
const selectedTelemetry = computed(() => {
  const vehicle = selectedVehicle.value
  if (!vehicle) return null
  if (selectedMode.value !== 'demo') return vehicle
  const points = payload.value.tracks?.[vehicle.vehicleId] || []
  const now = playbackSeconds.value
  const packets15m = points.filter((point) => point[0] <= now && point[0] >= now - 900)
  const speeds5m = packets15m.filter((point) => point[0] >= now - 300).map((point) => point[3])
  return {
    ...vehicle,
    packetCount15m: packets15m.length,
    meanSpeed5mKmh: speeds5m.length ? speeds5m.reduce((sum, speed) => sum + speed, 0) / speeds5m.length : null,
    stoppedFraction5m: speeds5m.length ? speeds5m.filter((speed) => speed < 2).length / speeds5m.length : null,
  }
})
const fleetStats = computed(() => {
  const vehicles = fleetVehicles.value
  const moving = vehicles.filter((vehicle) => vehicle.speedKmh != null && vehicle.speedKmh >= 2).length
  const stopped = vehicles.filter((vehicle) => vehicle.speedKmh != null && vehicle.speedKmh < 2).length
  const speeds = vehicles.map((vehicle) => vehicle.speedKmh).filter((speed) => speed != null)
  return {
    total: vehicles.length,
    moving,
    stopped,
    stale: vehicles.filter((vehicle) => vehicle.status === 'stale').length,
    noSchedule: vehicles.filter((vehicle) => vehicle.predictionStatus === 'no-schedule').length,
    meanSpeed: speeds.length ? speeds.reduce((sum, speed) => sum + speed, 0) / speeds.length : null,
    packets15m: vehicles.reduce((sum, vehicle) => sum + (vehicle.packetCount15m || 0), 0),
  }
})
const predictionStatusText = {
  'no-forecast-sample': 'Для этого ТС в валидационной выборке нет прогноза на выбранный момент.',
  'no-schedule': 'Нет актуального плана остановок для этого ТС.',
  'no-deviation': 'План есть, но пока нет измеренного отклонения от графика.',
  'outside-window': 'План есть, но сейчас нет остановки в окне прогноза 10–15 минут.',
  pending: 'Данные для прогноза есть, ожидается обновление модели.',
  available: 'Прогноз доступен в карточке инцидента.',
}
const displayTime = computed(() => {
  if (dataSource.mode !== 'demo' || !currentTime.value) return payload.value.fleetGeneratedAt || currentTime.value
  const seconds = Math.floor(playbackSeconds.value)
  const pad = (value) => String(value).padStart(2, '0')
  return `${currentTime.value.slice(0, 11)}${pad(Math.floor(seconds / 3600))}:${pad(Math.floor(seconds % 3600 / 60))}:${pad(seconds % 60)}`
})

const chartBuckets = computed(() => timestamps.value.filter((time) => {
  const age = (new Date(currentTime.value.replace(' ', 'T')) - new Date(time.replace(' ', 'T'))) / 1000
  return age >= 0 && age <= 3600
}).map((time) => {
  const latest = new Map()
  for (const record of allRecords.value) {
    if (record.timestamp > time || record.targetTime <= time) continue
    if ((new Date(time.replace(' ', 'T')) - new Date(record.timestamp.replace(' ', 'T'))) / 1000 > 900) continue
    if (!latest.has(record.vehicleId) || latest.get(record.vehicleId).timestamp < record.timestamp) latest.set(record.vehicleId, record)
  }
  const records = [...latest.values()]
  return { time, totalDelaySec: records.reduce((sum, record) => sum + Math.max(0, record.predictionSec), 0), vehicles: records.length, high: records.filter((record) => riskOf(record) === 'high').length }
}).filter((bucket) => bucket.vehicles > 0))
const chartMaximum = computed(() => Math.max(120, ...chartBuckets.value.map((bucket) => bucket.totalDelaySec)))
const chartPoints = computed(() => chartBuckets.value.map((bucket, index) => ({
  ...bucket,
  x: 20 + index * (560 / Math.max(1, chartBuckets.value.length - 1)),
  y: 142 - bucket.totalDelaySec / chartMaximum.value * 127,
})))
const chartPath = computed(() => chartPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x},${point.y}`).join(' '))

function notify(message) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 3600)
}
function setPage(next) {
  page.value = next
  showScenario.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function setTheme(value) {
  followSystemTheme = false
  theme.value = value
  localStorage.setItem('metro-theme', value)
}
function syncSystemTheme(event) {
  if (followSystemTheme) theme.value = event.matches ? 'dark' : 'light'
}
function chooseMode(mode) {
  clearInterval(pollingTimer)
  playing.value = false
  playbackRate.value = mode === 'demo' ? 0.25 : 1
  payload.value = { records: [] }
  selectedId.value = null
  timelinePosition.value = 0
  initialSelectionMade = false
  page.value = 'overview'
  selectedMode.value = mode
  dataSource.setMode(mode)
  connection.value = mode === 'demo' ? 'demo' : 'connecting'
  loadData()
  pollingTimer = setInterval(loadData, 5000)
}
function changeMode() {
  clearInterval(pollingTimer)
  playing.value = false
  selectedMode.value = null
  dataSource.mode = null
}
function step(delta) { timelinePosition.value = Math.max(0, Math.min(timestamps.value.length - 1, currentIndex.value + delta)) }
function jumpToAlert() {
  if (maxRiskRecord.value) {
    selectedId.value = maxRiskRecord.value.vehicleId
    page.value = 'overview'
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } else notify('В этом срезе нет активных прогнозов')
}
function exportVisible() {
  const rows = [['sample_id', 'prediction'], ...visibleRecords.value.map((record) => [record.sampleId, record.predictionSec])]
  const csv = rows.map((row) => row.join(';')).join('\n') + '\n'
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8' }))
  link.download = `dashboard-snapshot-${currentTime.value.slice(11, 16).replace(':', '-')}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
  notify('Срез прогнозов скачан. Это не полный submission.csv')
}
async function loadData() {
  const requestedMode = dataSource.mode
  if (!requestedMode) return
  const previousLastIndex = timestamps.value.length - 1
  const wasFollowingLatest = currentIndex.value >= previousLastIndex
  const previousTime = currentTime.value
  try {
    const result = await dataSource.load(AbortSignal.timeout(4000))
    if (requestedMode !== dataSource.mode) return
    payload.value = result
    if (requestedMode === 'demo' && result.state === 'complete') clearInterval(pollingTimer)
    connection.value = dataSource.mode === 'demo' ? 'demo' : result.source === 'submission-replay' ? 'replay' : result.source === 'backend-live' ? 'api' : 'empty'
    connectionError.value = ''
    if (!initialSelectionMade && timestamps.value.length > (requestedMode === 'demo' ? 1 : 0)) {
      const preferred = timestamps.value.indexOf('2026-01-06 21:00:00')
      timelinePosition.value = dataSource.mode === 'demo' && preferred >= 0 ? preferred : timestamps.value.length - 1
      initialSelectionMade = true
      if (requestedMode === 'demo' && timestamps.value.length > 1) playing.value = true
    } else if (dataSource.mode === 'api') {
      const previousTimeIndex = timestamps.value.indexOf(previousTime)
      timelinePosition.value = wasFollowingLatest || previousTimeIndex < 0
        ? Math.max(0, timestamps.value.length - 1)
        : previousTimeIndex
    }
  } catch (error) {
    if (requestedMode !== dataSource.mode) return
    connection.value = 'offline'
    connectionError.value = error.message
  }
}

watch(theme, (value) => {
  document.documentElement.dataset.theme = value
}, { immediate: true })
watch([playing, playbackRate], ([value]) => {
  clearInterval(replayTimer)
  cancelAnimationFrame(replayFrame)
  if (!value) return
  if (dataSource.mode === 'demo') {
    let lastFrame = 0
    const animate = (now) => {
      if (!playing.value) return
      if (lastFrame && now - lastFrame >= 25) {
        timelinePosition.value = Math.min(timestamps.value.length - 1, timelinePosition.value + (now - lastFrame) * playbackRate.value / 1600)
        lastFrame = now
      } else if (!lastFrame) lastFrame = now
      if (timelinePosition.value >= timestamps.value.length - 1) { playing.value = false; return }
      replayFrame = requestAnimationFrame(animate)
    }
    replayFrame = requestAnimationFrame(animate)
  } else replayTimer = setInterval(() => {
    if (currentIndex.value >= timestamps.value.length - 1) { playing.value = false; return }
    step(1)
  }, 1600 / playbackRate.value)
})
onMounted(() => {
  systemTheme.addEventListener('change', syncSystemTheme)
})
onUnmounted(() => { clearInterval(replayTimer); cancelAnimationFrame(replayFrame); clearInterval(pollingTimer); clearTimeout(toastTimer); systemTheme.removeEventListener('change', syncSystemTheme) })
</script>

<template>
  <div class="app-shell">
    <section v-if="!selectedMode" class="mode-start" aria-labelledby="mode-start-title">
      <div class="mode-start-card">
        <span class="mode-start-kicker">Диспетчерская</span>
        <h1 id="mode-start-title">Выберите источник данных</h1>
        <div class="mode-start-actions">
          <button class="mode-start-option" @click="chooseMode('demo')"><span class="mode-start-icon"><Activity :size="23" /></span><strong>Тестовые данные</strong><small>Исторический поток через бэкенд и ML, карта и графики</small><ArrowRight :size="20" /></button>
          <button class="mode-start-option" @click="chooseMode('api')"><span class="mode-start-icon"><Radio :size="23" /></span><strong>Эмулятор NDTP</strong><small>Живые GPS-пакеты через бэкенд</small><ArrowRight :size="20" /></button>
        </div>
      </div>
    </section>
    <div v-else class="main-column">
      <header class="topbar">
        <div class="topbar-left"><span class="brand-stripe"></span><span class="topbar-project">Маршруты Москвы</span></div>
        <nav class="topnav" aria-label="Разделы"><button :class="{ active: page === 'overview' }" @click="setPage('overview')">Карта</button><button :class="{ active: page === 'fleet' }" @click="setPage('fleet')">Прогнозы</button><button :class="{ active: page === 'analytics' }" @click="setPage('analytics')">Динамика</button></nav>
        <div class="topbar-right">
          <button class="mode-switch" @click="changeMode">{{ selectedMode === 'demo' ? 'Тестовые данные' : 'NDTP' }}</button>
          <button class="top-icon theme-top" :aria-label="theme === 'light' ? 'Тёмная тема' : 'Светлая тема'" @click="setTheme(theme === 'light' ? 'dark' : 'light')"><Moon v-if="theme === 'light'" :size="19" /><Sun v-else :size="19" /></button>
        </div>
      </header>

      <main class="work-area">
        <div v-if="connection === 'offline'" class="connection-warning"><AlertCircle :size="18" /> Нет связи с API: {{ connectionError }}. Последний полученный срез сохранён на экране. <button @click="loadData">Повторить</button></div>
        <div v-if="selectedMode === 'demo' && payload.state === 'running'" class="mode-note"><Activity :size="17" /> Бэкенд обрабатывает историческую телеметрию и рассчитывает прогнозы моделью: {{ payload.completed || 0 }} / {{ payload.total || '…' }}.</div>
        <Transition name="page" mode="out-in"><div :key="page" class="page-content">
        <div class="page-heading">
          <div><div class="eyebrow">{{ dateLabel(displayTime) }} · {{ timeLabel(displayTime) }} МСК</div><h1>{{ page === 'overview' ? 'Обстановка на маршрутах' : page === 'fleet' ? 'Прогнозы транспорта' : 'Динамика прогнозов' }}</h1></div>
          <div class="heading-actions"><button v-if="page === 'fleet'" class="outline-button" @click="exportVisible"><Download :size="16" /> Скачать таблицу</button><span class="heading-count">{{ pageVehicleCount }} {{ vehicleWord(pageVehicleCount) }} {{ page === 'overview' ? 'на карте' : 'в таблице' }}</span></div>
        </div>

        <template v-if="page === 'overview'">
          <section v-if="selectedRecord" class="priority-hero" :class="riskOf(selectedRecord)" aria-label="Главный прогноз">
            <div class="priority-hero-main"><span class="priority-eyebrow">{{ riskOf(selectedRecord) === 'high' ? 'Требует внимания' : riskOf(selectedRecord) === 'medium' ? 'Под наблюдением' : 'По графику' }} · ТС {{ selectedRecord.vehicleId }}</span><h2>{{ riskOf(selectedRecord) === 'high' ? 'Ожидается опоздание' : riskOf(selectedRecord) === 'medium' ? 'Возможное отклонение' : 'Движение в норме' }}</h2><p>Целевая остановка через <strong>{{ Math.round(selectedRecord.horizonSec / 60) }} мин</strong> от момента прогноза</p></div>
            <div class="priority-hero-side"><strong>{{ signedMinutes(selectedRecord.predictionSec) }}</strong><span>{{ selectedRecord.targetAddress }}</span></div>
          </section>
          <div class="content-grid">
            <section class="panel map-panel">
              <div class="panel-heading"><div><h2>Карта Москвы</h2><small v-if="fleetVehicles.length > mapRecords.length">{{ fleetVehicles.length - mapRecords.length }} ТС без валидного GPS</small></div><div class="map-heading-right"><label v-if="connection === 'demo' || connection === 'replay'" class="map-speed-control"><span>Скорость</span><select v-model.number="playbackRate" aria-label="Скорость воспроизведения"><option v-for="rate in playbackRates" :key="rate" :value="rate">×{{ String(rate).replace('.', ',') }}</option></select></label><span class="map-live" :class="{ demo: connection === 'demo' }"><span></span>{{ timeLabel(displayTime) }} МСК</span><button class="icon-button" title="Показать весь транспорт" aria-label="Показать весь транспорт" @click="transportMap?.resetView()"><RotateCcw :size="16" /></button></div></div>
              <TransportMap ref="transportMap" :records="mapRecords" :selected-id="selectedId" @select="selectedId = $event" />
              <div class="vehicle-telemetry" aria-label="Телеметрия выбранного ТС">
                <div class="vehicle-telemetry-head"><div><span class="panel-kicker">ТЕЛЕМЕТРИЯ ТС</span><h3>{{ selectedTelemetry ? `ТС ${selectedTelemetry.vehicleId}` : 'Выберите ТС на карте' }}</h3></div><span v-if="selectedTelemetry" class="telemetry-source">{{ selectedMode === 'demo' ? 'Исторический GPS' : selectedTelemetry.source === 'emulator' ? 'Эмулятор NDTP' : 'NDTP' }}</span></div>
                <div v-if="selectedTelemetry" class="vehicle-telemetry-grid">
                  <div><span>Скорость сейчас</span><strong>{{ selectedTelemetry.speedKmh == null ? '—' : `${Math.round(selectedTelemetry.speedKmh)} км/ч` }}</strong></div>
                  <div><span>Средняя за 5 мин</span><strong>{{ selectedTelemetry.meanSpeed5mKmh == null ? '—' : `${Math.round(selectedTelemetry.meanSpeed5mKmh)} км/ч` }}</strong></div>
                  <div><span>Простой за 5 мин</span><strong>{{ selectedTelemetry.stoppedFraction5m == null ? '—' : `${Math.round(selectedTelemetry.stoppedFraction5m * 100)}%` }}</strong></div>
                  <div><span>Пакеты за 15 мин</span><strong>{{ selectedTelemetry.packetCount15m ?? '—' }}</strong></div>
                  <div><span>Курс</span><strong>{{ selectedTelemetry.headingDeg == null ? '—' : `${Math.round(selectedTelemetry.headingDeg)}°` }}</strong></div>
                  <div><span>Последний GPS</span><strong>{{ duration(selectedTelemetry.telemetryAgeSec) }} назад</strong></div>
                </div>
                <p v-if="selectedMode === 'api'" class="vehicle-telemetry-note">Статус дверей недоступен: сейчас бэкенд разбирает навигационную ячейку NDTP.</p>
              </div>
            </section>

            <section class="panel incident-panel">
              <div class="panel-heading"><div><h2>Рейс под контролем</h2></div><button class="icon-button" title="Все прогнозы" aria-label="Все прогнозы" @click="setPage('fleet')"><MoreHorizontal :size="20" /></button></div>
              <template v-if="selectedRecord">
                <div class="incident-vehicle"><div class="vehicle-symbol"><Activity :size="22" /></div><div><h3>ТС {{ selectedRecord.vehicleId }}</h3><span class="vehicle-destination">{{ selectedRecord.targetAddress }}</span></div><span class="risk-pill" :class="riskOf(selectedRecord)"><i></i>{{ riskText[riskOf(selectedRecord)] }}</span></div>
                <div class="incident-details"><div><span>План прибытия</span><strong>{{ timeLabel(selectedRecord.targetTime) }}</strong></div><div><span>Прогноз прибытия</span><strong>{{ timeLabel(selectedRecord.estimatedArrival) }}</strong></div><div><span>Прогноз отклонения</span><strong>{{ preciseDelay(selectedRecord.predictionSec) }}</strong></div><div><span>Вероятность опоздания &gt; 2 мин</span><strong>{{ probabilityLabel(selectedRecord.delayProbability) }}</strong></div><div><span>{{ deviationLabel(selectedRecord) }}</span><strong>{{ preciseDelay(selectedRecord.currentDeviationSec) }}</strong></div><div><span>Последний GPS-пакет</span><strong :class="{ 'red-text': !isFresh(selectedRecord) }">{{ duration(telemetryAge(selectedRecord)) }} назад</strong></div></div>
                <div class="incident-context"><span>{{ selectedRecord.segmentLabel }}</span><span>Наблюдение: {{ selectedRecord.signal }}</span></div>
                <div v-if="selectedRecord.reasonFactors?.length" class="incident-factors"><strong>Что повлияло на прогноз</strong><span>Вклад признаков модели</span><ul><li v-for="factor in selectedRecord.reasonFactors" :key="factor.feature"><span>{{ factor.label }}{{ factor.value == null ? ' · нет данных' : '' }}</span><b>{{ preciseDelay(factor.shapValueSec) }}</b></li></ul></div>
                <div class="recommendation"><Zap :size="18" /><div><strong>Что проверить</strong><span>{{ recommendation }}</span></div></div>
                <div class="incident-foot"><button @click="showScenario = true">Оценить сценарий <ArrowRight :size="15" /></button></div>
              </template><div v-else-if="selectedFleetVehicle" class="empty-state"><Activity :size="24" /><strong>ТС {{ selectedFleetVehicle.vehicleId }}{{ selectedFleetVehicle.telemetrySource === 'emulator' ? ' · эмулятор' : '' }}</strong><span>Последний GPS-пакет: {{ duration(selectedFleetVehicle.telemetryAgeSec) }} назад · скорость {{ selectedFleetVehicle.speedKmh ?? '—' }} км/ч.</span><span>GPS: {{ selectedFleetVehicle.position?.[1]?.toFixed(6) }}, {{ selectedFleetVehicle.position?.[0]?.toFixed(6) }}</span><span>{{ predictionStatusText[selectedFleetVehicle.predictionStatus] || 'Прогноз пока недоступен.' }}</span></div><div v-else class="empty-state"><Check :size="24" /><strong>{{ fleetVehicles.length ? 'Есть телеметрия, нет прогнозов' : 'Нет активных прогнозов' }}</strong><span>{{ fleetVehicles.length ? 'Для прогноза нужен актуальный план остановок и измеренное отклонение от графика. Выберите ТС на карте, чтобы увидеть подробности.' : 'Транспорт появится на карте после получения валидных GPS-пакетов.' }}</span></div>
            </section>
          </div>

          <section class="panel fleet-panel compact-panel"><div class="section-head"><div><h2>Ближайшие прогнозы <span>{{ activeRecords.length }}</span></h2></div><button class="text-button" @click="setPage('fleet')">Все прогнозы <ArrowRight :size="16" /></button></div><div class="fleet-table-wrap"><table class="fleet-table"><thead><tr><th>ТРАНСПОРТ</th><th>ЦЕЛЕВАЯ ОСТАНОВКА</th><th>ПРИБЫТИЕ</th><th>ПРОГНОЗ</th><th>РИСК</th><th></th></tr></thead><tbody><tr v-for="record in activeRecords" :key="record.sampleId" :class="{ selected: selectedRecord?.sampleId === record.sampleId }" @click="selectedId = record.vehicleId"><td><span class="table-vehicle-icon"><Activity :size="16" /></span><strong>ТС {{ record.vehicleId }}</strong></td><td class="address-cell">{{ record.targetAddress }}</td><td>{{ timeLabel(record.targetTime) }}</td><td><strong :class="`${riskOf(record)}-text`">{{ signedMinutes(record.predictionSec) }}</strong><small>{{ preciseDelay(record.predictionSec) }}</small></td><td><span class="risk-pill" :class="riskOf(record)"><i></i>{{ riskText[riskOf(record)] }}</span></td><td><ChevronRight :size="17" /></td></tr><tr v-if="!activeRecords.length"><td colspan="6" class="no-rows">Нет прогнозов в выбранном моменте. Используйте шкалу воспроизведения.</td></tr></tbody></table></div></section>
        </template>

        <template v-else-if="page === 'fleet'">
          <div class="fleet-toolbar"><div class="search-box"><Search :size="18" /><input v-model="search" placeholder="Найти ТС, остановку или sample_id" aria-label="Поиск прогнозов" /><button v-if="search" aria-label="Очистить поиск" @click="search = ''"><X :size="16" /></button></div><div class="filter-pills" aria-label="Фильтр риска"><button v-for="option in [{ id:'all',label:'Все' },{ id:'high',label:'Высокий' },{ id:'medium',label:'Внимание' },{ id:'low',label:'В норме' }]" :key="option.id" :class="{ active: riskFilter === option.id }" @click="riskFilter = option.id">{{ option.label }}</button></div></div>
          <section class="panel full-fleet-panel"><div class="section-head"><div><div class="panel-kicker">ТЕКУЩИЕ ПРОГНОЗЫ</div><h2>На контроле сейчас <span>{{ visibleRecords.length }}</span></h2></div><span class="caption">Каждый прогноз создан за 10–15 мин до плановой остановки</span></div><div class="fleet-table-wrap"><table class="fleet-table"><thead><tr><th>ТРАНСПОРТ</th><th>ЦЕЛЕВАЯ ОСТАНОВКА</th><th>ПЛАН</th><th>ПРОГНОЗ</th><th>ТЕЛЕМЕТРИЯ</th><th>РИСК</th></tr></thead><tbody><tr v-for="record in visibleRecords" :key="record.sampleId" @click="selectedId = record.vehicleId; page = 'overview'"><td><strong>ТС {{ record.vehicleId }}</strong><small>{{ record.sampleId }}</small></td><td class="address-cell">{{ record.targetAddress }}</td><td>{{ timeLabel(record.targetTime) }}</td><td><strong :class="`${riskOf(record)}-text`">{{ preciseDelay(record.predictionSec) }}</strong></td><td>{{ duration(record.telemetryAgeSec) }} назад</td><td><span class="risk-pill" :class="riskOf(record)"><i></i>{{ riskText[riskOf(record)] }}</span></td></tr><tr v-if="!visibleRecords.length"><td colspan="6" class="no-rows">Нет записей по выбранному фильтру.</td></tr></tbody></table></div></section>
          <section class="panel history-panel"><div class="section-head"><div><div class="panel-kicker">ИСТОРИЯ ВОСПРОИЗВЕДЕНИЯ</div><h2>Последний час <span>{{ recentRecords.length }}</span></h2></div></div><div class="history-list"><div v-for="record in recentRecords" :key="record.sampleId" class="history-row"><span class="history-time">{{ timeLabel(record.timestamp) }}</span><span class="history-line" :class="riskOf(record)"></span><strong>ТС {{ record.vehicleId }}</strong><span class="history-address">{{ record.targetAddress }}</span><span :class="`${riskOf(record)}-text`">{{ preciseDelay(record.predictionSec) }}</span><span class="risk-pill" :class="riskOf(record)"><i></i>{{ riskText[riskOf(record)] }}</span></div><div v-if="!recentRecords.length" class="no-rows">Нет точек за последний час.</div></div></section>
        </template>

        <template v-else>
          <div class="analytics-grid">
            <section class="panel telemetry-overview">
              <div class="section-head"><div><div class="panel-kicker">{{ selectedMode === 'demo' ? 'ИСТОРИЧЕСКИЙ ПОТОК' : 'ЖИВОЙ NDTP-ПОТОК' }}</div><h2>Состояние всего транспорта</h2></div><span class="caption">{{ selectedMode === 'demo' ? `Прогнозов через ML: ${payload.completed || 0} / ${payload.total || '…'}` : `Принято NDTP-пакетов: ${payload.ndtpStatus?.received_packets ?? '—'}` }}</span></div>
              <div class="telemetry-overview-grid">
                <div><span>ТС с GPS</span><strong>{{ fleetStats.total }}</strong></div>
                <div><span>В движении</span><strong>{{ fleetStats.moving }}</strong></div>
                <div><span>Стоят</span><strong>{{ fleetStats.stopped }}</strong></div>
                <div><span>Средняя скорость</span><strong>{{ fleetStats.meanSpeed == null ? '—' : `${Math.round(fleetStats.meanSpeed)} км/ч` }}</strong></div>
                <div><span>Активные прогнозы</span><strong>{{ activeRecords.length }}</strong></div>
                <div><span>Высокий риск</span><strong class="red-text">{{ highCount }}</strong></div>
                <div><span>Нет плана</span><strong>{{ fleetStats.noSchedule }}</strong></div>
                <div><span>{{ selectedMode === 'demo' ? 'Устаревший GPS' : 'Пакеты за 15 мин' }}</span><strong>{{ selectedMode === 'demo' ? fleetStats.stale : fleetStats.packets15m }}</strong></div>
              </div>
            </section>
            <section class="panel analytics-chart"><div class="section-head"><div><div class="panel-kicker">ПОСЛЕДНИЙ ЧАС</div><h2>Сумма прогнозируемых опозданий</h2></div></div><div class="chart-area"><div class="chart-y"><span>{{ Math.round(chartMaximum / 60) }} мин</span><span>{{ Math.round(chartMaximum * 2 / 180) }} мин</span><span>{{ Math.round(chartMaximum / 180) }} мин</span><span>0</span></div><svg viewBox="0 0 600 180" preserveAspectRatio="xMidYMid meet" aria-label="Сумма прогнозируемых опозданий активных ТС"><line x1="20" y1="15" x2="580" y2="15"/><line x1="20" y1="55" x2="580" y2="55"/><line x1="20" y1="95" x2="580" y2="95"/><line x1="20" y1="142" x2="580" y2="142"/><path v-if="chartPath" :d="chartPath" class="chart-path"/><g v-for="point in chartPoints" :key="point.time" class="chart-point" @mouseenter="hoveredChartPoint = point.time" @mouseleave="hoveredChartPoint = null" @focusin="hoveredChartPoint = point.time" @focusout="hoveredChartPoint = null"><circle :cx="point.x" :cy="point.y" r="12" class="chart-point-hit" tabindex="0" :aria-label="`${timeLabel(point.time)}, суммарное опоздание ${Math.round(point.totalDelaySec / 60)} мин, ${point.vehicles} ТС`"/><circle :cx="point.x" :cy="point.y" :r="hoveredChartPoint === point.time ? 7 : 5" :class="point.high ? 'high' : 'low'" class="chart-point-dot"/><g v-if="hoveredChartPoint === point.time" :transform="`translate(${point.x > 420 ? point.x - 168 : point.x + 12}, ${point.y < 42 ? point.y + 10 : point.y - 40})`" class="chart-risk-tag" :class="point.high ? 'high' : 'low'"><rect width="156" height="30" rx="8"/><text x="10" y="19">{{ Math.round(point.totalDelaySec / 60) }} мин · {{ point.vehicles }} ТС · риск {{ point.high }}</text></g></g></svg></div><div class="chart-caption"><span>{{ timeLabel(chartBuckets[0]?.time) }}</span><span>{{ timeLabel(currentTime) }}</span></div><p v-if="!chartPoints.length" class="chart-empty">Пока нет активных прогнозов для графика. Телеметрия ТС показана ниже.</p></section>
            <section class="panel telemetry-fleet-panel">
              <div class="section-head"><div><div class="panel-kicker">ВСЕ ВИДИМЫЕ ТС</div><h2>Сводка по транспорту</h2></div><span class="caption">{{ selectedMode === 'demo' ? 'Исторический GPS' : `Ошибок NDTP: ${payload.ndtpStatus?.rejected_frames ?? 0}` }}</span></div>
              <div class="fleet-table-wrap"><table class="fleet-table"><thead><tr><th>ТС</th><th>ИСТОЧНИК</th><th>СКОРОСТЬ</th><th>GPS: ШИРОТА, ДОЛГОТА / ВРЕМЯ</th><th>ПРОГНОЗ</th></tr></thead><tbody>
                <tr v-for="vehicle in fleetVehicles" :key="vehicle.vehicleId" @click="selectedId = vehicle.vehicleId; page = 'overview'">
                  <td><strong>ТС {{ vehicle.vehicleId }}</strong></td>
                  <td>{{ selectedMode === 'demo' ? 'Исторический' : vehicle.source === 'emulator' ? 'Эмулятор' : 'NDTP' }}</td>
                  <td>{{ vehicle.speedKmh == null ? '—' : `${Math.round(vehicle.speedKmh)} км/ч` }}</td>
                  <td class="gps-coordinate-cell"><strong>{{ gpsCoordinateLabel(vehicle) }}</strong><small>GPS {{ gpsTimeLabel(vehicle) }} · получен {{ gpsReceivedLabel(vehicle) }} МСК</small></td>
                  <td class="numeric-forecast-cell"><template v-if="activePredictionFor(vehicle.vehicleId)"><strong :class="`${riskOf(activePredictionFor(vehicle.vehicleId))}-text`">{{ preciseDelay(activePredictionFor(vehicle.vehicleId).predictionSec) }}</strong><small>{{ probabilityLabel(activePredictionFor(vehicle.vehicleId).delayProbability) }} · задержка &gt; 2 мин</small></template><span v-else>—</span></td>
                </tr>
                <tr v-if="!fleetVehicles.length"><td colspan="5" class="no-rows">Пока нет телеметрии для выбранного момента.</td></tr>
              </tbody></table></div>
            </section>
          </div>
        </template>
        </div></Transition>
      </main>

      <footer class="replay-bar"><div class="replay-label"><span class="replay-icon"><Clock3 :size="18" /></span><div><strong>{{ connection === 'replay' || connection === 'demo' ? 'Историческое воспроизведение' : 'Текущие прогнозы' }}</strong><small>{{ dateLabel(displayTime) }} · МСК</small></div></div><div class="replay-controls"><button aria-label="Предыдущая точка" title="Предыдущая точка" @click="step(-1)"><ChevronLeft :size="19" /></button><button class="play-button" :aria-label="playing ? 'Пауза' : 'Воспроизвести'" @click="playing = !playing"><Pause v-if="playing" :size="17" fill="currentColor" /><Play v-else :size="17" fill="currentColor" /></button><button aria-label="Следующая точка" title="Следующая точка" @click="step(1)"><ChevronRight :size="19" /></button></div><div class="timeline"><span>{{ timestamps[0] ? timeLabel(timestamps[0]) : '—' }}</span><input type="range" :min="0" :max="Math.max(0, timestamps.length - 1)" :step="selectedMode === 'demo' ? 0.01 : 1" :value="timelinePosition" @input="timelinePosition = Number($event.target.value)" aria-label="Время воспроизведения" /><span>{{ timestamps.at(-1) ? timeLabel(timestamps.at(-1)) : '—' }}</span></div><div class="current-clock">{{ timeLabel(displayTime) }} <span>МСК</span></div></footer>
    </div>

    <div v-if="showScenario" class="modal-backdrop" @click.self="showScenario = false"><section class="scenario-modal" role="dialog" aria-modal="true" aria-labelledby="scenario-title"><div class="modal-head"><span class="modal-icon"><SlidersHorizontal :size="21" /></span><button aria-label="Закрыть" @click="showScenario = false"><X :size="21" /></button></div><div class="panel-kicker">СЦЕНАРИЙ ДИСПЕТЧЕРА</div><h2 id="scenario-title">Что, если сократить простой?</h2><p>Оцените возможный эффект для выбранного ТС.</p><div v-if="selectedRecord" class="scenario-target"><span>ТС {{ selectedRecord.vehicleId }} · {{ selectedRecord.targetAddress }}</span><strong>{{ preciseDelay(selectedRecord.predictionSec) }}</strong></div><label class="scenario-label" for="scenario-range">Сократить задержку на остановках <strong>{{ scenarioSeconds }} с</strong></label><input id="scenario-range" v-model.number="scenarioSeconds" type="range" min="0" max="300" step="15" /><div class="scenario-scale"><span>0 с</span><span>5 мин</span></div><div class="scenario-result"><div><span>Исходный прогноз</span><strong>{{ selectedRecord ? preciseDelay(selectedRecord.predictionSec) : '—' }}</strong></div><ArrowRight :size="22" /><div><span>Сценарное отклонение</span><strong>{{ selectedRecord ? preciseDelay(scenarioResult) : '—' }}</strong></div></div><button class="primary-button modal-done" @click="showScenario = false">Готово</button></section></div>
    <div v-if="toast" class="toast" role="status"><Check :size="17" /> {{ toast }}</div>
  </div>
</template>


