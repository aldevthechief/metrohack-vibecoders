<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  Activity, AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, Bell,
  Check, ChevronLeft, ChevronRight, Clock3, Download, Gauge, Info, Moon,
  MoreHorizontal, Pause, Play, Radio, RotateCcw, Search,
  SlidersHorizontal, Sun, X, Zap,
} from 'lucide-vue-next'
import { dataSource } from './services/dataSource'
import TransportMap from './components/TransportMap.vue'

const payload = ref({ records: [] })
const connection = ref(dataSource.mode === 'demo' ? 'demo' : 'connecting')
const connectionError = ref('')
const page = ref('overview')
const theme = ref(localStorage.getItem('metro-theme') || 'light')
const search = ref('')
const riskFilter = ref('all')
const selectedId = ref(null)
const showScenario = ref(false)
const scenarioSeconds = ref(60)
const playing = ref(false)
const transportMap = ref(null)
const toast = ref('')
const currentIndex = ref(0)
let initialSelectionMade = false
let replayTimer
let pollingTimer
let toastTimer

const allRecords = computed(() => payload.value.records || [])
const timestamps = computed(() => [...new Set(allRecords.value.map((item) => item.timestamp))].sort())
const currentTime = computed(() => timestamps.value[currentIndex.value] || '')
const timeLabel = (value) => value ? value.slice(11, 16) : '—'
const dateLabel = (value) => value ? new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(value.replace(' ', 'T'))) : '—'
const signedMinutes = (seconds) => {
  const value = Math.round(Math.abs(seconds) / 60)
  if (Math.abs(seconds) < 30) return 'по графику'
  return `${seconds < 0 ? '−' : '+'}${value} мин`
}
const preciseDelay = (seconds) => Math.abs(seconds) < 0.5 ? '0 с' : `${seconds > 0 ? '+' : '−'}${Math.round(Math.abs(seconds))} с`
const deviationLabel = (record) => record.currentDeviationSource === 'gps-estimate' ? 'Отклонение · оценка по GPS' : record.currentDeviationSource === 'configured' ? 'Начальное отклонение · задано' : 'Текущее отклонение'
const riskOf = (record) => ['high', 'medium', 'low'].includes(record.riskLevel) ? record.riskLevel : record.predictionSec > 120 ? 'high' : record.predictionSec >= 60 ? 'medium' : 'low'
const probabilityLabel = (value) => value == null ? '—' : `${Math.round(value * 100)}%`
const riskText = { high: 'Высокий', medium: 'Внимание', low: 'В норме' }
const isFresh = (record) => record.telemetryAgeSec !== null && record.telemetryAgeSec <= 120
const duration = (seconds) => seconds == null ? 'нет данных' : seconds < 60 ? `${seconds} с` : `${Math.round(seconds / 60)} мин`
const vehicleWord = (count) => count % 10 === 1 && count % 100 !== 11 ? 'машина' : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 12 || count % 100 > 14) ? 'машины' : 'машин'

