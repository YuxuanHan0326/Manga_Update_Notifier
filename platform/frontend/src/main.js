import './style.css'
import {
  buildCheckCronFromHours,
  buildDailyCronFromTime,
  normalizeCheckHours,
  parseCheckCronToHours,
  parseDailyCronToTime,
  statusText
} from './utils'

const app = document.querySelector('#app')

app.innerHTML = `
  <div class="container">
    <h1>Manga Update Notifier</h1>

    <div class="tab-nav" role="tablist" aria-label="主视图">
      <button class="tab-btn is-active" data-tab="general" type="button">通用</button>
      <button class="tab-btn" data-tab="copymanga" type="button">CopyManga</button>
      <button class="tab-btn" data-tab="kxo" type="button">KXO</button>
    </div>

    <section class="tab-panel is-active" data-panel="general">
      <div class="card">
        <h2>订阅管理</h2>
        <div class="actions">
          <button id="refreshSubs" type="button">刷新</button>
          <button id="runCheck" type="button">立即检查</button>
          <button id="runSummary" type="button">立即汇总</button>
        </div>
        <p class="field-guide">调试说明：可对单个订阅执行“测试通知”和“模拟更新”。模拟更新仅用于验证链路，不会进入自动汇总推送。</p>
        <table id="subsTable">
          <thead><tr><th>编号</th><th>封面</th><th>来源</th><th>作品</th><th>状态</th><th>最近记录</th><th>操作</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>

      <div class="card">
        <h2>计划与通用设置</h2>
        <div class="grid">
          <label>时区 <select id="timezone"></select></label>
          <label>每几小时检查一次 <input id="checkEveryHours" type="number" min="1" max="24" step="1" /></label>
          <label>每日汇总时间 <input id="dailySummaryTime" type="time" /></label>
          <label>检查 Cron（高级） <input id="checkCron" /></label>
          <label>日报 Cron（高级） <input id="dailyCron" /></label>
          <label>Webhook 地址 <input id="webhookUrl" /></label>
        </div>
        <div class="actions" style="margin-top: 8px;">
          <label class="toggle-option">时区自动识别（按 IP） <input type="checkbox" id="timezoneAuto" /></label>
          <label class="toggle-option">启用 Webhook <input type="checkbox" id="webhookEnabled" /></label>
          <label class="toggle-option">启用 RSS <input type="checkbox" id="rssEnabled" /></label>
          <button id="saveGeneralSettings" type="button">保存通用设置</button>
        </div>
        <p id="timezoneHint" class="field-guide"></p>
        <p id="scheduleHint" class="field-guide"></p>
        <p class="field-guide">配置指南：优先使用“每几小时检查一次”和“每日汇总时间”，高级场景再手动填写 Cron。</p>
      </div>

      <div class="card">
        <h2>事件</h2>
        <div class="actions">
          <button id="refreshEvents" type="button">刷新事件</button>
          <a class="badge" href="/api/notifications/rss.xml" target="_blank" rel="noreferrer">RSS</a>
        </div>
        <p class="field-guide">事件默认仅显示启用订阅且非调试记录；排障可使用 API 参数 include_debug/include_inactive。</p>
        <table id="eventsTable">
          <thead><tr><th>编号</th><th>更新标题</th><th>状态</th><th>检测时间</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <section class="tab-panel" data-panel="copymanga">
      <div class="card">
        <h2>CopyManga 搜索与订阅</h2>
        <div class="actions">
          <input id="copySearchInput" placeholder="关键词" />
          <button id="copySearchBtn" type="button">搜索 CopyManga</button>
        </div>
        <table id="copySearchTable">
          <thead><tr><th>封面</th><th>漫画</th><th>操作</th></tr></thead>
          <tbody></tbody>
        </table>
        <div id="copySearchPager" class="search-pager"></div>
      </div>
    </section>

    <section class="tab-panel" data-panel="kxo">
      <div class="card">
        <h2>KXO 模式</h2>
        <p class="field-guide">KXO 当前仅支持手动 URL/ID 订阅，不提供站内搜索或账号密码登录入口。</p>
      </div>

      <div class="card">
        <h2>手动添加 KXO 订阅</h2>
        <div class="actions">
          <input id="kxoManualRef" placeholder="KXO URL 或 ID（如 /c/20001.htm 或 20001）" />
          <input id="kxoManualTitle" placeholder="手动标题（可选）" />
          <button id="addKxoManual" type="button">添加 KXO 订阅</button>
        </div>
      </div>

      <div class="card">
        <h2>KXO 设置</h2>
        <div class="grid">
          <label>KXO 基础 URL <input id="kxoBaseUrl" placeholder="https://kzo.moe" /></label>
          <label>KXO 浏览器标识（User Agent） <input id="kxoUserAgent" /></label>
        </div>
        <div class="actions" style="margin-top: 8px;">
          <button id="testKxoSettings" type="button">测试 KXO</button>
          <button id="saveKxoSettings" type="button">保存 KXO 设置</button>
        </div>
        <p id="kxoHint" class="field-guide"></p>
        <p class="field-guide">仅用于手动订阅场景的基础连通配置，账号密码与 Cookie 登录链路已移除。</p>
      </div>
    </section>
  </div>
`

