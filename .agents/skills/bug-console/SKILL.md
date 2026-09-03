---
name: "bug-console"
description: "Instruments code with diagnostic logs to root-cause bugs. Invoke when a non-trivial bug needs runtime evidence that static analysis alone cannot resolve, or when user provides logs from a running app that need interpretation."
---

# Bug Diagnostics

## 核心概念

通过插桩 `console.log` 收集运行时证据，5 轮迭代内定位或给出诊断报告。**只用原生调试输出**，禁止引入第三方调试库。

## 调试工具

| 环境 | 工具 |
|------|------|
| 小程序 (miniapp*/) | `console.log()` |
| Web SaaS (web-saas/) | `console.log()` |
| Node.js (server*/) | `console.log()` |
| PostgreSQL | `RAISE WARNING` / `RAISE NOTICE` |

## 插桩规则

```js
// 客户端/服务端通用格式
console.log('[<module>] <description>:', key_value1, key_value2)

// PostgreSQL
-- RAISE WARNING '[<module>] <description>: %', key_value;
```

**插桩位置**：
- 入口点：函数名 + 入参
- 决策点：条件值 + 分支走向
- 数据变换：变换前后关键值
- 选择器查询：节点存在性、尺寸
- 样式/属性变更：设了什么值
- 异步回调：回调入口 + 接收数据

**关键值处理**：
- 对象/数组用 `JSON.stringify()`（最多 2 层）
- 布尔值用 `!!value` 显式转真值
- 尺寸值包含宽、高、比例

## 工作流（最多 5 轮）

### 第 1 轮：理解问题

读 bug 报告，确定代码路径（入口 → 数据流 → 渲染），判断需要哪些运行时证据。

### 第 2 轮：插桩

在目标代码路径插入 `console.log`，遵守插桩规则。

### 第 3 轮：尝试沙盒测试

有沙盒环境时：
```bash
npm run build      # 构建检查
npm run dev        # 启动开发服务器
npx tsc --noEmit   # TypeScript 检查
```

无沙盒环境（如微信小程序需模拟器）则跳到第 4 轮。

### 第 4 轮：收集并分析日志

- **客户端**：用户从开发者工具控制台复制输出
- **服务端**：PM2 日志或 `console.log` 输出
- **PostgreSQL**：通过 pgAdmin 查看 RAISE 输出

分析流程：全链路追踪 → 找偏差值 → 查 null/undefined → 校验尺寸/坐标计算 → 验证参数传递。

### 第 5 轮：修复或报告

**找到根因（5 轮内）**：
1. 实现修复
2. 请用户验证
3. **用户确认后**才清除所有插桩代码

**未找到根因（超 5 轮）**：
创建诊断报告 `diagnostic-report/<bug-short-name>.md`：

```markdown
# Bug Diagnostic Report: <title>
Date: <date>
Iterations: <number>

## Symptom
## Logs Collected
## Analysis Per Iteration
### Iteration 1
- Logs added: <files and locations>
- Findings:
- Hypothesis:
### Iteration 2
...
## Remaining Unknowns
## Suspected Areas
## Recommended Next Steps
```

## 日志示例

```
[result] canvas node found, canvasRect: {"width":300,"height":150}
[result] paperSize passed to renderQuestions: A4
[result] setCanvasDisplaySize - paperSize param: A4 resolved paper: {"w":210,"h":297}
[result] setCanvasDisplaySize - FINAL via setData: {"canvasDisplayWidth":343.2,"canvasDisplayHeight":485.38}
```

此日志暴露 `canvas.style` 为 null → 改用 WXML data binding。

## 禁止事项

❌ 禁止添加浮动调试按钮/调试浮层  
❌ 禁止创建专用调试工具库（`bug-logger.js` 等）  
❌ 禁止将日志写入文件（`debug/` 目录等）  
❌ 禁止添加全局日志收集器或日志缓存数组  
❌ 禁止引入第三方调试库  

## 注意事项

1. **日志清理时机**：必须等用户确认 bug 已修复后才移除插桩代码，不留残留
2. **JSON.stringify 深度**：对象/数组最多 2 层，过深会导致日志不可读
3. **迭代上限**：最多 5 轮插桩→收集→分析循环，超时产出诊断报告
4. **尺寸值完整性**：宽、高、比例同时输出，方便比对预期值
5. **异步回调必打**：回调入口和接收数据都要 log，避免异步流程盲区
