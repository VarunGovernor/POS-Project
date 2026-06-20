from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.database.connection import connect


@contextmanager
def transaction() -> Iterator[Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
