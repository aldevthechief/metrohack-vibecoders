<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import yandexLogo from '../assets/yandex-logo.svg'

const props = defineProps({
  records: { type: Array, default: () => [] },
  selectedId: { type: String, default: null },
})
const emit = defineEmits(['select'])
const element = ref(null)
const tilesUnavailable = ref(false)
const mapFallback = ref(false)
const activeProvider = ref(import.meta.env.VITE_YANDEX_TILES_API_KEY ? 'yandex' : 'osm')
let map
let overlay
let tileLayer
let tileErrors = 0
let resizeObserver

const osmUrl = import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const osmAttribution = import.meta.env.VITE_MAP_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
const yandexKey = import.meta.env.VITE_YANDEX_TILES_API_KEY?.trim()
const yandexStyles = ['map', 'future_map', 'driving', 'transit', 'admin']
const yandexStyle = yandexStyles.includes(import.meta.env.VITE_YANDEX_MAP_STYLE) ? import.meta.env.VITE_YANDEX_MAP_STYLE : 'map'
// Leaflet uses spherical Web Mercator. Request the matching projection so overlays align.
const yandexUrl = yandexKey && `https://tiles.api-maps.yandex.ru/v1/tiles/?apikey=${encodeURIComponent(yandexKey)}&lang=ru_RU&x={x}&y={y}&z={z}&l=map&projection=web_mercator&maptype=${yandexStyle}`
const yandexAttribution = '&copy; <a href="https://yandex.ru/maps/" target="_blank" rel="noopener">Яндекс</a> · <a href="https://yandex.ru/legal/maps_termsofuse/" target="_blank" rel="noopener">Условия использования</a>'

function setTileLayer(provider) {
  if (!map) return
  if (tileLayer) map.removeLayer(tileLayer)
  tileErrors = 0
  tilesUnavailable.value = false
  activeProvider.value = provider
  tileLayer = L.tileLayer(provider === 'yandex' ? yandexUrl : osmUrl, {
    maxZoom: provider === 'yandex' ? 20 : 18,
    attribution: provider === 'yandex' ? yandexAttribution : osmAttribution,
  })
  tileLayer.on('tileerror', () => {
    tileErrors += 1
    if (tileErrors < 3) return
    if (provider === 'yandex') {
      mapFallback.value = true
      setTileLayer('osm')
    } else tilesUnavailable.value = true
  })
  tileLayer.on('tileload', () => { tileErrors = 0; tilesUnavailable.value = false })
  tileLayer.addTo(map)
}

const latLng = ([lon, lat]) => [lat, lon]
const risk = (record) => ['high', 'medium', 'low'].includes(record.riskLevel) ? record.riskLevel : record.predictionSec > 120 ? 'high' : record.predictionSec >= 60 ? 'medium' : 'low'

// Scheduled stops form a useful corridor, but they are not road geometry.
// A small Douglas–Peucker pass removes minor zigzags while retaining turns.
function straightenRoute(points, tolerance = 0.0015) {
  if (points.length < 3) return points
  const planar = ([lon, lat]) => [lon * Math.cos(55.75 * Math.PI / 180), lat]
  const distance = (point, start, end) => {
    const [px, py] = planar(point)
    const [ax, ay] = planar(start)
    const [bx, by] = planar(end)
    const dx = bx - ax; const dy = by - ay
    const t = dx || dy ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy))) : 0
    return Math.hypot(px - ax - t * dx, py - ay - t * dy)
  }
  let farthest = 0; let index = 0
  for (let i = 1; i < points.length - 1; i += 1) {
    const d = distance(points[i], points[0], points.at(-1))
    if (d > farthest) { farthest = d; index = i }
  }
  if (farthest <= tolerance) return [points[0], points.at(-1)]
  return [...straightenRoute(points.slice(0, index + 1), tolerance).slice(0, -1), ...straightenRoute(points.slice(index), tolerance)]
}

function vehicleIcon(record) {
  const state = risk(record)
  const vehicleId = String(record.vehicleId).replace(/[^0-9A-Za-z_-]/g, '')
  return L.divIcon({
    className: 'vehicle-map-icon',
    html: `<span class="vehicle-map-pin ${state} ${record.sampleId === props.selectedId ? 'selected' : ''}"><span class="vehicle-map-symbol"></span>${vehicleId}</span>`,
    iconSize: [86, 34],
    iconAnchor: [43, 17],
  })
}

