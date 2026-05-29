# Lumina Agent

WhatsApp AI assistant for an aesthetic clinic demo. Agent "Lara" (Claude-backed) qualifies leads, checks availability via Google Calendar, and books appointments. A React dashboard lets receptionists manage appointments in real time.

## Stack

- **Backend:** Python 3.11 + Flask, Anthropic Claude, SQLite
- **Frontend:** React 18 + Vite + TypeScript + Tailwind + Recharts
- **WhatsApp:** Evolution API v1.8.2
- **Infrastructure:** Docker Compose (5 services)

## Commands

```bash
make setup          # Verify prerequisites + create .env
make up             # Start all Docker services
make down           # Stop all services
make webhook        # Register webhook URL with Evolution API
make test           # Run golden + smoke tests
make test-golden    # Run full AI conversation scenarios (needs agent running)
make smoke          # Health checks only (no Claude calls)
make logs           # Follow all service logs
make dev-dashboard  # Hot-reload React dev server on :5173
```

## Services & Ports

| Service     | Port  | Description                                  |
|-------------|-------|----------------------------------------------|
| agent       | 3000  | Flask: POST /webhook, GET/POST /api/*        |
| dashboard   | 80    | Nginx (prod) or Vite on :5173 (dev)          |
| evolution   | 8080  | WhatsApp API (atendai/evolution-api:v1.8.2)  |

## Environment Setup

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...
EVOLUTION_API_KEY=...
EVOLUTION_INSTANCE=lumina-demo
AGENT_WEBHOOK_URL=http://agent:3000  # ngrok URL for local dev
GOOGLE_CREDENTIALS_PATH=./credentials/google_credentials.json
GOOGLE_CALENDAR_ID=...@gmail.com
VITE_API_URL=http://localhost:3000
```

Google OAuth credentials go in `credentials/` (never committed).

## Architecture

Message flow:

```
WhatsApp → Evolution API (:8080)
  → POST /webhook (main.py)
    → dedup (24h) + debounce (4s)
      → agent_core.py (Claude loop, max 5 tool iterations)
        → verticals/estetica/tools.py (tool execution)
          → sessions.py (SQLite), gcal.py (availability)
      → evolution.py (send reply)
```

System prompt is assembled in layers (`prompt_builder.py`): engine rules → persona → vertical fragment → tenant extra rules → RAG context → lead/appointment state → current time.

## Key Files

| File | Purpose |
|------|---------|
| `agent/agent_core.py` | Claude loop + context assembly (RAG, lead state, appointments) |
| `agent/sessions.py` | SQLite models: Lead, Appointment, Conversation |
| `agent/api.py` | REST API for dashboard (`/api/stats`, `/api/leads`, `/api/appointments/*`) |
| `verticals/estetica/tools.py` | Claude tool implementations (`save_lead_field`, `list_available_slots`, `create_pending_appointment`, `escalate_to_human`) |
| `tenants/lumina.yaml` | All business config: hours, procedures, agent persona, integrations |
| `knowledge/*.md` | RAG source: `servicos.md`, `faq.md`, `cuidados.md` |
| `prompts/base/` | `engine_rules.md` + `human_persona.md` |
| `tests/runner.py` | Golden test executor: sends messages via `/api/test/message`, validates tool calls |

## Adding a New Vertical

1. Create `verticals/<name>/` with `tools.py`, `prompt_fragment.md`, `notifications.py`
2. Add a new tenant YAML in `tenants/` pointing to the vertical
3. Mount the tenant config in `docker-compose.yml`

## Testing Locally Without WhatsApp

The agent exposes `/api/test/message` for sending messages directly via HTTP — no Evolution API or phone needed:

```bash
curl -X POST http://localhost:3000/api/test/message \
  -H "Content-Type: application/json" \
  -d '{"phone": "5511999999999", "message": "Olá, quero agendar um procedimento"}'
```

This is the fastest dev loop: `make up` → send curl → check response.

## Logs

The project uses `structlog` with structured JSON output. Key fields: `lead_id`, `tool_name`, `tool_result`, `session_id`.

```bash
make logs                          # All services
make logs | jq '.message'          # Just log messages
make logs | jq 'select(.tool_name)'  # Only tool calls
```

## Non-obvious Behaviors

- **Debounce:** Rapid messages from the same user are batched into one (4s window) before being sent to Claude.
- **Message splitting:** Agent replies containing `---` are sent as separate WhatsApp bubbles.
- **Tool loop:** Claude can call tools up to 5 times per message before the loop breaks.
- **Dashboard polling:** React fetches via `useFetch` every 30s — no WebSocket.
- **SQLite backups:** Automatic daily backup at 2 AM via the `backup` container.
