import { useLocation } from 'react-router-dom'
import { Bell, User } from 'lucide-react'
import { navItems } from '../../lib/navigation'

export default function Header() {
  const location = useLocation()

  // Find current page label, default to Dashboard
  const currentItem = navItems.find(item => item.to === location.pathname)
  const pageTitle = currentItem?.label || 'Dashboard'

  return (
    <header className="h-16 bg-white/[0.05] backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-6">
      {/* Breadcrumbs */}
      <div className="text-sm text-white/60">
        Home / <span className="text-white font-medium">{pageTitle}</span>
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button
          className="p-2 rounded-lg hover:bg-white/10 transition-colors relative focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
          aria-label="Notifications"
          title="Notifications"
        >
          <Bell size={20} className="text-white/60" aria-hidden="true" />
          {/* Notification badge */}
          <div className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full">
            <span className="sr-only">New notifications</span>
          </div>
        </button>

        {/* User menu */}
        <button
          className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
          aria-label="User menu"
          title="User menu"
        >
          <User size={20} className="text-white/60" aria-hidden="true" />
          <span className="text-sm text-white/80">User</span>
        </button>
      </div>
    </header>
  )
}
