# 贡献指南（Contributing）

感谢你参与 `Manga Update Notifier`。

## 1. 基本原则
- 先最小改动，再考虑重构。
- 不擅自扩大需求，所有实现需映射到 `REQUIREMENTS.md`。
- 新决策必须写入 `DECISIONS.md` 并说明原因。
- 每轮实现必须同步维护 `README.md`、`.gitignore`，并按需更新 `docs/`。
- 代码变更必须补充有价值的调试/维护注释，避免无信息注释。

## 2. 开发前必读
请先阅读并遵守以下文件：
- `PROJECT_BRIEF.md`
- `REQUIREMENTS.md`
- `ARCHITECTURE.md`
- `DECISIONS.md`
- `TASKS.md`
- `STATE.md`
- `NEXT_STEP.md`
- `WORKLOG.md`
- `PROMPT_TEMPLATE.md`

## 3. 本地开发
后端：
```powershell
python -m pip install -r platform/backend/requirements.txt -r platform/backend/requirements-dev.txt
$env:PYTHONPATH="platform/backend"
uvicorn app.main:app --reload --port 8000
```

前端：
```powershell
cd platform/frontend
corepack enable
pnpm install
pnpm dev
```

## 4. 提交前检查
在仓库根目录执行：
```powershell
make ci-backend
make ci-frontend
make ci-integration
make ci-build
```

若本次改动触及程序本体，还需做 Docker 运行验证：
```powershell
cd platform
docker compose up -d --build
docker compose ps
curl http://localhost:8000/api/health
```

## 5. 文档与台账要求
- `TASKS.md`：开始实现前创建 `IN_PROGRESS` 任务。
- `WORKLOG.md`：记录关键步骤；超过 150 行时按协议自动归档。
- `STATE.md`：更新当前状态、风险、下一步。
- `NEXT_STEP.md`：记录接力点与阻塞。

## 6. 安全与隐私
- 不要提交真实密钥、令牌、Webhook 地址。
- 不要提交 `platform/data/` 运行数据与本地数据库。
- 对外发布前请阅读 `SECURITY.md`。
