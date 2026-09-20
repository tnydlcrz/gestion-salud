# Especificación técnica — Tablero de indicadores de gestión

Ministerio de Salud Pública de Corrientes. Documento de referencia del desarrollo.

## 1. Objetivo del sistema

Tablero web multi-área para:

- Definir indicadores de gestión por área/dirección
- Registrar mediciones periódicas en el tiempo
- Evaluar el cumplimiento contra metas (con soporte de metas variables por período)
- Graficar la evolución de cada indicador
- Controlar el acceso por área con permisos granulares (un usuario puede tener rol distinto en cada área)

**Escala esperada**: 20–40 áreas, 40–80 usuarios.

## 2. Stack técnico

| Capa | Elección | Motivo |
|---|---|---|
| Backend + frontend | Django 5 monolito, server-rendered + HTMX | Auth y admin de fábrica; un solo despliegue |
| Base de datos | PostgreSQL (local en desarrollo; Neon free en la nube) | Neon despierta sola; Supabase free pausa el proyecto a la semana |
| Hosting app (futuro) | Koyeb free (always-on) o Render free | Render free duerme a los 15 min (cold start 30–60 s); no usar como demo ejecutiva |
| Gráficos | Chart.js en templates Django | Liviano; suficiente para series de 12–36 puntos |
| Upgrade | Render Starter (~7 USD/mes) + Neon Launch (apaga scale-to-zero) | Sin cambiar código |

**Desarrollo**: se arranca en local. El deploy se documenta, no es parte del MVP.

Django resuelve login y hash de contraseñas, **no** el filtrado por área: eso va en mixins/querysets sobre `usuario_area`.

## 3. Modelo de datos

### 3.1 Catálogos

**`area_direccion`**: `id`, `nombre`

**`dimension`**: `id`, `nombre`

Valores del MVP: Gestión Específica del Área, Capacitaciones, Producción/Gestión Administrativa y/o Presupuestaria, Intervenciones Comunitarias y Cobertura Territorial, Resultados.

**`periodo`**: `id`, `anio`, `frecuencia`, `nro_periodo`, `fecha_inicio`, `fecha_fin`, `label`

Único por `(anio, frecuencia, nro_periodo)`. El label se genera (ej. "1er semestre 2026"). No se usa texto libre en mediciones.

**`usuario`** (extiende auth de Django): `id`, `nombre`, `email`, `es_admin_global`

**`responsable`**: `id`, `nombre`, `area_id`, `correo`, `telefono`

### 3.2 Permisos por área (con historial)

**`usuario_area`**

- `id` PK propia (un mismo usuario/área puede tener varias filas en el tiempo)
- `usuario_id`, `area_id`
- `rol` — `area` | `coordinador` (el admin **no** vive acá)
- `otorgado_por`, `fecha_alta`, `fecha_baja` (`NULL` = vigente)

Al revocar se cierra la fila. Un re-alta crea una fila **nueva**.

### 3.3 Indicadores versionados

**`indicador`**: `id`, `nombre`, `area_id`, `dimension_id`, `responsable_id`, `activo`, auditoría (`creado_por`, `fecha_creacion`, `actualizado_por`, `fecha_actualizacion`)

**`indicador_version`**

- `indicador_id`, `version_num`
- `fecha_vigencia_desde`, `fecha_vigencia_hasta` (`NULL` = vigente; una sola vigente por indicador)
- `formula_calculo`
- `tipo_calculo` — `valor_directo` | `razon`
- `numerador_descripcion`, `numerador_unidad`, `denominador_descripcion`, `denominador_unidad`
- `unidad_resultado`
- `meta_tipo` — `minimo` | `maximo` | `rango` | `sostener` | `seguimiento`
- `sentido_mejora` — `ascendente` | `descendente`
- `fuente_datos`, `frecuencia`, `objetivo_operativo`, `nota_metodologica`

Versión nueva solo si cambian fórmula, fuente o `meta_tipo`. El backend cierra la anterior en la misma transacción (`fecha_vigencia_hasta` = `fecha_vigencia_desde` de la nueva).

### 3.4 Metas por período

**`meta_periodo`**: `indicador_version_id`, `meta_min`, `meta_max`, `fecha_inicio_meta`, `fecha_fin_meta`

Varias metas en el tiempo sobre la misma versión, sin solaparse.

### 3.5 Mediciones

**`medicion`**

- `indicador_version_id`, `periodo_id`, `fecha_corte`
- `numerador_valor`, `denominador_valor`, `valor_calculado` (se persiste al guardar)
- `conclusion`, `estado` — `borrador` | `publicado`
- `usuario_carga_id`, `fecha_carga`

Única por `(indicador_version, periodo)`.

Cálculo: `valor_directo` copia el numerador; `razon` = numerador / denominador, × 100 si `unidad_resultado` es `%`.

## 4. Semáforo (MVP)

| `meta_tipo` | Verde | Rojo | Gris |
|---|---|---|---|
| `minimo` | valor ≥ `meta_min` | valor < `meta_min` | sin dato o sin meta |
| `maximo` | valor ≤ `meta_max` | valor > `meta_max` | sin dato o sin meta |
| `rango` | `meta_min` ≤ valor ≤ `meta_max` | fuera de banda | sin dato o sin meta |
| `sostener` | `meta_min` ≤ valor (y ≤ `meta_max` si existe) | fuera | sin dato o sin meta |
| `seguimiento` | — | — | siempre (solo tendencia) |

El tablero ejecutivo solo considera mediciones **publicadas**. Umbral amarillo: fuera del MVP.

## 5. Roles

| Rol | Dónde vive | Alcance |
|---|---|---|
| `es_admin_global` (o `is_superuser`) | `usuario` | Todas las áreas |
| `coordinador` | fila vigente de `usuario_area` | Solo esas áreas |
| `area` | fila vigente de `usuario_area` | Solo esas áreas |

La misma persona puede ser `coordinador` en un área y `area` en otra. Coordinador y área pueden cargar mediciones de sus áreas.

## 6. Alcance del MVP

Modelo completo + login + home ejecutivo + ficha con gráfico + formulario de carga.

Seed: 5 indicadores de UEP (`docs/Indicadores UEP.pdf`) y los 6 del bloque A de Laboratorio Central (`docs/Informe Lab Central.pdf`).

Definición de fórmulas: Django Admin + seed. Sin ABM público de indicadores.

## 7. Vistas

| Ruta | Acceso | Contenido |
|---|---|---|
| `/login/` `/logout/` | público / autenticado | Auth Django |
| `/` | autenticado | Cards por área visible, % en meta, conteos semáforo |
| `/area/<id>/` | permiso sobre el área | Dimensiones + indicadores |
| `/indicador/<id>/` | permiso | KPI, meta, Chart.js, última conclusión |
| `/indicador/<id>/cargar/` | área, coordinador o admin | Alta/edición de medición |

## 8. Fuera del MVP

ABM público de indicadores, umbral amarillo, export Excel/PDF, deploy a Koyeb/Render, resto de áreas de los PDF.
