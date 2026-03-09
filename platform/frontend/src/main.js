import './style.css'
import { statusText } from './utils'

const app = document.querySelector('#app')

app.innerHTML = `
  <div class="container">
    <h1>Manga Update Platform</h1>

    <div class="card">
      <h2>Search & One-Click Subscribe</h2>
      <div class="actions">
        <select id="sourceSelect"><option value="copymanga">CopyManga</option></select>
        <input id="searchInput" placeholder="keyword" />
        <button id="searchBtn">Search</button>
      </div>
      <table id="searchTable">
        <thead><tr><th>Cover</th><th>Comic</th><th>Action</th></tr></thead>
        <tbody></tbody>
      </table>
      <div id="searchPager" class="search-pager"></div>
    </div>

    <div class="card">
      <h2>Subscriptions</h2>
      <div class="actions">
        <button id="refreshSubs">Refresh</button>
        <button id="runCheck">Run Check</button>
        <button id="runSummary">Run Daily Summary</button>
      </div>
      <p class="field-guide">调试说明：可对某个订阅执行“测试通知”与“模拟更新”。模拟更新仅用于验证链路，不会进入当日自动汇总推送。</p>
      <table id="subsTable">
        <thead><tr><th>ID</th><th>Source</th><th>Title</th><th>Status</th><th>Last Seen</th><th>Action</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <div class="card">
      <h2>Schedules & Settings</h2>
      <div class="grid">
        <label>Timezone <select id="timezone"></select></label>
        <label>Check Cron <input id="checkCron" /></label>
        <label>Daily Summary Cron <input id="dailyCron" /></label>
        <label>Webhook URL <input id="webhookUrl" /></label>
      </div>
      <div class="actions" style="margin-top:8px;">
        <label><input type="checkbox" id="timezoneAuto" /> Timezone Auto (by IP)</label>
        <label><input type="checkbox" id="webhookEnabled" /> Webhook Enabled</label>
        <label><input type="checkbox" id="rssEnabled" /> RSS Enabled</label>
        <button id="saveSettings">Save Settings</button>
      </div>
      <p id="timezoneHint" class="field-guide"></p>
      <p class="field-guide">配置指南：Timezone Auto 开启后会按当前访问 IP 自动设置时区；关闭后可手动选择时区。Check Cron 控制抓取频率；Daily Summary Cron 控制每日汇总发送时间。汇总会发送尚未汇总的真实更新，避免停机恢复后漏推送。</p>
    </div>

    <div class="card">
      <h2>Events</h2>
      <div class="actions"><button id="refreshEvents">Refresh Events</button><a class="badge" href="/api/notifications/rss.xml" target="_blank">RSS</a></div>
      <table id="eventsTable">
        <thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Detected</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
`

const searchTable = document.querySelector('#searchTable tbody')
const searchPager = document.querySelector('#searchPager')
const subsTable = document.querySelector('#subsTable tbody')
const eventsTable = document.querySelector('#eventsTable tbody')
const SEARCH_PAGE_SIZE = 20
let searchKeyword = ''
let searchPage = 1
let searchTotal = 0

// When auto-timezone is enabled, manual timezone input must be read-only in UI.
function applyTimezoneInputMode() {
  const auto = document.querySelector('#timezoneAuto').checked
  const timezoneSelect = document.querySelector('#timezone')
  timezoneSelect.disabled = auto
  timezoneSelect.title = auto ? '开启自动模式时由访问 IP 自动设置' : ''
}

function setTimezoneHint(timezone, timezoneAuto) {
  const hint = document.querySelector('#timezoneHint')
  if (timezoneAuto) {
    hint.textContent = `当前自动时区：${timezone}`
    return
  }
  hint.textContent = `当前手动时区：${timezone}`
}

function ensureTimezoneOption(timezone) {
  if (!timezone) {
    return
  }
  const timezoneSelect = document.querySelector('#timezone')
  const exists = Array.from(timezoneSelect.options).some((opt) => opt.value === timezone)
  if (exists) {
    return
  }
  const option = document.createElement('option')
  option.value = timezone
  option.textContent = timezone
  timezoneSelect.appendChild(option)
}

async function loadTimezoneOptions() {
  const zones = await req('/api/timezones')
  const timezoneSelect = document.querySelector('#timezone')
  timezoneSelect.innerHTML = ''
  for (const zone of zones) {
    const option = document.createElement('option')
    option.value = zone
    option.textContent = zone
    timezoneSelect.appendChild(option)
  }
}

async function req(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}

