"""Postgres access for the write path.

Plain per-command connections over DATABASE_ADMIN_URL — the workers are batch jobs, not a
long-lived service, so a connection pool would be overkill. Workers run as the trusted
(table-owner) role, so RLS does not filter their writes; the worker is responsible for
stamping the correct tenant_id on every tenant-scoped row. We still set the
`app.tenant_id` GUC inside tenant-scoped transactions so the same code path stays correct
if it is ever run under the RLS-enforced role.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from tickertea.common.settings import get_settings


def connect() -> psycopg.Connection:
    """Open a new trusted connection. Caller is responsible for closing it."""
    s = get_settings()
    return psycopg.connect(s.database_admin_url, row_factory=dict_row)


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """A connection that commits on success and rolls back on error, then closes."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def tenant_tx(tenant_id: UUID | str) -> Iterator[psycopg.Connection]:
    """A transaction with the tenant GUC set, for writing tenant-scoped rows."""
    conn = connect()
    try:
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
