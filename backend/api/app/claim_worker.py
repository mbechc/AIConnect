import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from threading import Event
from typing import Any

import paho.mqtt.client as mqtt
from psycopg.rows import dict_row

from app.config import settings
from app.db import pool
from app.mqtt import (
    TOPIC_PREFIX,
    claim_request_topic,
    claim_response_topic,
    device_heartbeat_topic,
    device_status_topic,
)

logger = logging.getLogger(__name__)


class ClaimWorker:
    def __init__(self) -> None:
        self._stopped = Event()
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_api_client_id,
            clean_session=True,
        )
        self._client.username_pw_set("controller")
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    def start(self) -> None:
        logger.info("starting MQTT claim worker on %s:%s", settings.mqtt_host, settings.mqtt_port)
        self._client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=30)
        self._client.loop_start()

    def stop(self) -> None:
        self._stopped.set()
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        logger.info("MQTT claim worker connected: %s", reason_code)
        client.subscribe(claim_request_topic(), qos=1)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if not self._stopped.is_set():
            logger.warning("MQTT claim worker disconnected: %s", reason_code)

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except Exception as exc:
            logger.warning("invalid claim payload on %s: %s", message.topic, exc)
            return

        device_id = normalize_device_id(payload)
        response_topic = claim_response_topic(device_id or "unknown")
        try:
            result = process_claim(payload)
        except Exception as exc:
            logger.exception("claim processing failed")
            result = {
                "status": "rejected",
                "reason": "claim-processing-error",
            }

        if result.get("device_id"):
            response_topic = claim_response_topic(result["device_id"])

        client.publish(response_topic, json.dumps(result), qos=1, retain=False)
        logger.info("claim response published to %s: %s", response_topic, result.get("status"))


def normalize_device_id(payload: dict[str, Any]) -> str:
    device_id = payload.get("device_id") or payload.get("deviceId") or payload.get("client_id")
    if device_id:
        return str(device_id).strip()

    efuse_mac = payload.get("efuse_mac") or payload.get("efuseMac") or payload.get("mac")
    if efuse_mac:
        return f"esp32-{normalize_mac(str(efuse_mac)).lower()}"

    return ""


def normalize_mac(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch in "0123456789ABCDEF")


