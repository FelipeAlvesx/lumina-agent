import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  FunnelChart, Funnel, LabelList, Cell,
  PieChart, Pie, Legend,
} from 'recharts'
import { api } from '../lib/api'
import { useFetch } from '../hooks/useFetch'

const COLORS = ['#7C3D6E', '#C5A87D', '#9B5089', '#D4BB99', '#5E2D53']

export function Metrics() {
  const { data: stats } = useFetch(() => api.getStats())
  const { data: leads } = useFetch(() => api.getLeads({ limit: 500 }))
  const { data: appointments } = useFetch(() => api.getAppointments())

  const funnelData = stats
    ? [
        { name: 'Sessões', value: stats.leads_total, fill: '#7C3D6E' },
        { name: 'Leads qualificados', value: stats.leads_qualified, fill: '#9B5089' },
        { name: 'Agendamentos', value: stats.appointments_total, fill: '#C5A87D' },
        { name: 'Confirmados', value: stats.appointments_confirmed, fill: '#D4BB99' },
      ]
    : []

  const procedureCounts: Record<string, number> = {}
  for (const lead of leads ?? []) {
    if (lead.procedimento_interesse) {
      procedureCounts[lead.procedimento_interesse] = (procedureCounts[lead.procedimento_interesse] ?? 0) + 1
    }
  }
  const procedureData = Object.entries(procedureCounts).map(([name, value]) => ({ name, value }))

  const statusCounts: Record<string, number> = {}
  for (const apt of appointments ?? []) {
    statusCounts[apt.status] = (statusCounts[apt.status] ?? 0) + 1
  }
  const statusData = Object.entries(statusCounts).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Métricas</h1>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Funil de conversão</h2>
          <ResponsiveContainer width="100%" height={260}>
            <FunnelChart>
              <Tooltip />
              <Funnel dataKey="value" data={funnelData} isAnimationActive>
                <LabelList position="right" fill="#374151" stroke="none" dataKey="name" />
              </Funnel>
            </FunnelChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Procedimentos de interesse</h2>
          {procedureData.length === 0 ? (
            <p className="text-sm text-gray-400">Sem dados ainda.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={procedureData} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {procedureData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Status dos agendamentos</h2>
          {statusData.length === 0 ? (
            <p className="text-sm text-gray-400">Sem dados ainda.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {statusData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {stats && (
          <div className="card flex flex-col justify-center items-center gap-2">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Taxa de conversão geral</p>
            <p className="text-5xl font-bold text-primary">
              {(stats.conversion_rate * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-gray-400">sessões → leads qualificados</p>
          </div>
        )}
      </div>
    </div>
  )
}