async function loadSettings() {
  const s = await req('/api/settings')
  ensureTimezoneOption(s.timezone)
  document.querySelector('#timezone').value = s.timezone
  document.querySelector('#timezoneAuto').checked = Boolean(s.timezone_auto)
  document.querySelector('#checkCron').value = s.check_cron
  document.querySelector('#dailyCron').value = s.daily_summary_cron
  document.querySelector('#webhookUrl').value = s.webhook_url
  document.querySelector('#webhookEnabled').checked = s.webhook_enabled
  document.querySelector('#rssEnabled').checked = s.rss_enabled
  applyTimezoneInputMode()
  setTimezoneHint(s.timezone, Boolean(s.timezone_auto))
}

function buildSearchMeta(item) {
  const fetchStatus = item?.meta?.meta_fetch_status || 'fetch_failed'
  const latestUpdateTime = typeof item?.meta?.latest_update_time === 'string'
    ? item.meta.latest_update_time.trim()
    : ''
  const latestUpdate = latestUpdateTime || (fetchStatus === 'ok' ? '暂无时间' : '未抓到')

  const chapters = Array.isArray(item?.meta?.latest_chapters)
    ? item.meta.latest_chapters.filter((name) => typeof name === 'string' && name.trim())
    : []
  const latestChapters = chapters.length > 0
    ? chapters.join(' / ')
    : (fetchStatus === 'ok' ? '暂无章节' : '未抓到')

  return `最后更新：${latestUpdate} | 最新话：${latestChapters}`
}

function renderSearchPager() {
  searchPager.innerHTML = ''
  if (!searchKeyword) {
    return
  }

  const totalPages = Math.max(1, Math.ceil(searchTotal / SEARCH_PAGE_SIZE))
  const prevBtn = document.createElement('button')
  prevBtn.textContent = 'Prev'
  prevBtn.disabled = searchPage <= 1
  prevBtn.addEventListener('click', () => {
    search(searchPage - 1).catch((err) => alert(err.message))
  })

  const nextBtn = document.createElement('button')
  nextBtn.textContent = 'Next'
  nextBtn.disabled = searchPage >= totalPages
  nextBtn.addEventListener('click', () => {
    search(searchPage + 1).catch((err) => alert(err.message))
  })

  const info = document.createElement('span')
  info.className = 'search-pager-info'
  info.textContent = `Page ${searchPage}/${totalPages} - Total ${searchTotal}`

  searchPager.appendChild(prevBtn)
  searchPager.appendChild(nextBtn)
  searchPager.appendChild(info)
}

async function search(page = 1) {
  const source = document.querySelector('#sourceSelect').value
  if (page === 1) {
    searchKeyword = document.querySelector('#searchInput').value.trim()
  }
  if (!searchKeyword) {
    return
  }
  const data = await req(
    `/api/search?source=${encodeURIComponent(source)}&q=${encodeURIComponent(searchKeyword)}&page=${page}`
  )
  searchPage = data.page
  searchTotal = data.total
  searchTable.innerHTML = ''
  for (const item of data.items) {
    const tr = document.createElement('tr')
    const coverCell = item.cover
      ? `<img class="search-cover" src="${item.cover}" alt="${item.title}" loading="lazy" />`
      : `<div class="search-cover search-cover-empty">No Cover</div>`
    tr.innerHTML = `
      <td>${coverCell}</td>
      <td>
        <div class="search-title">${item.title}</div>
        <div class="search-author">Author: ${item.author || '-'}</div>
        <div class="search-meta">${buildSearchMeta(item)}</div>
      </td>
      <td><button>Subscribe</button></td>
    `
    tr.querySelector('button').addEventListener('click', async () => {
      // Persist search metadata so subscription list can show Last Seen immediately.
      await req('/api/subscriptions', {
        method: 'POST',
        body: JSON.stringify({
          source_code: source,
          item_id: item.item_id,
          item_title: item.title,
          group_word: item.group_word || 'default',
          item_meta: { ...(item.meta || {}), group_word: item.group_word || 'default' }
        })
      })
      await loadSubscriptions()
    })
    searchTable.appendChild(tr)
  }
  renderSearchPager()
}

