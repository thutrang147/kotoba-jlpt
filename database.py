"""Small DB-API adapter; business SQL remains shared by SQLite and PostgreSQL.

Nested connections share one transaction. A transaction lock serializes this
single-user application's reads/mutations across workers, including empty rows.
"""
import os
import sqlite3
import threading
from contextlib import contextmanager

_local = threading.local()

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
    if url:
        import psycopg
        from psycopg.rows import dict_row
        raw = psycopg.connect(url, row_factory=dict_row, connect_timeout=15)
        c = Postgres(raw)
        raw.execute('SET TIME ZONE \'UTC\'')
        raw.execute('SELECT pg_advisory_xact_lock(734902138)')
    else:
        raw = sqlite3.connect(path, timeout=30)
        raw.row_factory = sqlite3.Row
        raw.execute('BEGIN IMMEDIATE')
        c = raw
    _local.connection = c
    try:
        yield c
        raw.commit()
    except BaseException:
        raw.rollback()
        raise
    finally:
        _local.connection = None
        raw.close()

def columns(c, table):
    if os.environ.get('DATABASE_URL'):
        return [r['column_name'] for r in c.execute(
            'SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=?', (table,))]
    return [r['name'] for r in c.execute('PRAGMA table_info('+table+')')]
