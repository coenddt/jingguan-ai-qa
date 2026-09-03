# artwork-first-mile — 原始作品盘点入册 CLI（第一公里）

## 触发
- 画家交来一批原始作品图（如 `原始作品/` 下的哈希文件名图片），需要盘点、去重、编号归位到 `投递文件夹/` 并登记 `作品清单.csv` 时
- 本 skill 只做"原始作品 → 作品清单/投递文件夹"，落库交给 `gallery-ingest`

## 用法（两段式，参数一律走 --params-file）
```bash
PY=server-py/.venv/Scripts/python.exe
CLI=.trae/skills/artwork-first-mile/first-mile.py

# ① 盘点：tmp/_args.json = { "action": "scan", "out": "tmp/first-mile-scan.json" }
$PY $CLI --params-file tmp/_args.json
```
2. AI 查看盘点报告 + 用 Read 看图，产出 plan（写 `tmp/_plan.json`）：
   - 初拟系列归属与暂拟标题（画家命名后在小程序管理区覆盖）；题材判断可参考画面内容
   - 编号规则 `GYY-<系列号>-<序号>`，从报告 `occupiedNos` 之外取号；新系列登记进 `series`
```json
{ "series": [{ "seq": 6, "name": "窗边与屋" }],
  "items": [{ "file": "XXXX.png", "seq": 6, "no": 1, "title": "暂拟标题" }] }
```
```bash
# ② 归位：tmp/_args.json = { "action": "apply", "plan": "tmp/_plan.json", "out": "tmp/first-mile-report.json" }
$PY $CLI --params-file tmp/_args.json
```
3. 之后用 `gallery-ingest` 扫描 `投递文件夹/` 落库

## 可选参数（params-file 内）
- `src`（默认 `原始作品`）、`deliver`（默认 `投递文件夹`）、`csv`（默认 `作品清单/作品清单.csv`）
- 绝对/相对路径均可；测试时指向 tmp 沙箱目录即可，不碰真实目录

## 行为
- **scan**：md5 内容去重（批内重复 + 与投递文件夹已投递比对）、Pillow 长边质检（<2000px 记低清）、已占编号与系列登记汇总
- **apply**：校验编号占用/系列登记 → 复制原图到 `投递文件夹/<系列号>-<系列名>/GYY-<系列号>-<序号>[_<标题>].<ext>`（**只复制不移动原件**）→ 新增行插入 CSV 数据区、新系列追加到 `### 系列登记 ###` 区 → 输出归位报告
- 标题非法字符自动剔除；标题为空落"（待命名）"，状态列填"待归档"

## 铁律
- 暂拟标题与"感悟"均为 AI/策展初拟，画家命名后直接覆盖
- **AI 禁止代写画家的文字想法**：不生成同名 .txt 骨架，想法文字必须本人提供（原文照录禁改写）
- 原件不动：apply 只复制，`原始作品/` 保持原样作归档底稿

## 临时文件清理（强制）
- `tmp/_args.json`、`tmp/_plan.json` 与报告文件用完立即删除，禁止跨任务遗留
