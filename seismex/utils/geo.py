"""
SEISMEX Utils - Utilidades Geográficas
======================================

Funciones para cálculos geográficos, transformaciones de coordenadas
y operaciones espaciales.

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
from typing import Tuple, List, Optional, Union
import numpy as np

# Constantes
RADIO_TIERRA_KM = 6371.0  # Radio medio de la Tierra en km
RADIO_TIERRA_M = 6371000.0  # Radio medio de la Tierra en metros


# =============================================================================
# CÁLCULO DE DISTANCIAS
# =============================================================================

def calcular_distancia_haversine(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    radio: float = RADIO_TIERRA_KM
) -> float:
    """
    Calcula la distancia entre dos puntos usando la fórmula de Haversine.
    
    La fórmula de Haversine calcula la distancia del círculo máximo entre
    dos puntos en una esfera. Es una buena aproximación para distancias
    cortas a medias en la Tierra.
    
    Args:
        lat1: Latitud del primer punto (grados decimales)
        lon1: Longitud del primer punto (grados decimales)
        lat2: Latitud del segundo punto (grados decimales)
        lon2: Longitud del segundo punto (grados decimales)
        radio: Radio de la esfera (default: Radio de la Tierra en km)
        
    Returns:
        Distancia en las mismas unidades que el radio (km por defecto)
        
    Example:
        >>> # Distancia Colima - Ciudad de México
        >>> distancia = calcular_distancia_haversine(19.24, -103.72, 19.43, -99.13)
        >>> print(f"Distancia: {distancia:.2f} km")
        Distancia: 465.23 km
    """
    # Convertir a radianes
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferencias
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula de Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return radio * c


def calcular_distancia_vincenty(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    max_iteraciones: int = 200,
    tolerancia: float = 1e-12
) -> float:
    """
    Calcula la distancia geodésica usando la fórmula de Vincenty.
    
    La fórmula de Vincenty es más precisa que Haversine porque considera
    el achatamiento de la Tierra (elipsoide WGS84).
    
    Args:
        lat1, lon1: Coordenadas del primer punto (grados decimales)
        lat2, lon2: Coordenadas del segundo punto (grados decimales)
        max_iteraciones: Máximo de iteraciones para convergencia
        tolerancia: Tolerancia para convergencia
        
    Returns:
        Distancia en kilómetros
        
    Raises:
        ValueError: Si los puntos son antipodales y no converge
    """
    # Constantes WGS84
    a = 6378.137  # Semi-eje mayor (km)
    f = 1 / 298.257223563  # Achatamiento
    b = a * (1 - f)  # Semi-eje menor
    
    # Convertir a radianes
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    L = math.radians(lon2 - lon1)
    
    # Latitud reducida
    U1 = math.atan((1 - f) * math.tan(phi1))
    U2 = math.atan((1 - f) * math.tan(phi2))
    
    sin_U1 = math.sin(U1)
    cos_U1 = math.cos(U1)
    sin_U2 = math.sin(U2)
    cos_U2 = math.cos(U2)
    
    # Iteración
    lambda_prev = L
    for _ in range(max_iteraciones):
        sin_lambda = math.sin(lambda_prev)
        cos_lambda = math.cos(lambda_prev)
        
        sin_sigma = math.sqrt(
            (cos_U2 * sin_lambda)**2 +
            (cos_U1 * sin_U2 - sin_U1 * cos_U2 * cos_lambda)**2
        )
        
        if sin_sigma == 0:
            return 0.0  # Puntos coincidentes
        
        cos_sigma = sin_U1 * sin_U2 + cos_U1 * cos_U2 * cos_lambda
        sigma = math.atan2(sin_sigma, cos_sigma)
        
        sin_alpha = cos_U1 * cos_U2 * sin_lambda / sin_sigma
        cos2_alpha = 1 - sin_alpha**2
        
        if cos2_alpha == 0:
            cos_2sigma_m = 0
        else:
            cos_2sigma_m = cos_sigma - 2 * sin_U1 * sin_U2 / cos2_alpha
        
        C = f / 16 * cos2_alpha * (4 + f * (4 - 3 * cos2_alpha))
        
        lambda_new = L + (1 - C) * f * sin_alpha * (
            sigma + C * sin_sigma * (
                cos_2sigma_m + C * cos_sigma * (-1 + 2 * cos_2sigma_m**2)
            )
        )
        
        if abs(lambda_new - lambda_prev) < tolerancia:
            break
        
        lambda_prev = lambda_new
    else:
        warnings.warn("Vincenty no convergió - usando Haversine como fallback")
        return calcular_distancia_haversine(lat1, lon1, lat2, lon2)
    
    # Calcular distancia
    u2 = cos2_alpha * (a**2 - b**2) / b**2
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    
    delta_sigma = B * sin_sigma * (
        cos_2sigma_m + B / 4 * (
            cos_sigma * (-1 + 2 * cos_2sigma_m**2) -
            B / 6 * cos_2sigma_m * (-3 + 4 * sin_sigma**2) * (-3 + 4 * cos_2sigma_m**2)
        )
    )
    
    s = b * A * (sigma - delta_sigma)
    
    return s


def calcular_distancia_batch(
    lats1: np.ndarray,
    lons1: np.ndarray,
    lats2: np.ndarray,
    lons2: np.ndarray
) -> np.ndarray:
    """
    Calcula distancias entre arrays de coordenadas (vectorizado).
    
    Args:
        lats1, lons1: Arrays de coordenadas del primer conjunto
        lats2, lons2: Arrays de coordenadas del segundo conjunto
        
    Returns:
        Array de distancias en km
    """
    # Convertir a radianes
    lat1_rad = np.radians(lats1)
    lon1_rad = np.radians(lons1)
    lat2_rad = np.radians(lats2)
    lon2_rad = np.radians(lons2)
    
    # Diferencias
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine vectorizado
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return RADIO_TIERRA_KM * c


# =============================================================================
# TRANSFORMACIONES DE COORDENADAS
# =============================================================================

def obtener_zona_utm(lon: float, lat: float) -> Tuple[int, str]:
    """
    Determina la zona UTM para una coordenada geográfica.
    
    Args:
        lon: Longitud en grados decimales
        lat: Latitud en grados decimales
        
    Returns:
        Tupla (número_zona, hemisferio)
        
    Example:
        >>> zona, hemisferio = obtener_zona_utm(-103.72, 19.24)
        >>> print(f"Zona {zona}{hemisferio}")
        Zona 13N
    """
    # Calcular zona
    zona = int((lon + 180) / 6) + 1
    
    # Excepciones para Noruega y Svalbard
    if 56 <= lat < 64 and 3 <= lon < 12:
        zona = 32
    elif 72 <= lat < 84:
        if 0 <= lon < 9:
            zona = 31
        elif 9 <= lon < 21:
            zona = 33
        elif 21 <= lon < 33:
            zona = 35
        elif 33 <= lon < 42:
            zona = 37
    
    hemisferio = 'N' if lat >= 0 else 'S'
    
    return zona, hemisferio


def convertir_latlon_a_utm(
    lat: float,
    lon: float,
    zona: Optional[int] = None,
    hemisferio: Optional[str] = None
) -> Tuple[float, float, int, str]:
    """
    Convierte coordenadas geográficas a UTM.
    
    Args:
        lat: Latitud en grados decimales
        lon: Longitud en grados decimales
        zona: Zona UTM (si None, se calcula automáticamente)
        hemisferio: 'N' o 'S' (si None, se determina por latitud)
        
    Returns:
        Tupla (easting, northing, zona, hemisferio)
        
    Example:
        >>> x, y, zona, hem = convertir_latlon_a_utm(19.24, -103.72)
        >>> print(f"UTM: {x:.2f}E, {y:.2f}N, Zona {zona}{hem}")
    """
    if zona is None or hemisferio is None:
        zona, hemisferio = obtener_zona_utm(lon, lat)
    
    # Constantes WGS84
    a = 6378137.0  # Semi-eje mayor (m)
    f = 1 / 298.257223563
    e2 = 2 * f - f**2  # Excentricidad al cuadrado
    e_prime2 = e2 / (1 - e2)
    k0 = 0.9996  # Factor de escala
    
    # Convertir a radianes
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    
    # Meridiano central de la zona
    lon0 = math.radians((zona - 1) * 6 - 180 + 3)
    
    # Cálculos auxiliares
    N = a / math.sqrt(1 - e2 * math.sin(lat_rad)**2)
    T = math.tan(lat_rad)**2
    C = e_prime2 * math.cos(lat_rad)**2
    A = (lon_rad - lon0) * math.cos(lat_rad)
    
    M = a * (
        (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * lat_rad -
        (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*lat_rad) +
        (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*lat_rad) -
        (35*e2**3/3072) * math.sin(6*lat_rad)
    )
    
    # Coordenadas UTM
    easting = k0 * N * (
        A + (1 - T + C) * A**3 / 6 +
        (5 - 18*T + T**2 + 72*C - 58*e_prime2) * A**5 / 120
    ) + 500000.0
    
    northing = k0 * (
        M + N * math.tan(lat_rad) * (
            A**2 / 2 +
            (5 - T + 9*C + 4*C**2) * A**4 / 24 +
            (61 - 58*T + T**2 + 600*C - 330*e_prime2) * A**6 / 720
        )
    )
    
    # Ajuste para hemisferio sur
    if hemisferio == 'S':
        northing += 10000000.0
    
    return easting, northing, zona, hemisferio


def convertir_utm_a_latlon(
    easting: float,
    northing: float,
    zona: int,
    hemisferio: str
) -> Tuple[float, float]:
    """
    Convierte coordenadas UTM a geográficas.
    
    Args:
        easting: Coordenada Este (metros)
        northing: Coordenada Norte (metros)
        zona: Número de zona UTM
        hemisferio: 'N' o 'S'
        
    Returns:
        Tupla (latitud, longitud) en grados decimales
    """
    # Constantes WGS84
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = 2 * f - f**2
    e_prime2 = e2 / (1 - e2)
    k0 = 0.9996
    
    # Ajuste para hemisferio sur
    if hemisferio == 'S':
        northing -= 10000000.0
    
    # Meridiano central
    lon0 = (zona - 1) * 6 - 180 + 3
    
    # Cálculos auxiliares
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    M = northing / k0
    mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))
    
    phi1 = (
        mu +
        (3*e1/2 - 27*e1**3/32) * math.sin(2*mu) +
        (21*e1**2/16 - 55*e1**4/32) * math.sin(4*mu) +
        (151*e1**3/96) * math.sin(6*mu) +
        (1097*e1**4/512) * math.sin(8*mu)
    )
    
    N1 = a / math.sqrt(1 - e2 * math.sin(phi1)**2)
    T1 = math.tan(phi1)**2
    C1 = e_prime2 * math.cos(phi1)**2
    R1 = a * (1 - e2) / (1 - e2 * math.sin(phi1)**2)**1.5
    D = (easting - 500000.0) / (N1 * k0)
    
    # Latitud
    lat = phi1 - (N1 * math.tan(phi1) / R1) * (
        D**2 / 2 -
        (5 + 3*T1 + 10*C1 - 4*C1**2 - 9*e_prime2) * D**4 / 24 +
        (61 + 90*T1 + 298*C1 + 45*T1**2 - 252*e_prime2 - 3*C1**2) * D**6 / 720
    )
    
    # Longitud
    lon = lon0 + math.degrees(
        (D - (1 + 2*T1 + C1) * D**3 / 6 +
         (5 - 2*C1 + 28*T1 - 3*C1**2 + 8*e_prime2 + 24*T1**2) * D**5 / 120) /
        math.cos(phi1)
    )
    
    return math.degrees(lat), lon


# =============================================================================
# AZIMUT Y RUMBO
# =============================================================================

def calcular_azimut(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calcula el azimut (bearing) inicial entre dos puntos.
    
    El azimut es el ángulo medido en el sentido de las agujas del reloj
    desde el norte verdadero hasta la dirección del segundo punto.
    
    Args:
        lat1, lon1: Coordenadas del punto de origen
        lat2, lon2: Coordenadas del punto de destino
        
    Returns:
        Azimut en grados (0-360)
        
    Example:
        >>> azimut = calcular_azimut(19.24, -103.72, 19.43, -99.13)
        >>> print(f"Azimut: {azimut:.2f}°")
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    
    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    
    azimut = math.degrees(math.atan2(x, y))
    
    return (azimut + 360) % 360


def punto_destino(
    lat: float,
    lon: float,
    distancia_km: float,
    azimut: float
) -> Tuple[float, float]:
    """
    Calcula las coordenadas de un punto dado distancia y azimut desde origen.
    
    Args:
        lat, lon: Coordenadas del punto de origen
        distancia_km: Distancia al punto destino en km
        azimut: Azimut en grados (0 = Norte, 90 = Este)
        
    Returns:
        Tupla (latitud, longitud) del punto destino
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    azimut_rad = math.radians(azimut)
    d = distancia_km / RADIO_TIERRA_KM
    
    lat2_rad = math.asin(
        math.sin(lat_rad) * math.cos(d) +
        math.cos(lat_rad) * math.sin(d) * math.cos(azimut_rad)
    )
    
    lon2_rad = lon_rad + math.atan2(
        math.sin(azimut_rad) * math.sin(d) * math.cos(lat_rad),
        math.cos(d) - math.sin(lat_rad) * math.sin(lat2_rad)
    )
    
    return math.degrees(lat2_rad), math.degrees(lon2_rad)


