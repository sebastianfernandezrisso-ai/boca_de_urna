import os
from sqlalchemy import create_engine, text
import streamlit as st

DATABASE_URL = st.secrets["DATABASE_URL"]

engine = create_engine(DATABASE_URL)



def create_table():
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mesas (
    id SERIAL PRIMARY KEY,
    mesa TEXT UNIQUE,
    sede TEXT,
    localidad TEXT,
    movimiento INTEGER,
    lista2 INTEGER,
    lista3 INTEGER,
    blanco INTEGER,
    impugnados INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


        """))
        conn.commit()

