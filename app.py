import streamlit as st
import pandas as pd
from datetime import date
import sqlite3
import os
from database import obtener_conexion, inicializar_bd

# Configuración inicial de la página
st.set_page_config(
    page_title="Sistema de Mantenimiento",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar la hoja de estilos externa
def cargar_css(ruta_archivo="style.css"):
    if os.path.exists(ruta_archivo):
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

cargar_css()

# Conectar BD
inicializar_bd()
conn = obtener_conexion()

ICONOS = {
    "Aire Acondicionado": "❄️",
    "Plancha de Calentamiento / Agitación": "🔥",
    "Horno / Mufla / Estufa": "🌡️",
    "Nevera / Refrigerador de reactivos": "🧊",
    "Balanza Analítica / Granataria": "⚖️",
    "Espectrofotómetro / Medidor Óptico": "🔬",
    "Video Beam / Proyector": "📽️",
    "Bomba / Reactor": "⚙️",
    "Otro": "📦"
}

def badge_html(estado):
    if estado == "Operativo":
        return '<span class="badge badge-operativo">● Operativo</span>'
    elif estado == "En Mantenimiento":
        return '<span class="badge badge-mantenimiento">▲ En Mantenimiento</span>'
    else:
        return '<span class="badge badge-falla">■ Fuera de Servicio</span>'

# ================= SIDEBAR =================
st.sidebar.markdown("## 🏢 Gestión Institucional")

df_ubicaciones = pd.read_sql("SELECT * FROM ubicaciones ORDER BY tipo DESC, nombre ASC", conn)
laboratorios = df_ubicaciones[df_ubicaciones["tipo"] == "Laboratorio"]["nombre"].tolist()
aulas = df_ubicaciones[df_ubicaciones["tipo"] == "Aula"]["nombre"].tolist()

tipo_filtro = st.sidebar.radio("Clasificación de Espacios:", ["Laboratorios", "Aulas"])

if tipo_filtro == "Laboratorios":
    espacio_actual = st.sidebar.selectbox("Laboratorio Activo:", laboratorios)
else:
    espacio_actual = st.sidebar.selectbox("Aula Activa:", aulas)

fila_espacio = df_ubicaciones[df_ubicaciones["nombre"] == espacio_actual].iloc[0]
ubicacion_id = int(fila_espacio["id"])

# ================= ENCABEZADO =================
icono_espacio = "🔬" if fila_espacio["tipo"] == "Laboratorio" else "🏫"
st.markdown(f"# {icono_espacio} {espacio_actual}")
st.caption(f"**Ubicación:** {fila_espacio['tipo']} | **ID del Espacio:** #{ubicacion_id}")

tab_catalogo, tab_nuevo, tab_orden, tab_historial = st.tabs([
    "📋 Catálogo de Equipos", 
    "➕ Registrar Activo", 
    "🛠️ Registrar Mantenimiento", 
    "📜 Historial Técnico"
])

# ================= TAB 1: CATÁLOGO =================
with tab_catalogo:
    df_equipos = pd.read_sql("""
        SELECT id, codigo, nombre, categoria, marca, modelo, estado 
        FROM equipos 
        WHERE ubicacion_id = ?
    """, conn, params=(ubicacion_id,))

    if df_equipos.empty:
        st.info(f"💡 No hay equipos registrados en **{espacio_actual}**. Dirígete a la pestaña 'Registrar Activo' para agregar el primero.")
    else:
        # Métricas estilizadas con CSS externo
        c1, c2, c3 = st.columns(3)
        total = len(df_equipos)
        op = len(df_equipos[df_equipos["estado"] == "Operativo"])
        fallas = total - op

        c1.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Activos</div><div class="kpi-value">{total}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="kpi-card success"><div class="kpi-title">Operativos</div><div class="kpi-value">{op}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="kpi-card danger"><div class="kpi-title">En Falla / Mant.</div><div class="kpi-value">{fallas}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Buscador y filtros
        col_busq, col_est, col_vista = st.columns([2, 1, 1])
        busqueda = col_busq.text_input("Buscar equipo:", placeholder="Código, nombre o marca...")
        filtro_est = col_est.selectbox("Filtrar por estado:", ["Todos", "Operativo", "En Mantenimiento", "Fuera de Servicio"])
        modo_vista = col_vista.radio("Formato:", ["Tarjetas", "Tabla"], horizontal=True)

        df_filtrado = df_equipos.copy()
        if busqueda:
            df_filtrado = df_filtrado[
                df_filtrado["nombre"].str.contains(busqueda, case=False, na=False) |
                df_filtrado["codigo"].str.contains(busqueda, case=False, na=False) |
                df_filtrado["marca"].str.contains(busqueda, case=False, na=False)
            ]
        if filtro_est != "Todos":
            df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_est]

        if df_filtrado.empty:
            st.warning("No hay equipos que coincidan con el filtro.")
        else:
            if modo_vista == "Tabla":
                st.dataframe(df_filtrado.drop(columns=["id"]), use_container_width=True, hide_index=True)
            else:
                cols = st.columns(2)
                for i, row in df_filtrado.reset_index(drop=True).iterrows():
                    col = cols[i % 2]
                    ico = ICONOS.get(row['categoria'], '📦')
                    badge = badge_html(row['estado'])
                    
                    html_card = f"""
                    <div class="equip-card">
                        <div class="equip-header">
                            <span class="equip-code">{row['codigo']}</span>
                            {badge}
                        </div>
                        <div class="equip-name">{ico} {row['nombre']}</div>
                        <div class="equip-details">
                            <strong>Marca:</strong> {row['marca'] or 'N/A'} &nbsp;|&nbsp; 
                            <strong>Modelo:</strong> {row['modelo'] or 'N/A'}
                        </div>
                        <div>
                            <span class="cat-tag">{row['categoria']}</span>
                        </div>
                    </div>
                    """
                    col.markdown(html_card, unsafe_allow_html=True)

