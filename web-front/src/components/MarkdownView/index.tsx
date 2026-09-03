import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import DOMPurify from 'dompurify'
import { normalizeMarkdown } from '../../utils/markdown'

export default function MarkdownView({ content, className = '' }: { content: string; className?: string }) {
  const normalized = useMemo(() => normalizeMarkdown(DOMPurify.sanitize(content || '', {
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: [],
  })), [content])
  if (!content) return null
  return (
    <div className={`prose prose-sm max-w-none prose-p:my-2 prose-headings:my-3 prose-ul:my-2 text-slate-700 ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{normalized}</ReactMarkdown>
    </div>
  )
}
