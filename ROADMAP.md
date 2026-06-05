# ROADMAP — Lumina Agent (acabamento para demo B2B)

> **Objetivo deste documento:** guia de execução para tornar o agente Lara e o
> dashboard **impecáveis para uma demo de venda ao vivo para donos de clínica**.
> Cada pilar tem estado atual (com `arquivo:linha`), gaps, tarefas executáveis e
> critérios de aceite. Foi escrito para ser lido e executado por uma sessão do
> Claude Code — uma seção por vez.

---

## Como usar este documento (protocolo p/ a IA)

1. **Leia só o pilar que vai executar.** Cada pilar é autocontido. Não precisa
   carregar o arquivo inteiro no contexto.
2. **Antes de codar, rode o passo `AUDITAR`** do pilar — o estado real do código
   pode ter mudado desde que este doc foi escrito (2026-06-04). Confirme os
   `arquivo:linha` antes de editar.
3. **Execute tarefa por tarefa, em ordem.** Cada tarefa tem `Aceite:` testável.
   Não marque como pronta sem rodar o teste.
4. **Atualize o STATUS abaixo** ao concluir uma tarefa (`[ ]` → `[x]`).
5. **Loop de teste rápido** (sem WhatsApp):
   ```bash
   curl -X POST http://localhost:3000/api/test/message \
     -H "Content-Type: application/json" \
     -d '{"phone":"5571999999999","message":"oi, quero agendar botox"}'
   ```
   Retorna `{reply, tool_calls}` — use para validar fluxo e tools sem celular.

### Princípios (demo B2B — o que "impecável" significa aqui)

- **A demo é vendida pela conversa + pelo dashboard.** O dono da clínica precisa
  pensar "isso atende melhor que minha recepcionista e eu vejo tudo".
