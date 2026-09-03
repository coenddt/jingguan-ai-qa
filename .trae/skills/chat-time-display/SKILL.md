---
name: "chat-time-display"
description: "Chat message time label algorithm: show time separators intelligently (not every message). Invoke when adding time display to chat message lists or implementing similar smart time formatting."
---

# 聊天消息时间分隔显示方案

聊天消息列表不在每条消息上显示时间，只在合适的时机插入时间分隔符——减少视觉噪音，保留上下文参照系。

**目录**：`miniapp/pages/chat/`

## 显示规则

| 条件 | 显示内容 | 示例 |
|:---|:---|:---|
| 第一条消息 / 跨天 | 日期前缀 + 时间 | `今天 14:30` / `昨天 09:15` / `6月1日 10:00` |
| 同一天，间隔 > 5 分钟 | 仅时间 | `14:45` |
| 同一天，间隔 ≤ 5 分钟 | **不显示** | — |

## 核心算法

```js
function pad(n) { return n.toString().padStart(2, '0') }

function isSameDay(d1, d2) {
  return d1.getFullYear() === d2.getFullYear()
    && d1.getMonth() === d2.getMonth()
    && d1.getDate() === d2.getDate()
}

// currentDate - 当前消息时间；prevDate - 上条消息时间（null 为首条）；now - 当前时间
function formatTimeLabel(currentDate, prevDate, now) {
  var nowDate = now || new Date()
  var timeStr = pad(currentDate.getHours()) + ':' + pad(currentDate.getMinutes())

  if (!prevDate) return formatDatePrefix(currentDate, nowDate) + ' ' + timeStr   // 首条：完整日期+时间
  if (!isSameDay(currentDate, prevDate)) return formatDatePrefix(currentDate, nowDate) + ' ' + timeStr  // 跨天
  if ((currentDate - prevDate) / (1000 * 60) > 5) return timeStr  // > 5 分钟：仅时间
  return ''  // ≤ 5 分钟：不显示
}

function formatDatePrefix(date, now) {
  if (isSameDay(date, now)) return '今天'
  var yesterday = new Date(now); yesterday.setDate(yesterday.getDate() - 1)
  if (isSameDay(date, yesterday)) return '昨天'
  return (date.getMonth() + 1) + '月' + date.getDate() + '日'
}
```

## 消息标注方法

遍历消息数组，注入 `_showTime` 和 `_timeLabel` 字段：

```js
function enrichMessagesWithTime(messages) {
  var now = new Date()
  return messages.map(function(msg, index) {
    var prevMsg = index > 0 ? messages[index - 1] : null
    var label = formatTimeLabel(new Date(msg.createdAt), prevMsg ? new Date(prevMsg.createdAt) : null, now)
    return { ...msg, _timeLabel: label, _showTime: label !== '' }
  })
}
```

## WXML 渲染

```xml
<block wx:for="{{messages}}" wx:key="id">
  <view wx:if="{{item._showTime}}" class="time-separator">{{item._timeLabel}}</view>
  <view>...</view>
</block>
```

```css
.time-separator {
  display: flex; align-items: center; justify-content: center;
  margin: 36rpx 0 20rpx; font-size: 22rpx; color: #b0b0b0;
}
```

## 调用时机

每次消息列表变更时调用 `enrichMessagesWithTime`：

- 加载历史消息后（`loadHistory`）
- 合并新消息时（`mergeRemindersIntoMessages`）
- 新增消息时（`addMessage`）
- 流式追加（`appendToMessage`）不需要调用——只追加内容，不新增条目

参考 `miniapp/pages/chat/chat.js` 中的调用点及对应 WXML/WXSS。

## 禁止事项

❌ 不要在每条消息上显示时间  
❌ 不要用 `###` 及以上层级标题  
❌ 不要堆砌视觉元素（分割线、图标等干扰项）  

## 注意事项

1. `enrichMessagesWithTime` 必须是幂等的——多次调用不会产生重复时间标签
2. `prevDate` 取上一条消息的 `createdAt`，不是当前消息的前一条渲染结果
3. 跨天判断用 `isSameDay`，不要手动比较年月日字符串
