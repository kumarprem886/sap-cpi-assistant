import { useState } from 'react'
import { MessageSquare, Loader2, Send, Star, Shield } from 'lucide-react'
import { chatAPI } from '../api/client'
import MarkdownResult from '../components/MarkdownResult'
import ResultPanel from '../components/ResultPanel'

type Mode = 'ask' | 'review'

const quickQuestions = [
  'How do I configure CSRF token handling in CPI HTTP adapter?',
  'What is the difference between Exchange Property and Message Header in CPI?',
  'How to implement retry logic in SAP CPI iFlow?',
  'Best practices for error handling in SAP CPI',
  'How to call an OData service from SAP CPI?',
  'How to decode Base64 encoded payload in Groovy?',
]

export default function ChatAssistant() {
  const [mode, setMode] = useState<Mode>('ask')
  const [loading, setLoading] = useState(false)
  const [question, setQuestion] = useState('')
  const [context, setContext] = useState('')
  const [result, setResult] = useState('')

  const [reviewForm, setReviewForm] = useState({ code: '', code_type: 'groovy', context: '' })
  const [reviewResult, setReviewResult] = useState('')

  const ask = async (q?: string) => {
    const q_ = q || question
    if (!q_) return
    if (q) setQuestion(q)
    setLoading(true)
    try {
      const res = await chatAPI.ask(q_, context)
      setResult(res.data.result)
    } finally { setLoading(false) }
  }

  const review = async () => {
    setLoading(true)
    try {
      const res = await chatAPI.review(reviewForm)
      setReviewResult(res.data.result)
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <MessageSquare size={24} className="text-cyan-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">AI Assistant</h1>
          <p className="text-gray-400 text-sm">Ask anything about SAP CPI or get your code reviewed</p>
        </div>
      </div>

      <div className="flex gap-1 bg-gray-900 p-1 rounded-lg w-fit mb-6 border border-gray-800">
        <button onClick={() => setMode('ask')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${mode === 'ask' ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
          <MessageSquare size={13} />Ask a Question
        </button>
        <button onClick={() => setMode('review')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${mode === 'review' ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
          <Shield size={13} />Code Review
        </button>
      </div>

      {mode === 'ask' && (
        <>
          {/* Quick questions */}
          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-2 flex items-center gap-1"><Star size={11} />Quick questions</p>
            <div className="flex flex-wrap gap-2">
              {quickQuestions.map(q => (
                <button key={q} onClick={() => ask(q)} className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 px-3 py-1.5 rounded-full transition-colors text-left">
                  {q}
                </button>
              ))}
            </div>
          </div>

          <div className="card space-y-4">
            <div>
              <label className="label">Your Question *</label>
              <textarea className="textarea-field" rows={4} placeholder="Ask anything about SAP CPI — adapter configuration, scripting, best practices, error resolution..." value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) ask() }} />
              <p className="text-xs text-gray-600 mt-1">Ctrl+Enter to submit</p>
            </div>
            <div>
              <label className="label">Context (optional)</label>
              <textarea className="textarea-field" rows={3} placeholder="Paste relevant code, XML, or error message for context..." value={context} onChange={e => setContext(e.target.value)} />
            </div>
            <button className="btn-primary flex items-center gap-2" onClick={() => ask()} disabled={loading || !question}>
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              {loading ? 'Thinking...' : 'Ask Claude'}
            </button>
          </div>

          {result && <MarkdownResult content={result} title="Answer" />}
        </>
      )}

      {mode === 'review' && (
        <>
          <div className="card space-y-4">
            <div>
              <label className="label">Code Type</label>
              <div className="flex gap-4">
                {['groovy', 'xslt', 'xml', 'javascript'].map(t => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="code_type" value={t} checked={reviewForm.code_type === t} onChange={() => setReviewForm(f => ({ ...f, code_type: t }))} className="accent-sap-blue" />
                    <span className="text-sm text-gray-300 capitalize">{t}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Code to Review *</label>
              <textarea className="textarea-field" rows={12} placeholder="Paste your code here for AI review..." value={reviewForm.code} onChange={e => setReviewForm(f => ({ ...f, code: e.target.value }))} />
            </div>
            <div>
              <label className="label">Context (optional)</label>
              <textarea className="textarea-field" rows={2} placeholder="e.g. This script processes SuccessFactors employee data..." value={reviewForm.context} onChange={e => setReviewForm(f => ({ ...f, context: e.target.value }))} />
            </div>
            <button className="btn-primary flex items-center gap-2" onClick={review} disabled={loading || !reviewForm.code}>
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Shield size={16} />}
              {loading ? 'Reviewing...' : 'Review Code'}
            </button>
          </div>

          {reviewResult && <MarkdownResult content={reviewResult} title="Code Review" />}
        </>
      )}
    </div>
  )
}
