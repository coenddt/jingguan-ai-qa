---
name: "web-front-07-search-component-priority"
description: "列表页搜索筛选强制优先使用 SearchFilter 组件，禁止手写内联筛选代码。新增任何列表页搜索/筛选功能时调用。"
---

# 搜索组件优先使用规范（web-front/）

## 强制规则

**所有含有搜索筛选功能的列表页，必须优先使用 `SearchFilter` 组件**（`web-front/src/components/SearchFilter/index.tsx`，已复用），禁止手写内联筛选代码。

## 适用范围

| 场景 | 必须使用 SearchFilter | 允许自定义 |
|------|:--------------------:|:----------:|
| 纯文本搜索 + 下拉筛选 | ✅ | ❌ |
| 文本搜索 + 日期筛选 | ✅ | ❌ |
| 复杂筛选（超过 5 个字段） | ✅ 作为主体 | 可包裹自定义布局 |
| 筛选条件与表格行联动 | ✅ | 可结合 initialValues |

## 禁止模式

```jsx
// ❌ 禁止：手写 input + select + 搜索/重置按钮
<div className="grid grid-cols-12 gap-3">
  <input className="input input-bordered col-span-4" placeholder="搜索..." />
  <select className="select select-bordered col-span-3">...</select>
  <button className="btn btn-primary">搜索</button>
</div>
```

```jsx
// ✅ 正确：使用 SearchFilter
<div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-4">
  <SearchFilter
    fields={[...]}
    onSearch={handleSearch}
    onReset={handleReset}
  />
</div>
```

## 判断标准

```
页面有搜索/筛选功能？
├─ 是 → 筛选字段数 ≤ 5 个？
│  ├─ 是 → 直接使用 SearchFilter
│  └─ 否 → 以 SearchFilter 为基础，扩展自定义筛选
└─ 否 → 不需要 SearchFilter
```
