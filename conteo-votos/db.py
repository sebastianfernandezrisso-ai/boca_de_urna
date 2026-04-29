import streamlit as st
from sqlalchemy import create_engine, text

DATABASE_URL ="postgresql://postgres.vjhpuimpxssekyhoqwqu:Matanza2941@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"}
)

def create_table():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mesas (
    id SERIAL PRIMARY KEY,
    mesa TEXT UNIQUE,
    sede TEXT,
    localidad TEXT,
    movimiento INTEGER,
    lista2 INTEGER,
    
    blanco INTEGER,
    impugnados INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verificado BOOLEAN DEFAULT FALSE
);
        """))
    