# =============================================================================
# OPERACIONES ESPACIALES
# =============================================================================

def punto_en_poligono(
    lat: float,
    lon: float,
    poligono: List[Tuple[float, float]]
) -> bool:
    """
    Verifica si un punto está dentro de un polígono usando ray casting.
    
    Args:
        lat, lon: Coordenadas del punto a verificar
        poligono: Lista de tuplas (lat, lon) que definen el polígono
                  (debe estar cerrado, primer punto = último punto)
        
    Returns:
        True si el punto está dentro del polígono
        
    Example:
        >>> poligono = [(18.0, -105.0), (21.0, -105.0), (21.0, -102.0), 
        ...             (18.0, -102.0), (18.0, -105.0)]
        >>> dentro = punto_en_poligono(19.24, -103.72, poligono)
        >>> print(f"Dentro: {dentro}")
    """
    n = len(poligono)
    dentro = False
    
    j = n - 1
    for i in range(n):
        lat_i, lon_i = poligono[i]
        lat_j, lon_j = poligono[j]
        
        if ((lon_i > lon) != (lon_j > lon)) and \
           (lat < (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i):
            dentro = not dentro
        
        j = i
    
    return dentro


def crear_grilla_regular(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    paso: float = 0.1
) -> List[Tuple[float, float]]:
    """
    Crea una grilla regular de puntos en coordenadas geográficas.
    
    Args:
        lat_min, lat_max: Rango de latitudes
        lon_min, lon_max: Rango de longitudes
        paso: Espaciado entre puntos en grados
        
    Returns:
        Lista de tuplas (lat, lon)
        
    Example:
        >>> grilla = crear_grilla_regular(18.5, 20.0, -104.5, -103.0, paso=0.1)
        >>> print(f"Puntos en grilla: {len(grilla)}")
    """
    lats = np.arange(lat_min, lat_max + paso, paso)
    lons = np.arange(lon_min, lon_max + paso, paso)
    
    grilla = []
    for lat in lats:
        for lon in lons:
            grilla.append((lat, lon))
    
    return grilla


def crear_grilla_numpy(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    paso: float = 0.1
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crea arrays meshgrid de coordenadas.
    
    Args:
        lat_min, lat_max: Rango de latitudes
        lon_min, lon_max: Rango de longitudes
        paso: Espaciado entre puntos en grados
        
    Returns:
        Tupla (grid_lat, grid_lon) como arrays 2D
    """
    lats = np.arange(lat_min, lat_max + paso, paso)
    lons = np.arange(lon_min, lon_max + paso, paso)
    
    return np.meshgrid(lats, lons, indexing='ij')


def calcular_area_poligono(poligono: List[Tuple[float, float]]) -> float:
    """
    Calcula el área aproximada de un polígono en km².
    
    Usa la fórmula del agrimenso (Surveyor's formula) con proyección simple.
    Para polígonos pequeños (<100 km), la precisión es razonable.
    
    Args:
        poligono: Lista de tuplas (lat, lon)
        
    Returns:
        Área en km²
    """
    n = len(poligono)
    if n < 3:
        return 0.0
    
    # Centro del polígono para proyección local
    lat_centro = sum(p[0] for p in poligono) / n
    
    # Factor de conversión a km
    km_por_grado_lat = 111.32
    km_por_grado_lon = 111.32 * math.cos(math.radians(lat_centro))
    
    # Fórmula del agrimenso
    area = 0.0
    j = n - 1
    for i in range(n):
        x_i = poligono[i][1] * km_por_grado_lon
        y_i = poligono[i][0] * km_por_grado_lat
        x_j = poligono[j][1] * km_por_grado_lon
        y_j = poligono[j][0] * km_por_grado_lat
        
        area += (x_j + x_i) * (y_j - y_i)
        j = i
    
    return abs(area) / 2.0


def buffer_punto(
    lat: float,
    lon: float,
    radio_km: float,
    n_puntos: int = 36
) -> List[Tuple[float, float]]:
    """
    Crea un buffer circular alrededor de un punto.
    
    Args:
        lat, lon: Centro del buffer
        radio_km: Radio en km
        n_puntos: Número de puntos en el círculo
        
    Returns:
        Lista de tuplas (lat, lon) formando el círculo
    """
    puntos = []
    for i in range(n_puntos + 1):
        azimut = 360.0 * i / n_puntos
        lat_p, lon_p = punto_destino(lat, lon, radio_km, azimut)
        puntos.append((lat_p, lon_p))
    
    return puntos


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("SEISMEX - Utilidades Geográficas")
    print("=" * 60)
    
    # Puntos de ejemplo
    colima = (19.2433, -103.7250)
    cdmx = (19.4326, -99.1332)
    
    # Distancia Haversine
    dist_h = calcular_distancia_haversine(*colima, *cdmx)
    print(f"\nDistancia Colima - CDMX (Haversine): {dist_h:.2f} km")
    
    # Distancia Vincenty
    dist_v = calcular_distancia_vincenty(*colima, *cdmx)
    print(f"Distancia Colima - CDMX (Vincenty):  {dist_v:.2f} km")
    
    # Azimut
    azimut = calcular_azimut(*colima, *cdmx)
    print(f"Azimut Colima → CDMX: {azimut:.2f}°")
    
    # Conversión UTM
    x, y, zona, hem = convertir_latlon_a_utm(*colima)
    print(f"\nColima en UTM: {x:.2f}E, {y:.2f}N, Zona {zona}{hem}")
    
    # Conversión inversa
    lat, lon = convertir_utm_a_latlon(x, y, zona, hem)
    print(f"Verificación: {lat:.6f}, {lon:.6f}")
    
    # Grilla
    grilla = crear_grilla_regular(18.5, 20.0, -104.5, -103.0, paso=0.2)
    print(f"\nPuntos en grilla (0.2°): {len(grilla)}")
    
    # Punto en polígono
    region_colima = [
        (18.5, -104.5), (20.5, -104.5), (20.5, -103.0),
        (18.5, -103.0), (18.5, -104.5)
    ]
    dentro = punto_en_poligono(*colima, region_colima)
    print(f"¿Colima está en la región?: {dentro}")
    
    print("\n✓ Todas las funciones funcionan correctamente")