const subsTable = document.querySelector('#subsTable tbody')
const eventsTable = document.querySelector('#eventsTable tbody')
const SEARCH_PAGE_SIZE = 20
let copySearchKeyword = ''
let copySearchPage = 1
let copySearchTotal = 0

function setActiveTab(tabName) {
  const buttons = document.querySelectorAll('.tab-btn')
  const panels = document.querySelectorAll('.tab-panel')

  for (const button of buttons) {
    button.classList.toggle('is-active', button.dataset.tab === tabName)
  }

  for (const panel of panels) {
    panel.classList.toggle('is-active', panel.dataset.panel === tabName)
  }
}

function applyTimezoneInputMode() {
  const auto = document.querySelector('#timezoneAuto').checked
  const timezoneSelect = document.querySelector('#timezone')
  timezoneSelect.disabled = auto
  timezoneSelect.title = auto ? '开启自动模式时将根据访问 IP 自动设置' : ''
}

function setTimezoneHint(timezone, timezoneAuto) {
  const hint = document.querySelector('#timezoneHint')
  hint.textContent = timezoneAuto ? `当前自动时区：${timezone}` : `当前手动时区：${timezone}`
}

function setScheduleHint(checkCron, dailyCron) {
  const hint = document.querySelector('#scheduleHint')
  const checkHours = parseCheckCronToHours(checkCron)
  const dailyTime = parseDailyCronToTime(dailyCron)
  if (checkHours !== null && dailyTime !== null) {
    hint.textContent = `当前设置：每 ${checkHours} 小时检查一次；每日 ${dailyTime} 推送汇总。`
    return
  }
  hint.textContent = '检测到高级 Cron 表达式。可继续使用高级 Cron，或改用友好字段重新生成。'
}

function setKxoHint() {
  const hint = document.querySelector('#kxoHint')
  hint.textContent = 'KXO 当前为手动模式：仅支持手动 URL/ID 订阅与更新检测。'
}

function applyFriendlyScheduleToCron() {
  const hoursInput = document.querySelector('#checkEveryHours')
  const dailyTimeInput = document.querySelector('#dailySummaryTime')
  const checkCronInput = document.querySelector('#checkCron')
  const dailyCronInput = document.querySelector('#dailyCron')

  checkCronInput.value = buildCheckCronFromHours(normalizeCheckHours(hoursInput.value))
  dailyCronInput.value = buildDailyCronFromTime(dailyTimeInput.value)
  setScheduleHint(checkCronInput.value, dailyCronInput.value)
}

