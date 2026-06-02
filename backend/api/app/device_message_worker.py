import json
import logging
from threading import Event
from typing import Any

import paho.mqtt.client as mqtt
from psycopg.rows import dict_row

from app.config import settings
from app.db import pool
from app.mqtt import TOPIC_PREFIX

logger = logging.getLogger(__name__)

DEVICE_ORIGIN_SUBSCRIPTIONS = (
    f"{TOPIC_PREFIX}/devices/+/heartbeat",
    f"{TOPIC_PREFIX}/devices/+/status",
    f"{TOPIC_PREFIX}/devices/+/event",
    f"{TOPIC_PREFIX}/devices/+/sessions/+/rx",
    f"{TOPIC_PREFIX}/devices/+/sessions/+/opened",
    f"{TOPIC_PREFIX}/devices/+/sessions/+/closed",
    f"{TOPIC_PREFIX}/devices/+/sessions/+/event",
)


class DeviceMessageWorker:
    def __init__(self) -> None:
        self._stopped = Event()
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_device_events_client_id,
            clean_session=True,
        )
        self._client.username_pw_set("controller")
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    def start(self) -> None:
        logger.info("starting MQTT device message worker on %s:%s", settings.mqtt_host, settings.mqtt_port)
        self._client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=30)
        self._client.loop_start()

    def stop(self) -> None:
        self._stopped.set()
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        logger.info("MQTT device message worker connected: %s", reason_code)
        for topic in DEVICE_ORIGIN_SUBSCRIPTIONS:
            client.subscribe(topic, qos=1)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if not self._stopped.is_set():
            logger.warning("MQTT device message worker disconnected: %s", reason_code)

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        parsed = parse_device_origin_topic(message.topic)
        if parsed is None:
            logger.warning("ignoring invalid device-origin topic: %s", message.topic)
            return

        device_id = parsed["device_id"]
        payload = decode_optional_json(message.payload)
        if not is_valid_device_message(parsed, payload):
            logger.warning("ignoring invalid device message on %s", message.topic)
            return

        firmware_version = payload.get("firmware_version") if isinstance(payload, dict) else None
        touched = touch_device_last_seen(device_id, firmware_version)
        if not touched:
            logger.warning("ignoring message from unknown or inactive device: %s", device_id)


def parse_device_origin_topic(topic: str) -> dict[str, str] | None:
    parts = topic.split("/")
    prefix_parts = TOPIC_PREFIX.split("/")
    if parts[: len(prefix_parts)] != prefix_parts:
        return None
    rest = parts[len(prefix_parts) :]
    if len(rest) < 3 or rest[0] != "devices":
        return None

    device_id = rest[1]
    if not device_id:
        return None

    if len(rest) == 3 and rest[2] in {"heartbeat", "status", "event"}:
        return {"device_id": device_id, "kind": rest[2]}

    if len(rest) == 5 and rest[2] == "sessions" and rest[4] in {"rx", "opened", "closed", "event"}:
        return {"device_id": device_id, "kind": f"session.{rest[4]}", "session_id": rest[3]}

    return None


def decode_optional_json(payload: bytes) -> dict[str, Any] | None:
    if not payload:
        return None
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def is_valid_device_message(parsed: dict[str, str], payload: dict[str, Any] | None) -> bool:
    kind = parsed["kind"]
    topic_device_id = parsed["device_id"]

    if kind == "heartbeat":
        if payload is None:
            return False
        if str(payload.get("device_id") or "") != topic_device_id:
            return False
        if "seq" in payload and not isinstance(payload["seq"], int):
            return False
        if "uptime_ms" in payload and not isinstance(payload["uptime_ms"], int):
            return False
        if "wifi_rssi" in payload and not isinstance(payload["wifi_rssi"], int | float):
            return False
        if payload.get("state") not in (None, "claimed"):
            return False
        return True

    if payload is not None and payload.get("device_id") is not None:
        return str(payload["device_id"]) == topic_device_id

    return True


def touch_device_last_seen(device_id: str, firmware_version: Any = None) -> bool:
    firmware = firmware_version if isinstance(firmware_version, str) and firmware_version else None
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                update devices
                set last_seen_at = now(),
                    first_seen_at = coalesce(first_seen_at, now()),
                    firmware_version = coalesce(%s, firmware_version),
                    updated_at = now()
                where device_id = %s
                  and state = 'claimed'
                returning device_id
                """,
                (firmware, device_id),
            )
            return cur.fetchone() is not None
