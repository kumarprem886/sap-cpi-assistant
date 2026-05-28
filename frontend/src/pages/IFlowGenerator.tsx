import { useState, useRef } from 'react'
import { GitMerge, Loader2, Wand2, Eye, Download, FileCode, Upload, X, FileText, Paperclip, Cloud, CheckCircle, AlertCircle } from 'lucide-react'
import { iflowAPI, cpiAPI } from '../api/client'
import ResultPanel from '../components/ResultPanel'
import MarkdownResult from '../components/MarkdownResult'

const senderAdapters = ['HTTPS', 'Timer', 'SOAP', 'OData', 'SFTP', 'Kafka', 'AMQP', 'S4HANA']
const receiverAdapters = ['HTTP', 'HTTPS', 'OData', 'SOAP', 'SFTP', 'JDBC', 'Mail', 'ProcessDirect', 'Kafka', 'S4HANA']
const transformations = ['None', 'Message Mapping', 'XSLT', 'Groovy Script', 'Content Modifier', 'JSON to XML', 'XML to JSON']

type Tab = 'generate' | 'fd' | 'explain'

interface IFlowBundle {
  name: string
  iflw: string
  description: string
  scripts: Record<string, string>
  xsds?: Record<string, string>
  mmaps?: Record<string, string>
}

function ZipInfoBanner({ bundle, version }: { bundle: IFlowBundle; version: string }) {
  const scriptNames = Object.keys(bundle.scripts)
  const xsdNames    = Object.keys(bundle.xsds   ?? {})
  const mmapNames   = Object.keys(bundle.mmaps  ?? {})
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-700 px-4 py-3 text-xs text-gray-400 space-y-1 mt-2">
      <p className="text-gray-300 font-medium text-sm">📦 ZIP contents</p>
      <p>✔ <code>.project</code> · <code>metainfo.prop</code> · <code>META-INF/MANIFEST.MF</code></p>
      <p>✔ <code>parameters.prop</code> · <code>parameters.propdef</code> (auto-built from <code>{'{{params}}'}</code>)</p>
      <p>✔ <code>scenarioflows/integrationflow/{bundle.name || 'iflow'}.iflw</code></p>
      {scriptNames.length > 0 && <p>✔ Scripts: {scriptNames.map(s => <code key={s} className="mr-1">{s}</code>)}</p>}
      {xsdNames.length   > 0 && <p>✔ Schemas: {xsdNames.map(s => <code key={s} className="mr-1">{s}</code>)}</p>}
      {mmapNames.length  > 0 && <p>✔ Mappings: {mmapNames.map(s => <code key={s} className="mr-1">{s}</code>)}</p>}
      <p className="text-gray-500 pt-1">Import via SAP Integration Suite → Design → your package → Import</p>
    </div>
  )
}