function applyCronToFriendlySchedule() {
  const checkCronInput = document.querySelector('#checkCron')
  const dailyCronInput = document.querySelector('#dailyCron')
  const hoursInput = document.querySelector('#checkEveryHours')
  const dailyTimeInput = document.querySelector('#dailySummaryTime')

  const parsedHours = parseCheckCronToHours(checkCronInput.value)
  if (parsedHours !== null) {
    hoursInput.value = String(parsedHours)
  }

  const parsedTime = parseDailyCronToTime(dailyCronInput.value)
  if (parsedTime !== null) {
    dailyTimeInput.value = parsedTime
  }

  setScheduleHint(checkCronInput.value, dailyCronInput.value)
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
    let detail = await response.text()
    try {
      const parsed = JSON.parse(detail)
      detail = parsed.detail || detail
    } catch {
      // Ignore non-json response and bubble raw text for operator diagnostics.
    }
    throw new Error(detail)
  }
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  return response.text()
}

async function loadSettings() {
  const s = await req('/api/settings')
  ensureTimezoneOption(s.timezone)
  document.querySelector('#timezone').value = s.timezone
  document.querySelector('#timezoneAuto').checked = Boolean(s.timezone_auto)
  document.querySelector('#checkCron').value = s.check_cron
  document.querySelector('#dailyCron').value = s.daily_summary_cron
  document.querySelector('#checkEveryHours').value = String(parseCheckCronToHours(s.check_cron) ?? 6)
  document.querySelector('#dailySummaryTime').value = parseDailyCronToTime(s.daily_summary_cron) ?? '21:00'
  document.querySelector('#webhookUrl').value = s.webhook_url
  document.querySelector('#webhookEnabled').checked = s.webhook_enabled
  document.querySelector('#rssEnabled').checked = s.rss_enabled

  document.querySelector('#kxoBaseUrl').value = s.kxo_base_url
  document.querySelector('#kxoUserAgent').value = s.kxo_user_agent

  applyTimezoneInputMode()
  setTimezoneHint(s.timezone, Boolean(s.timezone_auto))
  setScheduleHint(s.check_cron, s.daily_summary_cron)
  setKxoHint()
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

function renderCopySearchPager() {
  const pager = document.querySelector('#copySearchPager')
  pager.innerHTML = ''
  if (!copySearchKeyword) {
    return
  }

  const totalPages = Math.max(1, Math.ceil(copySearchTotal / SEARCH_PAGE_SIZE))
  const prevBtn = document.createElement('button')
  prevBtn.textContent = '上一页'
  prevBtn.disabled = copySearchPage <= 1
  prevBtn.addEventListener('click', () => {
    searchCopyManga(copySearchPage - 1).catch((err) => alert(err.message))
  })

  const nextBtn = document.createElement('button')
  nextBtn.textContent = '下一页'
  nextBtn.disabled = copySearchPage >= totalPages
  nextBtn.addEventListener('click', () => {
    searchCopyManga(copySearchPage + 1).catch((err) => alert(err.message))
  })

  const info = document.createElement('span')
  info.className = 'search-pager-info'
  info.textContent = `第 ${copySearchPage}/${totalPages} 页，共 ${copySearchTotal} 条`

  pager.appendChild(prevBtn)
  pager.appendChild(nextBtn)
  pager.appendChild(info)
}

function toCoverProxyUrl(cover) {
  const raw = typeof cover === 'string' ? cover.trim() : ''
  if (!raw) {
    return ''
  }
  if (!/^https?:\/\//i.test(raw)) {
    return raw
  }
  return `/api/cover-proxy?url=${encodeURIComponent(raw)}`
}

function buildCoverBlock({ cover, title, type }) {
  const isSearch = type === 'search'
  const coverClass = isSearch ? 'search-cover' : 'sub-cover'
  const emptyClass = isSearch ? 'search-cover search-cover-empty' : 'sub-cover sub-cover-empty'
  const src = toCoverProxyUrl(cover)
  if (!src) {
    return `<div class="${emptyClass}">无封面</div>`
  }
  return `
    <span class="cover-slot">
      <img class="${coverClass}" src="${src}" alt="${title}" loading="lazy" data-cover-fallback="1" />
      <div class="${emptyClass} cover-fallback" hidden>无封面</div>
    </span>
  `
}

function bindCoverFallback(root) {
  for (const img of root.querySelectorAll('img[data-cover-fallback="1"]')) {
    img.addEventListener('error', () => {
      img.style.display = 'none'
      const fallback = img.parentElement?.querySelector('.cover-fallback')
      if (fallback) {
        fallback.hidden = false
      }
    }, { once: true })
  }
}

async function searchCopyManga(page = 1) {
  if (page === 1) {
    copySearchKeyword = document.querySelector('#copySearchInput').value.trim()
  }
  if (!copySearchKeyword) {
    return
  }

  const data = await req(
    `/api/search?source=copymanga&q=${encodeURIComponent(copySearchKeyword)}&page=${page}`
  )

  copySearchPage = data.page
  copySearchTotal = data.total

  const table = document.querySelector('#copySearchTable tbody')
  table.innerHTML = ''

  for (const item of data.items) {
    const tr = document.createElement('tr')
    const coverCell = buildCoverBlock({
      cover: item.cover || '',
      title: item.title || '封面',
      type: 'search'
    })

    tr.innerHTML = `
      <td>${coverCell}</td>
      <td>
        <div class="search-title">${item.title}</div>
        <div class="search-author">作者：${item.author || '-'}</div>
        <div class="search-meta">${buildSearchMeta(item)}</div>
      </td>
      <td><button type="button">订阅</button></td>
    `

    tr.querySelector('button').addEventListener('click', async () => {
      await req('/api/subscriptions', {
        method: 'POST',
        body: JSON.stringify({
          source_code: 'copymanga',
          item_id: item.item_id,
          item_title: item.title,
          group_word: item.group_word || 'default',
          // Persist cover + metadata so subscription list can render richer state immediately.
          item_meta: {
            ...(item.meta || {}),
            cover: item.cover || '',
            group_word: item.group_word || 'default'
          }
        })
      })
      await loadSubscriptions()
      // Explicit success feedback avoids the "clicked but no response" confusion in subscribe flow.
      alert(`订阅成功：${item.title || item.item_id}`)
    })

    bindCoverFallback(tr)
    table.appendChild(tr)
  }

  renderCopySearchPager()
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

function buildSubscriptionCover(sub) {
  const cover = typeof sub?.item_meta?.cover === 'string' ? sub.item_meta.cover.trim() : ''
  return buildCoverBlock({
    cover,
    title: sub?.item_title || '封面',
    type: 'subscription'
  })
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
      <td>${buildSubscriptionCover(sub)}</td>
      <td>${sub.source_code}</td>
      <td>${sub.item_title}</td>
      <td>${sub.status}</td>
      <td>
        <div class="sub-last-seen-time">${seenTime}</div>
        <div class="sub-last-seen-title">${seenTitle}</div>
      </td>
      <td>
        <div class="row-actions">
          <button data-action="simulate" type="button">模拟更新</button>
          <button data-action="notify" type="button">测试通知</button>
          <button data-action="delete" type="button">删除</button>
        </div>
      </td>
    `

    tr.querySelector('[data-action="delete"]').addEventListener('click', async () => {
      await req(`/api/subscriptions/${sub.id}`, { method: 'DELETE' })
      await loadSubscriptions()
    })

    tr.querySelector('[data-action="simulate"]').addEventListener('click', async () => {
      const out = await req(`/api/subscriptions/${sub.id}/debug/simulate-update`, { method: 'POST' })
      alert(`已创建模拟事件，编号=${out.event_id}`)
      await loadEvents()
    })

    tr.querySelector('[data-action="notify"]').addEventListener('click', async () => {
      const out = await req(`/api/subscriptions/${sub.id}/debug/notify-test`, { method: 'POST' })
      const delivered = Array.isArray(out.delivered_channels) ? out.delivered_channels.join(',') : '-'
      const skipped = Array.isArray(out.skipped_channels) ? out.skipped_channels.join(',') : '-'
      alert(`通知测试状态=${out.status}\n已投递=${delivered}\n已跳过=${skipped}`)
    })

    bindCoverFallback(tr)
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

async function saveGeneralSettings() {
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

  await req('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
  await loadSettings()
  alert('通用设置已保存')
}

async function saveKxoSettings() {
  const payload = {
    kxo_base_url: document.querySelector('#kxoBaseUrl').value.trim(),
    kxo_user_agent: document.querySelector('#kxoUserAgent').value.trim(),
    // Force guest/manual-only runtime to avoid stale login-mode residues.
    kxo_auth_mode: 'guest',
    kxo_remember_session: false,
    kxo_cookie: ''
  }

  await req('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
  await loadSettings()
  alert('KXO 设置已保存')
}

async function addKxoManualSubscription() {
  const ref = document.querySelector('#kxoManualRef').value.trim()
  const itemTitle = document.querySelector('#kxoManualTitle').value.trim()
  if (!ref) {
    return
  }

  await req('/api/subscriptions/manual-kxo', {
    method: 'POST',
    body: JSON.stringify({
      ref,
      item_title: itemTitle || null
    })
  })

  document.querySelector('#kxoManualRef').value = ''
  document.querySelector('#kxoManualTitle').value = ''
  await loadSubscriptions()
}

async function testKxoSettings() {
  const out = await req('/api/settings/kxo/test', { method: 'POST' })
  alert(`KXO 测试状态=${out.status}\n${out.detail || ''}`)
}

for (const button of document.querySelectorAll('.tab-btn')) {
  button.addEventListener('click', () => {
    setActiveTab(button.dataset.tab)
  })
}

document.querySelector('#copySearchBtn').addEventListener('click', () => {
  searchCopyManga(1).catch((err) => alert(err.message))
})

document.querySelector('#refreshSubs').addEventListener('click', () => {
  loadSubscriptions().catch((err) => alert(err.message))
})

document.querySelector('#refreshEvents').addEventListener('click', () => {
  loadEvents().catch((err) => alert(err.message))
})

document.querySelector('#saveGeneralSettings').addEventListener('click', () => {
  saveGeneralSettings().catch((err) => alert(err.message))
})

document.querySelector('#saveKxoSettings').addEventListener('click', () => {
  saveKxoSettings().catch((err) => alert(err.message))
})

document.querySelector('#testKxoSettings').addEventListener('click', () => {
  testKxoSettings().catch((err) => alert(err.message))
})

document.querySelector('#addKxoManual').addEventListener('click', () => {
  addKxoManualSubscription().catch((err) => alert(err.message))
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

document.querySelector('#checkEveryHours').addEventListener('change', () => {
  applyFriendlyScheduleToCron()
})

document.querySelector('#dailySummaryTime').addEventListener('change', () => {
  applyFriendlyScheduleToCron()
})

document.querySelector('#checkCron').addEventListener('input', () => {
  applyCronToFriendlySchedule()
})

document.querySelector('#dailyCron').addEventListener('input', () => {
  applyCronToFriendlySchedule()
})

document.querySelector('#runCheck').addEventListener('click', async () => {
  const out = await req('/api/jobs/run-check', { method: 'POST' })
  alert(`检查完成：已扫描=${out.scanned}，发现更新=${out.discovered}`)
  await loadEvents()
  await loadSubscriptions()
})

document.querySelector('#runSummary').addEventListener('click', async () => {
  const out = await req('/api/jobs/run-daily-summary', { method: 'POST' })
  alert(`汇总状态=${out.status}`)
  await loadEvents()
})

async function bootstrap() {
  await loadTimezoneOptions()
  await Promise.all([loadSettings(), loadSubscriptions(), loadEvents()])
}

bootstrap().catch((err) => {
  console.error(err)
})

