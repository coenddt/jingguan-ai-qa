---
name: "web-front-06-search-filter"
description: "SearchFilter 组件规范：fields 配置（text/select/date）、onSearch/onReset 回调、initialValues、搜索触发方式。实现列表页搜索筛选时调用。"
---

# 搜索筛选组件规范（web-front/）

## 概述

`SearchFilter` 组件位于 `web-front/src/components/SearchFilter/index.tsx`（已复用），所有列表页的搜索筛选区域必须优先使用。

## 组件 Props

| Prop | 类型 | 说明 |
|------|------|------|
| `fields` | `array` | 筛选字段配置数组 |
| `onSearch` | `function` | 搜索回调，参数为 `{ fieldName: value }` 对象 |
| `onReset` | `function` | 重置回调，无参数 |
| `initialValues` | `object` | 可选，字段的初始/默认值 |

### fields 配置

每个 field 对象：

| 属性 | 类型 | 说明 |
|------|------|------|
| `type` | `'text' \| 'select' \| 'date'` | 字段类型 |
| `name` | `string` | 字段名 |
| `placeholder` | `string` | text 类型占位文本 |
| `label` | `string` | select/date 类型标签 |
| `options` | `array` | select 类型选项：`{ label, value }` |
| `minWidth` | `number` | 控件最小宽度 |

### 标准用法

```jsx
<SearchFilter
  fields={[
    { type: 'text', name: 'keyword', placeholder: '搜索会话关键词' },
    { type: 'select', name: 'status', label: '状态', options: [
      { label: '全部', value: '' },
      { label: '已处理', value: '1' },
    ]},
  ]}
  onSearch={handleSearch}
  onReset={handleReset}
/>
```

### 日期筛选

```jsx
{ type: 'date', name: 'startDate', label: '开始日期' }
```

日期值为 `'YYYY-MM-DD'` 格式字符串。

## 搜索触发方式

- 点击"检索"按钮（Search 图标）
- 输入框按 Enter 键
- 点击"重置"按钮（RotateCcw 图标）清空所有字段为初始值

## 本项目适用场景

- 回复校对页（`/feedback`）的筛选区
- 问数日志 / 导入记录列表的筛选区
