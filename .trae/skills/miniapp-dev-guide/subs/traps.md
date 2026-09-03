# 已知陷阱记录

## 使用自定义导航栏但未移除系统标题栏（2026-08-05）

- **场景**：页面 WXML 中已使用 `<nav-bar>` 组件
- **问题**：页面 `.json` 漏配 `"navigationStyle": "custom"`，导致系统标题栏与自定义导航栏**同时显示**（"双标题栏"，顶栏内容被拉高、出现两层标题）
- **解决**：使用 `<nav-bar>` 的页面，其 `.json` **必须**配置：

```json
{
  "navigationStyle": "custom",
  "usingComponents": {}
}
```

- **验收检查**：新页面或改动页面 json 时，确认已含 `"navigationStyle": "custom"`
- **详细规则见**：`wechat-miniapp-navbar-rules` 技能"页面配置规则"章节

## copy-btn 与标题同行 (2026-07-30)

- **场景**：`sandbox-card` 中标题文字后跟复制按钮
- **问题**：`<view style="display:inline-flex">` 包裹 `<text> + <copy-btn>` 时布局异常
- **解决**：去掉 wrapper，`<text>` 和 `<copy-btn style="display:inline-flex">` 作为直排兄弟
- **涉及组件**：`sandbox-card`、`dd-card`、`policy-card`、`promotion-card`、`asset-cards`、`chat`、`favorite-detail`

## iOS 26+ backdrop-filter 重影 Bug (2026-08-11)

- **问题**：在 iPhone 17 (iOS 26+) 系统下，对 `fixed` 定位的元素（如导航栏、悬浮按钮、底部输入区）使用 `backdrop-filter: blur` 会导致渲染管线出现重影/层重叠 Bug。
- **解决**：实施视觉降级，全局移除 `backdrop-filter: blur`。同时将背景色的不透明度提升至 `0.9` 以上，以保证背景与内容的视觉对比度。
- **强制规则**：禁止在 LJM 小程序及 LJW Web 端的核心 `fixed` 元素上使用毛玻璃模糊效果，直至系统 Bug 修复。
