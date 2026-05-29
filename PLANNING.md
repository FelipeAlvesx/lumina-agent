# Lumina Agent — Planejamento Completo

> Demo de agente IA para WhatsApp · Clínica Estética · Stack: Python + Evolution API + Claude + React

---

## 1. Visão Geral

**Caso de uso:** Lumina Clínica Estética — agente chamado **Lara** que atende pelo WhatsApp, qualifica leads, consulta agenda (Google Calendar) e agenda procedimentos estéticos. O CRM dashboard (React) exibe em tempo real os contatos, agendamentos e métricas gerados pelo agente.

**Objetivos deste projeto vs. falkon-agent-setup:**

| Ponto                  | falkon-agent-setup          | lumina-agent                        |
|------------------------|-----------------------------|--------------------------------------|
| Dashboard              | HTML único de 1380 linhas   | React + Vite, componentes separados  |
| Setup inicial          | Manual, vários passos       | `make setup` — um comando            |
| Testes                 | Scripts soltos              | Framework YAML padronizado           |
| Organização do agente  | Dependências cruzadas       | Camadas bem definidas                |

---

## 2. Estrutura de Pastas

```
lumina-agent/
├── agent/                        # Serviço Python/Flask
│   ├── main.py                   # Webhook + scheduler
│   ├── agent_core.py             # Loop Claude com tool use
│   ├── config.py                 # Loader YAML do tenant
│   ├── sessions.py               # SQLite: histórico, leads, agendamentos
│   ├── prompt_builder.py         # Monta system prompt em camadas
│   ├── evolution.py              # Cliente Evolution API
│   ├── gcal.py                   # Cliente Google Calendar
│   ├── rag.py                    # Busca semântica no knowledge/
│   ├── api.py                    # Rotas REST /api/* para o dashboard
│   ├── requirements.txt
│   └── Dockerfile
│
├── dashboard/                    # React + Vite
│   ├── src/
│   │   ├── components/           # Componentes reutilizáveis (Card, Chart, Badge…)
│   │   ├── pages/                # Overview, Agendamentos, Contatos, Conversas, Métricas
│   │   ├── hooks/                # useFetch, useRealtime
│   │   ├── lib/                  # api.ts (chamadas REST ao agente)
│   │   └── App.tsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── verticals/
│   └── estetica/
│       ├── __init__.py
│       ├── tools.py              # Definições e executor das tools
│       ├── prompt_fragment.md    # Fragmento de prompt específico da vertical
│       └── receptionist.py      # Comandos da recepcionista humana
│
├── tenants/
│   ├── schema.yaml               # Documentação dos campos
│   └── lumina.yaml               # Config da clínica demo
│
├── knowledge/
│   ├── servicos.md               # Catálogo de procedimentos e preços
│   ├── faq.md                    # Perguntas frequentes
│   └── cuidados.md               # Cuidados pré/pós procedimento
│
├── prompts/
│   └── base/
│       ├── human_persona.md      # Tom de voz e personalidade da Lara
│       └── engine_rules.md       # Regras gerais de comportamento e tools
│
├── tests/
│   ├── golden/                   # Um .yaml por cenário de conversa
│   │   ├── 01_qualificacao.yaml
│   │   ├── 02_agendamento.yaml
│   │   ├── 03_remarcacao.yaml
│   │   └── 04_escalada.yaml
│   ├── runner.py                 # Executa golden tests e reporta diff
│   └── smoke.sh                  # Health checks básicos
│
├── setup/
│   ├── check_prerequisites.py    # Verifica Docker, portas, env vars
│   └── configure_webhook.py      # Registra webhook na Evolution API
│
├── credentials/
│   └── .gitignore                # Nunca commitar credenciais
│
├── .env.example                  # Todas as variáveis necessárias documentadas
├── docker-compose.yml
├── Makefile                      # Comandos padronizados
└── README.md                     # Onboarding em < 5 minutos
```

---

## 3. Arquitetura do Agente

### 3.1 Camadas (sem dependências cruzadas)

```
┌─────────────────────────────────────┐
│  main.py  (HTTP + scheduler)        │  ← só importa agent_core, evolution, sessions
├─────────────────────────────────────┤
│  agent_core.py  (loop Claude)       │  ← só importa sessions, config, evolution, verticals
├─────────────────────────────────────┤
│  verticals/estetica/tools.py        │  ← só importa sessions, gcal, config
├─────────────────────────────────────┤
│  sessions.py  (SQLite)              │  ← sem imports internos
│  gcal.py      (Google Cal)          │  ← sem imports internos
│  evolution.py (WhatsApp)            │  ← sem imports internos
│  config.py    (YAML loader)         │  ← sem imports internos
└─────────────────────────────────────┘
```

### 3.2 Fluxo de uma mensagem

