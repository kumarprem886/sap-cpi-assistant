import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
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

// ── Reusable XSD slot: catalog picker OR file upload ──────────────────────────

const ACCENT: Record<string, { border: string; bg: string; text: string; tab: string; tabActive: string }> = {
  blue:  { border: 'border-blue-600/60',   bg: 'bg-blue-900/10',   text: 'text-blue-400',   tab: 'hover:text-blue-300',   tabActive: 'bg-blue-700 text-white' },
  green: { border: 'border-green-600/60',  bg: 'bg-green-900/10',  text: 'text-green-400',  tab: 'hover:text-green-300',  tabActive: 'bg-green-700 text-white' },
}

function XsdSlot({
  label, accentClass, mode, onModeChange,
  selectedSchema, onSchemaChange,
  uploadedFile, onFileChange, fileRef,
  schemas,
}: {
  label: string
  accentClass: 'blue' | 'green'
  mode: 'catalog' | 'upload'
  onModeChange: (m: 'catalog' | 'upload') => void
  selectedSchema: string
  onSchemaChange: (v: string) => void
  uploadedFile: File | null
  onFileChange: (f: File | null) => void
  fileRef: React.RefObject<HTMLInputElement>
  schemas: Array<{filename: string; stem: string; kind: string}>
}) {
  const a = ACCENT[accentClass]
  const odataSchemas = schemas.filter(s => s.kind === 'odata')
  const idocSchemas  = schemas.filter(s => s.kind === 'idoc')

  return (
    <div className="space-y-2">
      {/* Label + mode toggle */}
      <div className="flex items-center justify-between">
        <label className="label mb-0">{label}</label>
        <div className="flex rounded-md overflow-hidden border border-gray-700 text-[10px] font-semibold">
          <button onClick={() => onModeChange('catalog')}
            className={`px-2 py-0.5 transition-colors ${mode === 'catalog' ? a.tabActive : 'bg-gray-800 text-gray-500 hover:text-gray-300'}`}>
            Catalog
          </button>
          <button onClick={() => onModeChange('upload')}
            className={`px-2 py-0.5 transition-colors ${mode === 'upload' ? a.tabActive : 'bg-gray-800 text-gray-500 hover:text-gray-300'}`}>
            Upload
          </button>
        </div>
      </div>

      {mode === 'catalog' ? (
        <div className={`rounded-lg border-2 ${selectedSchema ? a.border + ' ' + a.bg : 'border-gray-700 bg-gray-800/30'} p-2 space-y-1.5`}>
          {/* OData group */}
          {odataSchemas.length > 0 && (
            <div>
              <p className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1">OData APIs</p>
              <div className="grid grid-cols-1 gap-0.5 max-h-28 overflow-y-auto">
                {odataSchemas.map(s => (
                  <button key={s.filename} onClick={() => onSchemaChange(s.filename)}
                    className={`text-left text-[10px] px-2 py-1 rounded transition-colors truncate ${
                      selectedSchema === s.filename
                        ? `${a.tabActive} font-semibold`
                        : `text-gray-400 hover:text-white hover:bg-gray-700`
                    }`}>
                    {s.stem}
                  </button>
                ))}
              </div>
            </div>
          )}
          {/* IDoc group */}
          {idocSchemas.length > 0 && (
            <div>
              <p className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1 mt-1">IDoc Types</p>
              <div className="grid grid-cols-1 gap-0.5 max-h-28 overflow-y-auto">
                {idocSchemas.map(s => (
                  <button key={s.filename} onClick={() => onSchemaChange(s.filename)}
                    className={`text-left text-[10px] px-2 py-1 rounded transition-colors truncate ${
                      selectedSchema === s.filename
                        ? `${a.tabActive} font-semibold`
                        : `text-gray-400 hover:text-white hover:bg-gray-700`
                    }`}>
                    {s.stem}
                  </button>
                ))}
              </div>
            </div>
          )}
          {schemas.length === 0 && (
            <p className="text-xs text-gray-600 text-center py-3">Loading schemas…</p>
          )}
          {selectedSchema && (
            <div className={`flex items-center gap-1 mt-1 pt-1 border-t border-gray-700/50 ${a.text} text-[10px]`}>
              <CheckCircle2 size={10} className="shrink-0" />
              <span className="truncate font-medium">{selectedSchema}</span>
              <button onClick={() => onSchemaChange('')} className="ml-auto text-gray-600 hover:text-red-400 shrink-0"><X size={9} /></button>
            </div>
          )}
        </div>
      ) : (
        <>
          <button type="button" onClick={() => fileRef.current?.click()}
            className={`w-full flex flex-col items-center justify-center gap-2 h-28 rounded-lg border-2 border-dashed transition-colors cursor-pointer
              ${uploadedFile ? a.border + ' ' + a.bg : 'border-gray-700 hover:border-gray-500 bg-gray-800/30'}`}>
            {uploadedFile
              ? <><FileCode size={20} className={a.text} /><span className={`text-xs font-medium truncate max-w-full px-2 ${a.text}`}>{uploadedFile.name}</span></>
              : <><Upload size={18} className="text-gray-500" /><span className="text-xs text-gray-500">Click to upload .xsd</span></>
            }
          </button>
          <input ref={fileRef} type="file" accept=".xsd,.xml" className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) { onFileChange(f); e.target.value = '' } }} />
          {uploadedFile && (
            <button onClick={() => onFileChange(null)} className="text-xs text-gray-500 hover:text-red-400 flex items-center gap-1">
              <X size={10} />Remove
            </button>
          )}
        </>
      )}
    </div>
  )
}

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

  // XSD catalog selection for sheet mapping
  const [catalogSchemas, setCatalogSchemas] = useState<Array<{filename: string; stem: string; kind: string}>>([])
  const [sheetSrcMode,   setSheetSrcMode]   = useState<'catalog' | 'upload'>('catalog')
  const [sheetTgtMode,   setSheetTgtMode]   = useState<'catalog' | 'upload'>('catalog')
  const [sheetSrcSchema, setSheetSrcSchema] = useState('')
  const [sheetTgtSchema, setSheetTgtSchema] = useState('')

  // Load catalog schemas once on mount
  useEffect(() => {
    mappingAPI.catalog().then(r => {
      setCatalogSchemas(r.data.schemas || [])
    }).catch(() => {})
  }, [])

  // Resolve XSD: return uploaded File or fetch from catalog and wrap as File
  const resolveXsdFile = async (
    mode: 'catalog' | 'upload',
    catalogFilename: string,
    uploadedFile: File | null
  ): Promise<File | null> => {
    if (mode === 'upload') return uploadedFile
    if (!catalogFilename) return null
    const r = await mappingAPI.schema(catalogFilename)
    const blob = new Blob([r.data.content], { type: 'text/xml' })
    return new File([blob], catalogFilename, { type: 'text/xml' })
  }

  const sheetSrcReady  = sheetSrcMode === 'catalog' ? !!sheetSrcSchema : !!sheetSrcFile
  const sheetTgtReady  = sheetTgtMode === 'catalog' ? !!sheetTgtSchema : !!sheetTgtFile
  const sheetSrcLabel  = sheetSrcMode === 'catalog' ? (sheetSrcSchema || '') : (sheetSrcFile?.name || '')
  const sheetTgtLabel  = sheetTgtMode === 'catalog' ? (sheetTgtSchema || '') : (sheetTgtFile?.name || '')

  // Prebuilt quick-start
  const [selectedPrebuilt,  setSelectedPrebuilt]  = useState('')
  const [loadingPrebuilt,   setLoadingPrebuilt]   = useState(false)

  const loadFromPrebuilt = async (pairId: string) => {
    if (!pairId) return
    const pair = CATALOG_PAIRS.find(p => p.id === pairId)
    if (!pair) return
    setLoadingPrebuilt(true); setSheetError(''); setSheetPreview(null)

    // Auto-select XSDs
    setSheetSrcMode('catalog'); setSheetSrcSchema(pair.src)
    setSheetTgtMode('catalog'); setSheetTgtSchema(pair.tgt)
    setSheetMmapName(pair.name)

    try {
      const r = await mappingAPI.prebuiltPreview(pairId)
      const data = r.data as { field_mappings?: Array<{source_path?: string; target_path?: string; note?: string}>; mapping_name?: string }

      const lastSeg = (p: string) => p?.split('/').filter(Boolean).pop() ?? p

      const rows = (data.field_mappings ?? [])
        .filter(fm => fm.source_path && fm.target_path)
        .map(fm => ({
          source:          lastSeg(fm.source_path!),
          target:          lastSeg(fm.target_path!),
          functional_rule: '',   // leave blank — note is AI's internal reasoning, not a user rule
          technical_rule:  '',
          status:          'matched' as const,
          source_path:     fm.source_path ?? '',
          target_path:     fm.target_path ?? '',
        }))

      setSheetPreview({
        rows,
        matched: rows.length,
        unmatched: 0,
        unmatched_detail: [],
        src_paths: [],
        tgt_paths: [],
      })
      if (data.mapping_name) setSheetMmapName(data.mapping_name)
      setSheetStep('preview')
    } catch {
      setSheetError(`Prebuilt mapping for "${pair.label}" not generated yet. Go to Schema Mapping → Pre-built Catalog and click Generate.`)
    } finally { setLoadingPrebuilt(false) }
  }

  // Enhanced sheet mapping state
  const [sheetStep, setSheetStep] = useState<'upload' | 'preview' | 'generate'>('upload')
  const [sheetPreview, setSheetPreview] = useState<{
    rows: Array<{
      source: string; target: string
      functional_rule: string; technical_rule: string
      status: string; ai_derived?: boolean; derive_error?: string
      source_matched?: boolean; target_matched?: boolean
      source_path?: string; target_path?: string   // full resolved XSD paths
    }>
    matched: number; unmatched: number
    unmatched_detail: Array<{source: string; target: string; reason: string}>
    src_paths: string[]; tgt_paths: string[]
  } | null>(null)

  // Pre-computed lookup: last-segment (lower) → full XPath — used to show resolved paths in table
  const srcPathMap = useMemo(() => {
    const m = new Map<string, string>()
    sheetPreview?.src_paths.forEach(p => {
      const seg = p.split('/').filter(Boolean).pop()?.toLowerCase()
      if (seg && !m.has(seg)) m.set(seg, p)
    })
    return m
  }, [sheetPreview?.src_paths])
  const tgtPathMap = useMemo(() => {
    const m = new Map<string, string>()
    sheetPreview?.tgt_paths.forEach(p => {
      const seg = p.split('/').filter(Boolean).pop()?.toLowerCase()
      if (seg && !m.has(seg)) m.set(seg, p)
    })
    return m
  }, [sheetPreview?.tgt_paths])

  const [previewLoading, setPreviewLoading] = useState(false)
  const [derivingAll, setDerivingAll] = useState(false)
  const [derivingRow, setDerivingRow] = useState<number | null>(null)

  const generateFromSheet = async () => {
    if (!sheetFile) return
    setSheetLoading(true); setSheetError(''); setSheetSummary('')
    try {
      const srcFile = await resolveXsdFile(sheetSrcMode, sheetSrcSchema, sheetSrcFile)
      const tgtFile = await resolveXsdFile(sheetTgtMode, sheetTgtSchema, sheetTgtFile)
      if (!srcFile || !tgtFile) { setSheetError('Please select or upload both XSD files.'); return }
      const res = await mappingAPI.fromSheet(srcFile, tgtFile, sheetFile, sheetMmapName)
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

  const loadPreview = async () => {
    if (!sheetFile) return
    setPreviewLoading(true); setSheetError('')
    try {
      const srcFile = await resolveXsdFile(sheetSrcMode, sheetSrcSchema, sheetSrcFile)
      const tgtFile = await resolveXsdFile(sheetTgtMode, sheetTgtSchema, sheetTgtFile)
      if (!srcFile || !tgtFile) { setSheetError('Please select or upload both XSD files.'); setPreviewLoading(false); return }
      const r = await mappingAPI.previewSheet(srcFile, tgtFile, sheetFile)
      setSheetPreview(r.data)
      setSheetStep('preview')
    } catch (e: any) {
      const msg = e?.response?.data ? await new Response(e.response.data).text().then(t => { try { return JSON.parse(t).detail } catch { return t } }) : e?.message
      setSheetError(msg || 'Preview failed')
    } finally { setPreviewLoading(false) }
  }

  const updatePreviewRow = (idx: number, field: string, value: string | boolean) => {
    setSheetPreview(prev => {
      if (!prev) return prev
      const rows = [...prev.rows]
      // source_matched / target_matched come in as string 'true' — convert to bool
      const coerced = (field === 'source_matched' || field === 'target_matched')
        ? value === 'true' || value === true
        : value
      rows[idx] = { ...rows[idx], [field]: coerced }
      return { ...prev, rows }
    })
  }

  const deriveAllRules = async () => {
    if (!sheetPreview) return
    setDerivingAll(true)
    try {
      const r = await mappingAPI.deriveRules(sheetPreview.rows)
      setSheetPreview(prev => prev ? { ...prev, rows: r.data.rows } : prev)
    } catch (e: any) { setSheetError('AI derive failed') }
    finally { setDerivingAll(false) }
  }

  const deriveOneRule = async (idx: number) => {
    if (!sheetPreview) return
    setDerivingRow(idx)
    try {
      const r = await mappingAPI.deriveRules([sheetPreview.rows[idx]])
      const derived = r.data.rows[0]
      updatePreviewRow(idx, 'technical_rule', derived.technical_rule || '')
      updatePreviewRow(idx, 'ai_derived', derived.ai_derived)
    } catch {} finally { setDerivingRow(null) }
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

          {/* ── Step indicator ─── */}
          <div className="flex items-center gap-2 text-xs">
            {[
              { id: 'upload', label: '1. Upload Files' },
              { id: 'preview', label: '2. Preview & Edit' },
              { id: 'generate', label: '3. Generate .mmap' },
            ].map((step, i) => (
              <React.Fragment key={step.id}>
                {i > 0 && <div className="w-6 h-px bg-gray-700" />}
                <button
                  onClick={() => step.id !== 'generate' || sheetPreview ? setSheetStep(step.id as any) : undefined}
                  className={`px-3 py-1 rounded-full font-medium transition-colors ${
                    sheetStep === step.id
                      ? 'bg-blue-600 text-white'
                      : sheetPreview || step.id === 'upload'
                      ? 'bg-gray-800 text-gray-300 hover:text-white'
                      : 'bg-gray-900 text-gray-600 cursor-default'
                  }`}
                >
                  {step.label}
                </button>
              </React.Fragment>
            ))}
          </div>

          {/* ── Step 1: Upload ─── */}
          {sheetStep === 'upload' && (
            <div className="card space-y-5">

              {/* ── Quick Start from Prebuilt ── */}
              <div className="rounded-xl border border-amber-700/40 bg-amber-950/20 p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Zap size={14} className="text-amber-400 shrink-0" />
                  <p className="text-sm font-semibold text-white">Quick Start from Prebuilt Mapping</p>
                  <span className="text-xs text-gray-500">— auto-selects XSDs and loads all mapped fields</span>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={selectedPrebuilt}
                    onChange={e => { setSelectedPrebuilt(e.target.value); loadFromPrebuilt(e.target.value) }}
                    className="input-field flex-1 text-sm"
                    disabled={loadingPrebuilt}
                  >
                    <option value="">— Select a standard SAP mapping pair —</option>
                    {['Material','Customer','Vendor','Procurement','Sales','Finance','Logistics'].map(grp => {
                      const pairs = CATALOG_PAIRS.filter(p => p.group === grp)
                      if (!pairs.length) return null
                      return (
                        <optgroup key={grp} label={`── ${grp} ──`}>
                          {pairs.map(p => (
                            <option key={p.id} value={p.id}
                              disabled={prebuilt[p.id]?.status !== 'ready'}
                            >
                              {prebuilt[p.id]?.status === 'ready'
                                ? `${p.label}  (${prebuilt[p.id].fields} fields)`
                                : `${p.label}  — not generated`}
                            </option>
                          ))}
                        </optgroup>
                      )
                    })}
                  </select>
                  {loadingPrebuilt && <Loader2 size={16} className="animate-spin text-amber-400 shrink-0" />}
                  {selectedPrebuilt && !loadingPrebuilt && (
                    <button onClick={() => { setSelectedPrebuilt(''); setSheetSrcSchema(''); setSheetTgtSchema(''); setSheetPreview(null); setSheetStep('upload') }}
                      className="text-gray-500 hover:text-red-400 shrink-0" title="Clear"><X size={14} /></button>
                  )}
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">
                  Selects the paired XSDs automatically and populates the mapping table with AI-verified field mappings.
                  Edit rows, add new fields, or tweak rules — then click <strong className="text-white">Generate .mmap</strong>.
                  {Object.values(prebuilt).filter(p => p.status !== 'ready').length > 0 && (
                    <span className="text-amber-500/80"> Greyed-out pairs need generation — go to Schema Mapping → Pre-built Catalog.</span>
                  )}
                </p>
              </div>

              {/* Download template banner */}
              <div className="flex items-center justify-between rounded-xl bg-blue-950/30 border border-blue-800/50 px-4 py-3">
                <div>
                  <p className="text-sm font-semibold text-white">Start with the template</p>
                  <p className="text-xs text-gray-400 mt-0.5">Pre-filled with examples, Function Reference sheet, and Instructions for functional consultants</p>
                </div>
                <button
                  onClick={async () => {
                    try {
                      const r = await mappingAPI.template()
                      const url = URL.createObjectURL(new Blob([r.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
                      const a = document.createElement('a'); a.href = url; a.download = 'CPI_Mapping_Template.xlsx'; a.click()
                      URL.revokeObjectURL(url)
                    } catch {}
                  }}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors whitespace-nowrap shrink-0"
                >
                  <Download size={14} /> Download Template
                </button>
              </div>

              {/* File / Catalog grid */}
              <div className="grid grid-cols-3 gap-3">

                {/* ── Source XSD ── */}
                <XsdSlot
                  label="Source XSD"
                  accentClass="blue"
                  mode={sheetSrcMode}
                  onModeChange={m => { setSheetSrcMode(m); setSheetPreview(null); setSheetStep('upload') }}
                  selectedSchema={sheetSrcSchema}
                  onSchemaChange={v => { setSheetSrcSchema(v); setSheetPreview(null); setSheetStep('upload') }}
                  uploadedFile={sheetSrcFile}
                  onFileChange={f => { setSheetSrcFile(f); setSheetPreview(null); setSheetStep('upload') }}
                  fileRef={sheetSrcRef}
                  schemas={catalogSchemas}
                />

                {/* ── Target XSD ── */}
                <XsdSlot
                  label="Target XSD"
                  accentClass="green"
                  mode={sheetTgtMode}
                  onModeChange={m => { setSheetTgtMode(m); setSheetPreview(null); setSheetStep('upload') }}
                  selectedSchema={sheetTgtSchema}
                  onSchemaChange={v => { setSheetTgtSchema(v); setSheetPreview(null); setSheetStep('upload') }}
                  uploadedFile={sheetTgtFile}
                  onFileChange={f => { setSheetTgtFile(f); setSheetPreview(null); setSheetStep('upload') }}
                  fileRef={sheetTgtRef}
                  schemas={catalogSchemas}
                />

                {/* ── Mapping Sheet ── */}
                <div className="space-y-2">
                  <label className="label mb-0">Mapping Sheet</label>
                  <button type="button" onClick={() => sheetFileRef.current?.click()}
                    className={`w-full flex flex-col items-center justify-center gap-2 h-28 rounded-lg border-2 border-dashed transition-colors cursor-pointer
                      ${sheetFile ? 'border-purple-600/60 bg-purple-900/10' : 'border-gray-700 hover:border-gray-500 bg-gray-800/30'}`}>
                    {sheetFile
                      ? <><FileSpreadsheet size={20} className="text-purple-400" /><span className="text-xs text-purple-400 font-medium truncate max-w-full px-2">{sheetFile.name}</span></>
                      : <><FileSpreadsheet size={18} className="text-gray-500" /><span className="text-xs text-gray-500">Click to upload</span><span className="text-xs text-gray-600">.xlsx / .csv</span></>
                    }
                  </button>
                  <input ref={sheetFileRef} type="file" accept=".xlsx,.xlsm,.csv" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) { setSheetFile(f); setSheetPreview(null); setSheetStep('upload'); e.target.value = '' } }} />
                  {sheetFile && <button onClick={() => { setSheetFile(null); setSheetPreview(null) }} className="text-xs text-gray-500 hover:text-red-400 flex items-center gap-1"><X size={10} />Remove</button>}
                </div>
              </div>

              {sheetError && (
                <div className="flex items-start gap-2 rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-xs text-red-300">
                  <AlertCircle size={13} className="shrink-0 mt-0.5" />
                  <span><strong>Error: </strong>{sheetError}</span>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={loadPreview}
                  disabled={previewLoading || !sheetSrcReady || !sheetTgtReady || !sheetFile}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50">
                  {previewLoading ? <Loader2 size={15} className="animate-spin" /> : <Eye size={15} />}
                  {previewLoading ? 'Parsing…' : 'Preview Sheet'}
                </button>
                <p className="text-xs text-gray-500 self-center">Parses the sheet and shows which fields matched the XSD — before generating any .mmap</p>
              </div>

              {/* Sheet format reference */}
              <details className="border border-gray-700 rounded-lg overflow-hidden">
                <summary className="px-4 py-2.5 text-xs font-semibold text-gray-400 cursor-pointer hover:text-white bg-gray-800/40 select-none">
                  Expected sheet format & Mapping Rule syntax
                </summary>
                <div className="p-4 space-y-3">
                  <div className="overflow-x-auto rounded-lg border border-gray-700">
                    <table className="text-xs w-full">
                      <thead className="bg-gray-800">
                        <tr>
                          {['Source Field','Target Field','Functional Mapping Rule','Technical Mapping Rule','Notes'].map(h => (
                            <th key={h} className={`px-2 py-1.5 text-left font-semibold ${
                              h.includes('Functional') ? 'text-purple-400' :
                              h.includes('Technical') ? 'text-blue-400' : 'text-gray-400'}`}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {[
                          ['MaterialNumber', 'MATNR', 'Direct copy', '', ''],
                          ['CreationDate', 'ERSDA', 'Reformat date from YYYYMMDD to YYYY-MM-DD', 'formatDate((/CreationDate), yyyyMMdd, yyyy-MM-dd)', ''],
                          ['Sender + CompCode', 'SystemId', 'Concatenate Sender and CompCode with hyphen', '(/Sender)+- +(/CompCode)', ''],
                          ['Status', 'StatusText', 'Map: A=Active, I=Inactive', "mapWithDefault((/Status), A, Active, I, Inactive, Unknown)", ''],
                        ].map((row, i) => (
                          <tr key={i} className="hover:bg-gray-800/40">
                            {row.map((cell, j) => (
                              <td key={j} className={`px-2 py-1 font-mono text-[10px] ${
                                j === 2 ? 'text-purple-300 italic' :
                                j === 3 ? 'text-amber-400' : 'text-white'}`}>{cell || <span className="text-gray-600">—</span>}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-gray-500">
                    <span className="text-purple-400 font-medium">Functional Rule</span> — plain English for functional consultants (AI derives Technical Rule from this) &nbsp;|&nbsp;
                    <span className="text-blue-400 font-medium">Technical Rule</span> — CPI expression (overrides Functional if both present)
                  </p>
                </div>
              </details>
            </div>
          )}

          {/* ── Step 2: Preview & Edit ─── */}
          {sheetStep === 'preview' && sheetPreview && (
            <div className="space-y-3">
              {/* Stats bar */}
              <div className="flex items-center gap-3 flex-wrap">
                <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-green-900/30 border border-green-700/50 text-green-300">
                  <CheckCircle2 size={11} /> {sheetPreview.matched} matched
                </span>
                {sheetPreview.unmatched > 0 && (
                  <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-red-900/30 border border-red-700/50 text-red-300">
                    <AlertCircle size={11} /> {sheetPreview.unmatched} unmatched
                  </span>
                )}
                {sheetPreview.rows.filter(r => r.functional_rule && !r.technical_rule).length > 0 && (
                  <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-purple-900/30 border border-purple-700/50 text-purple-300">
                    <Wand2 size={11} /> {sheetPreview.rows.filter(r => r.functional_rule && !r.technical_rule).length} need AI derivation
                  </span>
                )}
                <div className="ml-auto flex gap-2">
                  <button onClick={() => setSheetStep('upload')}
                    className="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                    ← Back
                  </button>
                  <button
                    onClick={deriveAllRules}
                    disabled={derivingAll || sheetPreview.rows.filter(r => r.functional_rule && !r.technical_rule).length === 0}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-purple-700 hover:bg-purple-600 text-white rounded-lg transition-colors disabled:opacity-50">
                    {derivingAll ? <Loader2 size={11} className="animate-spin" /> : <Wand2 size={11} />}
                    {derivingAll ? 'Deriving…' : 'AI Derive All Rules'}
                  </button>
                  <button
                    onClick={() => setSheetStep('generate')}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors">
                    Continue → Generate .mmap
                  </button>
                </div>
              </div>

              {/* Preview table */}
              <div className="card p-0 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="text-xs w-full">
                    <thead className="bg-gray-800 sticky top-0">
                      <tr>
                        <th className="px-2 py-2 text-left text-gray-400 font-semibold w-4">#</th>
                        <th className="px-2 py-2 text-left text-blue-400 font-semibold">Source Field</th>
                        <th className="px-2 py-2 text-left text-green-400 font-semibold">Target Field</th>
                        <th className="px-2 py-2 text-left text-purple-400 font-semibold w-64">Functional Rule</th>
                        <th className="px-2 py-2 text-left text-amber-400 font-semibold w-72">Technical Rule (CPI expression)</th>
                        <th className="px-2 py-2 text-center text-gray-400 font-semibold w-20">Status</th>
                        <th className="px-2 py-2 text-center text-gray-400 font-semibold w-14">AI</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {sheetPreview.rows.map((row, i) => {
                        const isDirect = !row.functional_rule && !row.technical_rule && row.status !== 'unmatched'
                        const srcOk = row.source_matched !== false
                        const tgtOk = row.target_matched !== false
                        // Resolved full XPath — from backend (uploaded sheet) or prebuilt JSON
                        const srcFullPath = row.source_path || (row.source ? srcPathMap.get(row.source.toLowerCase()) : undefined)
                        const tgtFullPath = row.target_path || (row.target ? tgtPathMap.get(row.target.toLowerCase()) : undefined)
                        return (
                          <tr key={i} className={`hover:bg-gray-800/30 ${row.status === 'unmatched' ? 'bg-red-950/10' : ''}`}>
                            <td className="px-2 py-1 text-gray-600 text-[10px] align-top pt-2">{i + 1}</td>

                            {/* Source field + full XPath + picker if unmatched */}
                            <td className="px-1 py-1">
                              <div className="flex items-center gap-0.5">
                                <input value={row.source} onChange={e => updatePreviewRow(i, 'source', e.target.value)}
                                  className={`flex-1 min-w-0 bg-transparent rounded px-1.5 py-0.5 font-mono text-white outline-none transition-colors text-[10px]
                                    ${srcOk ? 'border border-transparent hover:border-blue-700/50 focus:border-blue-600'
                                            : 'border border-red-600/60 bg-red-950/20 focus:border-red-500'}`} />
                                {!srcOk && (
                                  <select onChange={e => { if (e.target.value) { updatePreviewRow(i, 'source', e.target.value); updatePreviewRow(i, 'source_matched', 'true') } e.target.value = '' }}
                                    className="text-[9px] bg-gray-800 border border-red-700/50 text-orange-300 rounded px-0.5 py-0.5 cursor-pointer max-w-[90px]" title="Pick from XSD">
                                    <option value="">↓ XSD</option>
                                    {sheetPreview.src_paths.map(p => {
                                      const seg = p.split('/').filter(Boolean).pop() ?? p
                                      return <option key={p} value={seg} title={p}>{seg}</option>
                                    })}
                                  </select>
                                )}
                              </div>
                              {srcFullPath
                                ? <div className="text-[9px] text-gray-600 font-mono truncate px-1.5 mt-0.5" title={srcFullPath}>{srcFullPath}</div>
                                : row.source && <div className="text-[9px] text-red-800 px-1.5 mt-0.5">not found in XSD</div>
                              }
                            </td>

                            {/* Target field + full XPath + picker if unmatched */}
                            <td className="px-1 py-1">
                              <div className="flex items-center gap-0.5">
                                <input value={row.target} onChange={e => updatePreviewRow(i, 'target', e.target.value)}
                                  className={`flex-1 min-w-0 bg-transparent rounded px-1.5 py-0.5 font-mono text-white outline-none transition-colors text-[10px]
                                    ${tgtOk ? 'border border-transparent hover:border-green-700/50 focus:border-green-600'
                                            : 'border border-red-600/60 bg-red-950/20 focus:border-red-500'}`} />
                                {!tgtOk && (
                                  <select onChange={e => { if (e.target.value) { updatePreviewRow(i, 'target', e.target.value); updatePreviewRow(i, 'target_matched', 'true') } e.target.value = '' }}
                                    className="text-[9px] bg-gray-800 border border-red-700/50 text-orange-300 rounded px-0.5 py-0.5 cursor-pointer max-w-[90px]" title="Pick from XSD">
                                    <option value="">↓ XSD</option>
                                    {sheetPreview.tgt_paths.map(p => {
                                      const seg = p.split('/').filter(Boolean).pop() ?? p
                                      return <option key={p} value={seg} title={p}>{seg}</option>
                                    })}
                                  </select>
                                )}
                              </div>
                              {tgtFullPath
                                ? <div className="text-[9px] text-gray-600 font-mono truncate px-1.5 mt-0.5" title={tgtFullPath}>{tgtFullPath}</div>
                                : row.target && <div className="text-[9px] text-red-800 px-1.5 mt-0.5">not found in XSD</div>
                              }
                            </td>

                            {/* Functional rule — blank for direct maps */}
                            <td className="px-1 py-1">
                              {isDirect
                                ? <span className="text-[9px] text-gray-700 italic px-1.5">direct</span>
                                : <input value={row.functional_rule || ''} onChange={e => updatePreviewRow(i, 'functional_rule', e.target.value)}
                                    placeholder="describe the mapping…"
                                    className="w-full bg-transparent border border-transparent hover:border-purple-700/50 focus:border-purple-600 rounded px-1.5 py-0.5 text-purple-300 italic outline-none transition-colors text-[10px] placeholder:text-gray-700" />
                              }
                            </td>

                            {/* Technical rule — blank for direct maps; derive button only when func_rule exists */}
                            <td className="px-1 py-1">
                              {isDirect
                                ? <span className="text-[9px] text-gray-700 italic px-1.5">direct</span>
                                : <div className="flex items-center gap-1">
                                    <input value={row.technical_rule || ''} onChange={e => updatePreviewRow(i, 'technical_rule', e.target.value)}
                                      placeholder={row.functional_rule && !row.technical_rule ? '← click ✨' : ''}
                                      className="flex-1 bg-transparent border border-transparent hover:border-amber-700/50 focus:border-amber-600 rounded px-1.5 py-0.5 font-mono text-amber-300 outline-none transition-colors text-[10px] placeholder:text-gray-600" />
                                    {row.functional_rule && (
                                      <button onClick={() => deriveOneRule(i)} disabled={derivingRow === i}
                                        className={`shrink-0 p-1 rounded transition-colors ${
                                          row.technical_rule ? 'text-gray-600 hover:text-purple-400' : 'text-purple-400 hover:text-purple-200 bg-purple-900/20'
                                        }`} title="AI derive technical rule from functional description">
                                        {derivingRow === i ? <Loader2 size={11} className="animate-spin" /> : <Wand2 size={11} />}
                                      </button>
                                    )}
                                    {row.ai_derived && <span title="AI derived" className="shrink-0 text-purple-400 text-[9px]">✨</span>}
                                  </div>
                              }
                            </td>

                            {/* Status badge */}
                            <td className="px-2 py-1 text-center">
                              <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold ${
                                row.status === 'matched'   ? 'bg-green-900/40 text-green-300' :
                                row.status === 'unmatched' ? 'bg-red-900/40 text-red-300' :
                                'bg-gray-800 text-gray-500'
                              }`}>
                                {row.status === 'matched' ? '✓' : row.status === 'unmatched' ? '✗' : '—'}
                              </span>
                            </td>

                            {/* AI derived indicator */}
                            <td className="px-2 py-1 text-center">
                              {row.ai_derived && <span className="text-[9px] text-purple-400">✨</span>}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Unmatched detail */}
              {sheetPreview.unmatched_detail.length > 0 && (
                <details className="border border-red-800/50 rounded-lg overflow-hidden">
                  <summary className="px-4 py-2.5 text-xs font-semibold text-red-300 cursor-pointer bg-red-950/20 select-none">
                    ✗ {sheetPreview.unmatched} unmatched fields — click to see details
                  </summary>
                  <div className="p-3 space-y-1">
                    {sheetPreview.unmatched_detail.map((u, i) => (
                      <div key={i} className="text-xs text-gray-400">
                        <span className="text-red-400 font-mono">{u.source || '(blank)'}</span>
                        <span className="text-gray-600"> → </span>
                        <span className="text-red-400 font-mono">{u.target || '(blank)'}</span>
                        <span className="text-gray-600"> — {u.reason}</span>
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {sheetError && (
                <div className="flex items-start gap-2 rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-xs text-red-300">
                  <AlertCircle size={13} className="shrink-0 mt-0.5" />
                  <span><strong>Error: </strong>{sheetError}</span>
                </div>
              )}
            </div>
          )}

          {/* ── Step 3: Generate ─── */}
          {sheetStep === 'generate' && sheetPreview && (
            <div className="card space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-900/40 border border-blue-700/50 flex items-center justify-center">
                  <Package size={18} className="text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">Generate .mmap file</p>
                  <p className="text-xs text-gray-400">
                    {sheetPreview.matched} matched fields &nbsp;·&nbsp;
                    {sheetPreview.rows.filter(r => r.ai_derived).length} AI-derived rules &nbsp;·&nbsp;
                    {sheetPreview.unmatched} unmatched (will be skipped)
                  </p>
                </div>
                <button onClick={() => setSheetStep('preview')} className="ml-auto text-xs text-gray-500 hover:text-white">← Back to Preview</button>
              </div>

              <div className="flex items-center gap-3">
                <label className="text-xs text-gray-400 whitespace-nowrap">Mapping name:</label>
                <input type="text" className="input-field text-sm py-1 px-2 w-60"
                  placeholder="MM_SheetMapping"
                  value={sheetMmapName}
                  onChange={e => setSheetMmapName(e.target.value.replace(/\s+/g, '_'))} />
              </div>

              {IS_STATIC_HOST ? (
                <div className="flex items-center gap-2 px-4 py-3 rounded-lg text-sm bg-amber-900/40 border border-amber-700/50 text-amber-300">
                  <AlertCircle size={15} className="shrink-0" />
                  Backend not available on GitHub Pages — run locally to use this feature
                </div>
              ) : (
                <button
                  onClick={generateFromSheet}
                  disabled={sheetLoading || !sheetSrcFile || !sheetTgtFile || !sheetFile}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50">
                  {sheetLoading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
                  {sheetLoading ? 'Building .mmap…' : 'Download .mmap'}
                </button>
              )}

              {sheetSummary && !sheetError && (
                <div className="flex items-center gap-2 rounded-lg bg-green-950/50 border border-green-700/50 px-3 py-2 text-xs text-green-300">
                  <CheckCircle2 size={13} className="shrink-0" />
                  {sheetSummary} — .mmap downloaded.
                </div>
              )}
              {sheetError && (
                <div className="flex items-start gap-2 rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-xs text-red-300">
                  <AlertCircle size={13} className="shrink-0 mt-0.5" />
                  <span><strong>Error: </strong>{sheetError}</span>
                </div>
              )}
            </div>
          )}
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
