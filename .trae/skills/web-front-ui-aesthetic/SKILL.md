---
name: "web-front-ui-aesthetic"
description: "web-front（经管之星·AI问数助手）UI 美学基调规范：深蓝+金色品牌视觉体系、排版、间距、卡片、动效、背景装饰。开发新页面或评审 UI 时调用。"
---

# 经管之星 · AI问数助手 — UI 美学基调（web-front/）

> 此规范定义 web-front 的整体视觉风格基调（复用自 web-saas 漉金体系，品牌色板保留深蓝+金色），所有页面开发、组件设计、动效实现均应遵循此基调。

---

## 一、设计哲学

### 1.1 "经管之星" 的品牌意象

> **经管** — 数据的严谨、专业的深度
> **星** — 闪耀的洞察、从数据中提炼出的答案

| 意象 | 视觉表达 |
|------|---------|
| **专业严谨** | 干净利落的留白、克制的装饰、清晰的层级 |
| **数据洞察** | 高对比度的信息层级、精准的数据展示、锐利的线条 |
| **星光质感** | 深色背景中的金色点缀、厚重而不笨拙 |
| **历久弥新** | 经典的比例关系、考究的排版 |

### 1.2 风格定位

```
大气 ───── 非张扬，而是胸有成竹的留白与从容的版面
厚重 ───── 非笨重，而是深色背景中的沉稳与信息密度的掌控
设计感 ─── 非花哨，而是克制的装饰、精准的间距、考究的比例
未来感 ─── 非炫技，而是光效的克制运用、流畅的微动效、通透的玻璃质感
```

---

## 二、色彩体系

### 2.1 主色调

```css
/* 深蓝 — 代表专业与深度 */
--color-primary:       #1a3a6c;   /* 深海蓝，主色 */
--color-primary-light: #2c5282;   /* 稍亮 */
--color-primary-lighter: #3d6a9e; /* 更亮，用于 hover 状态 */
--color-primary-dark:  #0f294d;   /* 极深，用于大面积背景 */

/* 金色 — 代表"星"的价值与高光 */
--color-secondary:       #b48a32;   /* 哑金，主金色 */
--color-secondary-light: #d4af37;   /* 亮金，用于重点高亮 */
--color-secondary-lighter: #e8cc6e; /* 极亮金，用于发光效果 */
--color-secondary-dark:  #8e6d24;   /* 深金，稳重 */
```

### 2.2 场景色

```css
--color-success: #16a34a;   /* 成功 — 沉稳绿 */
--color-warning: #d97706;   /* 警告 — 琥珀色 */
--color-error:   #dc2626;   /* 错误 — 正红 */
--color-info:    #2563eb;   /* 信息 — 明亮蓝 */
```

### 2.3 中性色

```css
--color-bg-default: #f5f7fa;    /* 页面背景，微冷灰 */
--color-bg-paper:   #ffffff;     /* 卡片/面板背景，纯白 */
--color-text-primary: #1a202c;  /* 主文字，深灰黑 */
--color-text-secondary: #64748b; /* 辅助文字，石板灰 */
--color-divider: #e2e8f0;       /* 分割线 */
```

### 2.4 色彩使用原则

- **大面积色块**：使用深蓝 `#1a3a6c` 或极深蓝 `#0f294d` 作为背景色，营造厚重感
- **点缀色**：金色 `#d4af37` / `#b48a32` 仅用于关键元素（CTA 按钮、高亮数据、品牌标识），**不可滥用**
- **文字层级**：主文字 `#1a202c` > 辅助文字 `#64748b` > 占位文字 `#94a3b8`
- **深色背景文字**：深色背景上白色文字统一使用 `text-white/85`（正文）和 `text-white/50`（辅助）

---

## 三、排版体系

### 3.1 字体家族

```css
/* 标题字体 — 衬线体，传达经典与厚重 */
font-family: Georgia, "Noto Serif SC", serif;

/* 正文字体 — 无衬线体，保证可读性 */
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
```

### 3.2 字号层级

| 层级 | 移动端 | 桌面端 | 字重 | 行高 | 用途 |
|------|--------|--------|------|------|------|
| 展示级 H1 | `2.5rem` / 40px | `4rem` / 64px | 900 (Black) | 1.1 | 登录页大标题 |
| 页面级 H1 | `1.75rem` / 28px | `2.25rem` / 36px | 800 (ExtraBold) | 1.2 | 内页标题 |
| 区块标题 H2 | `1.5rem` / 24px | `1.75rem` / 28px | 800 (ExtraBold) | 1.3 | 区块标题 |
| 卡片标题 H3 | `1.125rem` / 18px | `1.25rem` / 20px | 700 (Bold) | 1.4 | 卡片/AI卡片标题 |
| 正文 | `0.9375rem` / 15px | `1rem` / 16px | 400 (Normal) | 1.6 | 正文内容 |
| 辅助文字 | `0.75rem` / 12px | `0.8125rem` / 13px | 400 | 1.5 | 标签、时间戳、辅助信息 |

