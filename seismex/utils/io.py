"""
SEISMEX Utils - Entrada y Salida
================================

Funciones para lectura/escritura de archivos y formatos especializados.

Incluye:
- Lectura de catálogos sísmicos (SSN, ISC, USGS)
- Exportación a formatos GIS (GeoJSON, GeoTIFF, KML)
- Serialización (pickle, JSON)
- Compresión de archivos
- Utilidades de archivos

Ejemplo de uso:
    >>> from seismex.utils.io import leer_catalogo_ssn, exportar_geojson
    >>> catalogo = leer_catalogo_ssn('sismos.csv')
    >>> exportar_geojson(catalogo, 'sismos.geojson')

Autor: SEISMEX Team
Licencia: MIT
"""

from __future__ import annotations

import json
import pickle
import gzip
import zipfile
import shutil
import logging
import warnings
from pathlib import Path
from datetime import datetime
from typing import (
    Optional, List, Dict, Any, Union, Tuple, 
    TYPE_CHECKING, BinaryIO, TextIO
)

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import geopandas as gpd
    import rasterio

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================

# Mapeos de columnas por formato
MAPEO_SSN = {
    'Fecha': 'fecha',
    'Hora': 'hora',
    'Magnitud': 'magnitud',
    'Latitud': 'latitud',
    'Longitud': 'longitud',
    'Profundidad': 'profundidad_km',
    'Referencia de localizacion': 'lugar',
    'Fecha UTC': 'fecha_utc',
}

MAPEO_USGS = {
    'time': 'fecha',
    'latitude': 'latitud',
    'longitude': 'longitud',
    'depth': 'profundidad_km',
    'mag': 'magnitud',
    'magType': 'tipo_magnitud',
    'place': 'lugar',
    'id': 'id_evento',
}

MAPEO_ISC = {
    'date': 'fecha',
    'time': 'hora',
    'lat': 'latitud',
    'lon': 'longitud',
    'depth': 'profundidad_km',
    'mag': 'magnitud',
    'magtype': 'tipo_magnitud',
    'author': 'fuente',
}

MAPEO_IRIS = {
    'Time': 'fecha',
    'Latitude': 'latitud',
    'Longitude': 'longitud',
    'Depth/km': 'profundidad_km',
    'Magnitude': 'magnitud',
    'MagType': 'tipo_magnitud',
    'EventLocationName': 'lugar',
}


# =============================================================================
# LECTURA DE CATÁLOGOS
# =============================================================================

