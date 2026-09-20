# Tablero de indicadores — MSP Corrientes

Django 5 + PostgreSQL. Primera entrega: vista ejecutiva, ficha con gráfico y carga de mediciones.

## Arranque local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d
copy .env.example .env
# En .env: DATABASE_URL=postgres://tablero:tablero@127.0.0.1:5433/tablero
python manage.py migrate
python manage.py seed_tablero
python manage.py runserver
```

Usuarios de prueba (clave `tablero2026`):

- `admin@local` — ve UEP, Laboratorio, SUMAR+ y Dirección de Sistemas
- `uep@local` — solo Unidad Ejecutora Provincial
- `lab@local` — solo Laboratorio Central
- `sumar@local` — solo SUMAR+
- `sistemas@local` — solo Dirección de Sistemas

## Seed

Indicadores de UEP, Laboratorio Central (bloque A), SUMAR+ y los 9 de Dirección de Sistemas (`docs/Indicadores Gestion Direccion Sistemas.docx`). Los valores 2026 de SUMAR+ y Sistemas son de prueba (salvo la línea de base 68/95 de ancho de banda) y se editan desde Cargar medición.

## Piloto en la nube (gratis)

Camino recomendado: **Neon** (PostgreSQL, no vence a los 30 días) + **Render** (web, plan Free). No hace falta tarjeta si no se supera el cupo mensual.

1. Crear un repositorio en GitHub y subir este proyecto (`main`).
2. En [Neon](https://console.neon.tech): New Project → copiar la connection string con `sslmode=require`.
3. En [Render](https://dashboard.render.com): New → Blueprint, o Web Service desde el repo.
   - Build: `bash build.sh`
   - Start: `bash start.sh`
   - Plan: Free
   - Variables: `DEBUG=False`, `SECRET_KEY` (Generate), `DATABASE_URL` (la de Neon)
4. El primer arranque corre migraciones y el seed. Usuarios de prueba: los mismos de arriba.

**Limitaciones del plan free (para avisar al compartir el enlace):**

- Si nadie entra ~15 minutos, Render duerme el servicio. La próxima visita tarda alrededor de un minuto.
- Neon también puede dormir el cómputo: el primer query del día a veces suma unos segundos.
- No usar el Postgres free de Render: caduca a los 30 días.

## Piloto Streamlit (misma base)

La UI ejecutiva también corre en Streamlit contra **la misma Neon** (sin migrar tablas).

```powershell
pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
```

En [Streamlit Cloud](https://share.streamlit.io): New app → este repo → `streamlit_app.py`. En Secrets:

```
DATABASE_URL = "postgresql://...neon.tech/neondb?sslmode=require"
```

Usuarios y clave: los mismos del seed.