```
WhatsApp → Evolution API → POST /webhook
  → dedup (24h cache)
  → debounce (4s, combina mensagens rápidas)
  → process_message() em thread separada
      → RAG context
      → lead context + appointments context + temporal context
      → loop Claude com tools (máx 5 iterações)
      → _split_and_send() — balões separados por ---
```

### 3.3 Diferencial: api.py (novo)

O agente expõe `/api/*` para o dashboard React. Isso evita que o dashboard acesse o SQLite diretamente e mantém o backend como única fonte de verdade.

```
GET  /api/stats          → métricas gerais (leads, agendamentos, escaladas)
GET  /api/leads          → lista de contatos qualificados
GET  /api/appointments   → agendamentos com filtros de status/data
GET  /api/conversations  → histórico de conversa por telefone
POST /api/appointments/:id/confirm   → recepcionista confirma
POST /api/appointments/:id/reject    → recepcionista rejeita
```

---

## 4. Vertical: Estética

### 4.1 Lead fields
`nome`, `procedimento_interesse`, `indicacao` (quem indicou ou como chegou)

### 4.2 Tools do agente

| Tool | Descrição |
|------|-----------|
| `save_lead_field` | Salva campo de qualificação |
| `mark_lead_complete` | Sinaliza lead completo |
| `list_available_slots` | Consulta horários livres no Google Calendar |
| `create_pending_appointment` | Cria agendamento pendente + notifica recepcionista |
| `reschedule_appointment` | Solicita remarcação |
| `cancel_appointment` | Solicita cancelamento |
| `escalate_to_human` | Passa para recepcionista humana |

### 4.3 Lumina — config do tenant (`tenants/lumina.yaml`)

```yaml
tenant_id: lumina
vertical: estetica

business:
  name: Lumina Clínica Estética
  segment: Clínica de estética avançada e dermatologia cosmética
  address: "Av. das Flores 1200, Sala 304 — Jardins, São Paulo/SP"
  timezone: America/Sao_Paulo
  hours: "segunda a sábado, das 9h às 19h."

agent:
  name: Lara
  role: consultora de agendamentos

integrations:
  evolution:
    instance: "lumina-demo"
  human_phone: "11999999999"
  google_calendar:
    calendar_id: "..."
    slot_duration_minutes: 60

vertical_config:
  lead_fields: [nome, procedimento_interesse, indicacao]
  procedures:
    - Limpeza de pele
    - Peeling químico
    - Botox
    - Preenchimento labial
    - Laser CO2
    - Microagulhamento
    - Fio de sustentação
    - Skinbooster
    - Luz intensa pulsada (LIP)
    - Bioestimulador de colágeno
  payment_methods:
    - Cartão de crédito (até 12x)
    - PIX
    - Particular

knowledge:
  extra_faq:
    - q: "Precisa de consulta antes?"
      a: "Sim, sempre iniciamos com uma avaliação gratuita com nossa especialista."
    - q: "Tem lista de espera?"
      a: "Sim! Me passa seus dados e entro em contato assim que abrir uma vaga."
```

---

## 5. CRM Dashboard (React + Vite)

### 5.1 Design System

Mantém a linguagem visual do falkon-agent-setup, refinada:

```
Cores primárias:  #7C3D6E (roxo estético) + #C5A87D (dourado)
Background:       #F0EFEC (bege quente)
Surfaces:         #FFFFFF / #FAFAF8
Bordas:           #E8E6E1
Texto:            #1A1918 / #615D57 / #9C978F
Status OK:        #2E7D52  Warn: #7A5500  Error: #B83535
Font:             Inter (Google Fonts)
Animações:        transitions 200ms ease + skeleton loaders
```

### 5.2 Páginas

| Rota | Página | Conteúdo |
|------|--------|----------|
| `/` | Overview | KPIs do dia, últimos agendamentos, últimos leads |
| `/appointments` | Agendamentos | Tabela com filtros de status; confirmar/rejeitar inline |
| `/contacts` | Contatos | Lista de leads com qualificação e histórico |
| `/conversations` | Conversas | Timeline de mensagens por contato |
| `/metrics` | Métricas | Gráficos: volume, taxa de conversão, procedimentos |

### 5.3 Componentes reutilizáveis

```
src/components/
├── Sidebar.tsx
├── StatCard.tsx
├── DataTable.tsx
├── StatusBadge.tsx
├── ConversationTimeline.tsx
├── AppointmentCard.tsx
└── charts/
    ├── VolumeChart.tsx
    └── ConversionFunnel.tsx
```

### 5.4 Comunicação com o agente

```typescript
// src/lib/api.ts
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:3000'

export const api = {
  stats: () => fetch(`${BASE}/api/stats`).then(r => r.json()),
  leads: (params?) => fetch(`${BASE}/api/leads?${qs(params)}`).then(r => r.json()),
  appointments: (params?) => fetch(`${BASE}/api/appointments?${qs(params)}`).then(r => r.json()),
  conversations: (phone: string) => fetch(`${BASE}/api/conversations/${phone}`).then(r => r.json()),
  confirmAppointment: (id: number) => fetch(`${BASE}/api/appointments/${id}/confirm`, {method: 'POST'}),
  rejectAppointment: (id: number) => fetch(`${BASE}/api/appointments/${id}/reject`, {method: 'POST'}),
}
```

