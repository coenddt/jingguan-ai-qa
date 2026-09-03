---
name: "miniapp-dev-guide"
description: "微信小程序开发指南：布局规则、组件规范、常见陷阱。开发 miniapp-finance 或 miniapp 相关页面/组件时必须调用此技能。"
---

# 微信小程序开发指南

> **UI 标准**：LJM 页面/组件样式以 `wechat-miniapp-ui-style-rules` 技能为**权威标准**（漉金金色品牌、深色优先、CSS 变量设计令牌、--fs 字体系统、多主题），其规范源自 [miniapp-finance/app.wxss](file:///f:/独立开发者/项目/生活助手智能体/miniapp-finance/app.wxss)，编写任何样式前先读该技能。

> **有设计图时以设计图为最终标准**，UI 还原以 `wechat-miniapp-ui-style-rules` 技能的「0.0 设计图还原最高准则」为权威完整版，本指南不再重复。

## 按需加载（决策树）

正文只保留引用与红线约束，实现细节按需读取 `subs/` 子文件：

| 场景 | 读取文件 |
|------|---------|
| 布局规则（text/flex、自定义组件 inline、CSS Grid 卡片、注意点） | [subs/layout-rules.md](subs/layout-rules.md) |
| UI 区域中文 id 命名规则 | [subs/naming-rules.md](subs/naming-rules.md) |
| 已知陷阱（双标题栏 / copy-btn 同行 / iOS 26 backdrop-filter） | [subs/traps.md](subs/traps.md) |
| 查找相关专门 skill（UI/交互/组件/图片/业务等） | [subs/related-skills.md](subs/related-skills.md) |

## 禁止事项

❌ `<text>` 放入 flex 容器（占满整行，推挤兄弟元素）  
❌ 自定义组件宿主不设 inline 布局（默认 block 独占一行）  
❌ 固定 N 列卡片用 `flex + calc()` 或 `flex: 1`（必须 CSS Grid）  
❌ UI 区域 `id` 用英文或无意义命名（必须中文）  
❌ 使用 `<nav-bar>` 的页面 `.json` 漏配 `"navigationStyle": "custom"`（双标题栏）  
❌ 在 `fixed` 元素上使用 `backdrop-filter: blur`（iOS 26+ 重影 Bug）  
❌ 依赖 `virtualHost: true` / `:host` 选择器（部分微信版本不支持）  
❌ `<text>` 内嵌套 `<view>` / `<image>`（只能含文本和其他 `<text>`）

## 注意事项

1. LJM 页面/组件样式一律以 `wechat-miniapp-ui-style-rules` 为权威标准，先读再写
2. 有设计图时以设计图为最终标准（详见该技能「0.0 设计图还原最高准则」）
3. `copy-btn` 与标题同行时去掉 wrapper，`<text>` 与 `<copy-btn style="display:inline-flex">` 直排兄弟
4. 开发具体功能前，先查 `subs/related-skills.md` 路由到对应专门 skill
