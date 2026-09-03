---
name: "user-guide-creator"
description: "创建面向普通用户的操作指南文档，以操作示例为核心，存入 doc/user-guide/YYYY/MM/ 目录。当用户要求编写用户操作指南、操作文档、使用说明、用户手册时调用。"
---

# 用户操作指南创建器

## 核心概念

**操作示例即文档主体**——不说技术细节，只说"在哪里点、填什么、看到什么"。存放路径：`doc/user-guide/<YYYY>/<MM>/<功能名称>.md`

## 与 design-doc-creator 的区别

| 维度 | design-doc-creator | user-guide-creator |
|------|-------------------|-------------------|
| 读者 | 开发者/技术决策者 | **普通用户**（非技术人员） |
| 内容 | 概念设计、数据模型、技术方案 | **操作示例**、具体操作场景 |
| 语言 | 技术术语 | 用户视角白话 |
| 存放路径 | `doc/design/` | `doc/user-guide/` |

## 文档模板

```markdown
# <功能名称> — 使用指南

## 概述

一两句话说明功能是什么、什么场景下用。不涉及技术实现。

## 操作示例

> 核心：每个示例是一个完整操作场景，用户照着做就能完成。

### <示例一：基础场景>

**场景**：谁在什么情况下使用。

**操作**：
1. 在哪里点击什么
2. 填写/选择什么内容
3. 观察什么结果

> **效果**：操作完成后用户会看到什么。

### <示例二：进阶场景>

（同上结构，覆盖所有常见场景）

## 附录

### 配置项说明
| 配置项 | 说明 | 可选值 | 默认值 |

### 注意事项
- 边界情况说明
- 常见踩坑点

### FAQ
**Q：xxx 为什么不生效？**
A：请检查 xxx。
```

## 编写原则

1. **示例优先**：操作示例是文档主体，配置说明放附录
2. **以例代步骤**：一个示例就是一个完整场景，无需单独步骤章节
3. **全覆盖**：覆盖基础、进阶、边界等所有常见场景
4. **用户视角**：不说后端、接口、数据结构
5. **效果可见**：每个示例末尾说明用户看到的效果
6. **配图优先**：真实截图效果远好于纯文字，截图存 `doc/user-guide/<YYYY>/<MM>/images/`

## Playwright 实景截图

> 适用场景：CMS 编辑器、拖拽式页面搭建、可视化配置后台等需要在运行界面中展示操作步骤时。

### 实现原理

```
Playwright 脚本 → 启动浏览器 → 加载编辑器页面 → 拦截 API 返回 mock 数据 → 编辑器渲染 → 截图保存
```

### 脚本模板

```javascript
import { chromium } from 'playwright';
import path from 'path';

const BASE_URL = 'http://localhost:<PORT>';
const IMG_DIR = 'doc/user-guide/<YYYY>/<MM>/images';

// 组件配置：名称、描述、点击 ID
const COMPONENT_CONFIGS = [
  { name: "编辑器全景", desc: "编辑器完整界面", clickId: null },
  { name: "组件A", desc: "组件A说明", clickId: "node-comp-a" },
];

// Craft.js Mock State — resolvedName 必须与项目 resolver 完全一致！
function createMockCraftState() {
  return {
    ROOT: {
      type: { resolvedName: "PageContainer" },  // 通常用 PageContainer
      isCanvas: true,
      props: { /* ... */ },
      displayName: "Root",
      nodes: ["node-comp-a"],
    },
    "node-comp-a": {
      type: { resolvedName: "正确的Resolver名称" },  // ⚠ 必须匹配 resolver
      isCanvas: false,
      props: { /* ... */ },
      nodes: [],
      parent: "ROOT",
    },
  };
}

async function capture() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  // 拦截 GraphQL，返回 mock 数据
  await page.route('**/graphql', async (route) => {
    /* 返回 craftSettings 的 lzString 编码数据 */
  });

  await page.goto(`${BASE_URL}/edit/<mock-page-id>`);
  await page.waitForSelector('.craftjs-renderer', { timeout: 15000 });
  await page.waitForTimeout(3000);

  // 截图每个组件
  for (const comp of COMPONENT_CONFIGS) {
    if (comp.clickId) {
      const el = await page.$(`#${comp.clickId}`);
      if (el) { await el.click(); await page.waitForTimeout(1500); }
    }
    await page.screenshot({ path: path.join(IMG_DIR, `${comp.name}.png`) });
  }
  await browser.close();
}
```

### 关键踩坑点

**① resolvedName 必须与项目 resolver 一致**
```javascript
// ❌ 错误
type: { resolvedName: "Image" }
// ✅ 正确
type: { resolvedName: "DragImage" }
```
常见映射：`Container`→容器、`DragImage`→图片、`Text`→文本、`Button`→按钮

**② 图片组件用 data URI 占位**
```javascript
// ✅ 正确
settings: { defaultImg: "data:image/svg+xml,%3Csvg...%3E" }
// ❌ 错误
settings: { src: "" }
```

**③ canvas 组件（GridWrapper、IfEditor 等）无独立 DOM id**，无法通过 `#id` 点击选中，跳过点击。

