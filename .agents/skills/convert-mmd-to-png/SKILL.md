---
name: "convert-mmd-to-png"
description: "Converts Mermaid (.mmd) diagrams to PNG images. Invoke when user needs to convert .mmd files to PNG, batch process Mermaid diagrams, or update document images."
---

# Convert MMD to PNG

用 `mmdc`（Mermaid CLI）将 `.mmd` 文件转为高分辨率 PNG。

**前置**：Node.js + `npm install -g @mermaid-js/mermaid-cli`

**目录**：`doc/design/boss-report/mmd/` → `doc/design/boss-report/png/`

## 单文件转换

统一在 **Git Bash** 终端执行：

```bash
npx -p @mermaid-js/mermaid-cli mmdc \
  -i doc/design/boss-report/mmd/system-architecture.mmd \
  -o doc/design/boss-report/png/system-architecture.png \
  -w 1440 -H 1080  # 宽高（像素）
```

## 批量转换

```bash
for f in doc/design/boss-report/mmd/*.mmd; do
  npx -p @mermaid-js/mermaid-cli mmdc \
    -i "$f" \
    -o "doc/design/boss-report/png/$(basename "$f" .mmd).png"
done
```

## 参数速查

| 参数 | 作用 |
|------|------|
| `-i <path>` | 输入 .mmd 文件路径 |
| `-o <path>` | 输出 PNG 文件路径 |
| `-w <number>` | PNG 宽度（像素） |
| `-H <number>` | PNG 高度（像素） |
| `-b transparent` | 透明背景 |
| `-t neutral` | 中性主题 |

## 禁止事项

❌ 不要手动截图替代（清晰度不一致）  
❌ 不要用 `###` 及以上层级标题  

## 注意事项

1. 首次使用先 `npm install -g @mermaid-js/mermaid-cli` 安装
2. 宽高建议 1440×1080 以上，保证嵌入文档时清晰
3. 输入输出目录需事先存在，`mmdc` 不会自动创建
