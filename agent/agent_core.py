"""
Cérebro do agente: recebe mensagem, busca contexto no RAG,
monta o histórico e chama o Claude com tool use e prompt cache.
"""

import os
import re
import json
import time
import hashlib
import threading
from importlib import import_module
from io import BytesIO
from datetime import datetime

import structlog
import anthropic
from openai import OpenAI as _OpenAI
from prometheus_client import Counter, Histogram

from config import get_config
from prompt_builder import build_system_prompt
from rag import search
from sessions import (
    get_history, save_turn,
    get_lead_data, is_lead_qualified,
    get_patient_appointments,
    log_escalation,
)
from evolution import send_message, notify_human

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

messages_sent_total        = Counter("messages_sent_total",        "Mensagens enviadas ao cliente")
escalations_total          = Counter("escalations_total",          "Escaladas para humano")
leads_qualified_total      = Counter("leads_qualified_total",      "Leads qualificados")
appointments_created_total = Counter("appointments_created_total", "Agendamentos criados")
errors_total               = Counter("errors_total",               "Erros no processamento")
llm_latency_seconds        = Histogram("llm_latency_seconds",      "Latência das chamadas Claude")

_anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_whisper_client   = _OpenAI(api_key=os.getenv("OPENAI_API_KEY", "dummy"))

_CLAUDE_MODEL = get_config().model
SYSTEM_PROMPT = build_system_prompt(get_config())
_SYSTEM_CACHE = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]

RESPONSE_DELAY = 5
BALLOON_DELAY  = 1

_WEEKDAYS_PT = [
    "segunda-feira", "terça-feira", "quarta-feira",
    "quinta-feira", "sexta-feira", "sábado", "domingo",
]

# ── Escalation flag ───────────────────────────────────────────────────────────
_ESCALATED: dict[str, float] = {}
_ESCALATED_LOCK = threading.Lock()
ESCALATION_TTL  = 30 * 60


def mark_escalated(phone: str) -> None:
    with _ESCALATED_LOCK:
        _ESCALATED[phone] = time.time()


def is_escalated(phone: str) -> bool:
    with _ESCALATED_LOCK:
        ts = _ESCALATED.get(phone)
        if ts is None:
            return False
        if time.time() - ts > ESCALATION_TTL:
            del _ESCALATED[phone]
            return False
        return True


def clear_escalation(phone: str) -> None:
    with _ESCALATED_LOCK:
        _ESCALATED.pop(phone, None)


# ── Vertical loader ───────────────────────────────────────────────────────────
_vertical_module = None
_tools_cache: list | None = None


def _get_vertical():
    global _vertical_module
    if _vertical_module is None:
        _vertical_module = import_module(f"verticals.{get_config().vertical}.tools")
    return _vertical_module


def _get_tools() -> list:
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = _get_vertical().get_tool_definitions(get_config())
    return _tools_cache


# ── Context builders ──────────────────────────────────────────────────────────

def _temporal_context() -> str:
    now     = datetime.now(get_config().tz)
    weekday = _WEEKDAYS_PT[now.weekday()]
    # Lumina: seg-sab 9h-19h
    is_open = now.weekday() <= 5 and 9 <= now.hour < 19
    status  = "DENTRO" if is_open else "FORA"
    return (
        f"\n\n[CONTEXTO TEMPORAL]\n"
        f"Agora é {weekday}, {now.strftime('%d/%m/%Y às %H:%M')} (horário de São Paulo).\n"
        f"Estamos {status} do horário de atendimento (seg-sáb, 9h-19h)."
    )


def _build_lead_context(phone: str) -> str:
    data = get_lead_data(phone)
    if not data:
        return ""
    lines   = [f"- {k}: {v}" for k, v in data.items()]
    missing = [f for f in get_config().lead_fields if f not in data]
    block   = "\n\n[DADOS DA CLIENTE JÁ COLETADOS]\n" + "\n".join(lines)
    if missing:
        block += f"\nAinda faltam coletar: {', '.join(missing)}"
    else:
        block += "\nLead completo — continue o atendimento normalmente."
    return block


def _slot_label(iso: str) -> str:
    _DAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(get_config().tz)
        return f"{_DAYS[dt.weekday()]}, {dt.strftime('%d/%m/%Y às %H:%M')}"
    except Exception:
        return iso


def _build_appointments_context(phone: str) -> str:
    apts   = get_patient_appointments(phone)
    active = [a for a in apts if a["status"] not in ("cancelled", "rejected")]
    if not active:
        return ""
    lines = [
        f"- ID #{a['id']}: {a['procedure_type']} em {_slot_label(a['slot_start'])} — {a['status']}"
        for a in active
    ]
    return "\n\n[AGENDAMENTOS DA CLIENTE]\n" + "\n".join(lines)


# ── Audio transcription ───────────────────────────────────────────────────────

def transcribe_audio(audio_b64: str) -> str | None:
    try:
        import base64
        audio_bytes = base64.b64decode(audio_b64)
        audio_file  = BytesIO(audio_bytes)
        audio_file.name = "audio.ogg"
        result = _whisper_client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return result.text.strip() if result.text else None
    except Exception as e:
        log.error("transcription_failed", error=str(e))
        return None


# ── Claude tool loop ──────────────────────────────────────────────────────────

