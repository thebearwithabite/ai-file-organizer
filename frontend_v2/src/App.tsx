import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy } from 'react'
import Layout from './components/layout/Layout'

// Lazy load page components for better performance
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Organize = lazy(() => import('./pages/Organize'))
const Triage = lazy(() => import('./pages/Triage'))
const Search = lazy(() => import('./pages/Search'))
const VeoStudio = lazy(() => import('./pages/VeoStudio'))
const Analysis = lazy(() => import('./pages/Analysis'))
const RollbackCenter = lazy(() => import('./pages/RollbackCenter'))
const Settings = lazy(() => import('./pages/Settings'))
const Duplicates = lazy(() => import('./pages/Duplicates'))

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="organize" element={<Organize />} />
          <Route path="triage" element={<Triage />} />
          <Route path="search" element={<Search />} />
          <Route path="veo" element={<VeoStudio />} />
          <Route path="analysis" element={<Analysis />} />
          <Route path="rollback" element={<RollbackCenter />} />
          <Route path="duplicates" element={<Duplicates />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
