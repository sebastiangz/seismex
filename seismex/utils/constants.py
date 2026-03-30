"""
SEISMEX Constants - Constantes del sistema
==========================================

Constantes físicas, geográficas y de configuración para SEISMEX.
"""

# ============================================
# CONSTANTES FÍSICAS - ENERGÍA SÍSMICA
# ============================================

# Relación de Kanamori (1977): log₁₀(E) = a*Mw + b
COEF_ENERGIA_A = 1.5    # Coeficiente de magnitud
COEF_ENERGIA_B = 11.8   # Constante (ergios)

# ============================================
# LÍMITES GEOGRÁFICOS DE MÉXICO
# ============================================

MEXICO_LAT_MIN = 14.5   # Límite sur (Chiapas)
MEXICO_LAT_MAX = 32.7   # Límite norte (Baja California)
MEXICO_LON_MIN = -117.1 # Límite oeste (Baja California)
MEXICO_LON_MAX = -86.7  # Límite este (Quintana Roo)

# Centro geográfico aproximado
MEXICO_LAT_CENTER = 23.6
MEXICO_LON_CENTER = -102.5

# ============================================
# ZONAS SÍSMICAS PRINCIPALES
# ============================================

ZONAS_SISMICAS = {
    'subduccion_pacifico': {
        'nombre': 'Zona de Subducción del Pacífico',
        'lat_min': 14.5, 'lat_max': 23.5,
        'lon_min': -106.0, 'lon_max': -92.0,
        'prof_max': 150
    },
    'falla_san_andreas': {
        'nombre': 'Sistema de Fallas de Baja California',
        'lat_min': 28.0, 'lat_max': 32.7,
        'lon_min': -117.1, 'lon_max': -114.0,
        'prof_max': 30
    },
    'eje_neovolcanico': {
        'nombre': 'Eje Neovolcánico Transmexicano',
        'lat_min': 18.5, 'lat_max': 21.0,
        'lon_min': -105.0, 'lon_max': -96.0,
        'prof_max': 80
    },
    'graben_colima': {
        'nombre': 'Graben de Colima',
        'lat_min': 18.5, 'lat_max': 20.5,
        'lon_min': -104.5, 'lon_max': -103.0,
        'prof_max': 100
    },
    'oaxaca': {
        'nombre': 'Zona Sísmica de Oaxaca',
        'lat_min': 15.5, 'lat_max': 18.5,
        'lon_min': -98.5, 'lon_max': -94.0,
        'prof_max': 100
    },
}

# ============================================
# CONFIGURACIÓN ESD POR DEFECTO
# ============================================

DEFAULT_CELL_SIZE = 10.0      # km
DEFAULT_SLIDE_STEP = 2.5      # km (paso de deslizamiento)
DEFAULT_DEPTH_RANGE = (0, 150) # km
DEFAULT_MC_METHOD = 'maxc'
DEFAULT_B_METHOD = 'mle'
DEFAULT_MC_CORRECTION = 0.2   # Corrección conservadora Woessner & Wiemer 2005

# ============================================
# PALETA DE COLORES ESD
# ============================================

# Colores basados en Del Pezzo et al. (GRL)
# Índigo → Azul → Verde → Rosa → Rojo
COLORES_ESD = [
    '#1a0033',  # Índigo muy oscuro
    '#3d0066',  # Índigo oscuro
    '#0000b3',  # Azul oscuro
    '#0066cc',  # Azul medio
    '#00cccc',  # Cian
    '#00cc66',  # Verde-cian
    '#66cc00',  # Verde-amarillo
    '#cccc00',  # Amarillo
    '#ff9900',  # Naranja
    '#ff3300',  # Rojo-naranja
    '#cc0000',  # Rojo oscuro
    '#800000',  # Granate
]

# Niveles de contorno para log₁₀(ESD)
NIVELES_ESD = [-12, -7, -4.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0, 0.5]

# ============================================
# CONFIGURACIÓN DE GUTENBERG-RICHTER
# ============================================

# Métodos de cálculo de Mc (magnitud de completitud)
MC_METHODS = ['maxc', 'gft', 'mbs', 'manual']

# Métodos de cálculo de valor-b
B_METHODS = ['mle', 'lsq']  # Máxima verosimilitud, Mínimos cuadrados

# ============================================
# RUTAS POR DEFECTO
# ============================================

import os
from pathlib import Path

# Directorio home del usuario
HOME_DIR = Path.home()

# Directorio de configuración de SEISMEX
DIR_CONFIG = HOME_DIR / '.seismex' / 'config'

# Directorio de caché
DIR_CACHE = HOME_DIR / '.seismex' / 'cache'

# Directorio de logs
DIR_LOGS = HOME_DIR / '.seismex' / 'logs'

# ============================================
# FORMATOS DE FECHA
# ============================================

DATE_FORMAT_ISO = '%Y-%m-%dT%H:%M:%S'
DATE_FORMAT_SSN = '%Y/%m/%d %H:%M:%S'
DATE_FORMAT_ISC = '%Y-%m-%d %H:%M:%S.%f'

# ============================================
# CONSTANTES DE CONVERSIÓN DE MAGNITUD
# ============================================

# Coeficientes para conversión Ml -> Mw (México)
# Mw = a * Ml + b
ML_TO_MW_A = 0.85
ML_TO_MW_B = 0.58

# Coeficientes para conversión mb -> Mw
# Mw = a * mb + b
MB_TO_MW_A = 1.03
MB_TO_MW_B = -0.20

# Coeficientes para conversión Ms -> Mw
# Mw = a * Ms + b
MS_TO_MW_A = 0.67
MS_TO_MW_B = 2.13

# ============================================
# UMBRALES Y LÍMITES
# ============================================

# Magnitud mínima considerada significativa
MAG_MIN_SIGNIFICATIVA = 4.0

# Magnitud mínima para análisis ESD
MAG_MIN_ESD = 2.0

# Profundidad máxima razonable (km)
PROF_MAX_RAZONABLE = 700

# Error máximo de localización aceptable (km)
ERROR_LOC_MAX = 50

# ============================================
# PARÁMETROS DE RED
# ============================================

# Timeout para peticiones HTTP (segundos)
HTTP_TIMEOUT = 30

# Reintentos máximos
HTTP_MAX_RETRIES = 3

# URLs de servicios
URL_SSN = "http://www2.ssn.unam.mx:8080/catalogo"
URL_ISC = "http://www.isc.ac.uk/cgi-bin/web-db-v4"
URL_USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
URL_GCMT = "https://www.globalcmt.org/cgi-bin/globalcmt-cgi-bin/CMT5/form"
