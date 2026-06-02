import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Cloud, RefreshCw, CheckCircle, XCircle, Package, GitMerge, Activity,
  ChevronDown, ChevronRight, Rocket, Shield, Key, AlertTriangle, Loader2,
  CheckCheck, Upload, X, Archive, FolderOpen, Download, Trash2, Plus,
  StopCircle, Info, Copy, Settings, Database, FileText, Lock, Globe,
  Hash, Layers, Edit2, Check, Search, Zap, LogIn, Variable, Network,
  Map, Server, EyeOff, ExternalLink,
} from 'lucide-react'
import { cpiAPI } from '../api/client'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface PingResult    { connected: boolean; tenant?: string; reason?: string }
interface CpiPackage    { id: string; name: string; description: string; version: string; modified: string }
interface Artifact      { id: string; name: string; version: string; artifactType: string }
interface AllArtifacts  {
  iflows:            Artifact[]
  messageMappings:   Artifact[]
  valueMappings:     Artifact[]
  scriptCollections: Artifact[]
  functionLibraries: Artifact[]
}
interface ConfigParam   { key: string; value: string; dataType: string; description: string }
interface Message       { id: string; iflow: string; status: string; start: string; end: string; sender: string; receiver: string }
interface MsgRun        { status: string; start: string; stop: string; processingNode: string; stepId: string }
interface MsgAttach     { id: string; name: string; contentType: string; timeStamp: string }
interface AdapterAttr   { name: string; value: string; adapterName: string }
interface Credential    { name: string; kind: string; modified: string }
interface Keystore      { alias: string; type: string }
interface SecureParam   { name: string; description: string; modified: string }
interface OAuthCred     { name: string; clientId: string; tokenServiceUrl: string; modified: string }
interface CertMapping   { id: string; user: string; validUntil: string }
interface NumRange      { name: string; description: string; min: string; max: string; current: string; fieldLength: string; rotate: boolean }
interface LogFile       { name: string; application: string; lastModified: string; contentType: string }
interface DataStore     { name: string; type: string; visibility: string; messages: number; overdue: number }
interface DSEntry       { id: string; messageId: string; status: string; dueAt: string; retries: number }
interface MsgStoreEntry { id: string; messageId: string; status: string; due: string; retries: number }
interface Variable      { name: string; iflow: string; visibility: string; updatedAt: string }
interface TenantConfig  { key: string; value: string; dataType: string }
interface AccessPolicy  { id: string; roleName: string; description: string }
interface JmsBroker     { name: string; status: string; queueCount: number; maxCapacity: number; capacityOk: boolean }
interface IdMap         { id: string; sourceAgency: string; sourceScheme: string; sourceId: string; targetAgency: string; targetScheme: string; targetId: string }

type MsgStatus    = 'ALL' | 'COMPLETED' | 'FAILED' | 'PROCESSING' | 'RETRY' | 'CANCELLED'
type ActiveTab    = 'packages' | 'messages' | 'security' | 'datastores' | 'import'
type ImportStatus = 'pending' | 'uploading' | 'done' | 'error'
interface ImportFile { file: File; status: ImportStatus; message: string; id?: string }

