from collections.abc import Iterator
from contextlib import contextmanager
import hashlib

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings


pool = ConnectionPool(settings.database_url, min_size=1, max_size=10, open=False)


def open_pool() -> None:
    pool.open(wait=True)


def close_pool() -> None:
    pool.close()


def hash_mqtt_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_mqtt_service_credentials() -> None:
    credentials = [
        (settings.mqtt_backend_username, settings.mqtt_backend_password, "backend"),
        (settings.mqtt_provisioning_username, settings.mqtt_provisioning_password, "provisioning"),
    ]
    with pool.connection() as conn:
        with conn.cursor() as cur:
            for username, password, role in credentials:
                cur.execute(
                    """
                    insert into mqtt_service_credentials (username, password_hash, role, enabled)
                    values (%s, %s, %s, true)
                    on conflict (username) do update set
                      password_hash = excluded.password_hash,
                      role = excluded.role,
                      enabled = true,
                      updated_at = now()
                    """,
                    (username, hash_mqtt_password(password), role),
                )


@contextmanager
def db() -> Iterator:
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur
