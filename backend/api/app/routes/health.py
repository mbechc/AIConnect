from fastapi import APIRouter

from app.db import db

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict:
    with db() as cur:
        cur.execute("select 1 as ok")
        row = cur.fetchone()
    return {"status": "ready", "db": row["ok"] == 1}
