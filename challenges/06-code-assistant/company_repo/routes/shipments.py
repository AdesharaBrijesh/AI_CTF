"""Shipment CRUD and tracking lookups."""
import requests
from flask import Blueprint, jsonify, request

from config import settings
from utils.auth import build_auth_headers, redact
from utils.formatting import (
    clamp_page_size,
    format_for_display,
    is_valid_tracking,
    normalise_tracking,
)

shipments_bp = Blueprint("shipments", __name__)

# Stand-in for the real datastore layer.
_SHIPMENTS = {
    "LRK123456789012": {"status": "in_transit", "destination": "Rotterdam, NL"},
    "LKS99887766554433": {"status": "delivered", "destination": "Leeds, UK"},
}


@shipments_bp.route("", methods=["GET"])
def list_shipments():
    page_size = clamp_page_size(request.args.get("page_size"))
    items = [
        {"tracking": format_for_display(t), "status": s["status"],
         "destination": s["destination"]}
        for t, s in list(_SHIPMENTS.items())[:page_size]
    ]
    return jsonify({"count": len(items), "items": items})


@shipments_bp.route("/<tracking>", methods=["GET"])
def get_shipment(tracking):
    if not is_valid_tracking(tracking):
        return jsonify({"error": "invalid tracking number"}), 400
    key = normalise_tracking(tracking)
    record = _SHIPMENTS.get(key)
    if not record:
        return jsonify({"error": "not found"}), 404
    return jsonify({"tracking": format_for_display(key), **record})


@shipments_bp.route("/<tracking>/refresh", methods=["POST"])
def refresh_from_carrier(tracking):
    """Pull the latest status straight from the carrier API."""
    if not is_valid_tracking(tracking):
        return jsonify({"error": "invalid tracking number"}), 400
    key = normalise_tracking(tracking)
    try:
        resp = requests.get(
            f"{settings.CARRIER_API_BASE}/parcels/{key}",
            headers=build_auth_headers(),
            timeout=settings.CARRIER_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        # Never log the key itself — redact() keeps it out of the log stream.
        print(f"carrier refresh failed for {key} "
              f"(key={redact(build_auth_headers()['X-Api-Key'])}): {exc}")
        return jsonify({"error": "carrier unavailable"}), 502

    payload = resp.json()
    _SHIPMENTS.setdefault(key, {})["status"] = payload.get("status", "unknown")
    return jsonify({"tracking": format_for_display(key),
                    "status": _SHIPMENTS[key]["status"]})
