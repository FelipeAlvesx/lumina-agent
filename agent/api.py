"""
Rotas REST /api/* servidas pelo agente para o dashboard React.
Registre este blueprint no main.py via app.register_blueprint(api_bp).
"""

from flask import Blueprint, jsonify, request

import os

from sessions import (
    get_stats, get_all_leads, get_all_appointments,
    get_history, get_appointment, update_appointment,
)
from gcal import confirm_event, confirm_event_with_new_slot, delete_event
from evolution import send_message
from config import get_config
from verticals.estetica.tools import slot_label

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@api_bp.after_request
def after_request(response):
    return _cors(response)


@api_bp.route("/stats", methods=["GET", "OPTIONS"])
def stats():
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    return jsonify(get_stats())


@api_bp.route("/leads", methods=["GET", "OPTIONS"])
def leads():
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    limit  = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    data   = get_all_leads(limit=limit, offset=offset)
    return jsonify({"leads": data, "count": len(data)})


@api_bp.route("/appointments", methods=["GET", "OPTIONS"])
def appointments():
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    status    = request.args.get("status") or None
    date_from = request.args.get("date_from") or None
    date_to   = request.args.get("date_to") or None
    limit     = int(request.args.get("limit", 50))
    offset    = int(request.args.get("offset", 0))
    data      = get_all_appointments(
        status=status, date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
    return jsonify({"appointments": data, "count": len(data)})


@api_bp.route("/conversations/<phone>", methods=["GET", "OPTIONS"])
def conversations(phone: str):
    if request.method == "OPTIONS":
        return _cors(jsonify({}))
    # Aceita telefone com ou sem @s.whatsapp.net
    if not phone.endswith("@s.whatsapp.net"):
        phone = phone + "@s.whatsapp.net"
    history = get_history(phone)
    return jsonify({"phone": phone, "messages": history})


@api_bp.route("/appointments/<int:appointment_id>/confirm", methods=["POST", "OPTIONS"])
def confirm_appointment(appointment_id: int):
    if request.method == "OPTIONS":
        return _cors(jsonify({}))

    apt = get_appointment(appointment_id)
    if not apt:
        return jsonify({"error": "Agendamento não encontrado"}), 404

    config = get_config()
    tz     = config.tz
    status = apt["status"]

    if status == "pending":
        confirm_event(apt.get("external_id") or "", apt["patient_name"], apt["procedure_type"])
        update_appointment(appointment_id, status="confirmed")
        sl = slot_label(apt["slot_start"], tz)
        send_message(
            apt["phone"],
            f"Boa notícia! Seu agendamento foi confirmado 🎉\n\n"
            f"💆 {apt['procedure_type']}\n"
            f"🕐 {sl}\n\n"
            f"Qualquer dúvida, é só me chamar!",
        )
        return jsonify({"ok": True, "status": "confirmed"})

    elif status == "reschedule_requested":
        new_start = apt.get("new_slot_start")
        new_end   = apt.get("new_slot_end")
        if not new_start:
            return jsonify({"error": "Dados de remarcação não encontrados"}), 400
        confirm_event_with_new_slot(
            apt.get("external_id") or "", apt["patient_name"], apt["procedure_type"],
            new_start, new_end,
        )
        update_appointment(
            appointment_id,
            status="confirmed",
            slot_start=new_start,
            slot_end=new_end,
            new_slot_start=None,
            new_slot_end=None,
        )
        send_message(
            apt["phone"],
            f"Seu agendamento foi remarcado com sucesso!\n\n"
            f"💆 {apt['procedure_type']}\n"
            f"🕐 {slot_label(new_start, tz)}\n\n"
            f"Qualquer dúvida, é só me chamar!",
        )
        return jsonify({"ok": True, "status": "confirmed"})

    elif status == "cancel_requested":
        delete_event(apt.get("external_id") or "")
        update_appointment(appointment_id, status="cancelled")
        send_message(
            apt["phone"],
            f"Seu agendamento foi cancelado conforme solicitado.\n"
            f"Se quiser agendar em outro momento, é só me chamar 😊",
        )
        return jsonify({"ok": True, "status": "cancelled"})

    return jsonify({"error": f"Status '{status}' não permite confirmação"}), 400


@api_bp.route("/appointments/<int:appointment_id>/reject", methods=["POST", "OPTIONS"])
def reject_appointment(appointment_id: int):
    if request.method == "OPTIONS":
        return _cors(jsonify({}))

    apt    = get_appointment(appointment_id)
    if not apt:
        return jsonify({"error": "Agendamento não encontrado"}), 404

    reason = (request.json or {}).get("reason", "") if request.is_json else ""
    status = apt["status"]

    if status in ("pending", "reschedule_requested"):
        if status == "reschedule_requested":
            update_appointment(appointment_id, status="confirmed", new_slot_start=None, new_slot_end=None)
            patient_msg = (
                f"Infelizmente não conseguimos remarcar para esse horário 😕\n"
                + (f"Motivo: {reason}\n\n" if reason else "\n")
                + "Quer tentar outro horário? É só me dizer!"
            )
        else:
            delete_event(apt.get("external_id") or "")
            update_appointment(appointment_id, status="rejected")
            patient_msg = (
                f"Infelizmente não conseguimos confirmar esse horário 😕\n"
                + (f"Motivo: {reason}\n\n" if reason else "\n")
                + "Quer tentar outro dia ou horário? É só me dizer!"
            )
        send_message(apt["phone"], patient_msg)
        return jsonify({"ok": True, "status": "rejected"})

    elif status == "cancel_requested":
        update_appointment(appointment_id, status="confirmed")
        send_message(
            apt["phone"],
            "Não conseguimos processar o cancelamento agora.\n"
            + (f"Motivo: {reason}\n\n" if reason else "\n")
            + "Seu agendamento continua confirmado. Precisa de outra ajuda?",
        )
        return jsonify({"ok": True, "status": "confirmed"})

    return jsonify({"error": f"Status '{status}' não permite rejeição"}), 400


@api_bp.route("/test/message", methods=["POST", "OPTIONS"])
def test_message():
    """Endpoint exclusivo para golden tests — não envia mensagens via WhatsApp."""
    if request.method == "OPTIONS":
        return _cors(jsonify({}))

    if os.getenv("FLASK_ENV") == "production":
        return jsonify({"error": "Endpoint disponível apenas em modo de teste"}), 403

    data    = request.get_json(force=True) or {}
    phone   = data.get("phone", "test@s.whatsapp.net")
    text    = data.get("text", "")
    history = data.get("history", [])

    if not phone.endswith("@s.whatsapp.net"):
        phone = phone + "@s.whatsapp.net"

    from agent_core import run_test_message
    result = run_test_message(phone, text, history)
    return jsonify(result)
