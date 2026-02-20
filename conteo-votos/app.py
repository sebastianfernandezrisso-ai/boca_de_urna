import streamlit as st
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from db import engine, create_table

st.set_page_config(layout="wide")

create_table()

st.title("🗳️ Fiscalización")

# =============================
# TABS
# =============================
tab1, tab2, tab3 = st.tabs([
    "📝 Carga de Mesa",
    "📊 Totales Generales",
    "🏙️ Totales por Localidad"
])

# =====================================================
# 📝 TAB 1 - CARGA
# =====================================================
with tab1:

    st.markdown("### Carga de Mesa")

    col_c1, col_c2, col_c3 = st.columns([1,2,1])

    with col_c2:
        with st.form("carga"):

            mesa = st.text_input("Mesa")

            col1, col2 = st.columns(2)

            with col1:
                movimiento = st.number_input("Movimiento", min_value=0,value=None, placeholder="Ingrese votos")
                lista2 = st.number_input("Lista 2", min_value=0,value=None, placeholder="Ingrese votos")
                blanco = st.number_input("Blanco", min_value=0,value=None, placeholder="Ingrese votos")

            with col2:
                lista3 = st.number_input("Lista 3", min_value=0,value=None, placeholder="Ingrese votos")
                impugnados = st.number_input("Impugnados", min_value=0,value=None, placeholder="Ingrese votos")

            submit = st.form_submit_button("Guardar")

            if submit:

                query = text("SELECT sede, localidad FROM mesas_padron WHERE mesa = :mesa")
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
                                conn.execute(text("""
                                    INSERT INTO mesas
                                    (mesa, sede, localidad, movimiento, lista2, lista3, blanco, impugnados)
                                    VALUES (:mesa, :sede, :localidad, :movimiento, :lista2, :lista3, :blanco, :impugnados)
                                """), {
                                    "mesa": mesa,
                                    "sede": sede,
                                    "localidad": localidad,
                                    "movimiento": movimiento,
                                    "lista2": lista2,
                                    "lista3": lista3,
                                    "blanco": blanco,
                                    "impugnados": impugnados
                                })

                            st.success("Mesa cargada correctamente")

                        except IntegrityError:
                            st.warning("Esa mesa ya está cargada")


# =====================================================
# 📊 TAB 2 - MESAS + TOTALES GENERALES
# =====================================================
with tab2:

    st.markdown("### Mesas Cargadas")

    df = pd.read_sql(
    "SELECT * FROM mesas ORDER BY CAST(mesa AS INTEGER) ASC",
    engine
    )

    if df.empty:
        st.info("Aún no hay datos cargados.")
    else:

        cols_numericas = ["movimiento", "lista2", "lista3", "blanco", "impugnados"]
        df[cols_numericas] = df[cols_numericas].apply(pd.to_numeric, errors="coerce").fillna(0)

        # =========================
        # EDITOR
        # =========================
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="fixed",
            disabled=["id", "mesa", "sede", "localidad", "created_at"],
            key="editor_mesas"
        )

        if st.button("💾 Guardar cambios en la mesa"):
            with engine.begin() as conn:
                for _, row in edited_df.iterrows():
                    conn.execute(text("""
                        UPDATE mesas SET
                            movimiento = :movimiento,
                            lista2 = :lista2,
                            lista3 = :lista3,
                            blanco = :blanco,
                            impugnados = :impugnados
                        WHERE id = :id
                    """), {
                        "movimiento": int(row["movimiento"]),
                        "lista2": int(row["lista2"]),
                        "lista3": int(row["lista3"]),
                        "blanco": int(row["blanco"]),
                        "impugnados": int(row["impugnados"]),
                        "id": int(row["id"])
                    })

            st.success("Cambios guardados correctamente")
            st.rerun()

        st.divider()

        # =========================
        # ELIMINAR MESA
        # =========================
        st.markdown("### Eliminar Mesa")

        mesa_a_eliminar = st.selectbox(
            "Seleccionar mesa",
            df["mesa"].unique()
        )

        if st.button("🗑️ Eliminar Mesa"):
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM mesas WHERE mesa = :mesa"),
                    {"mesa": mesa_a_eliminar}
                )

            st.success("Mesa eliminada correctamente")
            st.rerun()

        st.divider()

        # =========================
        # TOTALES GENERALES
        # =========================
        st.markdown("### Totales Generales")

        totales = edited_df[cols_numericas].sum().sort_values(ascending=False)
        st.dataframe(totales.to_frame("Total"))

        total_votos = totales.sum()

        if total_votos > 0:
            porcentajes = (totales / total_votos * 100).round(2).sort_values(ascending=False)
            st.markdown("#### Porcentajes")
            st.dataframe(porcentajes.to_frame("%"))


    


# =====================================================
# 🏙️ TAB 3 - RESULTADOS POR LOCALIDAD (SELECTOR)
# =====================================================
with tab3:

    st.markdown("### Resultados por Localidad")

    df = pd.read_sql("SELECT * FROM mesas", engine)

    cols = ["movimiento", "lista2", "lista3", "blanco", "impugnados"]

    if df.empty:
        st.info("Aún no hay datos cargados.")
    else:
        # Convertir a numérico
        df[cols] = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0)

        # Obtener lista de localidades únicas ordenadas
        localidades = sorted(df["localidad"].dropna().unique())

        # 🎯 SELECTOR DESPLEGABLE
        localidad_seleccionada = st.selectbox(
            "Seleccionar localidad",
            localidades
        )

        # Filtrar solo la localidad elegida
        df_localidad = df[df["localidad"] == localidad_seleccionada]

        st.markdown(f"### 📍 Resultados en {localidad_seleccionada}")

        # Totales de la localidad
        totales = df_localidad[cols].sum().sort_values(ascending=False)

        st.markdown("#### Totales")
        st.dataframe(
            totales.to_frame("Votos"),
            use_container_width=True
        )

        # Total de votos
        total_votos = totales.sum()

        # Porcentajes
        if total_votos > 0:
            porcentajes = (totales / total_votos * 100).round(2)

            st.markdown("#### Porcentajes")
            st.dataframe(
                porcentajes.to_frame("%"),
                use_container_width=True
            )
# Columnas reales de tu base de datos
cols_numericas = ["movimiento", "lista2", "lista3", "blanco", "impugnados"]

if 'df' in locals() and not df.empty:
    # Asegurar que sean numéricas
    df[cols_numericas] = df[cols_numericas].apply(pd.to_numeric, errors="coerce").fillna(0)
    
    total_votos = int(df[cols_numericas].sum().sum())
    mesas_cargadas = len(df)
else:
    total_votos = 0
    mesas_cargadas = 0

st.metric("🗳️ Mesas cargadas", mesas_cargadas)
st.metric("📊 Total de votos cargados", total_votos)




















