
class aeronave:
    def __init__(self,callsign,vel,latitud,longitud,altitud):
        self.callsign = callsign
        self.altitud = float(altitud)
        self.vel = float(vel)
        self.lat = float(latitud)
        self.long = float(longitud)
        


def extraer_datos ():
    try:
        dades = open("AERONAUS.txt","rt")
    except FileNotFoundError:
        print ("Fichero no encontrado")
    f = None
    if f == None:
        lista_aeronaves_radar = []
        avion = dades.readline()
        while avion != "":
            callsign,vel,latitud,longitud,altitud = avion.split(",")
            aeronave = callsign,vel,latitud,longitud,altitud 
            lista_aeronaves_radar.append(aeronave)
            avion = dades.readline()
        print(lista_aeronaves_radar)
        dades.close()



if __name__ == "__main__":
    extraer_datos()
   
   
import math 
import base64
import time
import requests
import folium
from folium.features import DivIcon  # para rotar el icono con CSS


# ---------- LECTURA DESDE IVAO, FILTRANDO CATALUÑA ----------
def distancia_nm(lat1, lon1, lat2, lon2):
    """
    Distancia aproximada entre dos puntos (lat, lon) en millas náuticas.
    """
    R_km = 6371.0
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    dist_km = R_km * c
    return dist_km * 0.539957  # km -> NM

def detectar_conflictos(aeronaves, sep_vertical_ft=500, sep_horizontal_nm=5):
    """
    Devuelve un conjunto de índices de aeronaves que están en posible conflicto.
    Criterio: |altitud1 - altitud2| <= sep_vertical_ft y distancia <= sep_horizontal_nm.
    """
    conflictos = set()
    n = len(aeronaves)

    for i in range(n):
        for j in range(i + 1, n):
            a1 = aeronaves[i]
            a2 = aeronaves[j]

            # Separación vertical
            if abs(a1["alt"] - a2["alt"]) > sep_vertical_ft:
                continue

            # Separación horizontal
            d_nm = distancia_nm(a1["lat"], a1["lon"], a2["lat"], a2["lon"])
            if d_nm <= sep_horizontal_nm:
                conflictos.add(i)
                conflictos.add(j)

    return conflictos


def obtener_aeronaves_ivao_catalunya(max_aviones=200):
    """
    Descarga Whazzup v2 de IVAO y devuelve solo las aeronaves
    dentro de un bounding box aproximado de Cataluña, con heading.
    """
    url = "https://api.ivao.aero/v2/tracker/whazzup"  # feed oficial Whazzup v2 [web:292]
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # ... igual hasta pilotos = data.get("clients", {}).get("pilots", [])
    pilotos = data.get("clients", {}).get("pilots", [])
    aeronaves = []

    LAT_MIN, LAT_MAX = 40.5, 42.9
    LON_MIN, LON_MAX = 0.0, 3.5

    for p in pilotos:
        track = p.get("lastTrack") or {}
        fp = p.get("flightPlan") or {}

        lat = track.get("latitude")
        lon = track.get("longitude")
        alt = track.get("altitude")
        gs = track.get("groundSpeed")
        hdg = track.get("heading")  # rumbo en grados
        destino = fp.get("arrivalId") or fp.get("departureId") or "N/A"

        if lat is None or lon is None:
            continue

        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            continue

        avion = {
            "callsign": p.get("callsign", "NOCALL"),
            "destino": destino,
            "vel": float(gs) if gs is not None else 0.0,
            "lat": float(lat),
            "lon": float(lon),
            "alt": float(alt) if alt is not None else 0.0,
            "heading": float(hdg) if hdg is not None else None,
        }
        aeronaves.append(avion)

        if len(aeronaves) >= max_aviones:
            break

    return aeronaves



# ---------- MAPA FOLIUM CON AVIÓN ROTADO ----------

