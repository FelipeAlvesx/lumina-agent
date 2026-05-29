"""
Google Calendar backend para agendamento de procedimentos estéticos.
Usa Service Account — sem OAuth interativo.
"""

import os
from datetime import datetime, date, time, timedelta

import structlog

from config import get_config

log = structlog.get_logger()

# Lumina funciona de segunda a sábado, das 9h às 19h
BUSINESS_START = 9
BUSINESS_END   = 19

_WEEKDAYS_PT = [
    "segunda-feira", "terça-feira", "quarta-feira",
    "quinta-feira", "sexta-feira", "sábado", "domingo",
]


def is_configured() -> bool:
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "/app/credentials/google_credentials.json")
    return os.path.isfile(creds_path) and bool(get_config().calendar_id)


def _get_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "/app/credentials/google_credentials.json")
    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _parse_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(get_config().tz)


def list_available_slots(date_range: str, procedure_type: str | None = None) -> dict:
    """
    Retorna até 3 slots livres no intervalo pedido.
    date_range: 'YYYY-MM-DD' ou 'YYYY-MM-DD/YYYY-MM-DD'.
    """
    if not is_configured():
        return {"error": "Calendário não configurado. Entre em contato com a recepção."}

    try:
        cfg = get_config()
        calendar_id   = cfg.calendar_id
        slot_duration = cfg.slot_duration
        tz            = cfg.tz
        service       = _get_service()

        if "/" in date_range:
            start_str, end_str = date_range.split("/", 1)
            start_date = date.fromisoformat(start_str)
            end_date   = date.fromisoformat(end_str)
        else:
            start_date = date.fromisoformat(date_range)
            end_date   = start_date + timedelta(days=6)

        time_min = datetime.combine(start_date, time(0, 0), tzinfo=tz).isoformat()
        time_max = datetime.combine(end_date + timedelta(days=1), time(0, 0), tzinfo=tz).isoformat()

        freebusy = service.freebusy().query(body={
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": calendar_id}],
            "timeZone": cfg.timezone,
        }).execute()

        busy_raw = freebusy.get("calendars", {}).get(calendar_id, {}).get("busy", [])
        busy = [(_parse_dt(b["start"]), _parse_dt(b["end"])) for b in busy_raw]

        now       = datetime.now(tz)
        available = []
        current   = start_date

        while current <= end_date and len(available) < 3:
            # Lumina abre segunda (0) a sábado (5)
            if current.weekday() > 5:
                current += timedelta(days=1)
                continue

            slot    = datetime.combine(current, time(BUSINESS_START, 0), tzinfo=tz)
            day_end = datetime.combine(current, time(BUSINESS_END, 0), tzinfo=tz)

            while slot + timedelta(minutes=slot_duration) <= day_end and len(available) < 3:
                slot_end = slot + timedelta(minutes=slot_duration)
                if slot > now:
                    occupied = any(slot < be and slot_end > bs for bs, be in busy)
                    if not occupied:
                        weekday = _WEEKDAYS_PT[current.weekday()]
                        available.append({
                            "slot_start": slot.isoformat(),
                            "slot_end":   slot_end.isoformat(),
                            "label": f"{weekday}, {current.strftime('%d/%m')} às {slot.strftime('%H:%M')}",
                        })
                slot += timedelta(minutes=slot_duration)

            current += timedelta(days=1)

        if not available:
            return {"slots": [], "message": "Nenhum horário disponível no período. Tente outro intervalo."}

        return {"slots": available}

    except Exception as e:
        log.error("gcal_list_slots_error", error=str(e))
        return {"error": f"Erro ao consultar calendário: {str(e)}"}


def create_pending_event(appointment_id: int, patient_name: str, procedure_type: str,
                          slot_start: str, slot_end: str, notes: str = "") -> dict:
    if not is_configured():
        return {"ok": True, "external_id": None}

    try:
        cfg         = get_config()
        calendar_id = cfg.calendar_id
        service     = _get_service()

        description = f"Agendamento #{appointment_id}\nPaciente: {patient_name}\nProcedimento: {procedure_type}"
        if notes:
            description += f"\nObs: {notes}"

        event = {
            "summary":     f"[PENDENTE] {procedure_type} — {patient_name}",
            "description": description,
            "start": {"dateTime": slot_start, "timeZone": cfg.timezone},
            "end":   {"dateTime": slot_end,   "timeZone": cfg.timezone},
            "status": "tentative",
        }

        created = service.events().insert(calendarId=calendar_id, body=event).execute()
        return {"ok": True, "external_id": created["id"]}

    except Exception as e:
        log.error("gcal_create_event_error", error=str(e))
        return {"ok": True, "external_id": None}


def confirm_event(external_id: str, patient_name: str, procedure_type: str) -> dict:
    if not external_id or not is_configured():
        return {"ok": True}

    try:
        cfg         = get_config()
        calendar_id = cfg.calendar_id
        service     = _get_service()

        event = service.events().get(calendarId=calendar_id, eventId=external_id).execute()
        event["status"]  = "confirmed"
        event["summary"] = f"{procedure_type} — {patient_name}"
        service.events().update(calendarId=calendar_id, eventId=external_id, body=event).execute()
        return {"ok": True}

    except Exception as e:
        log.error("gcal_confirm_event_error", error=str(e))
        return {"ok": True}


def confirm_event_with_new_slot(external_id: str, patient_name: str, procedure_type: str,
                                 new_slot_start: str, new_slot_end: str) -> dict:
    if not external_id or not is_configured():
        return {"ok": True}

    try:
        cfg         = get_config()
        calendar_id = cfg.calendar_id
        service     = _get_service()

        event = service.events().get(calendarId=calendar_id, eventId=external_id).execute()
        event["status"]  = "confirmed"
        event["summary"] = f"{procedure_type} — {patient_name}"
        event["start"]   = {"dateTime": new_slot_start, "timeZone": cfg.timezone}
        event["end"]     = {"dateTime": new_slot_end,   "timeZone": cfg.timezone}
        service.events().update(calendarId=calendar_id, eventId=external_id, body=event).execute()
        return {"ok": True}

    except Exception as e:
        log.error("gcal_reschedule_confirm_error", error=str(e))
        return {"ok": True}


def delete_event(external_id: str) -> dict:
    if not external_id or not is_configured():
        return {"ok": True}

    try:
        calendar_id = get_config().calendar_id
        service     = _get_service()
        service.events().delete(calendarId=calendar_id, eventId=external_id).execute()
        return {"ok": True}

    except Exception as e:
        log.error("gcal_delete_event_error", error=str(e))
        return {"ok": True}
