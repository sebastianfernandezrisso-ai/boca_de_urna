import streamlit as st
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from db import engine, create_table
import hashlib
import io
from datetime import datetime
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

def mesa_existe(mesa):
    query = text("SELECT 1 FROM mesas WHERE mesa = :mesa LIMIT 1")
    result = pd.read_sql(query, engine, params={"mesa": mesa})
    return not result.empty
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
            labels = Reference(ws_chart, min_col=1, min_row=2, max_row=len(totales_df)+1)
            data = Reference(ws_chart, min_col=2, min_row=1, max_row=len(totales_df)+1)

            pie.add_data(data, titles_from_data=True)
            pie.set_categories(labels)
            pie.title = "Distribución de Votos"

            ws_chart.add_chart(pie, "D2")

    return output.getvalue()
# =========================
# USUARIOS
# =========================
USUARIOS = {
    "admin": {
        "password": hashlib.sha256("admin1986".encode()).hexdigest(),
        "rol": "admin",
    },
    "usuario": {
        "password": hashlib.sha256("carga123".encode()).hexdigest(),
        "rol": "user",
    },
    "superadmin": {
        "password": hashlib.sha256("super123".encode()).hexdigest(),
        "rol": "superadmin",
    },
}


def login():
    st.title("🔐 Login")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if usuario in USUARIOS:
            hashed = hashlib.sha256(password.encode()).hexdigest()

            if hashed == USUARIOS[usuario]["password"]:
                st.session_state.logged = True
                st.session_state.usuario = usuario
                st.session_state.rol = USUARIOS[usuario]["rol"]
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        else:
            st.error("Usuario no existe")


st.set_page_config(layout="wide")

create_table()
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
def colorear_filas(row):
    if row["verificado"]:
        return ["background-color: #c8f7c5; color: black"] * len(row)  # verde claro
    else:
        return ["background-color: #f7c5c5; color: black"] * len(row)  # rojo claros
# =========================
# 📊 MÉTRICAS GENERALES (ARRIBA)
# =========================
if st.session_state.rol == "admin":
    # todo el bloque completo (incluyendo df = read_sql)
    TOTAL_MESAS = 151

    df = pd.read_sql("SELECT * FROM mesas", engine)

    cols_numericas = ["Lista movimiento", "Multicolor", "blanco", "impugnados"]
    
    if not df.empty:
        df[cols_numericas] = (
            df[cols_numericas].apply(pd.to_numeric, errors="coerce").fillna(0)
    )
        total_votos = int(df[cols_numericas].sum().sum())
        mesas_cargadas = len(df)
    else:
        total_votos = 0
        mesas_cargadas = 0
    cols_listas = ["Lista movimiento", "Multicolor"]
    PADRON_TOTAL = 9814

    if total_votos > 0:
        participacion = (total_votos / PADRON_TOTAL) * 100
    else:
        participacion = 0
    if not df.empty:
        totales_listas = df[cols_listas].sum()

        lista_ganadora = totales_listas.idxmax()
        lista_perdedora = totales_listas.idxmin()

        votos_ganador = int(totales_listas[lista_ganadora])
        votos_perdedor = int(totales_listas[lista_perdedora])

        diferencia = votos_ganador - votos_perdedor

        votos_ganador = f"+{diferencia}"
    else:
        lista_ganadora = "-"
        votos_ganador = "0"
    progreso = mesas_cargadas / TOTAL_MESAS if TOTAL_MESAS > 0 else 0
    porcentaje = progreso * 100

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("🗳️ Mesas cargadas", mesas_cargadas)
    col2.metric("📊 Total de votos", total_votos)
    col3.metric("👥 Participación", f"{participacion:.2f}%")
    col4.metric("📈 % mesas escrutado", f"{porcentaje:.2f}%")
    col5.metric("🏆 Va ganando", lista_ganadora, votos_ganador)

    st.progress(progreso)
    st.caption(f"{mesas_cargadas} de {TOTAL_MESAS} mesas escrutadas")
    st.metric("👥 Participación sobre padrón", f"{participacion:.2f}%")


