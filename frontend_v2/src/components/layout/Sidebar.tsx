import { Link, useLocation } from 'react-router-dom'
import {
  Home,
  FolderOpen,
  ClipboardList,
  Search,
  Film,
  Eye,
  RotateCcw,
  Settings,
  Copy,
  ShieldAlert
} from 'lucide-react'
import { cn } from '../../lib/utils'

const navItems = [
  { to: '/', icon: Home, label: 'Dashboard' },
  { to: '/organize', icon: FolderOpen, label: 'Organize' },
  { to: '/triage', icon: ClipboardList, label: 'Triage Center' },
  { to: '/search', icon: Search, label: 'Search' },
  { to: '/veo', icon: Film, label: 'VEO Studio' },
  { to: '/analysis', icon: Eye, label: 'Analysis' },
  { to: '/duplicates', icon: Copy, label: 'Duplicates' },
  { to: '/forensic-vault', icon: ShieldAlert, label: 'Forensic Vault', highlight: true },
  { to: '/rollback', icon: RotateCcw, label: 'Rollback Center', highlight: true },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-64 bg-white/[0.05] backdrop-blur-xl border-r border-white/10 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <h1 className="text-xl font-bold text-white">
          🗂️ AI File Organizer
        </h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.to
          const Icon = item.icon

          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300",
                isActive
                  ? "bg-primary text-white"
                  : "text-white/60 hover:bg-white/10 hover:text-white",
                item.highlight && !isActive && "text-warning hover:text-warning"
              )}
            >
              <Icon size={20} />
              <span className="font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Recently Viewed (placeholder) */}
      <div className="p-4 border-t border-white/10">
        <div className="text-xs text-white/40 mb-2">Recently Viewed</div>
        <div className="text-sm text-white/60 space-y-1">
          <div className="truncate">contract_draft.pdf</div>
          <div className="truncate">Search: finn contracts</div>
        </div>
      </div>
    </aside>
  )
}
