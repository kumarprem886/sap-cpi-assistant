import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, GitMerge, Code2, FileCode2,
  Shuffle, MessageSquare, Zap, FileText
} from 'lucide-react'

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/iflow', icon: GitMerge, label: 'iFlow Generator' },
  { to: '/mapping', icon: Shuffle, label: 'Message Mapping' },
  { to: '/groovy', icon: Code2, label: 'Groovy Scripts' },
  { to: '/xslt', icon: FileCode2, label: 'XSLT Generator' },
  { to: '/docs', icon: FileText, label: 'Doc Generator' },
  { to: '/chat', icon: MessageSquare, label: 'AI Assistant' },
]

export default function Sidebar() {
  return (
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

      <div className="px-4 py-4 border-t border-gray-800">
        <p className="text-xs text-gray-600">Powered by Claude AI</p>
      </div>
    </aside>
  )
}
