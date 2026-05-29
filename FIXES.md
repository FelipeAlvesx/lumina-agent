# Lumina Agent — Lista de Correções Pendentes

Itens identificados após a revisão das Fases 1–4. Organizados por prioridade e impacto.

---

## Prioridade 1 — Bugs que explodem em runtime

### FIX-01 · `main.py` importa função privada `_slot_label`

**Arquivo:** `agent/main.py`, linha 13

**Problema:**
```python
# atual — frágil, viola a interface pública do módulo
from agent_core import process_message, transcribe_audio, _slot_label
```

`_slot_label` é uma função prefixada com `_`, ou seja, privada. Se o nome interno mudar, o import quebra silenciosamente.
A função pública equivalente já existe em `verticals/estetica/tools.py`.

**Correção:**
```python
# correto
from agent_core import process_message, transcribe_audio
from verticals.estetica.tools import slot_label as _slot_label
```

Verificar todas as chamadas de `_slot_label` em `main.py` após trocar o import.

---

### FIX-02 · Endpoint `/api/test/message` não tem proteção robusta em produção

**Arquivo:** `agent/api.py`, linha ~185

**Problema:**
A proteção atual depende de `FLASK_ENV == "production"`, mas essa variável nunca é definida no `docker-compose.yml`.
Resultado: o endpoint fica aberto em produção (qualquer pessoa pode injetar mensagens no agente).

**Correção — duas partes:**

1. Adicionar variável `TEST_ENDPOINT_ENABLED` ao `docker-compose.yml` e `.env.example`:
```yaml
# docker-compose.yml — service agent → environment
- TEST_ENDPOINT_ENABLED=${TEST_ENDPOINT_ENABLED:-false}
```

2. Trocar a checagem em `api.py`:
```python
# de:
if os.getenv("FLASK_ENV") == "production":
# para:
if os.getenv("TEST_ENDPOINT_ENABLED", "false").lower() != "true":
```

3. Adicionar ao `.env.example`:
```
# Habilite apenas em desenvolvimento para rodar golden tests
TEST_ENDPOINT_ENABLED=false
```

---

## Prioridade 2 — Problemas de segurança

### FIX-03 · Dashboard e API sem autenticação

**Arquivos:** `agent/api.py`, `dashboard/src/lib/api.ts`

**Problema:**
Qualquer pessoa com acesso à porta 3000 (agente) ou 5173 (dashboard) consegue:
- Ver todos os leads e conversas
- Confirmar ou rejeitar agendamentos
- Injetar mensagens de teste

Para um demo interno isso é aceitável. Para qualquer deploy acessível externamente, é um risco.

**Correção sugerida (minimal — token estático):**

1. Adicionar ao `.env.example`:
```
DASHBOARD_SECRET=troque-esta-chave
```

2. Em `api.py`, adicionar middleware de autenticação:
```python
@api_bp.before_request
def require_token():
    secret = os.getenv("DASHBOARD_SECRET")
    if not secret:
        return  # sem secret configurado, sem proteção (modo dev)
    token = request.headers.get("X-Dashboard-Token") or request.args.get("token")
    if token != secret:
        return jsonify({"error": "Não autorizado"}), 401
```

3. Em `dashboard/src/lib/api.ts`, passar o token nos headers via `VITE_DASHBOARD_SECRET`.

---

## Prioridade 3 — Qualidade de código

### FIX-04 · `import os` fora de ordem em `api.py`

**Arquivo:** `agent/api.py`, linha 8

**Problema:**
Stdlib imports devem vir antes de imports de terceiros (PEP 8).

```python
# atual (errado)
from flask import Blueprint, jsonify, request

import os

from sessions import ...
```

**Correção:**
```python
# correto
import os

from flask import Blueprint, jsonify, request

from sessions import ...
```

---

### FIX-05 · `import` lazy de `agent_core` dentro de função em `api.py`

**Arquivo:** `agent/api.py`, função `test_message()`, última linha antes do return

**Problema:**
```python
from agent_core import run_test_message  # import dentro de função
```

Imports dentro de função dificultam leitura e análise estática. Só fazem sentido para evitar importação circular — o que não é o caso aqui.

**Correção:**
Mover para o topo do arquivo junto com os outros imports internos:
```python
from agent_core import run_test_message
```

E remover o import de dentro da função `test_message()`.

---

## Prioridade 4 — Developer experience

### FIX-06 · `docker-compose.yml` não define `TEST_ENDPOINT_ENABLED`

Já descrito como parte do FIX-02. Registrado aqui separadamente para que apareça na lista de mudanças no `docker-compose.yml`.

---

### FIX-07 · `dashboard/dist/` presente no repositório

**Problema:**
A pasta `dashboard/dist/` (build de produção) está no disco. O `.gitignore` a exclui corretamente, mas se alguém inicializar um repositório git antes de rodar `npm run build`, o `dist/` pode acabar commitado por acidente.

**Correção:**
Adicionar ao `.gitignore` uma linha explícita de aviso:
```
# Build artifacts — gerados por `make build`, não commitar
dashboard/dist/
```

Já existe no `.gitignore` atual — apenas confirmar que está correto antes do primeiro `git init`.

---

### FIX-08 · `make setup` não copia `.env` automaticamente quando já existe

**Arquivo:** `Makefile`, target `setup`

**Problema:**
O target atual só copia `.env.example → .env` se o arquivo `.env` não existir. Isso é correto para não sobrescrever credenciais. Porém não há mensagem clara de "seu .env já existe — revise se tem todas as novas variáveis".

**Correção:**
Adicionar diff entre `.env.example` e `.env` para mostrar chaves que existem no exemplo mas não no `.env` local:

```makefile
setup:
	@python3 setup/check_prerequisites.py
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "==> .env criado. Edite com suas credenciais antes de continuar."; \
	else \
		echo "==> .env já existe."; \
		MISSING=$$(comm -23 <(grep -oE '^[A-Z_]+' .env.example | sort) <(grep -oE '^[A-Z_]+' .env | sort)); \
		if [ -n "$$MISSING" ]; then \
			echo "    Variáveis no .env.example que faltam no seu .env:"; \
			echo "$$MISSING" | sed 's/^/      - /'; \
		fi; \
	fi
```

---

## Resumo por arquivo

| Arquivo | FIX |
|---------|-----|
| `agent/main.py` | FIX-01 |
| `agent/api.py` | FIX-02, FIX-04, FIX-05 |
| `agent/api.py` + `dashboard/src/lib/api.ts` | FIX-03 |
| `docker-compose.yml` | FIX-02 (parte 1), FIX-06 |
| `.env.example` | FIX-02 (parte 3), FIX-03 |
| `.gitignore` | FIX-07 (verificação) |
| `Makefile` | FIX-08 |

---

## Ordem de execução recomendada

1. **FIX-01** — não quebra nada, feito em 2 linhas
2. **FIX-04** + **FIX-05** — limpeza de estilo, sem risco
3. **FIX-02** — proteção do endpoint de teste (requer restart do container)
4. **FIX-08** — melhora o DX no onboarding
5. **FIX-03** — autenticação (avalie se o ambiente exige antes de fazer deploy)
6. **FIX-06** + **FIX-07** — quando for criar o repositório git