### 3.3 排版原则

- **标题用衬线**（Georgia / Noto Serif SC）传达经典与信任感
- **正文用无衬线**确保小字号可读性
- **行高宽松**：正文行高 `1.6`+，段落间距充足
- **字间距紧凑**：大标题使用 `letter-spacing: -0.04em` 增加现代感
- **数据用粗体**：所有统计数据（count/avg/max/min）、数值使用 `font-extrabold` 加重视觉权重

---

## 四、间距与布局

### 4.1 间距体系

以 4px 为基准单位，遵循 4-8-12-16-20-24-32-40-48-64 的间距阶梯。

| 层级 | 间距 | 用途 |
|------|------|------|
| 紧凑 | 8px / 12px | 内边距、标签间距 |
| 标准 | 16px / 20px | 卡片内间距、表单项间距 |
| 宽松 | 24px / 32px | 区块间距、卡片间距 |
| 疏朗 | 40px / 48px | 大区块间隔 |
| 留白 | 64px+ | 登录页 Hero 场景 |

### 4.2 布局容器

- **页面最大宽度**：`max-w-6xl` (1152px) 或 `max-w-[1440px]`
- **内容区域**：`container mx-auto px-4 md:px-6`
- **网格系统**：Tailwind Grid — `grid grid-cols-1 md:grid-cols-3 gap-4`
- **卡片**：`bg-white rounded-2xl shadow-sm border border-gray-200 p-6`
- **深色区块**：`bg-[#0f172a]` 配合金色点缀
- **问数页布局**：左侧会话栏 + 右侧聊天区（`flex` + 固定侧栏宽度）

### 4.3 布局原则

- **呼吸感**：区块之间保持 48px+ 的垂直间距
- **对齐**：所有元素严格左对齐或居中对齐，避免凌乱
- **信息密度**：配置/日志类页面可适当降低间距以容纳更多信息，但不可密集到压迫感

---

## 五、卡片与面板

### 5.1 卡片分类

**亮色卡片（数据展示）**
```jsx
<div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
  {/* 内容 */}
</div>
```

**玻璃卡片（覆盖层/Hero 区域）**
```jsx
<div className="glass-card">
  {/* 背景模糊 + 半透明 + 细边框 */}
</div>
```

**深色卡片（深色区块）**
```jsx
<div style={{ backgroundColor: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
  {/* 深色背景上的卡片 */}
</div>
```

**AI 回复卡片**：白底圆角卡片，内部按 分析过程(折叠) → 数据发现 → 表格 → 统计 → 图表 → 追问 chips 分段，段间距 16~20px。

### 5.2 圆角规范

| 层级 | 圆角 | 用途 |
|------|------|------|
| 小 | `rounded-lg` / 8px | 按钮、输入框、标签 |
| 中 | `rounded-xl` / 12px | 小卡片、弹窗 |
| 大 | `rounded-2xl` / 16px | 主卡片、面板、容器 |
| 全 | `rounded-full` | 徽章、圆形头像、追问 chips |

---

## 六、动效与交互

### 6.1 微动效原则

- **克制**：动效不可喧宾夺主，只服务于用户体验
- **流畅**：统一使用 `transition-all duration-300` 或 `400ms ease`
- **自然**：缓动函数使用 `ease` 而非 `linear`

### 6.2 标准动效

**Hover 提升效果**
```css
.card-hover {
  transition: all 0.3s ease;
}
.card-hover:hover {
  transform: translateY(-4px);
  border-color: rgba(212, 175, 55, 0.3);
}
```

**金色发光按钮**
```css
.btn-gold {
  background: linear-gradient(135deg, #b48a32 0%, #d4af37 100%);
  box-shadow: 0 4px 20px rgba(180, 138, 50, 0.2);
}
.btn-gold:hover {
  box-shadow: 0 8px 30px rgba(180, 138, 50, 0.35);
  transform: translateY(-1px);
}
```

### 6.3 滚动入场

使用 `AnimateInView` 组件（已复用）实现滚动触发动画：
- 每个区块独立触发
- 延迟递进：`delay={0.12 * i}`（同一行多个卡片时）
- 方向：统一从下往上（`translateY(10px)` → `translateY(0)`）