export default function IFlowGenerator() {
  const [tab, setTab] = useState<Tab>('generate')
  const [loading, setLoading]         = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [bundle, setBundle]           = useState<IFlowBundle | null>(null)
  const [error, setError]             = useState('')
  const [explainXml, setExplainXml]       = useState('')
  const [explainResult, setExplainResult] = useState('')
  const [extractingZip, setExtractingZip] = useState(false)
  const [zipLoadedName, setZipLoadedName] = useState('')
  const explainZipRef = useRef<HTMLInputElement>(null)

  // ── Upload to CPI modal state ──────────────────────────────────────────────
  const [uploadModal, setUploadModal]         = useState(false)
  const [packages, setPackages]               = useState<{ id: string; name: string }[]>([])
  const [selectedPackage, setSelectedPackage] = useState('')
  const [loadingPkgs, setLoadingPkgs]         = useState(false)
  const [uploading, setUploading]             = useState(false)
  const [uploadResult, setUploadResult]       = useState<{ ok: boolean; msg: string } | null>(null)

  // ── Generate form ──────────────────────────────────────────────────────────
  const [form, setForm] = useState({
    name: '', description: '',
    sender_adapter: 'HTTPS', receiver_adapter: 'HTTP',
    transformation_type: 'None', include_error_handling: true,
    extra_steps: '', version: '1.0.0', package_id: '', package_name: '',
  })
  const setF = (k: string, v: string | boolean) => setForm(f => ({ ...f, [k]: v }))

  // ── FD form ────────────────────────────────────────────────────────────────
  const [fdFile, setFdFile]           = useState<File | null>(null)
  const [attachFiles, setAttachFiles] = useState<File[]>([])
  const [fdName, setFdName]           = useState('')
  const [fdVersion, setFdVersion]     = useState('1.0.0')
  const fdInputRef     = useRef<HTMLInputElement>(null)
  const attachInputRef = useRef<HTMLInputElement>(null)

  const switchTab = (t: Tab) => {
    setTab(t); setBundle(null); setError(''); setExplainResult('')
    setZipLoadedName(''); setExplainXml('')
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  const toBundle = (data: { result: string; scripts?: Record<string, string>; description?: string; name?: string; xsds?: Record<string, string>; mmaps?: Record<string, string> }, fallbackName: string): IFlowBundle => ({
    name:        data.name        || fallbackName,
    iflw:        data.result      || '',
    description: data.description || '',
    scripts:     data.scripts     || {},
    xsds:        data.xsds        || {},
    mmaps:       data.mmaps       || {},
  })

  const downloadZip = async (b: IFlowBundle, version: string) => {
    setDownloading(true)
    try {
      const res = await iflowAPI.downloadZip({
        xml: b.iflw, name: b.name, description: b.description,
        version, scripts: b.scripts, xsds: b.xsds, mmaps: b.mmaps,
      })
      const blob = new Blob([res.data], { type: 'application/zip' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url; a.download = `${b.name}.zip`; a.click()
      URL.revokeObjectURL(url)
    } finally { setDownloading(false) }
  }

  // ── Upload to CPI ─────────────────────────────────────────────────────────
  const openUploadModal = async () => {
    setUploadModal(true)
    setUploadResult(null)
    setLoadingPkgs(true)
    try {
      const res = await cpiAPI.packages()
      const pkgs = res.data as { id: string; name: string }[]
      setPackages(pkgs)
      if (pkgs.length > 0) setSelectedPackage(pkgs[0].id)
    } catch {
      setPackages([])
    } finally {
      setLoadingPkgs(false)
    }
  }

  const uploadToCPI = async () => {
    if (!bundle || !selectedPackage) return
    setUploading(true)
    setUploadResult(null)
    const version = tab === 'generate' ? form.version : fdVersion
    try {
      const res = await cpiAPI.importIflow({
        package_id:  selectedPackage,
        name:        bundle.name,
        version:     version || '1.0.0',
        description: bundle.description,
        xml:         bundle.iflw,
        scripts:     bundle.scripts,
        xsds:        bundle.xsds   ?? {},
        mmaps:       bundle.mmaps  ?? {},
      })
      const verb = res.data.status === 'updated' ? 'updated' : 'imported'
      setUploadResult({ ok: true, msg: `✓ iFlow "${bundle.name}" ${verb} successfully in package "${selectedPackage}". You can now deploy it from CPI Connect.` })
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Upload failed'
      setUploadResult({ ok: false, msg: String(msg) })
    } finally {
      setUploading(false)
    }
  }

  // ── Generate from form ─────────────────────────────────────────────────────
  const generate = async () => {
    if (!form.name || !form.description) return
    setLoading(true); setBundle(null); setError('')
    try {
      const res = await iflowAPI.generate(form)
      setBundle(toBundle(res.data, form.name))
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Generation failed'
      setError(String(msg))
    } finally { setLoading(false) }
  }

  // ── Generate from FD ───────────────────────────────────────────────────────
  const generateFromFD = async () => {
    if (!fdFile) return
    setLoading(true); setBundle(null); setError('')
    try {
      const res = await iflowAPI.fdToIflow(fdFile, attachFiles, fdName, fdVersion)
      setBundle(toBundle(res.data, fdName || res.data.name || 'GeneratedIFlow'))
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || 'Generation failed'
      setError(String(detail))
    } finally { setLoading(false) }
  }

  const removeAttach = (i: number) => setAttachFiles(f => f.filter((_, idx) => idx !== i))

  // ── Explain ────────────────────────────────────────────────────────────────
  const explain = async () => {
    if (!explainXml) return
    setLoading(true)
    try {
      const res = await iflowAPI.explain(explainXml)
      setExplainResult(res.data.result)
    } finally { setLoading(false) }
  }

  const extractFromZip = async (file: File) => {
    setExtractingZip(true)
    setZipLoadedName('')
    try {
      const res = await iflowAPI.extractXml(file)
      setExplainXml(res.data.xml)
      setZipLoadedName(res.data.name)
      setExplainResult('')
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Failed to extract ZIP'
      setError(String(msg))
    } finally {
      setExtractingZip(false)
    }
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <GitMerge size={24} className="text-sap-blue" />
        <div>
          <h1 className="text-2xl font-bold text-white">iFlow Generator</h1>
          <p className="text-gray-400 text-sm">Generate importable SAP CPI iFlow ZIPs — from scratch or from an FD document</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 p-1 rounded-lg w-fit mb-6 border border-gray-800">
        {([['generate', Wand2, 'Generate'], ['fd', FileText, 'FD → iFlow'], ['explain', Eye, 'Explain']] as const).map(([t, Icon, label]) => (
          <button key={t} onClick={() => switchTab(t as Tab)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${tab === t ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
            <Icon size={13} />{label}
          </button>
        ))}
      </div>

      {/* ── Generate tab ─────────────────────────────────────────────────── */}
      {tab === 'generate' && (
        <div className="card space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">iFlow Name *</label>
              <input className="input-field" placeholder="e.g. S4_to_Shroom_SalesOrder" value={form.name} onChange={e => setF('name', e.target.value)} />
            </div>
            <div>
              <label className="label">Transformation</label>
              <select className="select-field" value={form.transformation_type} onChange={e => setF('transformation_type', e.target.value)}>
                {transformations.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Description *</label>
            <textarea className="textarea-field" rows={2} placeholder="Describe what this iFlow should do..." value={form.description} onChange={e => setF('description', e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Sender / Trigger</label>
              <select className="select-field" value={form.sender_adapter} onChange={e => setF('sender_adapter', e.target.value)}>
                {senderAdapters.map(a => <option key={a}>{a}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Receiver Adapter</label>
              <select className="select-field" value={form.receiver_adapter} onChange={e => setF('receiver_adapter', e.target.value)}>
                {receiverAdapters.map(a => <option key={a}>{a}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Version</label>
              <input className="input-field" placeholder="1.0.0" value={form.version} onChange={e => setF('version', e.target.value)} />
            </div>
            <div>
              <label className="label">Package ID (optional)</label>
              <input className="input-field" placeholder="e.g. MyIntegrationPackage" value={form.package_id} onChange={e => setF('package_id', e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label">Additional Steps / Requirements</label>
            <textarea className="textarea-field" rows={2} placeholder="e.g. add CBR router, use OData v4, add content modifier for headers..." value={form.extra_steps} onChange={e => setF('extra_steps', e.target.value)} />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="eh" className="w-4 h-4 accent-sap-blue" checked={form.include_error_handling} onChange={e => setF('include_error_handling', e.target.checked)} />
            <label htmlFor="eh" className="text-sm text-gray-300">Include Exception Subprocess</label>
          </div>
          <div className="flex gap-3 flex-wrap">
            <button className="btn-primary flex items-center gap-2" onClick={generate} disabled={loading || !form.name || !form.description}>
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
              {loading ? 'Generating...' : 'Generate iFlow'}
            </button>
            {bundle && (
              <>
                <button className="btn-secondary flex items-center gap-2" onClick={() => downloadZip(bundle, form.version)} disabled={downloading}>
                  {downloading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                  {downloading ? 'Packaging...' : 'Download ZIP'}
                </button>
                <button className="btn-secondary flex items-center gap-2 !border-blue-700 !text-blue-300 hover:!bg-blue-900/30" onClick={openUploadModal}>
                  <Cloud size={16} /> Upload to CPI
                </button>
              </>
            )}
          </div>
          {error && (
            <div className="rounded-lg bg-red-950/50 border border-red-800 px-4 py-3 text-sm text-red-300">
              <span className="font-semibold">Error: </span>{error}
            </div>
          )}
          {bundle && <ZipInfoBanner bundle={bundle} version={form.version} />}
        </div>
      )}

      {/* ── FD → iFlow tab ──────────────────────────────────────────────── */}
      {tab === 'fd' && (
        <div className="card space-y-4">
          <p className="text-sm text-gray-400">
            Upload your Functional Design document. The AI will parse the FD text, analyse any embedded flow diagram image,
            and generate a complete importable iFlow ZIP — including Groovy scripts, parameters, and attached schemas.
          </p>

          {/* FD file upload */}
          <div>
            <label className="label">Functional Design Document (.docx) *</label>
            {fdFile ? (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-900 border border-gray-700">
                <FileText size={18} className="text-sap-blue flex-shrink-0" />
                <span className="text-sm text-gray-300 flex-1 truncate">{fdFile.name}</span>
                <span className="text-xs text-gray-500">{(fdFile.size / 1024).toFixed(0)} KB</span>
                <button onClick={() => setFdFile(null)} className="text-gray-500 hover:text-red-400"><X size={14} /></button>
              </div>
            ) : (
              <div onClick={() => fdInputRef.current?.click()}
                className="border-2 border-dashed border-gray-700 hover:border-sap-blue rounded-lg p-6 text-center cursor-pointer transition-colors">
                <Upload size={24} className="mx-auto mb-2 text-gray-500" />
                <p className="text-sm text-gray-400">Click to upload FD document</p>
                <p className="text-xs text-gray-600 mt-1">.docx files only</p>
              </div>
            )}
            <input ref={fdInputRef} type="file" accept=".docx" className="hidden"
              onChange={e => { if (e.target.files?.[0]) setFdFile(e.target.files[0]) }} />
          </div>

          {/* Attachment files */}
          <div>
            <label className="label flex items-center gap-2">
              <Paperclip size={13} /> Attachments — optional (XSD schemas, .mmap mappings, .groovy scripts)
            </label>
            <div className="space-y-2">
              {attachFiles.map((f, i) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-gray-900 border border-gray-800 text-sm">
                  <FileCode size={14} className="text-gray-500 flex-shrink-0" />
                  <span className="text-gray-300 flex-1 truncate">{f.name}</span>
                  <span className="text-xs text-gray-600">{(f.size / 1024).toFixed(0)} KB</span>
                  <button onClick={() => removeAttach(i)} className="text-gray-600 hover:text-red-400"><X size={12} /></button>
                </div>
              ))}
              <button onClick={() => attachInputRef.current?.click()}
                className="btn-secondary text-sm flex items-center gap-2 py-1.5">
                <Paperclip size={13} /> Add attachment
              </button>
            </div>
            <input ref={attachInputRef} type="file" multiple
              accept=".xsd,.wsdl,.mmap,.groovy,.txt,.xml,.csv" className="hidden"
              onChange={e => { if (e.target.files) setAttachFiles(f => [...f, ...Array.from(e.target.files!)]) }} />
          </div>

          {/* Optional overrides */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">iFlow Name override (optional)</label>
              <input className="input-field" placeholder="Auto-detected from FD" value={fdName} onChange={e => setFdName(e.target.value)} />
            </div>
            <div>
              <label className="label">Version</label>
              <input className="input-field" placeholder="1.0.0" value={fdVersion} onChange={e => setFdVersion(e.target.value)} />
            </div>
          </div>

          <div className="flex gap-3 flex-wrap">
            <button className="btn-primary flex items-center gap-2" onClick={generateFromFD} disabled={loading || !fdFile}>
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
              {loading ? 'Analysing FD...' : 'Analyse FD & Generate iFlow'}
            </button>
            {bundle && (
              <>
                <button className="btn-secondary flex items-center gap-2" onClick={() => downloadZip(bundle, fdVersion)} disabled={downloading}>
                  {downloading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                  {downloading ? 'Packaging...' : 'Download ZIP'}
                </button>
                <button className="btn-secondary flex items-center gap-2 !border-blue-700 !text-blue-300 hover:!bg-blue-900/30" onClick={openUploadModal}>
                  <Cloud size={16} /> Upload to CPI
                </button>
              </>
            )}
          </div>

          {error && (
            <div className="rounded-lg bg-red-950/50 border border-red-800 px-4 py-3 text-sm text-red-300">
              <span className="font-semibold">Error: </span>{error}
            </div>
          )}
          {bundle && <ZipInfoBanner bundle={bundle} version={fdVersion} />}
        </div>
      )}

      {/* ── Explain tab ───────────────────────────────────────────────────── */}
      {tab === 'explain' && (
        <div className="card space-y-4">

          {/* ZIP upload drop zone */}
          <div>
            <label className="label">Upload iFlow ZIP (optional)</label>
            <div
              onClick={() => explainZipRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
                zipLoadedName
                  ? 'border-green-500/50 bg-green-500/5'
                  : 'border-gray-700 hover:border-sap-blue'
              }`}
            >
              {extractingZip ? (
                <div className="flex items-center justify-center gap-2 text-gray-400 text-sm">
                  <Loader2 size={16} className="animate-spin" /> Extracting .iflw from ZIP…
                </div>
              ) : zipLoadedName ? (
                <div className="flex items-center justify-center gap-2 text-green-400 text-sm">
                  <CheckCircle size={16} />
                  <span className="font-medium">{zipLoadedName}.iflw</span>
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
              ref={explainZipRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={e => { if (e.target.files?.[0]) extractFromZip(e.target.files[0]); e.target.value = '' }}
            />
          </div>

          <div>
            <label className="label">iFlow XML (.iflw)</label>
            <textarea
              className="textarea-field"
              rows={12}
              placeholder="Paste your .iflw XML here, or upload a ZIP above…"
              value={explainXml}
              onChange={e => { setExplainXml(e.target.value); setZipLoadedName('') }}
            />
          </div>
          {error && (
            <div className="rounded-lg bg-red-950/50 border border-red-800 px-4 py-3 text-sm text-red-300">
              <span className="font-semibold">Error: </span>{error}
            </div>
          )}
          <button className="btn-primary flex items-center gap-2" onClick={explain} disabled={loading || !explainXml}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
            {loading ? 'Analyzing...' : 'Explain iFlow'}
          </button>
        </div>
      )}

      {/* ── Results ───────────────────────────────────────────────────────── */}
      {bundle && tab !== 'explain' && (
        <>
          <ResultPanel result={bundle.iflw} language="xml" title={`Generated iFlow XML — ${bundle.name}.iflw`} />
          {Object.keys(bundle.scripts).length > 0 && (
            <div className="mt-4 space-y-4">
              {Object.entries(bundle.scripts).map(([fname, src]) => (
                <div key={fname} className="card">
                  <div className="flex items-center gap-2 mb-3">
                    <FileCode size={16} className="text-sap-blue" />
                    <span className="font-semibold text-white text-sm">{fname}</span>
                  </div>
                  <pre className="bg-gray-950 rounded-lg border border-gray-800 text-gray-300 text-xs p-4 overflow-auto max-h-72">{src}</pre>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {explainResult && tab === 'explain' && <MarkdownResult content={explainResult} title="iFlow Analysis" />}

      {/* ── Upload to CPI Modal ──────────────────────────────────────────── */}
      {uploadModal && bundle && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl">

            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-white font-semibold text-lg flex items-center gap-2">
                <Cloud size={18} className="text-blue-400" /> Upload to CPI
              </h3>
              <button onClick={() => setUploadModal(false)} className="text-gray-500 hover:text-white transition-colors">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">

              {/* iFlow name (read-only) */}
              <div>
                <label className="label">iFlow Name</label>
                <div className="input-field bg-gray-800/60 text-gray-300 cursor-default select-text">{bundle.name}</div>
              </div>

              {/* Package picker */}
              <div>
                <label className="label">Target Package *</label>
                {loadingPkgs ? (
                  <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
                    <Loader2 size={14} className="animate-spin" /> Loading packages from CPI…
                  </div>
                ) : packages.length === 0 ? (
                  <div className="text-sm text-yellow-300 bg-yellow-950/30 border border-yellow-800 rounded-lg px-4 py-3">
                    No packages found on your CPI tenant. Create an integration package in SAP Integration Suite first, then try again.
                  </div>
                ) : (
                  <select className="select-field" value={selectedPackage} onChange={e => setSelectedPackage(e.target.value)}>
                    {packages.map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({p.id})</option>
                    ))}
                  </select>
                )}
              </div>

              {/* Info note */}
              {packages.length > 0 && !uploadResult && (
                <p className="text-xs text-gray-500">
                  The iFlow will be created in design-time. Go to <span className="text-gray-300">CPI Connect → Packages</span> to deploy it to runtime.
                  If an artifact with the same ID already exists it will be updated automatically.
                </p>
              )}

              {/* Result banner */}
              {uploadResult && (
                <div className={`flex items-start gap-3 rounded-lg px-4 py-3 text-sm ${
                  uploadResult.ok
                    ? 'bg-green-950/50 border border-green-700 text-green-300'
                    : 'bg-red-950/50 border border-red-800 text-red-300'
                }`}>
                  {uploadResult.ok
                    ? <CheckCircle size={16} className="mt-0.5 flex-shrink-0" />
                    : <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />}
                  <span>{uploadResult.msg}</span>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-3 justify-end pt-1">
                <button className="btn-secondary" onClick={() => setUploadModal(false)}>
                  {uploadResult?.ok ? 'Close' : 'Cancel'}
                </button>
                {!uploadResult?.ok && (
                  <button
                    className="btn-primary flex items-center gap-2"
                    onClick={uploadToCPI}
                    disabled={uploading || !selectedPackage || packages.length === 0}
                  >
                    {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                    {uploading ? 'Uploading…' : 'Import to CPI'}
                  </button>
                )}
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  )
}
