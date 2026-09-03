# 核心布局规则

## 1. `<text>` 元素避免放入 flex 容器

**问题**：微信小程序中，`<text>` 元素作为 flex 子项时，会占满整行宽度，导致同行其他元素被推到下一行。

```wxml
<!-- ❌ 错误：text 在 flex 容器中 -->
<view style="display:flex;align-items:center">
  <text class="subtitle">标题文字</text>
  <image class="icon" src="..." />
</view>
```

**修复**：去掉中间层 wrapper，让 `<text>` 和兄弟元素作为直排兄弟节点，无需 flex 容器：

```wxml
<!-- ✅ 正确：text 和 image 直排，无 wrapper -->
<text class="subtitle" style="display:inline">标题文字</text>
<image class="icon" src="..." style="display:inline-block" />
```

## 2. 自定义组件（custom component）必须显式设置 inline 布局

**问题**：自定义组件的宿主节点默认 `display: block`，即使组件内容是 inline 元素，组件外壳也会独占一行。

**修复**：在组件标签上加 `style="display:inline-flex"`：

```wxml
<!-- ✅ 正确：copy-btn 加 inline-flex -->
<text class="subtitle" style="display:inline">标题文字</text>
<copy-btn text="标题文字" style="display:inline-flex" />
```

## 3. CSS Grid 一排固定卡片布局

**适用场景**：一排固定显示 N 个卡片（如 2 列分类卡片、4 列入口图标、2 列热门列表等）。

**规则**：必须使用 CSS Grid，禁止 flex + `calc()` 百分比方案。

**稳定性优势 (2026-08-11)**：在 iPhone 17 (iOS 26+) 等极新系统版本中，Flexbox 配合 `calc` 可能会因为子像素渲染误差导致原本横排的元素意外折行（变竖排）。CSS Grid 能够物理锁定列宽，是目前最稳定的横排多列实现方案。

### 标准实现模板

```css
/* ✅ 正确：CSS Grid 布局 */
.grid-container {
  display: grid;
  grid-template-columns: repeat(N, 1fr);  /* N 为每排固定卡片数 */
  gap: 24rpx;
  padding: 0 32rpx;
}

.grid-item {
  width: 100%;          /* 撑满单元格，由 grid 分配宽度 */
  box-sizing: border-box;
  /* 内部用 flex 做自适应布局 */
  display: flex;
  align-items: center;
  gap: 20rpx;
}
```

### 典型列数配置

| 场景 | grid-template-columns |
|------|----------------------|
| 2 列卡片 | `1fr 1fr` |
| 4 列入口 | `repeat(4, 1fr)` |
| 3 列网格 | `repeat(3, 1fr)` |

### 为什么用 Grid 而非 flex-wrap

| 对比项 | flex + calc() | CSS Grid |
|--------|--------------|----------|
| 宽度计算 | 手动 `calc(50% - 12rpx)` 易出错 | `1fr` 自动分配，gap 独立 |
| 响应式 | 换屏需重算百分比 | 天然自适应，无需调整 |
| 对齐 | 多行可能有微小偏差 | 严格对齐，等高 |
| 维护 | 改列数需重算 | 改 `repeat(N, 1fr)` 即可 |

### 内部自适应布局

Grid 单元格内部使用 flex 做自适应：
- 卡片横向排列：`display: flex; align-items: center;`
- 卡片纵向排列：`display: flex; flex-direction: column;`
- 文本截断：`flex: 1; min-width: 0; overflow: hidden;`

### 禁止的写法

```css
/* ❌ 禁止：flex-wrap + calc() 百分比 */
.grid-container {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}
.grid-item {
  width: calc(50% - 12rpx);  /* 改列数需重算 */
}

/* ❌ 禁止：flex: 1 等分（无 gap 支持或需 hack） */
.grid-container {
  display: flex;
}
.grid-item {
  flex: 1;  /* 无间距，需用 padding hack */
}
```

## 4. 注意点

- `virtualHost: true` 和 `:host` 选择器在部分微信版本不支持，不依赖
- `<text>` 组件只能包含文本和其他 `<text>` 节点，不能嵌套 `<view>`、`<image>`
- `<image>` 默认 `display:inline-block`，可作为直排兄弟元素使用
