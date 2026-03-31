"""
SEISMEX Core - Módulo Central
==============================

Módulo central de SEISMEX con funcionalidades base para el manejo
de catálogos sísmicos, conversión de magnitudes y preprocesamiento.

Clases principales:
    - CatalogoSismico: Contenedor principal para catálogos sísmicos
    - MetadataCatalogo: Metadatos del catálogo
    - ResultadoValidacion: Resultado de validación

Funciones de conveniencia:
    - cargar_catalogo: Carga catálogos con detección automática de formato

Ejemplo de uso:
    >>> from seismex.core import CatalogoSismico, cargar_catalogo
    >>> 
    >>> # Cargar desde CSV
    >>> catalogo = CatalogoSismico.desde_csv('sismos.csv', formato='ssn')
    >>> 
    >>> # O usar la función de conveniencia
    >>> catalogo = cargar_catalogo('sismos.csv')
    >>> 
    >>> # Validar y filtrar
    >>> catalogo.validar()
    >>> filtrado = catalogo.filtrar_magnitud(mag_min=4.0)
    >>> print(filtrado.resumen())
"""

from .catalog import (
    # Clase principal
    CatalogoSismico,
    
    # Dataclasses auxiliares
    MetadataCatalogo,
    ResultadoValidacion,
    
    # Funciones de conveniencia
    cargar_catalogo,
    
    # Constantes
    COLUMNAS_REQUERIDAS,
    COLUMNAS_OPCIONALES,
    MAPEOS_COLUMNAS,
    CONVERSIONES_MAGNITUD,
)

__all__ = [
    # Clase principal
    'CatalogoSismico',
    
    # Dataclasses
    'MetadataCatalogo',
    'ResultadoValidacion',
    
    # Funciones
    'cargar_catalogo',
    
    # Constantes
    'COLUMNAS_REQUERIDAS',
    'COLUMNAS_OPCIONALES',
    'MAPEOS_COLUMNAS',
    'CONVERSIONES_MAGNITUD',
]
