from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.db import db
from app.device_reset import request_factory_reset
from app.security import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class DeviceUpsert(BaseModel):
    device_id: str = Field(min_length=6, max_length=80)
    efuse_mac: str = Field(min_length=6, max_length=32)
    display_name: str | None = Field(default=None, max_length=120)
    firmware_version: str | None = Field(default=None, max_length=40)
    hardware_model: str | None = Field(default="m5atom-lite-rs232", max_length=80)
    site_id: UUID | None = None


class DevicePatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, pattern="^(claimed|disabled|revoked)$")
    firmware_version: str | None = Field(default=None, max_length=40)


class DeviceFactoryResetRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=200)
    delete_record: bool = False


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


@router.post("/devices", status_code=status.HTTP_201_CREATED)
def upsert_device(payload: DeviceUpsert) -> dict:
    with db() as cur:
        cur.execute(
            """
            insert into devices (device_id, efuse_mac, display_name, firmware_version, hardware_model, site_id, state)
            values (%s, %s, %s, %s, %s, %s, 'claimed')
            on conflict (device_id) do update set
              efuse_mac = excluded.efuse_mac,
              display_name = coalesce(excluded.display_name, devices.display_name),
              firmware_version = excluded.firmware_version,
              hardware_model = excluded.hardware_model,
              site_id = excluded.site_id,
              updated_at = now()
            returning *
            """,
            (
                payload.device_id,
                payload.efuse_mac.upper(),
                payload.display_name,
                payload.firmware_version,
                payload.hardware_model,
                payload.site_id,
            ),
        )
        return add_presence(cur.fetchone())


@router.get("/devices")
def list_devices() -> list[dict]:
    with db() as cur:
        cur.execute("select * from devices order by created_at desc limit 500")
        now = datetime.now(timezone.utc)
        return [add_presence(row, now) for row in cur.fetchall()]


@router.get("/devices/{device_id}")
def get_device(device_id: str) -> dict:
    with db() as cur:
        cur.execute("select * from devices where device_id = %s", (device_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="device not found")
    return add_presence(row)


@router.patch("/devices/{device_id}")
def patch_device(device_id: str, payload: DevicePatch) -> dict:
    with db() as cur:
        cur.execute(
            """
            update devices
            set display_name = coalesce(%s, display_name),
                state = coalesce(%s, state),
                firmware_version = coalesce(%s, firmware_version),
                updated_at = now()
            where device_id = %s
            returning *
            """,
            (payload.display_name, payload.state, payload.firmware_version, device_id),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="device not found")
    return add_presence(row)


@router.post("/devices/{device_id}/disable")
def disable_device(device_id: str) -> dict:
    with db() as cur:
        cur.execute(
            "update devices set state = 'disabled', updated_at = now() where device_id = %s returning *",
            (device_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="device not found")
    return add_presence(row)


@router.post("/devices/{device_id}/factory-reset")
def factory_reset_device(device_id: str, payload: DeviceFactoryResetRequest) -> dict:
    result = request_factory_reset(
        device_id=device_id,
        reason=payload.reason,
        delete_record=payload.delete_record,
        actor_type="api",
    )
    if result.get("error") == "device-not-found":
        raise HTTPException(status_code=404, detail="device not found")
    return result
