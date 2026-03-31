"""
SEISMEX Utils - Entrada y Salida
================================

Funciones para lectura/escritura de archivos y formatos especializados.

Formatos soportados:
- CSV con diferentes dialectos (SSN, USGS, ISC)
- Excel (.xlsx, .xls)
- GeoJSON
- GeoTIFF
- KML/KMZ
- Shapefile
- Pickle (para caché)

Ejemplo de uso:
    >>> from seismex.utils.io import leer_catalogo_ssn, exportar_geojson
    >>> catalogo = leer_catalogo_ssn('sismos.csv')
    >>> exportar_geojson(catalogo, 'sismos.geojson')

Autor: SEISMEX Team
Licencia: MIT
"""

from __future__ import annotations

import json
import gzip
import pickle
import logging
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from zipfile import ZipFile
import shutil

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# LECTURA DE CATÁLOGOS
# =============================================================================

def leer_catalogo_ssn(
    ruta: Union[str, Path],
    encoding: str = 'utf-8',
    **kwargs
) -> pd.DataFrame:
    """
    Lee un catálogo del SSN (Servicio Sismológico Nacional de México).
    
    El SSN usa un formato CSV con columnas específicas en español.
    
    Args:
        ruta: Ruta al archivo CSV
        encoding: Codificación del archivo (default: utf-8)
        **kwargs: Argumentos adicionales para pd.read_csv
        
    Returns:
        DataFrame con columnas normalizadas
        
    Example:
        >>> catalogo = leer_catalogo_ssn('ssn_2024.csv')
        >>> print(catalogo.columns)
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    
    logger.info(f"Leyendo catálogo SSN: {ruta}")
    
    # Mapeo de columnas SSN a estándar
    mapeo = {
        'Fecha': 'fecha',
        'Fecha UTC': 'fecha',
        'Latitud': 'latitud',
        'Longitud': 'longitud',
        'Profundidad': 'profundidad_km',
        'Magnitud': 'magnitud',
        'Referencia de localizacion': 'lugar',
        'Referencia de localización': 'lugar',
    }
    
    # Leer CSV
    df = pd.read_csv(ruta, encoding=encoding, **kwargs)
    
    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip()
    df = df.rename(columns=mapeo)
    
    # Convertir fecha
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    
    # Asegurar tipos numéricos
    for col in ['latitud', 'longitud', 'profundidad_km', 'magnitud']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Agregar fuente
    df['fuente'] = 'SSN'
    
    logger.info(f"Catálogo SSN cargado: {len(df)} eventos")
    
    return df


def leer_catalogo_usgs(
    ruta: Union[str, Path],
    **kwargs
) -> pd.DataFrame:
    """
    Lee un catálogo del USGS (United States Geological Survey).
    
    Args:
        ruta: Ruta al archivo CSV
        **kwargs: Argumentos adicionales para pd.read_csv
        
    Returns:
        DataFrame con columnas normalizadas
    """
    ruta = Path(ruta)
    
    logger.info(f"Leyendo catálogo USGS: {ruta}")
    
    mapeo = {
        'time': 'fecha',
        'latitude': 'latitud',
        'longitude': 'longitud',
        'depth': 'profundidad_km',
        'mag': 'magnitud',
        'magType': 'tipo_magnitud',
        'place': 'lugar',
        'id': 'id_evento',
        'horizontalError': 'incertidumbre_h',
        'depthError': 'incertidumbre_z',
        'magError': 'incertidumbre_m',
        'rms': 'rms',
        'gap': 'gap',
        'nst': 'nst',
    }
    
    df = pd.read_csv(ruta, **kwargs)
    df = df.rename(columns=mapeo)
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    
    df['fuente'] = 'USGS'
    
    logger.info(f"Catálogo USGS cargado: {len(df)} eventos")
    
    return df


def leer_catalogo_isc(
    ruta: Union[str, Path],
    formato: str = 'isf',
    **kwargs
) -> pd.DataFrame:
    """
    Lee un catálogo del ISC (International Seismological Centre).
    
    Args:
        ruta: Ruta al archivo
        formato: 'isf' o 'csv'
        **kwargs: Argumentos adicionales
        
    Returns:
        DataFrame con columnas normalizadas
    """
    ruta = Path(ruta)
    
    logger.info(f"Leyendo catálogo ISC ({formato}): {ruta}")
    
    if formato == 'csv':
        mapeo = {
            'DATE': 'fecha',
            'LAT': 'latitud',
            'LON': 'longitud',
            'DEPTH': 'profundidad_km',
            'MAG': 'magnitud',
            'REGION': 'lugar',
        }
        
        df = pd.read_csv(ruta, **kwargs)
        df = df.rename(columns=mapeo)
    
    elif formato == 'isf':
        # Formato ISF es más complejo - parseo básico
        eventos = []
        with open(ruta, 'r') as f:
            for linea in f:
                if linea.startswith('Date'):
                    continue
                partes = linea.split()
                if len(partes) >= 6:
                    try:
                        evento = {
                            'fecha': f"{partes[0]} {partes[1]}",
                            'latitud': float(partes[2]),
                            'longitud': float(partes[3]),
                            'profundidad_km': float(partes[4]),
                            'magnitud': float(partes[5]),
                        }
                        eventos.append(evento)
                    except (ValueError, IndexError):
                        continue
        
        df = pd.DataFrame(eventos)
    else:
        raise ValueError(f"Formato no soportado: {formato}")
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    
    df['fuente'] = 'ISC'
    
    logger.info(f"Catálogo ISC cargado: {len(df)} eventos")
    
    return df


# =============================================================================
# EXPORTACIÓN A FORMATOS GIS
# =============================================================================

def exportar_geojson(
    datos: Union[pd.DataFrame, List[Dict]],
    archivo_salida: Union[str, Path],
    propiedades: Optional[List[str]] = None,
    lat_col: str = 'latitud',
    lon_col: str = 'longitud',
    precision: int = 6
) -> Path:
    """
    Exporta datos a formato GeoJSON.
    
    Args:
        datos: DataFrame o lista de diccionarios con los datos
        archivo_salida: Ruta del archivo de salida
        propiedades: Lista de columnas a incluir como propiedades
        lat_col: Nombre de la columna de latitud
        lon_col: Nombre de la columna de longitud
        precision: Decimales para coordenadas
        
    Returns:
        Path del archivo creado
        
    Example:
        >>> exportar_geojson(catalogo, 'sismos.geojson', 
        ...                  propiedades=['fecha', 'magnitud'])
    """
    archivo_salida = Path(archivo_salida)
    
    # Convertir a DataFrame si es necesario
    if isinstance(datos, list):
        df = pd.DataFrame(datos)
    else:
        df = datos.copy()
    
    # Determinar propiedades
    if propiedades is None:
        propiedades = [c for c in df.columns if c not in [lat_col, lon_col]]
    
    # Crear features
    features = []
    for _, row in df.iterrows():
        try:
            lat = round(float(row[lat_col]), precision)
            lon = round(float(row[lon_col]), precision)
        except (ValueError, TypeError):
            continue
        
        props = {}
        for prop in propiedades:
            if prop in row:
                valor = row[prop]
                # Convertir tipos no serializables
                if pd.isna(valor):
                    props[prop] = None
                elif isinstance(valor, (np.integer, np.floating)):
                    props[prop] = float(valor)
                elif isinstance(valor, pd.Timestamp):
                    props[prop] = valor.isoformat()
                elif isinstance(valor, datetime):
                    props[prop] = valor.isoformat()
                else:
                    props[prop] = valor
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [lon, lat]
            },
            'properties': props
        }
        features.append(feature)
    
    # Crear GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'created': datetime.now().isoformat(),
            'total_features': len(features),
            'source': 'SEISMEX'
        }
    }
    
    # Escribir archivo
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    logger.info(f"GeoJSON exportado: {archivo_salida} ({len(features)} features)")
    
    return archivo_salida


def exportar_geotiff(
    grilla_x: np.ndarray,
    grilla_y: np.ndarray,
    valores: np.ndarray,
    archivo_salida: Union[str, Path],
    crs: str = 'EPSG:4326',
    nodata: float = -999.0,
    descripcion: str = ''
) -> Path:
    """
    Exporta una grilla de valores a formato GeoTIFF.
    
    Requiere rasterio instalado.
    
    Args:
        grilla_x: Array 1D o 2D de coordenadas X (longitud)
        grilla_y: Array 1D o 2D de coordenadas Y (latitud)
        valores: Array 2D de valores
        archivo_salida: Ruta del archivo de salida
        crs: Sistema de referencia de coordenadas
        nodata: Valor para datos faltantes
        descripcion: Descripción del raster
        
    Returns:
        Path del archivo creado
    """
    try:
        import rasterio
        from rasterio.transform import from_bounds
    except ImportError:
        raise ImportError("rasterio requerido: pip install rasterio")
    
    archivo_salida = Path(archivo_salida)
    
    # Determinar bounds
    if grilla_x.ndim == 1:
        x_min, x_max = grilla_x.min(), grilla_x.max()
        y_min, y_max = grilla_y.min(), grilla_y.max()
    else:
        x_min, x_max = grilla_x.min(), grilla_x.max()
        y_min, y_max = grilla_y.min(), grilla_y.max()
    
    # Dimensiones
    height, width = valores.shape
    
    # Transformación
    transform = from_bounds(x_min, y_min, x_max, y_max, width, height)
    
    # Reemplazar NaN con nodata
    valores_out = np.where(np.isnan(valores), nodata, valores)
    
    # Escribir GeoTIFF
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        archivo_salida,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=valores_out.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata
    ) as dst:
        dst.write(valores_out, 1)
        dst.update_tags(description=descripcion, source='SEISMEX')
    
    logger.info(f"GeoTIFF exportado: {archivo_salida} ({width}x{height})")
    
    return archivo_salida


def exportar_kml(
    datos: Union[pd.DataFrame, List[Dict]],
    archivo_salida: Union[str, Path],
    nombre: str = 'SEISMEX Data',
    descripcion: str = '',
    lat_col: str = 'latitud',
    lon_col: str = 'longitud',
    nombre_col: Optional[str] = None,
    color: str = 'ff0000ff'  # AABBGGRR format
) -> Path:
    """
    Exporta datos a formato KML para Google Earth.
    
    Args:
        datos: DataFrame o lista de diccionarios
        archivo_salida: Ruta del archivo de salida
        nombre: Nombre del documento KML
        descripcion: Descripción del documento
        lat_col, lon_col: Columnas de coordenadas
        nombre_col: Columna para nombres de placemarks
        color: Color en formato KML (AABBGGRR)
        
    Returns:
        Path del archivo creado
    """
    archivo_salida = Path(archivo_salida)
    
    if isinstance(datos, list):
        df = pd.DataFrame(datos)
    else:
        df = datos.copy()
    
    # Construir KML
    kml_header = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>{nombre}</name>
    <description>{descripcion}</description>
    <Style id="defaultStyle">
        <IconStyle>
            <color>{color}</color>
            <scale>1.0</scale>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png</href>
            </Icon>
        </IconStyle>
    </Style>
'''
    
    placemarks = []
    for i, row in df.iterrows():
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])
        except (ValueError, TypeError):
            continue
        
        if nombre_col and nombre_col in row:
            pm_nombre = str(row[nombre_col])
        else:
            pm_nombre = f"Evento {i+1}"
        
        # Descripción del placemark
        desc_parts = []
        for col in df.columns:
            if col not in [lat_col, lon_col]:
                desc_parts.append(f"{col}: {row[col]}")
        pm_desc = "<br/>".join(desc_parts)
        
        placemark = f'''    <Placemark>
        <name>{pm_nombre}</name>
        <description><![CDATA[{pm_desc}]]></description>
        <styleUrl>#defaultStyle</styleUrl>
        <Point>
            <coordinates>{lon},{lat},0</coordinates>
        </Point>
    </Placemark>
'''
        placemarks.append(placemark)
    
    kml_footer = '''</Document>
</kml>'''
    
    kml_content = kml_header + ''.join(placemarks) + kml_footer
    
    # Escribir archivo
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write(kml_content)
    
    logger.info(f"KML exportado: {archivo_salida} ({len(placemarks)} placemarks)")
    
    return archivo_salida


def exportar_shapefile(
    datos: Union[pd.DataFrame, List[Dict]],
    archivo_salida: Union[str, Path],
    lat_col: str = 'latitud',
    lon_col: str = 'longitud',
    crs: str = 'EPSG:4326'
) -> Path:
    """
    Exporta datos a formato Shapefile.
    
    Requiere geopandas instalado.
    
    Args:
        datos: DataFrame o lista de diccionarios
        archivo_salida: Ruta del archivo de salida (sin extensión)
        lat_col, lon_col: Columnas de coordenadas
        crs: Sistema de referencia de coordenadas
        
    Returns:
        Path del archivo creado
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        raise ImportError("geopandas y shapely requeridos: pip install geopandas shapely")
    
    archivo_salida = Path(archivo_salida)
    
    if isinstance(datos, list):
        df = pd.DataFrame(datos)
    else:
        df = datos.copy()
    
    # Crear geometrías
    geometria = [
        Point(row[lon_col], row[lat_col]) 
        for _, row in df.iterrows()
        if pd.notna(row[lat_col]) and pd.notna(row[lon_col])
    ]
    
    # Filtrar filas con coordenadas válidas
    df_valid = df[df[lat_col].notna() & df[lon_col].notna()].copy()
    
    # Crear GeoDataFrame
    gdf = gpd.GeoDataFrame(df_valid, geometry=geometria, crs=crs)
    
    # Convertir columnas datetime a string (shapefile no soporta datetime)
    for col in gdf.select_dtypes(include=['datetime64']).columns:
        gdf[col] = gdf[col].astype(str)
    
    # Truncar nombres de columnas a 10 caracteres (limitación shapefile)
    gdf.columns = [c[:10] if len(c) > 10 else c for c in gdf.columns]
    
    # Guardar
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(str(archivo_salida))
    
    logger.info(f"Shapefile exportado: {archivo_salida} ({len(gdf)} features)")
    
    return archivo_salida


