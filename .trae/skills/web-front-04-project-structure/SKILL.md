---
name: "web-front-04-project-structure"
description: "web-front 项目结构：目录布局、路由定义、Cookie 认证机制。了解项目架构或新增页面时调用。"
---

# 项目结构规范（web-front/）

## 目录结构
```
web-front/
├── public/
├── src/
│   ├── api/             # API 接口
│   │   ├── client.ts     # axios 实例（baseURL /api、withCredentials、401 拦截）
│   │   └── modules/      # API 模块（按后端路由拆分）
│   ├── components/       # 通用组件（自 web-saas 复用，见 09 规范）
│   │   └── Layout/      # 布局组件（Sidebar/Header）
│   ├── features/qa/      # 问数业务组件（会话列表/AI卡片/输入栏/图表）
│   ├── pages/           # 页面组件（复杂页面用目录：index.tsx + 私有子组件）
│   ├── hooks/           # 自定义 Hooks（复杂状态/异步流程封装）
│   ├── services/        # 纯业务函数（按业务域拆：qa/tts/clipboard/download/chart/favorites）
│   ├── store/           # Zustand 状态管理
│   ├── utils/           # 通用工具函数（无业务语义：date/error/localStorage/markdown）
│   ├── App.tsx          # 根组件（含路由定义与守卫）
│   ├── index.css        # 全局样式（@theme 主题变量 + 装饰类）
│   ├── types.ts         # 全局 TS 契约（对齐后端 QaAskResp 等）
│   └── main.tsx         # 入口文件
├── index.html
├── tsconfig.json
├── package.json
└── vite.config.ts
```

## 页面路由
- `/login` - 登录页
- `/qa` - 智能问数（默认页，会话侧栏 + 聊天）
- `/config/app` - 应用配置（6 张卡片）
- `/config/model` - 模型配置（CRUD）
- `/feedback` - 回复校对（列表 + 详情/处理）

## 认证机制（与 web-saas 的 Bearer token 不同！）
- **Cookie 认证**：nginx `auth_request` + 后端 HMAC 签名 Cookie（24h 有效）
- `src/api/client.ts` axios 实例统一 `withCredentials: true`，无需手动传 token
- 响应 401 → dispatch `auth:expired` 自定义事件 → 路由守卫跳转 `/login`
- 登录后 24h 免重复登录；登出调 `POST /api/auth/logout` 主动失效
- 路由守卫在 `App.tsx` 中实现（未登录访问业务路由 → 重定向 `/login`）

## 页面位置判断
| 场景 | 位置 |
|------|------|
| 问数链路新组件 | `src/features/qa/` 下新建 |
| 独立新页面 | `src/pages/` 下新建目录 |
| 复杂状态/异步流程 | `src/hooks/` 下新建 useXxx.ts |
| 纯业务函数 | `src/services/` 下按业务域新建 |
| 配置类扩展 | 现有 `/config/*` 页内新增 Tab 或卡片 |
