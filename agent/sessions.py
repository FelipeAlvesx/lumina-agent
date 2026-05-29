"""
Gerencia histórico de conversas e dados de lead por telefone usando SQLite.
TTL de 30 minutos: conversa inativa por mais que isso começa do zero.
"""

import sqlite3
import time
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "/app/data/sessions.db")
TTL_SECONDS = 30 * 60
MAX_TURNS = 10


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            phone    TEXT    NOT NULL,
            role     TEXT    NOT NULL,
            content  TEXT    NOT NULL,
            ts       REAL    NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_phone_ts ON sessions(phone, ts)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lead_data (
            phone TEXT NOT NULL,
            field TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (phone, field)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            phone           TEXT    NOT NULL,
            patient_name    TEXT    NOT NULL DEFAULT '',
            procedure_type  TEXT    NOT NULL DEFAULT '',
            slot_start      TEXT    NOT NULL,
            slot_end        TEXT    NOT NULL,
            new_slot_start  TEXT,
            new_slot_end    TEXT,
            notes           TEXT    NOT NULL DEFAULT '',
            status          TEXT    NOT NULL DEFAULT 'pending',
            external_id     TEXT,
            created_at      REAL    NOT NULL,
            updated_at      REAL    NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_apt_phone ON appointments(phone)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_apt_status ON appointments(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_apt_slot ON appointments(slot_start)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            phone      TEXT NOT NULL,
            reason     TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_esc_phone ON escalations(phone)")
    conn.commit()
    return conn


# ── Session history ───────────────────────────────────────────────────────────

def get_history(phone: str) -> list[dict]:
    cutoff = time.time() - TTL_SECONDS
    conn = _get_conn()
    rows = conn.execute(
        """SELECT role, content FROM sessions
           WHERE phone = ? AND ts > ?
           ORDER BY ts ASC""",
        (phone, cutoff)
    ).fetchall()
    conn.close()
    history = [{"role": row[0], "content": row[1]} for row in rows]
    max_msgs = MAX_TURNS * 2
    return history[-max_msgs:] if len(history) > max_msgs else history


def save_turn(phone: str, user_text: str, assistant_text: str) -> None:
    now = time.time()
    conn = _get_conn()
    conn.executemany(
        "INSERT INTO sessions (phone, role, content, ts) VALUES (?, ?, ?, ?)",
        [
            (phone, "user",      user_text,      now),
            (phone, "assistant", assistant_text, now + 0.001),
        ]
    )
    conn.commit()
    conn.close()


def clear_history(phone: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM sessions WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()


# ── Lead qualification ────────────────────────────────────────────────────────

def get_lead_data(phone: str) -> dict:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT field, value FROM lead_data WHERE phone = ?", (phone,)
    ).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def save_lead_field(phone: str, field: str, value: str) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO lead_data (phone, field, value) VALUES (?, ?, ?)",
        (phone, field, value)
    )
    conn.commit()
    conn.close()


def is_lead_qualified(phone: str, lead_fields: tuple) -> bool:
    data = get_lead_data(phone)
    return all(f in data for f in lead_fields)


def get_all_leads(limit: int = 100, offset: int = 0) -> list[dict]:
    """Retorna todos os leads com seus dados de qualificação agregados."""
    conn = _get_conn()
    phones = conn.execute(
        """SELECT DISTINCT phone FROM lead_data
           ORDER BY rowid DESC LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()

    leads = []
    for (phone,) in phones:
        rows = conn.execute(
            "SELECT field, value FROM lead_data WHERE phone = ?", (phone,)
        ).fetchall()
        data = {r[0]: r[1] for r in rows}
        # Last contact timestamp from sessions
        last_ts = conn.execute(
            "SELECT MAX(ts) FROM sessions WHERE phone = ?", (phone,)
        ).fetchone()[0]
        leads.append({
            "phone": phone,
            "nome": data.get("nome", ""),
            "procedimento_interesse": data.get("procedimento_interesse", ""),
            "indicacao": data.get("indicacao", ""),
            "qualified": all(f in data for f in ("nome", "procedimento_interesse", "indicacao")),
            "last_contact": last_ts,
        })
    conn.close()
    return leads


# ── Appointments ──────────────────────────────────────────────────────────────

def _rows_to_dicts(cursor, rows: list) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


def create_appointment(
    phone: str,
    patient_name: str,
    procedure_type: str,
    slot_start: str,
    slot_end: str,
    notes: str = "",
) -> int:
    now = time.time()
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO appointments
           (phone, patient_name, procedure_type, slot_start, slot_end, notes, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (phone, patient_name, procedure_type, slot_start, slot_end, notes, now, now),
    )
    conn.commit()
    apt_id = cursor.lastrowid
    conn.close()
    return apt_id


def get_appointment(appointment_id: int) -> dict | None:
    conn = _get_conn()
    cur = conn.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    row = cur.fetchone()
    result = _rows_to_dicts(cur, [row])[0] if row else None
    conn.close()
    return result


def get_patient_appointments(phone: str) -> list[dict]:
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM appointments WHERE phone = ? ORDER BY created_at DESC LIMIT 10",
        (phone,),
    )
    result = _rows_to_dicts(cur, cur.fetchall())
    conn.close()
    return result


def update_appointment(appointment_id: int, **fields) -> bool:
    if not fields:
        return False
    fields["updated_at"] = time.time()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [appointment_id]
    conn = _get_conn()
    cursor = conn.execute(f"UPDATE appointments SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def get_all_appointments(status: str | None = None, date_from: str | None = None,
                          date_to: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
    """Retorna agendamentos com filtros opcionais."""
    conditions = []
    params: list = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if date_from:
        conditions.append("slot_start >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("slot_start <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]

    conn = _get_conn()
    cur = conn.execute(
        f"SELECT * FROM appointments {where} ORDER BY slot_start DESC LIMIT ? OFFSET ?",
        params,
    )
    result = _rows_to_dicts(cur, cur.fetchall())
    conn.close()
    return result


def get_confirmed_appointments_tomorrow() -> list[dict]:
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    day_end  = (now.date() + timedelta(days=2)).isoformat()
    conn = _get_conn()
    cur = conn.execute(
        """SELECT * FROM appointments
           WHERE status = 'confirmed'
             AND slot_start >= ? AND slot_start < ?
           ORDER BY slot_start""",
        (tomorrow, day_end),
    )
    result = _rows_to_dicts(cur, cur.fetchall())
    conn.close()
    return result


# ── Escalations ───────────────────────────────────────────────────────────────

def log_escalation(phone: str, reason: str = "") -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO escalations (phone, reason, created_at) VALUES (?, ?, ?)",
        (phone, reason, time.time()),
    )
    conn.commit()
    conn.close()


# ── Stats for dashboard ───────────────────────────────────────────────────────

def get_stats() -> dict:
    conn = _get_conn()

    total_leads = conn.execute(
        "SELECT COUNT(DISTINCT phone) FROM lead_data"
    ).fetchone()[0]

    total_qualified = conn.execute(
        """SELECT COUNT(*) FROM (
             SELECT phone FROM lead_data
             GROUP BY phone
             HAVING COUNT(DISTINCT field) >= 3
           )"""
    ).fetchone()[0]

    total_appointments = conn.execute(
        "SELECT COUNT(*) FROM appointments"
    ).fetchone()[0]

    pending_appointments = conn.execute(
        "SELECT COUNT(*) FROM appointments WHERE status = 'pending'"
    ).fetchone()[0]

    confirmed_appointments = conn.execute(
        "SELECT COUNT(*) FROM appointments WHERE status = 'confirmed'"
    ).fetchone()[0]

    total_escalations = conn.execute(
        "SELECT COUNT(*) FROM escalations"
    ).fetchone()[0]

    conn.close()
    return {
        "leads_total": total_leads,
        "leads_qualified": total_qualified,
        "appointments_total": total_appointments,
        "appointments_pending": pending_appointments,
        "appointments_confirmed": confirmed_appointments,
        "escalations_total": total_escalations,
    }
