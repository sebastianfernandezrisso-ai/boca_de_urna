**import streamlit as st**

**import pandas as pd**

**from sqlalchemy import text**

**from sqlalchemy.exc import IntegrityError**

**from db import engine, create\_table**



**st.set\_page\_config(layout="wide")**



**create\_table()**



**st.title("🗳️ Fiscalización")**



**# -----------------------**

**# 🎨 Estilo minimalista**

**# -----------------------**

**st.markdown("""**

**<style>**

**.form-minimal {**

    **max-width: 300px;**

    **margin: auto;**

    **padding: 8px 3px 15px 3px;**

**}**



**.stTextInput>div>div>input,**

**.stNumberInput>div>div>input {**

    **border-radius: 6px;**

**}**



**.stButton>button {**

    **width: 100%;**

    **border-radius: 6px;**

    **height: 40px;**

    **font-weight: 500;**

**}**

**</style>**

**""", unsafe\_allow\_html=True)**



**# -----------------------**

**# Formulario Minimal**

**# -----------------------**

**st.markdown('<div class="form-minimal">', unsafe\_allow\_html=True)**



**with st.form("carga"):**



    **mesa = st.text\_input("Mesa")**



    **col1, col2 = st.columns(2)**



    **with col1:**

        **movimiento = st.number\_input("Movimiento", min\_value=0)**

        **lista2 = st.number\_input("Lista 2", min\_value=0)**

        **blanco = st.number\_input("Blanco", min\_value=0)**



    **with col2:**

        **lista3 = st.number\_input("Lista 3", min\_value=0)**

        **impugnados = st.number\_input("Impugnados", min\_value=0)**



    **submit = st.form\_submit\_button("Guardar")**



    **if submit:**



        **query = text("SELECT sede, localidad FROM mesas\_padron WHERE mesa = :mesa")**

        **result = pd.read\_sql(query, engine, params={"mesa": mesa})**



        **if result.empty:**

            **st.error("Mesa no existe en padrón")**



        **else:**

            **sede = result.iloc\[0]\["sede"]**

            **localidad = result.iloc\[0]\["localidad"]**



            **check\_query = text("SELECT id FROM mesas WHERE mesa = :mesa")**

            **existe = pd.read\_sql(check\_query, engine, params={"mesa": mesa})**



            **if not existe.empty:**

                **st.warning("Esa mesa ya está cargada")**



            **else:**

                **try:**

                    **with engine.begin() as conn:**

                        **conn.execute(text("""**

                            **INSERT INTO mesas**

                            **(mesa, sede, localidad, movimiento, lista2, lista3, blanco, impugnados)**

                            **VALUES (:mesa, :sede, :localidad, :movimiento, :lista2, :lista3, :blanco, :impugnados)**

                        **"""), {**

                            **"mesa": mesa,**

                            **"sede": sede,**

                            **"localidad": localidad,**

                            **"movimiento": movimiento,**

                            **"lista2": lista2,**

                            **"lista3": lista3,**

                            **"blanco": blanco,**

                            **"impugnados": impugnados**

                        **})**



                    **st.success("Mesa cargada correctamente")**



                **except IntegrityError:**

                    **st.warning("Esa mesa ya está cargada")**



**st.markdown('</div>', unsafe\_allow\_html=True)**



**# -----------------------**

**# Mostrar datos en vivo**

**# -----------------------**

**st.subheader("📊 Datos en Tiempo Real")**



**df = pd.read\_sql("SELECT \* FROM mesas ORDER BY id DESC", engine)**



**if not df.empty:**



    **df\["Eliminar"] = False**



    **edited\_df = st.data\_editor(**

        **df,**

        **use\_container\_width=True,**

        **num\_rows="fixed",**

        **key="editor"**

    **)**



    **col1, col2 = st.columns(2)**



    **# ------------------------**

    **# GUARDAR CAMBIOS**

    **# ------------------------**

    **with col1:**

        **if st.button("💾 Guardar Cambios"):**

            **for index, row in edited\_df.iterrows():**

                **with engine.begin() as conn:**

                    **conn.execute(text("""**

                        **UPDATE mesas**

                        **SET sede=:sede,**

                            **localidad=:localidad,**

                            **mesa=:mesa,**

                            **movimiento=:movimiento,**

                            **lista2=:lista2,**

                            **lista3=:lista3,**

                            **blanco=:blanco,**

                            **impugnados=:impugnados**

                        **WHERE id=:id**

                    **"""), {**

                        **"sede": row\["sede"],**

                        **"localidad": row\["localidad"],**

                        **"mesa": row\["mesa"],**

                        **"movimiento": row\["movimiento"],**

                        **"lista2": row\["lista2"],**

                        **"lista3": row\["lista3"],**

                        **"blanco": row\["blanco"],**

                        **"impugnados": row\["impugnados"],**

                        **"id": row\["id"]**

                    **})**



            **st.success("Cambios guardados correctamente")**

            **st.rerun()**



    **# ------------------------**

    **# ELIMINAR**

    **# ------------------------**

    **with col2:**

        **if st.button("🗑️ Eliminar seleccionadas"):**

            **ids\_a\_borrar = edited\_df\[edited\_df\["Eliminar"] == True]\["id"].tolist()**



            **if ids\_a\_borrar:**

                **with engine.begin() as conn:**

                    **conn.execute(**

                        **text("DELETE FROM mesas WHERE id IN :ids"),**

                        **{"ids": tuple(ids\_a\_borrar)}**

                    **)**



                **st.success("Mesas eliminadas correctamente")**

                **st.rerun()**

            **else:**

                **st.warning("No seleccionaste ninguna mesa")**



    **# -----------------------**

    **# Totales**

    **# -----------------------**

    **st.subheader("📈 Totales Generales")**

    **totales = df\[\["movimiento", "lista2", "lista3", "blanco", "impugnados"]].sum()**

    **st.write(totales)**



