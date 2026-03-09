开始前请先读取并以记忆文件为准：
- PROJECT_BRIEF.md
- REQUIREMENTS.md
- ARCHITECTURE.md
- DECISIONS.md
- TASKS.md
- STATE.md
- NEXT_STEP.md
- WORKLOG.md

先不要直接改代码。先输出：
1. 你理解的本次任务
2. 本次涉及的范围
3. 本次不应改动的部分
4. 相关硬约束
5. 可能受影响的文件
6. 是否与已有决策冲突

先在 `TASKS.md` 创建 `IN_PROGRESS` task，然后再改代码

本次目标：
[写你的目标]

本次范围：
[写允许动的部分]

本次不做：
[写禁止扩展的部分]

实现要求：
- 先按最小改动原则实现
- 不擅自扩大需求
- 不重写无关模块
- 所有实现必须映射到 REQUIREMENTS.md
- 如需做新决策，先说明理由并写入 DECISIONS.md
- 每次更新必须同步维护 `README.md` 与 `.gitignore`
- 每次改动后按需同步维护相关 docs（如 `docs/` 下运维/治理文档）
- 每次实现功能或修复代码时，必须补充“便于开发与调试”的合适注释（避免无信息注释）
- `README.md` 必须使用准确中文，内容聚焦用户真正需要的信息（启动、配置、使用、排障入口）
- 每次完成一次改动后，默认执行一次 Docker 构建并启动，默认命令：
  - `cd platform && docker compose up -d --build`
  - 并反馈容器状态与健康检查结果（如 `docker compose ps`、`/api/health`）
- Docker 验证例外：
  - 若本次修改未触碰程序本体（例如仅修改 `README.md`、`PROMPT_TEMPLATE.md`、台账文档等），可跳过 Docker build
  - 若只是在解释问题、未执行新任务或未改任何文件，可跳过 Docker build
- 当 `WORKLOG.md` 超过 150 行时，必须自动执行归档轮转：
  - 将旧 `WORKLOG.md` 复制到 `worklog_archive/WORKLOG_ARCHIVE_<timestamp>.md`
  - 重新创建一个简短的新 `WORKLOG.md`
  - 新 `WORKLOG.md` 开头必须包含对归档文件关键内容的简洁总结

本轮结束后必须输出：
1. 已完成内容
2. 修改了哪些文件
3. 覆盖了哪些需求
4. 当前还未完成什么
5. 下一步具体接力点

记忆文件更新规则：
- 如果用户只是要求解释、建议等，不包含新的实现任务，则本轮结束无需更新记忆文件（由代理自行判断）
- 如果存在实际任务实现或协议变更，按需更新 `NEXT_STEP.md`、`WORKLOG.md`、`TASKS.md`、`STATE.md`，并在需要时更新 `DECISIONS.md`、`ARCHITECTURE.md`
- 若出现有必要更新 `REQUIREMENTS.md`、`PROJECT_BRIEF.md` 的情况，请先和开发者报告修改计划，获得批准后才可以编辑
