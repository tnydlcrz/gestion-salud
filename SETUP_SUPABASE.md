# Supabase — Tablero de indicadores (proyecto aparte)

Sí: en la misma cuenta de Supabase creá un **proyecto nuevo**. Cada proyecto es otra base Postgres. No mezclar con el de compromisos/agenda.

## 1. Crear el proyecto

1. [https://supabase.com/dashboard](https://supabase.com/dashboard) → **New project**
2. Name: `gestion-salud`
3. Region: **East US (North Virginia)** — Streamlit Cloud está en EE.UU.; ahí se siente parecido al tablero de compromisos. Si hace falta residencia en la región, usá São Paulo (un poco más de latencia).
4. Guardá la contraseña de la base.

## 2. Schema

SQL Editor → New query → pegar todo [`db/schema.sql`](db/schema.sql) → **Run**.

## 3. Copiar datos desde Neon

En PowerShell, desde la carpeta del proyecto:

```powershell
pip install supabase psycopg[binary]
$env:DATABASE_URL = "postgresql://...neon.tech/neondb?sslmode=require"
$env:SUPABASE_URL = "https://xxxxx.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "eyJ..."   # Settings → API → service_role (secreta)
python scripts/migrar_neon_a_supabase.py
```

Después, SQL Editor → pegar [`db/after_migrate.sql`](db/after_migrate.sql) → **Run**.

## 4. Secrets de Streamlit

Settings → API:

- Project URL → `SUPABASE_URL`
- `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (solo en secrets, nunca en GitHub)

`.streamlit/secrets.toml` (local) y **Secrets** en Streamlit Cloud:

```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJ..."
```

Quitá `DATABASE_URL` de Neon en Streamlit Cloud.

## 5. Redeploy

Streamlit Cloud → Reboot. Login: los mismos usuarios (`admin@local` / `tablero2026`, etc.).
