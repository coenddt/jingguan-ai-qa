# UI 区域命名规则

## 规则说明

**所有 UI 区域必须使用中文名称作为元素的 `id` 属性值**，以便于代码阅读、调试和跨团队沟通。

## 命名规范

1. **格式**：`id="中文区域名"`
2. **命名方式**：功能描述 + 区域类型，如：
   - 搜索功能区
   - 搜索图标区
   - 搜索输入区
   - 导航栏
   - 标题区
   - 图片展示区
   - 按钮区
   - 列表区
   - 卡片区
3. **层级关系**：父级区域和子级区域使用相同的命名风格

## 示例

```wxml
<!-- ✅ 正确：使用中文 id 命名 UI 区域 -->
<view class="search-function-area" id="搜索功能区">
  <view class="search-input">
    <view class="search-icon-area" id="搜索图标区">
      <image class="search-input-icon" src="{{icons.search}}" />
    </view>
    <input class="search-input-area" id="搜索输入区" placeholder="搜索..." />
  </view>
</view>

<!-- ❌ 错误：使用英文或无意义的 id -->
<view class="search-function-area" id="searchArea">
  <view class="search-input">
    <image class="icon" src="{{icons.search}}" />
    <input class="input" placeholder="搜索..." />
  </view>
</view>
```

## 常见区域命名参考

| 区域类型 | 建议命名 |
|---------|---------|
| 导航区域 | 导航栏 / 导航左侧区 / 导航右侧区 / 导航中心区 |
| 搜索区域 | 搜索功能区 / 搜索图标区 / 搜索输入区 / 搜索展示区 / 搜索标题区 / 搜索图片展示区 |
| 内容区域 | 内容区 / 列表区 / 卡片区 / 网格区 |
| 按钮区域 | 操作区 / 按钮组 / 确认按钮区 / 取消按钮区 |
| 提示区域 | 提示区 / 风险提示区 / 状态提示区 |
