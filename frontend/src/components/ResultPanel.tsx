import { useState } from 'react'
import { Copy, CheckCheck } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface Props {
  result: string
  language?: string
  title?: string
}

export default function ResultPanel({ result, language = 'xml', title = 'Generated Output' }: Props) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(result)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!result) return null

  return (
    <div className="card mt-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-white">{title}</h3>
        <button onClick={copy} className="btn-secondary flex items-center gap-1.5 text-sm py-1.5 px-3">
          {copied ? <CheckCheck size={14} /> : <Copy size={14} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className="rounded-lg overflow-hidden border border-gray-800">
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          customStyle={{ margin: 0, borderRadius: 0, fontSize: '13px', maxHeight: '520px' }}
          showLineNumbers
        >
          {result}
        </SyntaxHighlighter>
      </div>
    </div>
  )
}
