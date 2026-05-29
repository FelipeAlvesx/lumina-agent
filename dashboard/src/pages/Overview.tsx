import { useState, useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, PieChart, Pie,
} from 'recharts'
import { format, parseISO, subDays, isWithinInterval, startOfDay, endOfDay, getDay, getHours } from 'date-fns'
import { api } from '../lib/api'
import { useFetch } from '../hooks/useFetch'
import { StatCard } from '../components/StatCard'
import { IconUsers, IconCalendar, IconClock, IconTrendUp } from '../components/Icon'

type Period = 'today' | 'yesterday' | '7d' | '30d' | 'prev' | 'year'

const PERIOD_LABELS: Record<Period, string> = {
  today:     'Hoje',
  yesterday: 'Ontem',
  '7d':      'Últimos 7 dias',
  '30d':     'Este mês',
  prev:      'Mês passado',
  year:      'Este ano',
}

const COLORS = ['#7C3D6E', '#C5A87D', '#9B5089', '#D4BB99', '#5E2D53', '#2D6E7C']

function getPeriodInterval(p: Period): { start: Date; end: Date } {
  const now = new Date()
  switch (p) {
    case 'today':     return { start: startOfDay(now), end: endOfDay(now) }
    case 'yesterday': return { start: startOfDay(subDays(now, 1)), end: endOfDay(subDays(now, 1)) }
    case '7d':        return { start: startOfDay(subDays(now, 6)), end: endOfDay(now) }
    case '30d':       return { start: startOfDay(subDays(now, 29)), end: endOfDay(now) }
    case 'prev':      return { start: startOfDay(subDays(now, 59)), end: endOfDay(subDays(now, 30)) }
    case 'year':      return { start: startOfDay(subDays(now, 364)), end: endOfDay(now) }
  }
}

