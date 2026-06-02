from collections.abc import Iterator
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings


pool = ConnectionPool(settings.database_url, min_size=1, max_size=10, open=False)


def open_pool() -> None:
    pool.open(wait=True)


def close_pool() -> None:
    pool.close()


@contextmanager
def db() -> Iterator:
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur
