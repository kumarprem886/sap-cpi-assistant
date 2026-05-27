import { useState } from 'react'
import { Code2, Loader2, Wand2, Eye, Bug } from 'lucide-react'
import { groovyAPI } from '../api/client'
import ResultPanel from '../components/ResultPanel'
import MarkdownResult from '../components/MarkdownResult'

type Tab = 'generate' | 'explain' | 'debug'

const scriptTypes = [
  { value: 'message_transform', label: 'Message Transformation' },
  { value: 'header_property', label: 'Headers & Properties' },
  { value: 'http_call', label: 'HTTP Call' },
  { value: 'json_xml', label: 'JSON ↔ XML Conversion' },
  { value: 'exception_handler', label: 'Exception Handler' },
  { value: 'splitter', label: 'Message Splitter' },
  { value: 'aggregator', label: 'Message Aggregator' },
]

export default function GroovyGenerator() {
  const [tab, setTab] = useState<Tab>('generate')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')
  const [resultType, setResultType] = useState<'groovy' | 'markdown'>('groovy')

  const [genForm, setGenForm] = useState({ task: '', context: '', script_type: 'message_transform' })
  const [explainScript, setExplainScript] = useState('')
  const [debugForm, setDebugForm] = useState({ script: '', error: '', message_payload: '' })

  const generate = async () => {
    setLoading(true)
    try {
      const res = await groovyAPI.generate(genForm)
      setResult(res.data.result)
      setResultType('groovy')
    } finally { setLoading(false) }
  }

  const explain = async () => {
    setLoading(true)
    try {
      const res = await groovyAPI.explain(explainScript)
      setResult(res.data.result)
      setResultType('markdown')
    } finally { setLoading(false) }
  }

  const debug = async () => {
    setLoading(true)
    try {
      const res = await groovyAPI.debug(debugForm)
      setResult(res.data.result)
      setResultType('markdown')
    } finally { setLoading(false) }
  }

  const tabs: { id: Tab; label: string; icon: typeof Wand2 }[] = [
    { id: 'generate', label: 'Generate', icon: Wand2 },
    { id: 'explain', label: 'Explain', icon: Eye },
    { id: 'debug', label: 'Debug', icon: Bug },
  ]

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Code2 size={24} className="text-purple-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Groovy Scripts</h1>
          <p className="text-gray-400 text-sm">Generate, explain, and debug Groovy scripts for SAP CPI</p>
        </div>
      </div>

      <div className="flex gap-1 bg-gray-900 p-1 rounded-lg w-fit mb-6 border border-gray-800">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => { setTab(id); setResult('') }} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${tab === id ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
            <Icon size={13} />{label}
          </button>
        ))}
      </div>

      {tab === 'generate' && (
        <div className="card space-y-4">
          <div>
            <label className="label">Script Type</label>
            <select className="select-field" value={genForm.script_type} onChange={e => setGenForm(f => ({ ...f, script_type: e.target.value }))}>
              {scriptTypes.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
            </select>
          </div>
          <div>
            <label className="label">What should the script do? *</label>
            <textarea className="textarea-field" rows={3} placeholder="e.g. Read the JSON payload, extract the 'orderId' field, and set it as a message property called 'OrderID'" value={genForm.task} onChange={e => setGenForm(f => ({ ...f, task: e.target.value }))} />
          </div>
          <div>
            <label className="label">Additional Context (optional)</label>
            <textarea className="textarea-field" rows={3} placeholder="e.g. Sample payload, field names, expected output format..." value={genForm.context} onChange={e => setGenForm(f => ({ ...f, context: e.target.value }))} />
          </div>
          <button className="btn-primary flex items-center gap-2" onClick={generate} disabled={loading || !genForm.task}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
            {loading ? 'Generating...' : 'Generate Script'}
          </button>
        </div>
      )}

      {tab === 'explain' && (
        <div className="card space-y-4">
          <div>
            <label className="label">Paste Groovy Script</label>
            <textarea className="textarea-field" rows={14} placeholder="Paste your Groovy script here..." value={explainScript} onChange={e => setExplainScript(e.target.value)} />
          </div>
          <button className="btn-primary flex items-center gap-2" onClick={explain} disabled={loading || !explainScript}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
            {loading ? 'Analyzing...' : 'Explain Script'}
          </button>
        </div>
      )}

      {tab === 'debug' && (
        <div className="card space-y-4">
          <div>
            <label className="label">Failing Script *</label>
            <textarea className="textarea-field" rows={8} placeholder="Paste the script that is failing..." value={debugForm.script} onChange={e => setDebugForm(f => ({ ...f, script: e.target.value }))} />
          </div>
          <div>
            <label className="label">Error Message *</label>
            <textarea className="textarea-field" rows={3} placeholder="Paste the error message from CPI monitoring..." value={debugForm.error} onChange={e => setDebugForm(f => ({ ...f, error: e.target.value }))} />
          </div>
          <div>
            <label className="label">Message Payload (optional)</label>
            <textarea className="textarea-field" rows={4} placeholder="Paste the message payload that caused the error..." value={debugForm.message_payload} onChange={e => setDebugForm(f => ({ ...f, message_payload: e.target.value }))} />
          </div>
          <button className="btn-primary flex items-center gap-2" onClick={debug} disabled={loading || !debugForm.script || !debugForm.error}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Bug size={16} />}
            {loading ? 'Debugging...' : 'Debug Script'}
          </button>
        </div>
      )}

      {result && resultType === 'groovy' && <ResultPanel result={result} language="groovy" title="Generated Groovy Script" />}
      {result && resultType === 'markdown' && <MarkdownResult content={result} title={tab === 'explain' ? 'Script Explanation' : 'Debug Analysis'} />}
    </div>
  )
}