# ================= TAB 2: ALTA DE EQUIPO =================
with tab_nuevo:
    st.subheader(f"Registrar Nuevo Equipo en {espacio_actual}")
    with st.form("form_alta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Código de Inventario *", placeholder="Ej: EQ-AG-001")
        nom = col2.text_input("Nombre del Equipo *", placeholder="Ej: Plancha de calentamiento")

        col3, col4 = st.columns(2)
        cat = col3.selectbox("Tipo / Categoría", list(ICONOS.keys()))
        mar = col4.text_input("Marca / Fabricante", placeholder="Ej: Thermo Scientific")

        col5, col6 = st.columns(2)
        mod = col5.text_input("Modelo", placeholder="Ej: Cimarec+")
        est = col6.selectbox("Estado Inicial", ["Operativo", "En Mantenimiento", "Fuera de Servicio"])

        guardar = st.form_submit_button("Guardar en Inventario")
        if guardar:
            if cod.strip() and nom.strip():
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO equipos (codigo, nombre, categoria, marca, modelo, estado, ubicacion_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (cod.strip(), nom.strip(), cat, mar.strip(), mod.strip(), est, ubicacion_id))
                    conn.commit()
                    st.success(f"Equipo '{nom}' registrado correctamente.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Ya existe un equipo con ese código de inventario.")
            else:
                st.warning("Completa al menos el código y el nombre.")

# ================= TAB 3: MANTENIMIENTO =================
with tab_orden:
    st.subheader("Registrar Intervención Técnica")
    cursor = conn.cursor()
    cursor.execute("SELECT id, codigo, nombre FROM equipos WHERE ubicacion_id = ?", (ubicacion_id,))
    equipos_sala = cursor.fetchall()

    if not equipos_sala:
        st.warning("No hay equipos registrados en este espacio.")
    else:
        mapa = {f"[{eq[1]}] {eq[2]}": eq[0] for eq in equipos_sala}
        with st.form("form_mant", clear_on_submit=True):
            eq_sel = st.selectbox("Seleccionar Equipo:", list(mapa.keys()))
            col_t, col_e = st.columns(2)
            tipo_m = col_t.selectbox("Tipo de Tarea:", ["Preventivo (Rutina)", "Correctivo (Falla)"])
            nuevo_est = col_e.selectbox("Nuevo Estado:", ["Operativo", "En Mantenimiento", "Fuera de Servicio"])

            resp = st.text_input("Técnico o Responsable:")
            desc = st.text_area("Detalle de las labores realizadas:")

            if st.form_submit_button("Guardar Mantenimiento"):
                if resp.strip() and desc.strip():
                    id_eq = mapa[eq_sel]
                    cursor.execute("""
                        INSERT INTO mantenimientos (equipo_id, fecha, tipo, descripcion, responsable)
                        VALUES (?, ?, ?, ?, ?)
                    """, (id_eq, str(date.today()), tipo_m, desc.strip(), resp.strip()))
                    cursor.execute("UPDATE equipos SET estado = ? WHERE id = ?", (nuevo_est, id_eq))
                    conn.commit()
                    st.success("Mantenimiento registrado y estado sincronizado.")
                    st.rerun()
                else:
                    st.warning("Completa el responsable y la descripción.")

# ================= TAB 4: HISTORIAL =================
with tab_historial:
    st.subheader(f"Historial de {espacio_actual}")
    df_h = pd.read_sql("""
        SELECT m.fecha AS "Fecha", e.codigo AS "Código", e.nombre AS "Equipo", 
               m.tipo AS "Tipo", m.descripcion AS "Labor / Diagnóstico", 
               m.responsable AS "Responsable"
        FROM mantenimientos m
        INNER JOIN equipos e ON m.equipo_id = e.id
        WHERE e.ubicacion_id = ?
        ORDER BY m.id DESC
    """, conn, params=(ubicacion_id,))

    if df_h.empty:
        st.info("Sin registros de mantenimiento en este espacio.")
    else:
        st.dataframe(df_h, use_container_width=True, hide_index=True)