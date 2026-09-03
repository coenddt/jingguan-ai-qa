---
name: "web-front-10-table-column-width"
description: "表格列宽规范：按列数设置 minWidth、单元格宽度约束、主文本列换行、表头表体一致。创建或修改列表页表格时调用。"
---

# 表格列宽规范（web-front/）

## 强制规则

### 1. 每个表格必须设置 minWidth

| 列数 | 建议 minWidth |
|------|--------------|
| ≤4 列 | 750+ |
| 5~6 列 | 850+ |
| 7~8 列 | 1000+ |
| ≥9 列 | 1100+ |

外层用 `overflow-x-auto` 包装：

```jsx
<div className="overflow-x-auto">
  <table className="table" style={{ minWidth: 1000 }}>...</table>
</div>
```

### 2. 每个单元格必须设置宽度

**主文本列**（会话标题、模型名称、问题描述等）：

```jsx
<td className="min-w-[140px] max-w-[260px]">
```

**短内容列**（状态、数值、ID 等）：

```jsx
<th className="w-[100px]">
```

**时间列**：

```jsx
<th className="w-[160px]">
```

**操作列**：

```jsx
<th className="w-[100px]">
```

### 3. 主文本列的 body cell 必须允许换行

```jsx
<td className="min-w-[140px] max-w-[260px] whitespace-normal break-words">
  <span className="font-semibold text-sm">{row.title}</span>
</td>
```

### 4. 表头和表体的宽度必须一致

同一列的 `th` 与 `td` 宽度约束保持相同。

## 常见宽度参考

| 列类型 | 宽度约束 |
|--------|---------|
| 名称/标题 | `min-w-[140px] max-w-[260px]` |
| 较长文本（问题描述） | `min-w-[160px] max-w-[300px]` |
| UID/ID | `w-[100px]` |
| 数值/统计 | `w-[100px]` |
| 状态/类型 | `w-[80px]~w-[100px]` |
| 时间日期 | `w-[160px]` |
| 操作(图标) | `w-[100px]~w-[130px]` |

## 本项目适用表格

- 问数结果表格（columns/rows 动态列，以内容自适应 + 总 minWidth 兜底）
- 回复校对列表、问数日志、导入记录列表
