# Manga Update Notifier（NAS 漫画更新通知平台）

这是一个面向 NAS 的自托管项目。当前主实现位于 `platform/`，目标是提供“多源可扩展的更新检测 + 每日汇总通知 + Web 管理界面”。

## 当前能力（Phase 1）
- 已支持源：`CopyManga`、`KXO(kzo/kxo)`
- 已实现：搜索、订阅、定时检查、每日汇总、Webhook 通知、RSS 输出
- 搜索结果支持：封面、分页、最后更新时间、最新话
- CopyManga 搜索结果点击“订阅”后会弹出成功提示，便于确认操作已完成
- Web UI 已按管理场景拆分为三个页签：`General`、`CopyManga`、`KXO`
  - `General`：订阅列表、调度/通用通知配置、事件列表
  - `CopyManga`：CopyManga 搜索与一键订阅
  - `KXO`：KXO manual URL/ID 订阅、KXO 专属配置
- 页面文案已完成中文化（保留 CopyManga、KXO、RSS、Webhook、Cron 等必要专有名词）。
- KXO 当前策略：仅支持 `manual subscription`
  - 支持手动 URL/ID 添加订阅 + 更新检测
  - 不提供站内搜索
  - 不提供账号密码登录入口
- 设置支持：`Timezone Auto (by IP)` 自动时区（失败时回退默认时区）+ 手动时区下拉选择
- 排程设置支持：友好模式（每几小时检查、每日推送时间）+ Advanced Cron 兼容模式
- 订阅列表支持：显示上次获取时间与上次最新话标题（Last Seen）
- 历史数据中若存在 UTF-8/Latin-1 混淆导致的中文乱码，API 与通知输出会自动做安全修复显示
- 订阅列表支持：对历史“无封面”订阅进行读取时自动回填（若源站可提取到封面）
- 订阅封面加载策略：优先通过应用内封面代理加载，降低外链防盗链/跨域策略导致的渲染失败
  - KXO 封面 CDN（`mxomo`）已增加兼容请求策略，避免代理链路下的 403 拒绝
- 新增订阅支持：从搜索元信息预填充 Last Seen（无需等待首次检查）
- 订阅调试支持：
  - `Test Notify`：强制触发一次通知测试
  - `Sim Update`：模拟抓到更新（仅调试，不参与当日自动汇总推送）
- 日报策略：基于“未汇总的真实更新”发送，支持停机跨天恢复后补发，避免漏推送
- 订阅生命周期策略：
  - 取消订阅默认会删除该订阅下“未汇总事件”，避免后续继续触发汇总
  - 如需彻底清理历史，可在删除接口使用 `purge_history=true` 一并删除已汇总事件
  - RSS 与自动日报仅处理“当前仍为 active 的订阅”事件，不展示/汇总已暂停或已取消订阅的残留事件
- Events 列表默认仅展示“active 订阅 + 非 debug”事件，避免历史残留和调试噪声干扰

## 通知渠道
当前支持的通知渠道：
- `Webhook`（主动推送）
- `RSS`（拉取订阅）

### Webhook 结构（v2，已替换旧版）
- 当前 webhook payload 为统一 v2 结构（旧版已移除）：
  - 顶层：`schema_version`、`event_type`、`generated_at`、`timezone`、`title`、`window_start`、`window_end`、`count`、`summary`、`events`
  - `events[*]`：
    - `subscription`：`item_id`、`item_title`、`cover`、`source_item_url`
    - `update`：`update_id`、`update_title`、`update_url`、`detected_at`、`detected_at_local`、`dedupe_key`
- 适用场景：
  - n8n / 自建下游可直接按 `subscription.item_title`、`update.update_title` 等字段做模板化邮件/消息拼接，无需再查库。

### RSS 输出（阅读器友好）
- `RSS` 已改为“可直接阅读”的文本描述（旧版简陋描述已移除）：
  - `item.title`：`作品名 · 最新话`
  - `item.description`：短摘要（来源、时间、章节链接），保证列表视图不拥挤
  - `content:encoded`：详细文本（作品、最新更新、来源、时间、章节链接、作品页）
- 当前策略：RSS 不输出封面媒体字段（`media:thumbnail`/`enclosure`），只保留文本信息，提升阅读器兼容性
- 用户在 RSS 阅读器中可直接阅读关键信息，不需要解析内部 JSON 字段。
- CopyManga 链接安全修复：
  - RSS/Webhook 中的 CopyManga 作品/章节链接统一规范到官方域名 `https://www.mangacopy.com`
  - 历史遗留的 `copymanga.site` 链接会在输出时自动改写，避免下游读取到错误站点

## 快速启动（Docker）
在仓库根目录执行：

```powershell
cd platform
# 可选：先复制环境变量模板并按需修改
# copy .env.example .env
docker compose up -d --build
```

启动后访问：
- Web UI：`http://<你的NAS-IP>:8000`
- 健康检查：`http://<你的NAS-IP>:8000/api/health`
- RSS：`http://<你的NAS-IP>:8000/api/notifications/rss.xml`

停止服务：

```powershell
cd platform
docker compose down
```

## 常用手动操作
手动触发更新检查：

```powershell
curl -X POST http://localhost:8000/api/jobs/run-check
```

手动触发日报汇总：

```powershell
curl -X POST http://localhost:8000/api/jobs/run-daily-summary
```

删除订阅（默认仅清理未汇总事件）：

```powershell
curl -X DELETE "http://localhost:8000/api/subscriptions/<SUB_ID>"
```

删除订阅并彻底清理历史事件：

```powershell
curl -X DELETE "http://localhost:8000/api/subscriptions/<SUB_ID>?purge_history=true"
```