const activeRecords = computed(() => {
  const latest = new Map()
  for (const record of allRecords.value) {
    if (record.timestamp > currentTime.value || record.targetTime <= currentTime.value) continue
    const age = (new Date(currentTime.value.replace(' ', 'T')) - new Date(record.timestamp.replace(' ', 'T'))) / 1000
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
const selectedRecord = computed(() => activeRecords.value.find((record) => record.sampleId === selectedId.value) || visibleRecords.value[0] || activeRecords.value[0] || null)
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

const mapRecords = computed(() => visibleRecords.value.filter((item) => item.position))

const chartPoints = computed(() => {
  const records = recentRecords.value.slice().reverse()
  if (!records.length) return []
  return records.map((record, index) => ({
    x: 20 + index * (560 / Math.max(1, records.length - 1)),
    y: 142 - Math.min(140, Math.max(-30, record.predictionSec) / 420 * 130),
    record,
  }))
})
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
function step(delta) { currentIndex.value = Math.max(0, Math.min(timestamps.value.length - 1, currentIndex.value + delta)) }
function jumpToAlert() {
  if (maxRiskRecord.value) {
    selectedId.value = maxRiskRecord.value.sampleId
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
  const previousLastIndex = timestamps.value.length - 1
  const wasFollowingLatest = currentIndex.value >= previousLastIndex
  const previousTime = currentTime.value
  try {
    const result = await dataSource.load(AbortSignal.timeout(4000))
    payload.value = result
    connection.value = dataSource.mode === 'demo' ? 'demo' : result.source === 'submission-replay' ? 'replay' : result.source === 'backend-live' ? 'api' : 'empty'
    connectionError.value = ''
    if (!initialSelectionMade && timestamps.value.length) {
      const preferred = timestamps.value.indexOf('2026-01-06 21:00:00')
      currentIndex.value = dataSource.mode === 'demo' && preferred >= 0 ? preferred : timestamps.value.length - 1
      initialSelectionMade = true
    } else if (dataSource.mode === 'api') {
      const previousTimeIndex = timestamps.value.indexOf(previousTime)
      currentIndex.value = wasFollowingLatest || previousTimeIndex < 0
        ? Math.max(0, timestamps.value.length - 1)
        : previousTimeIndex
    }
  } catch (error) {
    connection.value = 'offline'
    connectionError.value = error.message
  }
}

watch(theme, (value) => {
  document.documentElement.dataset.theme = value
  localStorage.setItem('metro-theme', value)
}, { immediate: true })
watch(currentTime, () => { selectedId.value = null })
watch(playing, (value) => {
  clearInterval(replayTimer)
  if (value) replayTimer = setInterval(() => {
    if (currentIndex.value >= timestamps.value.length - 1) { playing.value = false; return }
    step(1)
  }, 1600)
})
onMounted(() => {
  loadData()
  if (dataSource.mode === 'api') pollingTimer = setInterval(loadData, 5000)
})
onUnmounted(() => { clearInterval(replayTimer); clearInterval(pollingTimer); clearTimeout(toastTimer) })
</script>

<template>
  <div class="app-shell">
    <div class="main-column">
      <header class="topbar">
        <div class="topbar-left"><span class="brand-stripe"></span><span class="topbar-project">Маршруты</span><span class="topbar-divider"></span><span class="topbar-section">Диспетчерская</span></div>
        <nav class="topnav" aria-label="Разделы"><button :class="{ active: page === 'overview' }" @click="setPage('overview')">Карта</button><button :class="{ active: page === 'fleet' }" @click="setPage('fleet')">Прогнозы</button><button :class="{ active: page === 'analytics' }" @click="setPage('analytics')">Динамика</button></nav>
        <div class="topbar-right">
          <span class="source-badge" :class="connection"><span class="status-dot"></span>{{ connection === 'demo' ? 'Локальное демо' : connection === 'replay' ? 'API · история' : connection === 'api' ? 'API · прогнозы' : connection === 'empty' ? 'API · нет данных' : connection === 'connecting' ? 'Подключение…' : 'API недоступен' }}</span>
          <button class="top-icon" aria-label="Уведомления" title="Уведомления" @click="jumpToAlert"><Bell :size="19" /><span v-if="highCount" class="notification-dot"></span></button>
          <button class="top-icon theme-top" :aria-label="theme === 'light' ? 'Тёмная тема' : 'Светлая тема'" @click="theme = theme === 'light' ? 'dark' : 'light'"><Moon v-if="theme === 'light'" :size="19" /><Sun v-else :size="19" /></button>
        </div>
      </header>

      <main class="work-area">
        <div v-if="connection === 'offline'" class="connection-warning"><AlertCircle :size="18" /> Нет связи с API: {{ connectionError }}. Последний полученный срез сохранён на экране. <button @click="loadData">Повторить</button></div>
        <Transition name="page" mode="out-in"><div :key="page" class="page-content">
        <div class="page-heading">
          <div><div class="eyebrow">{{ dateLabel(currentTime) }} · {{ timeLabel(currentTime) }} МСК</div><h1>{{ page === 'overview' ? 'Обстановка на маршрутах' : page === 'fleet' ? 'Прогнозы транспорта' : 'Динамика прогнозов' }}</h1></div>
          <div class="heading-actions"><button v-if="page === 'fleet'" class="outline-button" @click="exportVisible"><Download :size="16" /> Скачать срез</button><span class="heading-count">{{ activeRecords.length }} {{ vehicleWord(activeRecords.length) }} {{ page === 'overview' ? 'на карте' : 'в срезе' }}</span></div>
        </div>

        <template v-if="page === 'overview'">
          <section v-if="selectedRecord" class="priority-hero" :class="riskOf(selectedRecord)" aria-label="Главный прогноз">
            <div class="priority-hero-main"><span class="priority-eyebrow">{{ riskOf(selectedRecord) === 'high' ? 'Требует внимания' : riskOf(selectedRecord) === 'medium' ? 'Под наблюдением' : 'По графику' }} · ТС {{ selectedRecord.vehicleId }}</span><h2>{{ riskOf(selectedRecord) === 'high' ? 'Ожидается опоздание' : riskOf(selectedRecord) === 'medium' ? 'Возможное отклонение' : 'Движение в норме' }}</h2><p>Целевая остановка через <strong>{{ Math.round(selectedRecord.horizonSec / 60) }} мин</strong> от момента прогноза</p></div>
            <div class="priority-hero-side"><strong>{{ signedMinutes(selectedRecord.predictionSec) }}</strong><span>{{ selectedRecord.targetAddress }}</span></div>
          </section>
          <div class="content-grid">
            <section class="panel map-panel">
              <div class="panel-heading"><div><h2>Карта Москвы</h2></div><div class="map-heading-right"><span class="map-live" :class="{ demo: connection === 'demo' }"><span></span>{{ timeLabel(currentTime) }} МСК</span><button class="icon-button" title="Показать весь транспорт" aria-label="Показать весь транспорт" @click="transportMap?.resetView()"><RotateCcw :size="16" /></button></div></div>
              <TransportMap ref="transportMap" :records="mapRecords" :selected-id="selectedRecord?.sampleId" @select="selectedId = $event" />
            </section>

            <section class="panel incident-panel">
              <div class="panel-heading"><div><h2>Рейс под контролем</h2></div><button class="icon-button" title="Все прогнозы" aria-label="Все прогнозы" @click="setPage('fleet')"><MoreHorizontal :size="20" /></button></div>
              <template v-if="selectedRecord">
                <div class="incident-vehicle"><div class="vehicle-symbol"><Activity :size="22" /></div><div><h3>ТС {{ selectedRecord.vehicleId }}</h3><span class="vehicle-destination">{{ selectedRecord.targetAddress }}</span></div><span class="risk-pill" :class="riskOf(selectedRecord)"><i></i>{{ riskText[riskOf(selectedRecord)] }}</span></div>
                <div class="incident-details"><div><span>План прибытия</span><strong>{{ timeLabel(selectedRecord.targetTime) }}</strong></div><div><span>Прогноз прибытия</span><strong>{{ timeLabel(selectedRecord.estimatedArrival) }}</strong></div><div><span>Прогноз отклонения</span><strong>{{ preciseDelay(selectedRecord.predictionSec) }}</strong></div><div><span>Вероятность опоздания &gt; 2 мин</span><strong>{{ probabilityLabel(selectedRecord.delayProbability) }}</strong></div><div><span>{{ deviationLabel(selectedRecord) }}</span><strong>{{ preciseDelay(selectedRecord.currentDeviationSec) }}</strong></div><div><span>Последний GPS-пакет</span><strong :class="{ 'red-text': !isFresh(selectedRecord) }">{{ duration(selectedRecord.telemetryAgeSec) }} назад</strong></div></div>
                <div class="incident-context"><span>{{ selectedRecord.segmentLabel }}</span><span>Наблюдение: {{ selectedRecord.signal }}</span></div>
                <div v-if="selectedRecord.reasonFactors?.length" class="incident-factors"><strong>Что повлияло на прогноз</strong><span>Вклад признаков модели, не установленная причина задержки</span><ul><li v-for="factor in selectedRecord.reasonFactors" :key="factor.feature"><span>{{ factor.label }}{{ factor.value == null ? ' · нет данных' : '' }}</span><b>{{ preciseDelay(factor.shapValueSec) }}</b></li></ul></div>
                <div class="recommendation"><Zap :size="18" /><div><strong>Что проверить</strong><span>{{ recommendation }}</span></div></div>
                <div class="incident-foot"><button @click="showScenario = true">Оценить сценарий <ArrowRight :size="15" /></button></div>
              </template><div v-else class="empty-state"><Check :size="24" /><strong>Нет активных прогнозов</strong><span>Выберите другой момент на шкале времени.</span></div>
            </section>
          </div>

          <section class="panel fleet-panel compact-panel"><div class="section-head"><div><h2>Ближайшие прогнозы <span>{{ activeRecords.length }}</span></h2></div><button class="text-button" @click="setPage('fleet')">Все прогнозы <ArrowRight :size="16" /></button></div><div class="fleet-table-wrap"><table class="fleet-table"><thead><tr><th>ТРАНСПОРТ</th><th>ЦЕЛЕВАЯ ОСТАНОВКА</th><th>ПРИБЫТИЕ</th><th>ПРОГНОЗ</th><th>РИСК</th><th></th></tr></thead><tbody><tr v-for="record in activeRecords" :key="record.sampleId" :class="{ selected: selectedRecord?.sampleId === record.sampleId }" @click="selectedId = record.sampleId"><td><span class="table-vehicle-icon"><Activity :size="16" /></span><strong>ТС {{ record.vehicleId }}</strong></td><td class="address-cell">{{ record.targetAddress }}</td><td>{{ timeLabel(record.targetTime) }}</td><td><strong :class="`${riskOf(record)}-text`">{{ signedMinutes(record.predictionSec) }}</strong><small>{{ preciseDelay(record.predictionSec) }}</small></td><td><span class="risk-pill" :class="riskOf(record)"><i></i>{{ riskText[riskOf(record)] }}</span></td><td><ChevronRight :size="17" /></td></tr><tr v-if="!activeRecords.length"><td colspan="6" class="no-rows">Нет прогнозов в выбранном моменте. Используйте шкалу воспроизведения.</td></tr></tbody></table></div></section>
        </template>

        <template v-else-if="page === 'fleet'">
          <div class="fleet-toolbar"><div class="search-box"><Search :size="18" /><input v-model="search" placeholder="Найти ТС, остановку или sample_id" aria-label="Поиск прогнозов" /><button v-if="search" aria-label="Очистить поиск" @click="search = ''"><X :size="16" /></button></div><div class="filter-pills" aria-label="Фильтр риска"><button v-for="option in [{ id:'all',label:'Все' },{ id:'high',label:'Высокий' },{ id:'medium',label:'Внимание' },{ id:'low',label:'В норме' }]" :key="option.id" :class="{ active: riskFilter === option.id }" @click="riskFilter = option.id">{{ option.label }}</button></div></div>
          <section class="panel full-fleet-panel"><div class="section-head"><div><div class="panel-kicker">АКТИВНЫЙ СРЕЗ</div><h2>На контроле сейчас <span>{{ visibleRecords.length }}</span></h2></div><span class="caption">Каждый прогноз создан за 10–15 мин до плановой остановки</span></div><div class="fleet-table-wrap"><table class="fleet-table"><thead><tr><th>ТРАНСПОРТ</th><th>ЦЕЛЕВАЯ ОСТАНОВКА</th><th>ПЛАН</th><th>ПРОГНОЗ</th><th>ТЕЛЕМЕТРИЯ</th><th>РИСК</th></tr></thead><tbody><tr v-for="record in visibleRecords" :key="record.sampleId" @click="selectedId = record.sampleId; page = 'overview'"><td><strong>ТС {{ record.vehicleId }}</strong><small>{{ record.sampleId }}</small></td><td class="address-cell">{{ record.targetAddress }}</td><td>{{ timeLabel(record.targetTime) }}</td><td><strong :class="`${riskOf(record)}-text`">{{ preciseDelay(record.predictionSec) }}</strong></td><td>{{ duration(record.telemetryAgeSec) }} назад</td><td><span class="risk-pill" :class="riskOf(record)"><i></i>{{ riskText[riskOf(record)] }}</span></td></tr><tr v-if="!visibleRecords.length"><td colspan="6" class="no-rows">Нет записей по выбранному фильтру.</td></tr></tbody></table></div></section>
          <section class="panel history-panel"><div class="section-head"><div><div class="panel-kicker">ИСТОРИЯ ВОСПРОИЗВЕДЕНИЯ</div><h2>Последний час <span>{{ recentRecords.length }}</span></h2></div><span class="caption">Последние точки каждого ТС могут повторяться</span></div><div class="history-list"><div v-for="record in recentRecords" :key="record.sampleId" class="history-row"><span class="history-time">{{ timeLabel(record.timestamp) }}</span><span class="history-line" :class="riskOf(record)"></span><strong>ТС {{ record.vehicleId }}</strong><span class="history-address">{{ record.targetAddress }}</span><span :class="`${riskOf(record)}-text`">{{ preciseDelay(record.predictionSec) }}</span><span class="risk-pill" :class="riskOf(record)"><i></i>{{ riskText[riskOf(record)] }}</span></div><div v-if="!recentRecords.length" class="no-rows">Нет точек за последний час.</div></div></section>
        </template>

        <template v-else>
          <div class="analytics-grid"><section class="panel analytics-chart"><div class="section-head"><div><div class="panel-kicker">ПОСЛЕДНИЙ ЧАС</div><h2>Динамика прогнозов</h2></div><span class="caption">Секунды относительно плана</span></div><div class="chart-area"><div class="chart-y"><span>+6 мин</span><span>+4 мин</span><span>+2 мин</span><span>0</span></div><svg viewBox="0 0 600 180" preserveAspectRatio="none" aria-label="График прогнозируемых задержек"><line x1="20" y1="15" x2="580" y2="15"/><line x1="20" y1="55" x2="580" y2="55"/><line x1="20" y1="95" x2="580" y2="95"/><line x1="20" y1="142" x2="580" y2="142"/><path v-if="chartPath" :d="chartPath" class="chart-path"/><circle v-for="point in chartPoints" :key="point.record.sampleId" :cx="point.x" :cy="point.y" r="4" :class="riskOf(point.record)"><title>{{ timeLabel(point.record.timestamp) }} · ТС {{ point.record.vehicleId }} · {{ preciseDelay(point.record.predictionSec) }}</title></circle></svg></div><div class="chart-caption"><span>{{ timeLabel(recentRecords.at(-1)?.timestamp) }}</span><span>{{ timeLabel(currentTime) }}</span></div></section><section class="panel insight-panel"><div class="panel-kicker">КАК ЧИТАТЬ СИГНАЛЫ</div><h2>Логика приоритета</h2><div class="insight-row"><span class="insight-icon red"><AlertCircle :size="18" /></span><div><strong>Высокий риск</strong><p>Прогноз опоздания более 120 секунд.</p></div></div><div class="insight-row"><span class="insight-icon amber"><Gauge :size="18" /></span><div><strong>Нужен контроль</strong><p>Прогноз от 60 до 120 секунд.</p></div></div><div class="insight-row"><span class="insight-icon green"><Check :size="18" /></span><div><strong>В норме</strong><p>Менее 60 секунд или прибытие раньше плана.</p></div></div><div class="insight-foot"><Info :size="15" /> Пороги — правило интерфейса, не вероятность модели.</div></section></div>
        </template>
        </div></Transition>
      </main>

      <footer class="replay-bar"><div class="replay-label"><span class="replay-icon"><Clock3 :size="18" /></span><div><strong>{{ connection === 'replay' || connection === 'demo' ? 'Историческое воспроизведение' : 'Срез прогнозов' }}</strong><small>{{ dateLabel(currentTime) }} · МСК</small></div></div><div class="replay-controls"><button aria-label="Предыдущая точка" title="Предыдущая точка" @click="step(-1)"><ChevronLeft :size="19" /></button><button class="play-button" :aria-label="playing ? 'Пауза' : 'Воспроизвести'" @click="playing = !playing"><Pause v-if="playing" :size="17" fill="currentColor" /><Play v-else :size="17" fill="currentColor" /></button><button aria-label="Следующая точка" title="Следующая точка" @click="step(1)"><ChevronRight :size="19" /></button></div><div class="timeline"><span>{{ timestamps[0] ? timeLabel(timestamps[0]) : '—' }}</span><input type="range" :min="0" :max="Math.max(0, timestamps.length - 1)" v-model.number="currentIndex" aria-label="Время воспроизведения" /><span>{{ timestamps.at(-1) ? timeLabel(timestamps.at(-1)) : '—' }}</span></div><div class="current-clock">{{ timeLabel(currentTime) }} <span>МСК</span></div></footer>
    </div>

    <div v-if="showScenario" class="modal-backdrop" @click.self="showScenario = false"><section class="scenario-modal" role="dialog" aria-modal="true" aria-labelledby="scenario-title"><div class="modal-head"><span class="modal-icon"><SlidersHorizontal :size="21" /></span><button aria-label="Закрыть" @click="showScenario = false"><X :size="21" /></button></div><div class="panel-kicker">СЦЕНАРИЙ ДИСПЕТЧЕРА</div><h2 id="scenario-title">Что, если сократить простой?</h2><p>Оцените возможный эффект для выбранного ТС. Это арифметический сценарий, не повторный прогноз модели.</p><div v-if="selectedRecord" class="scenario-target"><span>ТС {{ selectedRecord.vehicleId }} · {{ selectedRecord.targetAddress }}</span><strong>{{ preciseDelay(selectedRecord.predictionSec) }}</strong></div><label class="scenario-label" for="scenario-range">Сократить задержку на остановках <strong>{{ scenarioSeconds }} с</strong></label><input id="scenario-range" v-model.number="scenarioSeconds" type="range" min="0" max="300" step="15" /><div class="scenario-scale"><span>0 с</span><span>5 мин</span></div><div class="scenario-result"><div><span>Исходный прогноз</span><strong>{{ selectedRecord ? preciseDelay(selectedRecord.predictionSec) : '—' }}</strong></div><ArrowRight :size="22" /><div><span>Сценарное отклонение</span><strong>{{ selectedRecord ? preciseDelay(scenarioResult) : '—' }}</strong></div></div><div class="scenario-disclaimer"><Info :size="16" /> Предположение: каждую сэкономленную секунду простоя переносим на прибытие один к одному. Влияние на остальные рейсы и вероятность реализации не рассчитаны.</div><button class="primary-button modal-done" @click="showScenario = false">Готово</button></section></div>
    <div v-if="toast" class="toast" role="status"><Check :size="17" /> {{ toast }}</div>
  </div>
</template>