def leer_catalogo_ssn(
    ruta: Union[str, Path],
    encoding: str = 'utf-8',
    combinar_fecha_hora: bool = True,
    **kwargs
) -> pd.DataFrame:
    """
    Lee un catálogo del Servicio Sismológico Nacional de México.
    
    El SSN exporta sus datos en formato CSV con columnas específicas
    que esta función normaliza al formato estándar de SEISMEX.
    
    Args:
        ruta: Ruta al archivo CSV del SSN
        encoding: Codificación del archivo
        combinar_fecha_hora: Si True, combina columnas Fecha y Hora
        **kwargs: Argumentos adicionales para pd.read_csv
        
    Returns:
        DataFrame normalizado con columnas estándar
        
    Example:
        >>> df = leer_catalogo_ssn('ssn_2024.csv')
        >>> print(df.columns.tolist())
        ['fecha', 'latitud', 'longitud', 'profundidad_km', 'magnitud', ...]
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    
    logger.info(f"Leyendo catálogo SSN: {ruta}")
    
    # Leer CSV
    df = pd.read_csv(ruta, encoding=encoding, **kwargs)
    
    # Renombrar columnas
    columnas_existentes = {k: v for k, v in MAPEO_SSN.items() if k in df.columns}
    df = df.rename(columns=columnas_existentes)
    
    # Combinar fecha y hora si existen separadas
    if combinar_fecha_hora and 'hora' in df.columns and 'fecha' in df.columns:
        try:
            df['fecha'] = pd.to_datetime(
                df['fecha'].astype(str) + ' ' + df['hora'].astype(str),
                format='%Y-%m-%d %H:%M:%S',
                errors='coerce'
            )
            df = df.drop(columns=['hora'])
        except Exception as e:
            logger.warning(f"No se pudo combinar fecha/hora: {e}")
    
    # Asegurar tipos
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    for col in ['latitud', 'longitud', 'profundidad_km', 'magnitud']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Agregar metadatos
    df['fuente'] = 'SSN'
    
    logger.info(f"Leídos {len(df)} eventos del SSN")
    return df


def leer_catalogo_usgs(
    ruta: Union[str, Path],
    **kwargs
) -> pd.DataFrame:
    """
    Lee un catálogo del USGS (formato CSV de earthquake.usgs.gov).
    
    Args:
        ruta: Ruta al archivo CSV
        **kwargs: Argumentos adicionales para pd.read_csv
        
    Returns:
        DataFrame normalizado
    """
    ruta = Path(ruta)
    logger.info(f"Leyendo catálogo USGS: {ruta}")
    
    df = pd.read_csv(ruta, **kwargs)
    
    # Renombrar columnas
    columnas_existentes = {k: v for k, v in MAPEO_USGS.items() if k in df.columns}
    df = df.rename(columns=columnas_existentes)
    
    # Convertir fecha ISO8601
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], utc=True, errors='coerce')
    
    df['fuente'] = 'USGS'
    
    logger.info(f"Leídos {len(df)} eventos del USGS")
    return df


def leer_catalogo_isc(
    ruta: Union[str, Path],
    formato: str = 'csv',
    **kwargs
) -> pd.DataFrame:
    """
    Lee un catálogo del ISC (International Seismological Centre).
    
    Soporta formato CSV e ISF (IASPEI Seismic Format).
    
    Args:
        ruta: Ruta al archivo
        formato: 'csv' o 'isf'
        **kwargs: Argumentos adicionales
        
    Returns:
        DataFrame normalizado
    """
    ruta = Path(ruta)
    logger.info(f"Leyendo catálogo ISC: {ruta}")
    
    if formato.lower() == 'isf':
        df = _leer_isf(ruta)
    else:
        df = pd.read_csv(ruta, **kwargs)
        columnas_existentes = {k: v for k, v in MAPEO_ISC.items() if k in df.columns}
        df = df.rename(columns=columnas_existentes)
    
    # Combinar fecha y hora si están separadas
    if 'hora' in df.columns and 'fecha' in df.columns:
        try:
            df['fecha'] = pd.to_datetime(
                df['fecha'].astype(str) + ' ' + df['hora'].astype(str),
                errors='coerce'
            )
            df = df.drop(columns=['hora'])
        except Exception:
            pass
    
    df['fuente'] = 'ISC'
    
    logger.info(f"Leídos {len(df)} eventos del ISC")
    return df


def _leer_isf(ruta: Path) -> pd.DataFrame:
    """
    Parser simplificado para formato ISF.
    
    El formato ISF es complejo; esta implementación extrae
    solo los campos principales de eventos.
    """
    eventos = []
    evento_actual = {}
    
    with open(ruta, 'r') as f:
        for linea in f:
            linea = linea.strip()
            
            if linea.startswith('Event'):
                if evento_actual:
                    eventos.append(evento_actual)
                evento_actual = {}
                
            elif linea.startswith('Date') and 'Time' in linea:
                # Línea de encabezado, ignorar
                continue
                
            elif len(linea) >= 50 and linea[0:4].isdigit():
                # Posible línea de datos
                try:
                    evento_actual['fecha'] = linea[0:10].strip()
                    evento_actual['hora'] = linea[11:22].strip()
                    evento_actual['latitud'] = float(linea[36:44].strip())
                    evento_actual['longitud'] = float(linea[45:54].strip())
                except (ValueError, IndexError):
                    continue
    
    # Agregar último evento
    if evento_actual:
        eventos.append(evento_actual)
    
    return pd.DataFrame(eventos)


def leer_catalogo_generico(
    ruta: Union[str, Path],
    mapeo_columnas: Optional[Dict[str, str]] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Lee un catálogo con formato genérico.
    
    Intenta detectar el formato automáticamente o usa el mapeo proporcionado.
    
    Args:
        ruta: Ruta al archivo (CSV, Excel, JSON)
        mapeo_columnas: Diccionario de mapeo de columnas
        **kwargs: Argumentos adicionales
        
    Returns:
        DataFrame normalizado
    """
    ruta = Path(ruta)
    ext = ruta.suffix.lower()
    
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(ruta, **kwargs)
    elif ext == '.json':
        df = pd.read_json(ruta, **kwargs)
    else:
        df = pd.read_csv(ruta, **kwargs)
    
    if mapeo_columnas:
        columnas_existentes = {k: v for k, v in mapeo_columnas.items() if k in df.columns}
        df = df.rename(columns=columnas_existentes)
    
    return df


