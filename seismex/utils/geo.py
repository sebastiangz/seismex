"""
SEISMEX Utils - Utilidades Geográficas
======================================

Funciones para cálculos geográficos y transformaciones de coordenadas.

Incluye:
- Cálculo de distancias (Haversine, Vincenty)
- Conversiones UTM ↔ Lat/Lon
- Cálculo de azimut
- Verificación de puntos en polígonos
- Creación de grillas regulares
- Funciones geodésicas auxiliares

Ejemplo de uso:
    >>> from seismex.utils.geo import calcular_distancia_haversine
    >>> distancia = calcular_distancia_haversine(19.24, -103.72, 19.43, -99.13)
    >>> print(f"Distancia: {distancia:.2f} km")

Autor: SEISMEX Team
Licencia: MIT
"""

from __future__ import annotations

import math
import warnings
from typing import Tuple, List, Optional, Union, Sequence
from dataclasses import dataclass

import numpy as np

# =============================================================================
# CONSTANTES
# =============================================================================

# Radio de la Tierra
RADIO_TIERRA_KM = 6371.0  # Radio medio en km
RADIO_TIERRA_M = 6371000.0  # Radio medio en metros

# Parámetros del elipsoide WGS84
WGS84_A = 6378137.0  # Semieje mayor (m)
WGS84_B = 6356752.314245  # Semieje menor (m)
WGS84_F = 1 / 298.257223563  # Aplanamiento

# Conversión grados ↔ radianes
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi

# Factor de conversión para grados a km (aproximado en el ecuador)
DEG_TO_KM_LAT = 111.32  # km por grado de latitud
DEG_TO_KM_LON_ECUADOR = 111.32  # km por grado de longitud en el ecuador


# =============================================================================
# FUNCIONES DE DISTANCIA
# =============================================================================

def calcular_distancia_haversine(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    radio_km: float = RADIO_TIERRA_KM
) -> float:
    """
    Calcula la distancia entre dos puntos usando la fórmula de Haversine.
    
    La fórmula de Haversine da la distancia del círculo máximo entre
    dos puntos en una esfera, dadas sus latitudes y longitudes.
    
    Args:
        lat1: Latitud del primer punto (grados)
        lon1: Longitud del primer punto (grados)
        lat2: Latitud del segundo punto (grados)
        lon2: Longitud del segundo punto (grados)
        radio_km: Radio de la Tierra en km (default: 6371)
        
    Returns:
        Distancia en kilómetros
        
    Example:
        >>> calcular_distancia_haversine(19.24, -103.72, 19.43, -99.13)
        465.23  # Colima a CDMX aproximadamente
        
    References:
        https://en.wikipedia.org/wiki/Haversine_formula
    """
    # Convertir a radianes
    lat1_rad = lat1 * DEG_TO_RAD
    lat2_rad = lat2 * DEG_TO_RAD
    dlat = (lat2 - lat1) * DEG_TO_RAD
    dlon = (lon2 - lon1) * DEG_TO_RAD
    
    # Fórmula de Haversine
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return radio_km * c


