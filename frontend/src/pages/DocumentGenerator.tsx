import { useState, useRef } from 'react'
import { FileText, Loader2, Download, Upload, Wand2, ArrowRight, FileCode2, CheckCircle } from 'lucide-react'
import axios from 'axios'
import { iflowAPI } from '../api/client'

type Tab = 'fd' | 'fd-to-td' | 'iflow-to-td'

const adapters = ['HTTP', 'HTTPS', 'SOAP', 'REST', 'OData', 'SFTP', 'JDBC', 'Mail', 'AS2', 'AMQP', 'IDoc', 'RFC']
const processingTypes = ['IDOC', 'REST API', 'SOAP', 'File Transfer', 'RFC', 'OData', 'Event-based']
const complexities = ['High', 'Medium', 'Low']

function StatusBadge({ text, color }: { text: string; color: string }) {
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>{text}</span>
}

export default function DocumentGenerator() {
  const [tab, setTab] = useState<Tab>('fd')
  const [loading, setLoading] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [downloadName, setDownloadName] = useState('')
  const [error, setError] = useState('')
  const fileRef       = useRef<HTMLInputElement>(null)
  const iflowZipRef  = useRef<HTMLInputElement>(null)
  const [extractingZip, setExtractingZip] = useState(false)
  const [iflowZipName, setIflowZipName]   = useState('')

  // FD form
  const [fdForm, setFdForm] = useState({
    interface_id: '', interface_name: '', from_system: '', to_system: '',
    transformation_system: 'SAP CPI', processing_type: 'IDOC',
    idoc_message_type: '', idoc_basic_type: '', business_context: '',
    key_fields: '', author: '',
  })

  // FD to TD
  const [fdFile, setFdFile] = useState<File | null>(null)
  const [fdMeta, setFdMeta] = useState({ author: '', project_team: '', developer: '' })

  // iFlow to TD
  const [iflowForm, setIflowForm] = useState({
    iflow_xml: '', author: '', project_team: '', developer: '', extra_context: ''
  })

  const extractFromZip = async (file: File) => {
    setExtractingZip(true)
    setIflowZipName('')
    setError('')
    try {
      const res = await iflowAPI.extractXml(file)
      setIflowForm(f => ({ ...f, iflow_xml: res.data.xml }))
      setIflowZipName(res.data.name)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to extract ZIP')
    } finally {
      setExtractingZip(false)
    }
  }

  const triggerDownload = (blob: Blob, name: string) => {
    const url = URL.createObjectURL(blob)
    setDownloadUrl(url)
    setDownloadName(name)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
  }

  const generateFD = async () => {
    setLoading(true); setError(''); setDownloadUrl(null)
    try {
      const res = await axios.post('/api/docs/generate-fd', fdForm, { responseType: 'blob' })
      const cd = res.headers['content-disposition'] || ''
      const name = cd.match(/filename=(.+)/)?.[1] || `${fdForm.interface_id}_FD.docx`
      triggerDownload(res.data, name)
    } catch (e: any) {
      setError('Generation failed. Check that the backend is running.')
    } finally { setLoading(false) }
  }

  const generateFDtoTD = async () => {
    if (!fdFile) return
    setLoading(true); setError(''); setDownloadUrl(null)
    try {
      const form = new FormData()
      form.append('file', fdFile)
      form.append('author', fdMeta.author)
      form.append('project_team', fdMeta.project_team)
      form.append('developer', fdMeta.developer)
      const res = await axios.post('/api/docs/fd-to-td', form, { responseType: 'blob' })
      const cd = res.headers['content-disposition'] || ''
      const name = cd.match(/filename=(.+)/)?.[1] || 'TD.docx'
      triggerDownload(res.data, name)
    } catch (e: any) {
      setError('Generation failed. Check that the backend is running and the file is a valid .docx FD.')
    } finally { setLoading(false) }
  }

  const generateIFlowToTD = async () => {
    if (!iflowForm.iflow_xml) return
    setLoading(true); setError(''); setDownloadUrl(null)
    try {
      const res = await axios.post('/api/docs/iflow-to-td', iflowForm, { responseType: 'blob' })
      const cd = res.headers['content-disposition'] || ''
      const name = cd.match(/filename=(.+)/)?.[1] || 'TD_from_iFlow.docx'
      triggerDownload(res.data, name)
    } catch (e: any) {
      setError('Generation failed. Check that the backend is running.')
    } finally { setLoading(false) }
  }

  const tabs: { id: Tab; label: string; icon: typeof Wand2; badge?: string }[] = [
    { id: 'fd', label: 'FD Generator', icon: FileText, badge: 'New' },
    { id: 'fd-to-td', label: 'FD → TD', icon: ArrowRight, badge: 'New' },
    { id: 'iflow-to-td', label: 'iFlow → TD', icon: FileCode2, badge: 'New' },
  ]

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <FileText size={24} className="text-yellow-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Document Generator</h1>
          <p className="text-gray-400 text-sm">AI-powered FD and TD document generation</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 p-1 rounded-lg w-fit mb-6 border border-gray-800">
        {tabs.map(({ id, label, icon: Icon, badge }) => (
          <button key={id} onClick={() => { setTab(id); setDownloadUrl(null); setError('') }}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${tab === id ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
            <Icon size={13} />{label}
            {badge && <span className="text-xs bg-green-500/20 text-green-400 px-1.5 rounded-full">{badge}</span>}
          </button>
        ))}
      </div>

      {/* ── FD Generator ─────────────────────────────────────── */}
      {tab === 'fd' && (
        <div className="card space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Interface ID *</label>
              <input className="input-field" placeholder="e.g. FDMAP_I_001V" value={fdForm.interface_id} onChange={e => setFdForm(f => ({ ...f, interface_id: e.target.value }))} />
            </div>
            <div>
              <label className="label">Author</label>
              <input className="input-field" placeholder="Your name" value={fdForm.author} onChange={e => setFdForm(f => ({ ...f, author: e.target.value }))} />
            </div>
          </div>

          <div>
            <label className="label">Interface Name *</label>
            <input className="input-field" placeholder="e.g. Material Master OUT MATMAS from ERP to Shroom" value={fdForm.interface_name} onChange={e => setFdForm(f => ({ ...f, interface_name: e.target.value }))} />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">From System *</label>
              <input className="input-field" placeholder="e.g. SAP S/4HANA" value={fdForm.from_system} onChange={e => setFdForm(f => ({ ...f, from_system: e.target.value }))} />
            </div>
            <div>
              <label className="label">Transformation System</label>
              <input className="input-field" value={fdForm.transformation_system} onChange={e => setFdForm(f => ({ ...f, transformation_system: e.target.value }))} />
            </div>
            <div>
              <label className="label">To System *</label>
              <input className="input-field" placeholder="e.g. Shroom WMS" value={fdForm.to_system} onChange={e => setFdForm(f => ({ ...f, to_system: e.target.value }))} />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">Processing Type</label>
              <select className="select-field" value={fdForm.processing_type} onChange={e => setFdForm(f => ({ ...f, processing_type: e.target.value }))}>
                {processingTypes.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="label">IDOC Message Type</label>
              <input className="input-field" placeholder="e.g. MATMAS" value={fdForm.idoc_message_type} onChange={e => setFdForm(f => ({ ...f, idoc_message_type: e.target.value }))} />
            </div>
            <div>
              <label className="label">IDOC Basic Type</label>
              <input className="input-field" placeholder="e.g. MATMAS03" value={fdForm.idoc_basic_type} onChange={e => setFdForm(f => ({ ...f, idoc_basic_type: e.target.value }))} />
            </div>
          </div>

          <div>
            <label className="label">Business Context *</label>
            <textarea className="textarea-field" rows={3} placeholder="Describe what this interface does and why it exists..." value={fdForm.business_context} onChange={e => setFdForm(f => ({ ...f, business_context: e.target.value }))} />
          </div>

          <div>
            <label className="label">Key Data Fields to Transfer</label>
            <textarea className="textarea-field" rows={3} placeholder="e.g. Material Number, Description, Base Unit of Measure, Material Type, Plant Data..." value={fdForm.key_fields} onChange={e => setFdForm(f => ({ ...f, key_fields: e.target.value }))} />
          </div>

          <button className="btn-primary flex items-center gap-2" onClick={generateFD}
            disabled={loading || !fdForm.interface_id || !fdForm.interface_name || !fdForm.from_system || !fdForm.to_system || !fdForm.business_context}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
            {loading ? 'Generating FD Document...' : 'Generate FD (.docx)'}
          </button>
        </div>
      )}

      {/* ── FD to TD ─────────────────────────────────────────── */}
      {tab === 'fd-to-td' && (
        <div className="card space-y-4">
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 text-sm text-blue-300">
            Upload your FD (.docx) — the AI will read it, extract all details, and generate a complete TD with all sections properly filled (no empty appendix placeholders).
          </div>

          <div>
            <label className="label">Upload FD Document (.docx) *</label>
            <div
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${fdFile ? 'border-green-500/50 bg-green-500/5' : 'border-gray-700 hover:border-sap-blue'}`}
              onClick={() => fileRef.current?.click()}
            >
              <input ref={fileRef} type="file" accept=".docx" className="hidden"
                onChange={e => setFdFile(e.target.files?.[0] || null)} />
              {fdFile ? (
                <div className="flex items-center justify-center gap-2 text-green-400">
                  <FileText size={20} />
                  <span className="font-medium">{fdFile.name}</span>
                  <StatusBadge text="Ready" color="bg-green-500/20 text-green-400" />
                </div>
              ) : (
                <div className="text-gray-500">
                  <Upload size={24} className="mx-auto mb-2" />
                  <p>Click to upload FD document</p>
                  <p className="text-xs mt-1">.docx files only</p>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">Author</label>
              <input className="input-field" placeholder="Author name" value={fdMeta.author} onChange={e => setFdMeta(f => ({ ...f, author: e.target.value }))} />
            </div>
            <div>
              <label className="label">Project Team</label>
              <input className="input-field" placeholder="Team name" value={fdMeta.project_team} onChange={e => setFdMeta(f => ({ ...f, project_team: e.target.value }))} />
            </div>
            <div>
              <label className="label">Integration Developer</label>
              <input className="input-field" placeholder="Developer name" value={fdMeta.developer} onChange={e => setFdMeta(f => ({ ...f, developer: e.target.value }))} />
            </div>
          </div>

          <button className="btn-primary flex items-center gap-2" onClick={generateFDtoTD} disabled={loading || !fdFile}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
            {loading ? 'Converting FD → TD...' : 'Generate TD from FD (.docx)'}
          </button>
        </div>
      )}

      {/* ── iFlow to TD ───────────────────────────────────────── */}
      {tab === 'iflow-to-td' && (
        <div className="card space-y-4">
          <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4 text-sm text-orange-300">
            Upload an iFlow ZIP or paste the XML — the AI will analyse all adapters, steps, mappings and generate a complete TD document.
          </div>

          {/* ZIP upload */}
          <div>
            <label className="label">Upload iFlow ZIP (optional)</label>
            <div
              onClick={() => iflowZipRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
                iflowZipName
                  ? 'border-green-500/50 bg-green-500/5'
                  : 'border-gray-700 hover:border-sap-blue'
              }`}
            >
              {extractingZip ? (
                <div className="flex items-center justify-center gap-2 text-gray-400 text-sm">
                  <Loader2 size={16} className="animate-spin" /> Extracting .iflw from ZIP…
                </div>
              ) : iflowZipName ? (
                <div className="flex items-center justify-center gap-2 text-green-400 text-sm">
                  <CheckCircle size={16} />
                  <span className="font-medium">{iflowZipName}.iflw</span>
                  <span className="text-green-600 text-xs">— XML loaded below</span>
                </div>
              ) : (
                <div className="text-gray-500 text-sm">
                  <Upload size={20} className="mx-auto mb-1" />
                  <p>Click to upload an iFlow ZIP to auto-extract the XML</p>
                  <p className="text-xs mt-0.5 text-gray-600">Or paste the XML directly below</p>
                </div>
              )}
            </div>
            <input
              ref={iflowZipRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={e => { if (e.target.files?.[0]) extractFromZip(e.target.files[0]); e.target.value = '' }}
            />
          </div>

          <div>
            <label className="label">iFlow XML *</label>
            <textarea
              className="textarea-field"
              rows={10}
              placeholder="Paste your SAP CPI iFlow XML here, or upload a ZIP above…"
              value={iflowForm.iflow_xml}
              onChange={e => { setIflowForm(f => ({ ...f, iflow_xml: e.target.value })); setIflowZipName('') }}
            />
          </div>

          <div>
            <label className="label">Additional Context (optional)</label>
            <textarea className="textarea-field" rows={2} placeholder="e.g. This iFlow handles Material Master sync from S/4HANA to Shroom WMS..." value={iflowForm.extra_context} onChange={e => setIflowForm(f => ({ ...f, extra_context: e.target.value }))} />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">Author</label>
              <input className="input-field" placeholder="Author name" value={iflowForm.author} onChange={e => setIflowForm(f => ({ ...f, author: e.target.value }))} />
            </div>
            <div>
              <label className="label">Project Team</label>
              <input className="input-field" placeholder="Team name" value={iflowForm.project_team} onChange={e => setIflowForm(f => ({ ...f, project_team: e.target.value }))} />
            </div>
            <div>
              <label className="label">Integration Developer</label>
              <input className="input-field" placeholder="Developer name" value={iflowForm.developer} onChange={e => setIflowForm(f => ({ ...f, developer: e.target.value }))} />
            </div>
          </div>

          <button className="btn-primary flex items-center gap-2" onClick={generateIFlowToTD} disabled={loading || !iflowForm.iflow_xml}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <FileCode2 size={16} />}
            {loading ? 'Generating TD from iFlow...' : 'Generate TD from iFlow (.docx)'}
          </button>
        </div>
      )}

      {/* Status */}
      {error && (
        <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {downloadUrl && !loading && (
        <div className="mt-4 bg-green-500/10 border border-green-500/30 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-green-400">
            <FileText size={18} />
            <span className="font-medium">{downloadName}</span>
            <StatusBadge text="Generated" color="bg-green-500/20 text-green-400" />
          </div>
          <a href={downloadUrl} download={downloadName} className="btn-primary flex items-center gap-2 text-sm py-1.5 px-3">
            <Download size={14} /> Download Again
          </a>
        </div>
      )}
    </div>
  )
}
