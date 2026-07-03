import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

_engine = None
_ScopedSession = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            os.environ["DATABASE_URL"],
            pool_pre_ping=True,   # descarta conexiones muertas antes de usarlas
            pool_size=10,         # conexiones persistentes en el pool
            max_overflow=20,      # conexiones extra bajo picos de carga
            pool_timeout=30,      # segundos de espera por una conexión libre
            pool_recycle=1800,    # recicla conexiones >30 min (evita cierres del servidor)
        )
    return _engine


def get_session_factory():
    global _ScopedSession
    if _ScopedSession is None:
        _ScopedSession = scoped_session(
            sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
        )
    return _ScopedSession


def get_db() -> Session:
    """Sesión con alcance por hilo/request.

    Todas las llamadas dentro del mismo request comparten la misma sesión.
    La conexión se devuelve al pool en `close_db`, registrado como
    `teardown_appcontext` en app.py — nunca depende del garbage collector.
    """
    return get_session_factory()()


def close_db(exception: BaseException | None = None) -> None:
    """Libera la sesión del request actual y devuelve la conexión al pool."""
    if _ScopedSession is not None:
        _ScopedSession.remove()
