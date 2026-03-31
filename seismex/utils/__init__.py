"""
SEISMEX Utils - Utilidades
==========================

Módulo de utilidades para SEISMEX.

Submódulos:
- constants: Constantes del proyecto
- geo: Utilidades geográficas
- io: Entrada/salida de archivos
- validators: Validación de datos

Uso típico:
    from seismex.utils import calcular_distancia_haversine
    from seismex.utils import leer_catalogo_ssn, exportar_geojson
    from seismex.utils import validar_catalogo_completo
"""

# Constantes
from seismex.utils.constants import (
    MEXICO_LAT_MIN,
    MEXICO_LAT_MAX,
    MEXICO_LON_MIN,
    MEXICO_LON_MAX,
    REGIONES_SISMICAS,
    CONVERSIONES_MAGNITUD,
    PROFUNDIDADES_TIPO,
)

# Utilidades geográficas
from seismex.utils.geo import (
    # Constantes
    RADIO_TIERRA_KM,
    RADIO_TIERRA_M,
    WGS84_A,
    WGS84_B,
    WGS84_F,
    DEG_TO_RAD,
    RAD_TO_DEG,
    DEG_TO_KM_LAT,
    # Distancias
    calcular_distancia_haversine,
    calcular_distancia_haversine_vectorizado,
    calcular_distancia_vincenty,
    calcular_distancia_3d,
    # UTM
    obtener_zona_utm,
    obtener_hemisferio,
    convertir_latlon_a_utm,
    convertir_utm_a_latlon,
    # Azimut y dirección
    calcular_azimut,
    calcular_rumbo,
    punto_destino,
    # Polígonos
    punto_en_poligono,
    puntos_en_poligono_vectorizado,
    crear_rectangulo,
    crear_circulo,
    # Grillas
    Grilla,
    crear_grilla_regular,
    crear_grilla_km,
    # Auxiliares
    normalizar_longitud,
    grados_a_km,
    km_a_grados,
    calcular_area_region,
)

# Entrada/salida
from seismex.utils.io import (
    # Mapeos de columnas
    MAPEO_SSN,
    MAPEO_USGS,
    MAPEO_ISC,
    MAPEO_IRIS,
    # Lectura de catálogos
    leer_catalogo_ssn,
    leer_catalogo_usgs,
    leer_catalogo_isc,
    leer_catalogo_generico,
    detectar_formato_catalogo,
    # Exportación GIS
    exportar_geojson,
    exportar_geotiff,
    exportar_kml,
    # Serialización
    guardar_pickle,
    cargar_pickle,
    guardar_json,
    cargar_json,
    # Compresión
    comprimir_directorio,
    descomprimir_archivo,
    # Utilidades de archivos
    asegurar_directorio,
    listar_archivos,
    obtener_tamaño_archivo,
    limpiar_nombre_archivo,
)

# Validadores
from seismex.utils.validators import (
    # Dataclasses
    ProblemaValidacion,
    ReporteCalidad,
    # Validación de coordenadas
    validar_coordenadas,
    validar_coordenadas_mexico,
    validar_coordenadas_array,
    # Validación de magnitud
    validar_magnitud,
    validar_magnitud_array,
    # Validación de profundidad
    validar_profundidad,
    validar_profundidad_array,
    # Validación de fechas
    validar_fecha,
    validar_fechas_array,
    # Detección de duplicados
    detectar_duplicados,
    contar_duplicados,
    # Detección de outliers
    detectar_outliers_iqr,
    detectar_outliers_zscore,
    detectar_outliers,
    # Validación completa
    validar_catalogo_completo,
    reportar_calidad,
    # Limpieza
    limpiar_catalogo,
)

__all__ = [
    # === CONSTANTES ===
    'MEXICO_LAT_MIN',
    'MEXICO_LAT_MAX',
    'MEXICO_LON_MIN',
    'MEXICO_LON_MAX',
    'REGIONES_SISMICAS',
    'CONVERSIONES_MAGNITUD',
    'PROFUNDIDADES_TIPO',
    
    # === GEO ===
    # Constantes
    'RADIO_TIERRA_KM',
    'RADIO_TIERRA_M',
    'WGS84_A',
    'WGS84_B',
    'WGS84_F',
    'DEG_TO_RAD',
    'RAD_TO_DEG',
    'DEG_TO_KM_LAT',
    # Distancias
    'calcular_distancia_haversine',
    'calcular_distancia_haversine_vectorizado',
    'calcular_distancia_vincenty',
    'calcular_distancia_3d',
    # UTM
    'obtener_zona_utm',
    'obtener_hemisferio',
    'convertir_latlon_a_utm',
    'convertir_utm_a_latlon',
    # Azimut y dirección
    'calcular_azimut',
    'calcular_rumbo',
    'punto_destino',
    # Polígonos
    'punto_en_poligono',
    'puntos_en_poligono_vectorizado',
    'crear_rectangulo',
    'crear_circulo',
    # Grillas
    'Grilla',
    'crear_grilla_regular',
    'crear_grilla_km',
    # Auxiliares
    'normalizar_longitud',
    'grados_a_km',
    'km_a_grados',
    'calcular_area_region',
    
    # === IO ===
    # Mapeos
    'MAPEO_SSN',
    'MAPEO_USGS',
    'MAPEO_ISC',
    'MAPEO_IRIS',
    # Lectura
    'leer_catalogo_ssn',
    'leer_catalogo_usgs',
    'leer_catalogo_isc',
    'leer_catalogo_generico',
    'detectar_formato_catalogo',
    # Exportación GIS
    'exportar_geojson',
    'exportar_geotiff',
    'exportar_kml',
    # Serialización
    'guardar_pickle',
    'cargar_pickle',
    'guardar_json',
    'cargar_json',
    # Compresión
    'comprimir_directorio',
    'descomprimir_archivo',
    # Archivos
    'asegurar_directorio',
    'listar_archivos',
    'obtener_tamaño_archivo',
    'limpiar_nombre_archivo',
    
    # === VALIDATORS ===
    # Dataclasses
    'ProblemaValidacion',
    'ReporteCalidad',
    # Coordenadas
    'validar_coordenadas',
    'validar_coordenadas_mexico',
    'validar_coordenadas_array',
    # Magnitud
    'validar_magnitud',
    'validar_magnitud_array',
    # Profundidad
    'validar_profundidad',
    'validar_profundidad_array',
    # Fechas
    'validar_fecha',
    'validar_fechas_array',
    # Duplicados
    'detectar_duplicados',
    'contar_duplicados',
    # Outliers
    'detectar_outliers_iqr',
    'detectar_outliers_zscore',
    'detectar_outliers',
    # Validación completa
    'validar_catalogo_completo',
    'reportar_calidad',
    # Limpieza
    'limpiar_catalogo',
]
