"""Cliente HTTP a PostgREST, mismo patrón que el tablero de compromisos."""

from functools import lru_cache

import streamlit as st
from supabase import Client, create_client


def normalize_supabase_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    return url.rstrip("/")


def get_supabase_config() -> tuple[str, str]:
    url = ""
    key = ""
    try:
        url = normalize_supabase_url(st.secrets.get("SUPABASE_URL", ""))
        key = (
            st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
            or st.secrets.get("SUPABASE_ANON_KEY")
            or ""
        )
    except Exception:
        pass
    if not url or not key:
        raise RuntimeError(
            "Configurá SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en .streamlit/secrets.toml"
        )
    return url, key


@lru_cache(maxsize=4)
def _cached_client(url: str, key: str) -> Client:
    return create_client(url, key)


def get_client() -> Client:
    url, key = get_supabase_config()
    return _cached_client(url, key)


def clear_client_cache() -> None:
    _cached_client.cache_clear()
