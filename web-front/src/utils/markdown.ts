/** 轻量规范化：去围栏残留/补空格，避免 LLM 输出残留标记 */
export function normalizeMarkdown(text: string): string {
  if (!text) return text
  return text
    .replace(/(^|\n)(#{1,6})(?=[^#\s])/g, '$1$2 ')
    .replace(/(^|\n)>(?=[^\s])/g, '$1> ')
    .replace(/(^|\n)([-+])(?=[^\s])/g, '$1$2 ')
}
