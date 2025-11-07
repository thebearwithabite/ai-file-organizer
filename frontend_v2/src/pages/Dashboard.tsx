import SystemStatusCard from '../components/dashboard/SystemStatusCard'
import QuickActionPanel from '../components/dashboard/QuickActionPanel'
import RecentActivityFeed from '../components/dashboard/RecentActivityFeed'
import MetricsGrid from '../components/dashboard/MetricsGrid'
import DiskSpaceWidget from '../components/dashboard/DiskSpaceWidget'
import MonitorStatusWidget from '../components/dashboard/MonitorStatusWidget'

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Dashboard</h1>

      {/* Top row: Status + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SystemStatusCard />
        <QuickActionPanel />
      </div>

      {/* Second row: Disk Space + Monitor Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DiskSpaceWidget />
        <MonitorStatusWidget />
      </div>

      {/* Metrics Grid */}
      <MetricsGrid />

      {/* Recent Activity */}
      <RecentActivityFeed />
    </div>
  )
}