# =============================
# TABS
# =============================
tab1, tab2, tab3 = st.tabs(
    [
        "📝 CARGA DE VOTOS POR MESA",
        "📊 TOTALES GENERALES",
        "🏙️ TOTALES POR LOCALIDAD/MESA",
    ]
)

# =====================================================
# 📝 TAB 1 - CARGA
# =====================================================
with tab1:

    st.markdown("### CARGA DE MESA")

    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    if "limpiar_form" not in st.session_state:
        st.session_state.limpiar_form = False
    with col_c2:
        if st.session_state.limpiar_form:
            st.session_state.mesa = ""
            st.session_state.movimiento = None
            st.session_state.lista2 = None
            st.session_state.blanco = None
            st.session_state.impugnados = None
            st.session_state.recurridos = None
            st.session_state.nulos = None
            st.session_state.limpiar_form = False
            if "mensaje_ok" in st.session_state:
                st.success(st.session_state.mensaje_ok)
                del st.session_state.mensaje_ok
        with st.form("carga"):

            mesa = st.text_input("Mesa", key="mesa")

            col1, col2 = st.columns(2)

            with col1:
                movimiento = st.number_input(
                    "Lista Movimiento",
                    min_value=0,
                    value=None,
                    placeholder="Ingrese votos",
                    key="movimiento",
                )
                lista2 = st.number_input(
                    "Multicolor",
                    min_value=0,
                    value=None,
                    placeholder="Ingrese votos",
                    key="lista2",
                )
                blanco = st.number_input(
                    "Blanco",
                    min_value=0,
                    value=None,
                    placeholder="Ingrese votos",
                    key="blanco",
                )

            with col2:

                impugnados = st.number_input(
                    "Impugnados",
                    min_value=0,
                    value=None,
                    placeholder="Ingrese votos",
                    key="impugnados",
                )
                recurridos = st.number_input(
                    "Recurridos",
                     min_value=0,
                     value=None,
                    placeholder="Ingrese votos",
                    key="recurridos",
                )

                nulos = st.number_input(
                    "Nulos",
                    min_value=0,
                    value=None,
                    placeholder="Ingrese votos",
                    key="nulos",
                )

            submit = st.form_submit_button("GUARDAR")

            if submit:

                query = text(
                    "SELECT sede, localidad FROM mesas_padron WHERE mesa = :mesa"
                )
                result = pd.read_sql(query, engine, params={"mesa": mesa})

                if result.empty:
                    st.error("Mesa no existe en padrón")

                else:
                    sede = result.iloc[0]["sede"]
                    localidad = result.iloc[0]["localidad"]

                    check_query = text("SELECT id FROM mesas WHERE mesa = :mesa")
                    existe = pd.read_sql(check_query, engine, params={"mesa": mesa})

                    if not existe.empty:
                        st.warning("Esa mesa ya está cargada")

                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(
                                    text(
                                        """
    INSERT INTO mesas
(mesa, sede, localidad, "Lista movimiento", "Multicolor", blanco, impugnados, recurridos, nulos)
VALUES (:mesa, :sede, :localidad, :movimiento, :lista2, :blanco, :impugnados, :recurridos, :nulos)
"""
                                    ),
                                    {
                                        "mesa": mesa,
                                        "sede": sede,
                                        "localidad": localidad,
                                        "movimiento": movimiento,
                                        "lista2": lista2,
                                        "blanco": blanco,
                                        "impugnados": impugnados,
                                        "recurridos": recurridos,
                                        "nulos": nulos,
                                    },
                                )

                            st.session_state.mensaje_ok = "Mesa cargada correctamente"
                            st.session_state.limpiar_form = True
                            st.rerun()

                        except IntegrityError:
                            st.warning("Esa mesa ya está cargada")


