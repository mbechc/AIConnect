from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db import db
from app.mqtt import session_topic
from app.security import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class SessionCreate(BaseModel):
    baud: int = Field(default=9600, ge=1200, le=921600)
    data_bits: int = Field(default=8, ge=5, le=8)
    parity: str = Field(default="none", pattern="^(none|even|odd)$")
    stop_bits: int = Field(default=1, ge=1, le=2)
    flow_control: str = Field(default="none", pattern="^(none|rtscts)$")


class SessionTx(BaseModel):
    data_base64: str = Field(min_length=1)
    seq: int | None = None


@router.post("/devices/{device_id}/sessions", status_code=status.HTTP_201_CREATED)
def create_session(device_id: str, payload: SessionCreate) -> dict:
    with db() as cur:
        cur.execute("select id from devices where device_id = %s and state = 'claimed'", (device_id,))
        device = cur.fetchone()
        if device is None:
            raise HTTPException(status_code=404, detail="claimed device not found")
        cur.execute(
            """
            select id from serial_sessions
            where device_id = %s and state in ('opening', 'active')
            limit 1
            """,
            (device_id,),
        )
        if cur.fetchone() is not None:
            raise HTTPException(status_code=409, detail="device already has an active session")
        cur.execute(
            """
            insert into serial_sessions (device_id, state, baud, data_bits, parity, stop_bits, flow_control)
            values (%s, 'opening', %s, %s, %s, %s, %s)
            returning *
            """,
            (
                device_id,
                payload.baud,
                payload.data_bits,
                payload.parity,
                payload.stop_bits,
                payload.flow_control,
            ),
        )
        row = cur.fetchone()
    row["mqtt_open_topic"] = session_topic(device_id, str(row["id"]), "open")
    return row


@router.get("/devices/{device_id}/sessions")
def list_device_sessions(device_id: str) -> list[dict]:
    with db() as cur:
        cur.execute(
            "select * from serial_sessions where device_id = %s order by created_at desc limit 100",
            (device_id,),
        )
        return list(cur.fetchall())


@router.get("/sessions/{session_id}")
def get_session(session_id: UUID) -> dict:
    with db() as cur:
        cur.execute("select * from serial_sessions where id = %s", (session_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    return row


@router.post("/sessions/{session_id}/tx", status_code=status.HTTP_202_ACCEPTED)
def record_tx(session_id: UUID, payload: SessionTx) -> dict:
    with db() as cur:
        cur.execute("select id, device_id from serial_sessions where id = %s", (session_id,))
        session = cur.fetchone()
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        cur.execute(
            """
            insert into serial_session_logs (session_id, direction, payload_base64, byte_count)
            values (%s, 'tx', %s, length(decode(%s, 'base64')))
            returning id, created_at
            """,
            (session_id, payload.data_base64, payload.data_base64),
        )
        row = cur.fetchone()
    return {
        **row,
        "mqtt_tx_topic": session_topic(session["device_id"], str(session_id), "tx"),
        "seq": payload.seq,
    }


@router.post("/sessions/{session_id}/close")
def close_session(session_id: UUID) -> dict:
    with db() as cur:
        cur.execute(
            """
            update serial_sessions
            set state = 'closed', closed_at = now(), close_reason = 'api-request', updated_at = now()
            where id = %s
            returning *
            """,
            (session_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    row["mqtt_close_topic"] = session_topic(row["device_id"], str(session_id), "close")
    return row


@router.get("/sessions/{session_id}/log")
def get_session_log(session_id: UUID) -> list[dict]:
    with db() as cur:
        cur.execute(
            """
            select id, direction, payload_base64, payload_text_preview, byte_count, created_at
            from serial_session_logs
            where session_id = %s
            order by created_at asc, id asc
            limit 5000
            """,
            (session_id,),
        )
        return list(cur.fetchall())