def detectar_formato_catalogo(ruta: Union[str, Path]) -> str:
    """
    Detecta el formato de un archivo de catálogo.
    
    Args:
        ruta: Ruta al archivo
        
    Returns:
        Formato detectado: 'ssn', 'usgs', 'isc', 'iris', o 'unknown'
    """
    ruta = Path(ruta)
    
    try:
        # Leer primeras líneas
        with open(ruta, 'r', encoding='utf-8') as f:
            header = f.readline().lower()
        
        if 'referencia de localizacion' in header or 'fecha utc' in header:
            return 'ssn'
        elif 'time' in header and 'magtype' in header:
            return 'usgs'
        elif 'magtype' in header.lower() and 'depth/km' in header.lower():
            return 'iris'
        elif 'author' in header and ('lat' in header or 'latitude' in header):
            return 'isc'
        else:
            return 'unknown'
    except Exception:
        return 'unknown'


# =============================================================================
# EXPORTACIÓN GIS
# =============================================================================

def exportar_geojson(
    datos: pd.DataFrame,
    ruta_salida: Union[str, Path],
    propiedades: Optional[List[str]] = None,
    columna_lat: str = 'latitud',
    columna_lon: str = 'longitud',
    precision: int = 6
) -> None:
    """
    Exporta un DataFrame a formato GeoJSON.
    
    Args:
        datos: DataFrame con coordenadas
        ruta_salida: Ruta de salida (.geojson)
        propiedades: Lista de columnas a incluir como propiedades
        columna_lat: Nombre de la columna de latitud
        columna_lon: Nombre de la columna de longitud
        precision: Decimales para coordenadas
        
    Example:
        >>> exportar_geojson(catalogo, 'sismos.geojson', 
        ...                  propiedades=['fecha', 'magnitud', 'profundidad_km'])
    """
    ruta_salida = Path(ruta_salida)
    
    if propiedades is None:
        propiedades = [col for col in datos.columns 
                       if col not in [columna_lat, columna_lon]]
    
    features = []
    for idx, row in datos.iterrows():
        # Obtener coordenadas
        lat = row.get(columna_lat)
        lon = row.get(columna_lon)
        
        if pd.isna(lat) or pd.isna(lon):
            continue
        
        # Crear propiedades
        props = {}
        for prop in propiedades:
            if prop in row:
                valor = row[prop]
                # Convertir tipos no serializables
                if isinstance(valor, (pd.Timestamp, datetime)):
                    valor = valor.isoformat()
                elif pd.isna(valor):
                    valor = None
                elif isinstance(valor, np.integer):
                    valor = int(valor)
                elif isinstance(valor, np.floating):
                    valor = float(valor)
                props[prop] = valor
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [round(lon, precision), round(lat, precision)]
            },
            'properties': props
        }
        features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Exportado GeoJSON con {len(features)} features: {ruta_salida}")


