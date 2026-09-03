# 文件拆分（>300 行）+ 目录结构优化

## 文件拆分（>300 行）

判断拆分边界：多个组件/类混在一处、数据获取+渲染+状态管理混杂、大段辅助函数块、大型常量/配置字典、类型定义可独立提取、CSS-in-JS/样式可分离。

**React / 组件项目**：

```js
// 拆分前：BigComponent.tsx (500 行)
// 拆分后：
//   BigComponent.tsx          — 核心组件逻辑 (~150 行)
//   BigComponent.types.ts     — 类型定义
//   BigComponent.styles.ts    — 样式
//   BigComponent.helpers.ts   — 工具函数
//   BigComponent.hooks.ts     — 自定义 hooks
//   BigComponent.constants.ts — 常量/枚举
```

**微信小程序**：

```js
// 拆分前：pages/order/order.js (600 行)
// 拆分后：
//   pages/order/order.js              — 核心页面逻辑 (~200 行)
//   pages/order/services/orderApi.js   — API 调用
//   pages/order/utils/orderUtils.js    — 工具函数
//   pages/order/components/            — 子组件
//     OrderCard/  OrderStatus/
```

**Node.js / 后端**：

```js
// 拆分前：routes/order.js (500 行)
// 拆分后：
//   routes/order.js              — 路由定义
//   controllers/orderController.js — 请求处理 (~100 行)
//   services/orderService.js     — 业务逻辑 (~150 行)
//   validators/orderValidator.js — 输入校验
//   models/orderModel.js         — DB 查询
```

拆分规则：

```js
// 向后兼容：原文件 re-export 已提取模块
export { default } from './BigComponent'
export { useBigComponentLogic } from './BigComponent.hooks'
export { COLORS, SIZES } from './BigComponent.constants'
```

1. 更新所有 import/require 路径
2. 需要时用 barrel export 保持向后兼容
3. 保持内聚——相关代码不随意拆分
4. 避免循环依赖——提取的模块不能互相引用

## 目录结构优化

```
拆分前（按文件类型）:
  components/UserHeader.js  components/UserProfile.js
  components/OrderList.js   components/OrderDetail.js

拆分后（按功能）:
  features/user/components/UserHeader.js  features/user/components/UserProfile.js
  features/order/components/OrderList.js  features/order/components/OrderDetail.js
```

分层架构模板：

```
src/
  features/       # 功能模块
  shared/         # 跨功能共享（组件/工具/hooks/API/常量）
  pages/          # 路由级页面
  app/            # 应用初始化
```
