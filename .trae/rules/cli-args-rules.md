---
alwaysApply: false
description: 调用 .trae/skills 下 CLI 工具（ssh-server-task 等）传参执行时必读
---

# 命令规则（按需读取）
- **CLI 工具传参一律用参数文件（最稳妥）**：CLI 支持 JSON 传参时，批量传参先用 `Write` 工具把 JSON 写入临时文件（如 `tmp/_args.json`，项目根 `tmp/` 已 gitignore，**禁止写项目根目录本体**，UTF-8），执行后**用完立即删除**临时文件（用 `DeleteFile`），收尾复查无残留。
- 避免 PowerShell 引号剥离与中文编码问题：含中文/引号的命令行参数优先在 **Git Bash** 用单引号内联或 heredoc 传参。
- **临时参数文件位置与清理（强制）**：临时参数文件统一写在项目根 `tmp/` 目录；每次命令执行完成后立即删除该临时文件，禁止跨任务遗留。
- 服务器操作前先读 `deploy-rules`：目标账号 `<user>@<SERVER_IP>`，同机其他项目账号（coen-user / ecs-user，及本项目已停用的旧账号 sattc）严禁误碰。
