import { Bell, User } from 'lucide-react'

export default function Header() {
  return (
    <header className="h-16 bg-white/[0.05] backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-6">
      {/* Breadcrumbs (add later with route context) */}
      <div className="text-sm text-white/60">
        Home / Dashboard
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="p-2 rounded-lg hover:bg-white/10 transition-colors relative">
          <Bell size={20} className="text-white/60" />
          {/* Notification badge */}
          <div className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full" />
        </button>

        {/* User menu */}
        <button className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-colors">
          <User size={20} className="text-white/60" />
          <span className="text-sm text-white/80">User</span>
        </button>
      </div>
    </header>
  )
}