def exportar_geotiff(
    datos: np.ndarray,
    ruta_salida: Union[str, Path],
    bounds: Tuple[float, float, float, float],
    crs: str = 'EPSG:4326',
    nodata: float = -9999.0,
    descripcion: str = ''
) -> None:
    """
    Exporta una matriz 2D a formato GeoTIFF.
    
    Requiere rasterio instalado.
    
    Args:
        datos: Matriz 2D de valores
        ruta_salida: Ruta de salida (.tif)
        bounds: Límites (lon_min, lat_min, lon_max, lat_max)
        crs: Sistema de coordenadas
        nodata: Valor para datos faltantes
        descripcion: Descripción del raster
    """
    try:
        import rasterio
        from rasterio.transform import from_bounds
    except ImportError:
        raise ImportError("rasterio requerido: pip install rasterio")
    
    ruta_salida = Path(ruta_salida)
    
    # Dimensiones
    height, width = datos.shape
    lon_min, lat_min, lon_max, lat_max = bounds
    
    # Transformación afín
    transform = from_bounds(lon_min, lat_min, lon_max, lat_max, width, height)
    
    # Escribir archivo
    with rasterio.open(
        ruta_salida,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=datos.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata,
        compress='lzw'
    ) as dst:
        dst.write(datos, 1)
        if descripcion:
            dst.update_tags(1, DESCRIPTION=descripcion)
    
    logger.info(f"Exportado GeoTIFF {height}x{width}: {ruta_salida}")


def exportar_kml(
    datos: pd.DataFrame,
    ruta_salida: Union[str, Path],
    columna_nombre: str = 'lugar',
    columna_descripcion: Optional[str] = None,
    columna_lat: str = 'latitud',
    columna_lon: str = 'longitud',
    columna_magnitud: Optional[str] = 'magnitud'
) -> None:
    """
    Exporta un DataFrame a formato KML para Google Earth.
    
    Args:
        datos: DataFrame con coordenadas
        ruta_salida: Ruta de salida (.kml)
        columna_nombre: Columna para nombre del marcador
        columna_descripcion: Columna para descripción
        columna_lat, columna_lon: Columnas de coordenadas
        columna_magnitud: Columna para escalar íconos
    """
    ruta_salida = Path(ruta_salida)
    
    # Plantilla KML
    kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>SEISMEX Export</name>
  <description>Catálogo sísmico exportado por SEISMEX</description>
  <Style id="sismo">
    <IconStyle>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/earthquake.png</href></Icon>
    </IconStyle>
  </Style>
'''
    
    kml_footer = '''</Document>
</kml>'''
    
    placemarks = []
    for idx, row in datos.iterrows():
        lat = row.get(columna_lat)
        lon = row.get(columna_lon)
        
        if pd.isna(lat) or pd.isna(lon):
            continue
        
        nombre = str(row.get(columna_nombre, f'Evento {idx}'))
        
        # Construir descripción
        if columna_descripcion and columna_descripcion in row:
            desc = str(row[columna_descripcion])
        else:
            desc_parts = []
            if 'fecha' in row:
                desc_parts.append(f"Fecha: {row['fecha']}")
            if columna_magnitud and columna_magnitud in row:
                desc_parts.append(f"Magnitud: {row[columna_magnitud]}")
            if 'profundidad_km' in row:
                desc_parts.append(f"Profundidad: {row['profundidad_km']} km")
            desc = '<br/>'.join(desc_parts)
        
        placemark = f'''  <Placemark>
    <name>{nombre}</name>
    <description><![CDATA[{desc}]]></description>
    <styleUrl>#sismo</styleUrl>
    <Point>
      <coordinates>{lon},{lat},0</coordinates>
    </Point>
  </Placemark>
