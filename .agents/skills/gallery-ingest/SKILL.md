---
name: "gallery-ingest"
description: "投递文件夹落库 CLI：画家往投递文件夹放入新作品资料（作品图+文字想法），需要扫描落库 MongoDB 并输出检验报告时调用。"
---

# gallery-ingest — 投递文件夹落库 CLI

## 触发
- 画家往 `投递文件夹/` 扔了新作品资料（作品图 + 文字想法），需要扫描落库并出检验报告时

## 用法
```bash
# 推荐：参数文件方式（见 cli-args-rules）
# tmp/_args.json: { "dir": "投递文件夹", "out": "tmp/ingest-report.json" }
server-py/.venv/Scripts/python.exe .agents/skills/gallery-ingest/gallery-ingest.py --params-file tmp/_args.json

# 或直接传参
server-py/.venv/Scripts/python.exe .agents/skills/gallery-ingest/gallery-ingest.py --dir 投递文件夹 --out tmp/ingest-report.json
```

## 前置条件
- `.env`（本目录）：`MONGODB_URI` 指向**线上库**（SSH 隧道 + directConnection）；同文件含 `GALLERY_AGENT_KEY`（AI 远程调 agent REST 用，2027-08-30 到期需轮换）
- 先起 SSH 隧道再执行：`ssh -N -L 27018:127.0.0.1:27017 coen-user@<SERVER_IP>`（跑完可停）
- `server-py/.venv` 已安装依赖（pymongo、Pillow，见 `server-py/requirements.txt`）
- 数据层/图片处理直接复用 `server-py/` 的 `db.store` 与 `utils.file_store`（脚本自动注入 sys.path）

## 输入约定（见《投递文件夹规范》）
- 系列目录：`<系列号>-<系列名>`，如 `01-桥下河滩`
- 作品图：`GYY-<系列号>-<序号>_<标题>.jpg`；采风实景照加 `_实景` 后缀
- 文字想法：与作品图同名的 `.txt`（UTF-8，原样照录禁改写）；docx 暂不解析，报告中提示转存

## 行为
1. 按系列目录 upsert Series（按 seq）
2. 每张图落一条 Artwork：artworkNo 去重（重复跳过）、storyText 原文照录、命名不符 → `status=pending_title`
3. Pillow 生成 original/watermark(1280)/thumb(480) 存 `server-py/data/`；实景照压为 1280 JPEG；长边 <2000px 记入低清清单
4. 输出检验报告 JSON（缺文字/待命名/低清/docx 待转）+ 控制台摘要

## 临时文件清理（强制）
- `tmp/_args.json` 与报告文件用完立即删除，禁止跨任务遗留
