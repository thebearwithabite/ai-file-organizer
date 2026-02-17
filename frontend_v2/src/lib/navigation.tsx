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

export const navItems = [
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
  // Handle root specifically
  if (pathname === '/') return 'Dashboard';

  // Find matching route
  const item = navItems.find(item => item.to !== '/' && pathname.startsWith(item.to));
  return item ? item.label : 'Dashboard';
}
