"""Small DB-API adapter; business SQL remains shared by SQLite and PostgreSQL.

Nested connections share one transaction. A transaction lock serializes this
single-user application's reads/mutations across workers, including empty rows.
"""
import os
import sqlite3
import threading
import atexit
from contextlib import contextmanager, closing

_local = threading.local()
_pool = None
_pool_url = None
_pool_lock = threading.Lock()

def close_pool():
    global _pool, _pool_url
    with _pool_lock:
        if _pool is not None:
            _pool.close()
        _pool = _pool_url = None

atexit.register(close_pool)

def postgres_pool(url):
    global _pool, _pool_url
    with _pool_lock:
        if _pool is None or _pool_url != url:
            if _pool is not None:
                _pool.close()
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
            _pool = ConnectionPool(url, min_size=0, max_size=4, open=True,
                                   timeout=15, max_idle=60, max_lifetime=300,
                                   kwargs={'row_factory':dict_row,'connect_timeout':10},
                                   check=ConnectionPool.check_connection)
            _pool_url = url
        return _pool

class Postgres:
    def __init__(self, raw): self.raw = raw
    def execute(self, sql, params=()):
        return self.raw.execute(sql.replace('?', '%s'), params)
    def executescript(self, sql):
        for statement in sql.split(';'):
            if statement.strip(): self.execute(statement)

@contextmanager
def connection(path):
    if getattr(_local, 'connection', None) is not None:
        yield _local.connection
        return
    url = os.environ.get('DATABASE_URL')
    manager = postgres_pool(url).connection() if url else closing(sqlite3.connect(path, timeout=30))
    with manager as raw:
        try:
            if url:
                c = Postgres(raw)
                raw.execute("SELECT pg_advisory_xact_lock(734902138), set_config('TimeZone','UTC',true)")
            else:
                raw.row_factory = sqlite3.Row
                raw.execute('BEGIN IMMEDIATE')
                c = raw
            _local.connection = c
            yield c
            raw.commit()
        except BaseException:
            raw.rollback()
            raise
        finally:
            _local.connection = None

def columns(c, table):
    if os.environ.get('DATABASE_URL'):
        return [r['column_name'] for r in c.execute(
            'SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=?', (table,))]
    return [r['name'] for r in c.execute('PRAGMA table_info('+table+')')]
