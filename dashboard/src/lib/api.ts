const BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}

export interface Stats {
  total_sessions: number
  qualified_leads: number
  appointments_scheduled: number
  appointments_confirmed: number
  escalations: number
  conversion_rate: number
}

export interface Lead {
  id: number
  phone: string
  nome: string | null
  procedimento_interesse: string | null
  indicacao: string | null
  qualified: boolean
  created_at: string
}

export interface Appointment {
  id: number
  phone: string
  nome: string | null
  procedure: string
  datetime: string
  status: 'pending' | 'confirmed' | 'rejected' | 'cancelled'
  notes: string | null
  created_at: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export const api = {
  getStats: () => request<Stats>('/api/stats'),

  getLeads: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams()
    if (params?.limit != null) qs.set('limit', String(params.limit))
    if (params?.offset != null) qs.set('offset', String(params.offset))
    return request<Lead[]>(`/api/leads?${qs}`)
  },

  getAppointments: (params?: { status?: string; date_from?: string; date_to?: string }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.date_from) qs.set('date_from', params.date_from)
    if (params?.date_to) qs.set('date_to', params.date_to)
    return request<Appointment[]>(`/api/appointments?${qs}`)
  },

  getConversation: (phone: string) =>
    request<Message[]>(`/api/conversations/${encodeURIComponent(phone)}`),

  confirmAppointment: (id: number) =>
    request<{ ok: boolean }>(`/api/appointments/${id}/confirm`, { method: 'POST' }),

  rejectAppointment: (id: number, reason?: string) =>
    request<{ ok: boolean }>(`/api/appointments/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
}