def calcular_distancia_haversine_vectorizado(
    lat1: np.ndarray,
    lon1: np.ndarray,
    lat2: Union[float, np.ndarray],
    lon2: Union[float, np.ndarray],
    radio_km: float = RADIO_TIERRA_KM
) -> np.ndarray:
    """
    Versión vectorizada de la distancia Haversine.
    
    Calcula la distancia desde múltiples puntos a uno o más puntos de referencia.
    Optimizado para arrays grandes usando NumPy.
    
    Args:
        lat1: Array de latitudes de origen
        lon1: Array de longitudes de origen
        lat2: Latitud(es) de destino (escalar o array)
        lon2: Longitud(es) de destino (escalar o array)
        radio_km: Radio de la Tierra en km
        
    Returns:
        Array de distancias en km
    """
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = (np.sin(dlat / 2) ** 2 +
         np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return radio_km * c


def calcular_distancia_vincenty(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    max_iter: int = 200,
    tol: float = 1e-12
) -> float:
    """
    Calcula la distancia geodésica usando la fórmula de Vincenty.
    
    Más precisa que Haversine para distancias largas ya que considera
    el aplanamiento de la Tierra (elipsoide WGS84).
    
    Args:
        lat1: Latitud del primer punto (grados)
        lon1: Longitud del primer punto (grados)
        lat2: Latitud del segundo punto (grados)
        lon2: Longitud del segundo punto (grados)
        max_iter: Máximo de iteraciones para convergencia
        tol: Tolerancia para convergencia
        
    Returns:
        Distancia en kilómetros
        
    Raises:
        ValueError: Si la fórmula no converge (puntos antípodas)
        
    References:
        Vincenty, T. (1975). Direct and Inverse Solutions of Geodesics
        on the Ellipsoid with Application of Nested Equations.
        Survey Review, 23(176), 88-93.
    """
    # Parámetros del elipsoide
    a = WGS84_A
    f = WGS84_F
    b = (1 - f) * a
    
    # Convertir a radianes
    phi1 = lat1 * DEG_TO_RAD
    phi2 = lat2 * DEG_TO_RAD
    L = (lon2 - lon1) * DEG_TO_RAD
    
    # Latitudes reducidas
    U1 = math.atan((1 - f) * math.tan(phi1))
    U2 = math.atan((1 - f) * math.tan(phi2))
    
    sin_U1 = math.sin(U1)
    cos_U1 = math.cos(U1)
    sin_U2 = math.sin(U2)
    cos_U2 = math.cos(U2)
    
    # Iterar hasta convergencia
    lambda_val = L
    for _ in range(max_iter):
        sin_lambda = math.sin(lambda_val)
        cos_lambda = math.cos(lambda_val)
        
        sin_sigma = math.sqrt(
            (cos_U2 * sin_lambda) ** 2 +
            (cos_U1 * sin_U2 - sin_U1 * cos_U2 * cos_lambda) ** 2
        )
        
        if sin_sigma == 0:
            return 0.0  # Puntos coincidentes
        
        cos_sigma = sin_U1 * sin_U2 + cos_U1 * cos_U2 * cos_lambda
        sigma = math.atan2(sin_sigma, cos_sigma)
        
        sin_alpha = cos_U1 * cos_U2 * sin_lambda / sin_sigma
        cos2_alpha = 1 - sin_alpha ** 2
        
        if cos2_alpha == 0:
            cos_2sigma_m = 0
        else:
            cos_2sigma_m = cos_sigma - 2 * sin_U1 * sin_U2 / cos2_alpha
        
        C = f / 16 * cos2_alpha * (4 + f * (4 - 3 * cos2_alpha))
        
        lambda_prev = lambda_val
        lambda_val = L + (1 - C) * f * sin_alpha * (
            sigma + C * sin_sigma * (
                cos_2sigma_m + C * cos_sigma * (-1 + 2 * cos_2sigma_m ** 2)
            )
        )
        
        if abs(lambda_val - lambda_prev) < tol:
            break
    else:
        warnings.warn("Vincenty no convergió, usando Haversine como fallback")
        return calcular_distancia_haversine(lat1, lon1, lat2, lon2)
    
    # Calcular distancia
    u2 = cos2_alpha * (a ** 2 - b ** 2) / (b ** 2)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    
    delta_sigma = B * sin_sigma * (
        cos_2sigma_m + B / 4 * (
            cos_sigma * (-1 + 2 * cos_2sigma_m ** 2) -
            B / 6 * cos_2sigma_m * (-3 + 4 * sin_sigma ** 2) * (-3 + 4 * cos_2sigma_m ** 2)
        )
    )
    
    s = b * A * (sigma - delta_sigma)
    
    return s / 1000.0  # Convertir a km


def calcular_distancia_3d(
    lat1: float,
    lon1: float,
    prof1: float,
    lat2: float,
    lon2: float,
    prof2: float
) -> float:
    """
    Calcula la distancia 3D entre dos puntos considerando profundidad.
    
    Útil para cálculos sísmicos donde la profundidad es relevante.
    
    Args:
        lat1, lon1, prof1: Coordenadas del primer punto (grados, grados, km)
        lat2, lon2, prof2: Coordenadas del segundo punto (grados, grados, km)
        
    Returns:
        Distancia 3D en kilómetros
    """
    # Distancia horizontal
    dist_h = calcular_distancia_haversine(lat1, lon1, lat2, lon2)
    
    # Diferencia de profundidad
    dist_v = abs(prof2 - prof1)
    
    # Distancia 3D (Pitágoras)
    return math.sqrt(dist_h ** 2 + dist_v ** 2)


# =============================================================================
# CONVERSIONES UTM
# =============================================================================

def obtener_zona_utm(longitud: float) -> int:
    """
    Determina la zona UTM para una longitud dada.
    
    Args:
        longitud: Longitud en grados (-180 a 180)
        
    Returns:
        Número de zona UTM (1-60)
    """
    return int((longitud + 180) / 6) + 1


def obtener_hemisferio(latitud: float) -> str:
    """
    Determina el hemisferio basado en la latitud.
    
    Args:
        latitud: Latitud en grados
        
    Returns:
        'N' para norte, 'S' para sur
    """
    return 'N' if latitud >= 0 else 'S'


def convertir_latlon_a_utm(
    latitud: float,
    longitud: float,
    zona: Optional[int] = None,
    forzar_zona: bool = False
) -> Tuple[float, float, int, str]:
    """
    Convierte coordenadas geográficas (lat/lon) a UTM.
    
    Implementación directa sin dependencias externas.
    
    Args:
        latitud: Latitud en grados (-80 a 84)
        longitud: Longitud en grados (-180 a 180)
        zona: Zona UTM forzada (opcional)
        forzar_zona: Si True, usa la zona especificada
        
    Returns:
        Tupla (easting, northing, zona, hemisferio)
        - easting: Coordenada Este en metros
        - northing: Coordenada Norte en metros
        - zona: Número de zona UTM
        - hemisferio: 'N' o 'S'
        
    Raises:
        ValueError: Si la latitud está fuera del rango UTM
        
    Example:
        >>> convertir_latlon_a_utm(19.24, -103.72)
        (649234.5, 2128456.7, 13, 'N')
    """
    # Validar rango
    if not -80 <= latitud <= 84:
        raise ValueError(f"Latitud {latitud} fuera del rango UTM (-80 a 84)")
    
    # Determinar zona
    if zona is None or not forzar_zona:
        zona = obtener_zona_utm(longitud)
    
    hemisferio = obtener_hemisferio(latitud)
    
    # Parámetros
    a = WGS84_A
    f = WGS84_F
    e2 = 2 * f - f ** 2  # Primera excentricidad al cuadrado
    e_prime2 = e2 / (1 - e2)  # Segunda excentricidad al cuadrado
    
    k0 = 0.9996  # Factor de escala
    
    # Meridiano central de la zona
    lon0 = (zona - 1) * 6 - 180 + 3
    
    # Convertir a radianes
    phi = latitud * DEG_TO_RAD
    lambda_diff = (longitud - lon0) * DEG_TO_RAD
    
    # Cálculos auxiliares
    N = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    T = math.tan(phi) ** 2
    C = e_prime2 * math.cos(phi) ** 2
    A = lambda_diff * math.cos(phi)
    
    # Arco meridiano
    M = a * (
        (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * phi -
        (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*phi) +
        (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*phi) -
        (35*e2**3/3072) * math.sin(6*phi)
    )
    
    # Calcular easting y northing
    easting = k0 * N * (
        A + (1-T+C) * A**3/6 +
        (5 - 18*T + T**2 + 72*C - 58*e_prime2) * A**5/120
    ) + 500000  # False easting
    
    northing = k0 * (
        M + N * math.tan(phi) * (
            A**2/2 + (5 - T + 9*C + 4*C**2) * A**4/24 +
            (61 - 58*T + T**2 + 600*C - 330*e_prime2) * A**6/720
        )
    )
    
    # Ajuste para hemisferio sur
    if hemisferio == 'S':
        northing += 10000000  # False northing para sur
    
    return easting, northing, zona, hemisferio


def convertir_utm_a_latlon(
    easting: float,
    northing: float,
    zona: int,
    hemisferio: str = 'N'
) -> Tuple[float, float]:
    """
    Convierte coordenadas UTM a geográficas (lat/lon).
    
    Args:
        easting: Coordenada Este en metros
        northing: Coordenada Norte en metros
        zona: Número de zona UTM (1-60)
        hemisferio: 'N' para norte, 'S' para sur
        
    Returns:
        Tupla (latitud, longitud) en grados
        
    Example:
        >>> convertir_utm_a_latlon(649234.5, 2128456.7, 13, 'N')
        (19.24, -103.72)
    """
    # Parámetros
    a = WGS84_A
    f = WGS84_F
    e2 = 2 * f - f ** 2
    e_prime2 = e2 / (1 - e2)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    
    k0 = 0.9996
    
    # Ajustes
    x = easting - 500000  # Remover false easting
    y = northing
    if hemisferio.upper() == 'S':
        y -= 10000000  # Remover false northing
    
    # Meridiano central
    lon0 = (zona - 1) * 6 - 180 + 3
    
    # Footprint latitude
    M = y / k0
    mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))
    
    phi1 = mu + (
        (3*e1/2 - 27*e1**3/32) * math.sin(2*mu) +
        (21*e1**2/16 - 55*e1**4/32) * math.sin(4*mu) +
        (151*e1**3/96) * math.sin(6*mu) +
        (1097*e1**4/512) * math.sin(8*mu)
    )
    
    # Cálculos auxiliares
    N1 = a / math.sqrt(1 - e2 * math.sin(phi1)**2)
    T1 = math.tan(phi1)**2
    C1 = e_prime2 * math.cos(phi1)**2
    R1 = a * (1 - e2) / (1 - e2 * math.sin(phi1)**2)**1.5
    D = x / (N1 * k0)
    
    # Calcular latitud y longitud
    lat = phi1 - (N1 * math.tan(phi1) / R1) * (
        D**2/2 - (5 + 3*T1 + 10*C1 - 4*C1**2 - 9*e_prime2) * D**4/24 +
        (61 + 90*T1 + 298*C1 + 45*T1**2 - 252*e_prime2 - 3*C1**2) * D**6/720
    )
    
    lon = lon0 + (
        D - (1 + 2*T1 + C1) * D**3/6 +
        (5 - 2*C1 + 28*T1 - 3*C1**2 + 8*e_prime2 + 24*T1**2) * D**5/120
    ) / math.cos(phi1)
    
    return lat * RAD_TO_DEG, lon * RAD_TO_DEG


