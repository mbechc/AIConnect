import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db import db
from app.security import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class ClaimCodeCreate(BaseModel):
    code: str | None = Field(default=None, min_length=6, max_length=64)
    site_id: UUID
    expires_in_hours: int = Field(default=24, ge=1, le=24 * 30)
    note: str | None = Field(default=None, max_length=200)


def hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


@router.post("/claim-codes", status_code=status.HTTP_201_CREATED)
def create_claim_code(payload: ClaimCodeCreate) -> dict:
    code = payload.code or f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours)
    with db() as cur:
        cur.execute("select id from sites where id = %s", (payload.site_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="site not found")
        cur.execute(
            """
            insert into claim_codes (code_hash, site_id, expires_at, note)
            values (%s, %s, %s, %s)
            returning id, state, site_id, expires_at, note, created_at
            """,
            (hash_code(code), payload.site_id, expires_at, payload.note),
        )
        row = cur.fetchone()
        cur.execute(
            """
            insert into audit_events (actor_type, action, target_type, target_id, payload_json)
            values ('api', 'claim_code.created', 'claim_code', %s, %s::jsonb)
            """,
            (str(row["id"]), json.dumps({"site_id": str(payload.site_id)})),
        )
    return {"code": code, **row}


@router.get("/claim-codes")
def list_claim_codes() -> list[dict]:
    with db() as cur:
        cur.execute(
            """
            select id, state, site_id, expires_at, used_by_device_id, used_at, note, created_at
            from claim_codes
            order by created_at desc
            limit 200
            """
        )
        return list(cur.fetchall())


@router.post("/claim-codes/{claim_code_id}/revoke")
def revoke_claim_code(claim_code_id: UUID) -> dict:
    with db() as cur:
        cur.execute(
            """
            update claim_codes
            set state = 'revoked'
            where id = %s and state = 'unused'
            returning id, state
            """,
            (claim_code_id,),
        )
        row = cur.fetchone()
        if row is not None:
            cur.execute(
                """
                insert into audit_events (actor_type, action, target_type, target_id)
                values ('api', 'claim_code.revoked', 'claim_code', %s)
                """,
                (str(claim_code_id),),
            )
    if row is None:
        raise HTTPException(status_code=404, detail="unused claim code not found")
    return row
