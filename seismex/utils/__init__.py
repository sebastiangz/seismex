"""
SEISMEX Utils - Utilidades y funciones auxiliares
=================================================

Módulos disponibles:
- geo: Cálculos geográficos y transformaciones de coordenadas
- io: Lectura/escritura de archivos y formatos
- validators: Validación y limpieza de datos
- constants: Constantes físicas y de configuración
"""

from seismex.utils.constants import (
    COEF_ENERGIA_A,
    COEF_ENERGIA_B,
    MEXICO_LAT_MIN,
    MEXICO_LAT_MAX,
    MEXICO_LON_MIN,
    MEXICO_LON_MAX,
    COLORES_ESD,
    NIVELES_ESD,
)

__all__ = [
    # Constantes de energía
    "COEF_ENERGIA_A",
    "COEF_ENERGIA_B",
    # Límites de México
    "MEXICO_LAT_MIN",
    "MEXICO_LAT_MAX",
    "MEXICO_LON_MIN",
    "MEXICO_LON_MAX",
    # ESD
    "COLORES_ESD",
    "NIVELES_ESD",
]
