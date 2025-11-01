import SystemStatusCard from '../components/dashboard/SystemStatusCard'
import QuickActionPanel from '../components/dashboard/QuickActionPanel'
import RecentActivityFeed from '../components/dashboard/RecentActivityFeed'
import MetricsGrid from '../components/dashboard/MetricsGrid'

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Dashboard</h1>

      {/* Top row: Status + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SystemStatusCard />
        <QuickActionPanel />
      </div>

      {/* Metrics Grid */}
      <MetricsGrid />

      {/* Recent Activity */}
      <RecentActivityFeed />
    </div>
  )
}
