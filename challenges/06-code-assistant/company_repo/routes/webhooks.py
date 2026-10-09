"""Inbound carrier status callbacks."""
from flask import Blueprint, jsonify, request

from utils.auth import verify_webhook
from utils.formatting import normalise_tracking

webhooks_bp = Blueprint("webhooks", __name__)

ACCEPTED_EVENTS = ("parcel.scanned", "parcel.delivered", "parcel.exception")


@webhooks_bp.route("/carrier", methods=["POST"])
def carrier_callback():
    signature = request.headers.get("X-Signature", "")
    timestamp = request.headers.get("X-Timestamp", "")
    body = request.get_data(as_text=True)

    if not verify_webhook(signature, timestamp, body):
        return jsonify({"error": "bad signature"}), 401

    event = request.get_json(silent=True) or {}
    event_type = event.get("type")
    if event_type not in ACCEPTED_EVENTS:
        return jsonify({"error": f"unsupported event: {event_type}"}), 400

    tracking = normalise_tracking(event.get("tracking", ""))
    if not tracking:
        return jsonify({"error": "missing tracking"}), 400

    # Downstream fan-out is handled by the warehouse queue consumer.
    return jsonify({"accepted": True, "tracking": tracking,
                    "type": event_type}), 202
