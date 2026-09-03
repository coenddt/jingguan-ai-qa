# 相关技能路由

开发微信小程序时，可根据需求调用以下专门 skill：

## 项目与架构

- **`wechat-miniapp-project-rules`** — 项目结构、页面约定、API 使用、VGDC UI 文本规则。**新建页面或组件时调用**
- **`wechat-miniapp-component-convention`** — 组件命名（kebab-case）、props 规范（camelCase）、样式隔离、抽象原则（重复 2 次以上提取组件）。**创建或重构组件时调用**
- **`code-structure-optimizer`** — 大文件拆分（>300 行）、提取可复用代码。**页面/组件完成后优化结构时调用**

## UI 与样式

- **`wechat-miniapp-ui-style-rules`** — **LJM UI 权威标准**（漉金金色品牌、深色优先、CSS 变量设计令牌、--fs 字体系统、多主题、通用组件类、漉金内容合规）。**创建 UI 组件或编写页面样式时首先调用**
- **`wechat-miniapp-css-glow-effect`** — 径向渐变发光效果（radial-gradient），用于页面氛围光晕与卡片金色装饰线。**添加发光背景时调用**
- **`wechat-miniapp-icon-svg`** — 纯线条 SVG 图标生成（fill=none, stroke-width=1.25, stroke=#64748b, viewBox 0 0 48 48, base64 data URI）。**添加或替换页面图标时调用（simple-icon-rule 已并入本技能）**
- **`wechat-miniapp-navbar-rules`** — 自定义导航栏封装（占位层+内容层）、操作布局规范。**创建或修复导航栏布局时调用**
- **`wechat-miniapp-safe-area-rules`** — 底部安全区适配（iPhone 刘海屏），全局 CSS 变量。**设计页面底部布局时调用**

## 交互与状态

- **`wechat-miniapp-state-feedback-rules`** — 加载/空状态（state-view 组件）、骨架屏、按压反馈（hover-class）、占位图策略。**实现数据加载或用户交互反馈时调用**
- **`wechat-miniapp-ux-interaction-rules`** — 悬浮按钮滚动隐藏、后端搜索分页、流式输出交互优化。**优化复杂列表交互或 AI 流式功能时调用**
- **`wechat-miniapp-keyboard-rules`** — 键盘弹出时页面推挤导致 fixed 元素错位问题，动态调整输入区位置。**开发聊天页或底部输入区页面时调用**
- **`wechat-miniapp-performance-rules`** — 高频 setData 优化、Token 缓冲、路径式更新、定时器管理。**优化性能、减少耗电时调用**

## 组件与功能

- **`wechat-miniapp-input-height`** — 输入框必须设置显式 height 的样式规则。**新建或修改 input 元素时调用**
- **`wechat-miniapp-scrollview-padding`** — 修复 scroll-view 水平 padding 右侧缺失问题。**scroll-view 内容溢出时调用**
- **`wechat-miniapp-canvas-rules`** — type='2d' Canvas DPR 缩放内容不显示的渲染管线断裂问题，含初始化模板。**实现或调试 Canvas 功能时调用**

## 图片与占位

- **`wechat-miniapp-no-image-default`** — 菜品/餐厅无图时使用首字符+随机色块占位。**显示菜品或餐厅图片时调用**

## AI 与微信生态

- **`wechat-ai-integration`** — 微信 AI 生态接入（Skill/MCP 协议），含目录结构、MCP 契约、原子接口、卡片组件。**将小程序接入微信 AI 生态时调用**

## 业务功能

- **`wechat-miniapp-restaurant-feature-workflow`** — 餐厅功能开发工作流：页面设计、API 集成、组件开发、UI/UX。**规划/开发餐厅新功能页面时调用**
- **`vegan-miniapp-dev`** — "请一亿人吃素"小程序开发（素食供斋、点餐、打卡、积分系统）。**构建素食捐赠相关功能时调用**