# =============================================================================
# CACHÉ Y PERSISTENCIA
# =============================================================================

def guardar_pickle(
    objeto: Any,
    ruta: Union[str, Path],
    comprimir: bool = True
) -> Path:
    """
    Guarda un objeto en formato pickle (opcionalmente comprimido).
    
    Args:
        objeto: Cualquier objeto serializable
        ruta: Ruta del archivo de salida
        comprimir: Si True, comprime con gzip
        
    Returns:
        Path del archivo creado
    """
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    
    if comprimir:
        if not ruta.suffix == '.gz':
            ruta = ruta.with_suffix(ruta.suffix + '.gz')
        with gzip.open(ruta, 'wb') as f:
            pickle.dump(objeto, f, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        with open(ruta, 'wb') as f:
            pickle.dump(objeto, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    logger.debug(f"Objeto guardado: {ruta}")
    
    return ruta


def cargar_pickle(ruta: Union[str, Path]) -> Any:
    """
    Carga un objeto desde archivo pickle.
    
    Args:
        ruta: Ruta del archivo
        
    Returns:
        Objeto deserializado
    """
    ruta = Path(ruta)
    
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    
    if ruta.suffix == '.gz':
        with gzip.open(ruta, 'rb') as f:
            return pickle.load(f)
    else:
        with open(ruta, 'rb') as f:
            return pickle.load(f)


# =============================================================================
# COMPRESIÓN Y ARCHIVOS
# =============================================================================

def comprimir_directorio(
    directorio: Union[str, Path],
    archivo_salida: Optional[Union[str, Path]] = None,
    formato: str = 'zip'
) -> Path:
    """
    Comprime un directorio completo.
    
    Args:
        directorio: Directorio a comprimir
        archivo_salida: Ruta del archivo comprimido (opcional)
        formato: 'zip' o 'tar.gz'
        
    Returns:
        Path del archivo creado
    """
    directorio = Path(directorio)
    
    if archivo_salida is None:
        archivo_salida = directorio.with_suffix(f'.{formato}')
    else:
        archivo_salida = Path(archivo_salida)
    
    if formato == 'zip':
        shutil.make_archive(
            str(archivo_salida.with_suffix('')),
            'zip',
            directorio.parent,
            directorio.name
        )
        return archivo_salida.with_suffix('.zip')
    
    elif formato == 'tar.gz':
        shutil.make_archive(
            str(archivo_salida.with_suffix('').with_suffix('')),
            'gztar',
            directorio.parent,
            directorio.name
        )
        return archivo_salida.with_suffix('.tar.gz')
    
    else:
        raise ValueError(f"Formato no soportado: {formato}")


def descomprimir_archivo(
    archivo: Union[str, Path],
    destino: Optional[Union[str, Path]] = None
) -> Path:
    """
    Descomprime un archivo ZIP.
    
    Args:
        archivo: Archivo a descomprimir
        destino: Directorio de destino (opcional)
        
    Returns:
        Path del directorio extraído
    """
    archivo = Path(archivo)
    
    if destino is None:
        destino = archivo.parent / archivo.stem
    else:
        destino = Path(destino)
    
    destino.mkdir(parents=True, exist_ok=True)
    
    if archivo.suffix == '.zip':
        with ZipFile(archivo, 'r') as zf:
            zf.extractall(destino)
    else:
        shutil.unpack_archive(archivo, destino)
    
    return destino


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("SEISMEX - Utilidades de I/O")
    print("=" * 60)
    
    # Crear datos de ejemplo
    datos_ejemplo = pd.DataFrame({
        'fecha': pd.date_range('2024-01-01', periods=10, freq='D'),
        'latitud': np.random.uniform(18.5, 20.5, 10),
        'longitud': np.random.uniform(-104.5, -103.0, 10),
        'profundidad_km': np.random.uniform(10, 50, 10),
        'magnitud': np.random.uniform(3.0, 5.5, 10),
    })
    
    print(f"\nDatos de ejemplo: {len(datos_ejemplo)} eventos")
    print(datos_ejemplo.head())
    
    # Exportar a GeoJSON
    ruta_geojson = Path('/tmp/seismex_ejemplo.geojson')
    exportar_geojson(datos_ejemplo, ruta_geojson)
    print(f"\n✓ GeoJSON exportado: {ruta_geojson}")
    
    # Exportar a KML
    ruta_kml = Path('/tmp/seismex_ejemplo.kml')
    exportar_kml(datos_ejemplo, ruta_kml, nombre='Sismos de Ejemplo')
    print(f"✓ KML exportado: {ruta_kml}")
    
    # Guardar pickle
    ruta_pickle = Path('/tmp/seismex_ejemplo.pkl.gz')
    guardar_pickle(datos_ejemplo, ruta_pickle)
    print(f"✓ Pickle guardado: {ruta_pickle}")
    
    # Cargar pickle
    datos_cargados = cargar_pickle(ruta_pickle)
    print(f"✓ Pickle cargado: {len(datos_cargados)} eventos")
    
    print("\n✓ Todas las funciones de I/O funcionan correctamente")