# =============================================================================
# AZIMUT Y DIRECCIÓN
# =============================================================================

def calcular_azimut(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calcula el azimut inicial desde el punto 1 al punto 2.
    
    El azimut es el ángulo medido en sentido horario desde el norte.
    
    Args:
        lat1, lon1: Coordenadas del punto de origen (grados)
        lat2, lon2: Coordenadas del punto de destino (grados)
        
    Returns:
        Azimut en grados (0-360)
        
    Example:
        >>> calcular_azimut(19.24, -103.72, 19.43, -99.13)
        78.5  # Aproximadamente hacia el este-noreste
    """
    lat1_rad = lat1 * DEG_TO_RAD
    lat2_rad = lat2 * DEG_TO_RAD
    dlon = (lon2 - lon1) * DEG_TO_RAD
    
    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    
    azimut = math.atan2(x, y) * RAD_TO_DEG
    
    # Normalizar a 0-360
    return (azimut + 360) % 360


def calcular_rumbo(azimut: float) -> str:
    """
    Convierte un azimut a rumbo cardinal.
    
    Args:
        azimut: Azimut en grados (0-360)
        
    Returns:
        Rumbo cardinal (N, NE, E, SE, S, SW, W, NW)
    """
    rumbos = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    indice = round(azimut / 45) % 8
    return rumbos[indice]


def punto_destino(
    lat: float,
    lon: float,
    distancia_km: float,
    azimut: float
) -> Tuple[float, float]:
    """
    Calcula las coordenadas del punto destino dado un origen, distancia y azimut.
    
    Args:
        lat, lon: Coordenadas del punto de origen (grados)
        distancia_km: Distancia al destino en km
        azimut: Dirección en grados (0-360, medido desde el norte)
        
    Returns:
        Tupla (latitud, longitud) del punto destino
    """
    lat_rad = lat * DEG_TO_RAD
    lon_rad = lon * DEG_TO_RAD
    azimut_rad = azimut * DEG_TO_RAD
    
    angular_distance = distancia_km / RADIO_TIERRA_KM
    
    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance) +
        math.cos(lat_rad) * math.sin(angular_distance) * math.cos(azimut_rad)
    )
    
    lon2 = lon_rad + math.atan2(
        math.sin(azimut_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(lat2)
    )
    
    return lat2 * RAD_TO_DEG, lon2 * RAD_TO_DEG


# =============================================================================
# POLÍGONOS Y REGIONES
# =============================================================================

def punto_en_poligono(
    lat: float,
    lon: float,
    poligono: Sequence[Tuple[float, float]]
) -> bool:
    """
    Verifica si un punto está dentro de un polígono (ray casting).
    
    Args:
        lat, lon: Coordenadas del punto a verificar
        poligono: Lista de tuplas (lat, lon) definiendo el polígono
                  (debe estar cerrado, primer punto = último punto)
        
    Returns:
        True si el punto está dentro del polígono
        
    Example:
        >>> poligono = [(18.0, -105.0), (20.0, -105.0), (20.0, -103.0), 
        ...             (18.0, -103.0), (18.0, -105.0)]
        >>> punto_en_poligono(19.0, -104.0, poligono)
        True
    """
    n = len(poligono)
    dentro = False
    
    j = n - 1
    for i in range(n):
        yi, xi = poligono[i]
        yj, xj = poligono[j]
        
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            dentro = not dentro
        j = i
    
    return dentro


def puntos_en_poligono_vectorizado(
    lats: np.ndarray,
    lons: np.ndarray,
    poligono: Sequence[Tuple[float, float]]
) -> np.ndarray:
    """
    Versión vectorizada de punto_en_poligono.
    
    Args:
        lats: Array de latitudes
        lons: Array de longitudes
        poligono: Lista de tuplas (lat, lon)
        
    Returns:
        Array booleano indicando qué puntos están dentro
    """
    n_puntos = len(lats)
    dentro = np.zeros(n_puntos, dtype=bool)
    
    for i in range(n_puntos):
        dentro[i] = punto_en_poligono(lats[i], lons[i], poligono)
    
    return dentro


def crear_rectangulo(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float
) -> List[Tuple[float, float]]:
    """
    Crea un polígono rectangular a partir de límites.
    
    Args:
        lat_min, lat_max: Rango de latitudes
        lon_min, lon_max: Rango de longitudes
        
    Returns:
        Lista de tuplas (lat, lon) formando un rectángulo cerrado
    """
    return [
        (lat_min, lon_min),
        (lat_min, lon_max),
        (lat_max, lon_max),
        (lat_max, lon_min),
        (lat_min, lon_min)  # Cerrar polígono
    ]


def crear_circulo(
    lat_centro: float,
    lon_centro: float,
    radio_km: float,
    n_puntos: int = 36
) -> List[Tuple[float, float]]:
    """
    Crea un polígono circular aproximado.
    
    Args:
        lat_centro, lon_centro: Centro del círculo
        radio_km: Radio en kilómetros
        n_puntos: Número de puntos del polígono
        
    Returns:
        Lista de tuplas (lat, lon) formando un círculo aproximado
    """
    puntos = []
    for i in range(n_puntos + 1):
        azimut = 360 * i / n_puntos
        lat, lon = punto_destino(lat_centro, lon_centro, radio_km, azimut)
        puntos.append((lat, lon))
    return puntos


# =============================================================================
# GRILLAS Y MALLAS
# =============================================================================

@dataclass
class Grilla:
    """Representa una grilla regular de puntos."""
    lats: np.ndarray
    lons: np.ndarray
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    paso_lat: float
    paso_lon: float
    n_filas: int
    n_columnas: int
    
    @property
    def n_puntos(self) -> int:
        """Número total de puntos en la grilla."""
        return self.n_filas * self.n_columnas
    
    def meshgrid(self) -> Tuple[np.ndarray, np.ndarray]:
        """Retorna matrices 2D de coordenadas (para plotting)."""
        return np.meshgrid(self.lons, self.lats)
    
    def puntos_planos(self) -> Tuple[np.ndarray, np.ndarray]:
        """Retorna arrays 1D de todas las coordenadas."""
        lon_grid, lat_grid = self.meshgrid()
        return lat_grid.flatten(), lon_grid.flatten()


def crear_grilla_regular(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    paso: float = 0.1,
    paso_lat: Optional[float] = None,
    paso_lon: Optional[float] = None
) -> Grilla:
    """
    Crea una grilla regular de puntos.
    
    Args:
        lat_min, lat_max: Rango de latitudes
        lon_min, lon_max: Rango de longitudes
        paso: Paso en grados (se usa para lat y lon si no se especifican)
        paso_lat: Paso específico para latitud
        paso_lon: Paso específico para longitud
        
    Returns:
        Objeto Grilla con las coordenadas
        
    Example:
        >>> grilla = crear_grilla_regular(18.5, 20.0, -104.5, -103.0, paso=0.1)
        >>> print(f"Puntos: {grilla.n_puntos}")
    """
    paso_lat = paso_lat or paso
    paso_lon = paso_lon or paso
    
    lats = np.arange(lat_min, lat_max + paso_lat/2, paso_lat)
    lons = np.arange(lon_min, lon_max + paso_lon/2, paso_lon)
    
    return Grilla(
        lats=lats,
        lons=lons,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        paso_lat=paso_lat,
        paso_lon=paso_lon,
        n_filas=len(lats),
        n_columnas=len(lons)
    )


def crear_grilla_km(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    paso_km: float = 10.0
) -> Grilla:
    """
    Crea una grilla con espaciado en kilómetros.
    
    El paso en grados se ajusta según la latitud central.
    
    Args:
        lat_min, lat_max: Rango de latitudes
        lon_min, lon_max: Rango de longitudes
        paso_km: Paso en kilómetros
        
    Returns:
        Objeto Grilla
    """
    lat_centro = (lat_min + lat_max) / 2
    
    # Convertir km a grados
    paso_lat = paso_km / DEG_TO_KM_LAT
    paso_lon = paso_km / (DEG_TO_KM_LON_ECUADOR * math.cos(lat_centro * DEG_TO_RAD))
    
    return crear_grilla_regular(
        lat_min, lat_max, lon_min, lon_max,
        paso_lat=paso_lat, paso_lon=paso_lon
    )


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def normalizar_longitud(lon: float) -> float:
    """
    Normaliza una longitud al rango [-180, 180].
    
    Args:
        lon: Longitud en grados
        
    Returns:
        Longitud normalizada
    """
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


def grados_a_km(grados: float, latitud: float = 0) -> float:
    """
    Convierte grados a kilómetros (aproximado).
    
    Args:
        grados: Distancia en grados
        latitud: Latitud de referencia (para ajuste por coseno)
        
    Returns:
        Distancia en km
    """
    factor = DEG_TO_KM_LAT * math.cos(latitud * DEG_TO_RAD)
    return grados * factor


def km_a_grados(km: float, latitud: float = 0) -> float:
    """
    Convierte kilómetros a grados (aproximado).
    
    Args:
        km: Distancia en kilómetros
        latitud: Latitud de referencia
        
    Returns:
        Distancia en grados
    """
    factor = DEG_TO_KM_LAT * math.cos(latitud * DEG_TO_RAD)
    return km / factor


def calcular_area_region(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float
) -> float:
    """
    Calcula el área aproximada de una región rectangular en km².
    
    Args:
        lat_min, lat_max: Rango de latitudes
        lon_min, lon_max: Rango de longitudes
        
    Returns:
        Área en km²
    """
    lat_centro = (lat_min + lat_max) / 2
    
    altura_km = (lat_max - lat_min) * DEG_TO_KM_LAT
    ancho_km = (lon_max - lon_min) * DEG_TO_KM_LON_ECUADOR * math.cos(lat_centro * DEG_TO_RAD)
    
    return altura_km * ancho_km


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("SEISMEX Utils - Ejemplos de uso de geo.py")
    print("=" * 60)
    
    # Ejemplo 1: Distancias
    print("\n--- Distancias ---")
    dist_haversine = calcular_distancia_haversine(19.24, -103.72, 19.43, -99.13)
    dist_vincenty = calcular_distancia_vincenty(19.24, -103.72, 19.43, -99.13)
    print(f"Colima a CDMX (Haversine): {dist_haversine:.2f} km")
    print(f"Colima a CDMX (Vincenty): {dist_vincenty:.2f} km")
    
    # Ejemplo 2: UTM
    print("\n--- Conversión UTM ---")
    e, n, zona, hem = convertir_latlon_a_utm(19.24, -103.72)
    print(f"Colima en UTM: {e:.2f} E, {n:.2f} N, Zona {zona}{hem}")
    
    lat_back, lon_back = convertir_utm_a_latlon(e, n, zona, hem)
    print(f"Reconversión: {lat_back:.4f}, {lon_back:.4f}")
    
    # Ejemplo 3: Azimut
    print("\n--- Azimut ---")
    azimut = calcular_azimut(19.24, -103.72, 19.43, -99.13)
    rumbo = calcular_rumbo(azimut)
    print(f"Azimut Colima→CDMX: {azimut:.1f}° ({rumbo})")
    
    # Ejemplo 4: Grilla
    print("\n--- Grilla ---")
    grilla = crear_grilla_regular(18.5, 20.0, -104.5, -103.0, paso=0.1)
    print(f"Grilla: {grilla.n_filas} x {grilla.n_columnas} = {grilla.n_puntos} puntos")
    
    # Ejemplo 5: Área
    print("\n--- Área ---")
    area = calcular_area_region(18.5, 20.0, -104.5, -103.0)
    print(f"Área región Colima: {area:.2f} km²")
    
    print("\n✓ Todos los ejemplos ejecutados correctamente")
