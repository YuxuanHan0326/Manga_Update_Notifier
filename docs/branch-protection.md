# GitHub 分支保护配置（T-014）

本文用于手动完成仓库侧的分支保护设置，确保 CI 门禁真正生效。

## 目标
- 保护分支：`main`
- 必须通过的检查：
  - `backend`
  - `frontend`
  - `docker-smoke`

## 前置条件
- 仓库已启用 Actions。
- `.github/workflows/ci.yml` 已在默认分支生效。
- 你有仓库管理员权限。

## 配置步骤（Ruleset 推荐）
1. 打开 GitHub 仓库页面，进入 `Settings` -> `Rules` -> `Rulesets`。
2. 点击 `New ruleset`，选择 `New branch ruleset`。
3. `Ruleset Name` 填写：`protect-main`（可自定义）。
4. `Enforcement status` 选择 `Active`。
5. `Target branches` 选择 `Include default branch` 或显式填写 `main`。
6. 勾选 `Require a pull request before merging`。
7. 勾选 `Require status checks to pass`，并添加以下检查名：
   - `backend`
   - `frontend`
   - `docker-smoke`
8. 建议同时勾选：
   - `Require branches to be up to date before merging`
   - `Require conversation resolution before merging`
   - `Block force pushes`
   - `Block branch deletion`
9. 保存 ruleset。

## 验证步骤
1. 新建测试分支并提交一个故意失败的 PR（例如触发 lint 失败）。
2. 确认 PR 页面显示 required checks，且未通过时不能 merge。
3. 修复后再次推送，确认三个检查全绿后可合并。

## 备注
- 发布流程由 `release.yml` 在 tag 触发，不建议作为 PR required check。
- 安全扫描流程在 `security.yml`，建议保留为可见信号，但不强制阻塞主线交付（可按团队策略调整）。
