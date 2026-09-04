---
name: "web-front-05-api-call-conventions"
description: "web-front API 调用规范：Cookie 认证、axios 实例、401 拦截、模块组织、后端端点清单。编写或修改 API 调用时调用。"
---

# API 调用规范（web-front/）

> 后端为 FastAPI（server/），接口契约见 `doc/execution/2026/09/未处理-后端FastAPI分层执行文档.md`。

## 认证机制（Cookie，非 Bearer）

- nginx `auth_request` + 后端 HMAC 签名 Cookie（24h），前端无需管理 token
- `src/api/client.ts` 的 axios 实例统一配置：

```js
import axios from 'axios'

export const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 30000,
})

// 401 → 未登录/过期
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:expired'))
    }
    return Promise.reject(err)
  }
)
```

- `App.tsx` 监听 `auth:expired` 事件 → 跳转 `/login`
- **在 API 函数或页面组件中，无需显式传递任何认证参数**

## 请求规范

- 所有 API 请求方法统一使用 `.post()` 或 `.get()`
- 请求参数以对象形式传入
- 问数 `POST /api/qa/ask` 耗时较长（AI 生成查询），注意 loading 态与超时设置

## 响应格式

- 后端直接返回业务 JSON（**无 `{code,message,data}` 包装，无需解包**）
- 组件中 `res.data` 即业务数据（如 `QaAskResp` 结构：steps/findings/columns/rows/stats/chart/follow_ups/meta）

## API 模块文件组织

- 所有 API 函数封装在 `web-front/src/api/modules/` 目录下，按业务模块拆分文件
- 页面组件应导入 API 模块函数进行调用，禁止页面内直接写 axios 裸调
- API 模块用 TypeScript 编写：入参与返回值标注类型，复用 `src/types.ts` 中的契约（如 `QaAskResp`）

## 后端端点清单（v2.0 契约）

| 端点 | 用途 |
|------|------|
| `POST /api/auth/login` / `GET /api/auth/check` / `POST /api/auth/logout` | 登录 / nginx 校验回调 / 登出 |
| `POST /api/qa/ask` | 智能问数（返回 QaAskResp） |
| `GET /api/qa/sessions` `PATCH /api/qa/sessions/{id}` `DELETE /api/qa/sessions/{id}` | 会话列表/置顶/重命名/删除 |
| `GET /api/qa/sessions/{id}/messages` | 会话消息恢复 |
| `GET /api/qa/sources` | 数据源分组列表 |
| `GET /api/qa/log` | 问数日志 |
| `GET/PUT /api/config` | 应用配置 |
| `GET /api/models` 等 | 模型配置 CRUD |
| `GET /api/feedback` `POST/PATCH /api/feedback/{id}` | 回复校对 |
| `POST /api/import/upload` `GET /api/import/log` | 台账导入 / 导入记录 |
| `POST /api/tts` | 语音播报 |

## 接口调用原则

1. **使用专用接口而非通用接口+遍历**
2. **服务端筛选优先**，避免全量拉取后在客户端过滤
