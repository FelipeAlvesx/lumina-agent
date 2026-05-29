import { Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Overview } from './pages/Overview'
import { Appointments } from './pages/Appointments'
import { Contacts } from './pages/Contacts'
import { Conversations } from './pages/Conversations'
import { Metrics } from './pages/Metrics'

export default function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/appointments" element={<Appointments />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/conversations" element={<Conversations />} />
          <Route path="/metrics" element={<Metrics />} />
        </Routes>
      </main>
    </div>
  )
}
