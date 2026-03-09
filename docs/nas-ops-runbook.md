# NAS 运维 Runbook（Phase 1）

本文覆盖本项目在 NAS 上的基础运维动作：部署、升级、回滚、排障与安全基线。

## 1. 部署与启动
在仓库根目录执行：

```powershell
cd platform
docker compose up -d --build
```

检查容器状态：

```powershell
cd platform
docker compose ps
```

基础健康检查：

```powershell
curl http://localhost:8000/api/health
```

## 2. 常规运维动作
手动执行一次更新检测：

```powershell
curl -X POST http://localhost:8000/api/jobs/run-check
```

手动执行一次日报汇总：

```powershell
curl -X POST http://localhost:8000/api/jobs/run-daily-summary
```

查看最近日志：

```powershell
cd platform
docker compose logs --tail=200 app
```

## 3. 版本升级
1. 拉取新代码（含 `platform/` 和 `.github/workflows/`）。
2. 备份 `platform/data/`（至少备份 SQLite 数据库）。
3. 执行：

```powershell
cd platform
docker compose down
docker compose up -d --build
```

4. 检查：
   - `/api/health` 是否正常。
   - `/api/search` 是否返回结果。
   - `/api/notifications/rss.xml` 是否可访问。

## 4. 快速回滚
当新版本异常时：
1. 切回上一个已知稳定 tag/commit。
2. 在该版本代码目录重新构建并启动：

```powershell
cd platform
docker compose down
docker compose up -d --build
```

3. 使用备份数据库恢复（若存在数据结构不兼容）。

## 5. 时区与计划任务操作
默认值：
- `timezone`: `Asia/Shanghai`
- `check_cron`: `0 */6 * * *`
- `daily_summary_cron`: `0 21 * * *`

可在 Web UI 的 `Schedules & Settings` 修改，也可通过 API：

```powershell
curl -X PUT http://localhost:8000/api/settings ^
  -H "Content-Type: application/json" ^
  -d "{\"timezone\":\"Asia/Shanghai\",\"check_cron\":\"0 */6 * * *\",\"daily_summary_cron\":\"0 21 * * *\"}"
```

修改后建议立即手动执行一次 `run-check` 和 `run-daily-summary` 验证。

## 6. 反向代理与鉴权基线
Phase 1 不内建重型登录，请在 NAS 反向代理层启用访问控制：
- 至少启用 Basic Auth / SSO 之一。
- 强制 HTTPS。
- 限制公网暴露范围（尽量仅内网或 VPN 可访问）。

建议最少暴露路径：
- `/`（Web UI）
- `/api/*`（管理与任务接口）

## 7. 常见故障排查
1. 搜索报 upstream/source error：
   - 先检查容器日志是否出现上游反爬页面返回。
   - 稍后重试，必要时降低频率。
2. 无日报通知：
   - 检查 `webhook_enabled` 与 `webhook_url` 配置。
   - 手动调用 `/api/notifications/webhook/test` 验证链路。
3. RSS 无更新：
   - 检查是否存在新的 `events`。
   - 确认 `rss_enabled` 未关闭。

## 8. 值班交接最小清单
- 当前运行版本（commit/tag）
- 最近一次成功 `run-check` 时间
- 最近一次成功 `run-daily-summary` 时间
- 当前 webhook 健康状态
- 已知风险（如上游反爬波动）

## 9. 公开仓库协作提醒
- 对外协作前请先阅读根目录 `CONTRIBUTING.md` 与 `SECURITY.md`。
- 运维截图、日志脱敏后再公开，避免泄露内网地址、Webhook 地址或认证信息。