def _run_tool_loop(phone: str, messages: list, track_calls: list | None = None) -> tuple[str, bool]:
    escalated     = False
    config        = get_config()
    was_qualified = is_lead_qualified(phone, config.lead_fields)
    phone_hash    = hashlib.sha256(phone.encode()).hexdigest()[:12]
    vertical      = _get_vertical()
    tools         = _get_tools()
    context       = {
        "phone":                     phone,
        "phone_hash":                phone_hash,
        "was_qualified":             was_qualified,
        "config":                    config,
        "inc_leads_qualified":       leads_qualified_total.inc,
        "inc_appointments_created":  appointments_created_total.inc,
    }

    for _ in range(5):
        t0 = time.time()
        response = _anthropic_client.messages.create(
            model=_CLAUDE_MODEL,
            max_tokens=600,
            system=_SYSTEM_CACHE,
            messages=messages,
            tools=tools,
        )
        llm_latency_seconds.observe(time.time() - t0)

        text_blocks     = [b for b in response.content if b.type == "text"]
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        content_text    = text_blocks[0].text if text_blocks else ""

        if not tool_use_blocks:
            return content_text.strip(), escalated

        messages = messages + [{"role": "assistant", "content": response.content}]

        tool_results = []
        for tool_block in tool_use_blocks:
            result = vertical.execute_tool(tool_block.name, tool_block.input or {}, context)

            if track_calls is not None:
                track_calls.append(tool_block.name)

            if tool_block.name == "escalate_to_human":
                escalations_total.inc()
                escalated = True

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": tool_block.id,
                "content":     json.dumps(result),
            })

        messages = messages + [{"role": "user", "content": tool_results}]

        if escalated:
            return "", True

    return "", escalated


def _split_and_send(phone: str, text: str) -> None:
    parts = [p.strip() for p in re.split(r'\n\s*-{3,}\s*(?:\n|$)', text) if p.strip()]
    if not parts:
        return
    for i, part in enumerate(parts):
        if i > 0:
            time.sleep(BALLOON_DELAY)
        send_message(phone, part)
        messages_sent_total.inc()


# ── Main entry point ──────────────────────────────────────────────────────────

def process_message(phone: str, text: str) -> None:
    phone_hash = hashlib.sha256(phone.encode()).hexdigest()[:12]

    if is_escalated(phone):
        log.info("message_forwarded_during_escalation", phone_hash=phone_hash)
        notify_human(phone, f"[ESCALADO — cliente enviou] {text}")
        return

    try:
        time.sleep(RESPONSE_DELAY)

        rag_context = search(text)
        rag_block   = f"\n\n[INFORMAÇÕES DA CLÍNICA RELEVANTES]\n{rag_context}" if rag_context else ""
        lead_block  = _build_lead_context(phone)
        apt_block   = _build_appointments_context(phone)
        time_block  = _temporal_context()

        history  = get_history(phone)
        messages = history + [
            {"role": "user", "content": text + rag_block + lead_block + apt_block + time_block}
        ]

        reply, escalated = _run_tool_loop(phone, messages)

        if escalated:
            save_turn(phone, text, "[ESCALADO PARA HUMANO]")
            log_escalation(phone, reason=text[:200])
            send_message(phone, "Um momento! Vou te transferir para nossa equipe agora 🙏")
            notify_human(phone, text)
            mark_escalated(phone)
            log.info("message_escalated", phone_hash=phone_hash)
            return

        if not reply:
            log.warning("empty_reply_after_tool_loop", phone_hash=phone_hash)
            reply = "Deixa eu confirmar uma coisa rápida com a equipe e já te respondo, tá? 🙏"

        save_turn(phone, text, reply)
        log.info("message_processed", phone_hash=phone_hash, reply_len=len(reply))
        _split_and_send(phone, reply)

    except Exception as e:
        errors_total.inc()
        log.error("process_message_error", phone_hash=phone_hash, error=str(e))
        save_turn(phone, text, "[ERRO TÉCNICO — ESCALADO PARA HUMANO]")
        send_message(phone, "Desculpe, tive um problema técnico aqui. Já avisei a equipe! 🙏")
        notify_human(phone, f"[ERRO TÉCNICO] Mensagem da cliente: {text}")
        mark_escalated(phone)


# ── Test entry point (golden tests) ──────────────────────────────────────────

def run_test_message(phone: str, text: str, history: list) -> dict:
    """
    Executa o loop Claude de forma síncrona sem enviar mensagens via Evolution.
    Retorna {reply, tool_calls} para o runner de golden tests.
    """
    rag_context = search(text)
    rag_block   = f"\n\n[INFORMAÇÕES DA CLÍNICA RELEVANTES]\n{rag_context}" if rag_context else ""
    lead_block  = _build_lead_context(phone)
    apt_block   = _build_appointments_context(phone)
    time_block  = _temporal_context()

    messages = history + [
        {"role": "user", "content": text + rag_block + lead_block + apt_block + time_block}
    ]

    tool_calls: list[str] = []
    reply, escalated = _run_tool_loop(phone, messages, track_calls=tool_calls)

    if escalated:
        save_turn(phone, text, "[ESCALADO PARA HUMANO]")
        log_escalation(phone, reason=text[:200])
        mark_escalated(phone)
        reply = "Um momento! Vou te transferir para nossa equipe agora 🙏"
    elif reply:
        save_turn(phone, text, reply)

    return {"reply": reply, "tool_calls": tool_calls}