function formatLastSeenTime(value) {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

async function loadSubscriptions() {
  const subs = await req('/api/subscriptions')
  subsTable.innerHTML = ''
  for (const sub of subs) {
    const seenTime = formatLastSeenTime(sub.last_seen_update_at)
    const seenTitle = sub.last_seen_update_title || '-'
    const tr = document.createElement('tr')
    tr.innerHTML = `
      <td>${sub.id}</td>
      <td>${sub.source_code}</td>
      <td>${sub.item_title}</td>
      <td>${sub.status}</td>
      <td>
        <div class="sub-last-seen-time">${seenTime}</div>
        <div class="sub-last-seen-title">${seenTitle}</div>
      </td>
      <td>
        <div class="row-actions">
          <button data-action="simulate">Sim Update</button>
          <button data-action="notify">Test Notify</button>
          <button data-action="delete">Delete</button>
        </div>
      </td>
    `
    tr.querySelector('[data-action="delete"]').addEventListener('click', async () => {
      await req(`/api/subscriptions/${sub.id}`, { method: 'DELETE' })
      await loadSubscriptions()
    })
    tr.querySelector('[data-action="simulate"]').addEventListener('click', async () => {
      // Simulated event is for diagnostics only and is excluded from auto summary.
      const out = await req(`/api/subscriptions/${sub.id}/debug/simulate-update`, { method: 'POST' })
      alert(`simulated event id=${out.event_id}`)
      await loadEvents()
    })
    tr.querySelector('[data-action="notify"]').addEventListener('click', async () => {
      const out = await req(`/api/subscriptions/${sub.id}/debug/notify-test`, { method: 'POST' })
      const delivered = Array.isArray(out.delivered_channels) ? out.delivered_channels.join(',') : '-'
      const skipped = Array.isArray(out.skipped_channels) ? out.skipped_channels.join(',') : '-'
      alert(`notify test status=${out.status}\ndelivered=${delivered}\nskipped=${skipped}`)
    })
    subsTable.appendChild(tr)
  }
}

async function loadEvents() {
  const events = await req('/api/events?status=all')
  eventsTable.innerHTML = ''
  for (const event of events) {
    const tr = document.createElement('tr')
    tr.innerHTML = `<td>${event.id}</td><td>${event.update_title}</td><td>${statusText(event)}</td><td>${event.detected_at}</td>`
    eventsTable.appendChild(tr)
  }
}

async function saveSettings() {
  const timezoneAuto = document.querySelector('#timezoneAuto').checked
  const payload = {
    timezone_auto: timezoneAuto,
    check_cron: document.querySelector('#checkCron').value,
    daily_summary_cron: document.querySelector('#dailyCron').value,
    webhook_url: document.querySelector('#webhookUrl').value,
    webhook_enabled: document.querySelector('#webhookEnabled').checked,
    rss_enabled: document.querySelector('#rssEnabled').checked
  }
  if (!timezoneAuto) {
    payload.timezone = document.querySelector('#timezone').value
  }
  // In auto mode backend determines timezone from request IP; do not force manual value.
  await req('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
  await loadSettings()
  alert('Settings saved')
}

document.querySelector('#searchBtn').addEventListener('click', () => {
  search(1).catch((err) => alert(err.message))
})

document.querySelector('#refreshSubs').addEventListener('click', () => {
  loadSubscriptions().catch((err) => alert(err.message))
})

document.querySelector('#refreshEvents').addEventListener('click', () => {
  loadEvents().catch((err) => alert(err.message))
})

document.querySelector('#saveSettings').addEventListener('click', () => {
  saveSettings().catch((err) => alert(err.message))
})

document.querySelector('#timezoneAuto').addEventListener('change', () => {
  applyTimezoneInputMode()
  const timezone = document.querySelector('#timezone').value
  const timezoneAuto = document.querySelector('#timezoneAuto').checked
  setTimezoneHint(timezone, timezoneAuto)
})

document.querySelector('#timezone').addEventListener('change', () => {
  const timezone = document.querySelector('#timezone').value
  const timezoneAuto = document.querySelector('#timezoneAuto').checked
  setTimezoneHint(timezone, timezoneAuto)
})

document.querySelector('#runCheck').addEventListener('click', async () => {
  const out = await req('/api/jobs/run-check', { method: 'POST' })
  alert(`check done: scanned=${out.scanned}, discovered=${out.discovered}`)
  await loadEvents()
  await loadSubscriptions()
})

document.querySelector('#runSummary').addEventListener('click', async () => {
  const out = await req('/api/jobs/run-daily-summary', { method: 'POST' })
  alert(`summary status=${out.status}`)
  await loadEvents()
})

async function bootstrap() {
  await loadTimezoneOptions()
  // Fetch settings first to ensure timezone hint/control state is accurate on first paint.
  await Promise.all([loadSettings(), loadSubscriptions(), loadEvents()])
}

bootstrap().catch((err) => {
  console.error(err)
})

