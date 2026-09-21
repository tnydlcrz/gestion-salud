"""Copia las tablas del tablero desde Neon hacia el proyecto Supabase nuevo."""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
TABLAS = [
    "cuentas_usuario",
    "indicadores_areadireccion",
    "indicadores_dimension",
    "indicadores_responsable",
    "indicadores_periodo",
    "indicadores_indicador",
    "indicadores_indicadorversion",
    "indicadores_metaperiodo",
    "indicadores_medicion",
    "cuentas_usuarioarea",
]


def _json(valor):
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return valor


def _limpiar(fila: dict) -> dict:
    return {clave: _json(valor) for clave, valor in fila.items()}


def _neon():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        env = ROOT / ".env"
        if env.exists():
            for linea in env.read_text(encoding="utf-8").splitlines():
                if linea.startswith("DATABASE_URL="):
                    url = linea.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        raise SystemExit("Falta DATABASE_URL de Neon (.env o variable de entorno).")
    if "channel_binding" in url:
        url = url.replace("channel_binding=require", "").replace("&&", "&").rstrip("&")
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=15)


def _supabase():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if (not url or not key) and secrets.exists():
        for linea in secrets.read_text(encoding="utf-8").splitlines():
            if linea.startswith("SUPABASE_URL"):
                url = linea.split("=", 1)[1].strip().strip('"')
            if linea.startswith("SUPABASE_SERVICE_ROLE_KEY"):
                key = linea.split("=", 1)[1].strip().strip('"')
    if not url or not key:
        raise SystemExit("Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY.")
    return create_client(url, key)


def main():
    origen = _neon()
    destino = _supabase()
    with origen:
        for tabla in TABLAS:
            with origen.cursor() as cur:
                try:
                    cur.execute(f"SELECT * FROM {tabla}")
                except Exception as exc:
                    print(f"omitida {tabla}: {exc}")
                    continue
                filas = [_limpiar(dict(fila)) for fila in cur.fetchall()]
            if not filas:
                print(f"{tabla}: 0 filas")
                continue
            for i in range(0, len(filas), 80):
                lote = filas[i : i + 80]
                destino.table(tabla).upsert(lote).execute()
            print(f"{tabla}: {len(filas)} filas")
    print("Listo. En SQL Editor de Supabase corré db/after_migrate.sql")


if __name__ == "__main__":
    main()
