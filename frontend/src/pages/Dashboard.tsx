import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
  GitMerge, Shuffle, Code2, FileCode2, MessageSquare, ArrowRight,
  Cpu, Cloud, CheckCircle, XCircle, Loader2, Settings,
} from 'lucide-react'
import axios from 'axios'

// ── Types ──────────────────────────────────────────────────────────────────────

interface AISettings {
  provider: string
  anthropicKey: string; anthropicModel: string
  groqKey: string;      groqModel: string
  openaiKey: string;    openaiModel: string
  geminiKey: string;    geminiModel: string
  ollamaBaseUrl: string; ollamaModel: string
}

interface CpiStatus { connected: boolean; tenant?: string; reason?: string }

// ── Feature cards ──────────────────────────────────────────────────────────────

const features = [
  {
    to: '/iflow',
    icon: GitMerge,
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    title: 'iFlow Generator',
    desc: 'Generate complete iFlow XML with sender/receiver adapters, routing, error handling, and all steps.',
    tags: ['Scaffold', 'XML', 'Adapters'],
  },
  {
    to: '/mapping',
    icon: Shuffle,
    color: 'bg-green-500/10 text-green-400 border-green-500/20',
    title: 'Message Mapping',
    desc: 'Auto-map source to target schemas. Get Groovy or XSLT output with field-level mapping logic.',
    tags: ['Auto-Map', 'Groovy', 'XSLT'],
  },
  {
    to: '/groovy',
    icon: Code2,
    color: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    title: 'Groovy Scripts',
    desc: 'Generate, explain, and debug Groovy scripts for CPI — transformations, headers, HTTP calls, and more.',
    tags: ['Generate', 'Debug', 'Explain'],
  },
  {
    to: '/xslt',
    icon: FileCode2,
    color: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    title: 'XSLT Generator',
    desc: 'Create XSLT 2.0 transformations from description or sample XML pairs. Works directly in CPI.',
    tags: ['XSLT 2.0', 'From Samples', 'Explain'],
  },
  {
    to: '/chat',
    icon: MessageSquare,
    color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    title: 'AI Assistant',
    desc: 'Ask anything about SAP CPI — adapter config, best practices, error resolution, code review.',
    tags: ['Chat', 'Review', 'Best Practices'],
  },
]

// ── Provider definitions ───────────────────────────────────────────────────────

const PROVIDERS = [
  {
    id: 'anthropic',
    label: 'Anthropic',
    sub: 'Claude',
    color: { ring: 'ring-orange-600/60', bg: 'bg-orange-900/20', dot: 'bg-orange-400', text: 'text-orange-300', badge: 'bg-orange-900/40 text-orange-300 border-orange-700' },
    isConfigured: (s: AISettings) => !!s.anthropicKey,
    model:        (s: AISettings) => s.anthropicModel,
  },
  {
    id: 'groq',
    label: 'Groq',
    sub: 'Free Cloud',
    color: { ring: 'ring-green-600/60', bg: 'bg-green-900/20', dot: 'bg-green-400', text: 'text-green-300', badge: 'bg-green-900/40 text-green-300 border-green-700' },
    isConfigured: (s: AISettings) => !!s.groqKey,
    model:        (s: AISettings) => s.groqModel,
  },
  {
    id: 'openai',
    label: 'OpenAI',
    sub: 'GPT',
    color: { ring: 'ring-teal-600/60', bg: 'bg-teal-900/20', dot: 'bg-teal-400', text: 'text-teal-300', badge: 'bg-teal-900/40 text-teal-300 border-teal-700' },
    isConfigured: (s: AISettings) => !!s.openaiKey,
    model:        (s: AISettings) => s.openaiModel,
  },
  {
    id: 'gemini',
    label: 'Gemini',
    sub: 'Google',
    color: { ring: 'ring-purple-600/60', bg: 'bg-purple-900/20', dot: 'bg-purple-400', text: 'text-purple-300', badge: 'bg-purple-900/40 text-purple-300 border-purple-700' },
    isConfigured: (s: AISettings) => !!s.geminiKey,
    model:        (s: AISettings) => s.geminiModel,
  },
  {
    id: 'ollama',
    label: 'Ollama',
    sub: 'Local',
    color: { ring: 'ring-blue-600/60', bg: 'bg-blue-900/20', dot: 'bg-blue-400', text: 'text-blue-300', badge: 'bg-blue-900/40 text-blue-300 border-blue-700' },
    isConfigured: (_: AISettings) => true,
    model:        (s: AISettings) => s.ollamaModel,
  },
]