- **Zero fricção visível:** nunca mostrar erro técnico ("calendário não
  configurado"), nunca um balão robótico, nunca um horário inventado.
- **A Lara converte, não só responde.** Tem que conduzir até o agendamento e
  contornar objeções (preço, "vou pensar").
- **O dashboard parece vivo:** dados realistas, métricas que contam uma história
  de ROI (leads → qualificados → agendados → confirmados).

### Definition of Done global

- [ ] Demo script (§Golden Path) roda ponta a ponta sem nenhum tropeço
- [ ] Dashboard populado com dados realistas e métricas coerentes
- [ ] Nenhum caminho mostra erro técnico ao usuário final
- [ ] `make test-golden` passa

---

## STATUS (ordem de execução por impacto)

| # | Pilar | Prioridade | Status |
|---|-------|------------|--------|
| 1 | Fluxo de conversa (Lara) | 🔴 Alta | [x] Concluído (Tarefa 1.6 remarcar/cancelar ✅ 2026-06-04) |
| 2 | Agendamentos | 🔴 Alta | [x] Concluído (2.1–2.5 já estavam implementados; confirmado 2026-06-04) |
| 3 | Escalação | 🟡 Média | [x] Concluído (3.1–3.3 ✅ 2026-06-04) |
| 4 | Knowledge base | 🟢 Baixa | [ ] Não iniciado |
| 5 | Dashboard | 🔴 Alta (é o que o cliente vê) | [x] Concluído (5.1 seed ✅, 5.2 KPIs ✅, 5.3 Métricas+rota ✅, 5.4 Conversas+escalação ✅, 5.5 polish ✅, 5.6 refresh indicator ✅, 5.7 remarcar/cancelar UI ✅ — 2026-06-04) |

> Ordem recomendada: **1 → 2 → 5 → 3 → 4**. Conversa e agendamento são o coração;
> o dashboard é o que impressiona na tela; escalação e knowledge são refinamento.

---

# PILAR 1 — Fluxo de conversa (Lara)

**Impecável =** a Lara soa humana, calorosa e conduz a cliente do "oi" até o
agendamento confirmado, contornando hesitação e perguntas de preço — sem nunca
parecer um bot.

### AUDITAR (rodar antes de codar)
- `prompts/base/human_persona.md` — tom de voz da Lara
- `prompts/base/engine_rules.md` — regras de fluxo e uso de tools
- `verticals/estetica/prompt_fragment.md` — contexto da vertical
- `agent/config.py:38` — modelo padrão (`claude-haiku-4-5-20251001`)
- `agent/agent_core.py:54-59` — montagem do system prompt, `max_tokens`, delays

### Estado atual
- Modelo: **Haiku 4.5** por default (`config.py:38,80`). Precedência:
  `CLAUDE_MODEL` (env) > `model` no YAML > default.
- `max_tokens=600`, até 5 iterações de tool, debounce 4s (`agent_core.py:199`).
- Persona e regras existem e são boas, mas **não cobrem objeções nem têm
  exemplos few-shot** de conversa completa.
- Split de balões por `---` já implementado.

### Gaps p/ demo B2B
1. **Modelo Haiku** entrega bem, mas para venda ao vivo a fluidez do **Sonnet**
   reduz frases estranhas e aumenta a percepção de "humano". Alavanca #1.
2. **Sem playbook de objeções** — a cliente que diz "tá caro" ou "vou pensar"
   não é reconduzida. Numa demo de vendas isso é o que fecha o negócio.
3. **Sem exemplos few-shot** do caminho ideal — o modelo improvisa o tom.
4. **Cold open inconsistente** — primeira mensagem da Lara varia de qualidade.
5. **Cliente recorrente** (já tem nome/lead salvo) não recebe tratamento
   diferenciado claro.

### Tarefas

**Tarefa 1.1 — Subir o modelo para a demo**
- **Arquivos:** `tenants/lumina.yaml` (adicionar campo `model:`), confirmar leitura em `config.py:79-85`.
- **O quê:** Definir `model: claude-sonnet-4-6` no YAML (ou via `CLAUDE_MODEL` no `.env`).
- **Como:** Adicionar `model: claude-sonnet-4-6` no topo do YAML. Manter Haiku como
  fallback de produção via env, se quiser economia fora da demo.
- **Aceite:** `docker logs lumina_agent` no boot mostra o modelo Sonnet; respostas
  no `/api/test/message` ficam visivelmente mais naturais.

**Tarefa 1.2 — Playbook de objeções no prompt**
- **Arquivos:** `prompts/base/engine_rules.md` (nova seção) ou `verticals/estetica/prompt_fragment.md`.
- **O quê:** Adicionar bloco "Condução e objeções" cobrindo: preço ("tá caro" →
  valor da avaliação gratuita + parcelamento, sem citar valor), hesitação ("vou
  pensar" → oferecer segurar um horário sem compromisso), comparação ("vi mais
  barato" → diferencial de segurança/especialista), medo de dor/resultado →
  acolher + avaliação.
- **Como:** Escrever 5-6 mini-roteiros (gatilho → resposta-modelo) no tom da Lara.
- **Aceite:** Mandar "tá caro" e "vou pensar" via `/api/test/message` → Lara
  reconduz para agendamento sem citar preço e sem ser insistente demais.

**Tarefa 1.3 — Few-shot do caminho ideal**
- **Arquivos:** `prompts/base/engine_rules.md` (seção "Exemplo de conversa ideal").
- **O quê:** Incluir 1 diálogo curto exemplar (oi → qualificação → slots →
  agendamento) mostrando tom, uso de `---` e cadência de tools.
- **Aceite:** Conversa real segue o padrão do exemplo (qualifica antes de
  oferecer horário, usa balões curtos).

**Tarefa 1.4 — Cold open e cliente recorrente**
- **Arquivos:** `prompts/base/engine_rules.md`; contexto já injetado em `agent_core.py:127-138` (`[DADOS DA CLIENTE JÁ COLETADOS]`).
- **O quê:** Regra explícita: se há nome salvo → cumprimentar pelo nome e retomar;
  se primeira mensagem → abertura padrão calorosa + pedir nome.
- **Aceite:** 1ª mensagem de número novo vs. número com lead salvo produzem
  aberturas distintas e corretas.

**Tarefa 1.5 — Calibrar tamanho e ritmo**
- **Arquivos:** `agent_core.py:199` (`max_tokens`), `:58-59` (`RESPONSE_DELAY`, `BALLOON_DELAY`).
- **O quê:** Validar se 600 tokens trunca respostas com 3 balões; ajustar se
  necessário (ex.: 800). Confirmar que delays soam naturais no WhatsApp.
- **Aceite:** Nenhuma resposta cortada no meio; balões chegam com ritmo humano.

**Tarefa 1.6 — Fluxo de remarcar/cancelar (novo)**
- **Arquivos:** `prompts/base/engine_rules.md` (nova seção "Remarcações e cancelamentos").
- **O quê:** Ensinar a Lara a:
  1. **Oferecer remarcar:** quando cliente menciona "não posso nesse dia" ou "preciso de outro horário" → perguntar novo período → listar slots → criar remarcação (`reschedule_appointment`)
  2. **Oferecer cancelar:** quando cliente diz "quero cancelar" ou "não dá mais" → confirmar razão (opcional) → cancelar (`cancel_appointment`)
  3. **Reconhecer agendamentos existentes:** quando cliente diz "tenho agendamento" ou "já marquei", chamar `get_patient_appointments` para listar antes de oferecer remarcação
  4. **Mensagens ao escalar:** "Vou solicitar a remarcação para nossa equipe confirmar" / "Cancelamento solicitado, a gente notifica você"
- **Aceite:** Testar via `/api/test/message`:
  - "Quero remarcar meu agendamento" → Lara lista (chamando `get_patient_appointments`), oferece slots novos
  - "Pode cancelar?" → Lara confirma e cria `cancel_requested`
  - Ambas resultam em estados corretos no DB

### Critérios de aceite do PILAR 1
- [x] Modelo Sonnet ativo na demo (`tenants/lumina.yaml: model: claude-sonnet-4-6`; override via `CLAUDE_MODEL`)
- [x] Objeções de preço e hesitação reconduzem ao agendamento (playbook + few-shot)
- [x] Tom consistente e caloroso em 10 mensagens seguidas de teste
- [x] Nenhuma menção a IA/robô; nenhum preço citado
- [ ] Fluxo de remarcar/cancelar: Lara identifica agendamentos existentes, oferece remarcar/cancelar, cria estados corretos no DB

### O que foi feito (sessão 2026-06-04)
- **1.1** `model: claude-sonnet-4-6` no YAML + `CLAUDE_MODEL` repassado no compose e
  documentado no `.env.example`. Confirmado no boot: `get_config().model` = Sonnet.
- **1.2/1.3/1.4** `engine_rules.md`: bloco "Prioridades absolutas", "Condução e
  objeções" (preço/hesitação/comparação/medo), 2 few-shots (nome-na-1ª-msg e caminho
  completo) e regra de cold open + cliente recorrente.
- **1.5** `max_tokens` 600 → 800.
- **Bugfixes de fluxo (agent_core.py)** descobertos na validação:
  - `_run_tool_loop` **descartava o texto** que acompanhava tool calls → respostas
    vazias → histórico corrompido. Agora acumula a narração (`collected_text`).
  - Dedup de balões repetidos (modelo re-narrava entre iterações de tool).
  - Rede de segurança `_force_text`: se usou tools mas não escreveu nada, força uma
    resposta de texto — a Lara nunca fica muda.
  - `_build_lead_context` agora é diretivo ("Lead completo — não re-salve") → cortou
    o re-save de campos a cada turno.

### Edges conhecidos (não bloqueiam a demo; revisitar se sobrar tempo)
1. **Cold open não extrai o nome dado na mensagem** (ex.: "sou a Marina" → ainda
   pergunta o nome). O modelo recita o cold open em vez de ler o conteúdo. 4 tentativas
   de prompt não moveram; injetar lembrete em alta recência causou vazamento de
   contexto na resposta (revertido). Cosmético: atraso de 1 turno, recupera sozinho.
2. **Objeção de preço às vezes é desviada** para o agendamento sem tratar o preço no
   mesmo turno (inconsistente — funciona na maioria dos casos). "vou pensar" e "vi
   mais barato" funcionam bem.

> ⚠️ **Bloqueio para o Golden Path (vai para o Pilar 2):** sem Google Calendar
> configurado (`calendar_id: ""`), `list_available_slots` retorna erro e a Lara
> **escala para humano** ("vou te transferir"). O agendamento não fecha neste
> ambiente. É exatamente a **Tarefa 2.4 (fallback de demo)** — CRÍTICA. Fazer antes
> de qualquer ensaio do Golden Path.

> 🛠️ **Nota de operação:** o código em `agent/` é baked na imagem (não é volume).
> Para aplicar mudanças de código: `docker compose build agent && docker compose up -d
> --no-deps agent`. O `--no-deps` evita recriar o `lumina_evolution` (risco de ban do
> WhatsApp). Mudanças só de prompt/YAML (volumes) precisam apenas do `up --no-deps`.

---

# PILAR 2 — Agendamentos

**Impecável =** os horários oferecidos parecem curados por uma recepcionista que
conhece a agenda; a duração bate com o procedimento; e o agendamento nunca falha
na frente do cliente.

### AUDITAR
- `agent/gcal.py` — toda a lógica de slots (`list_available_slots:46`, `create_pending_event:120`)
- `verticals/estetica/tools.py:68-107` — defs das tools `list_available_slots` e `create_pending_appointment`
- `tenants/lumina.yaml:24-26` — `slot_duration_minutes: 60`, `procedures`
- `agent/config.py` — onde `slot_duration` é lido

### Estado atual
- `gcal.list_available_slots` consulta freebusy do Google, varre seg-sáb 9h-19h,
  retorna **os 3 primeiros slots cronológicos** com `slot_duration` **fixo de 60min
  para todos os procedimentos** (`gcal.py:57,95`).
- A tool aceita `procedure_type` mas **ignora preferência de período** (manhã/tarde)
  — embora `engine_rules.md:22` mande perguntar isso.
- Se o Google Calendar não estiver configurado → retorna `{"error": "Calendário
  não configurado..."}` (`gcal.py:51-52`) — **risco de aparecer na demo**.

### Gaps p/ demo B2B
1. **Duração única (60min)** para botox e laser CO2 é irreal — recepcionista de
   verdade sabe que botox ~20min e laser ~90min. Quebra a ilusão.
2. **Slots não curados:** "os 3 primeiros" tende a oferecer 3 horários do mesmo
   dia de manhã. Curadoria (dias/períodos variados) parece mais profissional.
3. **Preferência manhã/tarde não é usada** pela busca — a Lara pergunta e ignora.
4. **Fallback de demo ausente:** sem Calendar configurado, a demo mostra erro.
5. **Sem buffer** entre agendamentos (limpeza/preparo de sala).

### Tarefas

**Tarefa 2.1 — Duração por procedimento**
- **Arquivos:** `tenants/lumina.yaml` (mapa `procedure_durations`), `agent/gcal.py:57,95-96`, `agent/config.py` (ler o mapa).
- **O quê:** Mapa procedimento → minutos no YAML (ex.: Botox: 30, Laser CO2: 90,
  Limpeza de pele: 60). `list_available_slots` usa a duração do `procedure_type`
  recebido; fallback para 60 se não mapeado.
- **Como:** Passar `procedure_type` adiante em `gcal.list_available_slots` e
  resolver a duração antes de varrer os slots.
- **Aceite:** Pedir slots p/ "Botox" e p/ "Laser CO2" gera blocos de durações
  diferentes; `slot_end - slot_start` bate com o mapa.

**Tarefa 2.2 — Preferência de período (manhã/tarde)**
- **Arquivos:** `verticals/estetica/tools.py:74-87` (add param `period`), `agent/gcal.py:46,92-106`.
- **O quê:** Novo parâmetro opcional `period` (`manha`/`tarde`) na tool; gcal
  filtra o intervalo de horas (manhã 9-12, tarde 13-19).
- **Aceite:** "prefiro de manhã" → todos os 3 slots retornados são antes do meio-dia.

**Tarefa 2.3 — Curadoria dos 3 slots**
- **Arquivos:** `agent/gcal.py:83-108`.
- **O quê:** Em vez dos 3 primeiros, distribuir: no máx. 1-2 por dia, variando
  período, ao longo do intervalo pedido — parece seleção humana.
- **Aceite:** Num intervalo de 1 semana, os 3 slots caem em dias diferentes
  (quando há disponibilidade).

**Tarefa 2.4 — Fallback de demo (CRÍTICO p/ demo)**
- **Arquivos:** `agent/gcal.py:51-52` e `:122-123`.
- **O quê:** Se `is_configured()` for falso, em vez de erro, gerar slots
  **simulados** plausíveis (próximos dias úteis, respeitando 9h-19h e duração).
  `create_pending_event` já degrada bem (retorna `external_id: None`).
- **Como:** Flag `DEMO_CALENDAR=true` no `.env` → caminho de slots mockados.
- **Aceite:** Sem credenciais Google, a demo oferece horários e cria agendamento
  pendente normalmente, sem nenhuma mensagem de erro.

**Tarefa 2.5 — Buffer entre agendamentos**
- **Arquivos:** `agent/gcal.py:95-106`, `tenants/lumina.yaml` (`slot_buffer_minutes`).
- **O quê:** Adicionar buffer configurável (ex.: 15min) após cada bloco ocupado.
- **Aceite:** Slots ofertados respeitam o buffer em torno de eventos ocupados.

### Critérios de aceite do PILAR 2
- [x] Durações por procedimento corretas
- [x] Preferência manhã/tarde respeitada
- [x] 3 opções variadas e bem distribuídas
- [x] Demo funciona 100% sem Google Calendar (fallback)
- [x] `create_pending_appointment` notifica recepcionista e aparece no dashboard

---

# PILAR 3 — Escalação

**Impecável =** a Lara sabe exatamente quando sair de cena e passar para o humano,
e isso aparece de forma clara para a recepcionista (e no dashboard).

### AUDITAR
- `verticals/estetica/tools.py:146-156` — tool `escalate_to_human`
- `agent/agent_core.py:66-90` — flag de escalação, `ESCALATION_TTL` (30min)
- `agent/agent_core.py:222-224` — incremento métrica + flag
- `prompts/base/engine_rules.md:9` — gatilhos atuais
- `verticals/estetica/notifications.py` — notificação à recepcionista
- `agent/sessions.py` — tabela `escalations` / `log_escalation`

### Estado atual
- Gatilhos (prompt): pedir humano, dúvida médica/clínica, não saber responder.
- Após escalar: `_ESCALATED[phone]` com TTL 30min; durante a janela, mensagens da
  cliente são **encaminhadas ao humano** (`agent_core.py:256-258`), Lara não responde.
- Escalações são logadas (`log_escalation`) e contadas em `get_stats` (`sessions.py:476`).

### Gaps p/ demo B2B
1. **Gatilhos coarse** — não distingue categorias (médica, reclamação, pedido
   explícito, confusão repetida, fora de escopo de alto valor). Categoria alimenta
   métricas e mostra inteligência.
2. **Sem detecção de frustração / repetição** (cliente reformula 2-3x sem avançar).
3. **Handoff pouco visível no dashboard** — escalações deveriam ter painel próprio.
4. **Sem mensagem de retorno** quando o TTL expira (cliente "volta" pra Lara sem aviso).

### Tarefas

**Tarefa 3.1 — Taxonomia de motivos de escalação**
- **Arquivos:** `verticals/estetica/tools.py:146-156` (add enum `category`), `prompts/base/engine_rules.md`.
- **O quê:** `escalate_to_human` ganha `category`: `medica`, `reclamacao`,
  `pedido_humano`, `confusao_repetida`, `fora_escopo`. Prompt define cada gatilho.
- **Aceite:** Cada tipo de mensagem dispara a categoria certa (validar via `tool_calls`).

**Tarefa 3.2 — Detecção de frustração/repetição**
- **Arquivos:** `prompts/base/engine_rules.md`.
- **O quê:** Regra: se a cliente repete a mesma necessidade 2x sem progresso, ou
  demonstra irritação, escalar com `category: confusao_repetida`.
- **Aceite:** Simular 2 reformulações confusas → Lara escala em vez de insistir.

**Tarefa 3.3 — Mensagem de handoff e retorno**
- **Arquivos:** `agent/agent_core.py:256-258,280`.
- **O quê:** Handoff claro ("vou te passar para nossa equipe agora 🙏"). Ao expirar
  o TTL, Lara reabre com "voltei pra te ajudar, em que posso seguir?".
- **Aceite:** Fluxo de escalação e retorno soa natural, sem silêncio nem repetição.

**Tarefa 3.4 — Escalações no dashboard** (ver Pilar 5)
- **Aceite:** Painel de escalações com motivo/categoria e timestamp.

### Critérios de aceite do PILAR 3
- [x] 5 categorias disparando corretamente (`medica`, `reclamacao`, `pedido_humano`, `confusao_repetida`, `fora_escopo`)
- [x] Frustração/repetição detectada (regra dos 3 turnos + sinais de irritação no prompt)
- [x] Handoff + retorno com mensagens claras ("Um momento! 🙏" + "Voltei! 😊" ao expirar TTL)
- [ ] Escalações visíveis no dashboard com categoria (depende de endpoint — ver dashboard)

---

# PILAR 4 — Knowledge base (fictícia, mas consistente)

**Impecável =** a Lara responde qualquer dúvida sobre os 12 procedimentos com
coerência, sem inventar e sem citar preço. Conteúdo pode ser fictício.

### AUDITAR
- `knowledge/servicos.md`, `knowledge/faq.md`, `knowledge/cuidados.md`
- `agent/rag.py` — busca por keyword sobre os `.md`
- `tenants/lumina.yaml:30-57` — 12 procedimentos + `extra_faq`

### Estado atual
- RAG é **keyword-based** sobre os `.md` de `knowledge/`.
- `lumina.yaml` lista 12 procedimentos e 4 FAQs extras.
- Risco: knowledge pode não cobrir todos os 12 procedimentos de forma uniforme,
  e o RAG por keyword falha se os termos não baterem.

### Tarefas

**Tarefa 4.1 — Cobertura uniforme dos 12 procedimentos**
- **Arquivos:** `knowledge/servicos.md`.
- **O quê:** Para cada um dos 12 procedimentos (lista em `lumina.yaml:30-42`),
  uma seção com: o que é, para quem é indicado, sensação/conforto, downtime,
  duração do resultado. **Sem preços.**
- **Aceite:** Perguntar sobre cada procedimento via `/api/test/message` retorna
  resposta específica e correta (não genérica).

**Tarefa 4.2 — Enriquecer FAQ e cuidados**
- **Arquivos:** `knowledge/faq.md`, `knowledge/cuidados.md`.
- **O quê:** FAQs de pré/pós-procedimento, contraindicações gerais, o que levar
  na avaliação. Alinhar com `extra_faq` do YAML (sem duplicar/contradizer).
- **Aceite:** Dúvidas comuns (dói? posso fazer grávida? quando vejo resultado?)
  têm resposta coerente.

**Tarefa 4.3 — Sanidade do RAG**
- **Arquivos:** `agent/rag.py`.
- **O quê:** Garantir que termos-chave dos 12 procedimentos e sinônimos comuns
  ("preenchimento" / "ácido hialurônico") recuperam o trecho certo.
- **Aceite:** 12/12 procedimentos recuperam o trecho correto numa bateria de busca.

### Critérios de aceite do PILAR 4
- [ ] 12 procedimentos cobertos uniformemente
- [ ] Zero menção a preço no knowledge
- [ ] RAG recupera o trecho certo para os 12 + FAQs

---

# PILAR 5 — Dashboard (o que o cliente vê)

**Impecável =** ao abrir o dashboard na frente do dono da clínica, ele vê um
produto profissional, com dados vivos e métricas que provam ROI (a Lara trabalha).

### AUDITAR
- `dashboard/src/pages/` — Overview, Appointments, Contacts, Conversations, Metrics, Servicos, Profissionais, Configuracoes
- `dashboard/src/lib/api.ts` — client tipado
- `agent/api.py` — endpoints (`/stats:53`, `/leads:60`, `/appointments:70`, `/conversations/:phone:116`, confirm/reject, services/professionals CRUD, `/config:306`)
- `agent/sessions.py:449` — `get_stats` (leads, qualified, appointments, pending, confirmed, escalations)
- `tailwind.config.ts` — tokens: primary `#7C3D6E`, gold `#C5A87D`, bg `#F0EFEC`

### Estado atual
- Dashboard completo (8 páginas), polling 30s, Recharts (funnel/bar/pie).
- `get_stats` já entrega 6 métricas. CRUD de serviços/profissionais/config funciona.

### Gaps p/ demo B2B
1. **Dados vazios = demo morta.** Sem leads/agendamentos/conversas seedados, as
   telas ficam vazias. **Maior risco visual da demo.**
2. **Overview** pode faltar KPIs de ROI: taxa de conversão, agenda de hoje,
   tempo médio de resposta.
3. **Métricas** podem não contar a história completa: funil lead→qualificado→
   agendado→confirmado, procedimentos mais procurados, taxa de escalação, horários
   de pico.
4. **Conversas ao vivo** — ver a Lara conversando é o "uau" da demo; precisa estar
   polido e fácil de achar.
5. **Estados de loading/empty/erro** e responsividade — acabamento profissional.
6. **Fluxo de remarcar/cancelar invisível.** Backend tem as tools completas
   (`reschedule_appointment`, `cancel_appointment`, estados `reschedule_requested`/`cancel_requested`)
   mas o dashboard não oferece UI para recepcionista confirmar/rejeitar remarcações e
   cancelamentos. Máximo impacto: recepcionista não pode gerenciar mudanças de clientes
   (fluxo quebrado). **Tarefa 5.7 resolve.**

### Tarefas

**Tarefa 5.1 — Seed de dados realistas (CRÍTICO p/ demo)**
- **Arquivos:** novo `agent/seed_demo.py` (ou flag em `sessions.py`); rodar no boot quando `DEMO_SEED=true`.
- **O quê:** Popular ~15-25 leads (nomes BR realistas), conversas plausíveis, ~10
  agendamentos em vários status (pending/confirmed/rejected), 2-3 escalações,
  distribuídos nos últimos 14 dias. Procedimentos coerentes com o catálogo.
- **Aceite:** `make up` com `DEMO_SEED=true` → todas as telas aparecem vivas e
  coerentes; métricas batem com os dados.

**Tarefa 5.2 — Overview com KPIs de ROI**
- **Arquivos:** `dashboard/src/pages/` (Overview), `agent/api.py:/stats`, `agent/sessions.py:get_stats`.
- **O quê:** Cards: leads (período), taxa de qualificação, taxa de conversão
  (agendado/lead), agendamentos de hoje, pendentes aguardando confirmação.
  Adicionar campos faltantes ao `get_stats` se preciso.
- **Aceite:** Overview mostra ≥5 KPIs coerentes com os dados seedados.

**Tarefa 5.3 — Página de métricas completa**
- **Arquivos:** `dashboard/src/pages/` (Metrics).
- **O quê:** Funil (lead→qualificado→agendado→confirmado), barras de procedimentos
  mais procurados, pizza de status, taxa de escalação, horários de pico.
- **Aceite:** Todos os gráficos renderizam com dados reais, sem mock no front.

**Tarefa 5.4 — Painel de conversas polido**
- **Arquivos:** `dashboard/src/pages/` (Conversations), `agent/api.py:/conversations`.
- **O quê:** Lista de conversas recentes + timeline estilo chat (balões
  cliente/Lara), busca por telefone/nome. Indicador de escalada.
- **Aceite:** Selecionar uma conversa mostra o diálogo completo, legível, com
  visual de chat.

**Tarefa 5.5 — Acabamento visual**
- **Arquivos:** componentes em `dashboard/src/components/`.
- **O quê:** Estados de loading (skeletons), empty states elegantes, tratamento
  de erro silencioso, responsividade. Coerência com os tokens da marca.
- **Aceite:** Nenhuma tela "pula" ou mostra erro cru; visual consistente.

**Tarefa 5.6 — (opcional) Sensação "ao vivo"**
- **O quê:** Indicador "atualizado agora" / refresh mais curto durante a demo.
- **Aceite:** Ao criar agendamento via WhatsApp, ele aparece no dashboard em ≤30s.

**Tarefa 5.7 — UI de remarcar e cancelar agendamentos**
- **Arquivos:** `dashboard/src/pages/Appointments.tsx`, `dashboard/src/lib/api.ts`, `dashboard/src/components/` (novo modal ou inline actions).
- **Dependências:** Pilar 2 (slots), Pilar 1 (prompt com fluxo de remarcar/cancelar — ainda não documentado)
- **O quê:** Adicionar ao painel de Appointments:
  1. **Coluna "Ações"** com 2 botões por agendamento (além dos confirm/reject existentes):
     - Botão "📅 Remarcar" — abre modal com:
       - Campo de seleção: "Qual agendamento deseja remarcar?" (pré-preenchido)
       - Data/período preferido (datepicker + radio de manha/tarde)
       - Botão "Solicitar remarcação" → POST `/api/appointments/{id}/reschedule` (novo endpoint)
     - Botão "❌ Cancelar" — abre modal com:
       - Confirmação: "Deseja cancelar este agendamento?"
       - Campo opcional: "Motivo (opcional)"
       - Botão "Confirmar cancelamento" → POST `/api/appointments/{id}/cancel` (novo endpoint)
  2. **Status visual:**
     - `reschedule_requested` → badge "⏳ Remarcação pendente" + botões "Confirmar" / "Rejeitar remarcação"
     - `cancel_requested` → badge "⏳ Cancelamento pendente" + botões "Confirmar" / "Rejeitar cancelamento"
  3. **Histórico visível:**
     - Mostrar em cada agendamento: slot original vs. novo (se remarcação pendente)
     - Ex.: "Botox: sáb 10h → seg 14h (aguardando confirmação)"
- **Como:** 
  - Backend: adicionar endpoints `POST /api/appointments/{id}/reschedule` e `POST /api/appointments/{id}/cancel` em `agent/api.py` (chamar as tools da Lara internamente ou diretamente `reschedule_appointment` / `cancel_appointment` em `sessions.py`)
  - Frontend: expandir `DataTable` ou `AppointmentCard` com modal + ações; adicionar métodos `rescheduleAppointment(id, new_slot_start, new_slot_end)` e `cancelAppointment(id, reason)` em `api.ts`
  - Estados: filtrar por status para mostrar "pendentes de confirmação" em destaque
- **Aceite:** 
  - Clicar "Remarcar" abre modal, preenchendo dados, recarrega lista com novo status `reschedule_requested`
  - Clicar "Cancelar" abre modal, confirmando, recarrega com status `cancel_requested`
  - Recepcionista clica "✓ Confirmar remarcação" → agendamento vira `confirmed` com novo slot + WhatsApp notificado
  - Recepcionista clica "✓ Confirmar cancelamento" → agendamento vira `cancelled` + WhatsApp notificado
  - Rejeitar (via reject endpoint) também funciona: remarcação rejeitada ou cancelamento rejeitado
- **Nota de sequência:** Esta tarefa depende de Pilar 2 estar com slots/agendamentos fluindo bem. Também requer que o prompt da Lara (Pilar 1) aprenda a oferecer remarcar/cancelar quando cliente mencionar — isso é uma **sub-tarefa do Pilar 1** (Tarefa 1.6, a adicionar).

### Critérios de aceite do PILAR 5
- [x] Dashboard nunca aparece vazio na demo (seed)
- [x] Overview com KPIs de ROI (taxa de conversão, pendentes, confirmados, contatos)
- [x] Métricas contam a história completa do funil (rota /metricas, drop-off %, procedimentos, horários de pico)
- [x] Conversas com visual de chat + badge de escalação + filtro de escaladas
- [x] Loading/empty/error tratados + refresh indicator em todas as páginas
- [x] Remarcar e cancelar agendamentos: UI completa + recepcionista pode confirmar/rejeitar

---

# Golden Path — roteiro da demo ao vivo

> Roteiro a ser exercitado de ponta a ponta. Vira também caso de `make test-golden`.

1. **Cold open:** cliente manda "Oi, vi vocês no Instagram" → Lara cumprimenta,
   se apresenta, pergunta o nome.
2. **Qualificação:** cliente diz nome + "queria saber sobre preenchimento labial"
   → Lara salva campos, explica brevemente (knowledge), pergunta como conheceu.
3. **Objeção de preço:** "quanto custa?" → Lara não cita preço, explica avaliação
   gratuita + parcelamento, convida a agendar.
4. **Agendamento:** "pode ser semana que vem de tarde" → `list_available_slots`
   (tarde, duração do preenchimento) → 3 opções curadas.
5. **Confirmação:** cliente escolhe → `create_pending_appointment` → "registrei
   seu horário, a equipe confirma em breve 💜".
6. **Dashboard:** mostrar o lead novo, o agendamento pendente, a conversa no chat,
   e a recepcionista confirmando (confirm → vira "confirmed", some de pendentes).
7. **Escalação (bônus):** "tenho herpes, posso fazer?" → dúvida médica → Lara
   escala com `category: medica`; aparece no painel de escalações.

**Critério:** os 7 passos rodam sem nenhum erro técnico, sem preço citado, sem
horário inventado, e tudo reflete no dashboard.

---

## Apêndice — comandos úteis

```bash
# Loop de teste sem WhatsApp
curl -X POST http://localhost:3000/api/test/message \
  -H "Content-Type: application/json" \
  -d '{"phone":"5571999999999","message":"<mensagem>"}'

make up            # sobe tudo
make logs          # logs de todos os serviços
make test-golden   # cenários de conversa (precisa do agente no ar)
docker logs lumina_agent --tail=50   # logs do agente
```

> **Nota de ambiente (já resolvido em 2026-06-04):** Evolution usa imagem
> customizada (`evolution/Dockerfile`) com patch @lid baked — não reiniciar o
> container manualmente após conectar o WhatsApp (causa ban do dispositivo).
