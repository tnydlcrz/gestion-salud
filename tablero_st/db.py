"""Compatibilidad: la app ya no usa SQL directo contra Neon."""

from .supabase_client import get_client


def table(nombre):
    return get_client().table(nombre)