def hash_claim_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def process_claim(payload: dict[str, Any]) -> dict[str, Any]:
    device_id = normalize_device_id(payload)
    efuse_mac = normalize_mac(str(payload.get("efuse_mac") or payload.get("efuseMac") or payload.get("mac") or ""))
    claim_code = str(payload.get("claim_code") or payload.get("claimCode") or payload.get("code") or "").strip()

    if not device_id:
        return {"status": "rejected", "reason": "missing-device-id"}
    if not efuse_mac:
        return {"status": "rejected", "reason": "missing-efuse-mac", "device_id": device_id}
    if not claim_code:
        return {"status": "rejected", "reason": "missing-claim-code", "device_id": device_id}

    now = datetime.now(timezone.utc)
    mqtt_username = device_id
    mqtt_password = secrets.token_urlsafe(24)
    mqtt_password_hash = hashlib.sha256(mqtt_password.encode("utf-8")).hexdigest()

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select device_id, efuse_mac, state
                from devices
                where device_id = %s or efuse_mac = %s
                for update
                """,
                (device_id, efuse_mac),
            )
            existing_devices = list(cur.fetchall())
            for existing in existing_devices:
                if existing["device_id"] != device_id or existing["efuse_mac"] != efuse_mac:
                    audit_claim_rejected(cur, device_id, "device-identity-conflict")
                    return {"status": "rejected", "reason": "device-identity-conflict", "device_id": device_id}
                if existing["state"] in ("claimed", "disabled", "revoked"):
                    reason = f"device-already-{existing['state']}"
                    audit_claim_rejected(cur, device_id, reason)
                    return {"status": "rejected", "reason": reason, "device_id": device_id}

            cur.execute(
                """
                select id, state, site_id, expires_at
                from claim_codes
                where code_hash = %s
                for update
                """,
                (hash_claim_code(claim_code),),
            )
            claim = cur.fetchone()
            if claim is None:
                audit_claim_rejected(cur, device_id, "invalid-claim-code")
                return {"status": "rejected", "reason": "invalid-claim-code", "device_id": device_id}
            if claim["state"] == "used":
                audit_claim_rejected(cur, device_id, "used-claim-code")
                return {"status": "rejected", "reason": "used-claim-code", "device_id": device_id}
            if claim["state"] == "revoked":
                audit_claim_rejected(cur, device_id, "revoked-claim-code")
                return {"status": "rejected", "reason": "revoked-claim-code", "device_id": device_id}
            if claim["state"] == "expired" or claim["expires_at"] <= now:
                cur.execute("update claim_codes set state = 'expired' where id = %s", (claim["id"],))
                audit_claim_rejected(cur, device_id, "expired-claim-code")
                return {"status": "rejected", "reason": "expired-claim-code", "device_id": device_id}
            if claim["site_id"] is None:
                audit_claim_rejected(cur, device_id, "unassigned-claim-code")
                return {"status": "rejected", "reason": "unassigned-claim-code", "device_id": device_id}

            cur.execute(
                """
                insert into devices (
                  device_id, efuse_mac, display_name, state, site_id,
                  firmware_version, hardware_model, mqtt_username,
                  mqtt_password_hash, first_seen_at, last_seen_at, claimed_at
                )
                values (%s, %s, %s, 'claimed', %s, %s, %s, %s, %s, now(), now(), now())
                on conflict (device_id) do update set
                  efuse_mac = excluded.efuse_mac,
                  state = case
                    when devices.state = 'unclaimed' then 'claimed'
                    else devices.state
                  end,
                  site_id = excluded.site_id,
                  firmware_version = excluded.firmware_version,
                  hardware_model = excluded.hardware_model,
                  mqtt_username = excluded.mqtt_username,
                  mqtt_password_hash = excluded.mqtt_password_hash,
                  last_seen_at = now(),
                  claimed_at = coalesce(devices.claimed_at, now()),
                  updated_at = now()
                where devices.state = 'unclaimed'
                returning device_id, efuse_mac, site_id, firmware_version, hardware_model
                """,
                (
                    device_id,
                    efuse_mac,
                    payload.get("display_name") or payload.get("displayName"),
                    claim["site_id"],
                    payload.get("firmware_version") or payload.get("firmwareVersion"),
                    payload.get("hardware_model") or payload.get("hardwareModel") or "m5atom-lite-rs232",
                    mqtt_username,
                    mqtt_password_hash,
                ),
            )
            device = cur.fetchone()
            if device is None:
                audit_claim_rejected(cur, device_id, "device-already-claimed")
                return {"status": "rejected", "reason": "device-already-claimed", "device_id": device_id}

            cur.execute(
                """
                update claim_codes
                set state = 'used',
                    used_by_device_id = %s,
                    used_at = now()
                where id = %s
                """,
                (device_id, claim["id"]),
            )
            cur.execute(
                """
                insert into device_events (device_id, event_type, payload_json)
                values (%s, 'claimed', %s::jsonb)
                """,
                (device_id, json.dumps({"claim_code_id": str(claim["id"]), "source": "mqtt"})),
            )
            cur.execute(
                """
                insert into audit_events (actor_type, actor_id, action, target_type, target_id, payload_json)
                values ('device', %s, 'device.claimed', 'device', %s, %s::jsonb)
                """,
                (
                    device_id,
                    device_id,
                    json.dumps({"site_id": str(device["site_id"]), "claim_code_id": str(claim["id"])}),
                ),
            )

    return {
        "status": "accepted",
        "device_id": device["device_id"],
        "efuse_mac": device["efuse_mac"],
        "mqtt": {
            "host": "mqtts.itego.dk",
            "port": settings.mqtt_tls_port,
            "tls": True,
            "username": mqtt_username,
            "password": mqtt_password,
            "topic_prefix": TOPIC_PREFIX,
            "status_topic": device_status_topic(device_id),
            "heartbeat_topic": device_heartbeat_topic(device_id),
        },
    }


def audit_claim_rejected(cur: Any, device_id: str, reason: str) -> None:
    cur.execute(
        """
        insert into audit_events (actor_type, actor_id, action, target_type, target_id, payload_json)
        values ('device', %s, 'device.claim_rejected', 'device', %s, %s::jsonb)
        """,
        (device_id or None, device_id or None, json.dumps({"reason": reason})),
    )
