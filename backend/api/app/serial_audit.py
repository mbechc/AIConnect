import base64
import binascii
import json
from typing import Any
from uuid import UUID


def text_preview(data: bytes, limit: int = 200) -> str:
    return data[:limit].decode("utf-8", errors="replace")


def decode_base64(data_base64: str) -> bytes:
    try:
        return base64.b64decode(data_base64, validate=True)
    except binascii.Error as exc:
        raise ValueError("invalid-base64") from exc


def encode_text(text: str) -> tuple[str, bytes]:
    data = text.encode("utf-8")
    return base64.b64encode(data).decode("ascii"), data


def log_serial_payload(
    cur: Any,
    session_id: str | UUID,
    device_id: str,
    direction: str,
    payload_base64: str | None,
    actor_type: str,
    actor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    byte_count = 0
    preview = None
    if payload_base64:
        decoded = decode_base64(payload_base64)
        byte_count = len(decoded)
        preview = text_preview(decoded)

    cur.execute(
        """
        insert into serial_session_logs (
          session_id, device_id, actor_type, actor_id, direction,
          payload_base64, payload_text_preview, byte_count, metadata_json
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        returning id, session_id, device_id, actor_type, actor_id, direction,
                  payload_base64, payload_text_preview, byte_count, metadata_json, created_at
        """,
        (
            session_id,
            device_id,
            actor_type,
            actor_id,
            direction,
            payload_base64,
            preview,
            byte_count,
            json.dumps(metadata or {}),
        ),
    )
    return cur.fetchone()


def log_serial_event(
    cur: Any,
    session_id: str | UUID,
    device_id: str,
    event: str,
    actor_type: str,
    actor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_metadata = {"event": event, **(metadata or {})}
    return log_serial_payload(
        cur=cur,
        session_id=session_id,
        device_id=device_id,
        direction="event",
        payload_base64=None,
        actor_type=actor_type,
        actor_id=actor_id,
        metadata=event_metadata,
    )


def find_active_session(cur: Any, session_id: str | UUID) -> dict[str, Any] | None:
    cur.execute(
        """
        select s.id, s.device_id
        from serial_sessions s
        join devices d on d.device_id = s.device_id
        where s.id = %s
          and s.state in ('opening', 'active')
          and d.state = 'claimed'
        """,
        (session_id,),
    )
    return cur.fetchone()
