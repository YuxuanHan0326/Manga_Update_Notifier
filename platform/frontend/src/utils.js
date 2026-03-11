export function statusText(event) {
  // Event status is derived from summary/notified timestamps to match backend semantics.
  if (!event.summarized_at) {
    return '未汇总'
  }
  if (!event.notified_at) {
    return '已汇总'
  }
  return '已通知'
}

function pad2(value) {
  return String(value).padStart(2, '0')
}

export function normalizeCheckHours(hoursRaw) {
  const hours = Number.parseInt(String(hoursRaw), 10)
  if (Number.isNaN(hours) || hours < 1) {
    return 6
  }
  if (hours > 24) {
    return 24
  }
  return hours
}

export function buildCheckCronFromHours(hoursRaw) {
  const hours = normalizeCheckHours(hoursRaw)
  // "Every 24 hours" is represented as once a day at midnight in simple mode.
  if (hours === 24) {
    return '0 0 * * *'
  }
  return `0 */${hours} * * *`
}

export function parseCheckCronToHours(cronRaw) {
  const cron = String(cronRaw || '').trim()
  if (cron === '0 0 * * *') {
    return 24
  }
  const match = /^0\s+\*\/([1-9]|1[0-9]|2[0-3])\s+\*\s+\*\s+\*$/.exec(cron)
  if (!match) {
    return null
  }
  return Number.parseInt(match[1], 10)
}

export function buildDailyCronFromTime(timeRaw) {
  const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(String(timeRaw || '').trim())
  if (!match) {
    return '0 21 * * *'
  }
  const [, hour, minute] = match
  return `${Number.parseInt(minute, 10)} ${Number.parseInt(hour, 10)} * * *`
}

export function parseDailyCronToTime(cronRaw) {
  const cron = String(cronRaw || '').trim()
  const match = /^([0-5]?\d)\s+([01]?\d|2[0-3])\s+\*\s+\*\s+\*$/.exec(cron)
  if (!match) {
    return null
  }
  const minute = Number.parseInt(match[1], 10)
  const hour = Number.parseInt(match[2], 10)
  return `${pad2(hour)}:${pad2(minute)}`
}