# =====================================================
# 📊 TAB 2 - MESAS + TOTALES GENERALES
# =====================================================
with tab2:
    if st.session_state.rol not in ["admin", "superadmin"]:
        st.warning("⛔ Solo el administrador puede acceder a esta sección")
        st.stop()

    st.markdown("### MESAS CARGADAS")

    df = pd.read_sql("SELECT * FROM mesas ORDER BY CAST(mesa AS INTEGER) ASC", engine)

    if df.empty:
        st.info("Aún no hay datos cargados.")
    else:
        cols_numericas = ["Lista movimiento", "Multicolor", "blanco", "impugnados","recurridos","nulos"]

        df[cols_numericas] = df[cols_numericas].apply(pd.to_numeric, errors="coerce").fillna(0)

        # =========================
        # 📝 EDITOR
        # =========================
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="fixed",
            disabled=["id", "mesa", "sede", "localidad", "created_at"],
            column_config={
                "verificado": st.column_config.CheckboxColumn("✔ Verificado")
            },
            key="editor_mesas",
        )

        st.dataframe(
            edited_df.style.apply(colorear_filas, axis=1),
            use_container_width=True
        )

        # =========================
        # 💾 GUARDAR
        # =========================
        if st.button("💾 Guardar cambios"):
            with engine.begin() as conn:
                for _, row in edited_df.iterrows():
                    conn.execute(text("""
                        UPDATE mesas SET
                            "Lista movimiento" = :movimiento,
                            "Multicolor" = :lista2,
                            blanco = :blanco,
                            impugnados = :impugnados,
                            recurridos = :recurridos,
                            nulos = :nulos,
                            verificado = :verificado
                        WHERE id = :id
                    """), {
                        "movimiento": int(row["Lista movimiento"]),
                        "lista2": int(row["Multicolor"]),
                        "blanco": int(row["blanco"]),
                        "impugnados": int(row["impugnados"]),
                        "recurridos": int(row["recurridos"]),
                        "nulos": int(row["nulos"]),
                        "verificado": bool(row["verificado"]),
                        "id": int(row["id"])
                    })

            st.success("Cambios guardados")
            st.rerun()

        st.divider()

        # =========================
        # 🗑️ ELIMINAR
        # =========================
        mesa_a_eliminar = st.selectbox("Seleccionar mesa", df["mesa"].unique())

        if st.button("🗑️ Eliminar Mesa"):
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM mesas WHERE mesa = :mesa"),
                    {"mesa": mesa_a_eliminar},
                )
            st.success("Mesa eliminada")
            st.rerun()

        st.divider()

        # =========================
        # 📊 TOTALES
        # =========================
        st.markdown("### Totales Generales")

        totales = edited_df[cols_numericas].sum().sort_values(ascending=False)
        st.dataframe(totales.to_frame("Total"))

        total_votos = totales.sum()

        if total_votos > 0:
            porcentajes = (totales / total_votos * 100).round(2)
            st.dataframe(porcentajes.to_frame("%"))

        st.divider()

        # =========================
        # 📥 EXPORTAR (LO QUE PEDISTE)
        # =========================
        if st.session_state.rol in ["admin", "superadmin"]:

            st.markdown("### ⬇️ Exportar datos")

            totales_df = totales.to_frame("Total").reset_index()
            totales_df.columns = ["Lista", "Votos"]

            if total_votos > 0:
                porcentajes_df = porcentajes.to_frame("%").reset_index()
                porcentajes_df.columns = ["Lista", "Porcentaje"]
            else:
                porcentajes_df = pd.DataFrame()
            # =========================
            # MÉTRICAS
            # =========================
            metricas_df = pd.DataFrame({
                "Indicador": [
                "Total votos",
                "Lista ganadora",
                "Diferencia"
                ],
                "Valor": [
            total_votos,
            totales.idxmax(),
            int(totales.max() - totales.min())
    ]
})
            excel_data = generar_excel({
            "Mesas": edited_df,
            "Totales": totales_df,
            "Porcentajes": porcentajes_df,
            "Metricas": metricas_df
})
            # =========================
            # MÉTRICAS
            # =========================
            metricas_df = pd.DataFrame({
                "Indicador": [
                "Total votos",
                "Lista ganadora",
                "Diferencia"
                ],
                "Valor": [
            total_votos,
            totales.idxmax(),
            int(totales.max() - totales.min())
    ]
})
            st.download_button(
                "📥 Descargar Excel Completo",
                data=excel_data,
                file_name="resultados_generales.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
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
                    st.session_state.backup_csv = df_backup.to_csv(index=False).encode("utf-8")

                    # ===== EXCEL =====
                    excel_data = generar_excel({
                        "Mesas": df_backup
                    })

                    st.session_state.backup_excel = excel_data

                # ===== RESET REAL =====
                with engine.begin() as conn:
                    conn.execute(text("TRUNCATE TABLE mesas RESTART IDENTITY"))

                # limpiar cache
                get_mesas.clear()

                st.success("✅ Base reiniciada correctamente")
                st.info("Ahora podés descargar el backup 👇")

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
            use_container_width=True
        )

    if st.session_state.get("backup_excel"):

        st.download_button(
            "⬇️ Descargar Backup Excel",
            st.session_state.backup_excel,
            f"backup_{timestamp}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
# =====================================================
# 🏙️ TAB 3 - RESULTADOS POR LOCALIDAD (SELECTOR)
# =====================================================
with tab3:
    if st.session_state.rol != "admin":
        st.warning("⛔ Solo el administrador puede ver resultados")
        st.stop()
    st.markdown("### RESULTADOS POR LOCALIDAD/MESAS")

    df = pd.read_sql("SELECT * FROM mesas", engine)

    cols = ["Lista movimiento", "Multicolor", "blanco", "impugnados","recurridos","nulos"]

    if df.empty:
        st.info("Aún no hay datos cargados.")
    else:
        # Convertir a numérico
        df[cols] = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0)

        # Obtener lista de localidades únicas ordenadas
        localidades = sorted(df["localidad"].dropna().unique())

        # 🎯 SELECTOR DESPLEGABLE
        localidad_seleccionada = st.selectbox("Seleccionar localidad", localidades)

        # Filtrar solo la localidad elegida
        df_localidad = df[df["localidad"] == localidad_seleccionada]

        st.markdown(f"### 📍 Resultados en {localidad_seleccionada}")

        # Totales de la localidad
        totales = df_localidad[cols].sum().sort_values(ascending=False)

        st.markdown("#### Totales")
        st.dataframe(totales.to_frame("Votos"), use_container_width=True)

        # Total de votos
        total_votos = totales.sum()

        # Porcentajes
        if total_votos > 0:
            porcentajes = (totales / total_votos * 100).round(2)

            st.markdown("#### Porcentajes")
            st.dataframe(porcentajes.to_frame("%"), use_container_width=True)
