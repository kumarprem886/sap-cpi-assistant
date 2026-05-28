import { useNavigate } from 'react-router-dom'
import { GitMerge, Shuffle, Code2, FileCode2, MessageSquare, ArrowRight } from 'lucide-react'

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

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">SAP CPI Assistant</h1>
        <p className="text-gray-400 text-lg">AI-powered toolkit for SAP Cloud Platform Integration developers</p>
      </div>

      {/* Feature cards */}
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
  )
}
