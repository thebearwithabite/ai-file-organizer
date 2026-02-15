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

export interface NavItem {
  to: string
  icon: React.ComponentType<{ size?: number; className?: string }>
  label: string
  highlight?: boolean
}

export const navItems: NavItem[] = [
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

export function getPageTitle(pathname: string): string {
  // Exact match
  const item = navItems.find((item) => item.to === pathname)
  if (item) {
    return item.label
  }

  // Handle nested routes or fallback
  if (pathname.startsWith('/organize')) return 'Organize'
  if (pathname.startsWith('/triage')) return 'Triage Center'
  if (pathname.startsWith('/search')) return 'Search'
  if (pathname.startsWith('/veo')) return 'VEO Studio'
  if (pathname.startsWith('/analysis')) return 'Analysis'
  if (pathname.startsWith('/duplicates')) return 'Duplicates'
  if (pathname.startsWith('/forensic-vault')) return 'Forensic Vault'
  if (pathname.startsWith('/rollback')) return 'Rollback Center'
  if (pathname.startsWith('/settings')) return 'Settings'

  return 'Dashboard'
}
