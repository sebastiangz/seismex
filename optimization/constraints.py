#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Optimization - Restricciones
================================================================================

Restricciones completas para optimización de ubicación de infraestructura.

Las restricciones retornan:
    - 0.0 si se cumple la restricción (factible)
    - > 0.0 valor de violación (no factible)

Restricciones disponibles:
    - restriccion_uso_suelo: Limitar a zonas con uso permitido
    - restriccion_pendiente: Pendiente máxima del terreno
    - restriccion_zona_inundable: Evitar zonas inundables
    - restriccion_distancia_minima: Distancia mínima entre sitios
    - restriccion_capacidad: Límites de capacidad del terreno
    - restriccion_zona_protegida: Evitar áreas naturales protegidas
    - restriccion_buffer_fallas: Buffer de seguridad alrededor de fallas
    - restriccion_elevacion: Rango de elevación permitido
    - restriccion_region: Limitar a región de estudio

Estado: ✅ IMPLEMENTADO

Autor: SEISMEX Team
Versión: 1.0.0
================================================================================
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    List, 
    Tuple, 
    Optional, 
    Callable, 
    Dict, 
    Any,
    Union,
    Set,
    TYPE_CHECKING
)
from enum import Enum
import numpy as np

if TYPE_CHECKING:
    import geopandas as gpd
    from shapely.geometry import Point, Polygon

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

RADIO_TIERRA_KM = 6371.0


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoRestriccion(Enum):
    """Tipos de restricción."""
    IGUALDAD = "igualdad"      # g(x) = 0
    DESIGUALDAD = "desigualdad"  # g(x) <= 0


class SeveridadRestriccion(Enum):
    """Severidad de la restricción."""
    OBLIGATORIA = "obligatoria"  # Debe cumplirse siempre
    PREFERENCIA = "preferencia"   # Penalización suave si no se cumple


