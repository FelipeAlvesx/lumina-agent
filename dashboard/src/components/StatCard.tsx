interface Props {
  label: string
  value: string | number
  sub?: string
  accent?: boolean
}

export function StatCard({ label, value, sub, accent }: Props) {
  return (
    <div className={`card flex flex-col gap-1 ${accent ? 'border-l-4 border-l-primary' : ''}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  )
}
