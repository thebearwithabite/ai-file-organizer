import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Organize from './pages/Organize'
import Triage from './pages/Triage'
import Search from './pages/Search'
import VeoStudio from './pages/VeoStudio'
import Analysis from './pages/Analysis'
import RollbackCenter from './pages/RollbackCenter'
import Settings from './pages/Settings'
import Duplicates from './pages/Duplicates'

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
