---
name: "pypi-publisher"
description: "PyPI 包发布与版本管理 CLI（build/publish/check/bump/release，token 存 .env）。当用户要求发布 Python 包到 PyPI、升级包版本、查询 PyPI 包名/版本时调用。"
---

# pypi-publisher — PyPI 包发布与版本管理

## 核心概念

Python 包（如 `packages/mongo-store-py`）→ 构建 wheel → twine 发布到公共 PyPI。token 存本目录 [.env](.env)（`PYPI_TOKEN`），**严禁写入代码/文档/命令行/提交入库**。

## 调用方式（stdin JSON，禁止散参数）

```powershell
'{"cmd":"check","package":"mongo-store"}' | python .trae/skills/pypi-publisher/pypi_publisher.py
```

含中文/引号的 JSON：先用 `Write` 写到 `tmp/_args.json`（UTF-8），执行后立即 `DeleteFile` 删除（见 cli-args-rules）。

## 命令一览

| cmd | 参数 | 作用 |
|-----|------|------|
| `check` | `package` | 查询 PyPI 上包是否存在及已有版本（404=包名可用） |
| `build` | `pkg_dir` | `python -m build --wheel` 构建最新 wheel |
| `publish` | `pkg_dir` | twine 上传 dist 下最新 wheel（token 走环境变量，不进命令行） |
| `bump` | `pkg_dir`, `part`=patch/minor/major | 升 `pyproject.toml` 里的 version |
| `release` | `pkg_dir`, `part` | bump + build + publish 一条龙 |

## 标准发版流程

```powershell
# 0. 源码在 GitHub（本地工作区不留副本）：先 clone 到临时目录再改代码
git clone https://github.com/coenddt/mongo-store tmp/mongo-store

# 1. 改完代码、自检通过后，一条龙发新版本（默认 patch）
'{"cmd":"release","pkg_dir":"tmp/mongo-store","part":"patch"}' | python .trae/skills/pypi-publisher/pypi_publisher.py

# 2. 确认 PyPI 已收录（约 1~2 分钟同步）
'{"cmd":"check","package":"mongo-store"}' | python .trae/skills/pypi-publisher/pypi_publisher.py
```

## 注意事项

- 发布前必须先跑完该包的自检（模块加载 + 相关单测）
- 版本号语义化：bug 修复 patch、新功能 minor、破坏性改动 major
- PyPI 发布后**不可删除同名版本**，发错只能发更高版本覆盖语义
- `dist/` 已被 .gitignore 忽略，wheel 不入库（可随时重建）
- 依赖工具首次使用自动提示安装：`pip install build twine`
