"""
database/base.py
------------------
SQLAlchemy engine + session factory.

Multi-user / shared-network-folder notes
=========================================
SQLite supports multiple readers/writers against the same file as long
as every process points at the identical path. When that file lives on
a Windows shared folder (SMB/CIFS), the safest configuration is:
  * journal_mode = DELETE (classic rollback journal) rather than WAL,
    since WAL depends on shared-memory (-shm) files that are unreliable
    over most network filesystems.
  * A generous busy_timeout so a user who is mid-write doesn't cause a
    "database is locked" error for a colleague opening the app at the
    same moment - SQLite waits and retries internally instead.
  * foreign_keys = ON so cascades declared in the ORM are enforced.
These PRAGMAs are applied on every new DBAPI connection via the
`connect` event below, so they're always in effect regardless of how a
session was obtained.
"""
from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

import config


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def _apply_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA journal_mode = DELETE;")
    cursor.execute("PRAGMA busy_timeout = 30000;")
    cursor.execute("PRAGMA synchronous = FULL;")
    cursor.close()


def init_engine(db_path: str | None = None):
    """(Re)initialises the module-level engine/session factory and
    creates all tables if they don't exist yet. Safe to call again after
    the user changes the database location in Settings."""
    global _engine, _SessionLocal

    path = db_path or config.get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    if _engine is not None:
        _engine.dispose()

    _engine = create_engine(f"sqlite:///{path}", future=True)
    event.listen(_engine, "connect", _apply_pragmas)

    # Import models so they register on Base.metadata before create_all.
    from models import transfer, preparation, release, support  # noqa: F401
    Base.metadata.create_all(_engine)

    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_engine():
    if _engine is None:
        init_engine()
    return _engine


@contextmanager
def session_scope() -> Session:
    """Provide a transactional scope: commits on success, rolls back and
    re-raises on error, always closes."""
    if _SessionLocal is None:
        init_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def new_session() -> Session:
    """A session the caller is responsible for committing/closing -
    used where the UI needs to keep a session open across a dialog's
    lifetime (e.g. editing a Transfer's nested Tools)."""
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal()
