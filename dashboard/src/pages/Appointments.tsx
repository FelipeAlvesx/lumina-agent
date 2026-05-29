import { useState } from 'react'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { api, Appointment } from '../lib/api'
import { useFetch } from '../hooks/useFetch'
import { DataTable, Column } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'

const STATUS_OPTIONS = ['', 'pending', 'confirmed', 'rejected', 'cancelled'] as const
const STATUS_LABELS: Record<string, string> = {
  '': 'Todos',
  pending: 'Pendentes',
  confirmed: 'Confirmados',
  rejected: 'Rejeitados',
  cancelled: 'Cancelados',
}

export function Appointments() {
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState<number | null>(null)

  const { data, refetch } = useFetch(() => api.getAppointments({ status: status || undefined }))

  async function act(id: number, action: 'confirm' | 'reject') {
    setBusy(id)
    try {
      if (action === 'confirm') await api.confirmAppointment(id)
      else await api.rejectAppointment(id)
      refetch()
    } finally {
      setBusy(null)
    }
  }

  const columns: Column<Appointment>[] = [
    { header: 'Cliente', accessor: (r) => <span className="font-medium">{r.nome ?? r.phone}</span> },
    { header: 'Telefone', accessor: (r) => <span className="text-gray-500">{r.phone}</span> },
    { header: 'Procedimento', accessor: (r) => r.procedure },
    {
      header: 'Data/Hora',
      accessor: (r) => format(parseISO(r.datetime), "d MMM yyyy, HH:mm", { locale: ptBR }),
    },
    { header: 'Status', accessor: (r) => <StatusBadge status={r.status} /> },
    {
      header: 'Ações',
      accessor: (r) =>
        r.status === 'pending' ? (
          <div className="flex gap-2">
            <button
              onClick={() => act(r.id, 'confirm')}
              disabled={busy === r.id}
              className="btn-primary py-1 text-xs"
            >
              Confirmar
            </button>
            <button
              onClick={() => act(r.id, 'reject')}
              disabled={busy === r.id}
              className="btn-ghost py-1 text-xs text-red-500"
            >
              Rejeitar
            </button>
          </div>
        ) : null,
    },
  ]

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Agendamentos</h1>

      <div className="flex gap-2 flex-wrap">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              status === s
                ? 'bg-primary text-white'
                : 'bg-surface border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {STATUS_LABELS[s]}
          </button>
        ))}
      </div>

      <DataTable
        columns={columns}
        rows={data ?? []}
        keyFn={(r) => r.id}
        emptyMessage="Nenhum agendamento encontrado."
      />
    </div>
  )
}