def crear_mapa_aeronaves(aeronaves, nombre_salida="mapa_ivao_catalunya.html", intervalo_refresh=30):
    if not aeronaves:
        print("No hay aeronaves para mostrar en el mapa")
        return

    lat_centro = sum(a["lat"] for a in aeronaves) / len(aeronaves)
    lon_centro = sum(a["lon"] for a in aeronaves) / len(aeronaves)

    # Mapa centrado en Cataluña
    mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=8)

    # Capas CartoDB claro/oscuro, Positron por defecto [web:258]
    folium.TileLayer(
        "cartodbpositron",
        name="CartoDB Positron",
        attr="Map tiles © CartoDB, data © OpenStreetMap contributors",
        show=True          # capa visible al abrir el mapa
    ).add_to(mapa)

    folium.TileLayer(
        "cartodbdark_matter",
        name="CartoDB Dark Matter",
        attr="Map tiles © CartoDB, data © OpenStreetMap contributors",
        show=False         # empieza desactivada
    ).add_to(mapa)

    folium.LayerControl().add_to(mapa)

    # Marcadores de las aeronaves con icono rotado
    for a in aeronaves:
        if a["heading"] is not None:
            rumbo_txt = f"{a['heading']:.0f}°"
            heading = a["heading"]
        else:
            rumbo_txt = "N/A"
            heading = 0.0

        popup = (
            f"{a['callsign']}<br>"
            f"Vel: {a['vel']} kt<br>"
            f"Alt: {a['alt']} ft<br>"
            f"Rumbo: {rumbo_txt}"
        )

        # Corrección de orientación del PNG (alineado con IVAO)
        angle_corr = heading + 65

        icon_html = f"""
        <div style="transform: rotate({angle_corr}deg);
                    transform-origin: 50% 50%;
                    width:32px; height:32px;">
            <img src='avion.png'
                 style='width:32px; height:32px;'>
        </div>
        """

        icono_rotado = DivIcon(
            html=icon_html,
            icon_size=(32, 32),
            icon_anchor=(16, 16)  # centro del icono
        )

        folium.Marker(
            location=[a["lat"], a["lon"]],
            popup=popup,
            icon=icono_rotado
        ).add_to(mapa)

    # Guardar HTML
    mapa.save(nombre_salida)
    print(f"Mapa guardado en {nombre_salida}")

    # Añadir meta-refresh al HTML para que el navegador recargue solo [web:352]
    try:
        with open(nombre_salida, "r", encoding="utf-8") as f:
            html = f.read()

        meta_tag = f'<meta http-equiv="refresh" content="{intervalo_refresh}">'
        if 'http-equiv="refresh"' not in html:
            html = html.replace(
                "<head>",
                f"<head>\n    {meta_tag}"
            )
            with open(nombre_salida, "w", encoding="utf-8") as f:
                f.write(html)
    except Exception as e:
        print(f"No se pudo insertar meta-refresh: {e}")


# ---------- PUNTO DE ENTRADA: ACTUALIZACIÓN AUTOMÁTICA ----------

if __name__ == "__main__":
    INTERVALO = 30  # segundos entre actualizaciones

    while True:
        print("Descargando datos de IVAO y actualizando mapa...")
        aeronaves = obtener_aeronaves_ivao_catalunya(max_aviones=200)
        crear_mapa_aeronaves(
            aeronaves,
            nombre_salida="mapa_ivao_catalunya.html",
            intervalo_refresh=INTERVALO
        )
        print(f"Mapa actualizado. Próxima actualización en {INTERVALO} segundos.")
        time.sleep(INTERVALO)

import base64
import folium
from folium.features import DivIcon

def crear_mapa_aeronaves_streamlit(aeronaves, conflictos=None):
    """
    Versión para Streamlit: crea y devuelve el objeto folium.Map.
    'conflictos' es un conjunto de índices de aeronaves en posible colisión.
    """
    if not aeronaves:
        return None

    if conflictos is None:
        conflictos = set()

    lat_centro = sum(a["lat"] for a in aeronaves) / len(aeronaves)
    lon_centro = sum(a["lon"] for a in aeronaves) / len(aeronaves)

    mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=8)

    folium.TileLayer(
        "cartodbpositron",
        name="CartoDB Positron",
        attr="Map tiles © CartoDB, data © OpenStreetMap contributors",
        show=True
    ).add_to(mapa)

    folium.TileLayer(
        "cartodbdark_matter",
        name="CartoDB Dark Matter",
        attr="Map tiles © CartoDB, data © OpenStreetMap contributors",
        show=False
    ).add_to(mapa)

    folium.LayerControl().add_to(mapa)

    # Cargar y codificar el icono una sola vez
    with open("avion.png", "rb") as f:
        icon_b64 = base64.b64encode(f.read()).decode("utf-8")

    for idx, a in enumerate(aeronaves):
        if a["heading"] is not None:
            rumbo_txt = f"{a['heading']:.0f}°"
            heading = a["heading"]
        else:
            rumbo_txt = "N/A"
            heading = 0.0

        en_conflicto = idx in conflictos

        popup = (
            ("<b>POSIBLE CONFLICTO</b><br>" if en_conflicto else "")
            + f"{a['callsign']}<br>"
            f"Vel: {a['vel']} kt<br>"
            f"Alt: {a['alt']} ft<br>"
            f"Rumbo: {rumbo_txt}"
        )

        angle_corr = heading + 65  # tu ajuste fino

        # Si está en conflicto, dibujamos un aro rojo alrededor del avión
        borde = "2px solid red" if en_conflicto else "none"
        sombra = "0 0 8px red" if en_conflicto else "none"

        icon_html = f"""
        <div style="transform: rotate({angle_corr}deg);
                    transform-origin: 50% 50%;
                    width:32px; height:32px;
                    border:{borde};
                    border-radius:50%;
                    box-shadow:{sombra};">
            <img src="data:image/png;base64,{icon_b64}"
                 style="width:32px; height:32px;">
        </div>
        """

        icono_rotado = DivIcon(
            html=icon_html,
            icon_size=(32, 32),
            icon_anchor=(16, 16)
        )

        folium.Marker(
            location=[a["lat"], a["lon"]],
            popup=popup,
            icon=icono_rotado
        ).add_to(mapa)

    return mapa

    
