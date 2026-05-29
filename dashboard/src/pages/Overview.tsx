import { api } from '../lib/api'
import { useFetch } from '../hooks/useFetch'
import { StatCard } from '../components/StatCard'
import { AppointmentCard } from '../components/AppointmentCard'
import { StatusBadge } from '../components/StatusBadge'

export function Overview() {
  const stats = useFetch(() => api.getStats())
  const appointments = useFetch(() => api.getAppointments({ status: 'pending' }))
  const leads = useFetch(() => api.getLeads({ limit: 5 }))

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Visão Geral</h1>

      {stats.data && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <StatCard label="Sessões" value={stats.data.total_sessions} accent />
          <StatCard label="Leads qualificados" value={stats.data.qualified_leads} accent />
          <StatCard label="Agendamentos" value={stats.data.appointments_scheduled} />
          <StatCard label="Confirmados" value={stats.data.appointments_confirmed} />
          <StatCard label="Escalações" value={stats.data.escalations} />
          <StatCard
            label="Taxa de conversão"
            value={`${(stats.data.conversion_rate * 100).toFixed(1)}%`}
            accent
          />
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        <section>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Agendamentos pendentes</h2>
          {appointments.data?.length === 0 && (
            <p className="text-sm text-gray-400">Nenhum agendamento pendente.</p>
          )}
          <div className="space-y-3">
            {appointments.data?.slice(0, 5).map((apt) => (
              <AppointmentCard key={apt.id} appointment={apt} onUpdate={appointments.refetch} />
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Leads recentes</h2>
          <div className="card divide-y divide-gray-50">
            {leads.data?.length === 0 && (
              <p className="text-sm text-gray-400 py-2">Nenhum lead ainda.</p>
            )}
            {leads.data?.map((lead) => (
              <div key={lead.id} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                <div>
                  <p className="text-sm font-medium text-gray-900">{lead.nome ?? lead.phone}</p>
                  <p className="text-xs text-gray-400">{lead.procedimento_interesse ?? '—'}</p>
                </div>
                <StatusBadge status={lead.qualified ? 'qualified' : 'new'} />
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