function targetIcon(record) {
  return L.divIcon({
    className: 'target-map-icon',
    html: `<span class="target-map-pin ${risk(record)}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  })
}

function renderRecords(fit = false) {
  if (!map || !overlay) return
  overlay.clearLayers()
  const bounds = []
  for (const record of props.records) {
    if (!record.position) continue
    const selected = record.sampleId === props.selectedId
    const state = risk(record)
    const color = state === 'high' ? '#cf303b' : state === 'medium' ? '#d58a2c' : '#2f9275'
    const route = straightenRoute(record.route || [])
    if (route.length > 1) {
      L.polyline(route.map(latLng), {
        color: '#ffffff', weight: selected ? 7 : 6, opacity: selected ? 0.9 : 0.65,
        interactive: false, lineJoin: 'round',
      }).addTo(overlay)
      L.polyline(route.map(latLng), {
        color, weight: selected ? 3.5 : 2.8, opacity: selected ? 0.95 : 0.75,
        interactive: false, lineJoin: 'round',
      }).addTo(overlay)
    }
    // Only show stop dots for the focused vehicle to keep street names legible.
    if (selected) {
      for (const stop of route.slice(1, -1)) {
        L.circleMarker(latLng(stop), { radius: 3, color, weight: 1.5, fillColor: '#fff', fillOpacity: 1, interactive: false }).addTo(overlay)
      }
    }
    if (record.targetCoordinate) {
      L.marker(latLng(record.targetCoordinate), { icon: targetIcon(record), keyboard: false, zIndexOffset: 100 })
        .bindTooltip('Целевая остановка', { direction: 'top', offset: [0, -8] }).addTo(overlay)
      bounds.push(latLng(record.targetCoordinate))
    }
    L.marker(latLng(record.position), { icon: vehicleIcon(record), riseOnHover: true, zIndexOffset: 400 })
      .on('click', () => emit('select', record.sampleId))
      .bindTooltip(`ТС ${String(record.vehicleId).replace(/[^0-9A-Za-z_-]/g, '')}`, { direction: 'top', offset: [0, -15] })
      .addTo(overlay)
    bounds.push(latLng(record.position))
  }
  if (fit) {
    const padding = map.getSize().x < 430 ? [68, 68] : [50, 50]
    if (bounds.length) map.fitBounds(L.latLngBounds(bounds), { padding, maxZoom: 12, animate: false })
    else map.setView([55.7512, 37.6184], 10, { animate: false })
  }
}

function focusSelected() {
  const record = props.records.find((item) => item.sampleId === props.selectedId)
  if (!record?.position || !map) return
  const positions = [record.position, record.targetCoordinate, ...(record.route || [])].filter(Boolean).map(latLng)
  const padding = map.getSize().x < 430 ? [70, 70] : [54, 54]
  map.fitBounds(L.latLngBounds(positions), { padding, maxZoom: 13, animate: true, duration: 0.35 })
}

function resetView() { renderRecords(true) }
defineExpose({ resetView })

onMounted(async () => {
  await nextTick()
  map = L.map(element.value, { center: [55.7512, 37.6184], zoom: 10, zoomControl: false, scrollWheelZoom: false, preferCanvas: true })
  L.control.zoom({ position: 'topright' }).addTo(map)
  setTileLayer(yandexKey ? 'yandex' : 'osm')
  overlay = L.layerGroup().addTo(map)
  renderRecords(true)
  resizeObserver = new ResizeObserver(() => {
    map.invalidateSize({ pan: false })
    renderRecords(true)
  })
  resizeObserver.observe(element.value)
  nextTick(() => map.invalidateSize())
})
onUnmounted(() => { resizeObserver?.disconnect(); map?.remove(); map = null })
watch(() => props.records, () => renderRecords(true))
watch(() => props.selectedId, (value) => { renderRecords(false); if (value) focusSelected() })
</script>

<template>
  <div class="transport-map-wrap">
    <div ref="element" class="transport-map" role="application" aria-label="Карта Москвы с транспортом и остановками"></div>
    <div v-if="tilesUnavailable" class="map-tile-warning">Не удалось загрузить карту улиц. Проверьте подключение к сети.</div>
    <div v-else-if="mapFallback" class="map-tile-warning">Яндекс Карты недоступны. Показана карта OpenStreetMap.</div>
    <template v-if="activeProvider === 'yandex'">
      <a class="yandex-map-logo" href="https://yandex.ru/maps/" target="_blank" rel="noopener" aria-label="Открыть Яндекс Карты"><img :src="yandexLogo" alt="Яндекс Карты" /></a>
      <a class="yandex-map-open" href="https://yandex.ru/maps/?ll=37.6184%2C55.7512&z=10" target="_blank" rel="noopener">Открыть в Яндекс Картах ↗</a>
    </template>
  </div>
</template>
