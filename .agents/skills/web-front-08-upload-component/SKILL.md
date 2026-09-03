---
name: "web-front-08-upload-component"
description: "web-front 文件上传指南：daisyUI 基础文件上传、台账 Excel/CSV 导入（/api/import/upload）。实现文件上传功能时调用。"
---

# 文件上传指南（web-front/）

## 概述

当前项目未有封装好的上传组件，文件上传功能通过基本的 daisyUI 组件 + 文件输入实现。

## 本项目上传场景

### 台账导入（ImportDialog）
- 入口：问数页数据源选择区的导入入口
- 上传目标：`POST /api/import/upload`（FormData，Excel/CSV）
- 导入记录查询：`GET /api/import/log`

## 上传实现建议

### 基础文件上传

```tsx
import { useState } from 'react'
import type { ChangeEvent } from 'react'
import { Upload } from 'lucide-react'
import { http } from '../../api/client'

const [selectedFile, setSelectedFile] = useState<File | null>(null)

const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
  setSelectedFile(event.target.files?.[0] ?? null)
}

const handleUpload = async () => {
  if (!selectedFile) return

  const formData = new FormData()
  formData.append('file', selectedFile)

  try {
    const res = await http.post('/import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    // 处理上传结果（配合 useSnackbar 提示）
  } catch (error) {
    // 处理错误
  }
}

// 渲染
<label className="btn btn-primary cursor-pointer whitespace-nowrap">
  <Upload size={20} />
  选择文件
  <input type="file" className="hidden" onChange={handleFileChange} />
</label>
```

### 拖拽上传区域

```jsx
<div
  className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-primary transition-colors"
  onDragOver={(e) => e.preventDefault()}
  onDrop={handleDrop}
>
  <Upload size={40} className="mx-auto text-gray-400" />
  <p className="text-gray-500 mt-2">拖拽文件到此处或点击上传</p>
</div>
```

## 注意事项

- 认证走 Cookie（`withCredentials`），FormData 无需附加 token
- 上传成功/失败用 `useSnackbar` + `SnackbarAlert` 反馈
- 大文件或慢网络时按钮需 loading 态，防止重复提交
