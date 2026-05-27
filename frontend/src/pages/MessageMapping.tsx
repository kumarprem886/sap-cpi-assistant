import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Shuffle, Loader2, Wand2, Zap, Upload, X, FileCode,
  Package, Cpu, BookOpen, ArrowRight, ChevronDown, ChevronUp,
  CheckCircle2, Clock, RefreshCw, Download, Eye, FileSpreadsheet,
  AlertCircle,
} from 'lucide-react'
import { mappingAPI } from '../api/client'
import { IS_STATIC_HOST } from '../components/Layout'
import ResultPanel from '../components/ResultPanel'
import MarkdownResult from '../components/MarkdownResult'

const outputFormats = [
  { value: 'groovy', label: 'Groovy Script' },
  { value: 'xslt', label: 'XSLT' },
  { value: 'description', label: 'Mapping Table (Description)' },
]

// Must match the IDs in prebuilt_mapper.py CATALOG_PAIRS
const CATALOG_PAIRS = [
  { id: 'MATMAS05_to_A_Product',          label: 'Material Master → Product OData',        src: 'MATMAS05.xsd',         tgt: 'A_Product.xsd',          name: 'MM_MATMAS_to_Product',          group: 'Material' },
  { id: 'A_Product_to_MATMAS05',          label: 'Product OData → Material Master',        src: 'A_Product.xsd',         tgt: 'MATMAS05.xsd',           name: 'MM_Product_to_MATMAS',          group: 'Material' },
  { id: 'DEBMAS06_to_A_BusinessPartner',  label: 'Customer Master → Business Partner',     src: 'DEBMAS06.xsd',          tgt: 'A_BusinessPartner.xsd',  name: 'MM_DEBMAS_to_BusinessPartner',  group: 'Customer' },
  { id: 'A_BusinessPartner_to_DEBMAS06',  label: 'Business Partner → Customer Master',     src: 'A_BusinessPartner.xsd', tgt: 'DEBMAS06.xsd',           name: 'MM_BusinessPartner_to_DEBMAS',  group: 'Customer' },
  { id: 'CREMAS05_to_A_Supplier',         label: 'Vendor Master → Supplier OData',         src: 'CREMAS05.xsd',          tgt: 'A_Supplier.xsd',         name: 'MM_CREMAS_to_Supplier',         group: 'Vendor' },
  { id: 'A_Supplier_to_CREMAS05',         label: 'Supplier OData → Vendor Master',         src: 'A_Supplier.xsd',        tgt: 'CREMAS05.xsd',           name: 'MM_Supplier_to_CREMAS',         group: 'Vendor' },
  { id: 'CREMAS05_to_A_BusinessPartner',  label: 'Vendor Master → Business Partner',       src: 'CREMAS05.xsd',          tgt: 'A_BusinessPartner.xsd',  name: 'MM_CREMAS_to_BusinessPartner',  group: 'Vendor' },
  { id: 'ORDERS05_to_A_PurchaseOrder',    label: 'Purchase Order IDoc → OData',            src: 'ORDERS05.xsd',          tgt: 'A_PurchaseOrder.xsd',    name: 'MM_ORDERS_to_PurchaseOrder',    group: 'Procurement' },
  { id: 'A_PurchaseOrder_to_ORDERS05',    label: 'Purchase Order OData → IDoc',            src: 'A_PurchaseOrder.xsd',   tgt: 'ORDERS05.xsd',           name: 'MM_PurchaseOrder_to_ORDERS',    group: 'Procurement' },
  { id: 'SALESORD05_to_A_SalesOrder',     label: 'Sales Order IDoc → OData',              src: 'SALESORD05.xsd',        tgt: 'A_SalesOrder.xsd',       name: 'MM_SALESORD_to_SalesOrder',     group: 'Sales' },
  { id: 'A_SalesOrder_to_SALESORD05',     label: 'Sales Order OData → IDoc',              src: 'A_SalesOrder.xsd',      tgt: 'SALESORD05.xsd',         name: 'MM_SalesOrder_to_SALESORD',     group: 'Sales' },
  { id: 'INVOIC02_to_A_SupplierInvoice',  label: 'Invoice IDoc → Supplier Invoice OData', src: 'INVOIC02.xsd',          tgt: 'A_SupplierInvoice.xsd',  name: 'MM_INVOIC_to_SupplierInvoice',  group: 'Finance' },
  { id: 'A_SupplierInvoice_to_INVOIC02',  label: 'Supplier Invoice OData → Invoice IDoc', src: 'A_SupplierInvoice.xsd', tgt: 'INVOIC02.xsd',           name: 'MM_SupplierInvoice_to_INVOIC',  group: 'Finance' },
  { id: 'INVOIC02_to_A_BillingDocument',  label: 'Invoice IDoc → Billing Document OData', src: 'INVOIC02.xsd',          tgt: 'A_BillingDocument.xsd',  name: 'MM_INVOIC_to_BillingDocument',  group: 'Finance' },
  { id: 'A_BillingDocument_to_INVOIC02',  label: 'Billing Document OData → Invoice IDoc', src: 'A_BillingDocument.xsd', tgt: 'INVOIC02.xsd',           name: 'MM_BillingDocument_to_INVOIC',  group: 'Finance' },
  { id: 'SALESORD05_to_A_OutboundDelivery',label:'Delivery IDoc → Outbound Delivery OData',src:'SALESORD05.xsd',        tgt: 'A_OutboundDelivery.xsd', name: 'MM_DESADV_to_OutboundDelivery', group: 'Logistics' },
  { id: 'A_OutboundDelivery_to_SALESORD05',label:'Outbound Delivery OData → Delivery IDoc',src:'A_OutboundDelivery.xsd',tgt: 'SALESORD05.xsd',          name: 'MM_OutboundDelivery_to_DESADV', group: 'Logistics' },
  { id: 'A_PurchaseOrder_to_A_MaterialDocument', label: 'Purchase Order → Material Document', src: 'A_PurchaseOrder.xsd', tgt: 'A_MaterialDocument.xsd', name: 'MM_PO_to_MaterialDoc', group: 'Logistics' },
]

