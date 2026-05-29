# Lumina Agent

Agente IA para WhatsApp da **Lumina Clínica Estética**.  
Responde mensagens, qualifica leads, consulta agenda e agenda procedimentos — tudo pelo WhatsApp.

**Stack:** Python + Flask · Evolution API · Anthropic Claude · React + Vite · SQLite · Google Calendar

---

## Onboarding em < 5 minutos

### 1. Pré-requisitos

- Docker Desktop instalado e rodando
- Python 3.11+
- Node.js 20+ (somente para desenvolvimento do dashboard)
- Credencial Google Calendar (service account JSON)

Verifique tudo de uma vez:

```bash
make setup
```

### 2. Configure o `.env`

```bash
cp .env.example .env
```

Edite o `.env` e preencha:

| Variável | O que colocar |
|----------|---------------|
| `ANTHROPIC_API_KEY` | Chave da Anthropic (console.anthropic.com) |
| `EVOLUTION_API_KEY` | Chave gerada ao criar a instância Evolution |
| `EVOLUTION_INSTANCE` | Nome da instância (ex: `lumina-demo`) |
| `AGENT_WEBHOOK_URL` | URL pública do agente — use ngrok em dev: `https://xxxx.ngrok.io` |
| `GOOGLE_CALENDAR_ID` | ID do calendário (encontrado em Configurações do Google Calendar) |

Coloque o arquivo `google_credentials.json` em `credentials/`.

### 3. Suba os containers

```bash
make up
```

Aguarde todos os serviços ficarem `healthy` (~30 segundos).

### 4. Conecte o WhatsApp

```bash
make webhook
```

Acesse `http://localhost:8080` → escaneie o QR Code com o WhatsApp Business da clínica.

### 5. Teste a instalação

```bash
make smoke      # health checks rápidos (< 5s)
make test       # golden tests completos (requer agente rodando e ANTHROPIC_API_KEY)
```

---

## Comandos úteis

| Comando | O que faz |
|---------|-----------|
| `make up` | Sobe todos os containers |
| `make down` | Para os containers |
| `make logs` | Logs do agente em tempo real |
| `make logs-all` | Logs de todos os serviços |
| `make dev-dashboard` | Dashboard React com hot-reload local |
| `make test` | Golden tests + smoke tests |
| `make test-golden` | Só os golden tests (cenários de conversa) |
| `make smoke` | Só os health checks básicos |
| `make webhook` | Registra o webhook na Evolution API |
| `make shell` | Terminal dentro do container do agente |
| `make backup` | Backup manual do SQLite |
| `make reset-db` | Apaga o banco (dev only — pede confirmação) |
| `make help` | Lista todos os comandos com descrição |

---

## Dashboard

Acesse em `http://localhost:5173` após `make up`.

| Página | URL | Conteúdo |
|--------|-----|----------|
| Overview | `/` | KPIs do dia, agendamentos e leads recentes |
| Agendamentos | `/appointments` | Tabela com confirmar/rejeitar inline |
| Contatos | `/contacts` | Lista de leads qualificados |
| Conversas | `/conversations` | Timeline de mensagens por contato |
| Métricas | `/metrics` | Gráficos de conversão e procedimentos |

Para desenvolvimento com hot-reload:

```bash
make dev-dashboard
```

---

## Arquitetura

```
lumina-agent/
├── agent/          Python/Flask — webhook, loop Claude com tool use, API REST
├── dashboard/      React + Vite — CRM dashboard
├── verticals/      Lógica por segmento (estetica/tools.py, receptionist.py)
├── tenants/        Configuração do cliente (lumina.yaml)
├── knowledge/      Base de conhecimento (serviços, FAQ, cuidados pré/pós)
├── prompts/        Fragmentos do system prompt (persona, regras)
├── tests/          Golden tests (YAML) + smoke tests
├── setup/          Scripts de verificação e configuração
└── credentials/    Credenciais — NUNCA commitadas
```

### Fluxo de uma mensagem

```
WhatsApp → Evolution API → POST /webhook
  → dedup 24h + debounce 4s
  → RAG (knowledge/)
  → contexto: lead + agendamentos + horário atual
  → loop Claude (máx 5 iterações com tool use)
  → split em balões separados por ---
  → Evolution API → WhatsApp
```

### API REST (para o dashboard)

```
GET  /api/stats
GET  /api/leads
GET  /api/appointments
GET  /api/conversations/:phone
POST /api/appointments/:id/confirm
POST /api/appointments/:id/reject
POST /api/test/message   ← golden tests (bloqueado em produção)
```

---

## Testes

### Golden tests

Cenários de conversa em YAML executados via Claude real:

```bash
make test-golden
```

Os 4 cenários cobertos:

| Arquivo | Cenário |
|---------|---------|
| `01_qualificacao.yaml` | Lead se apresenta, informa procedimento e indicação |
| `02_agendamento.yaml` | Lead qualificada agenda procedimento completo |
| `03_remarcacao.yaml` | Cliente solicita remarcação de horário |
| `04_escalada.yaml` | Cliente pede para falar com a equipe |

### Smoke tests

Health checks básicos que não requerem Claude:

```bash
make smoke
```

---

## Troubleshooting

**Agente não responde no WhatsApp**
1. `make logs` — procure erros de webhook
2. Confirme que `AGENT_WEBHOOK_URL` está acessível publicamente
3. `make webhook` para re-registrar o webhook

**QR Code não aparece**
- Acesse `http://localhost:8080` diretamente na Evolution API
- Verifique se `EVOLUTION_INSTANCE` no `.env` coincide com o nome criado

**Erro de Google Calendar**
- Confirme que `google_credentials.json` está em `credentials/`
- A service account precisa ter acesso ao calendário (compartilhe com o e-mail da SA)

**Dashboard em branco**
- Verifique se o agente está rodando: `curl http://localhost:3000/health`
- Confirme `VITE_API_URL=http://localhost:3000` no `.env`

**Golden tests falhando**
- O agente precisa estar rodando: `make up`
- Verifique `ANTHROPIC_API_KEY` no `.env`
- `make logs` para ver erros detalhados do loop Claude