查看 Events（默认过滤 debug 与非 active）：

```powershell
curl "http://localhost:8000/api/events?status=all"
```

查看包含调试与非 active 的 Events（排障模式）：

```powershell
curl "http://localhost:8000/api/events?status=all&include_debug=true&include_inactive=true"
```

搜索接口示例：

```powershell
curl "http://localhost:8000/api/search?source=copymanga&q=one&page=1"
```

KXO 手动添加订阅（URL/ID）示例：

```powershell
curl -X POST http://localhost:8000/api/subscriptions/manual-kxo `
  -H "Content-Type: application/json" `
  -d "{\"ref\":\"https://kzo.moe/c/20001.htm\"}"
```

## 常见问题排查
- 页面中文显示乱码：
  - 先执行浏览器硬刷新（`Ctrl + F5`）清理旧前端缓存。
  - 确认容器已重建到最新前端资源：`cd platform && docker compose up -d --build`。
  - 若仍异常，请打开浏览器开发者工具，确认 `index-*.js` 为最新构建版本并反馈具体乱码文本位置。

## 关键目录
- `platform/backend/`：后端 API、调度器、适配器、通知模块
- `platform/frontend/`：前端 Web UI
- `platform/tests/`：单元与集成测试
- `.github/workflows/`：CI/CD 工作流
- `docs/`：运维与仓库治理文档
- `PROJECT_BRIEF.md` / `REQUIREMENTS.md` / `ARCHITECTURE.md` / `DECISIONS.md`：项目长期记忆

## 运维与治理文档
- 分支保护配置：[`docs/branch-protection.md`](docs/branch-protection.md)
- NAS 运维 Runbook：[`docs/nas-ops-runbook.md`](docs/nas-ops-runbook.md)
- 开发协作规范：[`CONTRIBUTING.md`](CONTRIBUTING.md)
- 安全策略与漏洞上报：[`SECURITY.md`](SECURITY.md)

## 安全检查（GitHub Actions）
- 工作流：`.github/workflows/security.yml`
- 触发方式：
  - `pull_request`（`main`）
  - `push`（`main`）
  - `schedule`（每天 02:00 UTC）
  - `workflow_dispatch`（手动触发）
- 当前包含四类检查：
  - `dependency-review`：PR 增量依赖门禁（`high` 及以上阻断）
  - `python-audit`：`pip-audit` 扫描后端依赖漏洞（保留 `--strict`）
  - `frontend-audit`：`pnpm audit --prod --audit-level high` 扫描前端生产依赖漏洞
  - `trivy-image`：构建镜像后使用 Trivy 扫描镜像 `HIGH/CRITICAL` 漏洞并上传 SARIF artifact
- 稳定性增强（不降低安全门槛）：
  - 安装依赖步骤增加短重试，降低 runner 临时网络抖动导致的误失败
  - Trivy 改用 GHCR 镜像与缓存目录，减少拉取限流/冷启动抖动
  - 所有安全 job 增加 `timeout`，避免挂起占用 runner

## 核心配置（环境变量）
通过 `platform/docker-compose.yml` 传入：
- `MUP_DATABASE_URL`：数据库连接（默认 SQLite）
- `MUP_APP_TIMEZONE`：默认回退时区（默认 `Asia/Shanghai`）
- `MUP_TIMEZONE_AUTO`：是否启用按 IP 自动时区（默认 `true`）
- `MUP_IP_TIMEZONE_API_URL_TEMPLATE`：IP 时区查询地址模板（默认 `https://ipapi.co/{ip}/json/`）
- `MUP_IP_TIMEZONE_SELF_API_URL`：当请求 IP 为内网地址或直查失败时，使用服务端公网出口自动识别时区的查询地址（默认 `https://ipapi.co/json/`）
- `MUP_IP_TIMEZONE_TIMEOUT_SEC`：IP 时区查询超时秒数（默认 `5.0`）
- `MUP_CHECK_CRON`：检查任务 cron
- `MUP_DAILY_SUMMARY_CRON`：日报任务 cron
- `MUP_WEBHOOK_URL`：Webhook 地址
- `MUP_CM_API_BASE_URL`：CopyManga API 基地址
- `MUP_KXO_BASE_URL`：KXO 基地址（默认 `https://kzo.moe`）
- `MUP_KXO_AUTH_MODE`：KXO 认证模式（当前建议固定 `guest`）
- `MUP_KXO_COOKIE`：历史兼容字段（manual-only 模式下不需要）
- `MUP_KXO_USER_AGENT`：KXO 请求 UA
- `MUP_KXO_REMEMBER_SESSION`：历史兼容字段（manual-only 模式下不需要）

说明：
- KXO 已收敛为 manual-only 路径，站内搜索与凭证登录链路已移除。

可参考模板：`platform/.env.example`

## 项目开发
本项目100%采用AI开发（Codex），也建议后续工作继续使用AI开发
请使用PROMPT_TEMPLATE.md进行prompt，AI会自动读取repo内的.md记忆文件并重建上下文

## 公开仓库说明
- 本仓库默认可作为公开仓库使用，提交前请确认未包含任何私密配置（如真实 webhook 地址、令牌、内网拓扑信息）。
- 运行数据（`platform/data/`、数据库、日志）已在 `.gitignore` 中排除，不应提交。
- 若你要参与开发，请先阅读 `CONTRIBUTING.md`，按约定维护记忆文档、README 与调试注释。

## 许可证
本项目采用 `GNU General Public License v3.0 (GPLv3)`。详见根目录 [`LICENSE`](LICENSE)。