**④ 截图前展开 ant-collapse 工具箱**
```javascript
await page.evaluate(() => {
  document.querySelectorAll('.ant-collapse-header').forEach(h => {
    if (h.getAttribute('aria-expanded') !== 'true') {
      h.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    }
  });
});
```

### 截图标注入

支持五种标注类型，通过 `pointer-events: none` 的 SVG 叠加层注入：

| 类型 | 字段 | 用途 |
|------|------|------|
| `circle` | `cx, cy, r, color, label` | 圈出 UI 元素 |
| `arrow` | `fromX, fromY, toX, toY, color` | 箭头连线 |
| `text` | `x, y, text, color, fontSize, bgColor` | 文字说明 |
| `rect` | `x, y, w, h, color, dash, label` | 虚线框选区域 |
| `separator` | `x, y, h, color, dash` | 垂直分隔线 |

坐标基于 1440×900 viewport：工具箱 x≈0~260，画布 x≈260~950，属性面板 x≈950~1440。

### 动态标注（DOM 坐标不确定时）

```javascript
if (comp.name === "A标签链接跳转") {
  const dynamicAnns = await page.evaluate(() => {
    const anns = [];
    const toolbox = document.querySelector('#left_panel_id');
    // 在工具箱中找到元素 → 计算坐标 → 生成标注
    return anns;
  });
  await injectAnnotations(page, dynamicAnns);
}
```

## 禁止事项

❌ 使用技术术语（后端、接口、数据结构、API）  
❌ 纯文字无配图（操作指南优先用截图）  
❌ 存放路径放错（必须 `doc/user-guide/<YYYY>/<MM>/`）  
❌ 写技术实现原理（只说操作不说原理）  

## 文档状态生命周期（文件名前缀 = 文档级状态）

文件名前缀随文档进度推进，便于扫目录一眼看出进度、中断后定位续做：

| 阶段 | 文件名前缀 | 何时 |
|---|---|---|
| 未处理 | `未处理-<主题>.md` | 文档刚创建，尚未开始 |
| 处理中 | `处理中-<主题>.md` | 开始处理/编写时重命名 |
| 已完成 | `已完成-<主题>.md` | 全部完成时重命名 |

状态迁移规则：
- 开始处理 → 文件名前缀改 `处理中-`
- 全部完成 → 文件名前缀改 `已完成-`
- 中断续做：重新打开文档，从上次进度继续，已完成内容不重做

> 改名仅人工约定，**无任何脚本/流程依赖文件名**，可放心改名（各文档生成 skill 统一约定）。

## 注意事项

1. 创建文档前先确认目录 `doc/user-guide/<YYYY>/<MM>/` 是否存在，不存在则创建
2. 文档名称使用中文，简洁明了，格式：`未处理-<功能名称>.md`；开始处理改 `处理中-`，全部完成改 `已完成-`（见「文档状态生命周期」）
3. 文档语言与用户提问语言保持一致
4. 创建完成后告知用户文档存放路径
5. 已有 CMS 编辑器截图脚本可作为模板参考：`scripts/capture-editor-screenshots.mjs`
