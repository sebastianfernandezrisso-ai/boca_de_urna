import streamlit as st
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from db import engine, create_table
import hashlib
import io
from datetime import datetime

TOTAL_MESAS = 151
PADRON_TOTAL = 9814

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
create_table()

st.markdown("""
<style>
    /* Oculta el menú automático de páginas */
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)
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
    "admin": {"password": hashlib.sha256("admin1986".encode()).hexdigest(), "rol": "admin"},
    "superadmin": {"password": hashlib.sha256("super123".encode()).hexdigest(), "rol": "superadmin"},
}

for i in range(1, 152):
    user_id = f"fiscal{i}"
    # Password por defecto: "mesa" + número (ej: mesa1, mesa2...) 
    # ¡Cámbialo por algo más seguro si es necesario!
    pass_text = f"mesa{i}" 
    USUARIOS[user_id] = {
        "password": hashlib.sha256(pass_text.encode()).hexdigest(),
        "rol": "fiscal",
        "mesa_asignada": str(i)
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
                # Guardamos todo en el session_state
                st.session_state.logged = True
                st.session_state.usuario = usuario
                st.session_state.rol = USUARIOS[usuario]["rol"]
                
                # Guardamos la mesa asignada (será un número para fiscales o None para admin)
                st.session_state.mesa_asignada = USUARIOS[usuario].get("mesa_asignada")
                
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        else:
            st.error("Usuario no existe")
    else:
            st.error("Usuario no existe")
if st.session_state.get("logged", False) and st.session_state.rol in ["admin", "superadmin"]:

    # Mostrar sidebar nuevamente
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            display: block;
        }
    </style>
    """, unsafe_allow_html=True)

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
tab1, tab2, tab3 = st.tabs(
    [
        "📝 CARGA",
        "📊 GENERALES",
        "🏙️ LOCALIDAD",
    ]
)

# ================= TAB 1 =================
with tab1:

    if "limpiar_form" not in st.session_state:
        st.session_state.limpiar_form = False

    if st.session_state.limpiar_form:
        # Limpiamos los campos, pero NO tocamos 'mesa' en el session_state 
        # si es fiscal para que no se borre su asignación
        campos_a_limpiar = ["movimiento", "lista2", "blanco", "impugnados", "recurridos", "nulos"]
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
                                text(
                                    """
                                    INSERT INTO mesas 
                                    (mesa, sede, localidad, "Lista movimiento", "Multicolor", blanco, impugnados, recurridos, nulos, fiscal_user)
                                    VALUES (:mesa, :sede, :localidad, :movimiento, :lista2, :blanco, :impugnados, :recurridos, :nulos, :fiscal_user)
                                    """
                                ),
                                {
                                    "mesa": mesa,
                                    "sede": sede,
                                    "localidad": localidad,
                                    "movimiento": movimiento if movimiento is not None else 0,
                                    "lista2": lista2 if lista2 is not None else 0,
                                    "blanco": blanco if blanco is not None else 0,
                                    "impugnados": impugnados if impugnados is not None else 0,
                                    "recurridos": recurridos if recurridos is not None else 0,
                                    "nulos": nulos if nulos is not None else 0,
                                    "fiscal_user": fiscal_user
                                }
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
        st.stop()

    df = get_mesas()

    st.markdown(
        "🟢 **Mesa Verificada** &nbsp;&nbsp;&nbsp; 🔴 **Mesa No verificada**"
    )
    st.markdown("**La verificación se puede guardar desde tabla principal sin ir a editar datos. Esto es por si se chequea que los datos son correctos**")
    if df.empty:
        st.info("Sin datos")

    else:

        cols = [
            "Lista movimiento",
            "Multicolor",
            "blanco",
            "impugnados",
            "recurridos",
            "nulos",
        ]

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
                        text(
                            """
                            UPDATE mesas
                            SET verificado = :verificado
                            WHERE id = :id
                        """
                        ),
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

        st.download_button(
            "Descargar Excel con totales",
            excel_data,
            "resultados.xlsx"
        )
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
        st.stop()

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

            st.download_button(
                "📥 Descargar Excel Localidad",
                data=excel_data,
                file_name=f"resultados_{localidad_seleccionada}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
