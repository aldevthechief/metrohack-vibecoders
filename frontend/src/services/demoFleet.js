const MAX_GPS_AGE_SECONDS = 300
const MAX_INTERPOLATION_GAP_SECONDS = 45

export function secondsOfDay(timestamp) {
  if (!timestamp) return 0
  const [hours = 0, minutes = 0, seconds = 0] = timestamp.slice(11).split(':').map(Number)
  return hours * 3600 + minutes * 60 + seconds
}

function lastPointAtOrBefore(points, seconds) {
  let low = 0
  let high = points.length
  while (low < high) {
    const middle = (low + high) >>> 1
    if (points[middle][0] <= seconds) low = middle + 1
    else high = middle
  }
  return low - 1
}

export function vehiclesAtTime(tracks, seconds) {
  const vehicles = []
  for (const [vehicleId, points] of Object.entries(tracks || {})) {
    const index = lastPointAtOrBefore(points, seconds)
    if (index < 0 || seconds - points[index][0] > MAX_GPS_AGE_SECONDS) continue
    const current = points[index]
    const next = points[index + 1]
    const canInterpolate = next && next[0] > current[0] && next[0] - current[0] <= MAX_INTERPOLATION_GAP_SECONDS
    const fraction = canInterpolate ? Math.max(0, Math.min(1, (seconds - current[0]) / (next[0] - current[0]))) : 0
    const position = canInterpolate
      ? [current[1] + (next[1] - current[1]) * fraction, current[2] + (next[2] - current[2]) * fraction]
      : [current[1], current[2]]
    const trail = points.slice(Math.max(0, index - 15), index + 1).map((point) => [point[1], point[2]])
    if (canInterpolate && fraction > 0) trail.push(position)
    vehicles.push({
      vehicleId,
      position,
      trail,
      speedKmh: current[3],
      telemetryAgeSec: Math.round(seconds - current[0]),
      status: seconds - current[0] <= 120 ? 'live' : 'stale',
      source: 'demo',
      predictionStatus: 'no-forecast-sample',
    })
  }
  return vehicles
}