// ── Dashboard ──────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()

  const [aiSettings, setAiSettings] = useState<AISettings | null>(null)
  const [cpiStatus,  setCpiStatus]  = useState<CpiStatus | null>(null)
  const [loading,    setLoading]    = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get('/api/settings/ai').then(r => setAiSettings(r.data)).catch(() => {}),
      axios.get('/api/cpi/ping').then(r => setCpiStatus(r.data)).catch(() => setCpiStatus({ connected: false, reason: 'Could not reach backend' })),
    ]).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">SAP CPI Assistant</h1>
        <p className="text-gray-400 text-lg">AI-powered toolkit for SAP Cloud Platform Integration developers</p>
      </div>

      {/* ── Connections ────────────────────────────────────────────────────────── */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Connections</h2>

        {/* AI providers */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-3">
          {PROVIDERS.map(p => {
            const isActive    = aiSettings?.provider === p.id
            const configured  = aiSettings ? p.isConfigured(aiSettings) : false
            const model       = aiSettings ? p.model(aiSettings) : '—'
            const c           = p.color

            return (
              <button
                key={p.id}
                onClick={() => navigate('/chat')}
                className={`relative flex flex-col gap-2 p-4 rounded-xl border transition-all text-left group
                  ${isActive
                    ? `${c.bg} ring-1 ${c.ring} border-transparent`
                    : 'bg-gray-800/40 border-gray-700 hover:border-gray-600'}`}
              >
                {/* Active badge */}
                {isActive && (
                  <span className={`absolute top-3 right-3 text-[10px] font-semibold px-1.5 py-0.5 rounded border ${c.badge}`}>
                    Active
                  </span>
                )}

                <div className="flex items-center gap-2">
                  {loading
                    ? <Loader2 size={14} className="animate-spin text-gray-500" />
                    : configured
                      ? <span className={`w-2 h-2 rounded-full ${c.dot} shrink-0`} />
                      : <span className="w-2 h-2 rounded-full bg-gray-600 shrink-0" />
                  }
                  <Cpu size={14} className={configured ? c.text : 'text-gray-500'} />
                  <span className={`text-sm font-semibold ${configured ? 'text-white' : 'text-gray-500'}`}>{p.label}</span>
                  <span className={`text-xs ${configured ? 'text-gray-400' : 'text-gray-600'}`}>· {p.sub}</span>
                </div>

                <div className="pl-4">
                  <p className={`text-xs truncate ${configured ? 'text-gray-400' : 'text-gray-600'}`} title={model}>
                    {loading ? '…' : model}
                  </p>
                  <p className={`text-xs mt-0.5 ${configured ? c.text : 'text-gray-600'}`}>
                    {loading ? '' : p.id === 'ollama' ? 'No key needed' : configured ? 'API key configured' : 'No API key set'}
                  </p>
                </div>
              </button>
            )
          })}
        </div>

        {/* CPI Tenant */}
        <button
          onClick={() => navigate('/cpi')}
          className={`w-full flex items-center gap-4 p-4 rounded-xl border transition-all text-left group
            ${cpiStatus?.connected
              ? 'bg-green-900/10 border-green-800/60 hover:border-green-700'
              : 'bg-gray-800/40 border-gray-700 hover:border-gray-600'}`}
        >
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0
            ${cpiStatus?.connected ? 'bg-green-900/40' : 'bg-gray-700/60'}`}>
            {loading
              ? <Loader2 size={16} className="animate-spin text-gray-400" />
              : cpiStatus?.connected
                ? <CheckCircle size={16} className="text-green-400" />
                : <XCircle size={16} className="text-gray-500" />}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <Cloud size={13} className={cpiStatus?.connected ? 'text-green-400' : 'text-gray-500'} />
              <span className={`text-sm font-semibold ${cpiStatus?.connected ? 'text-white' : 'text-gray-400'}`}>
                SAP Integration Suite
              </span>
              {!loading && (
                <span className={`text-xs px-1.5 py-0.5 rounded border ${
                  cpiStatus?.connected
                    ? 'bg-green-900/40 text-green-300 border-green-700'
                    : 'bg-gray-800 text-gray-500 border-gray-700'}`}>
                  {cpiStatus?.connected ? 'Connected' : 'Not connected'}
                </span>
              )}
            </div>
            <p className={`text-xs truncate ${cpiStatus?.connected ? 'text-gray-400' : 'text-gray-500'}`}>
              {loading ? '…'
                : cpiStatus?.connected ? cpiStatus.tenant
                : cpiStatus?.reason ?? 'Open CPI Connect to configure'}
            </p>
          </div>

          <Settings size={14} className="text-gray-600 group-hover:text-gray-400 shrink-0 transition-colors" />
        </button>
      </div>

      {/* ── Tools ──────────────────────────────────────────────────────────────── */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Tools</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {features.map(({ to, icon: Icon, color, title, desc, tags }) => (
            <button
              key={to}
              onClick={() => navigate(to)}
              className="card text-left hover:border-gray-600 hover:bg-gray-800/80 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className={`w-10 h-10 rounded-lg border flex items-center justify-center ${color}`}>
                  <Icon size={18} />
                </div>
                <ArrowRight size={16} className="text-gray-600 group-hover:text-gray-400 transition-colors mt-1" />
              </div>
              <h3 className="font-semibold text-white mb-1">{title}</h3>
              <p className="text-sm text-gray-400 mb-3 leading-relaxed">{desc}</p>
              <div className="flex flex-wrap gap-1.5">
                {tags.map(t => (
                  <span key={t} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full border border-gray-700">
                    {t}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
