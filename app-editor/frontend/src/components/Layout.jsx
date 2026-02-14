import { Link, useLocation } from 'react-router-dom'
import { Clapperboard, ListMusic, AlignLeft, CheckCircle } from 'lucide-react'

const NAV = [
  { path: '/', label: 'Fila de Edição', icon: Clapperboard },
]

export default function Layout({ children }) {
  const location = useLocation()

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-purple text-white flex flex-col shrink-0">
        <div className="p-6 border-b border-purple-light/30">
          <h1 className="text-xl font-bold">Best of Opera</h1>
          <span className="text-xs opacity-70">APP3 — Editor</span>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {NAV.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === path
                  ? 'bg-white/20 text-white'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="p-4 text-xs opacity-50">v1.0.0</div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-8 overflow-auto">
        {children}
      </main>
    </div>
  )
}
