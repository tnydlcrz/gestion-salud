"""Tablero ejecutivo MSP Corrientes. Usa la base Django/Neon tal cual.

Local:  streamlit run streamlit_app.py
Nube:   Streamlit Cloud → este archivo + secret DATABASE_URL
"""

import html

import plotly.graph_objects as go
import streamlit as st

from tablero_st.auth import autenticar
from tablero_st.queries import (
    areas_visibles,
    guardar_medicion,
    indicador_detalle,
    indicadores_de_area,
    periodos_de,
    puede_ver_area,
    resumenes_areas,
)

st.set_page_config(page_title="Tablero de indicadores · MSP Corrientes", layout="wide", page_icon="◆")

CSS = """
<style>
html, body, [class*="css"] { font-family: "Segoe UI", Calibri, sans-serif; }
.stApp { background: #f4f1ea; }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stSidebar"] { background: #0c1c2e; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: 1.1rem 0.85rem 1.2rem 1rem; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.2rem !important; }
[data-testid="stSidebar"] .gold { color: #d4b45a !important; }
[data-testid="stSidebar"] .side-brand-title,
[data-testid="stSidebar"] .side-brand-title * { color: #ffffff !important; }
[data-testid="stSidebar"] .side-brand-place { color: #94a3b8 !important; }
[data-testid="stSidebar"] .side-user { color: #64748b !important; }
[data-testid="stSidebar"] .stMarkdown p { margin-bottom: 0 !important; }
[data-testid="stSidebar"] .stButton { width: 100%; margin-bottom: 0 !important; }
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] button,
[data-testid="stSidebar"] [data-testid="stBaseButton-tertiary"] {
    background: transparent !important;
    border: 0 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    text-align: left !important;
    justify-content: flex-start !important;
    align-items: center !important;
    display: flex !important;
    width: 100% !important;
    border-radius: 6px;
    padding: 0.48rem 0.45rem 0.48rem 0.15rem !important;
    min-height: 2.35rem !important;
    font-size: 1.16rem !important;
    font-weight: 500 !important;
    line-height: 1.3 !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] .stButton > button > div,
[data-testid="stSidebar"] button p,
[data-testid="stSidebar"] button span,
[data-testid="stSidebar"] button * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    align-items: center !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] button:hover { background: #143049 !important; color: #fff !important; }
[data-testid="stSidebar"] .st-key-cerrar-sesion button,
[data-testid="stSidebar"] .st-key-cerrar-sesion button * {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    font-size: 0.75rem !important;
    font-weight: 400 !important;
    min-height: 0 !important;
    padding: 0.15rem 0.15rem !important;
}
[data-testid="stSidebar"] .st-key-cerrar-sesion button:hover,
[data-testid="stSidebar"] .st-key-cerrar-sesion button:hover * {
    color: #94a3b8 !important;
    background: transparent !important;
}
.side-brand {
    padding: 0.15rem 0.15rem 1rem 0.15rem;
    margin-bottom: 1.15rem;
    border-bottom: 1px solid rgba(212, 180, 90, 0.28);
}
.side-brand-title {
    font-size: 1.42rem !important;
    line-height: 1.18 !important;
    margin: 0.4rem 0 0 !important;
    font-weight: 500 !important;
}
.side-brand-place {
    font-size: 0.72rem !important;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin: 0.45rem 0 0 !important;
}
.side-foot {
    margin-top: 2.25rem;
    padding-top: 0.85rem;
    border-top: 1px solid rgba(226, 232, 240, 0.1);
}
.side-user {
    font-size: 0.72rem !important;
    line-height: 1.35 !important;
    margin: 0 0 0.15rem 0.15rem !important;
}
.eyebrow { font-size: 11px; letter-spacing: .2em; text-transform: uppercase; color: #1d4463; opacity: .7; }
h1, h2, h3, .serif { font-family: Georgia, "Times New Roman", serif !important; color: #0c1c2e; }
.gold { color: #d4b45a; letter-spacing: .22em; font-size: 11px; text-transform: uppercase; }
.card {
    background: #fff; border: 1px solid #e7e5e4; border-radius: 16px;
    padding: 1.15rem 1.25rem; margin-bottom: .85rem;
}
.muted { color: #64748b; font-size: .9rem; }
.dot { display: inline-block; width: .65rem; height: .65rem; border-radius: 99px; margin-right: .35rem; }
.dot-verde { background: #0f766e; } .dot-rojo { background: #b91c1c; } .dot-gris { background: #94a3b8; }
.leyenda {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem 1.4rem;
  color: #64748b;
  font-size: 0.9rem;
  margin: 0.2rem 0 0.55rem;
}
.leyenda-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}
.leyenda-sep {
  width: 1px;
  height: 0.95rem;
  background: #d6deea;
}
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdown"],
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPlotlyChart"],
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="element-container"],
div[data-testid="stVerticalBlockBorderWrapper"] button,
div[data-testid="stVerticalBlockBorderWrapper"] .js-plotly-plot,
div[data-testid="stVerticalBlockBorderWrapper"] .plot-container {
  background: #ffffff !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid #e7e5e4 !important;
  border-radius: 16px !important;
  box-shadow: 0 1px 2px rgba(12, 28, 46, 0.04);
}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
  gap: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stButton"] {
  width: auto !important;
  margin: 0.15rem 0 0.35rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stButton"] button {
  background: #ffffff !important;
  color: #1d4463 !important;
  border: 1px solid #e7e5e4 !important;
  border-radius: 8px !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  padding: 0.22rem 0.75rem !important;
  min-height: 0 !important;
  width: auto !important;
  box-shadow: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stButton"] button:hover {
  background: #f8fafc !important;
  border-color: #d4b45a !important;
  color: #0c1c2e !important;
}
.login-panel { background: #0c1c2e; color: #f8fafc; border-radius: 0; min-height: 80vh; padding: 3.5rem; }
div[data-testid="stTextInput"] input,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input {
  background: #ffffff !important;
  color: #0c1c2e !important;
  caret-color: #0c1c2e !important;
  -webkit-text-fill-color: #0c1c2e !important;
  border: 1px solid #d6deea !important;
}
div[data-testid="stTextInput"] input::placeholder {
  color: #94a3b8 !important;
  -webkit-text-fill-color: #94a3b8 !important;
}
</style>
"""

