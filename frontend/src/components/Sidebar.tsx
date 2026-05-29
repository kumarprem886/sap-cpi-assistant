import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  LayoutDashboard, GitMerge, Code2, FileCode2,
  Shuffle, MessageSquare, Zap, FileText, Cloud, Cpu,
  Settings, X, Loader2, Check, CheckCircle, XCircle,
  ChevronDown,
} from 'lucide-react'
import { settingsAPI } from '../api/client'

const nav = [
  { to: '/',       icon: LayoutDashboard, label: 'Dashboard'       },
  { to: '/iflow',  icon: GitMerge,        label: 'iFlow Generator' },
  { to: '/mapping',icon: Shuffle,         label: 'Message Mapping' },
  { to: '/groovy', icon: Code2,           label: 'Groovy Scripts'  },
  { to: '/xslt',   icon: FileCode2,       label: 'XSLT Generator'  },
  { to: '/docs',   icon: FileText,        label: 'Doc Generator'   },
  { to: '/chat',   icon: MessageSquare,   label: 'AI Assistant'    },
  { to: '/cpi',    icon: Cloud,           label: 'CPI Connect'     },
]

const providerStyle: Record<string, { label: string; color: string; badge: string }> = {
  anthropic: { label: 'Claude',  color: 'text-orange-400', badge: 'bg-orange-900/40 text-orange-300 border-orange-700' },
  groq:      { label: 'Groq',    color: 'text-green-400',  badge: 'bg-green-900/40 text-green-300 border-green-700'   },
  openai:    { label: 'GPT',     color: 'text-teal-400',   badge: 'bg-teal-900/40 text-teal-300 border-teal-700'      },
  gemini:    { label: 'Gemini',  color: 'text-purple-400', badge: 'bg-purple-900/40 text-purple-300 border-purple-700'},
  ollama:    { label: 'Ollama',  color: 'text-blue-400',   badge: 'bg-blue-900/40 text-blue-300 border-blue-700'      },
}

const MASKED = '••••••••'

const GROQ_MODELS = [
  'llama-3.3-70b-versatile', 'llama-3.1-70b-versatile', 'llama-3.1-8b-instant',
  'llama3-8b-8192', 'llama3-70b-8192', 'mixtral-8x7b-32768', 'gemma2-9b-it',
]
const ANTHROPIC_MODELS = [
  'claude-opus-4-5', 'claude-sonnet-4-5', 'claude-3-5-sonnet-20241022',
  'claude-3-5-haiku-20241022', 'claude-3-opus-20240229',
]
const OPENAI_MODELS = [
  'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo',
]
const GEMINI_MODELS = [
  'gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-1.5-pro', 'gemini-1.5-flash',
]

// ── AI Settings Modal ──────────────────────────────────────────────────────────

interface AISettings {
  provider: 'anthropic' | 'groq' | 'openai' | 'gemini' | 'ollama'
  anthropicKey: string;  anthropicModel: string
  groqKey: string;       groqModel: string
  openaiKey: string;     openaiModel: string
  geminiKey: string;     geminiModel: string
  ollamaBaseUrl: string; ollamaModel: string; ollamaVisionModel: string
}

const DEFAULT_FORM: AISettings = {
  provider: 'groq',
  anthropicKey: '', anthropicModel: 'claude-opus-4-5',
  groqKey: '',      groqModel: 'llama-3.3-70b-versatile',
  openaiKey: '',    openaiModel: 'gpt-4o',
  geminiKey: '',    geminiModel: 'gemini-2.0-flash',
  ollamaBaseUrl: 'http://localhost:11434', ollamaModel: 'qwen2.5-coder:14b', ollamaVisionModel: 'llava:7b',
}

