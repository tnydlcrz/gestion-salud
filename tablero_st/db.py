import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import psycopg
from psycopg.rows import dict_row


def _from_dotenv():
    ruta = Path(__file__).resolve().parent.parent / ".env"
    if not ruta.exists():
        return ""
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.startswith("DATABASE_URL="):
            return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def database_url():
    try:
        import streamlit as st

        url = st.secrets.get("DATABASE_URL", "")
        if url:
            return url
    except Exception:
        pass
    return os.environ.get("DATABASE_URL") or _from_dotenv()


def _limpiar_url(url):
    partes = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(partes.query) if k != "channel_binding"]
    if not any(k == "sslmode" for k, _ in query) and "neon.tech" in (partes.hostname or ""):
        query.append(("sslmode", "require"))
    return urlunparse(partes._replace(query=urlencode(query)))


def _dsn():
    url = database_url()
    if not url:
        raise RuntimeError("Falta DATABASE_URL (secrets de Streamlit o .env).")
    return _limpiar_url(url)


def _make_pool():
    from psycopg_pool import ConnectionPool

    return ConnectionPool(
        conninfo=_dsn(),
        min_size=1,
        max_size=5,
        timeout=15,
        kwargs={"row_factory": dict_row, "connect_timeout": 8},
    )


try:
    import streamlit as st

    _cached_pool = st.cache_resource(show_spinner=False)(_make_pool)
except Exception:
    _cached_pool = None


def _pool():
    if _cached_pool is None:
        return None
    try:
        return _cached_pool()
    except Exception:
        return None


def _run(sql, params, write=False):
    pool = _pool()
    if pool is not None:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                filas = list(cur.fetchall()) if cur.description else []
            if write:
                conn.commit()
            return filas
    with psycopg.connect(_dsn(), row_factory=dict_row, connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            filas = list(cur.fetchall()) if cur.description else []
        if write:
            conn.commit()
        return filas


def fetch_all(sql, params=None):
    return _run(sql, params, write=False)


def fetch_one(sql, params=None):
    filas = fetch_all(sql, params)
    return filas[0] if filas else None


def execute(sql, params=None):
    _run(sql, params, write=True)
