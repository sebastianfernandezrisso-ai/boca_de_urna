import streamlit as st
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from db import engine, create_table
import hashlib
import io
from datetime import datetime
import PyPDF2
import re
TOTAL_MESAS = 151
PADRON_TOTAL = 9814

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
create_table()

st.markdown(
    """
<style>
    /* Oculta el menú automático de páginas */
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# CACHE
# =========================
@st.cache_data(ttl=5)
def get_mesas():
    return pd.read_sql("SELECT * FROM mesas", engine)


@st.cache_data(ttl=60)
def get_padron_mesa(mesa):
    query = text("SELECT sede, localidad FROM mesas_padron WHERE mesa = :mesa")
    return pd.read_sql(query, engine, params={"mesa": mesa})


def colorear_filas(row):
    if row["verificado"]:
        return ["background-color: #c8f7c5; color: black"] * len(row)
    else:
        return ["background-color: #f7c5c5; color: black"] * len(row)


import pdfplumber
import re

@st.cache_data
def procesar_padron_estatico(file_or_path):

    def reconstruir_numeros(texto):
        # junta números separados por espacios (15 06 -> 1506)
        texto = re.sub(r'(\d)\s+(\d)', r'\1\2', texto)
        return texto

    try:
        texto = ""

        pdf = pdfplumber.open(file_or_path)

        for page in pdf.pages:
            t = page.extract_text(x_tolerance=2, y_tolerance=2)
            if t:
                texto += " " + t

        pdf.close()

        # 🔥 clave: reconstruir números fragmentados
        texto = reconstruir_numeros(texto)

        dict_totales = {}

        pattern = re.compile(
    r'MESA\s*[:\-]?\s*(\d+).*?TOTAL\D{0,10}(\d{1,6})',
    re.IGNORECASE | re.DOTALL
)

        for match in pattern.finditer(texto):
            mesa = match.group(1)
            total = int(match.group(2))
            dict_totales[mesa] = total

        return dict_totales

    except Exception as e:
        st.error(f"Error PDF: {e}")
        return {}

# --- CARGA INICIAL (Fuera de los tabs, al principio del script) ---
# Cambia "padron-con-corte-por-mesa.pdf" por el nombre exacto de tu archivo
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_PDF = os.path.join(BASE_DIR, "padron-con-corte-por-mesa.pdf")
if "dict_padron" not in st.session_state:
    st.session_state["dict_padron"] = procesar_padron_estatico(RUTA_PDF)

# =========================
# EXCEL CON GRAFICOS
# =========================
def generar_excel(df_dict):
    import io
    from openpyxl.chart import PieChart, Reference
    from openpyxl import Workbook

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # =========================
        # GUARDAR DATAFRAMES
        # =========================
        for nombre_hoja, df in df_dict.items():
            df.to_excel(writer, index=False, sheet_name=nombre_hoja[:31])

        wb = writer.book

        # =========================
        # CREAR HOJA DE GRAFICO
        # =========================
        ws_chart = wb.create_sheet(title="Grafico")

        totales_df = df_dict.get("Totales")

        if totales_df is not None and not totales_df.empty:

            # Escribir datos para gráfico
            ws_chart.append(["Lista", "Votos"])

            for _, row in totales_df.iterrows():
                ws_chart.append([row["Lista"], row["Votos"]])

            # Crear gráfico de torta
            pie = PieChart()
            labels = Reference(
                ws_chart, min_col=1, min_row=2, max_row=len(totales_df) + 1
            )
            data = Reference(
                ws_chart, min_col=2, min_row=1, max_row=len(totales_df) + 1
            )

            pie.add_data(data, titles_from_data=True)
            pie.set_categories(labels)
            pie.title = "Distribución de Votos"

            ws_chart.add_chart(pie, "D2")

    return output.getvalue()


# =========================
# LOGIN
# =========================
# Generamos los 151 usuarios de fiscales dinámicamente
USUARIOS = {
    "admin": {
        "password": hashlib.sha256("admin1986".encode()).hexdigest(),
        "rol": "admin",
    },
    "superadmin": {
        "password": hashlib.sha256("super123".encode()).hexdigest(),
        "rol": "superadmin",
    },
}

for i in range(1, 152):
    user_id = f"fiscal{i}"
    # Password por defecto: "mesa" + número (ej: mesa1, mesa2...)
    # ¡Cámbialo por algo más seguro si es necesario!
    pass_text = f"mesa{i}"
    USUARIOS[user_id] = {
        "password": hashlib.sha256(pass_text.encode()).hexdigest(),
        "rol": "fiscal",
        "mesa_asignada": str(i),
    }


def login():
    st.title("🔐 Login")

    # Capturamos los datos de los inputs
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if usuario in USUARIOS:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            if hashed == USUARIOS[usuario]["password"]:
                st.session_state.logged = True
                st.session_state.usuario = usuario
                st.session_state.rol = USUARIOS[usuario]["rol"]
                st.session_state.mesa_asignada = USUARIOS[usuario].get("mesa_asignada")
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        else:
            st.error("Usuario no existe")


if st.session_state.get("logged", False) and st.session_state.rol in [
    "admin",
    "superadmin",
]:

    # Mostrar sidebar nuevamente
    st.markdown(
        """
    <style>
        section[data-testid="stSidebar"] {
            display: block;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("## ⚙️ Panel de administración")

        st.page_link("app.py", label="🏠 Inicio")
        st.page_link("pages/editar_mesas.py", label="✏️ Editar Mesas")

        st.divider()

        if st.button("🚪 Cerrar sesión"):
            st.session_state.clear()
            st.rerun()

# =========================
# CONTROL LOGIN
# =========================
if "logged" not in st.session_state:
    st.session_state.logged = False

if not st.session_state.logged:
    login()
    st.stop()

st.title("🗳️ Escrutinio")

col_user1, col_user2 = st.columns([6, 1])
with col_user2:
    st.write(f"👤 {st.session_state.usuario}")
    if st.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

# =========================
# 📊 METRICAS ARRIBA (FIX)
# =========================
if st.session_state.rol in ["admin", "superadmin"]:

    df_metrics = get_mesas()

    cols = [
        "Lista movimiento",
        "Multicolor",
        "blanco",
        "impugnados",
        "recurridos",
        "nulos",
    ]

    if not df_metrics.empty:
        df_metrics[cols] = (
            df_metrics[cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        )

        total_votos = int(df_metrics[cols].sum().sum())
        mesas_cargadas = len(df_metrics)

        totales_listas = df_metrics[["Lista movimiento", "Multicolor"]].sum()

        lista_ganadora = totales_listas.idxmax()
        diferencia = int(totales_listas.max() - totales_listas.min())

        participacion = (total_votos / PADRON_TOTAL) * 100 if total_votos > 0 else 0

    else:
        total_votos = 0
        mesas_cargadas = 0
        lista_ganadora = "-"
        diferencia = 0
        participacion = 0

    progreso = mesas_cargadas / TOTAL_MESAS if TOTAL_MESAS else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Mesas", mesas_cargadas)
    col2.metric("Votos", total_votos)
    col3.metric("Participación", f"{participacion:.2f}%")
    col4.metric("% Escrutado", f"{progreso*100:.2f}%")
    col5.metric("Ganador", lista_ganadora, f"+{diferencia}")

    st.progress(progreso)

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📝 CARGA",
        "📊 GENERALES",
        "🏙️ LOCALIDAD",
        "PARTICIPACION",
    ]
)

# ================= TAB 1 =================
with tab1:

    if "limpiar_form" not in st.session_state:
        st.session_state.limpiar_form = False

    if st.session_state.limpiar_form:
        # Limpiamos los campos, pero NO tocamos 'mesa' en el session_state
        # si es fiscal para que no se borre su asignación
        campos_a_limpiar = [
            "movimiento",
            "lista2",
            "blanco",
            "impugnados",
            "recurridos",
            "nulos",
        ]
        if st.session_state.rol != "fiscal":
            campos_a_limpiar.append("mesa")

        for k in campos_a_limpiar:
            st.session_state[k] = 0
        st.session_state.limpiar_form = False

    # --- Lógica de Usuario ---
    es_fiscal = st.session_state.rol == "fiscal"
    mesa_asignada = st.session_state.get("mesa_asignada", "")

    with st.form("carga"):
        # Si es fiscal, la mesa viene pre-cargada y bloqueada
        if es_fiscal:
            st.info(f"📋 Cargando datos como: **{st.session_state.usuario}**")
            mesa = st.text_input("Mesa", value=mesa_asignada, disabled=True)
        else:
            # Si es admin/superadmin, puede escribir la mesa
            mesa = st.text_input("Mesa", placeholder="Ingrese número de mesa")

        col1, col2 = st.columns(2)

        with col1:
            movimiento = st.number_input(
                "Lista Movimiento",
                min_value=0,
                value=None,
                placeholder="0",
                key="movimiento",
            )
            lista2 = st.number_input(
                "Multicolor",
                min_value=0,
                value=None,
                placeholder="0",
                key="lista2",
            )
            blanco = st.number_input(
                "Blanco",
                min_value=0,
                value=None,
                placeholder="0",
                key="blanco",
            )

        with col2:
            impugnados = st.number_input(
                "Impugnados",
                min_value=0,
                value=None,
                placeholder="0",
                key="impugnados",
            )
            recurridos = st.number_input(
                "Recurridos",
                min_value=0,
                value=None,
                placeholder="0",
                key="recurridos",
            )
            nulos = st.number_input(
                "Nulos",
                min_value=0,
                value=None,
                placeholder="0",
                key="nulos",
            )

        if st.form_submit_button("Guardar"):
            if not mesa:
                st.error("Debe indicar un número de mesa")
            else:
                result = get_padron_mesa(mesa)

                if result.empty:
                    st.error(f"La mesa {mesa} no existe en el padrón")
                else:
                    sede = result.iloc[0]["sede"]
                    localidad = result.iloc[0]["localidad"]

                    # Identificamos quién carga para la auditoría
                    fiscal_user = st.session_state.usuario

                    try:
                        with engine.begin() as conn:
                            conn.execute(
        text("""
            INSERT INTO mesas 
            (mesa, sede, localidad, "Lista movimiento", "Multicolor", blanco, impugnados, recurridos, nulos, fiscal_user)
            VALUES 
            (:mesa, :sede, :localidad, :movimiento, :lista2, :blanco, :impugnados, :recurridos, :nulos, :fiscal_user)
            ON CONFLICT (mesa)
            DO UPDATE SET
                "Lista movimiento" = EXCLUDED."Lista movimiento",
                "Multicolor" = EXCLUDED."Multicolor",
                blanco = EXCLUDED.blanco,
                impugnados = EXCLUDED.impugnados,
                recurridos = EXCLUDED.recurridos,
                nulos = EXCLUDED.nulos,
                fiscal_user = EXCLUDED.fiscal_user;
        """),
        {
            "mesa": mesa,
            "sede": sede,
            "localidad": localidad,
            "movimiento": movimiento or 0,
            "lista2": lista2 or 0,
            "blanco": blanco or 0,
            "impugnados": impugnados or 0,
            "recurridos": recurridos or 0,
            "nulos": nulos or 0,
            "fiscal_user": fiscal_user,
        },
    )

                        st.success(f"✅ Mesa {mesa} guardada exitosamente")
                        st.session_state.limpiar_form = True
                        get_mesas.clear()
                        st.rerun()

                    except IntegrityError:
                        st.warning(f"⚠️ La mesa {mesa} ya fue cargada anteriormente.")

# ================= TAB 2 =================
with tab2:
    if st.session_state.rol not in ["admin", "superadmin"]:
        st.warning("🔒 Acceso restringido a administradores. Por favor, utilice las pestañas de Carga o Participación.")
    else:
        df = get_mesas()

        st.markdown("🟢 **Mesa Verificada** &nbsp;&nbsp;&nbsp; 🔴 **Mesa No verificada**")
        st.markdown(
            "**La verificación se puede guardar desde tabla principal sin ir a editar datos. Esto es por si se chequea que los datos son correctos**"
        )
        
        if df.empty:
            st.info("Sin datos cargados aún.")
        else:
            cols = [
                "Lista movimiento",
                "Multicolor",
                "blanco",
                "impugnados",
                "recurridos",
                "nulos",
            ]

            # Normalizar datos numéricos
            df[cols] = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)

        # =========================
        # DATA EDITOR (CHECKBOX)
        # =========================
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            disabled=[
                "id",
                "mesa",
                "sede",
                "localidad",
                "Lista movimiento",
                "Multicolor",
                "blanco",
                "impugnados",
                "recurridos",
                "nulos",
                "created_at",
            ],
            column_config={
                "verificado": st.column_config.CheckboxColumn("✔ Verificado")
            },
            key="editor_verificacion",
        )
        # =========================
        # GUARDAR
        # =========================
        if st.button("💾 Guardar verificación"):
            with engine.begin() as conn:
                for _, row in edited_df.iterrows():
                    conn.execute(
                        text("""
                            UPDATE mesas
                            SET verificado = :verificado
                            WHERE id = :id
                        """),
                        {
                            "verificado": bool(row["verificado"]),
                            "id": int(row["id"]),
                        },
                    )
            st.success("Verificación actualizada")
            get_mesas.clear()
            st.rerun()
        # =========================
        # COLORES
        # =========================
        st.dataframe(
            edited_df.style.apply(colorear_filas, axis=1),
            use_container_width=True,
        )

        # =========================
        # NAVEGACIÓN
        # =========================
        st.page_link("pages/editar_mesas.py", label="✏️ Editar tabla completa")

        # =========================
        # TOTALES
        # =========================
        totales = df[cols].sum().sort_values(ascending=False)
        st.dataframe(totales.to_frame("Total"))

        # =========================
        # EXPORT
        # =========================
        
        st.divider()

        totales_df = totales.to_frame("Votos").reset_index()
        totales_df.columns = ["Lista", "Votos"]

        excel_data = generar_excel(
            {
                "Mesas": df,
                "Totales": totales_df,
            }
        )

        st.download_button("Descargar Excel con totales", excel_data, "resultados.xlsx")
