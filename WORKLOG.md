# Worklog

## Archive Summary
- Archive file: worklog_archive\WORKLOG_ARCHIVE_20260311_105834.md
- Reason: active WORKLOG.md exceeded 150 lines and was rotated per protocol.
- Key outcomes carried forward:
  - Completed subscription lifecycle v2 behavior: unsubscribe default pending-event cleanup, optional purge-history hard cleanup.
  - RSS and daily-summary candidate queries now include active subscriptions only.
  - Added regression tests and passed validation (`ruff`, `pytest 46 passed`).
  - Docker runtime verification passed (`compose up -d --build`, `compose ps`, `/api/health`).

## 2026-03-11

### 01. Worklog Rotation
- Archived previous long worklog to keep active execution memory concise.

### 02. Events Readability Bugfix (T-054)
- User reported Events panel remained noisy even when subscriptions were empty.
- Diagnosis confirmed:
  - RSS was already empty as expected.
  - `/api/events` still surfaced legacy debug/non-active history, causing operator confusion.
- Backend update:
  - `GET /api/events` now defaults to active-subscription + non-debug filters.
  - Added optional diagnostic flags: `include_debug=true`, `include_inactive=true`.
- Frontend update:
  - Added Events guide text to clarify default filtering and diagnostic query path.
- Tests/validation:
  - Added integration tests for default hide + opt-in show behavior.
  - `ruff` passed, `pytest` passed (`48 passed`).
  - Frontend lint/test/build passed (`npm test` executed in elevated mode due sandbox `spawn EPERM`).
  - Docker runtime verification passed (`compose up -d --build`, `compose ps`, `/api/health`).

### 03. Web UI 中文化（T-055）
- 用户要求网页文案避免中英文混用，仅保留必要专有名词英文。
- 实施范围：
  - `main.js`：页面标题、区块标题、按钮、表头、提示文案、弹窗提示中文化。
  - `utils.js`：事件状态文案改为 `未汇总 / 已汇总 / 已通知`。
  - `utils.test.js`：同步更新状态文案断言。
- 保留英文专有名词：
  - `CopyManga`、`KXO`、`RSS`、`Webhook`、`Cron`、`URL/IP`、API 参数名。
- 验证：
  - `ruff` 通过，`pytest 48 passed`。
  - 前端 `npm run lint/test/build` 通过（`npm test` elevated 运行，绕过 sandbox `EPERM`）。
  - Docker 运行验证通过（`compose up -d --build`、`compose ps`、`/api/health`）。

### 04. 新增中文乱码修复（T-056）
- 用户反馈：新加的中文文案出现乱码，旧文案正常；并要求主标题保留 `Manga_Update_Notifier`。
- 修复内容：
  - 修复前端页面模板中的新增中文文案乱码。
  - 主标题固定为 `Manga_Update_Notifier`（不做汉化）。
- 验证结果：
  - 前端校验通过：`npm run lint`、`npm run test`、`npm run build`。
  - Docker 重建启动通过：`cd platform && docker compose up -d --build`。
  - 容器状态正常：`docker compose ps` 显示 `Up`。
  - 健康检查通过：`GET /api/health` 返回 `{"status":"ok"}`。

### 05. 订阅成功反馈 + 标题文案调整（T-058）
- 用户需求：
  - 点击“订阅”成功后需要有明确反馈。
  - 主标题改为 `Manga Update Notifier`（不要下划线）。
- 前端实现（最小改动）：
  - `main.js` 将 `<h1>` 改为 `Manga Update Notifier`。
  - CopyManga 搜索结果“订阅”按钮成功回调中增加 `alert` 成功提示。
  - 补充一条调试注释，说明该反馈用于避免“点击后无响应”误判。
- 文档同步：
  - `README.md` 更新能力说明：订阅成功后会弹出提示。
- 验证：
  - 前端 `npm run lint/test/build` 全通过。
  - Docker 重建并启动通过：`compose up -d --build`。
  - 运行状态与健康检查通过：`compose ps`、`/api/health`。

### 06. RSS 去图片输出（T-060）
- 用户需求：RSS 无法稳定查看图片，希望直接不显示图片。
- 后端最小改动：
  - `rss.py` 移除 `media:thumbnail` 与 `enclosure` 输出逻辑。
  - 移除 `xmlns:media` 命名空间与相关图片 MIME 推断/URL 解析代码。
  - 保留文本友好结构：`title`、`description`、`content:encoded`。
- 测试与文档：
  - 更新集成测试断言：RSS 不再包含图片相关标签。
  - 更新 `README.md`：明确 RSS 当前为文本优先、无图片字段策略。
  - 记录决策 `D-035`，并注明覆盖 `D-032` 中图片字段部分。
- 验证：
  - 后端检查通过：`ruff`、`pytest 48 passed`。
  - Docker 验证通过：`compose up -d --build`、`compose ps`、`/api/health`。
  - 运行态 RSS 校验：未检测到 `media:thumbnail` / `enclosure` / `xmlns:media`。