function isCommercialHour(d: Date) {
  const day = getDay(d) // 0=Sun
  const h   = getHours(d)
  return day >= 1 && day <= 6 && h >= 9 && h < 19
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-100 shadow-lg rounded-xl px-3 py-2 text-xs">
      <p className="font-semibold text-gray-600 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-medium">
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

export function Overview() {
  const [period, setPeriod] = useState<Period>('30d')
  const { data: leads }        = useFetch(() => api.getLeads({ limit: 500 }))
  const { data: appointments } = useFetch(() => api.getAppointments())

  const interval = getPeriodInterval(period)

  const filteredLeads = useMemo(
    () => leads?.filter(l => {
      try { return isWithinInterval(parseISO(l.created_at), interval) } catch { return false }
    }) ?? [],
    [leads, interval]
  )

  const filteredApts = useMemo(
    () => appointments?.filter(a => {
      try { return isWithinInterval(parseISO(a.datetime), interval) } catch { return false }
    }) ?? [],
    [appointments, interval]
  )

  /* Commercial hours */
  const { commercial, afterHours } = useMemo(() => {
    let commercial = 0, afterHours = 0
    for (const l of filteredLeads) {
      try {
        if (isCommercialHour(parseISO(l.created_at))) commercial++
        else afterHours++
      } catch { /* skip */ }
    }
    return { commercial, afterHours }
  }, [filteredLeads])

  const commercialPct = filteredLeads.length > 0
    ? Math.round((commercial / filteredLeads.length) * 100) : 0

  /* Activity line chart — contacts per day */
  const activityData = useMemo(() => {
    const days: Record<string, number> = {}
    for (const l of leads ?? []) {
      try {
        const key = format(parseISO(l.created_at), 'dd/MM')
        days[key] = (days[key] ?? 0) + 1
      } catch { /* skip */ }
    }
    return Object.entries(days).slice(-30).map(([date, total]) => ({ date, total }))
  }, [leads])

  /* Top procedures */
  const procedureData = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const l of filteredLeads) {
      if (l.procedimento_interesse)
        counts[l.procedimento_interesse] = (counts[l.procedimento_interesse] ?? 0) + 1
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value]) => ({ name, value }))
  }, [filteredLeads])

  /* Apt status pie */
  const statusPieData = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const a of filteredApts) counts[a.status] = (counts[a.status] ?? 0) + 1
    const labelMap: Record<string, string> = {
      pending: 'Pendentes', confirmed: 'Confirmados',
      rejected: 'Rejeitados', cancelled: 'Cancelados',
    }
    return Object.entries(counts).map(([status, value]) => ({ name: labelMap[status] ?? status, value }))
  }, [filteredApts])

  /* Donut for commercial hours */
  const donutData = [
    { name: 'Horário comercial', value: commercial || 0 },
    { name: 'Fora do horário',   value: afterHours || 0 },
  ]
  const DONUT_COLORS = ['#7C3D6E', '#C5A87D']

  return (
    <div className="space-y-6 animate-fade-in pb-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-400 mt-0.5">Visão geral do negócio</p>
        </div>
      </div>

      {/* Period tabs */}
      <div className="flex gap-1.5 flex-wrap">
        {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={period === p ? 'tab-btn-active' : 'tab-btn-inactive'}
          >
            {PERIOD_LABELS[p]}
          </button>
        ))}
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger">
        <StatCard
          label="Clientes no período"
          subtitle="Contatos registrados"
          value={filteredLeads.length}
          trend={{ pct: 18 }}
          icon={<IconUsers className="w-5 h-5" />}
          delay={0}
        />
        <StatCard
          label="Agendamentos"
          subtitle="Total no período"
          value={filteredApts.length}
          trend={{ pct: 12 }}
          icon={<IconCalendar className="w-5 h-5" />}
          delay={80}
        />
        <StatCard
          label="Confirmados"
          subtitle="Agendamentos confirmados"
          value={filteredApts.filter(a => a.status === 'confirmed').length}
          trend={{ pct: 5.2 }}
          icon={<IconTrendUp className="w-5 h-5" />}
          delay={160}
        />
        <StatCard
          label="Horário comercial"
          subtitle={`${afterHours} fora do horário`}
          value={`${commercialPct}%`}
          trend={{ pct: 3.1 }}
          icon={<IconClock className="w-5 h-5" />}
          delay={240}
        />
      </div>

      {/* Charts row 1 */}
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-2 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          <h2 className="text-sm font-semibold text-gray-700 mb-1">Contatos ao longo do tempo</h2>
          <p className="text-xs text-gray-400 mb-4">Novos contatos por dia</p>
          {activityData.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-sm text-gray-300">Sem dados ainda</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={activityData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#7C3D6E" stopOpacity={0.25}/>
                    <stop offset="100%" stopColor="#7C3D6E" stopOpacity={0.03}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} interval="preserveStartEnd"/>
                <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} allowDecimals={false}/>
                <Tooltip content={<CustomTooltip />}/>
                <Area type="monotone" dataKey="total" name="Contatos" stroke="#7C3D6E" strokeWidth={2} fill="url(#grad)" dot={false} activeDot={{ r: 4, fill: '#7C3D6E', strokeWidth: 0 }}/>
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card animate-fade-in-up" style={{ animationDelay: '160ms' }}>
          <h2 className="text-sm font-semibold text-gray-700 mb-1">Por turno</h2>
          <p className="text-xs text-gray-400 mb-4">Horário comercial vs fora</p>
          {filteredLeads.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-sm text-gray-300">Sem dados</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={donutData}
                    cx="50%" cy="50%"
                    innerRadius={48} outerRadius={72}
                    dataKey="value"
                    paddingAngle={3}
                    isAnimationActive
                    animationBegin={200}
                    animationDuration={800}
                  >
                    {donutData.map((_, i) => (
                      <Cell key={i} fill={DONUT_COLORS[i]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />}/>
                </PieChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-4 mt-2">
                {donutData.map((d, i) => (
                  <div key={d.name} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: DONUT_COLORS[i] }}/>
                    <span className="text-xs text-gray-500">{d.name}</span>
                    <span className="text-xs font-semibold text-gray-700">{d.value}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card animate-fade-in-up" style={{ animationDelay: '200ms' }}>
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Procedimentos mais solicitados</h2>
          {procedureData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-sm text-gray-300">Sem dados ainda</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={procedureData} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                <XAxis type="number" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} allowDecimals={false}/>
                <YAxis dataKey="name" type="category" width={160} tick={{ fontSize: 11, fill: '#374151' }} axisLine={false} tickLine={false}/>
                <Tooltip content={<CustomTooltip />}/>
                <Bar dataKey="value" name="Contatos" radius={[0, 6, 6, 0]} isAnimationActive animationBegin={300} animationDuration={800}>
                  {procedureData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card animate-fade-in-up" style={{ animationDelay: '260ms' }}>
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Status dos agendamentos</h2>
          {statusPieData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-sm text-gray-300">Sem agendamentos</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={statusPieData}
                    cx="50%" cy="50%"
                    outerRadius={78}
                    dataKey="value"
                    paddingAngle={2}
                    isAnimationActive
                    animationBegin={300}
                    animationDuration={800}
                    label={({ percent }) => `${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {statusPieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />}/>
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap justify-center gap-3 mt-1">
                {statusPieData.map((d, i) => (
                  <div key={d.name} className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }}/>
                    <span className="text-xs text-gray-500">{d.name}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
