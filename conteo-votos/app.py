import streamlit as st
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from db import engine, create_table
import hashlib
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
        votos_ganador = int(totales_listas.max())
    else:
        lista_ganadora = "-"
        votos_ganador = 0
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
    (mesa, sede, localidad, "Lista movimiento", "Multicolor", blanco, impugnados)
    VALUES (:mesa, :sede, :localidad, :movimiento, :lista2, :blanco, :impugnados)
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
    if st.session_state.rol != "admin":
        st.warning("⛔ Solo el administrador puede acceder a esta sección")
        st.stop()
    st.markdown(
        "### MESAS CARGADAS (En la tabla se pueden editar los votos - Siempre dar a botón guardar cambios cuando se edita y se coloca el verificado)"
    )

    df = pd.read_sql("SELECT * FROM mesas ORDER BY CAST(mesa AS INTEGER) ASC", engine)

    if df.empty:
        st.info("Aún no hay datos cargados.")
    else:

        cols_numericas = ["Lista movimiento", "Multicolor", "blanco", "impugnados"]
        df[cols_numericas] = (
            df[cols_numericas].apply(pd.to_numeric, errors="coerce").fillna(0)
        )

        edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="fixed",
    disabled=["id", "mesa", "sede", "localidad", "created_at"],
    column_config={
        "verificado": st.column_config.CheckboxColumn(
            "✔ Verificado",
            help="Marcar cuando la mesa fue controlada",
            default=False
        )
    },
    key="editor_mesas",
)
        st.markdown("### Estado de verificación")
        st.markdown("""
🟢 **Verde**: Mesa verificada  
🔴 **Rojo**: Mesa no verificada
""")
        st.dataframe(
        edited_df.style.apply(colorear_filas, axis=1),
        use_container_width=True
)
        if st.button("💾 Guardar cambios"):
            with engine.begin() as conn:
                for _, row in edited_df.iterrows():
                    conn.execute(text("""
UPDATE mesas SET
    "Lista movimiento" = :movimiento,
    "Multicolor" = :lista2,
    blanco = :blanco,
    impugnados = :impugnados,
    verificado = :verificado
WHERE id = :id
"""), {
    "movimiento": int(row["Lista movimiento"]),
    "lista2": int(row["Multicolor"]),
    "blanco": int(row["blanco"]),
    "impugnados": int(row["impugnados"]),
    "verificado": bool(row["verificado"]),
    "id": int(row["id"])
})

            st.success("Cambios guardados correctamente")
            st.rerun()

        st.divider()

        # =========================
        # ELIMINAR MESA
        # =========================
        st.markdown(
            "### ELIMINAR MESA (Se puede eliminar la mesa y volver a cargarla desde **Carga de mesa**)"
        )

        mesa_a_eliminar = st.selectbox("Seleccionar mesa", df["mesa"].unique())

        if st.button("🗑️ Eliminar Mesa"):
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM mesas WHERE mesa = :mesa"),
                    {"mesa": mesa_a_eliminar},
                )

            st.success("Mesa eliminada correctamente")
            st.rerun()

        st.divider()

        # =========================
        # TOTALES GENERALES
        # =========================
        st.markdown("### Totales Generales en cantidad de votos")

        totales = edited_df[cols_numericas].sum().sort_values(ascending=False)
        st.dataframe(totales.to_frame("Total"))

        total_votos = totales.sum()

        if total_votos > 0:
            porcentajes = (
                (totales / total_votos * 100).round(2).sort_values(ascending=False)
            )
            st.markdown("#### Porcentajes totales")
            st.dataframe(porcentajes.to_frame("%"))


# =====================================================
# 🏙️ TAB 3 - RESULTADOS POR LOCALIDAD (SELECTOR)
# =====================================================
with tab3:
    if st.session_state.rol != "admin":
        st.warning("⛔ Solo el administrador puede ver resultados")
        st.stop()
    st.markdown("### RESULTADOS POR LOCALIDAD/MESAS")

    df = pd.read_sql("SELECT * FROM mesas", engine)

    cols = ["Lista movimiento", "Multicolor", "blanco", "impugnados"]

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
cols_numericas = ["Lista movimiento", "Multicolor", "blanco", "impugnados"]

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
