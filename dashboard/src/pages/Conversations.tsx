import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, Message } from '../lib/api'
import { ConversationTimeline } from '../components/ConversationTimeline'
import { IconSearch } from '../components/Icon'

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
    <div className="space-y-5 animate-fade-in pb-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Conversas</h1>
        <p className="text-sm text-gray-400 mt-0.5">Histórico de mensagens com o agente Lara</p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
            <IconSearch className="w-4 h-4" />
          </span>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="Número de telefone (ex: 5511999999999)"
            className="input pl-9"
          />
        </div>
        <button onClick={search} className="btn-primary">
          Buscar
        </button>
      </div>

      {loading && (
        <div className="card space-y-3">
          {[1,2,3].map(i => (
            <div key={i} className={`flex gap-3 ${i % 2 === 0 ? 'justify-end' : ''}`}>
              <div className="skeleton h-10 w-3/5 rounded-2xl" style={{ animationDelay: `${i * 0.15}s` }}/>
            </div>
          ))}
        </div>
      )}
      {error && (
        <div className="card border-red-100 bg-red-50">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
      {messages && messages.length === 0 && (
        <div className="card text-center py-10">
          <p className="text-sm text-gray-400">Nenhuma mensagem encontrada para este número.</p>
        </div>
      )}
      {messages && messages.length > 0 && (
        <div className="card max-h-[70vh] overflow-y-auto animate-fade-in-up">
          <ConversationTimeline messages={messages} />
        </div>
      )}
    </div>
  )
}