'''
        placemarks.append(placemark)
    
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(kml_header)
        f.write('\n'.join(placemarks))
        f.write(kml_footer)
    
    logger.info(f"Exportado KML con {len(placemarks)} marcadores: {ruta_salida}")


# =============================================================================
# SERIALIZACIÓN
# =============================================================================

def guardar_pickle(
    objeto: Any,
    ruta: Union[str, Path],
    comprimir: bool = True
) -> None:
    """
    Guarda un objeto en formato pickle (opcionalmente comprimido).
    
    Args:
        objeto: Cualquier objeto serializable
        ruta: Ruta de salida
        comprimir: Si True, usa compresión gzip
    """
    ruta = Path(ruta)
    
    if comprimir:
        if not ruta.suffix == '.gz':
            ruta = ruta.with_suffix(ruta.suffix + '.gz')
        with gzip.open(ruta, 'wb') as f:
            pickle.dump(objeto, f, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        with open(ruta, 'wb') as f:
            pickle.dump(objeto, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    logger.info(f"Guardado pickle: {ruta}")


def cargar_pickle(ruta: Union[str, Path]) -> Any:
    """
    Carga un objeto desde archivo pickle.
    
    Detecta automáticamente si está comprimido.
    
    Args:
        ruta: Ruta al archivo
        
    Returns:
        Objeto deserializado
    """
    ruta = Path(ruta)
    
    # Detectar si está comprimido
    try:
        with gzip.open(ruta, 'rb') as f:
            return pickle.load(f)
    except gzip.BadGzipFile:
        with open(ruta, 'rb') as f:
            return pickle.load(f)


def guardar_json(
    datos: Union[Dict, List],
    ruta: Union[str, Path],
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    Guarda datos en formato JSON.
    
    Maneja tipos numpy y datetime automáticamente.
    """
    ruta = Path(ruta)
    
    def convertir(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif pd.isna(obj):
            return None
        raise TypeError(f"No se puede serializar {type(obj)}")
    
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=indent, ensure_ascii=ensure_ascii, default=convertir)


def cargar_json(ruta: Union[str, Path]) -> Union[Dict, List]:
    """
    Carga datos desde archivo JSON.
    """
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)


# =============================================================================
# COMPRESIÓN
# =============================================================================

def comprimir_directorio(
    directorio: Union[str, Path],
    ruta_salida: Union[str, Path],
    formato: str = 'zip'
) -> None:
    """
    Comprime un directorio completo.
    
    Args:
        directorio: Directorio a comprimir
        ruta_salida: Ruta del archivo de salida
        formato: 'zip', 'gztar', 'bztar', 'xztar'
    """
    directorio = Path(directorio)
    ruta_salida = Path(ruta_salida)
    
    if formato == 'zip':
        shutil.make_archive(
            str(ruta_salida.with_suffix('')),
            'zip',
            directorio.parent,
            directorio.name
        )
    else:
        shutil.make_archive(
            str(ruta_salida.with_suffix('')),
            formato,
            directorio
        )
    
    logger.info(f"Comprimido: {ruta_salida}")


def descomprimir_archivo(
    archivo: Union[str, Path],
    directorio_destino: Union[str, Path]
) -> None:
    """
    Descomprime un archivo a un directorio.
    
    Soporta ZIP, TAR, GZ.
    """
    archivo = Path(archivo)
    directorio_destino = Path(directorio_destino)
    directorio_destino.mkdir(parents=True, exist_ok=True)
    
    if archivo.suffix == '.zip':
        with zipfile.ZipFile(archivo, 'r') as zf:
            zf.extractall(directorio_destino)
    elif archivo.suffix in ['.tar', '.gz', '.bz2', '.xz']:
        shutil.unpack_archive(archivo, directorio_destino)
    else:
        raise ValueError(f"Formato no soportado: {archivo.suffix}")
    
    logger.info(f"Descomprimido en: {directorio_destino}")


# =============================================================================
# UTILIDADES DE ARCHIVOS
# =============================================================================

def asegurar_directorio(ruta: Union[str, Path]) -> Path:
    """
    Asegura que un directorio exista, creándolo si es necesario.
    
    Args:
        ruta: Ruta del directorio
        
    Returns:
        Path del directorio
    """
    ruta = Path(ruta)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def listar_archivos(
    directorio: Union[str, Path],
    patron: str = '*',
    recursivo: bool = False
) -> List[Path]:
    """
    Lista archivos en un directorio con patrón.
    
    Args:
        directorio: Directorio a buscar
        patron: Patrón glob (ej: '*.csv')
        recursivo: Si buscar en subdirectorios
        
    Returns:
        Lista de rutas de archivos
    """
    directorio = Path(directorio)
    
    if recursivo:
        return list(directorio.rglob(patron))
    else:
        return list(directorio.glob(patron))


def obtener_tamaño_archivo(ruta: Union[str, Path]) -> Tuple[float, str]:
    """
    Obtiene el tamaño de un archivo en unidad legible.
    
    Returns:
        Tupla (valor, unidad) ej: (2.5, 'MB')
    """
    ruta = Path(ruta)
    tamaño = ruta.stat().st_size
    
    for unidad in ['B', 'KB', 'MB', 'GB', 'TB']:
        if tamaño < 1024:
            return round(tamaño, 2), unidad
        tamaño /= 1024
    
    return round(tamaño, 2), 'TB'


def limpiar_nombre_archivo(nombre: str) -> str:
    """
    Limpia un string para usarlo como nombre de archivo.
    
    Remueve caracteres no permitidos en sistemas de archivos.
    """
    # Caracteres no permitidos
    invalidos = '<>:"/\\|?*'
    for char in invalidos:
        nombre = nombre.replace(char, '_')
    
    # Remover espacios múltiples
    while '  ' in nombre:
        nombre = nombre.replace('  ', ' ')
    
    return nombre.strip()


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("SEISMEX Utils - Ejemplos de uso de io.py")
    print("=" * 60)
    
    # Crear datos de ejemplo
    datos_ejemplo = pd.DataFrame({
        'fecha': pd.date_range('2024-01-01', periods=5, freq='D'),
        'latitud': [19.2, 19.3, 19.4, 19.5, 19.6],
        'longitud': [-103.7, -103.8, -103.9, -104.0, -104.1],
        'profundidad_km': [10, 20, 30, 15, 25],
        'magnitud': [3.5, 4.0, 3.2, 4.5, 3.8],
        'lugar': ['Colima', 'Comala', 'Villa de Álvarez', 'Manzanillo', 'Tecomán']
    })
    
    print("\n--- Datos de ejemplo ---")
    print(datos_ejemplo)
    
    # Ejemplo: Exportar a GeoJSON
    print("\n--- Exportación GeoJSON ---")
    ruta_geojson = Path('/tmp/ejemplo_seismex.geojson')
    exportar_geojson(datos_ejemplo, ruta_geojson)
    print(f"Exportado: {ruta_geojson}")
    
    # Ejemplo: Exportar a KML
    print("\n--- Exportación KML ---")
    ruta_kml = Path('/tmp/ejemplo_seismex.kml')
    exportar_kml(datos_ejemplo, ruta_kml)
    print(f"Exportado: {ruta_kml}")
    
    # Ejemplo: Pickle
    print("\n--- Serialización ---")
    ruta_pickle = Path('/tmp/ejemplo_seismex.pkl.gz')
    guardar_pickle(datos_ejemplo, ruta_pickle)
    datos_cargados = cargar_pickle(ruta_pickle)
    print(f"Guardado y cargado: {len(datos_cargados)} filas")
    
    # Ejemplo: Detección de formato
    print("\n--- Detección de formato ---")
    # Simular archivo SSN
    ruta_test = Path('/tmp/test_ssn.csv')
    pd.DataFrame({
        'Fecha': ['2024-01-01'],
        'Latitud': [19.2],
        'Longitud': [-103.7],
        'Magnitud': [4.0],
        'Referencia de localizacion': ['Colima']
    }).to_csv(ruta_test, index=False)
    
    formato = detectar_formato_catalogo(ruta_test)
    print(f"Formato detectado: {formato}")
    
    print("\n✓ Todos los ejemplos ejecutados correctamente")