### 6.4 交互反馈

- **按钮点击**：保持 daisyUI 默认的 `active:scale-95` 按下效果
- **卡片悬浮**：轻微上移（`-4px`）+ 金色边框发光
- **加载状态**：问数等待时使用 `loading loading-spinner` 或骨架屏方案
- **空状态**：展示引导性提示，配合柔和插图或 icon

---

## 七、图像与图标

### 7.1 图标

- **图标库**：全部使用 `lucide-react`，禁止 emoji 替代图标
- **风格**：统一 `strokeWidth={1.5}` 线条风格
- **尺寸**：16px（辅助）、20px（标准）、24px（大图标）、28px（特性展示）
- **颜色**：默认跟随文字颜色；金色高亮图标使用 `color: #d4af37`

### 7.2 图像风格

- **背景装饰图形**：使用纯 CSS 实现（渐变、网格点阵、光晕），避免使用外部图片
- **图表**：使用 ECharts（echarts-for-react 封装于 `src/features/qa/charts/`），配色与品牌色板一致
- **禁止**：使用 Unsplash 等外部图片服务

---

## 八、背景与装饰

### 8.1 背景系统

**亮色页面背景** — `#f8fafc`（列表页、配置页）
- 可选网格叠加：`radial-gradient(rgba(26,58,108,0.04) 1px, transparent 1px)`，`background-size: 60px 60px`

**深色页面背景** — `#0f172a`（登录页、深色区块）
- 点阵纹理：`radial-gradient(circle at 2px 2px, white 1px, transparent 0)`，透明度 `0.1`
- 金色辉光：`radial-gradient(circle, rgba(212,175,55,0.12) 0%, transparent 70%)` + `filter: blur(80px)`

### 8.2 CSS 装饰方案（搭建骨架时定义于 `src/index.css`）

```css
/* 毛玻璃面板 */
.glass-panel {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

/* 毛玻璃卡片 */
.glass-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
}

/* 金色渐变 */
.gold-gradient {
  background: linear-gradient(135deg, #b48a32 0%, #d4af37 50%, #8e6d24 100%);
}

/* 深蓝渐变 */
.blue-gradient {
  background: linear-gradient(135deg, #1a3a6c 0%, #2c5282 50%, #0f294d 100%);
}

/* 蓝金混合渐变 */
.mixed-gradient {
  background: linear-gradient(135deg, #1a3a6c 0%, #b48a32 100%);
}

/* 金色文字渐变 */
.text-gradient-gold {
  background: linear-gradient(135deg, #b48a32 0%, #d4af37 50%, #8e6d24 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* 金色边框光晕 */
.gold-border-glow {
  border: 1px solid rgba(180, 138, 50, 0.3);
  box-shadow: 0 0 15px rgba(180, 138, 50, 0.1);
}
```

---

## 九、页面类型风格指南

### 9.1 登录页
- **深色 Hero**：大尺寸衬线标题（`font-black text-4xl md:text-6xl`）+ 金色 CTA
- **装饰**：网格点阵 + 金色辉光光晕

### 9.2 智能问数页（核心页面）
- **布局**：左侧会话导航 + 右侧聊天区
- **色块**：`bg-gray-50` 主背景，白色 AI 卡片
- **金色使用**：仅在 Logo、高亮数据、统计数值中使用
- **表格**：`table` 组件，表头深蓝背景白色文字，行 hover 金色边框高亮

### 9.3 配置页（应用配置/模型配置）
- **面板式展示**：信息分组使用卡片 `bg-white rounded-2xl shadow-sm`
- **状态标签**：`badge` 组件，成功用绿、失败用红、处理中用金色

---

## 十、禁止事项

- **禁止使用 emoji** 替代图标 — 全部图标使用 `lucide-react`
- **禁止使用 antd 或 MUI** — 统一 Tailwind + daisyUI
- **禁止大面积使用金色** — 金色只作为点缀色，大面积金色显得廉价
- **禁止使用纯黑色**（`#000000`）— 深色使用 `#0f172a`、`#1a202c`
- **禁止过度装饰** — 每个装饰元素必须有功能意义，不可为了"好看"而添加无意义的装饰
- **禁止使用外部图片** — 所有装饰通过 CSS 实现
- **禁止使用滤镜（filter）改变关键内容颜色** — 仅用于背景装饰光晕
- **禁止在深色背景上使用纯白色文字** — 使用 `text-white/85` / `text-white/50` 层次
