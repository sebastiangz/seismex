#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX - Módulo de Visualización
================================================================================
Herramientas para visualizar resultados de Energy Space Density (ESD).

Componentes:
    - VisualizadorESD: Visualización de secciones y paneles
    - PaletaColoresESD: Paletas de colores personalizadas
    - PaletaColoresSismicidad: Paletas para sismicidad
    - MapaInteractivo: Mapas web con Folium
    - ExportadorGIS: Exportación a formatos GIS
    - IntegradorGEE: Integración con Google Earth Engine

Autor: SEISMEX Project
Versión: 1.0.0
================================================================================
"""

# Importaciones principales
from .colormaps import (
    PaletaColoresESD,
    PaletaColoresSismicidad,
    crear_leyenda_profundidad,
    crear_leyenda_magnitud,
)

from .plotter import (
    VisualizadorESD,
    ConfigVisualizacion,
    ESTILOS_MATPLOTLIB,
)

from .interactive import (
    MapaInteractivo,
    crear_mapa_rapido,
    crear_mapa_esd_completo,
    TILES_DISPONIBLES,
)

from .gis_export import (
    ExportadorGIS,
)

from .gee_integration import (
    IntegradorGEE,
    crear_mapa_esd_completo as crear_mapa_gee,
)

# Versión del módulo
__version__ = '1.0.0'

# Exportaciones públicas
__all__ = [
    # Colormaps
    'PaletaColoresESD',
    'PaletaColoresSismicidad',
    'crear_leyenda_profundidad',
    'crear_leyenda_magnitud',
    
    # Plotter
    'VisualizadorESD',
    'ConfigVisualizacion',
    'ESTILOS_MATPLOTLIB',
    
    # Interactivo
    'MapaInteractivo',
    'crear_mapa_rapido',
    'crear_mapa_esd_completo',
    'TILES_DISPONIBLES',
    
    # GIS Export
    'ExportadorGIS',
    
    # GEE Integration
    'IntegradorGEE',
    'crear_mapa_gee',
]


def verificar_dependencias():
    """
    Verifica que las dependencias opcionales estén disponibles.
    
    Returns:
        Dict con estado de cada dependencia
    """
    estado = {}
    
    # Dependencias core
    try:
        import matplotlib
        estado['matplotlib'] = matplotlib.__version__
    except ImportError:
        estado['matplotlib'] = None
    
    try:
        import numpy
        estado['numpy'] = numpy.__version__
    except ImportError:
        estado['numpy'] = None
    
    # Mapas interactivos
    try:
        import folium
        estado['folium'] = folium.__version__
    except ImportError:
        estado['folium'] = None
    
    try:
        import branca
        estado['branca'] = branca.__version__
    except ImportError:
        estado['branca'] = None
    
    # GIS
    try:
        import rasterio
        estado['rasterio'] = rasterio.__version__
    except ImportError:
        estado['rasterio'] = None
    
    try:
        import geopandas
        estado['geopandas'] = geopandas.__version__
    except ImportError:
        estado['geopandas'] = None
    
    try:
        import shapely
        estado['shapely'] = shapely.__version__
    except ImportError:
        estado['shapely'] = None
    
    try:
        import fiona
        estado['fiona'] = fiona.__version__
    except ImportError:
        estado['fiona'] = None
    
    # Google Earth Engine
    try:
        import ee
        estado['earthengine-api'] = ee.__version__
    except ImportError:
        estado['earthengine-api'] = None
    
    try:
        import geemap
        estado['geemap'] = geemap.__version__
    except ImportError:
        estado['geemap'] = None
    
    return estado


def mostrar_info():
    """Muestra información del módulo y dependencias."""
    print("=" * 70)
    print("SEISMEX Visualization Module")
    print(f"Versión: {__version__}")
    print("=" * 70)
    
    print("\nComponentes disponibles:")
    print("  • VisualizadorESD    - Visualización de secciones ESD")
    print("  • PaletaColoresESD   - Paletas de colores")
    print("  • MapaInteractivo    - Mapas web con Folium")
    print("  • ExportadorGIS      - Exportación GeoTIFF/GeoJSON/Shapefile")
    print("  • IntegradorGEE      - Google Earth Engine")
    
    print("\nEstado de dependencias:")
    estado = verificar_dependencias()
    
    for dep, version in estado.items():
        if version:
            print(f"  ✓ {dep}: {version}")
        else:
            print(f"  ✗ {dep}: no instalado")
    
    print("\nPara instalar dependencias:")
    print("  pip install matplotlib numpy folium branca")
    print("  pip install rasterio geopandas shapely fiona")
    print("  pip install earthengine-api geemap")
    print("=" * 70)


# Información al importar
import warnings

_estado = verificar_dependencias()

if _estado['matplotlib'] is None:
    warnings.warn("matplotlib no disponible. Instale con: pip install matplotlib")

if _estado['folium'] is None:
    warnings.warn("folium no disponible. MapaInteractivo no funcionará. "
                 "Instale con: pip install folium branca")

if _estado['rasterio'] is None:
    warnings.warn("rasterio no disponible. Exportación GeoTIFF limitada. "
                 "Instale con: pip install rasterio")