# Columnas reales de tu base de datos
cols_numericas = ["Lista movimiento", "Multicolor", "blanco", "impugnados","recurridos","nulos"]

if "df" in locals() and not df.empty:
    # Asegurar que sean numéricas
    df[cols_numericas] = (
        df[cols_numericas].apply(pd.to_numeric, errors="coerce").fillna(0)
    )

    total_votos = int(df[cols_numericas].sum().sum())
    mesas_cargadas = len(df)
    porcentaje = (mesas_cargadas / TOTAL_MESAS) * 100 if TOTAL_MESAS > 0 else 0
else:
    total_votos = 0
    mesas_cargadas = 0
if st.session_state.rol in ["admin", "superadmin"] and not df.empty:

    st.divider()
    st.markdown("### ⬇️ Exportar resultados de localidad")

    # Preparar datos
    totales_df = totales.to_frame("Votos").reset_index()
    totales_df.columns = ["Lista", "Votos"]

    if total_votos > 0:
        porcentajes_df = porcentajes.to_frame("%").reset_index()
        porcentajes_df.columns = ["Lista", "Porcentaje"]
    else:
        porcentajes_df = pd.DataFrame()

    excel_data = generar_excel({
        f"Mesas_{localidad_seleccionada}": df_localidad,
        "Totales": totales_df,
        "Porcentajes": porcentajes_df
    })

    st.download_button(
        "📥 Descargar Excel Localidad",
        data=excel_data,
        file_name=f"resultados_{localidad_seleccionada}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