class CategoriaRestriccion(Enum):
    """Categorías de restricciones."""
    GEOGRAFICA = "geografica"
    GEOLOGICA = "geologica"
    AMBIENTAL = "ambiental"
    LEGAL = "legal"
    TECNICA = "tecnica"
    ESPACIAL = "espacial"


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def distancia_haversine(
    lat1: float, lon1: float, 
    lat2: float, lon2: float
) -> float:
    """
    Calcula la distancia entre dos puntos usando la fórmula de Haversine.
    
    Returns
    -------
    float
        Distancia en kilómetros
    """
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = (np.sin(dlat / 2) ** 2 + 
         np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return RADIO_TIERRA_KM * c


def interpolar_raster(
    lat: float, lon: float,
    raster: np.ndarray,
    bounds: Tuple[float, float, float, float],
    nodata: float = np.nan
) -> float:
    """
    Interpola un valor de un raster en las coordenadas dadas.
    
    Parameters
    ----------
    lat, lon : float
        Coordenadas del punto
    raster : np.ndarray
        Array 2D con los valores
    bounds : Tuple[float, float, float, float]
        Límites (lon_min, lat_min, lon_max, lat_max)
    nodata : float
        Valor para datos faltantes
        
    Returns
    -------
    float
        Valor interpolado
    """
    lon_min, lat_min, lon_max, lat_max = bounds
    nrows, ncols = raster.shape
    
    if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
        return nodata
    
    col = int((lon - lon_min) / (lon_max - lon_min) * (ncols - 1))
    row = int((lat_max - lat) / (lat_max - lat_min) * (nrows - 1))
    
    row = np.clip(row, 0, nrows - 1)
    col = np.clip(col, 0, ncols - 1)
    
    valor = raster[row, col]
    
    if np.isnan(valor) or valor == nodata:
        return nodata
    
    return valor


def punto_en_poligono(
    lat: float, lon: float,
    poligono_coords: List[Tuple[float, float]]
) -> bool:
    """
    Verifica si un punto está dentro de un polígono usando ray casting.
    
    Parameters
    ----------
    lat, lon : float
        Coordenadas del punto
    poligono_coords : List[Tuple[float, float]]
        Lista de coordenadas del polígono [(lat, lon), ...]
        
    Returns
    -------
    bool
        True si el punto está dentro del polígono
    """
    n = len(poligono_coords)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = poligono_coords[i]
        xj, yj = poligono_coords[j]
        
        if ((yi > lon) != (yj > lon)) and \
           (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


def distancia_punto_a_linea(
    lat: float, lon: float,
    linea: List[Tuple[float, float]]
) -> float:
    """
    Calcula la distancia mínima de un punto a una línea.
    
    Parameters
    ----------
    lat, lon : float
        Coordenadas del punto
    linea : List[Tuple[float, float]]
        Lista de puntos que forman la línea
        
    Returns
    -------
    float
        Distancia mínima en kilómetros
    """
    distancia_min = float('inf')
    
    for i in range(len(linea) - 1):
        lat1, lon1 = linea[i]
        lat2, lon2 = linea[i + 1]
        
        # Distancia al segmento (simplificada usando distancia a puntos)
        d1 = distancia_haversine(lat, lon, lat1, lon1)
        d2 = distancia_haversine(lat, lon, lat2, lon2)
        
        distancia_min = min(distancia_min, d1, d2)
    
    return distancia_min


# =============================================================================
# CLASE BASE
# =============================================================================

@dataclass
class Restriccion(ABC):
    """
    Clase base abstracta para restricciones.
    
    Las restricciones evalúan si una solución es factible.
    Retornan 0 si se cumple, o un valor positivo indicando la violación.
    
    Attributes
    ----------
    nombre : str
        Nombre descriptivo de la restricción
    tipo : TipoRestriccion
        Tipo de restricción (igualdad/desigualdad)
    severidad : SeveridadRestriccion
        Severidad de la restricción
    categoria : CategoriaRestriccion
        Categoría de la restricción
    descripcion : str
        Descripción detallada
    """
    nombre: str
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    severidad: SeveridadRestriccion = SeveridadRestriccion.OBLIGATORIA
    categoria: CategoriaRestriccion = CategoriaRestriccion.TECNICA
    descripcion: str = ""
    
    @abstractmethod
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa la restricción para las coordenadas dadas.
        
        Parameters
        ----------
        coordenadas : List[Tuple[float, float]]
            Lista de tuplas (latitud, longitud) de los sitios
            
        Returns
        -------
        float
            0.0 si se cumple, > 0.0 indica magnitud de violación
        """
        pass
    
    def __call__(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Permite usar la instancia como función."""
        return self.evaluar(coordenadas)
    
    def es_factible(self, coordenadas: List[Tuple[float, float]]) -> bool:
        """Verifica si las coordenadas cumplen la restricción."""
        return self.evaluar(coordenadas) <= 0.0


# =============================================================================
# RESTRICCIÓN: USO DE SUELO
# =============================================================================

@dataclass
class RestriccionUsoSuelo(Restriccion):
    """
    Limita la ubicación a zonas con uso de suelo permitido.
    
    Attributes
    ----------
    mapa_uso_suelo : np.ndarray
        Grilla con códigos de uso de suelo
    bounds : Tuple[float, float, float, float]
        Límites del mapa
    usos_permitidos : Set[int]
        Códigos de uso de suelo permitidos
    penalizacion_no_permitido : float
        Penalización por ubicarse en zona no permitida
    """
    nombre: str = "Uso de Suelo"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.LEGAL
    descripcion: str = "Limita ubicación a zonas con uso de suelo permitido"
    
    mapa_uso_suelo: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    usos_permitidos: Set[int] = field(default_factory=lambda: {1, 2, 3})
    penalizacion_no_permitido: float = 100.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si los sitios están en zonas con uso permitido."""
        if self.mapa_uso_suelo is None or self.bounds is None:
            return 0.0
        
        violacion = 0.0
        
        for lat, lon in coordenadas:
            uso = interpolar_raster(lat, lon, self.mapa_uso_suelo, self.bounds, nodata=-1)
            uso_int = int(round(uso)) if not np.isnan(uso) else -1
            
            if uso_int not in self.usos_permitidos:
                violacion += self.penalizacion_no_permitido
        
        return violacion


def restriccion_uso_suelo(
    mapa_uso_suelo: np.ndarray,
    bounds: Tuple[float, float, float, float],
    usos_permitidos: Optional[Set[int]] = None,
    penalizacion: float = 100.0
) -> RestriccionUsoSuelo:
    """Factory function para restricción de uso de suelo."""
    return RestriccionUsoSuelo(
        mapa_uso_suelo=mapa_uso_suelo,
        bounds=bounds,
        usos_permitidos=usos_permitidos or {1, 2, 3},
        penalizacion_no_permitido=penalizacion
    )


# =============================================================================
# RESTRICCIÓN: PENDIENTE MÁXIMA
# =============================================================================

@dataclass
class RestriccionPendiente(Restriccion):
    """
    Limita la pendiente máxima del terreno.
    
    Attributes
    ----------
    dem : np.ndarray
        Modelo Digital de Elevación
    bounds : Tuple[float, float, float, float]
        Límites del DEM
    pendiente_maxima : float
        Pendiente máxima permitida en grados
    resolucion : float
        Resolución del DEM en metros
    pendiente_cache : np.ndarray
        Grilla de pendientes pre-calculada
    """
    nombre: str = "Pendiente Máxima"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.TECNICA
    descripcion: str = "Limita la pendiente máxima del terreno"
    
    dem: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    pendiente_maxima: float = 15.0  # grados
    resolucion: float = 30.0  # metros
    pendiente_cache: Optional[np.ndarray] = None
    
    def __post_init__(self):
        """Calcula la grilla de pendientes."""
        if self.dem is not None and self.pendiente_cache is None:
            self._calcular_pendiente()
    
    def _calcular_pendiente(self) -> None:
        """Calcula la pendiente del DEM."""
        if self.dem is None:
            return
        
        gy, gx = np.gradient(self.dem, self.resolucion)
        self.pendiente_cache = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si la pendiente está dentro del límite."""
        if self.pendiente_cache is None or self.bounds is None:
            return 0.0
        
        violacion = 0.0
        
        for lat, lon in coordenadas:
            pendiente = interpolar_raster(
                lat, lon, self.pendiente_cache, self.bounds, nodata=0.0
            )
            
            if pendiente > self.pendiente_maxima:
                violacion += (pendiente - self.pendiente_maxima)
        
        return violacion


def restriccion_pendiente(
    dem: np.ndarray,
    bounds: Tuple[float, float, float, float],
    pendiente_maxima: float = 15.0,
    resolucion: float = 30.0
) -> RestriccionPendiente:
    """Factory function para restricción de pendiente."""
    return RestriccionPendiente(
        dem=dem,
        bounds=bounds,
        pendiente_maxima=pendiente_maxima,
        resolucion=resolucion
    )


# =============================================================================
# RESTRICCIÓN: ZONA INUNDABLE
# =============================================================================

@dataclass
class RestriccionZonaInundable(Restriccion):
    """
    Evita ubicación en zonas inundables.
    
    Attributes
    ----------
    mapa_inundacion : np.ndarray
        Grilla binaria de zonas inundables (1=inundable, 0=no)
    bounds : Tuple[float, float, float, float]
        Límites del mapa
    zonas_poligono : List[List[Tuple[float, float]]]
        Lista de polígonos de zonas inundables
    penalizacion : float
        Penalización por ubicarse en zona inundable
    """
    nombre: str = "Zona Inundable"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.GEOLOGICA
    descripcion: str = "Evita ubicación en zonas inundables"
    
    mapa_inundacion: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    zonas_poligono: List[List[Tuple[float, float]]] = field(default_factory=list)
    penalizacion: float = 1000.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si los sitios están en zonas inundables."""
        violacion = 0.0
        
        for lat, lon in coordenadas:
            en_zona_inundable = False
            
            # Verificar con raster
            if self.mapa_inundacion is not None and self.bounds is not None:
                valor = interpolar_raster(
                    lat, lon, self.mapa_inundacion, self.bounds, nodata=0
                )
                if valor > 0.5:
                    en_zona_inundable = True
            
            # Verificar con polígonos
            if not en_zona_inundable:
                for zona in self.zonas_poligono:
                    if punto_en_poligono(lat, lon, zona):
                        en_zona_inundable = True
                        break
            
            if en_zona_inundable:
                violacion += self.penalizacion
        
        return violacion


def restriccion_zona_inundable(
    mapa_inundacion: Optional[np.ndarray] = None,
    bounds: Optional[Tuple[float, float, float, float]] = None,
    zonas_poligono: Optional[List[List[Tuple[float, float]]]] = None,
    penalizacion: float = 1000.0
) -> RestriccionZonaInundable:
    """Factory function para restricción de zona inundable."""
    return RestriccionZonaInundable(
        mapa_inundacion=mapa_inundacion,
        bounds=bounds,
        zonas_poligono=zonas_poligono or [],
        penalizacion=penalizacion
    )


# =============================================================================
# RESTRICCIÓN: DISTANCIA MÍNIMA ENTRE SITIOS
# =============================================================================

@dataclass
class RestriccionDistanciaMinima(Restriccion):
    """
    Asegura una distancia mínima entre sitios seleccionados.
    
    Útil cuando se optimizan múltiples ubicaciones que no deben
    estar demasiado cerca entre sí.
    
    Attributes
    ----------
    distancia_minima_km : float
        Distancia mínima requerida entre sitios (km)
    """
    nombre: str = "Distancia Mínima entre Sitios"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.ESPACIAL
    descripcion: str = "Asegura distancia mínima entre sitios seleccionados"
    
    distancia_minima_km: float = 5.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si los sitios mantienen la distancia mínima."""
        if len(coordenadas) < 2:
            return 0.0
        
        violacion = 0.0
        n = len(coordenadas)
        
        for i in range(n):
            for j in range(i + 1, n):
                lat1, lon1 = coordenadas[i]
                lat2, lon2 = coordenadas[j]
                
                distancia = distancia_haversine(lat1, lon1, lat2, lon2)
                
                if distancia < self.distancia_minima_km:
                    violacion += (self.distancia_minima_km - distancia)
        
        return violacion


def restriccion_distancia_minima(
    distancia_km: float = 5.0
) -> RestriccionDistanciaMinima:
    """
    Factory function para restricción de distancia mínima.
    
    Parameters
    ----------
    distancia_km : float
        Distancia mínima en kilómetros entre sitios
        
    Returns
    -------
    RestriccionDistanciaMinima
        Restricción configurada
        
    Examples
    --------
    >>> restriccion = restriccion_distancia_minima(distancia_km=10)
    >>> violacion = restriccion.evaluar([(19.4, -103.6), (19.45, -103.65)])
    """
    return RestriccionDistanciaMinima(distancia_minima_km=distancia_km)


# =============================================================================
# RESTRICCIÓN: CAPACIDAD
# =============================================================================

@dataclass
class RestriccionCapacidad(Restriccion):
    """
    Limita la capacidad del terreno (ej: número de estructuras).
    
    Attributes
    ----------
    mapa_capacidad : np.ndarray
        Grilla con capacidad máxima por celda
    bounds : Tuple[float, float, float, float]
        Límites del mapa
    capacidad_requerida : float
        Capacidad mínima requerida
    """
    nombre: str = "Capacidad del Terreno"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.TECNICA
    descripcion: str = "Verifica que el terreno tenga capacidad suficiente"
    
    mapa_capacidad: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    capacidad_requerida: float = 1.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si el terreno tiene capacidad suficiente."""
        if self.mapa_capacidad is None or self.bounds is None:
            return 0.0
        
        violacion = 0.0
        
        for lat, lon in coordenadas:
            capacidad = interpolar_raster(
                lat, lon, self.mapa_capacidad, self.bounds, nodata=0
            )
            
            if capacidad < self.capacidad_requerida:
                violacion += (self.capacidad_requerida - capacidad)
        
        return violacion


def restriccion_capacidad(
    mapa_capacidad: np.ndarray,
    bounds: Tuple[float, float, float, float],
    capacidad_requerida: float = 1.0
) -> RestriccionCapacidad:
    """Factory function para restricción de capacidad."""
    return RestriccionCapacidad(
        mapa_capacidad=mapa_capacidad,
        bounds=bounds,
        capacidad_requerida=capacidad_requerida
    )


# =============================================================================
# RESTRICCIÓN: ZONA PROTEGIDA (ANP)
# =============================================================================

@dataclass
class RestriccionZonaProtegida(Restriccion):
    """
    Evita ubicación en Áreas Naturales Protegidas (ANP).
    
    Attributes
    ----------
    zonas_protegidas : List[List[Tuple[float, float]]]
        Lista de polígonos de ANPs
    nombres_zonas : List[str]
        Nombres de las zonas protegidas
    mapa_anp : np.ndarray
        Grilla binaria de ANPs (alternativa a polígonos)
    bounds : Tuple[float, float, float, float]
        Límites del mapa
    penalizacion : float
        Penalización por ubicarse en ANP
    """
    nombre: str = "Zona Protegida (ANP)"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.AMBIENTAL
    descripcion: str = "Evita ubicación en Áreas Naturales Protegidas"
    
    zonas_protegidas: List[List[Tuple[float, float]]] = field(default_factory=list)
    nombres_zonas: List[str] = field(default_factory=list)
    mapa_anp: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    penalizacion: float = 10000.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si los sitios están en zonas protegidas."""
        violacion = 0.0
        
        for lat, lon in coordenadas:
            en_anp = False
            
            # Verificar con raster
            if self.mapa_anp is not None and self.bounds is not None:
                valor = interpolar_raster(lat, lon, self.mapa_anp, self.bounds, nodata=0)
                if valor > 0.5:
                    en_anp = True
            
            # Verificar con polígonos
            if not en_anp:
                for zona in self.zonas_protegidas:
                    if punto_en_poligono(lat, lon, zona):
                        en_anp = True
                        break
            
            if en_anp:
                violacion += self.penalizacion
        
        return violacion


def restriccion_zona_protegida(
    zonas_protegidas: Optional[List[List[Tuple[float, float]]]] = None,
    mapa_anp: Optional[np.ndarray] = None,
    bounds: Optional[Tuple[float, float, float, float]] = None,
    penalizacion: float = 10000.0
) -> RestriccionZonaProtegida:
    """Factory function para restricción de zona protegida."""
    return RestriccionZonaProtegida(
        zonas_protegidas=zonas_protegidas or [],
        mapa_anp=mapa_anp,
        bounds=bounds,
        penalizacion=penalizacion
    )


# =============================================================================
# RESTRICCIÓN: BUFFER DE FALLAS GEOLÓGICAS
# =============================================================================

@dataclass
class RestriccionBufferFallas(Restriccion):
    """
    Mantiene un buffer de seguridad alrededor de fallas geológicas.
    
    Attributes
    ----------
    fallas : List[List[Tuple[float, float]]]
        Lista de fallas como líneas
    buffer_km : float
        Distancia de buffer en kilómetros
    penalizacion_por_km : float
        Penalización por cada km dentro del buffer
    """
    nombre: str = "Buffer de Fallas"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.GEOLOGICA
    descripcion: str = "Mantiene distancia de seguridad a fallas geológicas"
    
    fallas: List[List[Tuple[float, float]]] = field(default_factory=list)
    buffer_km: float = 5.0
    penalizacion_por_km: float = 100.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si los sitios respetan el buffer de fallas."""
        if not self.fallas:
            return 0.0
        
        violacion = 0.0
        
        for lat, lon in coordenadas:
            distancia_min = float('inf')
            
            for falla in self.fallas:
                dist = distancia_punto_a_linea(lat, lon, falla)
                distancia_min = min(distancia_min, dist)
            
            if distancia_min < self.buffer_km:
                violacion += (self.buffer_km - distancia_min) * self.penalizacion_por_km
        
        return violacion


def restriccion_buffer_fallas(
    fallas: List[List[Tuple[float, float]]],
    buffer_km: float = 5.0,
    penalizacion_por_km: float = 100.0
) -> RestriccionBufferFallas:
    """Factory function para restricción de buffer de fallas."""
    return RestriccionBufferFallas(
        fallas=fallas,
        buffer_km=buffer_km,
        penalizacion_por_km=penalizacion_por_km
    )


# =============================================================================
# RESTRICCIÓN: ELEVACIÓN
# =============================================================================

@dataclass
class RestriccionElevacion(Restriccion):
    """
    Limita el rango de elevación permitido.
    
    Attributes
    ----------
    dem : np.ndarray
        Modelo Digital de Elevación
    bounds : Tuple[float, float, float, float]
        Límites del DEM
    elevacion_minima : float
        Elevación mínima permitida (msnm)
    elevacion_maxima : float
        Elevación máxima permitida (msnm)
    """
    nombre: str = "Rango de Elevación"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.TECNICA
    descripcion: str = "Limita el rango de elevación permitido"
    
    dem: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    elevacion_minima: float = 0.0
    elevacion_maxima: float = 3000.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si la elevación está en el rango permitido."""
        if self.dem is None or self.bounds is None:
            return 0.0
        
        violacion = 0.0
        
        for lat, lon in coordenadas:
            elevacion = interpolar_raster(lat, lon, self.dem, self.bounds, nodata=0)
            
            if elevacion < self.elevacion_minima:
                violacion += (self.elevacion_minima - elevacion)
            elif elevacion > self.elevacion_maxima:
                violacion += (elevacion - self.elevacion_maxima)
        
        return violacion


def restriccion_elevacion(
    dem: np.ndarray,
    bounds: Tuple[float, float, float, float],
    elevacion_minima: float = 0.0,
    elevacion_maxima: float = 3000.0
) -> RestriccionElevacion:
    """Factory function para restricción de elevación."""
    return RestriccionElevacion(
        dem=dem,
        bounds=bounds,
        elevacion_minima=elevacion_minima,
        elevacion_maxima=elevacion_maxima
    )


# =============================================================================
# RESTRICCIÓN: REGIÓN DE ESTUDIO
# =============================================================================

@dataclass
class RestriccionRegion(Restriccion):
    """
    Limita la ubicación a la región de estudio definida.
    
    Attributes
    ----------
    lat_min, lat_max : float
        Límites de latitud
    lon_min, lon_max : float
        Límites de longitud
    poligono_region : List[Tuple[float, float]]
        Polígono de la región (opcional, más preciso)
    margen : float
        Margen interno desde los bordes (grados)
    """
    nombre: str = "Región de Estudio"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.GEOGRAFICA
    descripcion: str = "Limita ubicación a la región de estudio"
    
    lat_min: float = -90.0
    lat_max: float = 90.0
    lon_min: float = -180.0
    lon_max: float = 180.0
    poligono_region: Optional[List[Tuple[float, float]]] = None
    margen: float = 0.0
    penalizacion: float = 1000.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si los sitios están dentro de la región."""
        violacion = 0.0
        
        lat_min_eff = self.lat_min + self.margen
        lat_max_eff = self.lat_max - self.margen
        lon_min_eff = self.lon_min + self.margen
        lon_max_eff = self.lon_max - self.margen
        
        for lat, lon in coordenadas:
            fuera_de_region = False
            
            # Verificar con polígono si existe
            if self.poligono_region is not None:
                if not punto_en_poligono(lat, lon, self.poligono_region):
                    fuera_de_region = True
            else:
                # Verificar con bounding box
                if not (lat_min_eff <= lat <= lat_max_eff and 
                        lon_min_eff <= lon <= lon_max_eff):
                    fuera_de_region = True
            
            if fuera_de_region:
                # Calcular distancia al borde
                dist_lat = max(lat_min_eff - lat, 0, lat - lat_max_eff)
                dist_lon = max(lon_min_eff - lon, 0, lon - lon_max_eff)
                violacion += (dist_lat + dist_lon) * self.penalizacion
        
        return violacion


def restriccion_region(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    margen: float = 0.0,
    poligono_region: Optional[List[Tuple[float, float]]] = None
) -> RestriccionRegion:
    """Factory function para restricción de región."""
    return RestriccionRegion(
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        margen=margen,
        poligono_region=poligono_region
    )


# =============================================================================
# RESTRICCIÓN PERSONALIZADA
# =============================================================================

@dataclass
class RestriccionPersonalizada(Restriccion):
    """
    Permite crear una restricción personalizada con una función lambda.
    
    La función debe retornar:
        - 0.0 si se cumple la restricción
        - > 0.0 indicando la magnitud de la violación
    
    Examples
    --------
    >>> # Restricción: todos los sitios deben estar al norte de lat 19
    >>> restriccion = crear_restriccion_personalizada(
    ...     nombre="Norte de lat 19",
    ...     funcion=lambda coords: sum(max(0, 19 - lat) for lat, lon in coords)
    ... )
    """
    funcion: Optional[Callable[[List[Tuple[float, float]]], float]] = None
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa usando la función personalizada."""
        if self.funcion is None:
            raise ValueError("Función no configurada")
        return self.funcion(coordenadas)


def crear_restriccion_personalizada(
    nombre: str,
    funcion: Callable[[List[Tuple[float, float]]], float],
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD,
    categoria: CategoriaRestriccion = CategoriaRestriccion.TECNICA,
    descripcion: str = ""
) -> RestriccionPersonalizada:
    """
    Crea una restricción personalizada con una función arbitraria.
    
    Parameters
    ----------
    nombre : str
        Nombre de la restricción
    funcion : Callable
        Función que recibe List[Tuple[lat, lon]] y retorna float
        (0 = cumple, > 0 = violación)
    tipo : TipoRestriccion
        Tipo de restricción
    categoria : CategoriaRestriccion
        Categoría de la restricción
    descripcion : str
        Descripción detallada
        
    Returns
    -------
    RestriccionPersonalizada
        Restricción configurada
    """
    return RestriccionPersonalizada(
        nombre=nombre,
        funcion=funcion,
        tipo=tipo,
        categoria=categoria,
        descripcion=descripcion
    )


# =============================================================================
# RESTRICCIONES COMPUESTAS
# =============================================================================

@dataclass
class RestriccionCompuesta(Restriccion):
    """
    Combina múltiples restricciones en una sola.
    
    Attributes
    ----------
    restricciones : List[Restriccion]
        Lista de restricciones a combinar
    pesos : List[float]
        Pesos para cada restricción
    modo : str
        'suma' o 'max' para combinar violaciones
    """
    nombre: str = "Restricción Compuesta"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    
    restricciones: List[Restriccion] = field(default_factory=list)
    pesos: Optional[List[float]] = None
    modo: str = "suma"
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa todas las restricciones y combina las violaciones."""
        if not self.restricciones:
            return 0.0
        
        pesos = self.pesos or [1.0] * len(self.restricciones)
        
        violaciones = []
        for restriccion, peso in zip(self.restricciones, pesos):
            violacion = restriccion.evaluar(coordenadas)
            violaciones.append(violacion * peso)
        
        if self.modo == "max":
            return max(violaciones)
        else:
            return sum(violaciones)


def crear_restriccion_compuesta(
    restricciones: List[Restriccion],
    pesos: Optional[List[float]] = None,
    modo: str = "suma",
    nombre: str = "Restricción Compuesta"
) -> RestriccionCompuesta:
    """Crea una restricción que combina múltiples restricciones."""
    return RestriccionCompuesta(
        nombre=nombre,
        restricciones=restricciones,
        pesos=pesos,
        modo=modo
    )


# =============================================================================
# INFORMACIÓN DEL MÓDULO
# =============================================================================

def listar_restricciones() -> List[str]:
    """Lista todas las restricciones disponibles."""
    return [
        "restriccion_uso_suelo - Limitar a zonas con uso permitido",
        "restriccion_pendiente - Pendiente máxima del terreno",
        "restriccion_zona_inundable - Evitar zonas inundables",
        "restriccion_distancia_minima - Distancia entre sitios",
        "restriccion_capacidad - Capacidad del terreno",
        "restriccion_zona_protegida - Evitar ANPs",
        "restriccion_buffer_fallas - Buffer de fallas geológicas",
        "restriccion_elevacion - Rango de elevación",
        "restriccion_region - Límites de la región de estudio",
        "crear_restriccion_personalizada - Restricción con función lambda",
        "crear_restriccion_compuesta - Combinar restricciones",
    ]


def info_modulo():
    """Muestra información del módulo constraints."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              SEISMEX Optimization - constraints.py                   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Restricciones implementadas:                                        ║
║    ✅ restriccion_uso_suelo         - Uso de suelo permitido         ║
║    ✅ restriccion_pendiente         - Pendiente máxima               ║
║    ✅ restriccion_zona_inundable    - Zonas inundables               ║
║    ✅ restriccion_distancia_minima  - Distancia entre sitios         ║
║    ✅ restriccion_capacidad         - Capacidad del terreno          ║
║    ✅ restriccion_zona_protegida    - Áreas naturales protegidas     ║
║    ✅ restriccion_buffer_fallas     - Buffer de fallas               ║
║    ✅ restriccion_elevacion         - Rango de elevación             ║
║    ✅ restriccion_region            - Límites de región              ║
║    ✅ crear_restriccion_personalizada - Función lambda               ║
║    ✅ crear_restriccion_compuesta   - Combinar restricciones         ║
║                                                                      ║
║  Estado: ✅ COMPLETAMENTE IMPLEMENTADO                               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enumeraciones
    'TipoRestriccion',
    'SeveridadRestriccion',
    'CategoriaRestriccion',
    
    # Clase base
    'Restriccion',
    
    # Clases de restricciones
    'RestriccionUsoSuelo',
    'RestriccionPendiente',
    'RestriccionZonaInundable',
    'RestriccionDistanciaMinima',
    'RestriccionCapacidad',
    'RestriccionZonaProtegida',
    'RestriccionBufferFallas',
    'RestriccionElevacion',
    'RestriccionRegion',
    'RestriccionPersonalizada',
    'RestriccionCompuesta',
    
    # Factory functions
    'restriccion_uso_suelo',
    'restriccion_pendiente',
    'restriccion_zona_inundable',
    'restriccion_distancia_minima',
    'restriccion_capacidad',
    'restriccion_zona_protegida',
    'restriccion_buffer_fallas',
    'restriccion_elevacion',
    'restriccion_region',
    'crear_restriccion_personalizada',
    'crear_restriccion_compuesta',
    
    # Utilidades
    'distancia_haversine',
    'listar_restricciones',
    'info_modulo',
]