const GROUP_COLORS: Record<string, { card: string; badge: string }> = {
  Material:    { card: 'border-blue-700/50 bg-blue-950/30',    badge: 'bg-blue-800 text-blue-200' },
  Customer:    { card: 'border-green-700/50 bg-green-950/30',  badge: 'bg-green-800 text-green-200' },
  Vendor:      { card: 'border-orange-700/50 bg-orange-950/30',badge: 'bg-orange-800 text-orange-200' },
  Procurement: { card: 'border-purple-700/50 bg-purple-950/30',badge: 'bg-purple-800 text-purple-200' },
  Sales:       { card: 'border-cyan-700/50 bg-cyan-950/30',    badge: 'bg-cyan-800 text-cyan-200' },
  Finance:     { card: 'border-yellow-700/50 bg-yellow-950/30',badge: 'bg-yellow-800 text-yellow-200' },
  Logistics:   { card: 'border-rose-700/50 bg-rose-950/30',    badge: 'bg-rose-800 text-rose-200' },
}

type PrebuiltInfo = { id: string; status: string; fields: number }

export default function MessageMapping() {
  const [tab, setTab] = useState<'schema' | 'sheet' | 'automap'>('schema')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')
  const [resultType, setResultType] = useState('groovy')

  const [schemaForm, setSchemaForm] = useState({ source_schema: '', target_schema: '', mapping_hints: '', output_format: 'groovy' })
  const [mmapName, setMmapName] = useState('MM_Mapping')
  const [mmapLoading, setMmapLoading] = useState(false)
  const [mmapAutoLoading, setMmapAutoLoading] = useState(false)
  const [mmapError, setMmapError] = useState('')
  const [sourceFileName, setSourceFileName] = useState<string | null>(null)
  const [targetFileName, setTargetFileName] = useState<string | null>(null)
  const sourceFileRef = useRef<HTMLInputElement>(null)
  const targetFileRef = useRef<HTMLInputElement>(null)

  // Catalog state
  const [catalogOpen, setCatalogOpen] = useState(true)
  const [filterGroup, setFilterGroup] = useState('All')
  const [selectedPairIdx, setSelectedPairIdx] = useState<number | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(false)

  // Pre-built state
  const [prebuilt, setPrebuilt] = useState<Record<string, PrebuiltInfo>>({})
  const [generatingAll, setGeneratingAll] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [generatingId, setGeneratingId] = useState<string | null>(null)

  const groups = ['All', ...Array.from(new Set(CATALOG_PAIRS.map(p => p.group)))]
  const filteredPairs = filterGroup === 'All' ? CATALOG_PAIRS : CATALOG_PAIRS.filter(p => p.group === filterGroup)

  // Poll pre-built status
  const refreshPrebuilt = useCallback(async () => {
    try {
      const res = await mappingAPI.prebuiltStatus()
      const map: Record<string, PrebuiltInfo> = {}
      for (const item of res.data.prebuilt) map[item.id] = item
      setPrebuilt(map)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    refreshPrebuilt()
    const iv = setInterval(refreshPrebuilt, 5000)
    return () => clearInterval(iv)
  }, [refreshPrebuilt])

  // Download pre-built .mmap
  const downloadPrebuilt = async (pair: typeof CATALOG_PAIRS[0]) => {
    setDownloadingId(pair.id)
    setMmapError('')
    try {
      const res = await mappingAPI.prebuiltDownload(pair.id)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
      const a = document.createElement('a'); a.href = url; a.download = `${pair.name}.zip`; a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      setMmapError(`Download failed for ${pair.id}: ${e?.message}`)
    } finally {
      setDownloadingId(null)
    }
  }

  // Generate single pre-built
  const generateSingle = async (pair: typeof CATALOG_PAIRS[0]) => {
    setGeneratingId(pair.id)
    setMmapError('')
    try {
      await mappingAPI.prebuiltGenerate(pair.id)
      setTimeout(refreshPrebuilt, 3000)
      setTimeout(refreshPrebuilt, 8000)
      setTimeout(refreshPrebuilt, 15000)
    } catch (e: any) {
      setMmapError(`Generation failed: ${e?.message}`)
    } finally {
      setGeneratingId(null)
    }
  }

  // Generate all pre-built
  const generateAll = async () => {
    setGeneratingAll(true)
    setMmapError('')
    try {
      await mappingAPI.prebuiltGenerateAll()
      // Poll more aggressively while generating
      const poll = setInterval(async () => {
        await refreshPrebuilt()
        const status = await mappingAPI.prebuiltStatus()
        const allReady = status.data.prebuilt.every((p: any) => p.status === 'ready')
        if (allReady) { clearInterval(poll); setGeneratingAll(false) }
      }, 5000)
      setTimeout(() => { clearInterval(poll); setGeneratingAll(false) }, 300000) // 5min safety
    } catch (e: any) {
      setMmapError(`Generate all failed: ${e?.message}`)
      setGeneratingAll(false)
    }
  }

  // Load schemas for the schema editor
  const loadCatalogPair = async (idx: number) => {
    const pair = filteredPairs[idx]
    setCatalogLoading(true)
    setMmapError('')
    try {
      const [srcRes, tgtRes] = await Promise.all([mappingAPI.schema(pair.src), mappingAPI.schema(pair.tgt)])
      setSchemaForm(f => ({ ...f, source_schema: srcRes.data.content, target_schema: tgtRes.data.content }))
      setSourceFileName(pair.src)
      setTargetFileName(pair.tgt)
      setMmapName(pair.name)
      setSelectedPairIdx(idx)
    } catch (e: any) {
      setMmapError(e?.response?.data?.detail || 'Failed to load schemas')
    } finally {
      setCatalogLoading(false)
    }
  }

  const handleFileUpload = (side: 'source' | 'target', file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      if (side === 'source') { setSchemaForm(f => ({ ...f, source_schema: text })); setSourceFileName(file.name) }
      else { setSchemaForm(f => ({ ...f, target_schema: text })); setTargetFileName(file.name) }
      setSelectedPairIdx(null)
    }
    reader.readAsText(file)
  }

  const clearFile = (side: 'source' | 'target') => {
    if (side === 'source') { setSchemaForm(f => ({ ...f, source_schema: '' })); setSourceFileName(null); if (sourceFileRef.current) sourceFileRef.current.value = '' }
    else { setSchemaForm(f => ({ ...f, target_schema: '' })); setTargetFileName(null); if (targetFileRef.current) targetFileRef.current.value = '' }
    setSelectedPairIdx(null)
  }

  const generateMmap = async () => {
    if (!schemaForm.source_schema || !schemaForm.target_schema) return
    setMmapLoading(true); setMmapError('')
    try {
      const res = await mappingAPI.generateMmap({ source_xsd: schemaForm.source_schema, target_xsd: schemaForm.target_schema, source_xsd_name: sourceFileName || 'source.xsd', target_xsd_name: targetFileName || 'target.xsd', mapping_name: mmapName || 'MM_Mapping', hints: schemaForm.mapping_hints })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
      const a = document.createElement('a'); a.href = url; a.download = `${mmapName || 'MM_Mapping'}.zip`; a.click(); URL.revokeObjectURL(url)
    } catch (e: any) { setMmapError(e?.message || 'Failed') } finally { setMmapLoading(false) }
  }

  const generateMmapAuto = async () => {
    if (!schemaForm.source_schema || !schemaForm.target_schema) return
    setMmapAutoLoading(true); setMmapError('')
    try {
      const res = await mappingAPI.generateMmapAuto({ source_xsd: schemaForm.source_schema, target_xsd: schemaForm.target_schema, source_xsd_name: sourceFileName || 'source.xsd', target_xsd_name: targetFileName || 'target.xsd', mapping_name: mmapName || 'MM_Mapping' })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
      const a = document.createElement('a'); a.href = url; a.download = `${mmapName || 'MM_Mapping'}.zip`; a.click(); URL.revokeObjectURL(url)
    } catch (e: any) { setMmapError(e?.message || 'Auto-map failed') } finally { setMmapAutoLoading(false) }
  }

  // Sheet Mapping state
  const [sheetSrcFile,    setSheetSrcFile]    = useState<File | null>(null)
  const [sheetTgtFile,    setSheetTgtFile]    = useState<File | null>(null)
  const [sheetFile,       setSheetFile]       = useState<File | null>(null)
  const [sheetMmapName,   setSheetMmapName]   = useState('MM_SheetMapping')
  const [sheetLoading,    setSheetLoading]    = useState(false)
  const [sheetError,      setSheetError]      = useState('')
  const [sheetSummary,    setSheetSummary]    = useState('')
  const sheetSrcRef  = useRef<HTMLInputElement>(null)
  const sheetTgtRef  = useRef<HTMLInputElement>(null)
  const sheetFileRef = useRef<HTMLInputElement>(null)

  const generateFromSheet = async () => {
    if (!sheetSrcFile || !sheetTgtFile || !sheetFile) return
    setSheetLoading(true); setSheetError(''); setSheetSummary('')
    try {
      const res = await mappingAPI.fromSheet(sheetSrcFile, sheetTgtFile, sheetFile, sheetMmapName)
      const summary = res.headers?.['x-mapping-summary'] ?? ''
      const parts   = Object.fromEntries(summary.split(',').map((s: string) => s.split('=')))
      if (parts.mapped) setSheetSummary(`Mapped ${parts.mapped} field(s)${parts.unmatched !== '0' ? `, ${parts.unmatched} unmatched` : ''}`)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
      const a   = document.createElement('a'); a.href = url; a.download = `${sheetMmapName}.zip`; a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      const msg = e?.response?.data ? await new Response(e.response.data).text().then(t => { try { return JSON.parse(t).detail } catch { return t } }) : e?.message
      setSheetError(msg || 'Failed to generate .mmap')
    } finally { setSheetLoading(false) }
  }

  const [autoForm, setAutoForm] = useState({ source_fields: '', target_fields: '' })
  const generateFromSchema = async () => { setLoading(true); try { const res = await mappingAPI.generate(schemaForm); setResult(res.data.result); setResultType(schemaForm.output_format) } finally { setLoading(false) } }
  const autoMap = async () => { setLoading(true); try { const res = await mappingAPI.automap(autoForm); setResult(res.data.result); setResultType('markdown') } finally { setLoading(false) } }

  const readyCount  = Object.values(prebuilt).filter(p => p.status === 'ready').length
  const totalCount  = CATALOG_PAIRS.length

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Shuffle size={24} className="text-green-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Message Mapping</h1>
          <p className="text-gray-400 text-sm">Auto-generate field mappings between source and target schemas</p>
        </div>
      </div>

      <div className="flex gap-1 bg-gray-900 p-1 rounded-lg w-fit mb-6 border border-gray-800">
        <button onClick={() => { setTab('schema'); setResult('') }} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === 'schema' ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
          <Wand2 size={13} className="inline mr-1.5" />Schema Mapping
        </button>
        <button onClick={() => { setTab('sheet'); setResult('') }} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === 'sheet' ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
          <FileSpreadsheet size={13} className="inline mr-1.5" />Sheet Mapping
        </button>
        <button onClick={() => { setTab('automap'); setResult('') }} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === 'automap' ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
          <Zap size={13} className="inline mr-1.5" />Quick Field Automap
        </button>
      </div>

      {tab === 'schema' && (
        <div className="space-y-4">

          {/* ── Mapping Catalog ─────────────────────────────────────────────── */}
          <div className="card border border-gray-700 p-0 overflow-hidden">
            <button className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800/50 transition-colors" onClick={() => setCatalogOpen(o => !o)}>
              <div className="flex items-center gap-2">
                <BookOpen size={15} className="text-sap-blue shrink-0" />
                <span className="text-sm font-semibold text-white">Pre-built Mapping Catalog</span>
                <span className="text-xs text-gray-500 ml-1">— {totalCount} S/4HANA IDoc ↔ OData pairs</span>
                {readyCount > 0 && (
                  <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-900/50 border border-emerald-700/50 text-emerald-300">
                    <CheckCircle2 size={10} />{readyCount}/{totalCount} ready
                  </span>
                )}
              </div>
              {catalogOpen ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
            </button>

            {catalogOpen && (
              <div className="border-t border-gray-700 p-4 space-y-3">

                {/* Header actions */}
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  {/* Group filter chips */}
                  <div className="flex flex-wrap gap-1.5">
                    {groups.map(g => (
                      <button key={g} onClick={() => setFilterGroup(g)}
                        className={`px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors ${filterGroup === g ? 'bg-sap-blue border-sap-blue text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white'}`}>
                        {g}
                      </button>
                    ))}
                  </div>
                  {/* Generate all button */}
                  <button
                    onClick={generateAll}
                    disabled={generatingAll}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-sap-blue hover:bg-blue-600 text-white transition-colors disabled:opacity-60"
                  >
                    {generatingAll ? <Loader2 size={11} className="animate-spin" /> : <Wand2 size={11} />}
                    {generatingAll ? 'Generating…' : 'Generate All with AI'}
                  </button>
                </div>

                {/* Pair cards */}
                <div className="grid grid-cols-1 gap-2">
                  {filteredPairs.map((pair) => {
                    const colors  = GROUP_COLORS[pair.group] ?? { card: 'border-gray-700 bg-gray-800', badge: 'bg-gray-700 text-gray-300' }
                    const pb      = prebuilt[pair.id]
                    const isReady = pb?.status === 'ready'
                    const isPending = !pb || pb.status === 'pending'
                    const isActive = selectedPairIdx !== null && filteredPairs[selectedPairIdx]?.id === pair.id

                    return (
                      <div key={pair.id} className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${colors.card} ${isActive ? 'ring-2 ring-sap-blue' : ''}`}>
                        {/* Group badge */}
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 ${colors.badge}`}>{pair.group}</span>

                        {/* Label */}
                        <div className="flex-1 min-w-0">
                          <span className="text-xs font-medium text-white">{pair.label}</span>
                          <div className="text-[10px] text-gray-500 mt-0.5">
                            {pair.src} <ArrowRight size={9} className="inline" /> {pair.tgt}
                          </div>
                        </div>

                        {/* Status + actions */}
                        <div className="flex items-center gap-1.5 shrink-0">
                          {isReady ? (
                            <>
                              <span className="flex items-center gap-1 text-[10px] text-emerald-400">
                                <CheckCircle2 size={10} />{pb.fields} fields
                              </span>
                              {/* Download pre-built */}
                              <button
                                onClick={() => downloadPrebuilt(pair)}
                                disabled={downloadingId === pair.id}
                                title="Download pre-built .mmap (Claude-verified)"
                                className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold bg-emerald-700 hover:bg-emerald-600 text-white transition-colors disabled:opacity-60"
                              >
                                {downloadingId === pair.id ? <Loader2 size={10} className="animate-spin" /> : <Download size={10} />}
                                .mmap
                              </button>
                              {/* Re-generate */}
                              <button
                                onClick={() => generateSingle(pair)}
                                disabled={generatingId === pair.id}
                                title="Re-generate with AI"
                                className="p-1 rounded text-gray-500 hover:text-white transition-colors"
                              >
                                {generatingId === pair.id ? <Loader2 size={10} className="animate-spin" /> : <RefreshCw size={10} />}
                              </button>
                            </>
                          ) : (
                            <>
                              <span className="flex items-center gap-1 text-[10px] text-gray-500">
                                <Clock size={10} />{generatingAll || generatingId === pair.id ? 'generating…' : 'pending'}
                              </span>
                              <button
                                onClick={() => generateSingle(pair)}
                                disabled={generatingId === pair.id || generatingAll}
                                title="Generate with AI"
                                className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold bg-sap-blue hover:bg-blue-600 text-white transition-colors disabled:opacity-60"
                              >
                                {generatingId === pair.id ? <Loader2 size={10} className="animate-spin" /> : <Wand2 size={10} />}
                                Generate
                              </button>
                            </>
                          )}
                          {/* Load into editor */}
                          <button
                            onClick={() => loadCatalogPair(filteredPairs.indexOf(pair))}
                            disabled={catalogLoading}
                            title="Load schemas into editor below"
                            className="p-1 rounded text-gray-500 hover:text-sap-blue transition-colors"
                          >
                            {catalogLoading && isActive ? <Loader2 size={10} className="animate-spin" /> : <Eye size={10} />}
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>

                <p className="text-[10px] text-gray-600 leading-relaxed">
                  <strong className="text-gray-500">Pre-built .mmap</strong> — Claude AI analyses both schemas and maps only fields with a real semantic equivalent.
                  No forced mappings, no parent containers, no guessing.
                  Click <em>Generate</em> on any row to create it (uses Groq API), or <em>Generate All with AI</em> for all 18 pairs.
                  Once ready, <em>.mmap</em> downloads instantly — no API call needed at download time.
                </p>
              </div>
            )}
          </div>

          {/* ── Schema editor ───────────────────────────────────────────────── */}
          <div className="card space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Source */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="label mb-0">Source Schema</label>
                  <button type="button" onClick={() => sourceFileRef.current?.click()}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-gray-800 border border-gray-700 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors">
                    <Upload size={12} />Upload XSD / XML
                  </button>
                  <input ref={sourceFileRef} type="file" accept=".xsd,.xml" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload('source', f) }} />
                </div>
                {sourceFileName && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-sap-blue/10 border border-sap-blue/30 text-xs text-sap-blue">
                    <FileCode size={12} className="shrink-0" />
                    <span className="truncate flex-1">{sourceFileName}</span>
                    <button onClick={() => clearFile('source')} className="hover:text-red-400"><X size={12} /></button>
                  </div>
                )}
                <textarea className="textarea-field" rows={7}
                  placeholder="Paste source XSD / XML — or pick a catalog pair above (Eye icon) to load automatically..."
                  value={schemaForm.source_schema}
                  onChange={e => { setSchemaForm(f => ({ ...f, source_schema: e.target.value })); if (!e.target.value) setSourceFileName(null) }} />
              </div>

              {/* Target */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="label mb-0">Target Schema</label>
                  <button type="button" onClick={() => targetFileRef.current?.click()}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-gray-800 border border-gray-700 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors">
                    <Upload size={12} />Upload XSD / XML
                  </button>
                  <input ref={targetFileRef} type="file" accept=".xsd,.xml" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload('target', f) }} />
                </div>
                {targetFileName && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-sap-blue/10 border border-sap-blue/30 text-xs text-sap-blue">
                    <FileCode size={12} className="shrink-0" />
                    <span className="truncate flex-1">{targetFileName}</span>
                    <button onClick={() => clearFile('target')} className="hover:text-red-400"><X size={12} /></button>
                  </div>
                )}
                <textarea className="textarea-field" rows={7}
                  placeholder="Paste target XSD / XML — or pick a catalog pair above..."
                  value={schemaForm.target_schema}
                  onChange={e => { setSchemaForm(f => ({ ...f, target_schema: e.target.value })); if (!e.target.value) setTargetFileName(null) }} />
              </div>
            </div>

            <div>
              <label className="label">Mapping Hints / Business Rules (optional)</label>
              <textarea className="textarea-field" rows={2} placeholder="e.g. Map OrderId to PurchaseOrderNumber, convert date from YYYY-MM-DD to DD.MM.YYYY..." value={schemaForm.mapping_hints} onChange={e => setSchemaForm(f => ({ ...f, mapping_hints: e.target.value }))} />
            </div>

            <div>
              <label className="label">Output Format</label>
              <div className="flex gap-3">
                {outputFormats.map(({ value, label }) => (
                  <label key={value} className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="format" value={value} checked={schemaForm.output_format === value} onChange={() => setSchemaForm(f => ({ ...f, output_format: value }))} className="accent-sap-blue" />
                    <span className="text-sm text-gray-300">{label}</span>
                  </label>
                ))}
              </div>
            </div>

            <button className="btn-primary flex items-center gap-2" onClick={generateFromSchema} disabled={loading || !schemaForm.source_schema || !schemaForm.target_schema}>
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
              {loading ? 'Generating...' : 'Generate Mapping (AI)'}
            </button>

            {/* .mmap export */}
            <div className="border-t border-gray-700 pt-4 space-y-3">
              <div className="flex items-center gap-2">
                <Package size={15} className="text-sap-blue shrink-0" />
                <span className="text-sm font-medium text-white">Generate .mmap for CPI Graphical Message Mapping</span>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-400 whitespace-nowrap">Mapping name:</label>
                <input type="text" className="input-field text-sm py-1 px-2 w-64" placeholder="MM_Mapping" value={mmapName} onChange={e => setMmapName(e.target.value.replace(/\s+/g, '_'))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Cpu size={13} className="text-emerald-400 shrink-0" />
                    <span className="text-xs font-semibold text-white">Auto-Map (Local · No AI)</span>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    Parses both XSDs locally. Maps only <span className="text-white font-medium">leaf fields</span> with score ≥ 0.82 using SAP field dictionary (472 pairs). Omits unmatched fields — no forced mappings.
                  </p>
                  <button className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-emerald-700 hover:bg-emerald-600 text-white transition-colors disabled:opacity-50"
                    onClick={generateMmapAuto} disabled={mmapAutoLoading || !schemaForm.source_schema || !schemaForm.target_schema}>
                    {mmapAutoLoading ? <Loader2 size={13} className="animate-spin" /> : <Cpu size={13} />}
                    {mmapAutoLoading ? 'Parsing XSD…' : 'Download .mmap (Auto)'}
                  </button>
                </div>
                <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Wand2 size={13} className="text-sap-blue shrink-0" />
                    <span className="text-xs font-semibold text-white">AI-Assisted Map</span>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    Sends schemas to AI for <span className="text-white font-medium">semantic analysis</span>. Maps fields by business meaning. Uses Groq API — may be rate-limited on large schemas.
                  </p>
                  <button className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-sap-blue hover:bg-blue-600 text-white transition-colors disabled:opacity-50"
                    onClick={generateMmap} disabled={mmapLoading || !schemaForm.source_schema || !schemaForm.target_schema}>
                    {mmapLoading ? <Loader2 size={13} className="animate-spin" /> : <Wand2 size={13} />}
                    {mmapLoading ? 'Building .mmap…' : 'Download .mmap (AI)'}
                  </button>
                </div>
              </div>
              {mmapError && (
                <div className="rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-xs text-red-300">
                  <span className="font-semibold">Error: </span>{mmapError}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Sheet Mapping tab ─────────────────────────────────────────────── */}
      {tab === 'sheet' && (
        <div className="space-y-4">
          <div className="card space-y-5">

            {/* Instructions */}
            <div className="rounded-lg bg-sap-blue/10 border border-sap-blue/30 px-4 py-3 text-sm text-gray-300 space-y-1">
              <p className="font-semibold text-white flex items-center gap-2">
                <FileSpreadsheet size={15} className="text-sap-blue" />How it works
              </p>
              <p>Upload your source XSD, target XSD, and a mapping sheet (Excel or CSV). The sheet must have <strong className="text-white">Source Field</strong> and <strong className="text-white">Target Field</strong> columns containing field names or XPath segments. The tool resolves them to full paths in the XSDs and builds a ready-to-import <code className="bg-gray-800 px-1 rounded">.mmap</code> file.</p>
              <p className="text-gray-400 text-xs">Supports: short field names (e.g. <em>mn</em>), full names (e.g. <em>MaterialNumber</em>), structural nodes (e.g. <em>body</em> → <em>to_Stock</em>), and mapping rules in the sheet.</p>
            </div>

            {/* File upload grid */}
            <div className="grid grid-cols-3 gap-3">

              {/* Source XSD */}
              <div className="space-y-2">
                <label className="label mb-0">Source XSD</label>
                <button type="button" onClick={() => sheetSrcRef.current?.click()}
                  className={`w-full flex flex-col items-center justify-center gap-2 h-24 rounded-lg border-2 border-dashed transition-colors cursor-pointer
                    ${sheetSrcFile ? 'border-sap-blue/60 bg-sap-blue/5' : 'border-gray-700 hover:border-gray-500 bg-gray-800/30'}`}>
                  {sheetSrcFile
                    ? <><FileCode size={20} className="text-sap-blue" /><span className="text-xs text-sap-blue font-medium truncate max-w-full px-2">{sheetSrcFile.name}</span></>
                    : <><Upload size={18} className="text-gray-500" /><span className="text-xs text-gray-500">Click to upload .xsd</span></>
                  }
                </button>
                <input ref={sheetSrcRef} type="file" accept=".xsd,.xml" className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) { setSheetSrcFile(f); e.target.value = '' } }} />
                {sheetSrcFile && <button onClick={() => setSheetSrcFile(null)} className="text-xs text-gray-500 hover:text-red-400 flex items-center gap-1"><X size={10} />Remove</button>}
              </div>

              {/* Target XSD */}
              <div className="space-y-2">
                <label className="label mb-0">Target XSD</label>
                <button type="button" onClick={() => sheetTgtRef.current?.click()}
                  className={`w-full flex flex-col items-center justify-center gap-2 h-24 rounded-lg border-2 border-dashed transition-colors cursor-pointer
                    ${sheetTgtFile ? 'border-sap-blue/60 bg-sap-blue/5' : 'border-gray-700 hover:border-gray-500 bg-gray-800/30'}`}>
                  {sheetTgtFile
                    ? <><FileCode size={20} className="text-sap-blue" /><span className="text-xs text-sap-blue font-medium truncate max-w-full px-2">{sheetTgtFile.name}</span></>
                    : <><Upload size={18} className="text-gray-500" /><span className="text-xs text-gray-500">Click to upload .xsd</span></>
                  }
                </button>
                <input ref={sheetTgtRef} type="file" accept=".xsd,.xml" className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) { setSheetTgtFile(f); e.target.value = '' } }} />
                {sheetTgtFile && <button onClick={() => setSheetTgtFile(null)} className="text-xs text-gray-500 hover:text-red-400 flex items-center gap-1"><X size={10} />Remove</button>}
              </div>

              {/* Mapping Sheet */}
              <div className="space-y-2">
                <label className="label mb-0">Mapping Sheet</label>
                <button type="button" onClick={() => sheetFileRef.current?.click()}
                  className={`w-full flex flex-col items-center justify-center gap-2 h-24 rounded-lg border-2 border-dashed transition-colors cursor-pointer
                    ${sheetFile ? 'border-emerald-600/60 bg-emerald-900/10' : 'border-gray-700 hover:border-gray-500 bg-gray-800/30'}`}>
                  {sheetFile
                    ? <><FileSpreadsheet size={20} className="text-emerald-400" /><span className="text-xs text-emerald-400 font-medium truncate max-w-full px-2">{sheetFile.name}</span></>
                    : <><FileSpreadsheet size={18} className="text-gray-500" /><span className="text-xs text-gray-500">Click to upload .xlsx / .csv</span></>
                  }
                </button>
                <input ref={sheetFileRef} type="file" accept=".xlsx,.xlsm,.csv" className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) { setSheetFile(f); e.target.value = '' } }} />
                {sheetFile && <button onClick={() => setSheetFile(null)} className="text-xs text-gray-500 hover:text-red-400 flex items-center gap-1"><X size={10} />Remove</button>}
              </div>
            </div>

            {/* Mapping name + Generate */}
            <div className="flex items-center gap-3 flex-wrap">
              <label className="text-xs text-gray-400 whitespace-nowrap">Mapping name:</label>
              <input type="text" className="input-field text-sm py-1 px-2 w-60"
                placeholder="MM_SheetMapping"
                value={sheetMmapName}
                onChange={e => setSheetMmapName(e.target.value.replace(/\s+/g, '_'))} />
              {IS_STATIC_HOST ? (
                <div className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-amber-900/40 border border-amber-700/50 text-amber-300">
                  <AlertCircle size={15} className="shrink-0" />
                  Backend not available on GitHub Pages — run locally to use this feature
                </div>
              ) : (
                <button
                  onClick={generateFromSheet}
                  disabled={sheetLoading || !sheetSrcFile || !sheetTgtFile || !sheetFile}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-sap-blue hover:bg-blue-600 text-white transition-colors disabled:opacity-50">
                  {sheetLoading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
                  {sheetLoading ? 'Building .mmap…' : 'Generate & Download .mmap'}
                </button>
              )}
            </div>

            {/* Success summary */}
            {sheetSummary && !sheetError && (
              <div className="flex items-center gap-2 rounded-lg bg-emerald-950/50 border border-emerald-700/50 px-3 py-2 text-xs text-emerald-300">
                <CheckCircle2 size={13} className="shrink-0" />
                <span>{sheetSummary} — .mmap downloaded.</span>
              </div>
            )}

            {/* Error */}
            {sheetError && (
              <div className="flex items-start gap-2 rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-xs text-red-300">
                <AlertCircle size={13} className="shrink-0 mt-0.5" />
                <span><strong>Error: </strong>{sheetError}</span>
              </div>
            )}

            {/* Expected sheet format */}
            <div className="border-t border-gray-700 pt-4 space-y-4">
              <p className="text-xs text-gray-500 font-semibold">Expected sheet format (any extra columns are ignored):</p>
              <div className="overflow-x-auto rounded-lg border border-gray-700">
                <table className="text-xs w-full">
                  <thead className="bg-gray-800">
                    <tr>
                      {['Source Field','Description','Entity Set','Property Details','Target Field','Mapping Rule','Comment'].map(h => (
                        <th key={h} className={`px-2 py-1.5 text-left font-semibold ${h === 'Source Field' || h === 'Target Field' ? 'text-sap-blue' : 'text-gray-500'}`}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {[
                      ['mn','Material number','','','MaterialNumber','',''],
                      ['pl','Plant','','','Plant','',''],
                      ['sender','Sender ID','','','LSPId','toUpperCase((/msg/header/sender))','uppercase'],
                      [null,'—','','','RunDate','(/msg/header/date)+T+(/msg/header/time)','concat shorthand'],
                      ['date','','','','FormattedDate','formatDate((/msg/header/date), yyyyMMdd, yyyy-MM-dd)',''],
                    ].map((row, i) => (
                      <tr key={i} className="hover:bg-gray-800/40">
                        {row.map((cell, j) => (
                          <td key={j} className={`px-2 py-1 ${j === 0 || j === 4 ? 'text-white font-mono' : j === 5 ? 'text-amber-400 font-mono text-[10px]' : 'text-gray-500'}`}>
                            {cell || <span className="italic text-gray-700">—</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Node function reference */}
              <div>
                <p className="text-xs text-gray-500 font-semibold mb-2">Mapping Rule column — supported syntax:</p>
                <div className="rounded-lg border border-gray-700 overflow-hidden">
                  <table className="text-xs w-full">
                    <thead className="bg-gray-800/80">
                      <tr>
                        <th className="px-3 py-1.5 text-left text-gray-400 font-semibold w-1/3">Rule (Mapping Rule column)</th>
                        <th className="px-3 py-1.5 text-left text-gray-400 font-semibold w-1/4">Function used</th>
                        <th className="px-3 py-1.5 text-left text-gray-400 font-semibold">Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {[
                        ['(/field1)+CONST+(/field2)', 'concat', 'Concat shorthand — joins fields/constants with +'],
                        ['concat((/f1), SEP, (/f2))', 'concat', 'Explicit concat — same result, more readable'],
                        ['toUpperCase((/field))', 'toUpperCase', 'Convert text to upper case'],
                        ['toLowerCase((/field))', 'toLowerCase', 'Convert text to lower case'],
                        ['trim((/field))', 'trim', 'Remove leading/trailing whitespace'],
                        ['substring((/field), start, len)', 'substring', 'Extract substring (0-based start)'],
                        ['formatDate((/field), inFmt, outFmt)', 'formatDate', 'Reformat a date string'],
                        ['mapWithDefault((/field), k1, v1, k2, v2, …)', 'mapWithDefault', 'Value lookup table with key→value pairs'],
                        ['splitByValue((/field), DELIM)', 'splitByValue', 'Split a field by delimiter into occurrences'],
                        ['if(equals((/field), VAL), YES, NO)', 'if + equals', 'Conditional: if field = VAL then YES else NO'],
                        ['replaceAll((/field), REGEX, REPLACEMENT)', 'replaceAll', 'Regex replace within a field value'],
                        ['length((/field))', 'length', 'String length as a number'],
                        ['UseOneAsMany((/field))', 'UseOneAsMany', 'Repeat a single value for each occurrence of target'],
                      ].map(([rule, func, desc], i) => (
                        <tr key={i} className="hover:bg-gray-800/30">
                          <td className="px-3 py-1.5 font-mono text-amber-400 text-[10px]">{rule}</td>
                          <td className="px-3 py-1.5 text-emerald-400 text-[10px]">{func}</td>
                          <td className="px-3 py-1.5 text-gray-400">{desc}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="px-3 py-2 bg-gray-900/50 text-[10px] text-gray-500 border-t border-gray-700">
                    <strong className="text-gray-400">Args:</strong>&nbsp;
                    <code className="text-amber-400">(/xpath/to/field)</code> or <code className="text-amber-400">/xpath/to/field</code> → source field &nbsp;|&nbsp;
                    Bare text (no slashes) → constant string &nbsp;|&nbsp;
                    Any SAP CPI standard node function name works — write it exactly as in the mapping editor.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'automap' && (
        <div className="card space-y-4">
          <p className="text-sm text-gray-400">List fields one per line in format: <code className="bg-gray-800 px-1 rounded text-gray-300">fieldName: dataType</code></p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Source Fields</label>
              <textarea className="textarea-field" rows={10} placeholder={"OrderId: String\nCustomerName: String\nOrderDate: Date\nTotalAmount: Decimal"} value={autoForm.source_fields} onChange={e => setAutoForm(f => ({ ...f, source_fields: e.target.value }))} />
            </div>
            <div>
              <label className="label">Target Fields</label>
              <textarea className="textarea-field" rows={10} placeholder={"PurchaseOrderNo: String\nBuyerName: String\nDocumentDate: String\nNetValue: Number"} value={autoForm.target_fields} onChange={e => setAutoForm(f => ({ ...f, target_fields: e.target.value }))} />
            </div>
          </div>
          <button className="btn-primary flex items-center gap-2" onClick={autoMap} disabled={loading || !autoForm.source_fields || !autoForm.target_fields}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
            {loading ? 'Mapping...' : 'Auto-Map Fields'}
          </button>
        </div>
      )}

      {result && resultType === 'groovy' && <ResultPanel result={result} language="groovy" title="Generated Mapping (Groovy)" />}
      {result && resultType === 'xslt' && <ResultPanel result={result} language="xml" title="Generated Mapping (XSLT)" />}
      {result && (resultType === 'description' || resultType === 'markdown' || resultType === 'automap') && <MarkdownResult content={result} title="Mapping Result" />}
    </div>
  )
}