// ─────────────────────────────────────────────────────────────────────────────
// Shared helpers
// ─────────────────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    COMPLETED: 'bg-green-900/60 text-green-300 border-green-700',
    STARTED:   'bg-green-900/60 text-green-300 border-green-700',
    FAILED:    'bg-red-900/60 text-red-300 border-red-700',
    ERROR:     'bg-red-900/60 text-red-300 border-red-700',
    PROCESSING:'bg-blue-900/60 text-blue-300 border-blue-700',
    STARTING:  'bg-blue-900/60 text-blue-300 border-blue-700',
    RETRY:     'bg-yellow-900/60 text-yellow-300 border-yellow-700',
    CANCELLED: 'bg-gray-800 text-gray-400 border-gray-600',
    STOPPED:   'bg-gray-800 text-gray-400 border-gray-600',
    OVERDUE:   'bg-orange-900/60 text-orange-300 border-orange-700',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${map[status] ?? 'bg-gray-800 text-gray-400 border-gray-600'}`}>
      {status}
    </span>
  )
}

function fmtDate(raw?: string | null): string {
  if (!raw) return '—'
  const ms = raw.match(/\/Date\((\d+)\)\//)
  const d  = ms ? new Date(+ms[1]) : new Date(raw)
  return isNaN(d.getTime()) ? raw : d.toLocaleString()
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  Object.assign(document.createElement('a'), { href: url, download: filename }).click()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

function SectionHeader({ icon: Icon, title, count, color = 'text-gray-400' }: { icon: any; title: string; count?: number; color?: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon size={15} className={color} />
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      {count !== undefined && <span className="text-xs text-gray-500">({count})</span>}
    </div>
  )
}

function EmptyState({ icon: Icon, title, sub }: { icon: any; title: string; sub?: string }) {
  return (
    <div className="text-center py-8 text-gray-500">
      <Icon size={32} className="mx-auto mb-2 opacity-30" />
      <p className="text-sm">{title}</p>
      {sub && <p className="text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Connection Settings Modal
// ─────────────────────────────────────────────────────────────────────────────

interface CpiSettings {
  authType: 'oauth' | 'basic'
  apiBaseUrl: string
  baseUrl: string
  clientId: string
  clientSecret: string
  tokenUrl: string
  user: string
  password: string
}

const MASKED = '••••••••'

function ConnectionSettingsModal({ onClose, onSaved }: { onClose: () => void; onSaved: (connected: boolean, tenant: string) => void }) {
  const [form, setForm]       = useState<CpiSettings>({ authType: 'oauth', apiBaseUrl: '', baseUrl: '', clientId: '', clientSecret: '', tokenUrl: '', user: '', password: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [testing, setTesting] = useState(false)
  const [result, setResult]   = useState<{ ok: boolean; msg: string } | null>(null)

  useEffect(() => {
    cpiAPI.getSettings().then(r => {
      setForm(r.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const set = (k: keyof CpiSettings, v: string) => setForm(f => ({ ...f, [k]: v }))

  const save = async () => {
    setSaving(true); setResult(null)
    try {
      const r = await cpiAPI.saveSettings(form)
      const ok = r.data.connected as boolean
      const msg = ok ? `Connected to ${r.data.tenant}` : (r.data.reason ?? 'Settings saved but connection failed')
      setResult({ ok, msg })
      onSaved(ok, r.data.tenant ?? '')
    } catch (e: any) {
      setResult({ ok: false, msg: e?.response?.data?.detail ?? 'Save failed' })
    } finally { setSaving(false) }
  }

  const test = async () => {
    setTesting(true); setResult(null)
    try {
      const r = await cpiAPI.ping()
      setResult({ ok: r.data.connected, msg: r.data.connected ? `Connected: ${r.data.tenant}` : (r.data.reason ?? 'Connection failed') })
    } catch { setResult({ ok: false, msg: 'Could not reach backend' }) }
    finally { setTesting(false) }
  }

  const isOAuth = form.authType === 'oauth'

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-lg space-y-5 shadow-2xl" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center">
              <Settings size={16} className="text-blue-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white text-sm">CPI Connection Settings</h3>
              <p className="text-xs text-gray-500">Changes take effect immediately — no restart needed</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white p-1"><X size={16} /></button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <Loader2 size={20} className="animate-spin mr-2" /> Loading current settings…
          </div>
        ) : (
          <div className="space-y-4">
            {/* Auth Type toggle */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">Authentication Type</label>
              <div className="flex gap-1 bg-gray-800 p-1 rounded-lg w-fit">
                {(['oauth', 'basic'] as const).map(t => (
                  <button key={t} onClick={() => set('authType', t)}
                    className={`px-4 py-1.5 rounded-md text-xs font-medium transition-colors ${form.authType === t ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                    {t === 'oauth' ? 'OAuth 2.0' : 'Basic Auth'}
                  </button>
                ))}
              </div>
            </div>

            {/* API Base URL — always visible */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                API Base URL <span className="text-red-400">*</span>
                <span className="text-gray-600 font-normal ml-1">e.g. https://…cfapps.eu10.hana.ondemand.com/api/v1</span>
              </label>
              <input className="input-field w-full text-sm font-mono" placeholder="https://<tenant>.it-cpi018.cfapps.eu10.hana.ondemand.com/api/v1"
                value={form.apiBaseUrl} onChange={e => set('apiBaseUrl', e.target.value)} />
            </div>

            {/* OAuth fields */}
            {isOAuth && (
              <div className="space-y-3 p-4 rounded-xl bg-gray-800/40 border border-gray-700/50">
                <p className="text-xs font-medium text-blue-400 flex items-center gap-1.5"><Globe size={12} /> OAuth 2.0 — Client Credentials</p>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Token Service URL <span className="text-red-400">*</span></label>
                  <input className="input-field w-full text-sm font-mono text-xs" placeholder="https://<subaccount>.authentication.eu10.hana.ondemand.com/oauth/token"
                    value={form.tokenUrl} onChange={e => set('tokenUrl', e.target.value)} />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Client ID <span className="text-red-400">*</span></label>
                    <input className="input-field w-full text-sm" placeholder="sb-..."
                      value={form.clientId} onChange={e => set('clientId', e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Client Secret <span className="text-red-400">*</span></label>
                    <input className="input-field w-full text-sm" type="password" placeholder={form.clientSecret === MASKED ? 'unchanged' : 'enter secret'}
                      value={form.clientSecret === MASKED ? '' : form.clientSecret}
                      onFocus={() => { if (form.clientSecret === MASKED) set('clientSecret', '') }}
                      onBlur={() => { if (form.clientSecret === '') set('clientSecret', MASKED) }}
                      onChange={e => set('clientSecret', e.target.value)} />
                  </div>
                </div>
              </div>
            )}

            {/* Basic Auth fields */}
            {!isOAuth && (
              <div className="space-y-3 p-4 rounded-xl bg-gray-800/40 border border-gray-700/50">
                <p className="text-xs font-medium text-yellow-400 flex items-center gap-1.5"><Key size={12} /> Basic Authentication</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Username <span className="text-red-400">*</span></label>
                    <input className="input-field w-full text-sm" placeholder="S-user or technical user"
                      value={form.user} onChange={e => set('user', e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Password <span className="text-red-400">*</span></label>
                    <input className="input-field w-full text-sm" type="password" placeholder={form.password === MASKED ? 'unchanged' : 'enter password'}
                      value={form.password === MASKED ? '' : form.password}
                      onFocus={() => { if (form.password === MASKED) set('password', '') }}
                      onBlur={() => { if (form.password === '') set('password', MASKED) }}
                      onChange={e => set('password', e.target.value)} />
                  </div>
                </div>
              </div>
            )}

            {/* Result feedback */}
            {result && (
              <div className={`flex items-start gap-2.5 px-4 py-3 rounded-lg text-sm border ${result.ok ? 'bg-green-900/20 border-green-800 text-green-300' : 'bg-red-900/20 border-red-800 text-red-300'}`}>
                {result.ok ? <CheckCircle size={16} className="shrink-0 mt-0.5" /> : <XCircle size={16} className="shrink-0 mt-0.5" />}
                <span className="text-xs leading-relaxed">{result.msg}</span>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 pt-1">
              <button onClick={save} disabled={saving || !form.apiBaseUrl}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg transition-colors font-medium">
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                Save &amp; Connect
              </button>
              <button onClick={test} disabled={testing}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 rounded-lg transition-colors">
                {testing ? <Loader2 size={14} className="animate-spin" /> : <Activity size={14} />}
                Test
              </button>
              <button onClick={onClose} className="ml-auto px-3 py-2 text-sm text-gray-500 hover:text-white transition-colors">Cancel</button>
            </div>

            <p className="text-xs text-gray-600 flex items-start gap-1.5 pt-0.5">
              <Info size={11} className="mt-0.5 shrink-0" />
              Settings are written to <code className="text-blue-400">backend/.env</code> and applied immediately. Secrets left blank remain unchanged.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Copy-iFlow modal
// ─────────────────────────────────────────────────────────────────────────────

function CopyModal({ sourceId, sourceName, packages, onClose, onCopied }:
  { sourceId: string; sourceName: string; packages: CpiPackage[]; onClose: () => void; onCopied: () => void }) {
  const [targetPkg, setTargetPkg] = useState(packages[0]?.id ?? '')
  const [newName, setNewName]     = useState(sourceName + '_copy')
  const [copying, setCopying]     = useState(false)
  const [err, setErr]             = useState('')

  const doCopy = async () => {
    setCopying(true); setErr('')
    try {
      await cpiAPI.copyIflow(sourceId, targetPkg, newName)
      onCopied()
      onClose()
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? 'Copy failed')
    } finally { setCopying(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white flex items-center gap-2"><Copy size={16} className="text-blue-400" /> Copy iFlow</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X size={16} /></button>
        </div>
        <p className="text-sm text-gray-400">Copying: <span className="text-white font-medium">{sourceName}</span></p>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Target Package</label>
            <select className="select-field w-full text-sm" value={targetPkg} onChange={e => setTargetPkg(e.target.value)}>
              {packages.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">New Name (becomes the artifact ID)</label>
            <input className="input-field w-full text-sm" value={newName} onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doCopy()} />
          </div>
        </div>
        {err && <p className="text-xs text-red-400">{err}</p>}
        <div className="flex gap-2 pt-1">
          <button onClick={doCopy} disabled={copying || !targetPkg}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg transition-colors">
            {copying ? <Loader2 size={14} className="animate-spin" /> : <Copy size={14} />} Copy
          </button>
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">Cancel</button>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Config params panel (externalized parameters)
// ─────────────────────────────────────────────────────────────────────────────

function ConfigPanel({ iflowId }: { iflowId: string }) {
  const [params, setParams]     = useState<ConfigParam[]>([])
  const [loading, setLoading]   = useState(true)
  const [edits, setEdits]       = useState<Record<string, string>>({})
  const [saving, setSaving]     = useState<Record<string, boolean>>({})
  const [saved, setSaved]       = useState<Record<string, boolean>>({})

  useEffect(() => {
    cpiAPI.configurations(iflowId).then(r => setParams(r.data)).catch(() => setParams([])).finally(() => setLoading(false))
  }, [iflowId])

  const save = async (key: string) => {
    setSaving(s => ({ ...s, [key]: true }))
    try {
      await cpiAPI.updateConfig(iflowId, key, edits[key])
      setParams(p => p.map(x => x.key === key ? { ...x, value: edits[key] } : x))
      setEdits(e => { const n = { ...e }; delete n[key]; return n })
      setSaved(s => ({ ...s, [key]: true }))
      setTimeout(() => setSaved(s => ({ ...s, [key]: false })), 2000)
    } catch { /* keep editing */ }
    finally { setSaving(s => ({ ...s, [key]: false })) }
  }

  if (loading) return <div className="flex items-center gap-2 text-xs text-gray-500 py-2"><Loader2 size={12} className="animate-spin" /> Loading parameters…</div>
  if (params.length === 0) return <p className="text-xs text-gray-500 py-1">No externalized parameters defined for this iFlow.</p>

  return (
    <div className="space-y-2 mt-1">
      {params.map(p => (
        <div key={p.key} className="flex items-start gap-3 bg-gray-800/60 rounded-lg px-3 py-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-blue-300">{p.key}</span>
              <span className="text-xs text-gray-600 bg-gray-800 px-1.5 rounded">{p.dataType}</span>
              {p.description && <span className="text-xs text-gray-500 truncate hidden md:inline">{p.description}</span>}
            </div>
              {p.key in edits ? (
              <input
                className="input-field w-full text-xs mt-1.5"
                value={edits[p.key]}
                onChange={e => setEdits(s => ({ ...s, [p.key]: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && save(p.key)}
              />
            ) : (
              <p className="text-xs text-gray-300 font-mono mt-0.5 truncate">{p.value || <span className="text-gray-600 italic">empty</span>}</p>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0 mt-1">
            {p.key in edits ? (
              <>
                <button onClick={() => save(p.key)} disabled={saving[p.key]}
                  className="text-green-400 hover:text-green-300 p-1">
                  {saving[p.key] ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                </button>
                <button onClick={() => setEdits(e => { const n = { ...e }; delete n[p.key]; return n })}
                  className="text-gray-500 hover:text-white p-1"><X size={13} /></button>
              </>
            ) : (
              <button onClick={() => setEdits(e => ({ ...e, [p.key]: p.value }))}
                className={`p-1 transition-colors ${saved[p.key] ? 'text-green-400' : 'text-gray-500 hover:text-blue-400'}`}>
                {saved[p.key] ? <Check size={13} /> : <Edit2 size={13} />}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Package Row
// ─────────────────────────────────────────────────────────────────────────────

interface PackageRowProps {
  pkg:              CpiPackage
  deployedIds:      Record<string, string>
  packages:         CpiPackage[]
  onDeleted:        (id: string) => void
  onRuntimeChange:  () => void
  onCopyRequest:    (id: string, name: string) => void
  searchQuery:      string
}

function PackageRow({ pkg, deployedIds, packages, onDeleted, onRuntimeChange, onCopyRequest, searchQuery }: PackageRowProps) {
  const [open, setOpen]         = useState(false)
  const [artifacts, setArtifacts] = useState<AllArtifacts | null>(null)
  const [loading, setLoading]   = useState(false)
  const [actionMsg, setActionMsg] = useState<Record<string, string>>({})
  const [actionErr, setActionErr] = useState<Record<string, boolean>>({})
  const [busy, setBusy]         = useState<string | null>(null)
  const [configOpen, setConfigOpen] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [editName, setEditName] = useState(pkg.name)
  const [editDesc, setEditDesc] = useState(pkg.description)
  const [saving, setSaving]     = useState(false)
  const [delPkg, setDelPkg]     = useState(false)
  const [bulkDeploying, setBulkDeploying] = useState(false)
  const [bulkMsg, setBulkMsg]   = useState('')

  const setMsg = (id: string, msg: string, isErr = false) => {
    setActionMsg(m => ({ ...m, [id]: msg }))
    setActionErr(m => ({ ...m, [id]: isErr }))
  }

  const loadArtifacts = async () => {
    if (open) { setOpen(false); return }
    setOpen(true)
    if (artifacts) return
    setLoading(true)
    try { const r = await cpiAPI.allArtifacts(pkg.id); setArtifacts(r.data) }
    catch { setArtifacts({ iflows: [], messageMappings: [], valueMappings: [], scriptCollections: [], functionLibraries: [] }) }
    finally { setLoading(false) }
  }

  const deploy = async (artifact: Artifact) => {
    setBusy(artifact.id); setMsg(artifact.id, '')
    try {
      await cpiAPI.deploy(pkg.id, artifact.id)
      setMsg(artifact.id, 'Deploying…')
      const start = Date.now()
      const poll = async (): Promise<void> => {
        if (Date.now() - start > 90_000) { setMsg(artifact.id, 'Timed out — check SAP UI'); onRuntimeChange(); return }
        try {
          const { data } = await cpiAPI.runtimeIflowStatus(artifact.id)
          if (data.status === 'STARTED')   { setMsg(artifact.id, '✓ Deployed'); onRuntimeChange() }
          else if (data.status === 'ERROR') { setMsg(artifact.id, `Deploy failed: ${data.error ?? 'Unknown error'}`, true); onRuntimeChange() }
          else setTimeout(poll, 4000)
        } catch { setTimeout(poll, 4000) }
      }
      setTimeout(poll, 5000)
    } catch (e: any) { setMsg(artifact.id, e?.response?.data?.detail ?? 'Deploy failed', true) }
    finally { setBusy(null) }
  }

  const undeploy = async (artifact: Artifact) => {
    setBusy(artifact.id + '_un'); setMsg(artifact.id, '')
    try { await cpiAPI.undeploy(artifact.id); setMsg(artifact.id, 'Undeployed'); onRuntimeChange() }
    catch (e: any) { setMsg(artifact.id, e?.response?.data?.detail ?? 'Undeploy failed', true) }
    finally { setBusy(null) }
  }

  const exportZip = async (artifact: Artifact) => {
    setBusy(artifact.id + '_exp')
    try { const r = await cpiAPI.exportIflow(pkg.id, artifact.id); triggerDownload(r.data, `${artifact.id}.zip`) }
    catch (e: any) { setMsg(artifact.id, e?.response?.data?.detail ?? 'Export failed', true) }
    finally { setBusy(null) }
  }

  const deleteArtifact = async (artifact: Artifact) => {
    if (!confirm(`Delete "${artifact.name}" from design-time? This cannot be undone.`)) return
    setBusy(artifact.id + '_del')
    try {
      await cpiAPI.deleteIflow(pkg.id, artifact.id)
      setArtifacts(a => a ? {
        ...a,
        iflows:            a.iflows.filter(x => x.id !== artifact.id),
        messageMappings:   a.messageMappings.filter(x => x.id !== artifact.id),
        valueMappings:     a.valueMappings.filter(x => x.id !== artifact.id),
        scriptCollections: a.scriptCollections.filter(x => x.id !== artifact.id),
        functionLibraries: a.functionLibraries.filter(x => x.id !== artifact.id),
      } : a)
    } catch (e: any) { setMsg(artifact.id, e?.response?.data?.detail ?? 'Delete failed', true) }
    finally { setBusy(null) }
  }

  const deletePackage = async () => {
    if (!confirm(`Delete package "${pkg.name}"? It must be empty.`)) return
    setDelPkg(true)
    try { await cpiAPI.deletePackage(pkg.id); onDeleted(pkg.id) }
    catch (e: any) { alert(e?.response?.data?.detail ?? 'Delete failed'); setDelPkg(false) }
  }

  const savePackageEdit = async () => {
    if (!editName.trim()) return
    setSaving(true)
    try { await cpiAPI.updatePackage(pkg.id, editName.trim(), editDesc.trim()); setEditMode(false) }
    catch (e: any) { alert(e?.response?.data?.detail ?? 'Update failed') }
    finally { setSaving(false) }
  }

  const bulkDeploy = async () => {
    if (!confirm(`Deploy all iFlows in "${pkg.name}"?`)) return
    setBulkDeploying(true); setBulkMsg('Deploying…')
    try {
      const r = await cpiAPI.deployAll(pkg.id)
      setBulkMsg(`Triggered ${r.data.deployed.length}/${r.data.total} · ${r.data.errors.length} error(s)`)
      setTimeout(onRuntimeChange, 5000)
    } catch (e: any) { setBulkMsg(e?.response?.data?.detail ?? 'Bulk deploy failed') }
    finally { setBulkDeploying(false) }
  }

  // Filter artifacts by search query
  const filterArtifacts = (list: Artifact[]) =>
    searchQuery ? list.filter(a => a.name.toLowerCase().includes(searchQuery.toLowerCase()) || a.id.toLowerCase().includes(searchQuery.toLowerCase())) : list

  const allIflows   = filterArtifacts(artifacts?.iflows            ?? [])
  const allMMs      = filterArtifacts(artifacts?.messageMappings   ?? [])
  const allVMs      = filterArtifacts(artifacts?.valueMappings     ?? [])
  const allScripts  = filterArtifacts(artifacts?.scriptCollections ?? [])
  const allFnLibs   = filterArtifacts(artifacts?.functionLibraries ?? [])
  const totalArtifacts = allIflows.length + allMMs.length + allVMs.length + allScripts.length + allFnLibs.length

  const renderArtifactRow = (artifact: Artifact, icon: any, iconClass: string, showDeploy: boolean) => {
    const isDeployed  = !!deployedIds[artifact.id]
    const runtimeStat = deployedIds[artifact.id]
    const isBusy      = busy === artifact.id
    const isExporting = busy === artifact.id + '_exp'
    const isDeleting  = busy === artifact.id + '_del'
    const isUndeploying = busy === artifact.id + '_un'
    const ArtifactIcon = icon

    return (
      <div key={artifact.id}>
        <div className="flex items-center gap-2 px-5 py-2 border-b border-gray-800/50 last:border-0">
          <ArtifactIcon size={13} className={`${iconClass} shrink-0`} />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-200 truncate">{artifact.name}</p>
            <p className="text-xs text-gray-500">{artifact.id} · v{artifact.version}</p>
          </div>

          {/* Runtime badge */}
          {showDeploy && (isDeployed
            ? <StatusBadge status={runtimeStat} />
            : <span className="text-xs text-gray-600 bg-gray-800/60 px-2 py-0.5 rounded border border-gray-700 hidden sm:inline">not deployed</span>
          )}

          {/* Config params toggle (iFlows only) */}
          {artifact.artifactType === 'iflow' && (
            <button
              onClick={() => setConfigOpen(c => c === artifact.id ? null : artifact.id)}
              title="Externalized Parameters"
              className={`p-1 transition-colors ${configOpen === artifact.id ? 'text-yellow-400' : 'text-gray-500 hover:text-yellow-400'}`}
            >
              <Settings size={13} />
            </button>
          )}

          {/* Deploy / Undeploy */}
          {showDeploy && (isDeployed ? (
            <button onClick={() => undeploy(artifact)} disabled={isUndeploying}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-700 hover:bg-red-700/60 disabled:opacity-50 text-gray-300 hover:text-white rounded transition-colors">
              {isUndeploying ? <Loader2 size={11} className="animate-spin" /> : <StopCircle size={11} />}
              <span className="hidden sm:inline">Undeploy</span>
            </button>
          ) : (
            <button onClick={() => deploy(artifact)} disabled={isBusy}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded transition-colors">
              {isBusy ? <Loader2 size={11} className="animate-spin" /> : <Rocket size={11} />}
              <span className="hidden sm:inline">Deploy</span>
            </button>
          ))}

          {/* Copy (iFlows only) */}
          {artifact.artifactType === 'iflow' && (
            <button onClick={() => onCopyRequest(artifact.id, artifact.name)} title="Copy to another package"
              className="text-gray-500 hover:text-purple-400 transition-colors p-1"><Copy size={13} /></button>
          )}

          {/* Export ZIP */}
          <button onClick={() => exportZip(artifact)} disabled={isExporting} title="Download ZIP"
            className="text-gray-500 hover:text-blue-400 transition-colors p-1 disabled:opacity-40">
            {isExporting ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
          </button>

          {/* Delete */}
          <button onClick={() => deleteArtifact(artifact)} disabled={isDeleting} title="Delete"
            className="text-gray-600 hover:text-red-400 transition-colors p-1 disabled:opacity-40">
            {isDeleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
          </button>
        </div>

        {/* Status message */}
        {actionMsg[artifact.id] && (
          <p className={`text-xs px-5 pb-1.5 ${actionErr[artifact.id] ? 'text-red-400' : 'text-yellow-300'}`}>
            {actionMsg[artifact.id]}
          </p>
        )}

        {/* Config params panel */}
        {configOpen === artifact.id && (
          <div className="px-5 pb-3 bg-gray-900/60">
            <p className="text-xs font-medium text-yellow-400 mb-2 flex items-center gap-1"><Settings size={11} /> Externalized Parameters</p>
            <ConfigPanel iflowId={artifact.id} />
          </div>
        )}
      </div>
    )
  }

  // Filter package header by search
  const pkgMatchesSearch = !searchQuery || pkg.name.toLowerCase().includes(searchQuery.toLowerCase()) || pkg.id.toLowerCase().includes(searchQuery.toLowerCase())
  if (!pkgMatchesSearch && searchQuery && !open) return null

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      {/* Package header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-gray-800/60 hover:bg-gray-800 transition-colors">
        <button onClick={loadArtifacts} className="flex items-center gap-2 flex-1 text-left min-w-0">
          {open ? <ChevronDown size={15} className="text-gray-400 shrink-0" /> : <ChevronRight size={15} className="text-gray-400 shrink-0" />}
          <Package size={15} className="text-blue-400 shrink-0" />
          {editMode ? (
            <div className="flex items-center gap-2 flex-1" onClick={e => e.stopPropagation()}>
              <input className="input-field text-sm flex-1 py-0.5" value={editName} onChange={e => setEditName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && savePackageEdit()} autoFocus />
              <input className="input-field text-sm flex-1 py-0.5" value={editDesc} onChange={e => setEditDesc(e.target.value)}
                placeholder="Description" onKeyDown={e => e.key === 'Enter' && savePackageEdit()} />
            </div>
          ) : (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{pkg.name}</p>
              <p className="text-xs text-gray-500 truncate">{pkg.id} · v{pkg.version}</p>
            </div>
          )}
        </button>

        {/* Bulk deploy */}
        {!editMode && (
          <button onClick={e => { e.stopPropagation(); bulkDeploy() }} disabled={bulkDeploying}
            title="Deploy all iFlows in this package"
            className="flex items-center gap-1 px-2 py-1 text-xs bg-purple-700/70 hover:bg-purple-600 disabled:opacity-50 text-white rounded transition-colors shrink-0">
            {bulkDeploying ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
            <span className="hidden md:inline">Deploy All</span>
          </button>
        )}

        {/* Edit save/cancel */}
        {editMode ? (
          <div className="flex gap-1 shrink-0" onClick={e => e.stopPropagation()}>
            <button onClick={savePackageEdit} disabled={saving}
              className="text-green-400 hover:text-green-300 p-1">{saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}</button>
            <button onClick={() => { setEditMode(false); setEditName(pkg.name); setEditDesc(pkg.description) }}
              className="text-gray-500 hover:text-white p-1"><X size={14} /></button>
          </div>
        ) : (
          <button onClick={e => { e.stopPropagation(); setEditMode(true) }} title="Edit package"
            className="text-gray-500 hover:text-blue-400 transition-colors p-1 shrink-0"><Edit2 size={13} /></button>
        )}

        <button onClick={e => { e.stopPropagation(); deletePackage() }} disabled={delPkg} title="Delete package"
          className="text-gray-600 hover:text-red-400 transition-colors p-1 shrink-0 disabled:opacity-40">
          {delPkg ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
        </button>
      </div>

      {/* Bulk deploy message */}
      {bulkMsg && <p className="text-xs text-yellow-300 px-4 py-1 bg-gray-900/60">{bulkMsg}</p>}

      {/* Expanded content */}
      {open && (
        <div className="bg-gray-900/50 border-t border-gray-700">
          {loading ? (
            <div className="flex items-center gap-2 px-5 py-3 text-sm text-gray-400">
              <Loader2 size={14} className="animate-spin" /> Loading artifacts…
            </div>
          ) : (
            <>
              {/* Integration Flows */}
              {allIflows.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider px-5 pt-3 pb-1">
                    🔗 Integration Flows ({allIflows.length})
                  </p>
                  {allIflows.map(a => renderArtifactRow(a, GitMerge, 'text-purple-400', true))}
                </div>
              )}

              {/* Message Mappings */}
              {allMMs.length > 0 && (
                <div className={allIflows.length > 0 ? 'border-t border-gray-800/60' : ''}>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider px-5 pt-3 pb-1">
                    🗺️ Message Mappings ({allMMs.length})
                  </p>
                  {allMMs.map(a => renderArtifactRow(a, Layers, 'text-blue-400', false))}
                </div>
              )}

              {/* Value Mappings */}
              {allVMs.length > 0 && (
                <div className={(allIflows.length + allMMs.length) > 0 ? 'border-t border-gray-800/60' : ''}>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider px-5 pt-3 pb-1">
                    📋 Value Mappings ({allVMs.length})
                  </p>
                  {allVMs.map(a => renderArtifactRow(a, Layers, 'text-green-400', false))}
                </div>
              )}

              {/* Script Collections */}
              {allScripts.length > 0 && (
                <div className={(allIflows.length + allMMs.length + allVMs.length) > 0 ? 'border-t border-gray-800/60' : ''}>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider px-5 pt-3 pb-1">
                    📜 Script Collections ({allScripts.length})
                  </p>
                  {allScripts.map(a => renderArtifactRow(a, FileText, 'text-yellow-400', false))}
                </div>
              )}

              {/* Function Libraries */}
              {allFnLibs.length > 0 && (
                <div className={(allIflows.length + allMMs.length + allVMs.length + allScripts.length) > 0 ? 'border-t border-gray-800/60' : ''}>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider px-5 pt-3 pb-1">
                    ⚡ Function Libraries ({allFnLibs.length})
                  </p>
                  {allFnLibs.map(a => renderArtifactRow(a, FileText, 'text-orange-400', false))}
                </div>
              )}

              {totalArtifacts === 0 && (
                <EmptyState icon={Package} title="No artifacts found" sub={searchQuery ? 'No matches for your search' : 'This package is empty'} />
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Message Row (expandable error + runs + attachments)
// ─────────────────────────────────────────────────────────────────────────────

function MessageRow({ msg }: { msg: Message }) {
  const [expanded, setExpanded]     = useState(false)
  const [errText, setErrText]       = useState<string | null>(null)
  const [runs, setRuns]             = useState<MsgRun[] | null>(null)
  const [attachments, setAttachments] = useState<MsgAttach[] | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [adapterAttrs, setAdapterAttrs] = useState<AdapterAttr[] | null>(null)

  const loadDetails = async () => {
    if (expanded) { setExpanded(false); return }
    setExpanded(true)
    if (errText !== null || runs !== null) return
    setLoadingDetail(true)
    try {
      const calls: Promise<any>[] = [
        cpiAPI.messageRuns(msg.id),
        cpiAPI.messageAttachments(msg.id),
        cpiAPI.messageAdapterAttributes(msg.id),
      ]
      if (msg.status === 'FAILED') calls.push(cpiAPI.messageError(msg.id))
      const [runsRes, attachRes, attrRes, errRes] = await Promise.all(calls)
      setRuns(runsRes.data)
      setAttachments(attachRes.data)
      setAdapterAttrs(attrRes.data)
      if (errRes) setErrText(errRes.data.text || 'No error details available.')
    } catch { setErrText('Could not load details.') }
    finally { setLoadingDetail(false) }
  }

  return (
    <>
      <tr className="hover:bg-gray-800/40 transition-colors cursor-pointer" onClick={loadDetails}>
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5">
            <StatusBadge status={msg.status} />
            {expanded ? <ChevronDown size={11} className="text-gray-500" /> : <ChevronRight size={11} className="text-gray-500" />}
          </div>
        </td>
        <td className="px-4 py-3 text-gray-200 font-medium max-w-xs truncate">{msg.iflow ?? '—'}</td>
        <td className="px-4 py-3 text-gray-400 text-xs hidden md:table-cell whitespace-nowrap">{fmtDate(msg.start)}</td>
        <td className="px-4 py-3 text-gray-400 text-xs hidden lg:table-cell">{msg.sender ?? '—'}</td>
        <td className="px-4 py-3 text-gray-400 text-xs hidden lg:table-cell">{msg.receiver ?? '—'}</td>
      </tr>
      {expanded && (
        <tr className="bg-gray-900/60">
          <td colSpan={5} className="px-4 pb-4 pt-1">
            {loadingDetail ? (
              <div className="flex items-center gap-2 text-xs text-gray-500"><Loader2 size={12} className="animate-spin" /> Loading…</div>
            ) : (
              <div className="space-y-3">
                {errText && (
                  <div>
                    <p className="text-xs font-medium text-red-400 mb-1">Error Details</p>
                    <pre className="text-xs text-red-300 whitespace-pre-wrap font-mono bg-red-950/30 rounded p-3 max-h-32 overflow-y-auto">{errText}</pre>
                  </div>
                )}
                {runs && runs.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-400 mb-1">Processing Runs ({runs.length})</p>
                    <div className="space-y-1">
                      {runs.map((r, i) => (
                        <div key={i} className="flex items-center gap-3 text-xs text-gray-400 bg-gray-800/40 rounded px-3 py-1.5">
                          <StatusBadge status={r.status} />
                          <span className="font-mono text-gray-500">{r.stepId ?? '—'}</span>
                          <span>{r.processingNode ?? '—'}</span>
                          <span className="ml-auto">{fmtDate(r.start)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {attachments && attachments.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-400 mb-1">Attachments ({attachments.length})</p>
                    <div className="space-y-1">
                      {attachments.map(a => (
                        <div key={a.id} className="flex items-center gap-3 text-xs bg-gray-800/40 rounded px-3 py-1.5">
                          <FileText size={12} className="text-gray-500 shrink-0" />
                          <span className="text-gray-300">{a.name}</span>
                          <span className="text-gray-500">{a.contentType}</span>
                          <span className="ml-auto text-gray-500">{fmtDate(a.timeStamp)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {adapterAttrs && adapterAttrs.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-400 mb-1">Adapter Attributes ({adapterAttrs.length})</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                      {adapterAttrs.map((a, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs bg-gray-800/40 rounded px-3 py-1.5">
                          <span className="text-gray-500 shrink-0 w-28 truncate" title={a.adapterName}>{a.adapterName || '—'}</span>
                          <span className="text-blue-300 font-mono shrink-0">{a.name}</span>
                          <span className="text-gray-300 truncate ml-auto">{a.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {runs?.length === 0 && attachments?.length === 0 && !errText && !adapterAttrs?.length && (
                  <p className="text-xs text-gray-500">No additional details available.</p>
                )}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Data Stores Tab
// ─────────────────────────────────────────────────────────────────────────────

function DataStoresTab() {
  const [stores, setStores]         = useState<DataStore[]>([])
  const [loading, setLoading]       = useState(true)
  const [expanded, setExpanded]     = useState<string | null>(null)
  const [entries, setEntries]       = useState<Record<string, DSEntry[]>>({})
  const [loadingEntries, setLoadingEntries] = useState<string | null>(null)
  const [deleting, setDeleting]     = useState<string | null>(null)
  const [msgEntries, setMsgEntries] = useState<MsgStoreEntry[]>([])
  const [msgLoading, setMsgLoading] = useState(true)

  // Variables
  const [variables, setVariables]   = useState<Variable[]>([])
  const [varLoading, setVarLoading] = useState(true)
  const [deletingVar, setDeletingVar] = useState<string | null>(null)

  // Tenant Configurations
  const [tenantCfg, setTenantCfg]   = useState<TenantConfig[]>([])
  const [cfgLoading, setCfgLoading] = useState(true)
  const [cfgEdits, setCfgEdits]     = useState<Record<string, string>>({})
  const [cfgSaving, setCfgSaving]   = useState<Record<string, boolean>>({})

  // JMS Brokers
  const [jmsBrokers, setJmsBrokers] = useState<JmsBroker[]>([])

  // ID Mapper
  const [idMaps, setIdMaps]         = useState<IdMap[]>([])
  const [idLoading, setIdLoading]   = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      cpiAPI.datastores().then(r => setStores(r.data)).catch(() => setStores([])),
      cpiAPI.messageStoreEntries().then(r => setMsgEntries(r.data)).catch(() => setMsgEntries([])),
      cpiAPI.variables().then(r => setVariables(r.data)).catch(() => setVariables([])).finally(() => setVarLoading(false)),
      cpiAPI.tenantConfigurations().then(r => setTenantCfg(r.data)).catch(() => setTenantCfg([])).finally(() => setCfgLoading(false)),
      cpiAPI.jmsBrokers().then(r => setJmsBrokers(r.data)).catch(() => setJmsBrokers([])),
      cpiAPI.idMaps().then(r => setIdMaps(r.data)).catch(() => setIdMaps([])).finally(() => setIdLoading(false)),
    ]).finally(() => { setLoading(false); setMsgLoading(false) })
  }, [])

  const saveTenantConfig = async (key: string) => {
    setCfgSaving(s => ({ ...s, [key]: true }))
    try {
      await cpiAPI.updateTenantConfig(key, cfgEdits[key])
      setTenantCfg(p => p.map(c => c.key === key ? { ...c, value: cfgEdits[key] } : c))
      setCfgEdits(e => { const n = { ...e }; delete n[key]; return n })
    } catch { /* keep editing */ }
    finally { setCfgSaving(s => ({ ...s, [key]: false })) }
  }

  const deleteVar = async (v: Variable) => {
    if (!confirm(`Delete variable "${v.name}" for iFlow "${v.iflow}"?`)) return
    setDeletingVar(v.name + v.iflow)
    try {
      await cpiAPI.deleteVariable(v.iflow, v.name)
      setVariables(p => p.filter(x => !(x.name === v.name && x.iflow === v.iflow)))
    } catch (e: any) { alert(e?.response?.data?.detail ?? 'Delete failed') }
    finally { setDeletingVar(null) }
  }

  const deleteIdEntry = async (id: string) => {
    if (!confirm('Delete this ID mapping?')) return
    setDeletingId(id)
    try {
      await cpiAPI.deleteIdMap(id)
      setIdMaps(p => p.filter(x => x.id !== id))
    } catch (e: any) { alert(e?.response?.data?.detail ?? 'Delete failed') }
    finally { setDeletingId(null) }
  }

  const toggleStore = async (name: string) => {
    if (expanded === name) { setExpanded(null); return }
    setExpanded(name)
    if (entries[name]) return
    setLoadingEntries(name)
    try { const r = await cpiAPI.datastoreEntries(name); setEntries(e => ({ ...e, [name]: r.data })) }
    catch { setEntries(e => ({ ...e, [name]: [] })) }
    finally { setLoadingEntries(null) }
  }

  const deleteEntry = async (storeName: string, entryId: string) => {
    if (!confirm('Delete this data store entry?')) return
    setDeleting(entryId)
    try {
      await cpiAPI.deleteDatastoreEntry(storeName, entryId)
      setEntries(e => ({ ...e, [storeName]: (e[storeName] ?? []).filter(x => x.id !== entryId) }))
    } catch (e: any) { alert(e?.response?.data?.detail ?? 'Delete failed') }
    finally { setDeleting(null) }
  }

  if (loading) return <div className="flex items-center justify-center py-16 text-gray-500"><Loader2 size={24} className="animate-spin mr-3" /> Loading data stores…</div>

  return (
    <div className="space-y-6">
      {/* Data Stores */}
      <div>
        <SectionHeader icon={Database} title="Data Stores" count={stores.length} color="text-cyan-400" />
        {stores.length === 0 ? <EmptyState icon={Database} title="No data stores found" sub="Data stores appear when iFlows use the Data Store Write step." /> : (
          <div className="space-y-2">
            {stores.map(ds => (
              <div key={ds.name} className="border border-gray-700 rounded-lg overflow-hidden">
                <button onClick={() => toggleStore(ds.name)}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-gray-800/60 hover:bg-gray-800 transition-colors text-left">
                  {expanded === ds.name ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
                  <Database size={14} className="text-cyan-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white">{ds.name}</p>
                    <p className="text-xs text-gray-500">{ds.type} · {ds.visibility}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-gray-400">{ds.messages} msg</span>
                    {ds.overdue > 0 && <StatusBadge status="OVERDUE" />}
                  </div>
                </button>
                {expanded === ds.name && (
                  <div className="bg-gray-900/50 border-t border-gray-700">
                    {loadingEntries === ds.name ? (
                      <div className="flex items-center gap-2 px-5 py-3 text-xs text-gray-400"><Loader2 size={12} className="animate-spin" /> Loading entries…</div>
                    ) : (entries[ds.name] ?? []).length === 0 ? (
                      <p className="px-5 py-3 text-xs text-gray-500">No entries found.</p>
                    ) : (
                      <table className="w-full text-xs">
                        <thead><tr className="bg-gray-800/60 text-gray-500 uppercase tracking-wide text-left">
                          <th className="px-4 py-2">ID</th><th className="px-4 py-2">Status</th>
                          <th className="px-4 py-2 hidden md:table-cell">Due</th><th className="px-4 py-2">Retries</th><th className="px-4 py-2"></th>
                        </tr></thead>
                        <tbody className="divide-y divide-gray-800">
                          {(entries[ds.name] ?? []).map(e => (
                            <tr key={e.id} className="hover:bg-gray-800/30">
                              <td className="px-4 py-2 text-gray-300 font-mono truncate max-w-[120px]">{e.id}</td>
                              <td className="px-4 py-2"><StatusBadge status={e.status} /></td>
                              <td className="px-4 py-2 text-gray-400 hidden md:table-cell">{fmtDate(e.dueAt)}</td>
                              <td className="px-4 py-2 text-gray-400">{e.retries}</td>
                              <td className="px-4 py-2 flex items-center gap-1">
                                <button onClick={async () => {
                                  try { const r = await cpiAPI.datastoreEntryPayload(ds.name, e.id); triggerDownload(r.data, `entry_${e.id}.xml`) }
                                  catch { alert('Payload download failed') }
                                }} title="Download payload" className="text-gray-600 hover:text-blue-400 transition-colors p-1">
                                  <Download size={12} />
                                </button>
                                <button onClick={() => deleteEntry(ds.name, e.id)} disabled={deleting === e.id}
                                  className="text-gray-600 hover:text-red-400 transition-colors p-1">
                                  {deleting === e.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Message Store Entries */}
      <div>
        <SectionHeader icon={Archive} title="Message Store Entries" count={msgEntries.length} color="text-indigo-400" />
        {msgLoading ? <div className="flex items-center gap-2 text-xs text-gray-500"><Loader2 size={12} className="animate-spin" /> Loading…</div>
          : msgEntries.length === 0 ? <EmptyState icon={Archive} title="No message store entries" />
          : (
            <div className="overflow-hidden rounded-xl border border-gray-700">
              <table className="w-full text-sm">
                <thead><tr className="bg-gray-800/80 text-left text-xs text-gray-400 uppercase tracking-wide">
                  <th className="px-4 py-3">ID</th><th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 hidden md:table-cell">Due</th><th className="px-4 py-3">Retries</th><th className="px-4 py-3"></th>
                </tr></thead>
                <tbody className="divide-y divide-gray-800">
                  {msgEntries.map(e => (
                    <tr key={e.id} className="hover:bg-gray-800/40">
                      <td className="px-4 py-3 text-gray-300 font-mono text-xs truncate max-w-[180px]">{e.messageId ?? e.id}</td>
                      <td className="px-4 py-3"><StatusBadge status={e.status ?? 'UNKNOWN'} /></td>
                      <td className="px-4 py-3 text-gray-400 text-xs hidden md:table-cell">{fmtDate(e.due)}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{e.retries ?? '—'}</td>
                      <td className="px-4 py-3">
                        <button onClick={async () => {
                          try { const r = await cpiAPI.messageStoreEntryPayload(e.id); triggerDownload(r.data, `msg_${e.id}.xml`) }
                          catch { alert('Payload download failed') }
                        }} title="Download payload" className="text-gray-600 hover:text-blue-400 transition-colors p-1">
                          <Download size={12} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>

      {/* Variables (runtime iFlow string parameters) */}
      <div>
        <SectionHeader icon={Variable} title="Runtime Variables" count={variables.length} color="text-yellow-300" />
        {varLoading ? <div className="flex items-center gap-2 text-xs text-gray-500"><Loader2 size={12} className="animate-spin" /> Loading…</div>
          : variables.length === 0 ? <EmptyState icon={Variable} title="No runtime variables" sub="Variables are set by iFlows using the Write Variable step." />
          : (
            <div className="overflow-hidden rounded-xl border border-gray-700">
              <table className="w-full text-sm">
                <thead><tr className="bg-gray-800/80 text-left text-xs text-gray-400 uppercase tracking-wide">
                  <th className="px-4 py-3">Name</th><th className="px-4 py-3">iFlow</th>
                  <th className="px-4 py-3 hidden md:table-cell">Visibility</th>
                  <th className="px-4 py-3 hidden lg:table-cell">Updated</th><th className="px-4 py-3"></th>
                </tr></thead>
                <tbody className="divide-y divide-gray-800">
                  {variables.map(v => (
                    <tr key={v.name + v.iflow} className="hover:bg-gray-800/40">
                      <td className="px-4 py-3 text-yellow-300 font-mono text-xs">{v.name}</td>
                      <td className="px-4 py-3 text-gray-300 text-xs">{v.iflow}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs hidden md:table-cell">{v.visibility}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs hidden lg:table-cell">{fmtDate(v.updatedAt)}</td>
                      <td className="px-4 py-3">
                        <button onClick={() => deleteVar(v)} disabled={deletingVar === v.name + v.iflow}
                          className="text-gray-600 hover:text-red-400 transition-colors p-1">
                          {deletingVar === v.name + v.iflow ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>

      {/* Tenant Configurations (global string parameters) */}
      <div>
        <SectionHeader icon={Settings} title="Tenant Configurations" count={tenantCfg.length} color="text-teal-400" />
        <p className="text-xs text-gray-500 mb-2">Global tenant-level configuration parameters (non-sensitive). Editable inline.</p>
        {cfgLoading ? <div className="flex items-center gap-2 text-xs text-gray-500"><Loader2 size={12} className="animate-spin" /> Loading…</div>
          : tenantCfg.length === 0 ? <EmptyState icon={Settings} title="No tenant configurations found" sub="Tenant configurations appear based on your Integration Suite plan." />
          : (
            <div className="space-y-1">
              {tenantCfg.map(c => (
                <div key={c.key} className="flex items-center gap-3 px-4 py-2.5 bg-gray-800/40 rounded-lg border border-gray-700/50">
                  <span className="text-xs font-mono text-teal-300 w-48 shrink-0 truncate">{c.key}</span>
                  <span className="text-xs text-gray-600 bg-gray-800 px-1.5 rounded shrink-0">{c.dataType}</span>
                  {c.key in cfgEdits ? (
                    <input className="input-field flex-1 text-xs py-1" value={cfgEdits[c.key]}
                      onChange={e => setCfgEdits(s => ({ ...s, [c.key]: e.target.value }))}
                      onKeyDown={e => e.key === 'Enter' && saveTenantConfig(c.key)} />
                  ) : (
                    <span className="text-xs text-gray-300 font-mono flex-1 truncate">{c.value || <span className="text-gray-600 italic">empty</span>}</span>
                  )}
                  {c.key in cfgEdits ? (
                    <div className="flex gap-1 shrink-0">
                      <button onClick={() => saveTenantConfig(c.key)} disabled={cfgSaving[c.key]} className="text-green-400 hover:text-green-300 p-1">
                        {cfgSaving[c.key] ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                      </button>
                      <button onClick={() => setCfgEdits(e => { const n = { ...e }; delete n[c.key]; return n })} className="text-gray-500 hover:text-white p-1"><X size={12} /></button>
                    </div>
                  ) : (
                    <button onClick={() => setCfgEdits(e => ({ ...e, [c.key]: c.value }))} className="text-gray-500 hover:text-teal-400 p-1 shrink-0">
                      <Edit2 size={12} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
      </div>

      {/* JMS Brokers */}
      {jmsBrokers.length > 0 && (
        <div>
          <SectionHeader icon={Server} title="JMS Brokers" count={jmsBrokers.length} color="text-orange-400" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {jmsBrokers.map(b => (
              <div key={b.name} className="px-4 py-3 bg-gray-800/40 rounded-lg border border-gray-700/50">
                <div className="flex items-center gap-2 mb-1">
                  <Server size={13} className="text-orange-400" />
                  <p className="text-sm font-medium text-white">{b.name}</p>
                  <StatusBadge status={b.status ?? 'UNKNOWN'} />
                </div>
                <div className="flex gap-4 text-xs text-gray-500 pl-5">
                  <span>Queues: <span className="text-white">{b.queueCount ?? '—'}</span></span>
                  <span>Max: <span className="text-white">{b.maxCapacity ?? '—'}</span></span>
                  {b.capacityOk === false && <span className="text-red-400">Capacity exceeded</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ID Mapper */}
      <div>
        <SectionHeader icon={Map} title="ID Mappings" count={idMaps.length} color="text-pink-400" />
        {idLoading ? <div className="flex items-center gap-2 text-xs text-gray-500"><Loader2 size={12} className="animate-spin" /> Loading…</div>
          : idMaps.length === 0 ? <EmptyState icon={Map} title="No ID mappings" sub="ID mappings are created by the ID Mapper step in iFlows." />
          : (
            <div className="overflow-hidden rounded-xl border border-gray-700">
              <table className="w-full text-xs">
                <thead><tr className="bg-gray-800/80 text-left text-gray-400 uppercase tracking-wide">
                  <th className="px-4 py-2.5">Source Agency</th><th className="px-4 py-2.5">Source ID</th>
                  <th className="px-4 py-2.5 hidden md:table-cell">Target Agency</th><th className="px-4 py-2.5 hidden md:table-cell">Target ID</th>
                  <th className="px-4 py-2.5"></th>
                </tr></thead>
                <tbody className="divide-y divide-gray-800">
                  {idMaps.map(m => (
                    <tr key={m.id} className="hover:bg-gray-800/40">
                      <td className="px-4 py-2.5 text-gray-300">{m.sourceAgency}</td>
                      <td className="px-4 py-2.5 text-pink-300 font-mono">{m.sourceId}</td>
                      <td className="px-4 py-2.5 text-gray-300 hidden md:table-cell">{m.targetAgency}</td>
                      <td className="px-4 py-2.5 text-pink-300 font-mono hidden md:table-cell">{m.targetId}</td>
                      <td className="px-4 py-2.5">
                        <button onClick={() => deleteIdEntry(m.id)} disabled={deletingId === m.id}
                          className="text-gray-600 hover:text-red-400 transition-colors p-1">
                          {deletingId === m.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Security Tab — with CRUD for credentials, secure params, OAuth, number ranges,
//                access policies, plus read-only keystores, cert mappings, log files
// ─────────────────────────────────────────────────────────────────────────────

function SecurityTab() {
  const [creds, setCreds]         = useState<Credential[]>([])
  const [ks, setKs]               = useState<Keystore[]>([])
  const [sp, setSp]               = useState<SecureParam[]>([])
  const [oauth, setOauth]         = useState<OAuthCred[]>([])
  const [certs, setCerts]         = useState<CertMapping[]>([])
  const [nr, setNr]               = useState<NumRange[]>([])
  const [logs, setLogs]           = useState<LogFile[]>([])
  const [policies, setPolicies]   = useState<AccessPolicy[]>([])
  const [loading, setLoading]     = useState(true)

  // Inline add-form visibility
  const [showAddCred, setShowAddCred]   = useState(false)
  const [showAddSp, setShowAddSp]       = useState(false)
  const [showAddOauth, setShowAddOauth] = useState(false)
  const [showAddNr, setShowAddNr]       = useState(false)
  const [showAddPolicy, setShowAddPolicy] = useState(false)

  // Deleting state
  const [deleting, setDeleting]   = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      cpiAPI.credentials().then(r => setCreds(r.data)).catch(() => setCreds([])),
      cpiAPI.keystores().then(r => setKs(r.data)).catch(() => setKs([])),
      cpiAPI.secureParameters().then(r => setSp(r.data)).catch(() => setSp([])),
      cpiAPI.oauthCredentials().then(r => setOauth(r.data)).catch(() => setOauth([])),
      cpiAPI.certMappings().then(r => setCerts(r.data)).catch(() => setCerts([])),
      cpiAPI.numberRanges().then(r => setNr(r.data)).catch(() => setNr([])),
      cpiAPI.logFiles().then(r => setLogs(r.data)).catch(() => setLogs([])),
      cpiAPI.accessPolicies().then(r => setPolicies(r.data)).catch(() => setPolicies([])),
    ]).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center py-16 text-gray-500"><Loader2 size={24} className="animate-spin mr-3" /> Loading security artifacts…</div>

  // ── Generic delete helper ──────────────────────────────────────────────────
  const doDelete = async (key: string, apiFn: () => Promise<any>, onDone: () => void) => {
    if (!confirm(`Delete "${key}"? This cannot be undone.`)) return
    setDeleting(key)
    try { await apiFn(); onDone() }
    catch (e: any) { alert(e?.response?.data?.detail ?? 'Delete failed') }
    finally { setDeleting(null) }
  }

  // ── AddCredentialForm ──────────────────────────────────────────────────────
  function AddCredentialForm() {
    const [name, setName] = useState(''); const [user, setUser] = useState('')
    const [pass, setPass] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
    const submit = async () => {
      if (!name || !user || !pass) { setErr('All fields required'); return }
      setBusy(true); setErr('')
      try {
        await cpiAPI.createCredential({ name, username: user, password: pass })
        setCreds(p => [...p, { name, kind: 'default', modified: new Date().toISOString() }])
        setShowAddCred(false)
      } catch (e: any) { setErr(e?.response?.data?.detail ?? 'Create failed') }
      finally { setBusy(false) }
    }
    return (
      <div className="p-3 bg-gray-800/60 rounded-lg border border-yellow-800/40 space-y-2">
        <div className="grid grid-cols-3 gap-2">
          <input className="input-field text-xs py-1.5" placeholder="Name *" value={name} onChange={e => setName(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Username *" value={user} onChange={e => setUser(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Password *" type="password" value={pass} onChange={e => setPass(e.target.value)} />
        </div>
        {err && <p className="text-xs text-red-400">{err}</p>}
        <div className="flex gap-2">
          <button onClick={submit} disabled={busy} className="flex items-center gap-1 px-3 py-1 text-xs bg-yellow-700 hover:bg-yellow-600 text-white rounded disabled:opacity-50">
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />} Add
          </button>
          <button onClick={() => setShowAddCred(false)} className="px-3 py-1 text-xs text-gray-400 hover:text-white bg-gray-700 rounded">Cancel</button>
        </div>
      </div>
    )
  }

  // ── AddSecureParamForm ─────────────────────────────────────────────────────
  function AddSecureParamForm() {
    const [name, setName] = useState(''); const [value, setValue] = useState('')
    const [desc, setDesc] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
    const submit = async () => {
      if (!name || !value) { setErr('Name and value required'); return }
      setBusy(true); setErr('')
      try {
        await cpiAPI.createSecureParameter({ name, value, description: desc })
        setSp(p => [...p, { name, description: desc, modified: new Date().toISOString() }])
        setShowAddSp(false)
      } catch (e: any) { setErr(e?.response?.data?.detail ?? 'Create failed') }
      finally { setBusy(false) }
    }
    return (
      <div className="p-3 bg-gray-800/60 rounded-lg border border-red-800/40 space-y-2">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <input className="input-field text-xs py-1.5" placeholder="Name *" value={name} onChange={e => setName(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Value *" type="password" value={value} onChange={e => setValue(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Description" value={desc} onChange={e => setDesc(e.target.value)} />
        </div>
        {err && <p className="text-xs text-red-400">{err}</p>}
        <div className="flex gap-2">
          <button onClick={submit} disabled={busy} className="flex items-center gap-1 px-3 py-1 text-xs bg-red-700 hover:bg-red-600 text-white rounded disabled:opacity-50">
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />} Add
          </button>
          <button onClick={() => setShowAddSp(false)} className="px-3 py-1 text-xs text-gray-400 hover:text-white bg-gray-700 rounded">Cancel</button>
        </div>
      </div>
    )
  }

  // ── AddOAuthForm ───────────────────────────────────────────────────────────
  function AddOAuthForm() {
    const [name, setName] = useState(''); const [clientId, setClientId] = useState('')
    const [secret, setSecret] = useState(''); const [tokenUrl, setTokenUrl] = useState('')
    const [scope, setScope] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
    const submit = async () => {
      if (!name || !clientId || !secret || !tokenUrl) { setErr('Name, Client ID, Secret and Token URL required'); return }
      setBusy(true); setErr('')
      try {
        await cpiAPI.createOAuthCredential({ name, clientId, clientSecret: secret, tokenServiceUrl: tokenUrl, scope })
        setOauth(p => [...p, { name, clientId, tokenServiceUrl: tokenUrl, modified: new Date().toISOString() }])
        setShowAddOauth(false)
      } catch (e: any) { setErr(e?.response?.data?.detail ?? 'Create failed') }
      finally { setBusy(false) }
    }
    return (
      <div className="p-3 bg-gray-800/60 rounded-lg border border-blue-800/40 space-y-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input className="input-field text-xs py-1.5" placeholder="Name *" value={name} onChange={e => setName(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Client ID *" value={clientId} onChange={e => setClientId(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Client Secret *" type="password" value={secret} onChange={e => setSecret(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Token Service URL *" value={tokenUrl} onChange={e => setTokenUrl(e.target.value)} />
          <input className="input-field text-xs py-1.5 sm:col-span-2" placeholder="Scope (optional)" value={scope} onChange={e => setScope(e.target.value)} />
        </div>
        {err && <p className="text-xs text-red-400">{err}</p>}
        <div className="flex gap-2">
          <button onClick={submit} disabled={busy} className="flex items-center gap-1 px-3 py-1 text-xs bg-blue-700 hover:bg-blue-600 text-white rounded disabled:opacity-50">
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />} Add
          </button>
          <button onClick={() => setShowAddOauth(false)} className="px-3 py-1 text-xs text-gray-400 hover:text-white bg-gray-700 rounded">Cancel</button>
        </div>
      </div>
    )
  }

  // ── AddNumberRangeForm ─────────────────────────────────────────────────────
  function AddNumberRangeForm() {
    const [name, setName] = useState(''); const [min, setMin] = useState('1')
    const [max, setMax] = useState('99999999'); const [start, setStart] = useState('1')
    const [len, setLen] = useState('10'); const [rotate, setRotate] = useState(false)
    const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
    const submit = async () => {
      if (!name) { setErr('Name required'); return }
      setBusy(true); setErr('')
      try {
        await cpiAPI.createNumberRange({ name, minValue: min, maxValue: max, currentValue: start, fieldLength: len, rotate })
        setNr(p => [...p, { name, description: '', min, max, current: start, fieldLength: len, rotate }])
        setShowAddNr(false)
      } catch (e: any) { setErr(e?.response?.data?.detail ?? 'Create failed') }
      finally { setBusy(false) }
    }
    return (
      <div className="p-3 bg-gray-800/60 rounded-lg border border-orange-800/40 space-y-2">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <input className="input-field text-xs py-1.5 col-span-2 sm:col-span-1" placeholder="Name *" value={name} onChange={e => setName(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Min" value={min} onChange={e => setMin(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Max" value={max} onChange={e => setMax(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Start" value={start} onChange={e => setStart(e.target.value)} />
          <input className="input-field text-xs py-1.5" placeholder="Field length" value={len} onChange={e => setLen(e.target.value)} />
          <label className="flex items-center gap-1.5 text-xs text-gray-400 col-span-2">
            <input type="checkbox" checked={rotate} onChange={e => setRotate(e.target.checked)} className="rounded" /> Rotate
          </label>
        </div>
        {err && <p className="text-xs text-red-400">{err}</p>}
        <div className="flex gap-2">
          <button onClick={submit} disabled={busy} className="flex items-center gap-1 px-3 py-1 text-xs bg-orange-700 hover:bg-orange-600 text-white rounded disabled:opacity-50">
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />} Add
          </button>
          <button onClick={() => setShowAddNr(false)} className="px-3 py-1 text-xs text-gray-400 hover:text-white bg-gray-700 rounded">Cancel</button>
        </div>
      </div>
    )
  }

  // ── AddAccessPolicyForm ────────────────────────────────────────────────────
  function AddAccessPolicyForm() {
    const [role, setRole] = useState(''); const [desc, setDesc] = useState('')
    const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
    const submit = async () => {
      if (!role) { setErr('Role name required'); return }
      setBusy(true); setErr('')
      try {
        const r = await cpiAPI.createAccessPolicy({ roleName: role, description: desc })
        setPolicies(p => [...p, { id: r.data.id ?? String(Date.now()), roleName: role, description: desc }])
        setShowAddPolicy(false)
      } catch (e: any) { setErr(e?.response?.data?.detail ?? 'Create failed') }
      finally { setBusy(false) }
    }
    return (
      <div className="p-3 bg-gray-800/60 rounded-lg border border-violet-800/40 space-y-2">
        <div className="flex gap-2">
          <input className="input-field text-xs py-1.5 flex-1" placeholder="Role Name *" value={role} onChange={e => setRole(e.target.value)} />
          <input className="input-field text-xs py-1.5 flex-1" placeholder="Description" value={desc} onChange={e => setDesc(e.target.value)} />
        </div>
        {err && <p className="text-xs text-red-400">{err}</p>}
        <div className="flex gap-2">
          <button onClick={submit} disabled={busy} className="flex items-center gap-1 px-3 py-1 text-xs bg-violet-700 hover:bg-violet-600 text-white rounded disabled:opacity-50">
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />} Add
          </button>
          <button onClick={() => setShowAddPolicy(false)} className="px-3 py-1 text-xs text-gray-400 hover:text-white bg-gray-700 rounded">Cancel</button>
        </div>
      </div>
    )
  }

  // ── Section header with optional add button ───────────────────────────────
  const SecHeader = ({ icon: Icon, title, count, color, onAdd }: { icon: any; title: string; count: number; color: string; onAdd?: () => void }) => (
    <div className="flex items-center gap-2 mb-3">
      <Icon size={15} className={color} />
      <h3 className="text-sm font-semibold text-white flex-1">{title}</h3>
      {count !== undefined && <span className="text-xs text-gray-500">({count})</span>}
      {onAdd && <button onClick={onAdd} title="Add new" className={`p-1 ${color} opacity-70 hover:opacity-100 transition-opacity`}><Plus size={13} /></button>}
    </div>
  )

  // ── Deletable row ─────────────────────────────────────────────────────────
  const DRow = ({ icon: Icon, iconClass, main, sub, deleteKey, apiFn, onDone }: {
    icon: any; iconClass: string; main: string; sub?: string
    deleteKey: string; apiFn: () => Promise<any>; onDone: () => void
  }) => (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-gray-800/40 rounded-lg border border-gray-700/50">
      <Icon size={14} className={`${iconClass} shrink-0`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 truncate">{main}</p>
        {sub && <p className="text-xs text-gray-500 truncate">{sub}</p>}
      </div>
      <button onClick={() => doDelete(deleteKey, apiFn, onDone)} disabled={deleting === deleteKey}
        className="text-gray-600 hover:text-red-400 transition-colors p-1 shrink-0">
        {deleting === deleteKey ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
      </button>
    </div>
  )

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

      {/* User Credentials */}
      <div className="space-y-2">
        <SecHeader icon={Key} title="User Credentials" count={creds.length} color="text-yellow-400" onAdd={() => setShowAddCred(s => !s)} />
        {showAddCred && <AddCredentialForm />}
        {creds.length === 0 && !showAddCred ? <EmptyState icon={Key} title="No credentials" /> :
          <div className="space-y-2">{creds.map(c => (
            <DRow key={c.name} icon={Key} iconClass="text-yellow-400" main={c.name} sub={`${c.kind} · ${fmtDate(c.modified)}`}
              deleteKey={c.name} apiFn={() => cpiAPI.deleteCredential(c.name)} onDone={() => setCreds(p => p.filter(x => x.name !== c.name))} />
          ))}</div>}
      </div>

      {/* Keystore Entries (read-only) */}
      <div className="space-y-2">
        <SectionHeader icon={Shield} title="Keystore Entries" count={ks.length} color="text-green-400" />
        {ks.length === 0 ? <EmptyState icon={Shield} title="No keystore entries" /> :
          <div className="space-y-2">{ks.map(k => (
            <div key={k.alias} className="flex items-center gap-3 px-4 py-2.5 bg-gray-800/40 rounded-lg border border-gray-700/50">
              <Shield size={14} className="text-green-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate">{k.alias}</p>
                <p className="text-xs text-gray-500">{k.type}</p>
              </div>
            </div>
          ))}</div>}
      </div>

      {/* Secure Parameters */}
      <div className="space-y-2">
        <SecHeader icon={EyeOff} title="Secure Parameters" count={sp.length} color="text-red-400" onAdd={() => setShowAddSp(s => !s)} />
        {showAddSp && <AddSecureParamForm />}
        {sp.length === 0 && !showAddSp ? <EmptyState icon={EyeOff} title="No secure parameters" /> :
          <div className="space-y-2">{sp.map(p => (
            <DRow key={p.name} icon={EyeOff} iconClass="text-red-400" main={p.name} sub={p.description || fmtDate(p.modified)}
              deleteKey={p.name} apiFn={() => cpiAPI.deleteSecureParameter(p.name)} onDone={() => setSp(prev => prev.filter(x => x.name !== p.name))} />
          ))}</div>}
      </div>

      {/* OAuth Credentials */}
      <div className="space-y-2">
        <SecHeader icon={Globe} title="OAuth Credentials" count={oauth.length} color="text-blue-400" onAdd={() => setShowAddOauth(s => !s)} />
        {showAddOauth && <AddOAuthForm />}
        {oauth.length === 0 && !showAddOauth ? <EmptyState icon={Globe} title="No OAuth credentials" /> :
          <div className="space-y-2">{oauth.map(o => (
            <DRow key={o.name} icon={Globe} iconClass="text-blue-400" main={o.name} sub={`${o.clientId ?? '—'} → ${o.tokenServiceUrl ?? '—'}`}
              deleteKey={o.name} apiFn={() => cpiAPI.deleteOAuthCredential(o.name)} onDone={() => setOauth(p => p.filter(x => x.name !== o.name))} />
          ))}</div>}
      </div>

      {/* Certificate Mappings (read-only) */}
      <div className="space-y-2">
        <SectionHeader icon={LogIn} title="Certificate Mappings" count={certs.length} color="text-purple-400" />
        {certs.length === 0 ? <EmptyState icon={LogIn} title="No certificate mappings" /> :
          <div className="space-y-2">{certs.map(c => (
            <div key={c.id} className="flex items-center gap-3 px-4 py-2.5 bg-gray-800/40 rounded-lg border border-gray-700/50">
              <LogIn size={14} className="text-purple-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate">{c.user ?? c.id}</p>
                <p className="text-xs text-gray-500">Valid until: {fmtDate(c.validUntil)}</p>
              </div>
            </div>
          ))}</div>}
      </div>

      {/* Number Ranges */}
      <div className="space-y-2">
        <SecHeader icon={Hash} title="Number Ranges" count={nr.length} color="text-orange-400" onAdd={() => setShowAddNr(s => !s)} />
        {showAddNr && <AddNumberRangeForm />}
        {nr.length === 0 && !showAddNr ? <EmptyState icon={Hash} title="No number ranges" /> :
          <div className="space-y-2">{nr.map(n => (
            <div key={n.name} className="flex items-start gap-3 px-4 py-2.5 bg-gray-800/40 rounded-lg border border-gray-700/50">
              <Hash size={14} className="text-orange-400 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200">{n.name}</p>
                <div className="flex flex-wrap gap-3 mt-0.5 text-xs text-gray-500">
                  <span>Current: <span className="text-white font-mono">{n.current}</span></span>
                  <span>Range: {n.min}–{n.max}</span>
                  <span>Len: {n.fieldLength}</span>
                  {n.rotate && <span className="text-yellow-400">Rotate</span>}
                </div>
              </div>
              <button onClick={() => doDelete(n.name, () => cpiAPI.deleteNumberRange(n.name), () => setNr(p => p.filter(x => x.name !== n.name)))}
                disabled={deleting === n.name} className="text-gray-600 hover:text-red-400 transition-colors p-1 shrink-0 mt-0.5">
                {deleting === n.name ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
              </button>
            </div>
          ))}</div>}
      </div>

      {/* Access Policies */}
      <div className="space-y-2">
        <SecHeader icon={Lock} title="Access Policies" count={policies.length} color="text-violet-400" onAdd={() => setShowAddPolicy(s => !s)} />
        {showAddPolicy && <AddAccessPolicyForm />}
        {policies.length === 0 && !showAddPolicy ? <EmptyState icon={Lock} title="No access policies" sub="Access policies control artifact visibility per role." /> :
          <div className="space-y-2">{policies.map(p => (
            <DRow key={p.id} icon={Lock} iconClass="text-violet-400" main={p.roleName} sub={p.description}
              deleteKey={p.id} apiFn={() => cpiAPI.deleteAccessPolicy(p.id)} onDone={() => setPolicies(prev => prev.filter(x => x.id !== p.id))} />
          ))}</div>}
      </div>

      {/* Log Files */}
      <div className="space-y-2 md:col-span-2">
        <SectionHeader icon={FileText} title="Log Files" count={logs.length} color="text-gray-400" />
        {logs.length === 0 ? <EmptyState icon={FileText} title="No log files found" sub="Log files appear based on your tenant's logging configuration." /> : (
          <div className="overflow-hidden rounded-xl border border-gray-700">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-800/80 text-left text-xs text-gray-400 uppercase tracking-wide">
                <th className="px-4 py-3">Name</th><th className="px-4 py-3">Application</th>
                <th className="px-4 py-3 hidden md:table-cell">Last Modified</th><th className="px-4 py-3"></th>
              </tr></thead>
              <tbody className="divide-y divide-gray-800">
                {logs.map(f => (
                  <tr key={f.name} className="hover:bg-gray-800/40">
                    <td className="px-4 py-2.5 text-gray-200 text-xs font-mono">{f.name}</td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{f.application}</td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs hidden md:table-cell">{fmtDate(f.lastModified)}</td>
                    <td className="px-4 py-2.5">
                      <button onClick={async () => {
                        try { const r = await cpiAPI.downloadLogFile(f.application); triggerDownload(r.data, `${f.application}_logs.zip`) }
                        catch { alert('Log download failed — logs may require specific SAP permissions.') }
                      }} title="Download log archive" className="text-gray-600 hover:text-blue-400 transition-colors p-1">
                        <Download size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────────────────────

export default function CPIConnect() {
  const [ping, setPing]             = useState<PingResult | null>(null)
  const [pinging, setPinging]       = useState(true)
  const [activeTab, setActiveTab]   = useState<ActiveTab>('packages')
  const [showSettings, setShowSettings] = useState(false)

  // Packages
  const [packages, setPackages]   = useState<CpiPackage[]>([])
  const [pkgLoading, setPkgLoading] = useState(false)
  const [deployedIds, setDeployedIds] = useState<Record<string, string>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreate, setShowCreate]   = useState(false)
  const [newName, setNewName]         = useState('')
  const [newDesc, setNewDesc]         = useState('')
  const [creating, setCreating]       = useState(false)
  const [createErr, setCreateErr]     = useState('')
  const [copyModal, setCopyModal]     = useState<{ id: string; name: string } | null>(null)

  // Messages
  const [messages, setMessages]   = useState<Message[]>([])
  const [msgLoading, setMsgLoading] = useState(false)
  const [msgStatus, setMsgStatus] = useState<MsgStatus>('ALL')

  // Import
  const [importFiles, setImportFiles]   = useState<ImportFile[]>([])
  const [importPkg, setImportPkg]       = useState('')
  const [importingAll, setImportingAll] = useState(false)
  const [importArtifactType, setImportArtifactType] = useState('iflow')
  const importZipRef = useRef<HTMLInputElement>(null)

  // Ping
  const doPing = useCallback(async () => {
    setPinging(true)
    try { const r = await cpiAPI.ping(); setPing(r.data) }
    catch { setPing({ connected: false, reason: 'Could not reach backend' }) }
    setPinging(false)
  }, [])
  useEffect(() => { doPing() }, [doPing])

  // Runtime
  const loadRuntime = useCallback(async () => {
    try { const r = await cpiAPI.runtimeStatus(); setDeployedIds(r.data) } catch { /* silent */ }
  }, [])

  // Packages
  const loadPackages = useCallback(async () => {
    setPkgLoading(true)
    try {
      const r = await cpiAPI.packages()
      setPackages(r.data)
      if (r.data.length > 0) setImportPkg(p => p || r.data[0].id)
      loadRuntime()
    } catch { setPackages([]) }
    finally { setPkgLoading(false) }
  }, [loadRuntime])

  // Messages
  const loadMessages = useCallback(async (status: MsgStatus) => {
    setMsgLoading(true)
    try { const r = await cpiAPI.messages(50, status === 'ALL' ? undefined : status); setMessages(r.data) }
    catch { setMessages([]) }
    finally { setMsgLoading(false) }
  }, [])

  useEffect(() => {
    if (activeTab === 'packages' || activeTab === 'import') loadPackages()
    if (activeTab === 'messages') loadMessages(msgStatus)
  }, [activeTab])

  useEffect(() => { if (activeTab === 'messages') loadMessages(msgStatus) }, [msgStatus])

  // Create package
  const createPackage = async () => {
    if (!newName.trim()) { setCreateErr('Name is required.'); return }
    setCreating(true); setCreateErr('')
    try {
      await cpiAPI.createPackage(newName.trim(), newDesc.trim())
      setShowCreate(false); setNewName(''); setNewDesc('')
      loadPackages()
    } catch (e: any) { setCreateErr(e?.response?.data?.detail ?? 'Create failed') }
    finally { setCreating(false) }
  }

  // Import preview state
  const [importPreview, setImportPreview] = useState<{
    idx: number; file: File; cpi_url: string; method: string
    body: Record<string, string>; artifact_id: string; artifact_name: string
  } | null>(null)
  const [previewBodyText, setPreviewBodyText] = useState('')
  const [previewJsonError, setPreviewJsonError] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)

  // Import helpers
  const addImportFiles = (files: FileList | File[]) => {
    const arr = Array.from(files).filter(f => f.name.endsWith('.zip'))
    setImportFiles(p => [...p, ...arr.map(f => ({ file: f, status: 'pending' as ImportStatus, message: '' }))])
  }
  const removeImportFile = (idx: number) => setImportFiles(p => p.filter((_, i) => i !== idx))

  // Show preview modal before actually importing
  const previewImport = async (idx: number, pkg: string, fileObj?: File) => {
    if (!pkg) return
    const file = fileObj ?? importFiles[idx].file
    setPreviewLoading(true)
    try {
      const r = await cpiAPI.previewImport(file, pkg, importArtifactType)
      const preview = r.data
      setImportPreview({ idx, file, cpi_url: preview.cpi_url, method: preview.method, body: preview.body, artifact_id: preview.artifact_id, artifact_name: preview.artifact_name })
      setPreviewBodyText(JSON.stringify(preview.body, null, 2))
      setPreviewJsonError('')
    } catch (e: any) {
      setImportFiles(p => p.map((f, i) => i === idx ? { ...f, status: 'error', message: 'Preview failed: ' + (e?.response?.data?.detail || e?.message) } : f))
    } finally { setPreviewLoading(false) }
  }

  // Actually send after user confirms the preview
  const confirmImport = async () => {
    if (!importPreview) return
    // Validate JSON
    let edited: Record<string, string>
    try {
      edited = JSON.parse(previewBodyText)
      setPreviewJsonError('')
    } catch {
      setPreviewJsonError('Invalid JSON — please fix before confirming.')
      return
    }
    const { idx, file } = importPreview
    setImportPreview(null)
    setImportFiles(p => p.map((f, i) => i === idx ? { ...f, status: 'uploading', message: '' } : f))
    try {
      const r = await cpiAPI.importZip(file, edited.PackageId ?? importPkg, importArtifactType, edited.Id, edited.Name)
      const verb = r.data.status === 'updated' ? 'updated' : 'imported'
      setImportFiles(p => p.map((f, i) => i === idx ? { ...f, status: 'done', message: `${verb} · ID: ${r.data.id}`, id: r.data.id } : f))
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Upload failed'
      setImportFiles(p => p.map((f, i) => i === idx ? { ...f, status: 'error', message: String(msg) } : f))
    }
  }

  const importOne = async (idx: number, pkg: string, fileObj?: File) => {
    await previewImport(idx, pkg, fileObj)
  }
  const importAll = async () => {
    if (!importPkg) return
    // For Import All, show preview for first pending item at a time
    const pending = importFiles.map((f, i) => ({ f, i })).filter(({ f }) => f.status === 'pending' || f.status === 'error')
    if (pending.length > 0) {
      await previewImport(pending[0].i, importPkg, pending[0].f.file)
    }
  }

  const msgStatuses: MsgStatus[] = ['ALL', 'COMPLETED', 'FAILED', 'PROCESSING', 'RETRY', 'CANCELLED']

  const tabs = [
    { id: 'packages'  as ActiveTab, label: 'Packages', icon: Package },
    { id: 'messages'  as ActiveTab, label: 'Monitor',  icon: Activity },
    { id: 'security'  as ActiveTab, label: 'Security', icon: Shield },
    { id: 'datastores'as ActiveTab, label: 'Data',     icon: Database },
    { id: 'import'    as ActiveTab, label: 'Import',   icon: Upload },
  ]

  const filteredPackages = searchQuery
    ? packages.filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.id.toLowerCase().includes(searchQuery.toLowerCase()))
    : packages

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center">
            <Cloud size={20} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">CPI Connect</h1>
            <p className="text-sm text-gray-400">SAP Integration Suite — all APIs</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowSettings(true)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="Change tenant / credentials">
            <Settings size={14} /> Connect
          </button>
          <button onClick={doPing} disabled={pinging}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
            <RefreshCw size={14} className={pinging ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Connection status */}
      <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${
        pinging ? 'bg-gray-800/40 border-gray-700'
          : ping?.connected ? 'bg-green-900/20 border-green-800'
          : 'bg-red-900/20 border-red-800'}`}>
        {pinging ? <Loader2 size={18} className="animate-spin text-gray-400" />
          : ping?.connected ? <CheckCircle size={18} className="text-green-400 shrink-0" />
          : <XCircle size={18} className="text-red-400 shrink-0" />}
        <div>
          {pinging ? <p className="text-sm text-gray-400">Checking connection…</p>
            : ping?.connected ? <><p className="text-sm font-medium text-green-300">Connected</p><p className="text-xs text-gray-500 truncate">{ping.tenant}</p></>
            : <><p className="text-sm font-medium text-red-300">Not connected</p><p className="text-xs text-gray-500">{ping?.reason}</p></>}
        </div>
      </div>

      {ping?.connected && (
        <>
          {/* Tab bar */}
          <div className="flex gap-1 bg-gray-800/40 p-1 rounded-xl">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors flex-1 justify-center ${
                  activeTab === id ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}>
                <Icon size={14} /><span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>

          {/* ── Packages Tab ──────────────────────────────────────────── */}
          {activeTab === 'packages' && (
            <div className="space-y-3">
              {/* Toolbar */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="relative flex-1 min-w-[180px]">
                  <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search packages & iFlows…"
                    className="input-field w-full pl-8 py-1.5 text-sm" />
                </div>
                <button onClick={() => { setShowCreate(c => !c); setCreateErr('') }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-green-700/80 hover:bg-green-600 text-white rounded-lg transition-colors shrink-0">
                  <Plus size={13} /> New Package
                </button>
                <button onClick={loadPackages} className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 shrink-0">
                  <RefreshCw size={12} className={pkgLoading ? 'animate-spin' : ''} /> Reload
                </button>
              </div>

              {/* Create form */}
              {showCreate && (
                <div className="border border-green-800 bg-green-950/20 rounded-xl p-4 space-y-3">
                  <p className="text-sm font-medium text-green-300">Create Integration Package</p>
                  <div className="flex flex-wrap gap-3">
                    <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Package name *"
                      className="input-field flex-1 min-w-[180px] text-sm" onKeyDown={e => e.key === 'Enter' && createPackage()} autoFocus />
                    <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Description"
                      className="input-field flex-1 min-w-[200px] text-sm" onKeyDown={e => e.key === 'Enter' && createPackage()} />
                  </div>
                  {createErr && <p className="text-xs text-red-400">{createErr}</p>}
                  <div className="flex gap-2">
                    <button onClick={createPackage} disabled={creating}
                      className="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white rounded-lg">
                      {creating ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />} Create
                    </button>
                    <button onClick={() => { setShowCreate(false); setNewName(''); setNewDesc(''); setCreateErr('') }}
                      className="px-4 py-1.5 text-sm text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg">Cancel</button>
                  </div>
                </div>
              )}

              {pkgLoading ? (
                <div className="flex items-center justify-center py-16 text-gray-500"><Loader2 size={24} className="animate-spin mr-3" /> Loading…</div>
              ) : filteredPackages.length === 0 ? (
                <EmptyState icon={Package} title={searchQuery ? 'No matches' : 'No packages found'} sub={searchQuery ? 'Try a different search' : 'Create a package above'} />
              ) : (
                <div className="space-y-2">
                  {filteredPackages.map(pkg => (
                    <PackageRow key={pkg.id} pkg={pkg} deployedIds={deployedIds} packages={packages}
                      onDeleted={id => setPackages(p => p.filter(x => x.id !== id))}
                      onRuntimeChange={loadRuntime}
                      onCopyRequest={(id, name) => setCopyModal({ id, name })}
                      searchQuery={searchQuery} />
                  ))}
                </div>
              )}

              <p className="text-xs text-gray-600 flex items-center gap-1.5 pt-1">
                <Info size={11} />
                <Settings size={11} /> = ext. params · <Copy size={11} /> = copy · <Download size={11} /> = export ZIP · <Zap size={11} /> = bulk deploy · <Trash2 size={11} /> = delete
              </p>
            </div>
          )}

          {/* ── Messages Tab ──────────────────────────────────────────── */}
          {activeTab === 'messages' && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {msgStatuses.map(s => (
                  <button key={s} onClick={() => setMsgStatus(s)}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors ${msgStatus === s ? 'bg-blue-600 border-blue-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white'}`}>
                    {s}
                  </button>
                ))}
                <button onClick={() => loadMessages(msgStatus)} className="ml-auto text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1">
                  <RefreshCw size={12} className={msgLoading ? 'animate-spin' : ''} /> Reload
                </button>
              </div>

              {!msgLoading && messages.length > 0 && (
                <p className="text-xs text-gray-500">
                  {messages.length} messages · <span className="text-green-400">{messages.filter(m => m.status === 'COMPLETED').length} ok</span> ·{' '}
                  <span className="text-red-400">{messages.filter(m => m.status === 'FAILED').length} failed</span>
                  <span className="ml-2 text-gray-600">— click any row for runs, attachments &amp; error details</span>
                </p>
              )}

              {msgLoading ? (
                <div className="flex items-center justify-center py-16 text-gray-500"><Loader2 size={24} className="animate-spin mr-3" /> Loading…</div>
              ) : messages.length === 0 ? (
                <EmptyState icon={Activity} title="No message processing logs" sub="Deploy and trigger an iFlow to see entries here." />
              ) : (
                <div className="overflow-hidden rounded-xl border border-gray-700">
                  <table className="w-full text-sm">
                    <thead><tr className="bg-gray-800/80 text-left text-xs text-gray-400 uppercase tracking-wide">
                      <th className="px-4 py-3">Status</th><th className="px-4 py-3">iFlow</th>
                      <th className="px-4 py-3 hidden md:table-cell">Start</th>
                      <th className="px-4 py-3 hidden lg:table-cell">Sender</th>
                      <th className="px-4 py-3 hidden lg:table-cell">Receiver</th>
                    </tr></thead>
                    <tbody className="divide-y divide-gray-800">
                      {messages.map(m => <MessageRow key={m.id} msg={m} />)}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── Security Tab ──────────────────────────────────────────── */}
          {activeTab === 'security' && <SecurityTab />}

          {/* ── Data Stores Tab ───────────────────────────────────────── */}
          {activeTab === 'datastores' && <DataStoresTab />}

          {/* ── Import ZIP Tab ────────────────────────────────────────── */}
          {activeTab === 'import' && (
            <div className="space-y-5">

              {/* Artifact type + Package selectors */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Artifact Type <span className="text-red-400">*</span></label>
                  <select className="select-field w-full" value={importArtifactType} onChange={e => setImportArtifactType(e.target.value)}>
                    <optgroup label="Integration">
                      <option value="iflow">Integration Flow (iFlow)</option>
                    </optgroup>
                    <optgroup label="Mapping">
                      <option value="messagemapping">Message Mapping (.mmap)</option>
                      <option value="valuemapping">Value Mapping</option>
                    </optgroup>
                    <optgroup label="Script & Function">
                      <option value="scriptcollection">Script Collection (Groovy)</option>
                      <option value="functionlibrary">Function Library</option>
                    </optgroup>
                    <optgroup label="API">
                      <option value="restapi">REST API</option>
                      <option value="soapapi">SOAP API</option>
                      <option value="odataapi">OData API</option>
                    </optgroup>
                  </select>
                  <p className="text-xs text-gray-600 mt-1">
                    {importArtifactType === 'iflow'          && 'Upload a CPI iFlow export ZIP'}
                    {importArtifactType === 'messagemapping' && 'Upload a .mmap ZIP (generated by this app or exported from CPI)'}
                    {importArtifactType === 'valuemapping'   && 'Upload a Value Mapping ZIP exported from CPI'}
                    {importArtifactType === 'scriptcollection' && 'Upload a Script Collection ZIP from CPI'}
                    {importArtifactType === 'functionlibrary' && 'Upload a Function Library ZIP from CPI'}
                    {importArtifactType === 'restapi'        && 'Upload a REST API artifact ZIP'}
                    {importArtifactType === 'soapapi'        && 'Upload a SOAP API artifact ZIP'}
                    {importArtifactType === 'odataapi'       && 'Upload an OData API artifact ZIP'}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Target Package <span className="text-red-400">*</span></label>
                  {pkgLoading
                    ? <div className="flex items-center gap-2 text-gray-400 text-sm py-2"><Loader2 size={14} className="animate-spin" /> Loading…</div>
                    : packages.length === 0
                    ? <p className="text-sm text-yellow-300">No packages found — visit the Packages tab first.</p>
                    : (
                      <select className="select-field w-full" value={importPkg} onChange={e => setImportPkg(e.target.value)}>
                        {!importPkg && <option value="">Select a package…</option>}
                        {packages.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
                      </select>
                    )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  {importArtifactType === 'messagemapping' ? 'Message Mapping ZIP files' :
                   importArtifactType === 'valuemapping'   ? 'Value Mapping ZIP files' :
                   importArtifactType === 'scriptcollection' ? 'Script Collection ZIP files' :
                   importArtifactType === 'functionlibrary' ? 'Function Library ZIP files' :
                   importArtifactType === 'restapi'        ? 'REST API ZIP files' :
                   importArtifactType === 'soapapi'        ? 'SOAP API ZIP files' :
                   importArtifactType === 'odataapi'       ? 'OData API ZIP files' :
                   'iFlow ZIP files'}
                </label>
                <div onClick={() => importZipRef.current?.click()} onDragOver={e => e.preventDefault()}
                  onDrop={e => { e.preventDefault(); addImportFiles(e.dataTransfer.files) }}
                  className="border-2 border-dashed border-gray-700 hover:border-blue-500 rounded-xl p-8 text-center cursor-pointer transition-colors">
                  <FolderOpen size={28} className="mx-auto mb-2 text-gray-500" />
                  <p className="text-gray-300 text-sm font-medium">Click or drag-and-drop ZIP files here</p>
                  <p className="text-gray-500 text-xs mt-1">Artifact ID and name are read from the ZIP automatically</p>
                </div>
                <input ref={importZipRef} type="file" accept=".zip" multiple className="hidden"
                  onChange={e => { if (e.target.files) addImportFiles(e.target.files); e.target.value = '' }} />
              </div>

              {importFiles.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-400">
                      {importFiles.length} queued · {importFiles.filter(f => f.status === 'done').length} done · {importFiles.filter(f => f.status === 'error').length} failed
                    </p>
                    <button onClick={() => setImportFiles([])} className="text-xs text-gray-500 hover:text-red-400">Clear all</button>
                  </div>
                  <div className="rounded-xl border border-gray-700 overflow-hidden divide-y divide-gray-800">
                    {importFiles.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-3 px-4 py-3 bg-gray-800/30">
                        <div className="shrink-0 w-5">
                          {item.status === 'uploading' && <Loader2 size={16} className="animate-spin text-blue-400" />}
                          {item.status === 'done'      && <CheckCircle size={16} className="text-green-400" />}
                          {item.status === 'error'     && <XCircle size={16} className="text-red-400" />}
                          {item.status === 'pending'   && <Archive size={16} className="text-gray-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-200 truncate">{item.file.name}</p>
                          <p className="text-xs truncate mt-0.5" style={{ color: item.status === 'error' ? '#f87171' : item.status === 'done' ? '#4ade80' : '#6b7280' }}>
                            {item.status === 'pending' ? `${(item.file.size / 1024).toFixed(0)} KB` : item.message || (item.status === 'uploading' ? 'Uploading…' : '')}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {(item.status === 'pending' || item.status === 'error') && (
                            <button onClick={() => importPkg && importOne(idx, importPkg, item.file)} disabled={!importPkg}
                              className="text-xs px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white">{item.status === 'error' ? 'Retry' : 'Import'}</button>
                          )}
                          {item.status !== 'uploading' && (
                            <button onClick={() => removeImportFile(idx)} className="text-gray-600 hover:text-red-400"><X size={14} /></button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  {importFiles.some(f => f.status === 'pending' || f.status === 'error') && (
                    <button onClick={importAll} disabled={importingAll || !importPkg}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium">
                      {importingAll ? <><Loader2 size={15} className="animate-spin" /> Importing…</> : <><Upload size={15} /> Import All</>}
                    </button>
                  )}
                  {importFiles.length > 0 && importFiles.every(f => f.status === 'done') && (
                    <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-green-900/30 border border-green-700 text-green-300 text-sm">
                      <CheckCheck size={16} /> All {importFiles.length} artifact{importFiles.length !== 1 ? 's' : ''} imported. Go to Packages to deploy them.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ── Import Preview Modal ──────────────────────────────────────── */}
      {importPreview && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setImportPreview(null)}>
          <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
              <div>
                <h3 className="text-white font-semibold">Preview CPI Request</h3>
                <p className="text-xs text-gray-500 mt-0.5">Review and edit before sending to CPI</p>
              </div>
              <button onClick={() => setImportPreview(null)} className="text-gray-500 hover:text-white"><X size={16} /></button>
            </div>

            <div className="p-5 space-y-4">
              {/* URL + Method */}
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1.5">Endpoint</label>
                <div className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
                  <span className="text-xs font-bold text-green-400 shrink-0">{importPreview.method}</span>
                  <span className="text-xs font-mono text-gray-300 break-all">{importPreview.cpi_url}</span>
                </div>
              </div>

              {/* Editable JSON body */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-gray-400">Request Body (JSON)</label>
                  <span className="text-[10px] text-gray-600">ArtifactContent sent as base64 ZIP at confirm — not shown here</span>
                </div>
                <textarea
                  value={previewBodyText}
                  onChange={e => { setPreviewBodyText(e.target.value); setPreviewJsonError('') }}
                  rows={10}
                  className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 rounded-lg px-3 py-2.5 text-xs font-mono text-gray-200 outline-none resize-none"
                />
                {previewJsonError && (
                  <p className="text-xs text-red-400 mt-1">{previewJsonError}</p>
                )}
              </div>

              {/* File info */}
              <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-800/50 rounded-lg px-3 py-2">
                <Archive size={13} />
                <span>File: <span className="text-gray-300">{importPreview.file.name}</span></span>
                <span>·</span>
                <span>{(importPreview.file.size / 1024).toFixed(0)} KB</span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3 pt-1">
                <button onClick={confirmImport}
                  className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold transition-colors">
                  <Upload size={15} /> Confirm Send
                </button>
                <button onClick={() => setImportPreview(null)}
                  className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Not connected help */}
      {!pinging && !ping?.connected && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/30 p-6 space-y-4">
          <div className="flex items-center gap-2 text-yellow-400"><AlertTriangle size={18} /><h3 className="font-semibold">Not connected</h3></div>
          <p className="text-sm text-gray-400">Configure your SAP Integration Suite tenant to get started.</p>
          <button onClick={() => setShowSettings(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition-colors">
            <Settings size={15} /> Open Connection Settings
          </button>
          <details className="text-xs text-gray-600">
            <summary className="cursor-pointer hover:text-gray-400 transition-colors">Or edit manually…</summary>
            <pre className="mt-2 bg-gray-900 border border-gray-700 rounded-lg p-4 text-green-300 overflow-x-auto">{`CPI_AUTH_TYPE=oauth
CPI_API_BASE_URL=https://<tenant>.it-cpi018.cfapps.eu10.hana.ondemand.com/api/v1
CPI_CLIENT_ID=sb-...
CPI_CLIENT_SECRET=...
CPI_TOKEN_URL=https://<subaccount>.authentication.eu10.hana.ondemand.com/oauth/token`}</pre>
          </details>
        </div>
      )}

      {/* Copy modal */}
      {copyModal && (
        <CopyModal sourceId={copyModal.id} sourceName={copyModal.name} packages={packages}
          onClose={() => setCopyModal(null)} onCopied={loadPackages} />
      )}

      {/* Connection Settings modal */}
      {showSettings && (
        <ConnectionSettingsModal
          onClose={() => setShowSettings(false)}
          onSaved={(connected, tenant) => {
            setPing({ connected, tenant })
            setShowSettings(false)
            if (connected) loadPackages()
          }}
        />
      )}
    </div>
  )
}
