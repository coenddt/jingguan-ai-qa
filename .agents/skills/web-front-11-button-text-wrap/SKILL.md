---
name: "web-front-11-button-text-wrap"
description: "按钮文字禁止换行：所有按钮必须 whitespace-nowrap；输入框+按钮同行布局用 flex-1 而非 w-full 撑满。创建或审查按钮布局时调用。"
---

# 按钮文字换行规范（web-front/）

## 核心原则
**所有按钮中的文字，必须保持在同一行内显示，禁止换行断词。**

## 规范细则

### 1. 所有按钮必须加 whitespace-nowrap

```jsx
// ✅ 正确
<button className="btn btn-primary whitespace-nowrap">
  添加模型
</button>

// ❌ 错误
<button className="btn btn-primary">
  添加模型
</button>
```

### 2. 输入框 + 按钮同一行的布局规范

当输入框和按钮需要在同一行并列显示时：

```jsx
// ✅ 正确 — 输入框 flex-1，按钮按内容收缩
<div className="flex gap-2">
  <input className="input input-bordered flex-1" placeholder="搜索关键词" />
  <button className="btn btn-primary whitespace-nowrap">搜索</button>
</div>

// ❌ 错误 — w-full 导致按钮被挤出
<div className="flex gap-2">
  <input className="input input-bordered w-full" />
  <button className="btn">搜索</button>
</div>
```

### 3. 通用按钮容器也需设置 whitespace

```jsx
<div className="flex gap-2 whitespace-nowrap">
  <button className="btn btn-ghost"><RefreshCw size={16} />重置</button>
  <button className="btn btn-primary"><FilterList size={16} />检索</button>
</div>
```

### 4. 应用范围

此规范适用于项目中所有按钮：页面操作按钮、弹窗按钮、搜索栏按钮、表格内按钮、AI 卡片追问 chips（chips 文字短，天然单行）等。
