import { Outlet } from 'react-router-dom'
import { Suspense } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import SystemStateStrip from './SystemStateStrip'
import LoadingSpinner from '../ui/LoadingSpinner'

export default function Layout() {
  return (
    <div className="flex h-screen bg-background overflow-hidden relative font-sans">
      {/* System State Strip - Fixed at top, full width */}
      <div className="absolute top-0 left-0 right-0 z-[60]">
        <SystemStateStrip />
      </div>

      {/* Main Container - Pushed down by strip height */}
      <div className="flex w-full h-full pt-10">
        {/* Sidebar */}
        <Sidebar />

        {/* Main content area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />

          {/* Page content (routes render here) */}
          <main className="flex-1 overflow-y-auto p-6">
            <Suspense fallback={<LoadingSpinner />}>
              <Outlet />
            </Suspense>
          </main>
        </div>
      </div>
    </div>
  )
}