###RESET POR MESA########
if st.session_state.rol in ["admin", "superadmin"]:

    st.divider()
    st.markdown("### 🧽 Limpiar votos de una mesa (sin afectar participación)")

    mesa_borrar = st.text_input("Mesa a limpiar", key="mesa_limpiar")

    if st.button("Limpiar escrutinio definitivo"):
        if not mesa_borrar:
            st.warning("Ingrese una mesa")
        else:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE mesas
                        SET 
                            "Lista movimiento" = NULL,
                            "Multicolor" = NULL,
                            blanco = NULL,
                            impugnados = NULL,
                            recurridos = NULL,
                            nulos = NULL
                        WHERE mesa = :mesa
                    """),
                    {"mesa": mesa_borrar}
                )

            st.success(f"✅ Escrutinio de mesa {mesa_borrar} limpiado")
            get_mesas.clear()
            st.rerun()
# =========================
# 🔥 RESET TOTAL (SOLO SUPERADMIN)
# =========================
if st.session_state.rol == "superadmin":

    st.divider()
    st.markdown("### ⚠️ RESET TOTAL DEL SISTEMA")

    st.warning("Esta acción borra TODAS las mesas cargadas")

    confirmar = st.checkbox("Confirmo que quiero borrar todos los datos")
    texto = st.text_input("Escribí RESET para confirmar")

    # Inicializar sesión
    if "backup_csv" not in st.session_state:
        st.session_state.backup_csv = None

    if "backup_excel" not in st.session_state:
        st.session_state.backup_excel = None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

    if st.button("🧨 Generar Backup y Resetear", use_container_width=True):

        if not confirmar or texto != "RESET":
            st.error("Debes confirmar y escribir RESET correctamente")
        else:
            try:
                df_backup = get_mesas()

                if not df_backup.empty:

                    # ===== CSV =====
                    st.session_state.backup_csv = df_backup.to_csv(index=False).encode(
                        "utf-8"
                    )

                    # ===== EXCEL =====
                    excel_data = generar_excel({"Mesas": df_backup})

                    st.session_state.backup_excel = excel_data

                # ===== RESET REAL =====
                with engine.begin() as conn:
                    conn.execute(text("TRUNCATE TABLE mesas RESTART IDENTITY"))

                # limpiar cache
                get_mesas.clear()

                st.success("✅ Base reiniciada correctamente")
                st.info("Ahora podés descargar el backup 👇")
                get_mesas.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    # =========================
    # ⬇️ DESCARGAS
    # =========================
    if st.session_state.get("backup_csv"):

        st.download_button(
            "⬇️ Descargar Backup CSV",
            st.session_state.backup_csv,
            f"backup_{timestamp}.csv",
            "text/csv",
            use_container_width=True,
        )

    if st.session_state.get("backup_excel"):

        st.download_button(
            "⬇️ Descargar Backup Excel",
            st.session_state.backup_excel,
            f"backup_{timestamp}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

with tab3:
    if st.session_state.rol != "admin":
        st.warning("⛔ Solo el administrador puede ver resultados")
        #st.stop()

    st.markdown("### RESULTADOS POR LOCALIDAD/MESAS")

    df = pd.read_sql("SELECT * FROM mesas", engine)

    cols = [
        "Lista movimiento",
        "Multicolor",
        "blanco",
        "impugnados",
        "recurridos",
        "nulos",
    ]

    if df.empty:
        st.info("Aún no hay datos cargados.")

    else:
        # =========================
        # NORMALIZAR DATOS
        # =========================
        df[cols] = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)

        localidades = sorted(df["localidad"].dropna().unique())

        localidad_seleccionada = st.selectbox("Seleccionar localidad", localidades)
        st.session_state["localidad_seleccionada"] = localidad_seleccionada
        df_localidad = df[df["localidad"] == localidad_seleccionada]
        
        st.markdown(f"### 📍 Resultados en {localidad_seleccionada}")

        # =========================
        # TOTALES
        # =========================
        totales = df_localidad[cols].sum().sort_values(ascending=False)

        st.markdown("#### Totales")
        st.dataframe(totales.to_frame("Votos"), use_container_width=True)

        # =========================
        # PORCENTAJES
        # =========================
        total_votos = totales.sum()

        if total_votos > 0:
            porcentajes = (totales / total_votos * 100).round(2)

            st.markdown("#### Porcentajes")
            st.dataframe(porcentajes.to_frame("%"), use_container_width=True)
        else:
            porcentajes = pd.DataFrame()

        # =========================
        # EXPORTAR ✅ (ACÁ VA)
        # =========================
        if st.session_state.rol in ["admin", "superadmin"]:

            st.divider()
            st.markdown("### ⬇️ Exportar resultados de localidad")

            totales_df = totales.to_frame("Votos").reset_index()
            totales_df.columns = ["Lista", "Votos"]

            if not porcentajes.empty:
                porcentajes_df = porcentajes.to_frame("%").reset_index()
                porcentajes_df.columns = ["Lista", "Porcentaje"]
            else:
                porcentajes_df = pd.DataFrame()

            excel_data = generar_excel(
                {
                    f"Mesas_{localidad_seleccionada}": df_localidad,
                    "Totales": totales_df,
                    "Porcentajes": porcentajes_df,
                }
            )
# ================= TAB 4 =================
with tab4:
    st.header("📈 Participación Provisoria Dinámica")

    # --- CARGA DEL PADRON (Solo Admin/Superadmin) ---
    if st.session_state.rol in ["admin", "superadmin"]:
        with st.expander("📁 Cargar Padrón Oficial (PDF)"):
            archivo_padron = st.file_uploader("Subir PDF del padrón para calcular porcentajes exactos", type="pdf")
            if archivo_padron:
                dict_padron = procesar_padron_estatico(archivo_padron)
                st.session_state["dict_padron"] = dict_padron
                st.success(f"✅ Padrón procesado: {len(dict_padron)} mesas detectadas.")

    # Variables de control
    rol = st.session_state.get("rol")
    mesa_f = st.session_state.get("mesa_asignada")
    usuario_f = st.session_state.get("usuario")
    padron_procesado = st.session_state.get("dict_padron", {})

    # --- VISTA FISCAL: FORMULARIO DE CARGA ---
    if rol == "fiscal":
        total_esta_mesa = padron_procesado.get(str(mesa_f), 0)
        st.subheader(f"Corte de mesa {mesa_f}")
        
        if total_esta_mesa > 0:
            st.info(f"📍 Total electores en padrón para esta mesa: **{total_esta_mesa}**")
        else:
            st.warning("⚠️ Padrón no cargado por administrador. El porcentaje global no se verá reflejado aún.")

        # Consultamos si ya existe algún dato previo en la DB para mostrarlo
        with engine.connect() as conn:
            res_p = conn.execute(
        text("SELECT cantidad_voto, hora_participacion FROM mesas WHERE mesa = :m"),
        {"m": mesa_f}
        ).fetchone()
        
        c_ini = res_p[0] if res_p and res_p[0] is not None else 0
        h_ini_str = res_p[1] if res_p and res_p[1] is not None else datetime.now().strftime("%H:%M")

        with st.form("carga_participacion_fiscal"):
            col_a, col_b = st.columns(2)
            with col_a:
                nueva_cantidad = st.number_input("Cantidad de votantes actuales", min_value=0, value=c_ini, step=1)
            with col_b:
                try:
                    h_obj = datetime.strptime(h_ini_str, "%H:%M").time()
                except:
                    h_obj = datetime.now().time()
                nueva_hora = st.time_input("Hora del corte", value=h_obj)
            
            enviar = st.form_submit_button("Actualizar Participación Provisoria")

            if enviar:
                info_mesa = get_padron_mesa(mesa_f)

                sede_f = info_mesa.iloc[0]["sede"] if not info_mesa.empty else "S/D"
                loc_f = info_mesa.iloc[0]["localidad"] if not info_mesa.empty else "S/D"

                with engine.begin() as conn:
                    conn.execute(
    text("""
        INSERT INTO mesas (
            mesa, cantidad_voto, hora_participacion, fiscal_user
        )
        VALUES (
            :mesa, :cant, :hora, :user
        )
        ON CONFLICT (mesa)
        DO UPDATE SET
            cantidad_voto = EXCLUDED.cantidad_voto,
            hora_participacion = EXCLUDED.hora_participacion,
            fiscal_user = EXCLUDED.fiscal_user;
    """),
    {
        "mesa": str(mesa_f),   # 👈 IMPORTANTE: sin PART-
        "cant": nueva_cantidad,
        "hora": nueva_hora.strftime("%H:%M"),
        "user": usuario_f
    }
)

                    st.success(
                f"✅ Provisorio actualizado — {nueva_cantidad} votantes a las {nueva_hora.strftime('%H:%M')}"
                )

                get_mesas.clear()
                st.rerun()

    # --- VISTA ADMIN/SUPERADMIN: MÉTRICAS BASADAS EN PDF ---
    if rol in ["admin", "superadmin"]:
        df_admin = get_mesas()
        
        if not df_admin.empty:
            # Solo trabajamos con las que tienen datos de votos o participación
            df_con_datos = df_admin.copy()
            
            # Función para calcular métricas individuales por fila comparando con el PDF
            def calcular_metricas_pdf(row):
                m_id = str(row["mesa"])
                votos = row["cantidad_voto"] if row["cantidad_voto"] else 0
                total_padron = padron_procesado.get(m_id, 0)
                porc = (votos / total_padron * 100) if total_padron > 0 else 0
                return pd.Series([total_padron, porc])

            df_con_datos[["Total Padrón", "% Part."]] = df_con_datos.apply(calcular_metricas_pdf, axis=1)
            
            # Totales Generales
            t_votantes = int(df_con_datos["cantidad_voto"].sum())
            total_electores_pdf = sum(padron_procesado.values()) if padron_procesado else PADRON_TOTAL
            perc_global = (t_votantes / total_electores_pdf * 100) if total_electores_pdf > 0 else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Votantes en Urna", f"{t_votantes:,}")
            m2.metric("% Participación Global", f"{perc_global:.2f}%")
            m3.metric("Mesas Reportadas", f"{len(df_con_datos[df_con_datos['cantidad_voto'] > 0])}")

            st.divider()
            
            # Tabla de monitoreo detallada
            st.subheader("📋 Detalle por Mesa")
            st.dataframe(
                df_con_datos[["mesa", "localidad", "cantidad_voto", "Total Padrón", "% Part.", "hora_participacion"]]
                .sort_values(by="% Part.", ascending=False),
                use_container_width=True,
                column_config={
                    "mesa": "Mesa",
                    "cantidad_voto": "Votaron",
                    "Total Padrón": "Padron Real",
                    "% Part.": st.column_config.NumberColumn("Participación", format="%.2f%%"),
                    "hora_participacion": "Últ. Corte"
                }
            )
        else:
            st.info("Aún no hay datos de participación cargados.")
            st.download_button(
                "📥 Descargar Excel Localidad",
                data=excel_data,
                file_name = f"resultados_{st.session_state.get('localidad_seleccionada','')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
