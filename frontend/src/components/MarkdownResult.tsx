import { useState } from 'react'
import { Copy, CheckCheck } from 'lucide-react'

interface Props {
  content: string
  title?: string
}

export default function MarkdownResult({ content, title = 'Result' }: Props) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!content) return null

  return (
    <div className="card mt-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-white">{title}</h3>
        <button onClick={copy} className="btn-secondary flex items-center gap-1.5 text-sm py-1.5 px-3">
          {copied ? <CheckCheck size={14} /> : <Copy size={14} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className="prose prose-invert prose-sm max-w-none bg-gray-800 rounded-lg p-4 text-gray-200 whitespace-pre-wrap font-mono text-sm leading-relaxed max-h-[520px] overflow-y-auto">
        {content}
      </div>
    </div>
  )
}
