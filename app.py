#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 11 18:16:51 2025

@author: paugarcia
"""

import streamlit as st
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh
import pandas as pd

from tfg import (
    obtener_aeronaves_ivao_catalunya,
    crear_mapa_aeronaves_streamlit,
    detectar_conflictos,
)

def resaltar_conflictos(row, indices_conflicto):
    """
    Devuelve estilo CSS para cada fila: fondo rojo si el índice está en conflicto.
    """
    if row.name in indices_conflicto:
        return ["background-color: #ffcccc"] * len(row)  # rojo claro
    else:
        return [""] * len(row)

st.set_page_config(
    page_title="Radar IVAO Cataluña",
    layout="wide"
)

st.title("Radar de vuelos IVAO sobre Cataluña")
st.write("Mapa en tiempo casi real basado en el feed Whazzup v2 de IVAO.")

# Estado inicial
if "aeronaves" not in st.session_state:
    st.session_state["aeronaves"] = None

col1, col2, col3 = st.columns(3)
with col1:
    max_aviones = st.slider("Máximo de aeronaves a mostrar", 10, 300, 150, 10)
with col2:
    intervalo = st.slider("Intervalo de actualización (segundos)", 10, 120, 30, 5)
with col3:
    auto = st.checkbox("Auto-actualizar mapa", value=False)

# --- Lógica de actualización de datos ---

if auto:
    st_autorefresh(interval=intervalo * 1000, key="auto_refresh")
    st.session_state["aeronaves"] = obtener_aeronaves_ivao_catalunya(
        max_aviones=max_aviones
    )
elif st.button("Actualizar ahora"):
    st.session_state["aeronaves"] = obtener_aeronaves_ivao_catalunya(
        max_aviones=max_aviones
    )

aeronaves = st.session_state["aeronaves"]

# --- Panel de métricas + mapa y tabla ---

if aeronaves:
    df = pd.DataFrame(aeronaves)

    # Detectar conflictos
    conflictos_indices = detectar_conflictos(aeronaves)
    num_conflictos = len(conflictos_indices)

    # Métricas arriba
    m1, m2, m3, m4 = st.columns(4)
    num_vuelos = len(df)
    alt_media = df["alt"].mean() if num_vuelos > 0 else 0
    vel_media = df["vel"].mean() if num_vuelos > 0 else 0

    m1.metric("Vuelos en la zona", num_vuelos)
    m2.metric("Altitud media (ft)", f"{alt_media:,.0f}")
    m3.metric("Velocidad media (kt)", f"{vel_media:,.0f}")
    m4.metric("Vuelos en posible conflicto", num_conflictos)


    # Mapa + tabla en dos columnas
    c_mapa, c_tabla = st.columns((2, 1))

    with c_mapa:
        mapa = crear_mapa_aeronaves_streamlit(aeronaves,conflictos=conflictos_indices)
        if mapa is None:
            st.warning("No hay aeronaves en la zona definida.")
        else:
            st_folium(mapa, width=900, height=650)
            if auto:
                st.caption(
                    f"Auto-actualización activada cada {intervalo} s. "
                    "Los datos se recargan automáticamente."
                )
            else:
                st.caption(
                    "Mapa mostrado con los últimos datos descargados. "
                    "Pulsa 'Actualizar ahora' para refrescar."
                )

    with c_tabla:
        st.subheader("Detalle de vuelos")
    
        # Seleccionamos columnas a mostrar
        df_mostrar = df[["callsign", "destino", "alt", "vel", "heading"]].copy()
        df_mostrar.rename(columns={
            "callsign": "Callsign",
            "destino": "Aeropuerto estimado",
            "alt": "Altitud (ft)",
            "vel": "Velocidad (kt)",
            "heading": "Rumbo (°)"
        }, inplace=True)
    
        # Aplicar estilo: filas en conflicto en rojo claro
        styled = df_mostrar.style.apply(
            resaltar_conflictos,
            axis=1,
            indices_conflicto=conflictos_indices
        )

        st.dataframe(styled, use_container_width=True, height=650)


else:
    st.info("Pulsa 'Actualizar ahora' o activa 'Auto-actualizar mapa' para cargar los vuelos.")

st.info(
    "Versión demo para TFG. El panel muestra número de vuelos, altitud y velocidad "
    "medias, y el detalle de cada vuelo (callsign, aeropuerto estimado, altitud, "
    "velocidad y rumbo)."
)

