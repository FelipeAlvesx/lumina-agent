import { useNavigate } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { api, Lead } from '../lib/api'
import { useFetch } from '../hooks/useFetch'
import { DataTable, Column } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'

export function Contacts() {
  const { data } = useFetch(() => api.getLeads({ limit: 200 }))
  const navigate = useNavigate()

  const columns: Column<Lead>[] = [
    {
      header: 'Nome',
      accessor: (r) => (
        <button
          className="font-medium text-primary hover:underline text-left"
          onClick={() => navigate(`/conversations?phone=${encodeURIComponent(r.phone)}`)}
        >
          {r.nome ?? '(sem nome)'}
        </button>
      ),
    },
    { header: 'Telefone', accessor: (r) => <span className="text-gray-500">{r.phone}</span> },
    { header: 'Procedimento', accessor: (r) => r.procedimento_interesse ?? '—' },
    { header: 'Indicação', accessor: (r) => r.indicacao ?? '—' },
    { header: 'Status', accessor: (r) => <StatusBadge status={r.qualified ? 'qualified' : 'new'} /> },
    {
      header: 'Criado em',
      accessor: (r) => format(parseISO(r.created_at), "d MMM yyyy", { locale: ptBR }),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Contatos</h1>
        {data && (
          <span className="text-sm text-gray-400">
            {data.length} lead{data.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      <DataTable
        columns={columns}
        rows={data ?? []}
        keyFn={(r) => r.id}
        emptyMessage="Nenhum lead registrado ainda."
      />
    </div>
  )
}
