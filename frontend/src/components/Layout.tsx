import { ReactNode } from 'react'
import Sidebar from './Sidebar'

// Detect GitHub Pages or any static host (no backend available)
const IS_STATIC_HOST = window.location.hostname.includes('github.io') ||
                       !window.location.hostname.includes('localhost') &&
                       !window.location.hostname.includes('127.0.0.1')

export { IS_STATIC_HOST }

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-gray-950">
        {IS_STATIC_HOST && (
          <div className="w-full bg-amber-900/80 border-b border-amber-700 px-6 py-2.5 flex items-center gap-3 text-sm text-amber-200">
            <span className="text-lg">⚠️</span>
            <span>
              <strong className="text-amber-100">Demo only</strong> — This hosted version cannot run AI features (no backend).
              To use all features, run the app locally:&nbsp;
              <code className="bg-amber-900 text-amber-100 px-1.5 py-0.5 rounded text-xs">
                uvicorn main:app --port 8000
              </code>
              &nbsp;+&nbsp;
              <code className="bg-amber-900 text-amber-100 px-1.5 py-0.5 rounded text-xs">
                npm run dev
              </code>
            </span>
            <a
              href="https://github.com/kumarprem886/sap-cpi-assistant"
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto shrink-0 text-xs underline text-amber-300 hover:text-amber-100"
            >
              GitHub →
            </a>
          </div>
        )}
        <div className="max-w-5xl mx-auto px-6 py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