function AISettingsModal({ onClose, onSaved }: {
  onClose: () => void
  onSaved: (provider: string, model: string) => void
}) {
  const [form, setForm]       = useState<AISettings>(DEFAULT_FORM)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [result, setResult]   = useState<{ ok: boolean; msg: string } | null>(null)
  const [customGroq, setCustomGroq] = useState(false)

  useEffect(() => {
    settingsAPI.getAI().then(r => {
      setForm({ ...DEFAULT_FORM, ...r.data })
      setCustomGroq(r.data.groqModel && !GROQ_MODELS.includes(r.data.groqModel))
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const set = <K extends keyof AISettings>(k: K, v: AISettings[K]) =>
    setForm(f => ({ ...f, [k]: v }))

  const save = async () => {
    setSaving(true); setResult(null)
    try {
      const r = await settingsAPI.saveAI(form)
      const ok = !r.data.warning
      setResult({ ok, msg: ok ? `Active: ${r.data.provider} · ${r.data.model}` : `Saved — warning: ${r.data.warning}` })
      onSaved(r.data.provider, r.data.model)
    } catch (e: any) {
      setResult({ ok: false, msg: e?.response?.data?.detail ?? 'Save failed' })
    } finally { setSaving(false) }
  }

  const maskField = (val: string, setter: (v: string) => void, placeholder: string) => (
    <input
      className="input-field w-full text-sm" type="password"
      placeholder={val === MASKED ? 'unchanged' : placeholder}
      value={val === MASKED ? '' : val}
      onFocus={() => { if (val === MASKED) setter('') }}
      onBlur={() => { if (val === '') setter(MASKED) }}
      onChange={e => setter(e.target.value)}
    />
  )

  const ALL_PROVIDERS = ['anthropic', 'groq', 'openai', 'gemini', 'ollama'] as const

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-t-2xl sm:rounded-2xl p-6 w-full sm:max-w-md space-y-5 shadow-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center">
              <Cpu size={15} className="text-gray-300" />
            </div>
            <div>
              <h3 className="font-semibold text-white text-sm">AI Provider Settings</h3>
              <p className="text-xs text-gray-500">Applied immediately — no restart needed</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white p-1 rounded"><X size={16} /></button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <Loader2 size={20} className="animate-spin mr-2" /> Loading…
          </div>
        ) : (
          <div className="space-y-4">

            {/* Provider tabs — 5 across */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">Provider</label>
              <div className="grid grid-cols-5 gap-1">
                {ALL_PROVIDERS.map(p => {
                  const ps = providerStyle[p]
                  return (
                    <button key={p} onClick={() => set('provider', p)}
                      className={`py-2 rounded-lg text-xs font-medium transition-all border ${
                        form.provider === p
                          ? `${ps.badge} border-current`
                          : 'bg-gray-800 text-gray-500 border-gray-700 hover:text-gray-300 hover:border-gray-500'
                      }`}>
                      {ps.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* ── Anthropic ── */}
            {form.provider === 'anthropic' && (
              <div className="space-y-3 p-4 rounded-xl bg-orange-950/20 border border-orange-800/40">
                <p className="text-xs font-medium text-orange-400">Anthropic — Claude</p>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">API Key <span className="text-red-400">*</span></label>
                  {maskField(form.anthropicKey, v => set('anthropicKey', v), 'sk-ant-...')}
                  <p className="text-xs text-gray-600 mt-1">Get your key at <span className="text-orange-400">console.anthropic.com</span></p>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Model</label>
                  <select className="input-field w-full text-sm" value={form.anthropicModel} onChange={e => set('anthropicModel', e.target.value)}>
                    {ANTHROPIC_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </div>
            )}

            {/* ── Groq ── */}
            {form.provider === 'groq' && (
              <div className="space-y-3 p-4 rounded-xl bg-green-950/20 border border-green-800/40">
                <p className="text-xs font-medium text-green-400">Groq — Free Cloud Inference</p>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">API Key <span className="text-red-400">*</span></label>
                  {maskField(form.groqKey, v => set('groqKey', v), 'gsk_...')}
                  <p className="text-xs text-gray-600 mt-1">Free key at <span className="text-green-400">console.groq.com</span></p>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Model</label>
                  {!customGroq ? (
                    <div className="flex gap-1.5">
                      <select className="input-field flex-1 text-sm" value={form.groqModel} onChange={e => set('groqModel', e.target.value)}>
                        {GROQ_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                      </select>
                      <button onClick={() => setCustomGroq(true)} className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 bg-gray-800 rounded border border-gray-700" title="Custom model ID">
                        <ChevronDown size={12} />
                      </button>
                    </div>
                  ) : (
                    <div className="flex gap-1.5">
                      <input className="input-field flex-1 text-sm" value={form.groqModel} onChange={e => set('groqModel', e.target.value)} placeholder="e.g. llama-3.3-70b-versatile" />
                      <button onClick={() => setCustomGroq(false)} className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 bg-gray-800 rounded border border-gray-700">List</button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── OpenAI ── */}
            {form.provider === 'openai' && (
              <div className="space-y-3 p-4 rounded-xl bg-teal-950/20 border border-teal-800/40">
                <p className="text-xs font-medium text-teal-400">OpenAI — GPT Models</p>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">API Key <span className="text-red-400">*</span></label>
                  {maskField(form.openaiKey, v => set('openaiKey', v), 'sk-...')}
                  <p className="text-xs text-gray-600 mt-1">Get your key at <span className="text-teal-400">platform.openai.com</span></p>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Model</label>
                  <select className="input-field w-full text-sm" value={form.openaiModel} onChange={e => set('openaiModel', e.target.value)}>
                    {OPENAI_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </div>
            )}

            {/* ── Gemini ── */}
            {form.provider === 'gemini' && (
              <div className="space-y-3 p-4 rounded-xl bg-purple-950/20 border border-purple-800/40">
                <p className="text-xs font-medium text-purple-400">Google — Gemini Models</p>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">API Key <span className="text-red-400">*</span></label>
                  {maskField(form.geminiKey, v => set('geminiKey', v), 'AIza...')}
                  <p className="text-xs text-gray-600 mt-1">Get your key at <span className="text-purple-400">aistudio.google.com</span></p>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Model</label>
                  <select className="input-field w-full text-sm" value={form.geminiModel} onChange={e => set('geminiModel', e.target.value)}>
                    {GEMINI_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </div>
            )}

            {/* ── Ollama ── */}
            {form.provider === 'ollama' && (
              <div className="space-y-3 p-4 rounded-xl bg-blue-950/20 border border-blue-800/40">
                <p className="text-xs font-medium text-blue-400">Ollama — Local Models (no key needed)</p>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Base URL</label>
                  <input className="input-field w-full text-sm font-mono" value={form.ollamaBaseUrl}
                    onChange={e => set('ollamaBaseUrl', e.target.value)} placeholder="http://localhost:11434" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Text Model</label>
                  <input className="input-field w-full text-sm" value={form.ollamaModel}
                    onChange={e => set('ollamaModel', e.target.value)} placeholder="e.g. qwen2.5-coder:14b" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Vision Model <span className="text-gray-600">(for FD image analysis)</span></label>
                  <input className="input-field w-full text-sm" value={form.ollamaVisionModel}
                    onChange={e => set('ollamaVisionModel', e.target.value)} placeholder="e.g. llava:7b" />
                </div>
              </div>
            )}

            {/* Result */}
            {result && (
              <div className={`flex items-start gap-2.5 px-4 py-3 rounded-lg text-xs border ${
                result.ok ? 'bg-green-900/20 border-green-800 text-green-300' : 'bg-red-900/20 border-red-800 text-red-300'}`}>
                {result.ok ? <CheckCircle size={14} className="shrink-0 mt-0.5" /> : <XCircle size={14} className="shrink-0 mt-0.5" />}
                <span className="leading-relaxed">{result.msg}</span>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 pt-1">
              <button onClick={save} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors">
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                Save &amp; Apply
              </button>
              <button onClick={onClose} className="ml-auto px-3 py-2 text-sm text-gray-500 hover:text-white transition-colors">Close</button>
            </div>

            <p className="text-xs text-gray-600 leading-relaxed">
              Saved to <code className="text-blue-400">backend/.env</code> and applied in-memory immediately.
              API keys left blank are kept unchanged.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sidebar ────────────────────────────────────────────────────────────────────

export default function Sidebar() {
  const [aiInfo, setAiInfo]       = useState<{ provider: string; model: string } | null>(null)
  const [showAISettings, setShowAISettings] = useState(false)

  const fetchStatus = () => {
    import('axios').then(({ default: axios }) =>
      axios.get('/api/chat/status').then(r => setAiInfo(r.data)).catch(() => {})
    )
  }

  useEffect(() => { fetchStatus() }, [])

  const ps = aiInfo ? (providerStyle[aiInfo.provider] ?? { label: aiInfo.provider, color: 'text-gray-400', badge: '' }) : null

  return (
    <>
      <aside className="w-60 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-sap-blue rounded-lg flex items-center justify-center">
              <Zap size={16} className="text-white" />
            </div>
            <div>
              <p className="font-bold text-white text-sm leading-tight">SAP CPI</p>
              <p className="text-xs text-gray-400 leading-tight">AI Assistant</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-sap-blue text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* AI provider footer */}
        <div className="px-4 py-4 border-t border-gray-800">
          <button
            onClick={() => setShowAISettings(true)}
            className="w-full flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-gray-800 transition-colors group"
            title="Change AI provider / API key"
          >
            {ps ? (
              <>
                <Cpu size={13} className={ps.color} />
                <div className="min-w-0 flex-1 text-left">
                  <p className={`text-xs font-medium leading-tight ${ps.color}`}>{ps.label}</p>
                  <p className="text-xs text-gray-600 truncate leading-tight" title={aiInfo!.model}>{aiInfo!.model}</p>
                </div>
              </>
            ) : (
              <>
                <Cpu size={13} className="text-gray-600" />
                <p className="text-xs text-gray-600 flex-1 text-left">AI not configured</p>
              </>
            )}
            <Settings size={13} className="text-gray-600 group-hover:text-gray-400 transition-colors shrink-0" />
          </button>
        </div>
      </aside>

      {/* AI Settings modal — rendered outside aside so it overlays everything */}
      {showAISettings && (
        <AISettingsModal
          onClose={() => setShowAISettings(false)}
          onSaved={(provider, model) => {
            setAiInfo({ provider, model })
            setShowAISettings(false)
          }}
        />
      )}
    </>
  )
}
