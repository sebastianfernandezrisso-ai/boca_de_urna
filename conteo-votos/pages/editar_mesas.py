import streamlit as st
import pandas as pd
from sqlalchemy import text
from db import engine
from app import get_mesas  # reutilizás cache


if "logged" not in st.session_state or not st.session_state.logged:
    st.warning("Debes iniciar sesión")
    st.stop()

if st.session_state.rol not in ["admin", "superadmin"]:
    st.error("No tenés permisos para editar")
    st.stop()
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)
st.set_page_config(layout="wide")

st.title("✏️ Edición de Mesas")

# =========================
# CARGAR DATOS
# =========================
df = get_mesas()

if df.empty:
    st.warning("No hay mesas cargadas")
    st.stop()

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
# EDITOR GRANDE
# =========================
edited = st.data_editor(
    df,
    use_container_width=True,
    num_rows="fixed",
    disabled=["id", "mesa", "sede", "localidad", "created_at"],
    column_config={
        "verificado": st.column_config.CheckboxColumn("✔ Verificado")
    },
)

# =========================
# BOTONES
# =========================
col1, col2 = st.columns(2)

with col1:
    if st.button("💾 Guardar cambios", use_container_width=True):

        with engine.begin() as conn:
            for _, row in edited.iterrows():
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
                    "id": int(row["id"]),
                })

        get_mesas.clear()
        st.success("Cambios guardados correctamente")

with col2:
    if st.button("⬅️ Volver", use_container_width=True):
        st.switch_page("app.py")