import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  Shuffle, Loader2, Wand2, Zap, Upload, X, Plus, FileCode,
  Package, BookOpen, ArrowRight,
  CheckCircle2, Clock, RefreshCw, Download, Eye, FileSpreadsheet,
  AlertCircle, Sparkles, Lightbulb,
} from 'lucide-react'
import { mappingAPI } from '../api/client'
import { IS_STATIC_HOST } from '../components/Layout'

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

// ── Searchable XPath picker ───────────────────────────────────────────────────

function XPathPicker({
  value, onChange, paths, onSelect, isUnmatched, accentColor,
}: {
  value: string
  onChange: (v: string) => void
  paths: string[]
  onSelect: (path: string, fieldName: string) => void
  isUnmatched: boolean
  accentColor: 'blue' | 'green'
}) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')
  const ref = React.useRef<HTMLDivElement>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)
  const searchRef = React.useRef<HTMLInputElement>(null)

  // Close on outside click
  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false); setSearch('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Focus search input when dropdown opens
  React.useEffect(() => {
    if (open) setTimeout(() => searchRef.current?.focus(), 50)
  }, [open])

  const filtered = React.useMemo(() => {
    if (!search) return paths
    const q = search.toLowerCase()
    return paths.filter(p =>
      p.toLowerCase().includes(q) ||
      (p.split('/').filter(Boolean).pop() ?? '').toLowerCase().includes(q)
    )
  }, [paths, search])

  const accent = accentColor === 'blue'
    ? { border: 'border-blue-600', focus: 'focus:border-blue-500', tag: 'text-blue-300', btn: 'hover:border-blue-600/60' }
    : { border: 'border-green-600', focus: 'focus:border-green-500', tag: 'text-green-300', btn: 'hover:border-green-600/60' }

  return (
    <div ref={ref} className="relative flex-1 min-w-0">
      <div className="flex items-center gap-0.5">
        <input
          ref={inputRef}
          value={value}
          onChange={e => onChange(e.target.value)}
          className={`flex-1 min-w-0 bg-gray-900/60 rounded-l px-2 py-1 font-mono text-xs text-white outline-none transition-colors
            ${isUnmatched ? 'border border-red-600 bg-red-950/30' : `border border-gray-700 ${accent.focus} hover:border-gray-600`}`}
        />
        {paths.length > 0 && (
          <button
            type="button"
            onClick={() => setOpen(o => !o)}
            className={`shrink-0 px-1.5 py-1 bg-gray-800 border border-gray-700 ${accent.btn} rounded-r text-gray-400 hover:text-white transition-colors text-[10px] font-bold`}
            title="Search XSD paths"
          >
            {open ? '▲' : '▼'}
          </button>
        )}
      </div>

      {open && paths.length > 0 && (
        <div className="absolute top-full left-0 z-50 mt-0.5 w-80 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
          {/* Search input */}
          <div className="px-2 py-2 border-b border-gray-700">
            <input
              ref={searchRef}
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search field name or XPath…"
              className="w-full bg-gray-800 border border-gray-700 focus:border-blue-600 rounded-lg px-2.5 py-1.5 text-xs text-white outline-none placeholder:text-gray-500"
            />
          </div>
          {/* Results */}
          <div className="max-h-56 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="px-3 py-3 text-xs text-gray-500 text-center">No paths match "{search}"</div>
            ) : filtered.map(p => {
              const seg = p.split('/').filter(Boolean).pop() ?? p
              return (
                <button key={p} type="button"
                  onClick={() => { onSelect(p, seg); setOpen(false); setSearch('') }}
                  className={`w-full text-left px-3 py-1.5 hover:bg-gray-800 transition-colors group`}>
                  <div className={`text-xs font-semibold font-mono ${accent.tag}`}>{seg}</div>
                  <div className="text-[9px] text-gray-500 font-mono truncate group-hover:text-gray-400">{p}</div>
                </button>
              )
            })}
          </div>
          <div className="px-3 py-1.5 border-t border-gray-800 text-[9px] text-gray-600">
            {filtered.length} of {paths.length} paths
          </div>
        </div>
      )}
    </div>
  )
}

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
  mode: 'catalog' | 'upload' | 'paste'
  onModeChange: (m: 'catalog' | 'upload' | 'paste') => void
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

  // Paste mode state (local — converts to File on change)
  const [pasteText, setPasteText] = React.useState('')
  const [pasteDetected, setPasteDetected] = React.useState('')

  const handlePaste = (text: string) => {
    setPasteText(text)
    if (!text.trim()) { onFileChange(null); setPasteDetected(''); return }
    // Auto-detect type
    const isXsd = text.includes('XMLSchema') || text.includes('xs:schema') || text.includes('xsd:schema')
    const type  = isXsd ? 'XSD' : 'XML'
    setPasteDetected(type)
    // Wrap as a File so the rest of the pipeline handles it identically
    const ext  = isXsd ? '.xsd' : '.xml'
    const blob = new Blob([text], { type: 'text/xml' })
    const file = new File([blob], `pasted${ext}`, { type: 'text/xml' })
    onFileChange(file)
  }

  return (
    <div className="space-y-2">
      {/* Label + mode toggle — 3 tabs */}
      <div className="flex items-center justify-between">
        <label className="label mb-0">{label}</label>
        <div className="flex rounded-md overflow-hidden border border-gray-700 text-[10px] font-semibold">
          {(['catalog', 'upload', 'paste'] as const).map(m => (
            <button key={m} onClick={() => onModeChange(m)}
              className={`px-2 py-0.5 capitalize transition-colors ${mode === m ? a.tabActive : 'bg-gray-800 text-gray-500 hover:text-gray-300'}`}>
              {m === 'paste' ? 'Paste XML' : m}
            </button>
          ))}
        </div>
      </div>

      {/* Catalog mode */}
      {mode === 'catalog' && (
        <div className={`rounded-lg border-2 ${selectedSchema ? a.border + ' ' + a.bg : 'border-gray-700 bg-gray-800/30'} p-2 space-y-1.5`}>
          {odataSchemas.length > 0 && (
            <div>
              <p className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1">OData APIs (S/4HANA 2025FPS00)</p>
              <div className="grid grid-cols-1 gap-0.5 max-h-36 overflow-y-auto">
                {odataSchemas.map(s => (
                  <button key={s.filename} onClick={() => onSchemaChange(s.filename)}
                    className={`text-left text-[10px] px-2 py-1 rounded transition-colors truncate ${selectedSchema === s.filename ? `${a.tabActive} font-semibold` : `text-gray-400 hover:text-white hover:bg-gray-700`}`}>
                    {s.stem}
                  </button>
                ))}
              </div>
            </div>
          )}
          {idocSchemas.length > 0 && (
            <div>
              <p className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mb-1 mt-1">IDoc Types</p>
              <div className="grid grid-cols-1 gap-0.5 max-h-36 overflow-y-auto">
                {idocSchemas.map(s => (
                  <button key={s.filename} onClick={() => onSchemaChange(s.filename)}
                    className={`text-left text-[10px] px-2 py-1 rounded transition-colors truncate ${selectedSchema === s.filename ? `${a.tabActive} font-semibold` : `text-gray-400 hover:text-white hover:bg-gray-700`}`}>
                    {s.stem}
                  </button>
                ))}
              </div>
            </div>
          )}
          {schemas.length === 0 && <p className="text-xs text-gray-600 text-center py-3">Loading schemas…</p>}
          {selectedSchema && (
            <div className={`flex items-center gap-1 mt-1 pt-1 border-t border-gray-700/50 ${a.text} text-[10px]`}>
              <CheckCircle2 size={10} className="shrink-0" />
              <span className="truncate font-medium">{selectedSchema}</span>
              <button onClick={() => onSchemaChange('')} className="ml-auto text-gray-600 hover:text-red-400 shrink-0"><X size={9} /></button>
            </div>
          )}
        </div>
      )}

      {/* Upload mode */}
      {mode === 'upload' && (
        <>
          <button type="button" onClick={() => fileRef.current?.click()}
            className={`w-full flex flex-col items-center justify-center gap-2 h-24 rounded-lg border-2 border-dashed transition-colors cursor-pointer
              ${uploadedFile ? a.border + ' ' + a.bg : 'border-gray-700 hover:border-gray-500 bg-gray-800/30'}`}>
            {uploadedFile
              ? <><FileCode size={18} className={a.text} /><span className={`text-xs font-medium truncate max-w-full px-2 ${a.text}`}>{uploadedFile.name}</span></>
              : <><Upload size={16} className="text-gray-500" /><span className="text-xs text-gray-500">Upload .xsd or .xml</span></>
            }
          </button>
          <input ref={fileRef} type="file" accept=".xsd,.xml" className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) { onFileChange(f); e.target.value = '' } }} />
          {uploadedFile && (
            <button onClick={() => onFileChange(null)} className="text-xs text-gray-500 hover:text-red-400 flex items-center gap-1"><X size={10} />Remove</button>
          )}
        </>
      )}

      {/* Paste mode — accepts raw XML or XSD */}
      {mode === 'paste' && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <p className="text-[10px] text-gray-500">Paste XSD schema or sample XML — auto-detected</p>
            {pasteDetected && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold ${pasteDetected === 'XSD' ? 'bg-orange-900/40 text-orange-300' : 'bg-blue-900/40 text-blue-300'}`}>
                {pasteDetected} detected
              </span>
            )}
          </div>
          <textarea
            value={pasteText}
            onChange={e => handlePaste(e.target.value)}
            placeholder={'Paste your XSD or XML here…\n\nExamples:\n<?xml version="1.0"?>\n<xs:schema ...> (XSD)\n\nor\n\n<MATMAS05><IDOC>... (XML)'}
            rows={7}
            className={`w-full bg-gray-900/60 border rounded-lg px-3 py-2 text-xs font-mono text-gray-200 outline-none transition-colors resize-none placeholder:text-gray-600
              ${uploadedFile && pasteText ? (a.border.replace('border-', 'border ') + ' ' + a.bg) : 'border-gray-700 focus:border-blue-600'}`}
          />
          {pasteText && (
            <button onClick={() => { setPasteText(''); setPasteDetected(''); onFileChange(null) }}
              className="text-xs text-gray-500 hover:text-red-400 flex items-center gap-1"><X size={10} />Clear</button>
          )}
        </div>
      )}
    </div>
  )
}

// ── Upload to CPI button (for generated .mmap files) ─────────────────────────

import { cpiAPI } from '../api/client'

function UploadToCpiButton({
  buildFile, artifactType, defaultName,
}: {
  buildFile: () => Promise<File>
  artifactType: string
  defaultName: string
}) {
  const [step, setStep]          = React.useState<'pick' | 'preview' | 'done'>('pick')
  const [open, setOpen]          = React.useState(false)
  const [packages, setPkgs]      = React.useState<Array<{id: string; name: string}>>([])
  const [pkg, setPkg]            = React.useState('')
  const [loadingPkgs, setLP]     = React.useState(false)
  const [buildingPreview, setBP] = React.useState(false)
  const [uploading, setUp]       = React.useState(false)
  const [msg, setMsg]            = React.useState('')
  const [previewUrl, setPreviewUrl]   = React.useState('')
  const [previewBody, setPreviewBody] = React.useState('')
  const [previewFile, setPreviewFile] = React.useState<File | null>(null)
  const [jsonError, setJsonError]     = React.useState('')

  const openModal = async () => {
    setOpen(true); setStep('pick'); setMsg(''); setLP(true)
    try {
      const r = await cpiAPI.packages()
      setPkgs(r.data.value || r.data || [])
    } catch { setPkgs([]) }
    finally { setLP(false) }
  }

  const goPreview = async () => {
    if (!pkg) { setMsg('Please select a package'); return }
    setBP(true); setMsg('')
    try {
      const file = await buildFile()
      setPreviewFile(file)
      const r = await cpiAPI.previewImport(file, pkg, artifactType)
      setPreviewUrl(r.data.cpi_url)
      setPreviewBody(JSON.stringify(r.data.body, null, 2))
      setJsonError('')
      setStep('preview')
    } catch (e: any) {
      setMsg('Preview failed: ' + (e?.response?.data?.detail || e?.message))
    } finally { setBP(false) }
  }

  const confirmUpload = async () => {
    let edited: Record<string, string>
    try { edited = JSON.parse(previewBody); setJsonError('') }
    catch { setJsonError('Invalid JSON — fix before uploading'); return }
    if (!previewFile) return
    setUp(true); setMsg('')
    try {
      await cpiAPI.importZip(previewFile, edited.PackageId ?? pkg, artifactType, edited.Id, edited.Name)
      setMsg('✓ Uploaded successfully!')
      setStep('done')
      setTimeout(() => { setOpen(false); setStep('pick') }, 1800)
    } catch (e: any) {
      setMsg('Error: ' + (e?.response?.data?.detail || e?.message || 'Upload failed'))
    } finally { setUp(false) }
  }

  const close = () => { setOpen(false); setStep('pick'); setMsg(''); setJsonError('') }

  return (
    <>
      <button onClick={openModal}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-green-700 hover:bg-green-600 text-white transition-colors">
        <Upload size={15} /> Upload to CPI
      </button>

      {open && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={close}>
          <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
              <div>
                <h3 className="text-white font-semibold">Upload to CPI</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {step === 'pick' ? 'Select target package' : step === 'preview' ? 'Review and edit request before sending' : 'Done'}
                </p>
              </div>
              <button onClick={close} className="text-gray-500 hover:text-white"><X size={16} /></button>
            </div>

            <div className="p-5 space-y-4">
              {step === 'pick' && (
                <>
                  <p className="text-xs text-gray-400">
                    Artifact: <span className="text-white font-mono">{defaultName}</span>
                    &nbsp;·&nbsp;Type: <span className="text-white">{artifactType === 'messagemapping' ? 'Message Mapping' : artifactType}</span>
                  </p>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Target Package</label>
                    {loadingPkgs
                      ? <div className="text-xs text-gray-500 py-2">Loading packages…</div>
                      : <select className="input-field w-full text-sm" value={pkg} onChange={e => setPkg(e.target.value)}>
                          <option value="">Select a package…</option>
                          {packages.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </select>}
                  </div>
                  {msg && <p className="text-xs text-red-300 bg-red-900/30 px-3 py-2 rounded-lg">{msg}</p>}
                  <div className="flex gap-2">
                    <button onClick={goPreview} disabled={buildingPreview || !pkg}
                      className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors">
                      {buildingPreview ? <Loader2 size={14} className="animate-spin" /> : null}
                      {buildingPreview ? 'Building…' : 'Preview Request →'}
                    </button>
                    <button onClick={close} className="px-4 py-2 text-sm text-gray-500 hover:text-white">Cancel</button>
                  </div>
                </>
              )}

              {step === 'preview' && (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1.5">Endpoint</label>
                    <div className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
                      <span className="text-xs font-bold text-green-400 shrink-0">POST</span>
                      <span className="text-xs font-mono text-gray-300 break-all">{previewUrl}</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-semibold text-gray-400">Request Body (JSON — editable)</label>
                      <span className="text-[10px] text-gray-600">ArtifactContent = ZIP sent at confirm</span>
                    </div>
                    <textarea value={previewBody} onChange={e => { setPreviewBody(e.target.value); setJsonError('') }}
                      rows={8} className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg px-3 py-2.5 text-xs font-mono text-gray-200 outline-none resize-none" />
                    {jsonError && <p className="text-xs text-red-400 mt-1">{jsonError}</p>}
                  </div>
                  {msg && <p className={`text-xs px-3 py-2 rounded-lg ${msg.startsWith('✓') ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>{msg}</p>}
                  <div className="flex gap-2">
                    <button onClick={confirmUpload} disabled={uploading}
                      className="flex items-center gap-2 px-5 py-2.5 bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors">
                      {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                      {uploading ? 'Uploading…' : 'Confirm Send'}
                    </button>
                    <button onClick={() => setStep('pick')} className="px-4 py-2.5 text-sm text-gray-400 hover:text-white">← Back</button>
                  </div>
                </>
              )}

              {step === 'done' && (
                <div className="flex items-center gap-3 py-4 text-green-300">
                  <CheckCircle2 size={20} /><span className="font-medium">Uploaded successfully!</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

// ── Step 3: Generate with ZIP preview ────────────────────────────────────────

function ZipPreviewStep({ sheetPreview, sheetMmapName, setSheetMmapName, sheetSrcMode, sheetSrcSchema, sheetSrcFile,
  sheetTgtMode, sheetTgtSchema, sheetTgtFile, sheetFile, sheetLoading, sheetSrcReady, sheetTgtReady,
  sheetSummary, sheetError, generateFromSheet, buildSheetFileFromPreview, resolveXsdFile, onBack }: any) {
  const [zipPreview, setZipPreview] = React.useState<{ files: string[]; mmap_xml: string; matched: number } | null>(null)
  const [previewLoading, setPreviewLoading] = React.useState(false)
  const [showXml, setShowXml] = React.useState(false)
  const [previewError, setPreviewError] = React.useState('')

  const srcXsdName = sheetSrcMode === 'catalog' ? sheetSrcSchema : sheetSrcFile?.name || 'source.xsd'
  const tgtXsdName = sheetTgtMode === 'catalog' ? sheetTgtSchema : sheetTgtFile?.name || 'target.xsd'

  // Static file list preview (no backend call needed)
  const staticFiles = [
    `mapping/${sheetMmapName || 'MM_Mapping'}.mmap`,
    `wsdl/${srcXsdName}`,
    ...(tgtXsdName && tgtXsdName !== srcXsdName ? [`wsdl/${tgtXsdName}`] : []),
  ]

  const loadXmlPreview = async () => {
    setPreviewLoading(true); setPreviewError('')
    try {
      const srcFile = await resolveXsdFile(sheetSrcMode, sheetSrcSchema, sheetSrcFile)
      const tgtFile = await resolveXsdFile(sheetTgtMode, sheetTgtSchema, sheetTgtFile)
      if (!srcFile || !tgtFile) { setPreviewError('XSD files not ready'); return }
      const sheet = sheetPreview ? buildSheetFileFromPreview() : sheetFile
      if (!sheet) { setPreviewError('No mapping sheet'); return }
      const r = await mappingAPI.previewZip(srcFile, tgtFile, sheet, sheetMmapName || 'MM_Mapping')
      setZipPreview(r.data)
      setShowXml(true)
    } catch (e: any) {
      setPreviewError(e?.response?.data?.detail || e?.message || 'Preview failed')
    } finally { setPreviewLoading(false) }
  }

  return (
    <div className="card space-y-5">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-900/40 border border-blue-700/50 flex items-center justify-center">
          <Package size={18} className="text-blue-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">Generate .mmap file</p>
          <p className="text-xs text-gray-400">
            {sheetPreview.matched} matched fields &nbsp;·&nbsp;
            {sheetPreview.rows.filter((r: any) => r.ai_derived).length} AI-derived rules &nbsp;·&nbsp;
            {sheetPreview.unmatched} unmatched (will be skipped)
          </p>
        </div>
        <button onClick={onBack} className="ml-auto text-xs text-gray-500 hover:text-white">← Back to Preview</button>
      </div>

      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-400 whitespace-nowrap">Mapping name:</label>
        <input type="text" className="input-field text-sm py-1 px-2 w-60"
          placeholder="MM_SheetMapping" value={sheetMmapName}
          onChange={e => setSheetMmapName(e.target.value.replace(/\s+/g, '_'))} />
      </div>

      {/* ZIP contents preview */}
      <div className="rounded-xl border border-gray-700 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 bg-gray-800/60">
          <div className="flex items-center gap-2 text-xs font-semibold text-gray-300">
            <FileCode size={13} className="text-blue-400" />
            ZIP Contents
          </div>
          <button
            onClick={showXml ? () => setShowXml(false) : loadXmlPreview}
            disabled={previewLoading}
            className="flex items-center gap-1.5 text-[10px] text-gray-400 hover:text-blue-300 transition-colors">
            {previewLoading ? <Loader2 size={11} className="animate-spin" /> : null}
            {showXml ? 'Hide .mmap XML ▲' : previewLoading ? 'Loading…' : 'Preview .mmap XML ▼'}
          </button>
        </div>

        {/* File list */}
        <div className="px-4 py-3 space-y-1.5 bg-gray-900/40">
          {staticFiles.map(f => (
            <div key={f} className="flex items-center gap-2 text-xs">
              <span className={`font-mono ${f.endsWith('.mmap') ? 'text-blue-300' : 'text-gray-400'}`}>
                {f.endsWith('.mmap') ? '📄' : '📋'} {f}
              </span>
              {f.endsWith('.mmap') && <span className="text-[9px] text-blue-700 bg-blue-900/20 px-1.5 py-0.5 rounded">mapping XML</span>}
              {f.includes('/wsdl/') && <span className="text-[9px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded">XSD schema</span>}
            </div>
          ))}
        </div>

        {/* mmap XML preview */}
        {previewError && (
          <div className="px-4 py-2 text-xs text-red-400 bg-red-950/20 border-t border-gray-700">{previewError}</div>
        )}
        {showXml && zipPreview && (
          <div className="border-t border-gray-700">
            <pre className="text-[10px] font-mono text-gray-300 p-4 overflow-x-auto max-h-64 bg-gray-950/60 leading-relaxed whitespace-pre-wrap break-all">
              {zipPreview.mmap_xml}
            </pre>
          </div>
        )}
      </div>

      {IS_STATIC_HOST ? (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg text-sm bg-amber-900/40 border border-amber-700/50 text-amber-300">
          <AlertCircle size={15} className="shrink-0" />
          Backend not available on GitHub Pages — run locally to use this feature
        </div>
      ) : (
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={generateFromSheet}
            disabled={sheetLoading || !sheetSrcReady || !sheetTgtReady || (!sheetFile && !sheetPreview)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50">
            {sheetLoading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
            {sheetLoading ? 'Building .mmap…' : 'Download .mmap'}
          </button>
          <UploadToCpiButton
            buildFile={async () => {
              const srcFile = await resolveXsdFile(sheetSrcMode, sheetSrcSchema, sheetSrcFile)
              const tgtFile = await resolveXsdFile(sheetTgtMode, sheetTgtSchema, sheetTgtFile)
              if (!srcFile || !tgtFile) throw new Error('XSD files not ready')
              const sheet = sheetPreview ? buildSheetFileFromPreview() : sheetFile
              if (!sheet) throw new Error('No mapping sheet')
              const res = await mappingAPI.fromSheet(srcFile, tgtFile, sheet, sheetMmapName)
              return new File([res.data], `${sheetMmapName}.zip`, { type: 'application/zip' })
            }}
            artifactType="messagemapping"
            defaultName={sheetMmapName}
          />
        </div>
      )}

      {sheetSummary && !sheetError && (
        <div className="flex items-center gap-2 rounded-lg bg-green-950/50 border border-green-700/50 px-3 py-2 text-xs text-green-300">
          <CheckCircle2 size={13} className="shrink-0" />{sheetSummary} — .mmap downloaded.
        </div>
      )}
      {sheetError && (
        <div className="flex items-start gap-2 rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-xs text-red-300">
          <AlertCircle size={13} className="shrink-0 mt-0.5" />
          <span><strong>Error: </strong>{sheetError}</span>
        </div>
      )}
    </div>
  )
}

export default function MessageMapping() {
  const [tab, setTab] = useState<'catalog' | 'sheet' | 'smart'>('catalog')

  const [filterGroup, setFilterGroup] = useState('All')

  // Pre-built state
  const [prebuilt, setPrebuilt] = useState<Record<string, PrebuiltInfo>>({})
  const [generatingAll, setGeneratingAll] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [generatingId, setGeneratingId] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState('')

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
    setCatalogError('')
    try {
      const res = await mappingAPI.prebuiltDownload(pair.id)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
      const a = document.createElement('a'); a.href = url; a.download = `${pair.name}.zip`; a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      setCatalogError(`Download failed for ${pair.id}: ${e?.message}`)
    } finally {
      setDownloadingId(null)
    }
  }

  // Generate single pre-built
  const generateSingle = async (pair: typeof CATALOG_PAIRS[0]) => {
    setGeneratingId(pair.id)
    setCatalogError('')
    try {
      await mappingAPI.prebuiltGenerate(pair.id)
      setTimeout(refreshPrebuilt, 3000)
      setTimeout(refreshPrebuilt, 8000)
      setTimeout(refreshPrebuilt, 15000)
    } catch (e: any) {
      setCatalogError(`Generation failed: ${e?.message}`)
    } finally {
      setGeneratingId(null)
    }
  }

  // Generate all pre-built
  const generateAll = async () => {
    setGeneratingAll(true)
    setCatalogError('')
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
      setCatalogError(`Generate all failed: ${e?.message}`)
      setGeneratingAll(false)
    }
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
  const [sheetSrcMode,   setSheetSrcMode]   = useState<'catalog' | 'upload' | 'paste'>('catalog')
  const [sheetTgtMode,   setSheetTgtMode]   = useState<'catalog' | 'upload' | 'paste'>('catalog')
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
    mode: 'catalog' | 'upload' | 'paste',
    catalogFilename: string,
    uploadedFile: File | null
  ): Promise<File | null> => {
    if (mode === 'upload' || mode === 'paste') return uploadedFile   // paste wraps text as File
    if (!catalogFilename) return null
    const r = await mappingAPI.schema(catalogFilename)
    const blob = new Blob([r.data.content], { type: 'text/xml' })
    return new File([blob], catalogFilename, { type: 'text/xml' })
  }

  const sheetSrcReady  = sheetSrcMode === 'catalog' ? !!sheetSrcSchema : !!sheetSrcFile
  const sheetTgtReady  = sheetTgtMode === 'catalog' ? !!sheetTgtSchema : !!sheetTgtFile

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

  // Build a CSV file from current preview rows (used when no sheet was uploaded, e.g. prebuilt quick-start)
  const buildSheetFileFromPreview = (): File => {
    const rows = sheetPreview?.rows ?? []
    const header = 'Source Field,Target Field,Functional Mapping Rule,Technical Mapping Rule'
    const lines  = rows
      .filter(r => r.source || r.target)
      .map(r => `"${(r.source||'').replace(/"/g,'""')}","${(r.target||'').replace(/"/g,'""')}","${(r.functional_rule||'').replace(/"/g,'""')}","${(r.technical_rule||'').replace(/"/g,'""')}"`)
    const csv = [header, ...lines].join('\n')
    return new File([csv], 'mapping.csv', { type: 'text/csv' })
  }

  const generateFromSheet = async () => {
    if (!sheetFile && !sheetPreview) return
    setSheetLoading(true); setSheetError(''); setSheetSummary('')
    try {
      const srcFile = await resolveXsdFile(sheetSrcMode, sheetSrcSchema, sheetSrcFile)
      const tgtFile = await resolveXsdFile(sheetTgtMode, sheetTgtSchema, sheetTgtFile)
      if (!srcFile || !tgtFile) { setSheetError('Please select or upload both XSD files.'); return }
      // Always use preview rows when available — they include all AI-derived rules and edits.
      // Fall back to the raw uploaded sheet only if no preview exists.
      const effectiveSheet = sheetPreview ? buildSheetFileFromPreview() : (sheetFile ?? buildSheetFileFromPreview())
      const res = await mappingAPI.fromSheet(srcFile, tgtFile, effectiveSheet, sheetMmapName)
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

  const deletePreviewRow = (idx: number) => {
    setSheetPreview(prev => {
      if (!prev) return prev
      const rows = prev.rows.filter((_, i) => i !== idx)
      return { ...prev, rows, matched: rows.filter(r => r.status === 'matched').length }
    })
  }

  const addPreviewRow = () => {
    setSheetPreview(prev => {
      if (!prev) return prev
      const newRow = { source: '', target: '', functional_rule: '', technical_rule: '', status: 'unmatched' as const, source_matched: false, target_matched: false }
      return { ...prev, rows: [...prev.rows, newRow] }
    })
  }

  const updatePreviewRow = (idx: number, field: string, value: string | boolean) => {
    setSheetPreview(prev => {
      if (!prev) return prev
      const rows = [...prev.rows]
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
      const allSrcFields = sheetPreview.rows
        .filter(r => r.source)
        .map(r => r.source)
        .filter((v, i, a) => a.indexOf(v) === i)
        .join(', ')
      const rowsWithContext = sheetPreview.rows.map(r => ({
        ...r,
        available_source_fields: allSrcFields,
      }))
      const r = await mappingAPI.deriveRules(rowsWithContext)
      setSheetPreview(prev => prev ? { ...prev, rows: r.data.rows } : prev)
    } catch { setSheetError('AI derive failed') }
    finally { setDerivingAll(false) }
  }

  const deriveOneRule = async (idx: number) => {
    if (!sheetPreview) return
    setDerivingRow(idx)
    try {
      // Send all rows for context so AI can resolve references to other fields
      // (e.g. "map date and time with T in between" needs to know both field names)
      const allSrcFields = sheetPreview.rows
        .filter(r => r.source)
        .map(r => r.source)
        .filter((v, i, a) => a.indexOf(v) === i)  // unique

      const rowWithContext = {
        ...sheetPreview.rows[idx],
        available_source_fields: allSrcFields.join(', '),
      }
      const r = await mappingAPI.deriveRules([rowWithContext])
      const derived = r.data.rows[0]
      updatePreviewRow(idx, 'technical_rule', derived.technical_rule || '')
      updatePreviewRow(idx, 'ai_derived', derived.ai_derived)
    } catch {} finally { setDerivingRow(null) }
  }

  // Smart Generate state
  const [smartSrcFile, setSmartSrcFile]   = useState<File | null>(null)
  const [smartSrcMode, setSmartSrcMode]   = useState<'catalog' | 'upload'>('catalog')
  const [smartSrcSchema, setSmartSrcSchema] = useState('')
  const [smartDesc, setSmartDesc]         = useState('')
  const [smartIdea, setSmartIdea]         = useState('')
  const [smartSrcName, setSmartSrcName]   = useState('MM_SmartMapping')
  const [smartIdeaName, setSmartIdeaName] = useState('MM_IdeaMapping')
  const [smartSrcLoading, setSmartSrcLoading] = useState(false)
  const [smartIdeaLoading, setSmartIdeaLoading] = useState(false)
  const [smartError, setSmartError]       = useState('')
  const smartSrcRef = useRef<HTMLInputElement>(null)

  const smartSrcReady = smartSrcMode === 'catalog' ? !!smartSrcSchema : !!smartSrcFile

  // Store generated blobs so user can download OR upload to CPI
  const [smartSrcBlob,  setSmartSrcBlob]  = useState<Blob | null>(null)
  const [smartSrcCount, setSmartSrcCount] = useState(0)
  const [smartIdeaBlob,  setSmartIdeaBlob]  = useState<Blob | null>(null)
  const [smartIdeaCount, setSmartIdeaCount] = useState(0)

  const downloadBlob = (blob: Blob, name: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `${name}.zip`; a.click()
    URL.revokeObjectURL(url)
  }

  const generateFromSourceXsd = async () => {
    if (!smartSrcReady || !smartDesc.trim()) return
    setSmartSrcLoading(true); setSmartError(''); setSmartSrcBlob(null)
    try {
      let xsdText = ''
      let xsdName = 'source.xsd'
      if (smartSrcMode === 'catalog' && smartSrcSchema) {
        const r = await mappingAPI.schema(smartSrcSchema)
        xsdText = r.data.content
        xsdName = smartSrcSchema
      } else if (smartSrcFile) {
        xsdText = await smartSrcFile.text()
        xsdName = smartSrcFile.name
      }
      const res = await mappingAPI.generateFromSource({
        source_xsd: xsdText,
        source_xsd_name: xsdName,
        description: smartDesc,
        mapping_name: smartSrcName || 'MM_SmartMapping',
      })
      const blob = new Blob([res.data], { type: 'application/zip' })
      setSmartSrcBlob(blob)
      setSmartSrcCount(parseInt(res.headers?.['x-mapping-count'] || '0', 10))
    } catch (e: any) {
      const msg = e?.response?.data ? await new Response(e.response.data).text().then((t: string) => { try { return JSON.parse(t).detail } catch { return t } }) : e?.message
      setSmartError(msg || 'Generation failed')
    } finally { setSmartSrcLoading(false) }
  }

  const generateFromIdea = async () => {
    if (!smartIdea.trim()) return
    setSmartIdeaLoading(true); setSmartError(''); setSmartIdeaBlob(null)
    try {
      const res = await mappingAPI.generateFromIdea({
        idea: smartIdea,
        mapping_name: smartIdeaName || 'MM_IdeaMapping',
      })
      const blob = new Blob([res.data], { type: 'application/zip' })
      setSmartIdeaBlob(blob)
      setSmartIdeaCount(parseInt(res.headers?.['x-mapping-count'] || '0', 10))
    } catch (e: any) {
      const msg = e?.response?.data ? await new Response(e.response.data).text().then((t: string) => { try { return JSON.parse(t).detail } catch { return t } }) : e?.message
      setSmartError(msg || 'Generation failed')
    } finally { setSmartIdeaLoading(false) }
  }

  const readyCount  = Object.values(prebuilt).filter(p => p.status === 'ready').length
  const totalCount  = CATALOG_PAIRS.length

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Shuffle size={24} className="text-green-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Message Mapping</h1>
          <p className="text-gray-400 text-sm">Generate SAP CPI .mmap files from mapping sheets, prebuilt pairs, or AI descriptions</p>
        </div>
      </div>

      <div className="flex gap-1 bg-gray-900 p-1 rounded-lg w-fit mb-6 border border-gray-800">
        <button onClick={() => setTab('catalog')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === 'catalog' ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
          <BookOpen size={13} className="inline mr-1.5" />Prebuilt Catalog
        </button>
        <button onClick={() => setTab('sheet')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === 'sheet' ? 'bg-sap-blue text-white' : 'text-gray-400 hover:text-white'}`}>
          <FileSpreadsheet size={13} className="inline mr-1.5" />Sheet Mapping
        </button>
        <button onClick={() => setTab('smart')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === 'smart' ? 'bg-purple-700 text-white' : 'text-gray-400 hover:text-white'}`}>
          <Sparkles size={13} className="inline mr-1.5" />AI Generate
        </button>
      </div>

      {tab === 'catalog' && (
        <div className="space-y-4">
          {/* Header actions */}
          <div className="flex items-center justify-between gap-2 flex-wrap">
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
            <button
              onClick={generateAll}
              disabled={generatingAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-sap-blue hover:bg-blue-600 text-white transition-colors disabled:opacity-60"
            >
              {generatingAll ? <Loader2 size={11} className="animate-spin" /> : <Wand2 size={11} />}
              {generatingAll ? 'Generating…' : 'Generate All with AI'}
            </button>
          </div>

          {/* Group filter chips */}
          <div className="flex flex-wrap gap-1.5">
            {groups.map(g => (
              <button key={g} onClick={() => setFilterGroup(g)}
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors ${filterGroup === g ? 'bg-sap-blue border-sap-blue text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white'}`}>
                {g}
              </button>
            ))}
          </div>

          {/* Pair cards */}
          <div className="grid grid-cols-1 gap-2">
            {filteredPairs.map((pair) => {
              const colors  = GROUP_COLORS[pair.group] ?? { card: 'border-gray-700 bg-gray-800', badge: 'bg-gray-700 text-gray-300' }
              const pb      = prebuilt[pair.id]
              const isReady = pb?.status === 'ready'

              return (
                <div key={pair.id} className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${colors.card}`}>
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
                  </div>
                </div>
              )
            })}
          </div>

          {catalogError && (
            <div className="rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-xs text-red-300">
              <span className="font-semibold">Error: </span>{catalogError}
            </div>
          )}

          <p className="text-[10px] text-gray-600 leading-relaxed">
            <strong className="text-gray-500">Pre-built .mmap</strong> — Claude AI analyses both schemas and maps only fields with a real semantic equivalent.
            No forced mappings, no parent containers, no guessing.
            Click <em>Generate</em> on any row to create it (uses Groq API), or <em>Generate All with AI</em> for all {totalCount} pairs.
            Once ready, <em>.mmap</em> downloads instantly — no API call needed at download time.
          </p>
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
              {/* Stats computed live so they update as user fixes fields */}
              {(() => {
                const liveMatched   = sheetPreview.rows.filter(r => r.source_matched !== false && r.target_matched !== false && (r.source || r.target)).length
                const liveUnmatched = sheetPreview.rows.filter(r => (r.source_matched === false || r.target_matched === false) && (r.source || r.target)).length
                const needAI = sheetPreview.rows.filter(r => r.functional_rule && !r.technical_rule).length
                return (
              <div className="flex items-center gap-3 flex-wrap">
                <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-green-900/30 border border-green-700/50 text-green-300">
                  <CheckCircle2 size={11} /> {liveMatched} matched
                </span>
                {liveUnmatched > 0 && (
                  <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-red-900/30 border border-red-700/50 text-red-300">
                    <AlertCircle size={11} /> {liveUnmatched} unmatched
                  </span>
                )}
                {needAI > 0 && (
                  <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-purple-900/30 border border-purple-700/50 text-purple-300">
                    <Wand2 size={11} /> {needAI} need AI derivation
                  </span>
                )}
                <div className="ml-auto flex gap-2">
                  <button onClick={() => setSheetStep('upload')}
                    className="px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                    ← Back
                  </button>
                  <button
                    onClick={deriveAllRules}
                    disabled={derivingAll || needAI === 0}
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
                ) // end IIFE return
              })()} {/* end IIFE */}

              {/* Preview — card-per-row layout (no horizontal scrolling) */}
              <div className="space-y-1.5 -mx-2">
                {/* Column headers */}
                <div className="grid grid-cols-[2rem_1fr_1fr_1fr_1fr_2.5rem_1.5rem] gap-2 px-3 pb-1 border-b border-gray-700">
                  <span className="text-[10px] font-semibold text-gray-600">#</span>
                  <span className="text-[10px] font-semibold text-blue-400">Source Field</span>
                  <span className="text-[10px] font-semibold text-green-400">Target Field</span>
                  <span className="text-[10px] font-semibold text-purple-400">Functional Rule</span>
                  <span className="text-[10px] font-semibold text-amber-400">Technical Rule</span>
                  <span className="text-[10px] font-semibold text-gray-600 text-center">OK</span>
                  <span></span>{/* delete column header */}
                </div>

                {sheetPreview.rows.map((row, i) => {
                  const isDirect = !row.functional_rule && !row.technical_rule && row.status !== 'unmatched'
                  const srcOk = row.source_matched !== false
                  const tgtOk = row.target_matched !== false
                  // If source/target is already a full XPath (contains /) use it directly;
                  // otherwise look up the last-segment in the path map from the XSD
                  const srcFullPath = row.source_path
                    || (row.source?.includes('/') ? row.source : row.source ? srcPathMap.get(row.source.toLowerCase()) : undefined)
                  const tgtFullPath = row.target_path
                    || (row.target?.includes('/') ? row.target : row.target ? tgtPathMap.get(row.target.toLowerCase()) : undefined)

                  return (
                    <div key={i} className={`rounded-lg border px-3 py-2 transition-colors ${
                      row.status === 'unmatched' ? 'bg-red-950/10 border-red-800/40' : 'bg-gray-800/30 border-gray-700/50 hover:border-gray-600'
                    }`}>
                      {/* Row: # | Source | Target | Functional | Technical | Status | Delete */}
                      <div className="grid grid-cols-[2rem_1fr_1fr_1fr_1fr_2.5rem_1.5rem] gap-2 items-start">

                        {/* Row number */}
                        <span className="text-[10px] text-gray-600 pt-1.5 text-center">{i + 1}</span>

                        {/* Source field — searchable XPath picker */}
                        <div>
                          <XPathPicker
                            value={row.source}
                            onChange={v => updatePreviewRow(i, 'source', v)}
                            paths={sheetPreview.src_paths}
                            onSelect={(fullPath, seg) => {
                              updatePreviewRow(i, 'source', seg)
                              updatePreviewRow(i, 'source_path', fullPath)
                              updatePreviewRow(i, 'source_matched', 'true')
                            }}
                            isUnmatched={!srcOk}
                            accentColor="blue"
                          />
                          <div className={`text-[9px] font-mono mt-0.5 truncate pl-0.5 ${srcFullPath ? 'text-gray-500' : row.source ? 'text-red-700' : ''}`}
                            title={srcFullPath}>
                            {srcFullPath || (row.source ? 'not found in XSD' : '')}
                          </div>
                        </div>

                        {/* Target field — searchable XPath picker */}
                        <div>
                          <XPathPicker
                            value={row.target}
                            onChange={v => updatePreviewRow(i, 'target', v)}
                            paths={sheetPreview.tgt_paths}
                            onSelect={(fullPath, seg) => {
                              updatePreviewRow(i, 'target', seg)
                              updatePreviewRow(i, 'target_path', fullPath)
                              updatePreviewRow(i, 'target_matched', 'true')
                            }}
                            isUnmatched={!tgtOk}
                            accentColor="green"
                          />
                          <div className={`text-[9px] font-mono mt-0.5 truncate pl-0.5 ${tgtFullPath ? 'text-gray-500' : row.target ? 'text-red-700' : ''}`}
                            title={tgtFullPath}>
                            {tgtFullPath || (row.target ? 'not found in XSD' : '')}
                          </div>
                        </div>

                        {/* Functional rule */}
                        <input value={row.functional_rule || ''}
                          onChange={e => updatePreviewRow(i, 'functional_rule', e.target.value)}
                          placeholder={isDirect ? 'direct' : 'describe the mapping…'}
                          className="bg-gray-900/60 border border-gray-700 hover:border-purple-700/60 focus:border-purple-500 rounded px-2 py-1 text-xs text-purple-300 italic outline-none transition-colors placeholder:text-gray-600 w-full" />

                        {/* Technical rule + derive */}
                        <div className="flex items-center gap-1">
                          <input value={row.technical_rule || ''}
                            onChange={e => updatePreviewRow(i, 'technical_rule', e.target.value)}
                            placeholder={row.functional_rule && !row.technical_rule ? 'click ✨ to derive' : isDirect ? 'direct' : ''}
                            className="flex-1 min-w-0 bg-gray-900/60 border border-gray-700 hover:border-amber-700/60 focus:border-amber-500 rounded px-2 py-1 text-xs font-mono text-amber-300 outline-none transition-colors placeholder:text-gray-600" />
                          {row.functional_rule && (
                            <button onClick={() => deriveOneRule(i)} disabled={derivingRow === i}
                              className={`shrink-0 p-1.5 rounded-lg transition-colors ${row.technical_rule ? 'text-gray-600 hover:text-purple-400 hover:bg-gray-700' : 'text-purple-300 bg-purple-900/30 hover:bg-purple-900/50'}`}
                              title="AI derive from functional description">
                              {derivingRow === i ? <Loader2 size={12} className="animate-spin" /> : <Wand2 size={12} />}
                            </button>
                          )}
                          {row.ai_derived && <span className="text-[9px] text-purple-400 shrink-0" title="AI derived">✨</span>}
                        </div>

                        {/* Status — computed live from source_matched + target_matched, not the static parse-time field */}
                        <div className="flex items-start justify-center pt-1">
                          {(srcOk && tgtOk)
                            ? <span className="text-[10px] font-bold text-green-400">✓</span>
                            : (row.source || row.target)
                              ? <span className="text-[10px] font-bold text-red-400">✗</span>
                              : <span className="text-[10px] font-bold text-gray-600">—</span>
                          }
                        </div>

                        {/* Delete row */}
                        <div className="flex items-start justify-center pt-1">
                          <button onClick={() => deletePreviewRow(i)}
                            className="text-gray-600 hover:text-red-400 transition-colors p-0.5 rounded"
                            title="Delete this row">
                            <X size={12} />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Add Row button */}
              <button onClick={addPreviewRow}
                className="flex items-center gap-2 px-3 py-2 text-xs text-gray-400 hover:text-white bg-gray-800/50 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 rounded-lg transition-colors w-full justify-center">
                <Plus size={13} /> Add Row
              </button>

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
            <ZipPreviewStep
              sheetPreview={sheetPreview}
              sheetMmapName={sheetMmapName}
              setSheetMmapName={setSheetMmapName}
              sheetSrcMode={sheetSrcMode} sheetSrcSchema={sheetSrcSchema} sheetSrcFile={sheetSrcFile}
              sheetTgtMode={sheetTgtMode} sheetTgtSchema={sheetTgtSchema} sheetTgtFile={sheetTgtFile}
              sheetFile={sheetFile}
              sheetLoading={sheetLoading} sheetSrcReady={sheetSrcReady} sheetTgtReady={sheetTgtReady}
              sheetSummary={sheetSummary} sheetError={sheetError}
              generateFromSheet={generateFromSheet}
              buildSheetFileFromPreview={buildSheetFileFromPreview}
              resolveXsdFile={resolveXsdFile}
              onBack={() => setSheetStep('preview')}
            />
          )}
        </div>
      )}

      {/* ── AI Generate tab ─────────────────────────────────────────────── */}
      {tab === 'smart' && (
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-4 rounded-2xl bg-purple-950/30 border border-purple-700/40">
            <Sparkles size={22} className="text-purple-400 shrink-0" />
            <div>
              <p className="text-base font-bold text-white">Smart Mapping Generator</p>
              <p className="text-xs text-gray-400 mt-0.5">AI generates source XSD, target XSD, and field mappings — from whatever you have</p>
            </div>
          </div>

          {smartError && (
            <div className="flex items-start gap-2 rounded-lg bg-red-950/50 border border-red-800 px-4 py-3 text-sm text-red-300">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span><strong>Error: </strong>{smartError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">

            {/* Mode 1: Have Source XSD + Description */}
            <div className="card border border-blue-700/40 bg-blue-950/10 space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-800/60 flex items-center justify-center shrink-0">
                  <FileCode size={16} className="text-blue-300" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">I have a Source XSD</p>
                  <p className="text-xs text-gray-400">AI generates the target XSD and mapping</p>
                </div>
              </div>

              <div className="space-y-3">
                {/* Source XSD: catalog or upload */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-gray-400">Source XSD</label>
                    <div className="flex rounded-md overflow-hidden border border-gray-700 text-[10px] font-semibold">
                      <button onClick={() => setSmartSrcMode('catalog')}
                        className={`px-2 py-0.5 transition-colors ${smartSrcMode === 'catalog' ? 'bg-blue-700 text-white' : 'bg-gray-800 text-gray-500 hover:text-gray-300'}`}>
                        Catalog
                      </button>
                      <button onClick={() => setSmartSrcMode('upload')}
                        className={`px-2 py-0.5 transition-colors ${smartSrcMode === 'upload' ? 'bg-blue-700 text-white' : 'bg-gray-800 text-gray-500 hover:text-gray-300'}`}>
                        Upload
                      </button>
                    </div>
                  </div>

                  {smartSrcMode === 'catalog' ? (
                    <div className={`rounded-lg border-2 ${smartSrcSchema ? 'border-blue-600/60 bg-blue-900/10' : 'border-gray-700 bg-gray-800/30'} p-2 space-y-1.5`}>
                      <p className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider">SAP OData APIs (S/4HANA 2025FPS00)</p>
                      <div className="grid grid-cols-1 gap-0.5 max-h-24 overflow-y-auto">
                        {catalogSchemas.filter(s => s.kind === 'odata').map(s => (
                          <button key={s.filename} onClick={() => setSmartSrcSchema(s.filename)}
                            className={`text-left text-[10px] px-2 py-1 rounded transition-colors truncate ${smartSrcSchema === s.filename ? 'bg-blue-700 text-white font-semibold' : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}>
                            {s.stem}
                          </button>
                        ))}
                      </div>
                      <p className="text-[9px] font-semibold text-gray-500 uppercase tracking-wider mt-1">SAP IDoc Types</p>
                      <div className="grid grid-cols-1 gap-0.5 max-h-24 overflow-y-auto">
                        {catalogSchemas.filter(s => s.kind === 'idoc').map(s => (
                          <button key={s.filename} onClick={() => setSmartSrcSchema(s.filename)}
                            className={`text-left text-[10px] px-2 py-1 rounded transition-colors truncate ${smartSrcSchema === s.filename ? 'bg-blue-700 text-white font-semibold' : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}>
                            {s.stem}
                          </button>
                        ))}
                      </div>
                      {catalogSchemas.length === 0 && <p className="text-xs text-gray-600 text-center py-2">Loading schemas…</p>}
                      {smartSrcSchema && (
                        <div className="flex items-center gap-1 mt-1 pt-1 border-t border-gray-700/50 text-blue-400 text-[10px]">
                          <CheckCircle2 size={10} className="shrink-0" />
                          <span className="truncate font-medium">{smartSrcSchema}</span>
                          <button onClick={() => setSmartSrcSchema('')} className="ml-auto text-gray-600 hover:text-red-400 shrink-0"><X size={9} /></button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <>
                      <button type="button" onClick={() => smartSrcRef.current?.click()}
                        className={`w-full flex flex-col items-center justify-center gap-2 h-20 rounded-lg border-2 border-dashed transition-colors cursor-pointer
                          ${smartSrcFile ? 'border-blue-600/60 bg-blue-900/10' : 'border-gray-700 hover:border-gray-500 bg-gray-800/30'}`}>
                        {smartSrcFile
                          ? <><FileCode size={18} className="text-blue-400" /><span className="text-xs text-blue-300 font-medium truncate max-w-full px-2">{smartSrcFile.name}</span></>
                          : <><Upload size={16} className="text-gray-500" /><span className="text-xs text-gray-500">Click to upload .xsd</span></>
                        }
                      </button>
                      <input ref={smartSrcRef} type="file" accept=".xsd,.xml" className="hidden"
                        onChange={e => { const f = e.target.files?.[0]; if (f) { setSmartSrcFile(f); e.target.value = '' } }} />
                      {smartSrcFile && (
                        <button onClick={() => setSmartSrcFile(null)} className="text-xs text-gray-500 hover:text-red-400 flex items-center gap-1 mt-1">
                          <X size={10} />Remove
                        </button>
                      )}
                    </>
                  )}
                </div>

                {/* Description of target */}
                <div>
                  <label className="text-xs font-semibold text-gray-400 block mb-1">What should the target system receive?</label>
                  <textarea
                    className="textarea-field text-xs"
                    rows={4}
                    placeholder="e.g. A flat JSON-compatible XML for an external system that needs: order number, customer name, total amount in EUR, formatted date as YYYY-MM-DD, and item count."
                    value={smartDesc}
                    onChange={e => setSmartDesc(e.target.value)}
                  />
                </div>

                {/* Mapping name */}
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-400 whitespace-nowrap shrink-0">Mapping name:</label>
                  <input type="text" className="input-field text-xs py-1 px-2 flex-1"
                    placeholder="MM_SmartMapping" value={smartSrcName}
                    onChange={e => setSmartSrcName(e.target.value.replace(/\s+/g, '_'))} />
                </div>

                {IS_STATIC_HOST ? (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs bg-amber-900/40 border border-amber-700/50 text-amber-300">
                    <AlertCircle size={13} className="shrink-0" />
                    Backend not available on GitHub Pages
                  </div>
                ) : (
                  <button
                    onClick={generateFromSourceXsd}
                    disabled={smartSrcLoading || !smartSrcReady || !smartDesc.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50">
                    {smartSrcLoading ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                    {smartSrcLoading ? 'AI generating target XSD + mapping…' : 'Generate Mapping →'}
                  </button>
                )}
              </div>

              {/* Result panel for Mode 2 */}
              {smartSrcBlob && !smartSrcLoading && (
                <div className="rounded-xl border border-green-700/50 bg-green-900/10 p-4 space-y-3">
                  <div className="flex items-center gap-2 text-green-300">
                    <CheckCircle2 size={16} className="shrink-0" />
                    <span className="text-sm font-semibold">Mapping generated!</span>
                    {smartSrcCount > 0 && <span className="text-xs text-green-500 ml-1">· {smartSrcCount} fields mapped</span>}
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => downloadBlob(smartSrcBlob, smartSrcName || 'MM_SmartMapping')}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors">
                      <Download size={14} /> Download .mmap
                    </button>
                    <UploadToCpiButton
                      buildFile={async () => new File([smartSrcBlob], `${smartSrcName || 'MM_SmartMapping'}.zip`, { type: 'application/zip' })}
                      artifactType="messagemapping"
                      defaultName={smartSrcName || 'MM_SmartMapping'}
                    />
                  </div>
                </div>
              )}

              <p className="text-[10px] text-gray-600 leading-relaxed">
                AI creates a target XSD from your description, maps fields intelligently, then gives you download and CPI import options.
              </p>
            </div>

            {/* Mode 2: Have an idea only */}
            <div className="card border border-purple-700/40 bg-purple-950/10 space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-purple-800/60 flex items-center justify-center shrink-0">
                  <Lightbulb size={16} className="text-purple-300" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">I have an idea only</p>
                  <p className="text-xs text-gray-400">AI creates everything from scratch</p>
                </div>
              </div>

              <div className="space-y-3">
                {/* Idea textarea */}
                <div>
                  <label className="text-xs font-semibold text-gray-400 block mb-1">Describe your integration</label>
                  <textarea
                    className="textarea-field text-xs"
                    rows={7}
                    placeholder={
                      "e.g. Map a SAP S/4HANA Sales Order IDoc (SALESORD05) to a flat REST API payload for our logistics provider.\n\nThe target needs: order_id, customer_name, delivery_address, order_date in YYYY-MM-DD format, total_value in EUR, and a list of line items with material number, quantity and unit price."
                    }
                    value={smartIdea}
                    onChange={e => setSmartIdea(e.target.value)}
                  />
                </div>

                {/* Mapping name */}
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-400 whitespace-nowrap shrink-0">Mapping name:</label>
                  <input type="text" className="input-field text-xs py-1 px-2 flex-1"
                    placeholder="MM_IdeaMapping" value={smartIdeaName}
                    onChange={e => setSmartIdeaName(e.target.value.replace(/\s+/g, '_'))} />
                </div>

                {IS_STATIC_HOST ? (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs bg-amber-900/40 border border-amber-700/50 text-amber-300">
                    <AlertCircle size={13} className="shrink-0" />
                    Backend not available on GitHub Pages
                  </div>
                ) : (
                  <button
                    onClick={generateFromIdea}
                    disabled={smartIdeaLoading || !smartIdea.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold bg-purple-600 hover:bg-purple-500 text-white transition-colors disabled:opacity-50">
                    {smartIdeaLoading ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                    {smartIdeaLoading ? 'AI generating source XSD, target XSD + mapping…' : 'Generate Everything →'}
                  </button>
                )}
              </div>

              {/* Result panel for Mode 3 */}
              {smartIdeaBlob && !smartIdeaLoading && (
                <div className="rounded-xl border border-purple-700/50 bg-purple-900/10 p-4 space-y-3">
                  <div className="flex items-center gap-2 text-purple-300">
                    <CheckCircle2 size={16} className="shrink-0" />
                    <span className="text-sm font-semibold">Complete mapping generated!</span>
                    {smartIdeaCount > 0 && <span className="text-xs text-purple-400 ml-1">· {smartIdeaCount} fields mapped</span>}
                  </div>
                  <p className="text-xs text-gray-400">ZIP contains: source XSD, target XSD, and the .mmap mapping file — ready to import into CPI.</p>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => downloadBlob(smartIdeaBlob, smartIdeaName || 'MM_IdeaMapping')}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-purple-600 hover:bg-purple-500 text-white transition-colors">
                      <Download size={14} /> Download .mmap
                    </button>
                    <UploadToCpiButton
                      buildFile={async () => new File([smartIdeaBlob], `${smartIdeaName || 'MM_IdeaMapping'}.zip`, { type: 'application/zip' })}
                      artifactType="messagemapping"
                      defaultName={smartIdeaName || 'MM_IdeaMapping'}
                    />
                  </div>
                </div>
              )}

              <p className="text-[10px] text-gray-600 leading-relaxed">
                AI creates both XSD schemas and all field mappings from your description alone.
                Result includes Download and Upload to CPI options.
              </p>
            </div>
          </div>

          {/* Mode 1 reminder: Sheet Mapping */}
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-700 bg-gray-800/30">
            <FileSpreadsheet size={18} className="text-gray-400 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white">I have both XSDs and a mapping sheet</p>
              <p className="text-xs text-gray-400 mt-0.5">Use the Sheet Mapping tab for full control — upload XSDs + Excel sheet, preview, AI-derive rules, and generate.</p>
            </div>
            <button onClick={() => setTab('sheet')}
              className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-white transition-colors">
              Go to Sheet Mapping <ArrowRight size={12} />
            </button>
          </div>
        </div>
      )}

    </div>
  )
}
