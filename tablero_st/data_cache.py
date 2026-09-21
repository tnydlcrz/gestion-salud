"""Cache de lecturas Neon para evitar el parpadeo en cada rerun de Streamlit."""

from __future__ import annotations

import streamlit as st

LECTURA_TTL = 45


def invalidate_data_cache() -> None:
    areas_visibles_cached.clear()
    indicadores_de_area_cached.clear()
    indicador_detalle_cached.clear()
    resumenes_areas_cached.clear()
    periodos_de_cached.clear()


@st.cache_data(ttl=LECTURA_TTL, show_spinner=False)
def areas_visibles_cached(user_id: int, es_admin: bool):
    from .queries import _areas_visibles_impl

    return _areas_visibles_impl(user_id, es_admin)


@st.cache_data(ttl=LECTURA_TTL, show_spinner=False)
def indicadores_de_area_cached(area_id: int):
    from .queries import _indicadores_de_area_impl

    return _indicadores_de_area_impl(area_id)


@st.cache_data(ttl=LECTURA_TTL, show_spinner=False)
def indicador_detalle_cached(indicador_id: int):
    from .queries import _indicador_detalle_impl

    return _indicador_detalle_impl(indicador_id)


@st.cache_data(ttl=LECTURA_TTL, show_spinner=False)
def resumenes_areas_cached(user_id: int, es_admin: bool):
    from .queries import _resumenes_areas_impl

    return _resumenes_areas_impl(user_id, es_admin)


@st.cache_data(ttl=300, show_spinner=False)
def periodos_de_cached(frecuencia: str):
    from .queries import _periodos_de_impl

    return _periodos_de_impl(frecuencia)
