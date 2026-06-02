import json
import secrets
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt
from psycopg.rows import dict_row

from app.config import settings
from app.db import pool
from app.mqtt import device_factory_reset_topic
from app.serial_audit import log_serial_event


def add_presence(row: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    last_seen_at = row.get("last_seen_at")
    if last_seen_at is None:
        presence = "never_seen"
        online = False
        seconds_since_last_seen = None
    else:
        if last_seen_at.tzinfo is None:
            last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
        seconds_since_last_seen = max(0, int((now - last_seen_at).total_seconds()))
        online = seconds_since_last_seen <= settings.device_online_freshness_seconds
        presence = "online" if online else "stale"

    return {
        **row,
        "online": online,
        "presence": presence,
        "seconds_since_last_seen": seconds_since_last_seen,
        "online_freshness_seconds": settings.device_online_freshness_seconds,
    }


def publish_mqtt(topic: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{settings.mqtt_api_client_id}-reset-{secrets.token_hex(3)}",
        clean_session=True,
    )
    client.username_pw_set(settings.mqtt_backend_username, settings.mqtt_backend_password)
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    client.loop_start()
    try:
        result = client.publish(topic, json.dumps(payload), qos=1, retain=False)
        result.wait_for_publish(timeout=5)
    finally:
        client.loop_stop()
        client.disconnect()
    return {"topic": topic, "published": result.is_published(), "rc": result.rc}


def request_factory_reset(
    device_id: str,
    reason: str | None = None,
    delete_record: bool = False,
    actor_type: str = "api",
) -> dict[str, Any]:
    reason = reason or "operator-request"
    requested_at = datetime.now(timezone.utc)
    requested_at_text = requested_at.isoformat().replace("+00:00", "Z")

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from devices where device_id = %s for update", (device_id,))
            device = cur.fetchone()
            if device is None:
                return {"error": "device-not-found"}

            presence = add_presence(dict(device), requested_at)
            should_publish = device["state"] == "claimed" and presence["online"]
            command_payload = {
                "command": "factory_reset",
                "device_id": device_id,
                "reason": reason,
                "requested_at": requested_at_text,
                "delete_record": delete_record,
            }

            cur.execute(
                """
                update serial_sessions
                set state = 'failed',
                    closed_at = now(),
                    close_reason = 'factory-reset-requested',
                    updated_at = now()
                where device_id = %s
                  and state in ('opening', 'active', 'closing')
                returning id
                """,
                (device_id,),
            )
            closed_session_ids = [str(row["id"]) for row in cur.fetchall()]
            for session_id in closed_session_ids:
                log_serial_event(
                    cur,
                    session_id,
                    device_id,
                    "factory_reset_requested",
                    actor_type=actor_type,
                    metadata={"reason": reason, "delete_record": delete_record},
                )

            cur.execute(
                """
                update devices
                set state = 'revoked',
                    mqtt_username = null,
                    mqtt_password_hash = null,
                    certificate_fingerprint = null,
                    updated_at = now()
                where device_id = %s
                returning *
                """,
                (device_id,),
            )
            updated_device = cur.fetchone()

            delivery_state = "will_publish" if should_publish else "not_delivered"
            audit_payload = {
                "reason": reason,
                "requested_at": requested_at_text,
                "delete_record_requested": delete_record,
                "hard_delete_performed": False,
                "delivery_state": delivery_state,
                "previous_state": device["state"],
                "was_online": presence["online"],
                "closed_session_ids": closed_session_ids,
                "mqtt_topic": device_factory_reset_topic(device_id),
            }
            cur.execute(
                """
                insert into audit_events (actor_type, action, target_type, target_id, payload_json)
                values (%s, 'device.factory_reset_requested', 'device', %s, %s::jsonb)
                returning id, created_at
                """,
                (actor_type, device_id, json.dumps(audit_payload)),
            )
            audit_event = cur.fetchone()

    mqtt_result = None
    if should_publish:
        mqtt_result = publish_mqtt(device_factory_reset_topic(device_id), command_payload)
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    update audit_events
                    set payload_json = payload_json || %s::jsonb
                    where id = %s
                    """,
                    (
                        json.dumps(
                            {
                                "delivery_state": "published" if mqtt_result["published"] else "publish_failed",
                                "mqtt": mqtt_result,
                            }
                        ),
                        audit_event["id"],
                    ),
                )

    return {
        "device": add_presence(dict(updated_device), requested_at),
        "command": command_payload,
        "audit_event": {"id": audit_event["id"], "created_at": audit_event["created_at"]},
        "closed_session_ids": closed_session_ids,
        "delivery_state": "published" if mqtt_result and mqtt_result["published"] else delivery_state,
        "mqtt": mqtt_result,
        "delete_record_requested": delete_record,
        "hard_delete_performed": False,
        "history_preserved": True,
    }
