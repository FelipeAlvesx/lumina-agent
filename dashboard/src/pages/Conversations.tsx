import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, Message } from '../lib/api'
import { ConversationTimeline } from '../components/ConversationTimeline'

export function Conversations() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [phone, setPhone] = useState(searchParams.get('phone') ?? '')
  const [input, setInput] = useState(searchParams.get('phone') ?? '')
  const [messages, setMessages] = useState<Message[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!phone) return
    setLoading(true)
    setError(null)
    api
      .getConversation(phone)
      .then(setMessages)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [phone])

  function search() {
    const trimmed = input.trim()
    if (!trimmed) return
    setPhone(trimmed)
    setSearchParams({ phone: trimmed })
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900">Conversas</h1>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Número de telefone (ex: 5511999999999)"
          className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
        <button onClick={search} className="btn-primary">
          Buscar
        </button>
      </div>

      {loading && <p className="text-sm text-gray-400">Carregando...</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}
      {messages && messages.length === 0 && (
        <p className="text-sm text-gray-400">Nenhuma mensagem encontrada para este número.</p>
      )}
      {messages && messages.length > 0 && (
        <div className="card max-h-[70vh] overflow-y-auto">
          <ConversationTimeline messages={messages} />
        </div>
      )}
    </div>
  )
}
