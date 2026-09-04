/** 剪贴板写入（AiCard/ChatMessage 复制共用） */
export async function copyToClipboard(text: string): Promise<void> {
  await navigator.clipboard.writeText(text)
}
