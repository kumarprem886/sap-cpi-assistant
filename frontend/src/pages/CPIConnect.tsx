import { useState, useEffect, useCallback } from 'react'
import {
  Cloud, RefreshCw, CheckCircle, XCircle, Package,
  GitMerge, Activity, ChevronDown, ChevronRight,
  Rocket, Shield, Key, AlertTriangle, Clock, Loader2,
  CheckCheck, AlertCircle
} from 'lucide-react'
import { cpiAPI } from '../api/client'

// ── Types ─────────────────────────────────────────────────────────────────────

interface PingResult   { connected: boolean; tenant?: string; reason?: string }
interface Package      { id: string; name: string; description: string; version: string; modified: string }
interface IFlow        { id: string; name: string; version: string; type: string }
interface Message      { id: string; iflow: string; status: string; start: string; end: string; sender: string; receiver: string }
interface Credential   { name: string; kind: string; modified: string }
interface Keystore     { alias: string; type: string }

type MsgStatus = 'ALL' | 'COMPLETED' | 'FAILED' | 'PROCESSING' | 'RETRY' | 'CANCELLED'
type ActiveTab = 'packages' | 'messages' | 'security'

// ── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    COMPLETED:  'bg-green-900/60 text-green-300 border-green-700',
    FAILED:     'bg-red-900/60 text-red-300 border-red-700',
    PROCESSING: 'bg-blue-900/60 text-blue-300 border-blue-700',
    RETRY:      'bg-yellow-900/60 text-yellow-300 border-yellow-700',
    CANCELLED:  'bg-gray-800 text-gray-400 border-gray-600',
  }
  const style = map[status] ?? 'bg-gray-800 text-gray-400 border-gray-600'
  return (
    <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${style}`}>
      {status}
    </span>
  )
}

// ── Format date from OData /Date(ms)/ or ISO ──────────────────────────────────
function fmtDate(raw: string | null | undefined): string {
  if (!raw) return '—'
  const ms = raw.match(/\/Date\((\d+)\)\//)
  const d   = ms ? new Date(parseInt(ms[1])) : new Date(raw)
  if (isNaN(d.getTime())) return raw
  return d.toLocaleString()
}

// ── Package row with expandable iFlows ────────────────────────────────────────
function PackageRow({ pkg }: { pkg: Package }) {
  const [open, setOpen]       = useState(false)
  const [iflows, setIflows]   = useState<IFlow[]>([])
  const [loading, setLoading] = useState(false)
  const [deploying, setDeploying] = useState<string | null>(null)
  const [deployMsg, setDeployMsg] = useState<Record<string, string>>({})

  const loadIflows = async () => {
    if (open) { setOpen(false); return }
    setOpen(true)
    if (iflows.length) return
    setLoading(true)
    try {
      const res = await cpiAPI.iflows(pkg.id)
      setIflows(res.data)
    } catch { setIflows([]) }
    finally { setLoading(false) }
  }

  const deploy = async (iflow: IFlow) => {
    setDeploying(iflow.id)
    setDeployMsg(m => ({ ...m, [iflow.id]: '' }))
    try {
      await cpiAPI.deploy(pkg.id, iflow.id)
      setDeployMsg(m => ({ ...m, [iflow.id]: 'Deploying…' }))
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? 'Deploy failed'
      setDeployMsg(m => ({ ...m, [iflow.id]: msg }))
    } finally {
      setDeploying(null)
    }
  }

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      {/* Package header */}
      <button
        onClick={loadIflows}
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-800/60 hover:bg-gray-800 transition-colors text-left"
      >
        {open ? <ChevronDown size={16} className="text-gray-400 shrink-0" /> : <ChevronRight size={16} className="text-gray-400 shrink-0" />}
        <Package size={16} className="text-blue-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate">{pkg.name}</p>
          <p className="text-xs text-gray-500 truncate">{pkg.id} · v{pkg.version}</p>
        </div>
        {pkg.description && (
          <p className="text-xs text-gray-500 hidden sm:block max-w-xs truncate">{pkg.description}</p>
        )}
      </button>

      {/* iFlow list */}
      {open && (
        <div className="bg-gray-900/50 border-t border-gray-700">
          {loading ? (
            <div className="flex items-center gap-2 px-6 py-3 text-sm text-gray-400">
              <Loader2 size={14} className="animate-spin" /> Loading iFlows…
            </div>
          ) : iflows.length === 0 ? (
            <p className="px-6 py-3 text-sm text-gray-500">No iFlows in this package</p>
          ) : (
            iflows.map(iflow => (
              <div key={iflow.id} className="flex items-center gap-3 px-6 py-2.5 border-b border-gray-800/60 last:border-0">
                <GitMerge size={14} className="text-purple-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 truncate">{iflow.name}</p>
                  <p className="text-xs text-gray-500">{iflow.id} · v{iflow.version}</p>
                  {deployMsg[iflow.id] && (
                    <p className="text-xs text-yellow-400 mt-0.5">{deployMsg[iflow.id]}</p>
                  )}
                </div>
                <span className="text-xs text-gray-600 bg-gray-800 px-2 py-0.5 rounded">{iflow.type}</span>
                <button
                  onClick={() => deploy(iflow)}
                  disabled={deploying === iflow.id}
                  className="flex items-center gap-1.5 px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded transition-colors"
                >
                  {deploying === iflow.id
                    ? <Loader2 size={12} className="animate-spin" />
                    : <Rocket size={12} />}
                  Deploy
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CPIConnect() {
  const [ping, setPing]               = useState<PingResult | null>(null)
  const [pinging, setPinging]         = useState(true)
  const [activeTab, setActiveTab]     = useState<ActiveTab>('packages')

  // Packages
  const [packages, setPackages]       = useState<Package[]>([])
  const [pkgLoading, setPkgLoading]   = useState(false)

  // Messages
  const [messages, setMessages]       = useState<Message[]>([])
  const [msgLoading, setMsgLoading]   = useState(false)
  const [msgStatus, setMsgStatus]     = useState<MsgStatus>('ALL')

  // Security
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [keystores, setKeystores]     = useState<Keystore[]>([])
  const [secLoading, setSecLoading]   = useState(false)

  // ── Ping ──────────────────────────────────────────────────────────────────
  const doPing = useCallback(async () => {
    setPinging(true)
    try {
      const res = await cpiAPI.ping()
      setPing(res.data)
    } catch {
      setPing({ connected: false, reason: 'Could not reach backend' })
    }
    setPinging(false)
  }, [])

  useEffect(() => { doPing() }, [doPing])

  // ── Load packages ──────────────────────────────────────────────────────────
  const loadPackages = useCallback(async () => {
    setPkgLoading(true)
    try {
      const res = await cpiAPI.packages()
      setPackages(res.data)
    } catch { setPackages([]) }
    finally { setPkgLoading(false) }
  }, [])

  // ── Load messages ──────────────────────────────────────────────────────────
  const loadMessages = useCallback(async (status: MsgStatus) => {
    setMsgLoading(true)
    try {
      const res = await cpiAPI.messages(50, status === 'ALL' ? undefined : status)
      setMessages(res.data)
    } catch { setMessages([]) }
    finally { setMsgLoading(false) }
  }, [])

  // ── Load security ──────────────────────────────────────────────────────────
  const loadSecurity = useCallback(async () => {
    setSecLoading(true)
    try {
      const [cr, ks] = await Promise.all([cpiAPI.credentials(), cpiAPI.keystores()])
      setCredentials(cr.data)
      setKeystores(ks.data)
    } catch { setCredentials([]); setKeystores([]) }
    finally { setSecLoading(false) }
  }, [])

  // Load data when tab changes
  useEffect(() => {
    if (activeTab === 'packages') loadPackages()
    if (activeTab === 'messages') loadMessages(msgStatus)
    if (activeTab === 'security') loadSecurity()
  }, [activeTab])

  // Reload messages when status filter changes
  useEffect(() => {
    if (activeTab === 'messages') loadMessages(msgStatus)
  }, [msgStatus])

  const tabs: { id: ActiveTab; label: string; icon: typeof Package }[] = [
    { id: 'packages', label: 'Packages & iFlows', icon: Package },
    { id: 'messages', label: 'Message Monitor',   icon: Activity },
    { id: 'security', label: 'Security',          icon: Shield },
  ]

  const msgStatuses: MsgStatus[] = ['ALL', 'COMPLETED', 'FAILED', 'PROCESSING', 'RETRY', 'CANCELLED']

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
            <p className="text-sm text-gray-400">Live connection to your SAP Integration Suite tenant</p>
          </div>
        </div>
        <button
          onClick={doPing}
          disabled={pinging}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
        >
          <RefreshCw size={14} className={pinging ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Connection status */}
      <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${
        pinging
          ? 'bg-gray-800/40 border-gray-700'
          : ping?.connected
            ? 'bg-green-900/20 border-green-800'
            : 'bg-red-900/20 border-red-800'
      }`}>
        {pinging ? (
          <Loader2 size={18} className="animate-spin text-gray-400" />
        ) : ping?.connected ? (
          <CheckCircle size={18} className="text-green-400 shrink-0" />
        ) : (
          <XCircle size={18} className="text-red-400 shrink-0" />
        )}
        <div>
          {pinging ? (
            <p className="text-sm text-gray-400">Checking connection…</p>
          ) : ping?.connected ? (
            <>
              <p className="text-sm font-medium text-green-300">Connected</p>
              <p className="text-xs text-gray-500 truncate">{ping.tenant}</p>
            </>
          ) : (
            <>
              <p className="text-sm font-medium text-red-300">Not connected</p>
              <p className="text-xs text-gray-500">{ping?.reason ?? 'Check credentials in backend/.env'}</p>
            </>
          )}
        </div>
      </div>

      {/* Only show tabs if connected */}
      {ping?.connected && (
        <>
          {/* Tab bar */}
          <div className="flex gap-1 bg-gray-800/40 p-1 rounded-xl">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex-1 justify-center ${
                  activeTab === id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>

          {/* ── Packages tab ───────────────────────────────────────────────── */}
          {activeTab === 'packages' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-400">
                  {pkgLoading ? 'Loading…' : `${packages.length} package${packages.length !== 1 ? 's' : ''} found`}
                </p>
                <button
                  onClick={loadPackages}
                  className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
                >
                  <RefreshCw size={12} className={pkgLoading ? 'animate-spin' : ''} /> Reload
                </button>
              </div>

              {pkgLoading ? (
                <div className="flex items-center justify-center py-16 text-gray-500">
                  <Loader2 size={24} className="animate-spin mr-3" /> Loading packages…
                </div>
              ) : packages.length === 0 ? (
                <div className="text-center py-16 text-gray-500">
                  <Package size={40} className="mx-auto mb-3 opacity-30" />
                  <p>No integration packages found on this tenant.</p>
                  <p className="text-xs mt-1">Create a package in SAP Integration Suite → Design.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {packages.map(pkg => <PackageRow key={pkg.id} pkg={pkg} />)}
                </div>
              )}
            </div>
          )}

          {/* ── Messages tab ───────────────────────────────────────────────── */}
          {activeTab === 'messages' && (
            <div className="space-y-3">
              {/* Status filter */}
              <div className="flex flex-wrap gap-2">
                {msgStatuses.map(s => (
                  <button
                    key={s}
                    onClick={() => setMsgStatus(s)}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                      msgStatus === s
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white'
                    }`}
                  >
                    {s}
                  </button>
                ))}
                <button
                  onClick={() => loadMessages(msgStatus)}
                  className="ml-auto text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
                >
                  <RefreshCw size={12} className={msgLoading ? 'animate-spin' : ''} /> Reload
                </button>
              </div>

              {msgLoading ? (
                <div className="flex items-center justify-center py-16 text-gray-500">
                  <Loader2 size={24} className="animate-spin mr-3" /> Loading messages…
                </div>
              ) : messages.length === 0 ? (
                <div className="text-center py-16 text-gray-500">
                  <Activity size={40} className="mx-auto mb-3 opacity-30" />
                  <p>No message processing logs found.</p>
                  <p className="text-xs mt-1">Deploy and trigger an iFlow to see entries here.</p>
                </div>
              ) : (
                <div className="overflow-hidden rounded-xl border border-gray-700">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-800/80 text-left text-xs text-gray-400 uppercase tracking-wide">
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">iFlow</th>
                        <th className="px-4 py-3 hidden md:table-cell">Start</th>
                        <th className="px-4 py-3 hidden lg:table-cell">Sender</th>
                        <th className="px-4 py-3 hidden lg:table-cell">Receiver</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {messages.map(m => (
                        <tr key={m.id} className="hover:bg-gray-800/40 transition-colors">
                          <td className="px-4 py-3"><StatusBadge status={m.status} /></td>
                          <td className="px-4 py-3 text-gray-200 font-medium max-w-xs truncate">{m.iflow ?? '—'}</td>
                          <td className="px-4 py-3 text-gray-400 text-xs hidden md:table-cell whitespace-nowrap">{fmtDate(m.start)}</td>
                          <td className="px-4 py-3 text-gray-400 text-xs hidden lg:table-cell">{m.sender ?? '—'}</td>
                          <td className="px-4 py-3 text-gray-400 text-xs hidden lg:table-cell">{m.receiver ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── Security tab ───────────────────────────────────────────────── */}
          {activeTab === 'security' && (
            <div className="space-y-6">
              {secLoading ? (
                <div className="flex items-center justify-center py-16 text-gray-500">
                  <Loader2 size={24} className="animate-spin mr-3" /> Loading security artifacts…
                </div>
              ) : (
                <>
                  {/* User Credentials */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Key size={16} className="text-yellow-400" />
                      <h3 className="text-sm font-semibold text-white">User Credentials</h3>
                      <span className="text-xs text-gray-500">({credentials.length})</span>
                    </div>
                    {credentials.length === 0 ? (
                      <p className="text-sm text-gray-500 pl-6">No user credentials found.</p>
                    ) : (
                      <div className="space-y-2">
                        {credentials.map(c => (
                          <div key={c.name} className="flex items-center gap-3 px-4 py-3 bg-gray-800/40 rounded-lg border border-gray-700">
                            <Key size={14} className="text-yellow-400 shrink-0" />
                            <div className="flex-1">
                              <p className="text-sm text-gray-200">{c.name}</p>
                              <p className="text-xs text-gray-500">{c.kind} · Modified {fmtDate(c.modified)}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Keystore entries */}
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Shield size={16} className="text-green-400" />
                      <h3 className="text-sm font-semibold text-white">Keystore Entries</h3>
                      <span className="text-xs text-gray-500">({keystores.length})</span>
                    </div>
                    {keystores.length === 0 ? (
                      <p className="text-sm text-gray-500 pl-6">No keystore entries found.</p>
                    ) : (
                      <div className="space-y-2">
                        {keystores.map(k => (
                          <div key={k.alias} className="flex items-center gap-3 px-4 py-3 bg-gray-800/40 rounded-lg border border-gray-700">
                            <Shield size={14} className="text-green-400 shrink-0" />
                            <div className="flex-1">
                              <p className="text-sm text-gray-200">{k.alias}</p>
                              <p className="text-xs text-gray-500">{k.type}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* Not connected help */}
      {!pinging && !ping?.connected && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/30 p-6 space-y-3">
          <div className="flex items-center gap-2 text-yellow-400">
            <AlertTriangle size={18} />
            <h3 className="font-semibold">How to connect</h3>
          </div>
          <p className="text-sm text-gray-400">Edit <code className="text-blue-300 bg-gray-800 px-1.5 py-0.5 rounded">backend/.env</code> and set:</p>
          <pre className="text-xs bg-gray-900 border border-gray-700 rounded-lg p-4 text-green-300 overflow-x-auto">{`CPI_AUTH_TYPE=oauth
CPI_API_BASE_URL=https://<tenant>.it-cpi018.cfapps.eu10.hana.ondemand.com/api/v1
CPI_CLIENT_ID=sb-...
CPI_CLIENT_SECRET=...
CPI_TOKEN_URL=https://<subaccount>.authentication.eu10.hana.ondemand.com/oauth/token`}</pre>
          <p className="text-xs text-gray-500">Then restart the backend and click Refresh above.</p>
        </div>
      )}
    </div>
  )
}
