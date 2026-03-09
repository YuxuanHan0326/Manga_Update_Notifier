# Manga Update Notifier（NAS 漫画更新通知平台）

这是一个面向 NAS 的自托管项目。当前主实现位于 `platform/`，目标是提供“多源可扩展的更新检测 + 每日汇总通知 + Web 管理界面”。

## 当前能力（Phase 1）
- 首站支持：`CopyManga`
- 已实现：搜索、订阅、定时检查、每日汇总、Webhook 通知、RSS 输出
- 搜索结果支持：封面、分页、最后更新时间、最新话
- 设置支持：`Timezone Auto (by IP)` 自动时区（失败时回退默认时区）+ 手动时区下拉选择
- 订阅列表支持：显示上次获取时间与上次最新话标题（Last Seen）
- 新增订阅支持：从搜索元信息预填充 Last Seen（无需等待首次检查）
- 订阅调试支持：
  - `Test Notify`：强制触发一次通知测试
  - `Sim Update`：模拟抓到更新（仅调试，不参与当日自动汇总推送）
- 日报策略：基于“未汇总的真实更新”发送，支持停机跨天恢复后补发，避免漏推送

## 通知渠道
当前支持的通知渠道：
- `Webhook`（主动推送）
- `RSS`（拉取订阅）

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

搜索接口示例：

```powershell
curl "http://localhost:8000/api/search?source=copymanga&q=one&page=1"
```

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
