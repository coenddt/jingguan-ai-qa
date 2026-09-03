# 提取可复用代码

## 工具函数

```js
// 拆分前：内联在组件中
function formatDate(dateStr) {
  const date = new Date(dateStr)
  return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`
}

// 拆分后：提取到 utils/dateUtils.js
export function formatDate(dateStr) { ... }
import { formatDate } from '../../utils/dateUtils'
```

判断标准：在 2+ 文件重复使用、执行通用操作、不依赖调用组件状态。

## 可复用组件

```js
// 拆分前：嵌入在父组件
{items.map(item => (
  <view class="item-card">
    <image src={item.image} /> <text>{item.name}</text> <text>{item.price}</text>
    <button onTap={() => handleBuy(item.id)}>Buy</button>
  </view>
))}

// 拆分后：components/ItemCard/ItemCard.js  — <ItemCard item={item} onBuy={handleBuy} />
```

判断标准：2+ 处使用、有明确 UI 职责、可接受 props 配置行为。

## 共享样式与常量

```js
const COLORS = { primary: '#1890ff', text: '#333' }       // 设计 Token
const SPACING = { sm: 8, md: 16, lg: 24 }                 // 间距系统
const API_ENDPOINTS = { orders: '/api/orders' }           // 魔法字符串 → 常量
```
