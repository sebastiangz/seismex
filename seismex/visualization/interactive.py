#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX - Módulo de Mapas Interactivos
================================================================================
Herramientas para crear mapas interactivos con Folium/Leaflet:
- Visualización de capas ESD
- Epicentros con información popup
- Capas de fallas y volcanes
- Control de capas y leyendas
- Animaciones temporales
- Exportación HTML

Autor: SEISMEX Project
Versión: 1.0.0
================================================================================
"""

import numpy as np
from typing import Optional, List, Dict, Tuple, Union, Any
from pathlib import Path
import json
import warnings
from datetime import datetime, timedelta

# Importaciones de Folium (con manejo de errores)
try:
    import folium
    from folium import plugins
    from folium.plugins import HeatMap, TimestampedGeoJson, MarkerCluster
    from branca.colormap import LinearColormap
    from branca.element import MacroElement, Template
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    warnings.warn("Folium no disponible. Instale con: pip install folium branca")

# Importaciones internas
try:
    from .colormaps import PaletaColoresESD, PaletaColoresSismicidad
except ImportError:
    from colormaps import PaletaColoresESD, PaletaColoresSismicidad


# =============================================================================
# CONFIGURACIÓN DE TILES
# =============================================================================

TILES_DISPONIBLES = {
    'OpenStreetMap': {
        'tiles': 'OpenStreetMap',
        'attr': '© OpenStreetMap contributors'
    },
    'CartoDB positron': {
        'tiles': 'CartoDB positron',
        'attr': '© CartoDB'
    },
    'CartoDB dark_matter': {
        'tiles': 'CartoDB dark_matter',
        'attr': '© CartoDB'
    },
    'Stamen Terrain': {
        'tiles': 'Stamen Terrain',
        'attr': 'Map tiles by Stamen Design'
    },
    'Stamen Toner': {
        'tiles': 'Stamen Toner',
        'attr': 'Map tiles by Stamen Design'
    },
    'Esri WorldImagery': {
        'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        'attr': '© Esri'
    },
    'Esri WorldTopoMap': {
        'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        'attr': '© Esri'
    },
}


class MapaInteractivo:
    """
    Generador de mapas interactivos con Folium.
    
    Permite crear mapas web interactivos con capas de:
    - Resultados ESD (heatmaps, contornos)
    - Epicentros sísmicos
    - Fallas activas
    - Volcanes
    - Ciudades y puntos de interés
    
    Attributes:
        mapa: Objeto Folium Map
        centro: Coordenadas del centro (lat, lon)
        zoom: Nivel de zoom inicial
        
    Example:
        >>> mapa = MapaInteractivo(centro=(19.3, -103.5), zoom=8)
        >>> mapa.agregar_capa_esd(resultado_esd, profundidad_km=30)
        >>> mapa.agregar_epicentros(catalogo)
        >>> mapa.guardar('mapa_esd.html')
    """
    
    # Paletas de colores predefinidas
    PALETAS = {
        'esd': ['#4B0082', '#0000CD', '#00BFFF', '#98FB98', '#FFFFE0',
                '#FFB6C1', '#FF69B4', '#DC143C', '#8B0000'],
        'temperatura': ['#FFFFCC', '#FFEDA0', '#FED976', '#FD8D3C', '#E31A1C'],
        'profundidad': ['#FF0000', '#FF8C00', '#FFD700', '#32CD32', '#1E90FF', '#0000CD'],
        'magnitud': ['#FFFFB2', '#FECC5C', '#FD8D3C', '#F03B20', '#BD0026'],
        'divergente': ['#2166AC', '#92C5DE', '#F7F7F7', '#F4A582', '#B2182B'],
    }
    
    def __init__(self,
                 centro: Tuple[float, float] = (19.0, -103.5),
                 zoom: int = 8,
                 tiles: str = 'CartoDB positron',
                 ancho: str = '100%',
                 alto: str = '600px'):
        """
        Inicializa el mapa interactivo.
        
        Args:
            centro: Tupla (latitud, longitud) del centro del mapa
            zoom: Nivel de zoom inicial (1-18)
            tiles: Tipo de mapa base
            ancho: Ancho del mapa (CSS)
            alto: Alto del mapa (CSS)
        """
        if not FOLIUM_AVAILABLE:
            raise ImportError("Folium no está disponible. Instale con: pip install folium branca")
        
        self.centro = centro
        self.zoom = zoom
        self.ancho = ancho
        self.alto = alto
        
        # Crear mapa base
        if tiles in TILES_DISPONIBLES:
            tile_config = TILES_DISPONIBLES[tiles]
            self.mapa = folium.Map(
                location=list(centro),
                zoom_start=zoom,
                tiles=tile_config['tiles'],
                attr=tile_config['attr'],
                width=ancho,
                height=alto
            )
        else:
            self.mapa = folium.Map(
                location=list(centro),
                zoom_start=zoom,
                tiles=tiles,
                width=ancho,
                height=alto
            )
        
        # Grupos de capas
        self._capas = {}
        self._colormaps = {}
        
        # Paleta de colores
        self._paleta = PaletaColoresESD()
        self._paleta_sismicidad = PaletaColoresSismicidad()
    
    def agregar_tile_layer(self, nombre: str, tiles: str = 'OpenStreetMap'):
        """
        Agrega una capa de tiles adicional.
        
        Args:
            nombre: Nombre de la capa
            tiles: Tipo de tiles
        """
        if tiles in TILES_DISPONIBLES:
            config = TILES_DISPONIBLES[tiles]
            folium.TileLayer(
                tiles=config['tiles'],
                attr=config['attr'],
                name=nombre
            ).add_to(self.mapa)
        else:
            folium.TileLayer(tiles=tiles, name=nombre).add_to(self.mapa)
    
    # =========================================================================
    # CAPA ESD
    # =========================================================================
    
    def agregar_capa_esd(self,
                         resultado_esd: Any,
                         profundidad_km: float,
                         opacidad: float = 0.7,
                         mostrar_colorbar: bool = True,
                         nombre_capa: str = 'ESD',
                         metodo: str = 'heatmap') -> 'MapaInteractivo':
        """
        Agrega una capa de visualización ESD.
        
        Args:
            resultado_esd: ResultadoESD con los datos
            profundidad_km: Profundidad de la sección
            opacidad: Opacidad de la capa (0-1)
            mostrar_colorbar: Mostrar barra de colores
            nombre_capa: Nombre de la capa en el control
            metodo: 'heatmap' o 'contornos'
            
        Returns:
            self para encadenamiento
        """
        # Obtener sección
        iz = np.argmin(np.abs(resultado_esd.grid_z - profundidad_km))
        
        X, Y = np.meshgrid(resultado_esd.grid_x, resultado_esd.grid_y, indexing='ij')
        Z = resultado_esd.esd_log10[:, :, iz]
        
        if metodo == 'heatmap':
            self._agregar_heatmap_esd(X, Y, Z, opacidad, nombre_capa)
        else:
            self._agregar_contornos_esd(X, Y, Z, opacidad, nombre_capa)
        
        if mostrar_colorbar:
            self._agregar_colorbar_esd(nombre_capa)
        
        return self
    
    def _agregar_heatmap_esd(self, X, Y, Z, opacidad, nombre):
        """Agrega un heatmap de ESD."""
        # Preparar datos para heatmap
        datos_heat = []
        
        # Submuestrear si hay muchos puntos
        step = max(1, X.shape[0] // 50)
        
        for i in range(0, X.shape[0], step):
            for j in range(0, X.shape[1], step):
                lon = X[i, j]
                lat = Y[i, j]
                valor = Z[i, j]
                
                if np.isfinite(valor) and valor > -12:
                    # Normalizar valor para el heatmap
                    peso = (valor + 12) / 12.5  # Normalizar a 0-1
                    datos_heat.append([lat, lon, max(0, peso)])
        
        # Crear grupo de capa
        grupo = folium.FeatureGroup(name=nombre)
        
        # Agregar heatmap
        HeatMap(
            datos_heat,
            radius=15,
            blur=10,
            max_zoom=13,
            gradient={0.2: '#0000CD', 0.4: '#00BFFF', 0.6: '#98FB98',
                     0.8: '#FFB6C1', 1.0: '#8B0000'}
        ).add_to(grupo)
        
        grupo.add_to(self.mapa)
        self._capas[nombre] = grupo
    
    def _agregar_contornos_esd(self, X, Y, Z, opacidad, nombre):
        """Agrega contornos de ESD como GeoJSON."""
        import matplotlib.pyplot as plt
        from shapely.geometry import LineString, mapping
        
        # Generar contornos
        niveles = self._paleta.niveles_estandar
        fig, ax = plt.subplots()
        cs = ax.contour(X, Y, Z, levels=niveles)
        plt.close(fig)
        
        # Crear grupo de capa
        grupo = folium.FeatureGroup(name=nombre)
        
        # Convertir contornos a GeoJSON
        colores = self._paleta.colores_hex
        
        for i, nivel in enumerate(cs.levels):
            color = colores[min(i, len(colores) - 1)]
            
            if i < len(cs.collections):
                for path in cs.collections[i].get_paths():
                    if len(path.vertices) > 1:
                        coords = [(float(x), float(y)) for x, y in path.vertices]
                        
                        # Crear línea
                        folium.PolyLine(
                            locations=[(lat, lon) for lon, lat in coords],
                            color=color,
                            weight=2,
                            opacity=opacidad,
                            popup=f'ESD = {nivel:.1f}'
                        ).add_to(grupo)
        
        grupo.add_to(self.mapa)
        self._capas[nombre] = grupo
    
    def _agregar_colorbar_esd(self, nombre):
        """Agrega una barra de colores para ESD."""
        colormap = LinearColormap(
            colors=self.PALETAS['esd'],
            vmin=-12, vmax=0.5,
            caption=f'{nombre}: log₁₀(ESD normalizado)'
        )
        colormap.add_to(self.mapa)
        self._colormaps[nombre] = colormap
    
    # =========================================================================
    # EPICENTROS
    # =========================================================================
    
    def agregar_epicentros(self,
                           catalogo: Any,
                           color_por: str = 'magnitud',
                           tamanio_por: str = 'magnitud',
                           popup: bool = True,
                           clustering: bool = False,
                           nombre_capa: str = 'Epicentros') -> 'MapaInteractivo':
        """
        Agrega epicentros al mapa.
        
        Args:
            catalogo: CatalogoSismico con los datos
            color_por: Variable para color ('magnitud', 'profundidad', 'fecha')
            tamanio_por: Variable para tamaño ('magnitud', 'fijo')
            popup: Mostrar información al hacer clic
            clustering: Agrupar marcadores cercanos
            nombre_capa: Nombre de la capa
            
        Returns:
            self para encadenamiento
        """
        datos = catalogo.datos
        
        # Crear grupo de capa
        if clustering:
            grupo = MarkerCluster(name=nombre_capa)
        else:
            grupo = folium.FeatureGroup(name=nombre_capa)
        
        for _, row in datos.iterrows():
            lat = row['latitud']
            lon = row['longitud']
            mag = row.get('magnitud', 3.0)
            prof = row.get('profundidad_km', 10)
            fecha = row.get('fecha', '')
            
            # Color según variable
            if color_por == 'magnitud':
                color = self._paleta_sismicidad.color_por_magnitud(mag)
            elif color_por == 'profundidad':
                color = self._paleta_sismicidad.color_por_profundidad(prof)
            else:
                color = '#FF0000'
            
            # Tamaño según variable
            if tamanio_por == 'magnitud':
                radio = max(3, mag * 2)
            else:
                radio = 5
            
            # Popup
            popup_html = None
            if popup:
                popup_html = f"""
                <div style="font-family: Arial; font-size: 12px;">
                    <b>Magnitud:</b> {mag:.1f}<br>
                    <b>Profundidad:</b> {prof:.1f} km<br>
                    <b>Fecha:</b> {fecha}<br>
                    <b>Lat:</b> {lat:.4f}°<br>
                    <b>Lon:</b> {lon:.4f}°
                </div>
                """
            
            # Crear marcador
            folium.CircleMarker(
                location=[lat, lon],
                radius=radio,
                color='black',
                weight=1,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=200) if popup else None
            ).add_to(grupo)
        
        grupo.add_to(self.mapa)
        self._capas[nombre_capa] = grupo
        
        # Agregar leyenda
        if color_por == 'magnitud':
            self._agregar_leyenda_magnitud()
        elif color_por == 'profundidad':
            self._agregar_leyenda_profundidad()
        
        return self
    
    def _agregar_leyenda_magnitud(self):
        """Agrega leyenda de magnitudes."""
        colormap = LinearColormap(
            colors=self.PALETAS['magnitud'],
            vmin=2, vmax=7,
            caption='Magnitud'
        )
        colormap.add_to(self.mapa)
    
    def _agregar_leyenda_profundidad(self):
        """Agrega leyenda de profundidad."""
        colormap = LinearColormap(
            colors=self.PALETAS['profundidad'],
            vmin=0, vmax=200,
            caption='Profundidad (km)'
        )
        colormap.add_to(self.mapa)
    
    # =========================================================================
    # CAPAS GEOLÓGICAS
    # =========================================================================
    
    def agregar_fallas(self,
                       archivo_geojson: str,
                       color: str = '#FF0000',
                       peso: int = 2,
                       nombre_capa: str = 'Fallas') -> 'MapaInteractivo':
        """
        Agrega capa de fallas desde GeoJSON.
        
        Args:
            archivo_geojson: Ruta al archivo GeoJSON
            color: Color de las líneas
            peso: Grosor de las líneas
            nombre_capa: Nombre de la capa
            
        Returns:
            self para encadenamiento
        """
        with open(archivo_geojson, 'r') as f:
            geojson_data = json.load(f)
        
        grupo = folium.FeatureGroup(name=nombre_capa)
        
        folium.GeoJson(
            geojson_data,
            style_function=lambda x: {
                'color': color,
                'weight': peso,
                'opacity': 0.8
            },
            tooltip=folium.GeoJsonTooltip(fields=['nombre', 'tipo'] if 'nombre' in str(geojson_data) else [])
        ).add_to(grupo)
        
        grupo.add_to(self.mapa)
        self._capas[nombre_capa] = grupo
        
        return self
    
    def agregar_volcanes(self,
                         archivo_geojson: Optional[str] = None,
                         volcanes: Optional[List[Dict]] = None,
                         nombre_capa: str = 'Volcanes') -> 'MapaInteractivo':
        """
        Agrega capa de volcanes.
        
        Args:
            archivo_geojson: Ruta al archivo GeoJSON (opcional)
            volcanes: Lista de dicts con 'nombre', 'lat', 'lon' (opcional)
            nombre_capa: Nombre de la capa
            
        Returns:
            self para encadenamiento
        """
        grupo = folium.FeatureGroup(name=nombre_capa)
        
        if archivo_geojson:
            with open(archivo_geojson, 'r') as f:
                geojson_data = json.load(f)
            
            for feature in geojson_data.get('features', []):
                coords = feature['geometry']['coordinates']
                props = feature.get('properties', {})
                
                folium.Marker(
                    location=[coords[1], coords[0]],
                    icon=folium.Icon(color='red', icon='fire', prefix='fa'),
                    popup=props.get('nombre', 'Volcán')
                ).add_to(grupo)
        
        if volcanes:
            for volcan in volcanes:
                folium.Marker(
                    location=[volcan['lat'], volcan['lon']],
                    icon=folium.Icon(color='red', icon='fire', prefix='fa'),
                    popup=volcan.get('nombre', 'Volcán')
                ).add_to(grupo)
        
        grupo.add_to(self.mapa)
        self._capas[nombre_capa] = grupo
        
        return self
    
    def agregar_ciudades(self,
                         ciudades: List[Union[str, Dict]],
                         nombre_capa: str = 'Ciudades') -> 'MapaInteractivo':
        """
        Agrega marcadores de ciudades.
        
        Args:
            ciudades: Lista de nombres o dicts con 'nombre', 'lat', 'lon'
            nombre_capa: Nombre de la capa
            
        Returns:
            self para encadenamiento
        """
        # Coordenadas de ciudades principales de México
        CIUDADES_MEXICO = {
            'Colima': (19.2433, -103.7250),
            'Manzanillo': (19.0522, -104.3158),
            'Guadalajara': (20.6597, -103.3496),
            'Ciudad de México': (19.4326, -99.1332),
            'Morelia': (19.7060, -101.1950),
            'Tepic': (21.5085, -104.8946),
            'Puerto Vallarta': (20.6534, -105.2253),
            'Uruapan': (19.4167, -102.0500),
            'Tecomán': (18.9167, -103.8667),
        }
        
        grupo = folium.FeatureGroup(name=nombre_capa)
        
        for ciudad in ciudades:
            if isinstance(ciudad, str):
                if ciudad in CIUDADES_MEXICO:
                    lat, lon = CIUDADES_MEXICO[ciudad]
                    nombre = ciudad
                else:
                    continue
            else:
                lat = ciudad['lat']
                lon = ciudad['lon']
                nombre = ciudad.get('nombre', 'Ciudad')
            
            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color='blue', icon='building', prefix='fa'),
                popup=nombre,
                tooltip=nombre
            ).add_to(grupo)
        
        grupo.add_to(self.mapa)
        self._capas[nombre_capa] = grupo
        
        return self
    
    # =========================================================================
    # ANIMACIÓN TEMPORAL
    # =========================================================================
    
    def crear_animacion_temporal(self,
                                  catalogo: Any,
                                  ventana_dias: int = 365,
                                  paso_dias: int = 30,
                                  nombre_capa: str = 'Animación') -> 'MapaInteractivo':
        """
        Crea una animación temporal de sismicidad.
        
        Args:
            catalogo: CatalogoSismico con fechas
            ventana_dias: Tamaño de la ventana temporal
            paso_dias: Paso entre frames
            nombre_capa: Nombre de la capa
            
        Returns:
            self para encadenamiento
        """
        datos = catalogo.datos.copy()
        
        # Asegurar que fecha es datetime
        if not np.issubdtype(datos['fecha'].dtype, np.datetime64):
            datos['fecha'] = pd.to_datetime(datos['fecha'])
        
        # Crear features para TimestampedGeoJson
        features = []
        
        for _, row in datos.iterrows():
            fecha_str = row['fecha'].strftime('%Y-%m-%d')
            
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [row['longitud'], row['latitud']]
                },
                'properties': {
                    'time': fecha_str,
                    'style': {
                        'color': self._paleta_sismicidad.color_por_magnitud(row.get('magnitud', 3)),
                        'fillColor': self._paleta_sismicidad.color_por_magnitud(row.get('magnitud', 3)),
                        'fillOpacity': 0.7,
                        'weight': 1
                    },
                    'icon': 'circle',
                    'iconstyle': {
                        'fillColor': self._paleta_sismicidad.color_por_magnitud(row.get('magnitud', 3)),
                        'fillOpacity': 0.7,
                        'stroke': True,
                        'radius': max(3, row.get('magnitud', 3) * 2)
                    },
                    'popup': f"M{row.get('magnitud', '?'):.1f} - {row.get('profundidad_km', '?'):.1f} km"
                }
            }
            features.append(feature)
        
        geojson_data = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        TimestampedGeoJson(
            geojson_data,
            period='P1D',  # Un día
            add_last_point=True,
            auto_play=True,
            loop=True,
            max_speed=10,
            loop_button=True,
            date_options='YYYY-MM-DD',
            time_slider_drag_update=True
        ).add_to(self.mapa)
        
        return self
    
    # =========================================================================
    # CONTROLES Y EXPORTACIÓN
    # =========================================================================
    
    def agregar_control_capas(self, colapsado: bool = True) -> 'MapaInteractivo':
        """
        Agrega control de capas al mapa.
        
        Args:
            colapsado: Si el control aparece colapsado inicialmente
            
        Returns:
            self para encadenamiento
        """
        folium.LayerControl(collapsed=colapsado).add_to(self.mapa)
        return self
    
    def agregar_escala(self) -> 'MapaInteractivo':
        """Agrega barra de escala al mapa."""
        plugins.MiniMap().add_to(self.mapa)
        return self
    
    def agregar_fullscreen(self) -> 'MapaInteractivo':
        """Agrega botón de pantalla completa."""
        plugins.Fullscreen().add_to(self.mapa)
        return self
    
    def agregar_coordenadas_mouse(self) -> 'MapaInteractivo':
        """Muestra coordenadas del cursor."""
        plugins.MousePosition().add_to(self.mapa)
        return self
    
    def agregar_dibujo(self) -> 'MapaInteractivo':
        """Agrega herramientas de dibujo."""
        plugins.Draw().add_to(self.mapa)
        return self
    
    def centrar_en_datos(self, catalogo: Any) -> 'MapaInteractivo':
        """
        Centra el mapa en la extensión de los datos.
        
        Args:
            catalogo: CatalogoSismico
            
        Returns:
            self para encadenamiento
        """
        datos = catalogo.datos
        
        sw = [datos['latitud'].min(), datos['longitud'].min()]
        ne = [datos['latitud'].max(), datos['longitud'].max()]
        
        self.mapa.fit_bounds([sw, ne])
        
        return self
    
    def guardar(self, ruta: str) -> str:
        """
        Guarda el mapa como archivo HTML.
        
        Args:
            ruta: Ruta del archivo de salida
            
        Returns:
            Ruta del archivo guardado
        """
        self.mapa.save(ruta)
        print(f"Mapa guardado: {ruta}")
        return ruta
    
    def mostrar(self) -> folium.Map:
        """
        Retorna el mapa para visualización en Jupyter.
        
        Returns:
            Objeto Folium Map
        """
        return self.mapa
    
    def _repr_html_(self) -> str:
        """Representación HTML para Jupyter."""
        return self.mapa._repr_html_()


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def crear_mapa_rapido(catalogo: Any,
                      centro: Optional[Tuple[float, float]] = None,
                      zoom: int = 8) -> MapaInteractivo:
    """
    Crea un mapa rápido con epicentros.
    
    Args:
        catalogo: CatalogoSismico
        centro: Centro del mapa (auto si None)
        zoom: Nivel de zoom
        
    Returns:
        MapaInteractivo configurado
    """
    if centro is None:
        datos = catalogo.datos
        centro = (datos['latitud'].mean(), datos['longitud'].mean())
    
    mapa = MapaInteractivo(centro=centro, zoom=zoom)
    mapa.agregar_epicentros(catalogo, popup=True)
    mapa.agregar_control_capas()
    mapa.agregar_fullscreen()
    mapa.agregar_coordenadas_mouse()
    
    return mapa


def crear_mapa_esd_completo(resultado_esd: Any,
                            catalogo: Any,
                            profundidad_km: float = 30,
                            guardar: Optional[str] = None) -> MapaInteractivo:
    """
    Crea un mapa completo con ESD y epicentros.
    
    Args:
        resultado_esd: ResultadoESD
        catalogo: CatalogoSismico
        profundidad_km: Profundidad de la sección ESD
        guardar: Ruta para guardar
        
    Returns:
        MapaInteractivo configurado
    """
    # Calcular centro
    centro = (
        (resultado_esd.grid_y.min() + resultado_esd.grid_y.max()) / 2,
        (resultado_esd.grid_x.min() + resultado_esd.grid_x.max()) / 2
    )
    
    mapa = MapaInteractivo(centro=centro, zoom=9)
    
    # Agregar capas
    mapa.agregar_capa_esd(resultado_esd, profundidad_km)
    mapa.agregar_epicentros(catalogo, color_por='profundidad')
    
    # Controles
    mapa.agregar_control_capas()
    mapa.agregar_escala()
    mapa.agregar_fullscreen()
    mapa.agregar_coordenadas_mouse()
    
    if guardar:
        mapa.guardar(guardar)
    
    return mapa


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

def ejemplo_mapa_interactivo():
    """Ejemplo de uso del módulo de mapas interactivos."""
    import pandas as pd
    
    print("=" * 70)
    print("SEISMEX - Ejemplo de Mapa Interactivo")
    print("=" * 70)
    
    if not FOLIUM_AVAILABLE:
        print("ERROR: Folium no está disponible")
        print("Instale con: pip install folium branca")
        return None
    
    # Crear datos simulados
    np.random.seed(42)
    n_eventos = 100
    
    datos_cat = pd.DataFrame({
        'fecha': pd.date_range('2020-01-01', periods=n_eventos, freq='3D'),
        'latitud': np.random.normal(19.0, 0.5, n_eventos),
        'longitud': np.random.normal(-104.0, 0.5, n_eventos),
        'profundidad_km': np.abs(np.random.exponential(30, n_eventos)),
        'magnitud': np.random.exponential(0.8, n_eventos) + 2.0
    })
    
    class CatalogoSimulado:
        def __init__(self, datos):
            self.datos = datos
    
    catalogo = CatalogoSimulado(datos_cat)
    
    # Crear mapa
    mapa = MapaInteractivo(centro=(19.0, -104.0), zoom=8)
    
    # Agregar epicentros
    mapa.agregar_epicentros(catalogo, color_por='magnitud', popup=True)
    
    # Agregar ciudades
    mapa.agregar_ciudades(['Colima', 'Manzanillo', 'Guadalajara'])
    
    # Agregar volcanes ejemplo
    volcanes = [
        {'nombre': 'Volcán de Colima', 'lat': 19.514, 'lon': -103.617},
        {'nombre': 'Nevado de Colima', 'lat': 19.564, 'lon': -103.606},
    ]
    mapa.agregar_volcanes(volcanes=volcanes)
    
    # Controles
    mapa.agregar_control_capas()
    mapa.agregar_fullscreen()
    mapa.agregar_coordenadas_mouse()
    
    print("\n✓ Mapa creado exitosamente")
    print("  Use mapa.guardar('archivo.html') para exportar")
    
    return mapa


if __name__ == "__main__":
    mapa = ejemplo_mapa_interactivo()
    if mapa:
        mapa.guardar('/tmp/mapa_ejemplo.html')
        print("  Mapa guardado en: /tmp/mapa_ejemplo.html")
