import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Visão Geral', icon: '◈' },
  { to: '/appointments', label: 'Agendamentos', icon: '◷' },
  { to: '/contacts', label: 'Contatos', icon: '◉' },
  { to: '/conversations', label: 'Conversas', icon: '◎' },
  { to: '/metrics', label: 'Métricas', icon: '◫' },
]

export function Sidebar() {
  return (
    <aside className="w-60 min-h-screen bg-primary flex flex-col">
      <div className="px-6 py-6 border-b border-primary-dark">
        <span className="text-white text-xl font-semibold tracking-wide">Lumina</span>
        <p className="text-white/50 text-xs mt-0.5">Clínica Estética</p>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-white/20 text-white font-medium'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <span className="text-base">{l.icon}</span>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="px-6 py-4 border-t border-primary-dark">
        <p className="text-white/40 text-xs">v1.0 · Lumina CRM</p>
      </div>
    </aside>
  )
}