CSS_LOGIN = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
</style>
"""


def ir(vista, **extra):
    st.session_state.vista = vista
    for clave, valor in extra.items():
        st.session_state[clave] = valor
    st.rerun()


def figura(serie, alto=220):
    compacto = alto < 220
    fig = go.Figure()
    if serie:
        fig.add_trace(
            go.Scatter(
                x=[p["label"] for p in serie],
                y=[p["valor"] for p in serie],
                mode="lines+markers",
                line=dict(color="#143049", width=2),
                marker=dict(color=[p["color"] for p in serie], size=7),
                fill="tozeroy",
                fillcolor="rgba(20,48,73,0.08)",
                hovertemplate="%{x}<br>%{y}<extra></extra>",
                cliponaxis=False,
            )
        )
    fig.update_layout(
        height=alto,
        margin=dict(l=48, r=18, t=12, b=52) if compacto else dict(l=56, r=20, t=20, b=56),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        showlegend=False,
        font=dict(color="#475569"),
        xaxis=dict(
            automargin=True,
            showgrid=True,
            gridcolor="#e2e8f0",
            zeroline=False,
            tickangle=-25 if compacto else 0,
            tickfont=dict(size=11, color="#475569"),
            ticks="outside",
            ticklen=4,
        ),
        yaxis=dict(
            automargin=True,
            showgrid=True,
            gridcolor="#e2e8f0",
            zeroline=False,
            tickfont=dict(size=11, color="#475569"),
            ticks="outside",
            ticklen=4,
            separatethousands=True,
        ),
        hovermode="x unified",
    )
    return fig


def mostrar_figura(serie, alto, key=None, seleccionable=False):
    extras = {}
    if seleccionable:
        extras["on_select"] = "rerun"
        extras["selection_mode"] = "points"
    return st.plotly_chart(
        figura(serie, alto),
        use_container_width=True,
        config={"displayModeBar": False},
        key=key,
        theme=None,
        **extras,
    )


def pagina_login():
    st.markdown(CSS_LOGIN, unsafe_allow_html=True)
    izq, der = st.columns([1.05, 1], gap="large")
    with izq:
        st.markdown(
            """
            <div class="login-panel">
              <p class="gold">Ministerio de Salud Pública · Corrientes</p>
              <h1 style="font-family:Georgia,serif;font-size:2.6rem;line-height:1.15;color:#fff;margin-top:1.5rem">
                Tablero de<br>indicadores de gestión
              </h1>
              <p style="color:#cbd5e1;max-width:26rem;margin-top:1.2rem;line-height:1.55">
                Seguimiento de metas por área, con semáforo de cumplimiento y evolución en el tiempo.
              </p>
              <p style="color:#64748b;font-size:.8rem;margin-top:4rem">Acceso restringido a usuarios habilitados.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with der:
        st.markdown("<div style='height:4rem'></div>", unsafe_allow_html=True)
        st.markdown('<p class="serif" style="font-size:1.8rem;margin-bottom:0">Ingresar</p>', unsafe_allow_html=True)
        st.caption("Use el correo institucional.")
        with st.form("login"):
            email = st.text_input("Correo")
            password = st.text_input("Contraseña", type="password")
            enviar = st.form_submit_button("Entrar", use_container_width=True)
        if enviar:
            user = autenticar(email, password)
            if user:
                st.session_state.user = user
                st.session_state.vista = "home"
                st.rerun()
            st.error("Correo o contraseña incorrectos.")


