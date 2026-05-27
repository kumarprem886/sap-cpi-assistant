import { useState } from 'react'
import { FileCode2, Loader2, Wand2, Eye, Layers } from 'lucide-react'
import { xsltAPI } from '../api/client'
import ResultPanel from '../components/ResultPanel'
import MarkdownResult from '../components/MarkdownResult'

type Tab = 'generate' | 'from-samples' | 'explain'

export default function XSLTGenerator() {
  const [tab, setTab] = useState<Tab>('generate')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')
  const [resultType, setResultType] = useState<'xml' | 'markdown'>('xml')

  const [genForm, setGenForm] = useState({ description: '', source_xml: '', target_xml: '', rules: '' })
  const [samplesForm, setSamplesForm] = useState({ source_xml: '', target_xml: '' })
  const [explainXslt, setExplainXslt] = useState('')

  const generate = async () => {
    setLoading(true)
    try {
      const res = await xsltAPI.generate(genForm)
      setResult(res.data.result)
      setResultType('xml')
    } finally { setLoading(false) }
  }

  const fromSamples = async () => {
    setLoading(true)
    try {
      const res = await xsltAPI.fromSamples(samplesForm)
      setResult(res.data.result)
      setResultType('xml')
    } finally { setLoading(false) }
  }

  const explain = async () => {
    setLoading(true)
    try {
      const res = await xsltAPI.explain(explainXslt)
      setResult(res.data.result)
      setResultType('markdown')
    } finally { setLoading(false) }
  }

  const tabs: { id: Tab; label: string; icon: typeof Wand2 }[] = [
    { id: 'generate', label: 'Generate', icon: Wand2 },
    { id: 'from-samples', label: 'From Samples', icon: Layers },
    { id: 'explain', label: 'Explain', icon: Eye },
  ]

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <FileCode2 size={24} className="text-orange-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">XSLT Generator</h1>
          <p className="text-gray-400 text-sm">Generate XSLT 2.0 transformations for SAP CPI</p>
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
            <label className="label">Transformation Goal *</label>
            <textarea className="textarea-field" rows={3} placeholder="e.g. Transform SAP IDOC XML to REST JSON-like XML for S/4HANA Sales Order creation" value={genForm.description} onChange={e => setGenForm(f => ({ ...f, description: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Source XML Sample (optional)</label>
              <textarea className="textarea-field" rows={8} placeholder="<root>&#10;  <OrderId>1234</OrderId>&#10;</root>" value={genForm.source_xml} onChange={e => setGenForm(f => ({ ...f, source_xml: e.target.value }))} />
            </div>
            <div>
              <label className="label">Target XML Sample (optional)</label>
              <textarea className="textarea-field" rows={8} placeholder="<SalesOrder>&#10;  <PONumber>1234</PONumber>&#10;</SalesOrder>" value={genForm.target_xml} onChange={e => setGenForm(f => ({ ...f, target_xml: e.target.value }))} />
            </div>
          </div>
          <div>
            <label className="label">Special Rules (optional)</label>
            <textarea className="textarea-field" rows={2} placeholder="e.g. If status is 'OPEN' map to '01', concatenate first and last name fields..." value={genForm.rules} onChange={e => setGenForm(f => ({ ...f, rules: e.target.value }))} />
          </div>
          <button className="btn-primary flex items-center gap-2" onClick={generate} disabled={loading || !genForm.description}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
            {loading ? 'Generating...' : 'Generate XSLT'}
          </button>
        </div>
      )}

      {tab === 'from-samples' && (
        <div className="card space-y-4">
          <p className="text-sm text-gray-400">Paste source and target XML samples — the AI will reverse-engineer the XSLT transformation.</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Source XML *</label>
              <textarea className="textarea-field" rows={12} placeholder="Paste source XML..." value={samplesForm.source_xml} onChange={e => setSamplesForm(f => ({ ...f, source_xml: e.target.value }))} />
            </div>
            <div>
              <label className="label">Target XML (desired output) *</label>
              <textarea className="textarea-field" rows={12} placeholder="Paste target XML..." value={samplesForm.target_xml} onChange={e => setSamplesForm(f => ({ ...f, target_xml: e.target.value }))} />
            </div>
          </div>
          <button className="btn-primary flex items-center gap-2" onClick={fromSamples} disabled={loading || !samplesForm.source_xml || !samplesForm.target_xml}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Layers size={16} />}
            {loading ? 'Generating...' : 'Generate XSLT from Samples'}
          </button>
        </div>
      )}

      {tab === 'explain' && (
        <div className="card space-y-4">
          <div>
            <label className="label">Paste XSLT</label>
            <textarea className="textarea-field" rows={14} placeholder="Paste your XSLT here..." value={explainXslt} onChange={e => setExplainXslt(e.target.value)} />
          </div>
          <button className="btn-primary flex items-center gap-2" onClick={explain} disabled={loading || !explainXslt}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
            {loading ? 'Analyzing...' : 'Explain XSLT'}
          </button>
        </div>
      )}

      {result && resultType === 'xml' && <ResultPanel result={result} language="xml" title="Generated XSLT" />}
      {result && resultType === 'markdown' && <MarkdownResult content={result} title="XSLT Explanation" />}
    </div>
  )
}
