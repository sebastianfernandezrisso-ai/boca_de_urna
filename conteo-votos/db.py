import streamlit as st
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres.vjhpuimpxssekyhoqwqu:Matanza2941@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"}
)

def create_table():
    with engine.begin() as conn:

        # =========================
        # 🗳️ ESCRUTINIO FINAL
        # =========================
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mesas_resultados (
                id SERIAL PRIMARY KEY,
                mesa TEXT UNIQUE,
                sede TEXT,
                localidad TEXT,

                lista_movimiento INTEGER DEFAULT 0,
                multicolor INTEGER DEFAULT 0,
                blanco INTEGER DEFAULT 0,
                impugnados INTEGER DEFAULT 0,
                recurridos INTEGER DEFAULT 0,
                nulos INTEGER DEFAULT 0,

                fiscal_user TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # =========================
        # ⏱️ PARTICIPACIÓN (CORTES)
        # =========================
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mesas_participacion (
                id SERIAL PRIMARY KEY,
                mesa TEXT,
                cantidad_voto INTEGER DEFAULT 0,
                hora_participacion TEXT,
                fiscal_user TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # =========================
        # 🧾 AUDITORÍA (HISTORIAL REAL)
        # =========================
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mesas_auditoria (
                id SERIAL PRIMARY KEY,
                mesa TEXT,
                tipo_accion TEXT,
                datos JSONB,
                usuario TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