Polling a cada 30s para dados "ao vivo" (sem WebSocket por ora).

---

## 6. Docker Compose

```yaml
services:
  evolution:     # Evolution API v1 — WhatsApp
  patcher:       # One-shot: aplica patch @lid
  agent:         # Flask na porta 3000 (webhook + API REST)
  dashboard:     # Nginx servindo o build React (porta 5173 dev / 80 prod)
  backup:        # Alpine: backup diário do SQLite
```

O dashboard em **desenvolvimento** roda via `npm run dev` (Vite HMR).  
Em **produção/demo**, o Dockerfile faz `npm run build` e serve via Nginx.

---

## 7. Makefile — Interface Padrão

```makefile
make setup        # Verifica pré-requisitos + copia .env.example
make up           # docker compose up -d
make down         # docker compose down
make logs         # docker compose logs -f agent
make test         # Roda golden tests + smoke tests
make test-golden  # Só golden tests
make webhook      # Registra webhook na Evolution API
make shell        # Entra no container do agente
make backup       # Dispara backup manual do SQLite
make reset-db     # Apaga o banco (dev only — pede confirmação)
```

---

## 8. Framework de Testes

### 8.1 Golden tests (YAML)

```yaml
# tests/golden/02_agendamento.yaml
name: Agendamento completo com dados já coletados
messages:
  - role: user
    text: "Oi, quero agendar uma limpeza de pele"
  - role: agent
    expect_tool_calls:
      - save_lead_field
  - role: user
    text: "Me chamo Ana, fui indicada pela minha amiga"
  - role: agent
    expect_tool_calls:
      - save_lead_field
      - mark_lead_complete
  - role: user
    text: "Pode ser semana que vem de manhã?"
  - role: agent
    expect_tool_calls:
      - list_available_slots
  - role: user
    text: "Segunda às 9h serve"
  - role: agent
    expect_tool_calls:
      - create_pending_appointment
    expect_text_contains: "registrei"
```

### 8.2 Smoke tests

```bash
# tests/smoke.sh
curl -f http://localhost:3000/health
curl -f http://localhost:3000/api/stats
curl -f http://localhost:5173           # dashboard
```

---

## 9. Fases de Implementação

### Fase 1 — Esqueleto do projeto (1 sessão)
- [ ] Criar estrutura de pastas completa
- [ ] `docker-compose.yml` com todos os serviços
- [ ] `Makefile` com comandos básicos
- [ ] `.env.example` completo e comentado
- [ ] `tenants/lumina.yaml` com config da Lumina

### Fase 2 — Agente core (1-2 sessões)
- [ ] Copiar e refatorar `agent/` do falkon (camadas limpas)
- [ ] Implementar `verticals/estetica/tools.py`
- [ ] Implementar `prompts/` e `knowledge/` para a Lumina
- [ ] Implementar `agent/api.py` com rotas REST
- [ ] Google Calendar integrado e testado

### Fase 3 — Dashboard React (1-2 sessões)
- [ ] Setup Vite + React + TypeScript + Tailwind
- [ ] Design system (tokens CSS fiéis ao falkon)
- [ ] Sidebar + roteamento
- [ ] Página Overview com KPIs reais
- [ ] Página Agendamentos (tabela + confirmar/rejeitar)
- [ ] Página Contatos
- [ ] Página Conversas
- [ ] Página Métricas com Chart.js

### Fase 4 — Testes e polish (1 sessão)
- [ ] Golden tests para os 4 cenários principais
- [ ] Smoke tests no Makefile
- [ ] README com onboarding em < 5 minutos
- [ ] Testar fluxo completo ponta a ponta

---

## 10. Decisões de Arquitetura Relevantes

**Por que `api.py` separado do `main.py`?**
Mantém o webhook handler focado em receber mensagens, e a API REST focada em servir o dashboard. Mais fácil de testar cada um isoladamente.

**Por que polling e não WebSocket no dashboard?**
Para um demo funcional, polling a cada 30s é suficiente e elimina complexidade. WebSocket pode ser adicionado depois sem reescrever o frontend.

**Por que React em vez de HTML puro?**
O dashboard do falkon cresceu para 1380 linhas em um arquivo impossível de manter. Com React, cada página/componente tem seu arquivo. Adicionar uma nova seção não exige abrir um arquivo monolítico.

**Por que manter SQLite?**
Zero overhead de infraestrutura, funciona no `docker volume`, tem backup atômico com WAL mode. Para um demo (e até produção pequena), é suficiente e simples de operar.
