type Status = 'pending' | 'confirmed' | 'rejected' | 'cancelled' | 'qualified' | 'new'

const styles: Record<Status, string> = {
  pending: 'bg-amber-100 text-amber-700',
  confirmed: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-600',
  qualified: 'bg-purple-100 text-purple-700',
  new: 'bg-blue-100 text-blue-700',
}

const labels: Record<Status, string> = {
  pending: 'Pendente',
  confirmed: 'Confirmado',
  rejected: 'Rejeitado',
  cancelled: 'Cancelado',
  qualified: 'Qualificado',
  new: 'Novo',
}

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`badge ${styles[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {labels[status] ?? status}
    </span>
  )
}