def sidebar(user):
    with st.sidebar:
        st.markdown(
            """
            <div class="side-brand">
              <p class="gold" style="margin:0">Ministerio de Salud Pública</p>
              <p class="serif side-brand-title">Tablero de<br>indicadores</p>
              <p class="side-brand-place">Provincia de Corrientes</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Vista ejecutiva", use_container_width=True, type="tertiary"):
            ir("home")
        for area in areas_visibles(user):
            if st.button(area["nombre"], key=f"nav-{area['id']}", use_container_width=True, type="tertiary"):
                ir("area", area_id=area["id"])
        st.markdown(
            f'<div class="side-foot"><p class="side-user">{html.escape(user["nombre"])}</p></div>',
            unsafe_allow_html=True,
        )
        if st.button("Cerrar sesión", type="tertiary", key="cerrar-sesion"):
            st.session_state.clear()
            st.rerun()


def vista_home(user):
    st.markdown('<p class="eyebrow">Resumen</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="serif">Vista ejecutiva</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="muted">Cumplimiento de la última medición publicada de cada indicador, por área visible.</p>',
        unsafe_allow_html=True,
    )
    resumenes = resumenes_areas(user)
    cols = st.columns(2)
    for i, r in enumerate(resumenes):
        with cols[i % 2]:
            pct = f"{r['pct_meta']}%" if r["pct_meta"] is not None else "—"
            st.markdown(
                f"""
                <div class="card">
                  <div style="display:flex;justify-content:space-between;gap:1rem">
                    <div>
                      <p class="serif" style="font-size:1.45rem;margin:0">{r['area']['nombre']}</p>
                      <p class="muted" style="margin:.35rem 0 0">{r['total']} indicadores</p>
                    </div>
                    <div style="text-align:right">
                      <p class="serif" style="font-size:2rem;margin:0">{pct}</p>
                      <p class="eyebrow">en meta</p>
                    </div>
                  </div>
                  <p style="margin:1rem 0 0;font-size:.9rem">
                    <span class="dot dot-verde"></span>{r['verdes']} en meta
                    &nbsp;&nbsp;<span class="dot dot-rojo"></span>{r['rojos']} fuera
                    &nbsp;&nbsp;<span class="dot dot-gris"></span>{r['grises']} sin dato
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Abrir área", key=f"home-{r['area']['id']}"):
                ir("area", area_id=r["area"]["id"])
    if not resumenes:
        st.info("No hay áreas asignadas a esta cuenta.")


def mosaico_tarjeta(item):
    valor = "Sin medición publicada"
    if item["ultima"] and item["ultima"]["valor_calculado"] is not None:
        valor = f"{float(item['ultima']['valor_calculado']):.1f} {item.get('unidad_resultado') or ''}"
    periodo = item["ultima"]["label"] if item["ultima"] else ""
    extra = item.get("area_direccion") or ""
    nombre = html.escape(item["nombre"])
    extra_txt = html.escape(extra)
    periodo_txt = html.escape(periodo)
    meta_txt = html.escape(item["meta_texto"] or "—")
    nd_txt = html.escape(item["nd_texto"])
    with st.container(border=True):
        st.markdown(
            f"""
            <div style="background:#ffffff;margin:0;padding:.15rem .1rem .4rem">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:.75rem">
                <p class="serif" style="font-size:1.18rem;font-weight:600;line-height:1.35;margin:0;color:#0c1c2e">{nombre}</p>
                <span class="dot dot-{item["semaforo"]}" style="flex-shrink:0;margin-top:.4rem"></span>
              </div>
              <p class="eyebrow" style="margin:.7rem 0 0">{extra_txt}</p>
              <p class="serif" style="font-size:1.25rem;margin:.35rem 0 0">{html.escape(valor)}</p>
              <p class="muted" style="margin:.1rem 0 0">{periodo_txt}</p>
              <p class="muted" style="margin:.1rem 0 0">Meta {meta_txt} · {nd_txt}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        evento = mostrar_figura(item["serie"], 190, key=f"ch-{item['id']}", seleccionable=True)
        puntos = ()
        seleccion = getattr(evento, "selection", None)
        if seleccion is not None:
            puntos = tuple(getattr(seleccion, "points", None) or ())
        visto = f"ch-sel-{item['id']}"
        anterior = st.session_state.get(visto)
        st.session_state[visto] = puntos
        if puntos and puntos != anterior:
            ir("ficha", indicador_id=item["id"])
        if st.button("Ver más", key=f"ind-{item['id']}", type="tertiary"):
            ir("ficha", indicador_id=item["id"])


def vista_area(user):
    area_id = st.session_state.get("area_id")
    if not area_id or not puede_ver_area(user, area_id):
        ir("home")
    area = next(a for a in areas_visibles(user) if a["id"] == area_id)
    filas = indicadores_de_area(area_id)
    verdes = sum(1 for f in filas if f["semaforo"] == "verde")
    rojos = sum(1 for f in filas if f["semaforo"] == "rojo")
    grises = sum(1 for f in filas if f["semaforo"] == "gris")
    evaluados = verdes + rojos
    pct = f"{round(100 * verdes / evaluados)}% de indicadores en meta" if evaluados else "Sin indicadores evaluados"
    st.markdown(f'<h1 class="serif">{area["nombre"]}</h1>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="leyenda">
          <span class="leyenda-item">{pct}</span>
          <span class="leyenda-sep"></span>
          <span class="leyenda-item"><span class="dot dot-verde"></span>{verdes} en meta</span>
          <span class="leyenda-item"><span class="dot dot-rojo"></span>{rojos} fuera</span>
          <span class="leyenda-item"><span class="dot dot-gris"></span>{grises} sin dato</span>
          <span class="leyenda-sep"></span>
          <span class="leyenda-item">VP: valor de prueba</span>
          <span class="leyenda-item">s/d: sin dato</span>
          <span class="leyenda-item">n/a: no aplica</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    por_dim = {}
    for fila in filas:
        por_dim.setdefault(fila["dimension_nombre"], []).append(fila)
    for dimension, items in por_dim.items():
        st.markdown(f'<p class="eyebrow" style="margin-top:1.6rem">{dimension}</p>', unsafe_allow_html=True)
        pares = [items[i : i + 2] for i in range(0, len(items), 2)]
        for par in pares:
            cols = st.columns(2)
            for col, item in zip(cols, par):
                with col:
                    mosaico_tarjeta(item)


def vista_ficha(user):
    indicador_id = st.session_state.get("indicador_id")
    item = indicador_detalle(indicador_id) if indicador_id else None
    if not item or not puede_ver_area(user, item["area_id"]):
        ir("home")
    if st.button("← " + item["area_nombre"]):
        ir("area", area_id=item["area_id"])
    st.markdown(
        f'<p class="eyebrow">{item["area_nombre"]} · {item["dimension_nombre"]}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<h1 class="serif">{item["nombre"]}</h1>', unsafe_allow_html=True)
    ultima = item["ultima"]
    valor = "—"
    if ultima and ultima["valor_calculado"] is not None:
        valor = f"{float(ultima['valor_calculado']):.1f}"
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="card"><p class="eyebrow">Último valor</p>'
            f'<p class="serif" style="font-size:2.2rem;margin:.4rem 0 0">{valor}'
            f'<span class="muted" style="font-size:1rem"> {item.get("unidad_resultado") or ""}</span></p>'
            f'<p class="muted">{ultima["label"] if ultima else "Sin publicación"}</p></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="card"><p class="eyebrow">Meta</p>'
            f'<p class="serif" style="font-size:1.6rem;margin:.4rem 0 0">{item["meta_texto"] or "Seguimiento"}</p>'
            f'<p class="muted">{item.get("frecuencia") or ""} · {item.get("meta_tipo") or ""}</p></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="card"><p class="eyebrow">Semáforo</p>'
            f'<p style="margin:.8rem 0 0"><span class="dot dot-{item["semaforo"]}"></span>'
            f'<b>{item["semaforo"]}</b></p>'
            f'<p class="muted">{item.get("sentido_mejora") or ""}</p></div>',
            unsafe_allow_html=True,
        )
    if item.get("area_direccion"):
        st.caption(f"Área/Dirección · {item['area_direccion']}")
    with st.container(border=True):
        st.markdown(
            '<p class="eyebrow" style="margin:.15rem 0 .1rem">Evolución</p>',
            unsafe_allow_html=True,
        )
        mostrar_figura(item["serie"], 320, key=f"ch-ficha-{item['id']}")
        st.markdown(
            f"""
            <div class="leyenda" style="margin:.15rem 0 .4rem">
              <span class="leyenda-item">{html.escape(item["nd_texto"])}</span>
              <span class="leyenda-sep"></span>
              <span class="leyenda-item">VP: valor de prueba</span>
              <span class="leyenda-item">s/d: sin dato</span>
              <span class="leyenda-item">n/a: no aplica</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    if item["mediciones"]:
        st.markdown('<p class="eyebrow">Mediciones</p>', unsafe_allow_html=True)
        filas_tabla = [
            {
                "Período": m["label"],
                "Valor": f"{float(m['valor_calculado']):.1f}" if m["valor_calculado"] is not None else "s/d",
                "Numerador / Denominador": texto_nd_fila(item, m),
            }
            for m in item["mediciones"]
        ]
        st.dataframe(filas_tabla, use_container_width=True, hide_index=True)
    if ultima and ultima.get("conclusion"):
        st.markdown('<p class="eyebrow">Conclusión</p>', unsafe_allow_html=True)
        st.write(ultima["conclusion"])
    if item.get("formula_calculo"):
        st.caption(f"Fórmula. {item['formula_calculo']}")
    if item.get("fuente_datos"):
        st.caption(f"Fuente. {item['fuente_datos']}")
    st.markdown("---")
    st.markdown('<p class="serif" style="font-size:1.4rem">Cargar medición</p>', unsafe_allow_html=True)
    periodos = periodos_de(item["frecuencia"]) if item.get("frecuencia") else []
    if not periodos:
        st.info("No hay períodos cargados para esta frecuencia.")
        return
    etiquetas = {p["label"]: p["id"] for p in periodos}
    with st.form("cargar"):
        label = st.selectbox("Período", list(etiquetas))
        numerador = st.number_input("Numerador / valor", value=None, format="%f")
        denominador = None
        if item.get("tipo_calculo") == "razon":
            denominador = st.number_input("Denominador", value=None, format="%f")
        conclusion = st.text_area("Conclusión del período")
        es_prueba = st.checkbox("Dato de prueba o provisorio (VP)", value=True)
        estado = st.selectbox("Estado", ["publicado", "borrador"])
        guardar = st.form_submit_button("Guardar")
    if guardar:
        try:
            guardar_medicion(
                user,
                item,
                etiquetas[label],
                numerador,
                denominador,
                conclusion,
                es_prueba,
                estado,
            )
            st.success("Medición guardada.")
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo guardar: {exc}")


def texto_nd_fila(item, medicion):
    from tablero_st.logic import texto_nd

    return texto_nd(
        medicion["numerador_valor"],
        medicion["denominador_valor"],
        item.get("tipo_calculo") == "razon",
        medicion["es_prueba"],
    )


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    user = st.session_state.get("user")
    if not user:
        pagina_login()
        return
    sidebar(user)
    vista = st.session_state.get("vista", "home")
    if vista == "area":
        vista_area(user)
    elif vista == "ficha":
        vista_ficha(user)
    else:
        vista_home(user)


if __name__ == "__main__":
    main()
else:
    main()
