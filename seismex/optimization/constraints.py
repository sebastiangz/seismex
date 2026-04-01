#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Optimization - Restricciones
================================================================================

Restricciones predefinidas para optimización de ubicación de infraestructura.

Las restricciones retornan el grado de violación:
    - 0 = restricción satisfecha
    - > 0 = restricción violada (mayor valor = mayor violación)

Restricciones disponibles:
    - restriccion_uso_suelo: Limitar a zonas de uso permitido
    - restriccion_pendiente: Limitar pendiente máxima del terreno
    - restriccion_zona_inundable: Evitar zonas inundables
    - restriccion_distancia_minima: Distancia mínima entre sitios
    - restriccion_capacidad: Límites de capacidad
    - restriccion_zona_protegida: Evitar áreas naturales protegidas
    - restriccion_buffer_fallas: Mantener distancia mínima a fallas
    - restriccion_elevacion: Límites de elevación

Estado: PLANIFICADO - Estructura definida, implementación pendiente

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
    from shapely.geometry import Polygon, MultiPolygon

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoRestriccion(Enum):
    """Tipos de restricciones."""
    IGUALDAD = "igualdad"       # g(x) = 0
    DESIGUALDAD = "desigualdad"  # g(x) <= 0
    LIMITE = "limite"            # lb <= x <= ub


class CategoriaRestriccion(Enum):
    """Categorías de restricciones."""
    GEOGRAFICA = "geografica"
    NORMATIVA = "normativa"
    FISICA = "fisica"
    OPERACIONAL = "operacional"
    AMBIENTAL = "ambiental"


class UsoSuelo(Enum):
    """Tipos de uso de suelo."""
    URBANO = "urbano"
    RURAL = "rural"
    INDUSTRIAL = "industrial"
    AGRICOLA = "agricola"
    FORESTAL = "forestal"
    HUMEDAL = "humedal"
    AREA_NATURAL_PROTEGIDA = "anp"
    ZONA_FEDERAL = "zona_federal"
    CUERPO_AGUA = "cuerpo_agua"


# =============================================================================
# CLASE BASE
# =============================================================================

@dataclass
class Restriccion(ABC):
    """
    Clase base abstracta para restricciones.
    
    Las restricciones evalúan el grado de violación de una solución.
    Un valor de 0 indica que la restricción se satisface.
    Un valor > 0 indica violación (mayor = peor).
    
    Attributes
    ----------
    nombre : str
        Nombre descriptivo de la restricción
    tipo : TipoRestriccion
        Tipo de restricción (igualdad, desigualdad, límite)
    categoria : CategoriaRestriccion
        Categoría de la restricción
    peso : float
        Peso de penalización (default: 1.0)
    activa : bool
        Si la restricción está activa
    descripcion : str
        Descripción detallada
    
    Examples
    --------
    >>> class MiRestriccion(Restriccion):
    ...     def evaluar(self, coordenadas):
    ...         # Retorna 0 si ok, >0 si violada
    ...         return violacion
    """
    nombre: str
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.GEOGRAFICA
    peso: float = 1.0
    activa: bool = True
    descripcion: str = ""
    
    @abstractmethod
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa el grado de violación de la restricción.
        
        Parameters
        ----------
        coordenadas : List[Tuple[float, float]]
            Lista de tuplas (latitud, longitud) de los sitios
            
        Returns
        -------
        float
            Grado de violación (0 = satisfecha, >0 = violada)
        """
        pass
    
    def __call__(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Permite usar la instancia como función."""
        if not self.activa:
            return 0.0
        return self.evaluar(coordenadas)
    
    def satisfecha(self, coordenadas: List[Tuple[float, float]]) -> bool:
        """Verifica si la restricción está satisfecha."""
        return self.evaluar(coordenadas) == 0.0


# =============================================================================
# RESTRICCIÓN: USO DE SUELO
# =============================================================================

@dataclass
class RestriccionUsoSuelo(Restriccion):
    """
    Restringe las ubicaciones a zonas con uso de suelo permitido.
    
    Attributes
    ----------
    mapa_uso_suelo : Any
        GeoDataFrame o raster con tipos de uso de suelo
    usos_permitidos : Set[UsoSuelo]
        Conjunto de usos de suelo permitidos
    
    Examples
    --------
    >>> restriccion = restriccion_uso_suelo(
    ...     mapa_uso_suelo=gdf_uso_suelo,
    ...     usos_permitidos={UsoSuelo.INDUSTRIAL, UsoSuelo.RURAL}
    ... )
    """
    nombre: str = "Uso de Suelo"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.NORMATIVA
    descripcion: str = "Limita ubicaciones a zonas con uso de suelo permitido"
    
    # Parámetros específicos
    mapa_uso_suelo: Optional[Any] = None
    usos_permitidos: Set[UsoSuelo] = field(default_factory=set)
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa si las coordenadas están en zonas de uso permitido.
        
        Returns
        -------
        float
            0 si todas las ubicaciones están en zonas permitidas,
            > 0 indica el número de ubicaciones en zonas prohibidas
        """
        if self.mapa_uso_suelo is None:
            return 0.0  # Sin datos, no se puede evaluar
        
        # TODO: Implementar verificación de uso de suelo
        raise NotImplementedError("Evaluación de uso de suelo pendiente")


def restriccion_uso_suelo(
    mapa_uso_suelo: Any,
    usos_permitidos: Optional[Set[UsoSuelo]] = None
) -> RestriccionUsoSuelo:
    """
    Factory function para restricción de uso de suelo.
    
    Parameters
    ----------
    mapa_uso_suelo : Any
        GeoDataFrame o raster con uso de suelo
    usos_permitidos : Optional[Set[UsoSuelo]]
        Usos permitidos. Por defecto: industrial y rural
        
    Returns
    -------
    RestriccionUsoSuelo
        Instancia configurada
    """
    if usos_permitidos is None:
        usos_permitidos = {UsoSuelo.INDUSTRIAL, UsoSuelo.RURAL}
    
    return RestriccionUsoSuelo(
        mapa_uso_suelo=mapa_uso_suelo,
        usos_permitidos=usos_permitidos
    )


# =============================================================================
# RESTRICCIÓN: PENDIENTE
# =============================================================================

@dataclass
class RestriccionPendiente(Restriccion):
    """
    Restringe ubicaciones a zonas con pendiente menor al límite.
    
    Attributes
    ----------
    dem : Any
        Modelo Digital de Elevación
    pendiente_maxima : float
        Pendiente máxima permitida en grados
    
    Examples
    --------
    >>> restriccion = restriccion_pendiente(dem, pendiente_maxima=15)
    """
    nombre: str = "Pendiente Máxima"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.FISICA
    descripcion: str = "Limita la pendiente máxima del terreno"
    
    # Parámetros específicos
    dem: Optional[Any] = None
    pendiente_maxima: float = 15.0  # grados
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa si la pendiente está dentro del límite.
        
        Returns
        -------
        float
            0 si pendiente <= máxima, exceso si > máxima
        """
        if self.dem is None:
            return 0.0
        
        # TODO: Implementar cálculo de pendiente
        raise NotImplementedError("Evaluación de pendiente pendiente")


def restriccion_pendiente(
    dem: Any,
    pendiente_maxima: float = 15.0
) -> RestriccionPendiente:
    """Factory function para restricción de pendiente."""
    return RestriccionPendiente(
        dem=dem,
        pendiente_maxima=pendiente_maxima
    )


# =============================================================================
# RESTRICCIÓN: ZONA INUNDABLE
# =============================================================================

@dataclass
class RestriccionZonaInundable(Restriccion):
    """
    Evita ubicaciones en zonas inundables.
    
    Attributes
    ----------
    zonas_inundables : Any
        GeoDataFrame con polígonos de zonas inundables
    periodo_retorno : int
        Período de retorno a considerar (años)
    
    Examples
    --------
    >>> restriccion = restriccion_zona_inundable(
    ...     gdf_inundacion, 
    ...     periodo_retorno=100
    ... )
    """
    nombre: str = "Zona Inundable"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.FISICA
    descripcion: str = "Evita ubicaciones en zonas inundables"
    
    # Parámetros específicos
    zonas_inundables: Optional[Any] = None
    periodo_retorno: int = 100  # años
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa si las ubicaciones están fuera de zonas inundables.
        """
        if self.zonas_inundables is None:
            return 0.0
        
        # TODO: Implementar verificación de zonas inundables
        raise NotImplementedError("Evaluación de zona inundable pendiente")


def restriccion_zona_inundable(
    zonas_inundables: Any,
    periodo_retorno: int = 100
) -> RestriccionZonaInundable:
    """Factory function para restricción de zona inundable."""
    return RestriccionZonaInundable(
        zonas_inundables=zonas_inundables,
        periodo_retorno=periodo_retorno
    )


# =============================================================================
# RESTRICCIÓN: DISTANCIA MÍNIMA
# =============================================================================

@dataclass
class RestriccionDistanciaMinima(Restriccion):
    """
    Mantiene distancia mínima entre sitios seleccionados.
    
    Attributes
    ----------
    distancia_minima : float
        Distancia mínima entre sitios (km)
    
    Examples
    --------
    >>> restriccion = restriccion_distancia_minima(distancia_minima=5.0)
    """
    nombre: str = "Distancia Mínima entre Sitios"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.OPERACIONAL
    descripcion: str = "Mantiene distancia mínima entre sitios seleccionados"
    
    # Parámetros específicos
    distancia_minima: float = 5.0  # km
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa si todos los pares de sitios mantienen la distancia mínima.
        
        Returns
        -------
        float
            0 si todas las distancias >= mínima,
            suma de violaciones si alguna es menor
        """
        if len(coordenadas) < 2:
            return 0.0
        
        violacion_total = 0.0
        
        for i in range(len(coordenadas)):
            for j in range(i + 1, len(coordenadas)):
                lat1, lon1 = coordenadas[i]
                lat2, lon2 = coordenadas[j]
                
                # Distancia aproximada (Haversine simplificado)
                distancia = self._calcular_distancia(lat1, lon1, lat2, lon2)
                
                if distancia < self.distancia_minima:
                    violacion_total += self.distancia_minima - distancia
        
        return violacion_total
    
    def _calcular_distancia(
        self, 
        lat1: float, lon1: float, 
        lat2: float, lon2: float
    ) -> float:
        """Calcula distancia entre dos puntos en km (Haversine)."""
        R = 6371  # Radio de la Tierra en km
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = (np.sin(dlat / 2) ** 2 + 
             np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c


def restriccion_distancia_minima(
    distancia_minima: float = 5.0
) -> RestriccionDistanciaMinima:
    """Factory function para restricción de distancia mínima."""
    return RestriccionDistanciaMinima(
        distancia_minima=distancia_minima
    )


# =============================================================================
# RESTRICCIÓN: CAPACIDAD
# =============================================================================

@dataclass
class RestriccionCapacidad(Restriccion):
    """
    Limita la capacidad total o por sitio.
    
    Attributes
    ----------
    capacidad_maxima_total : float
        Capacidad máxima total permitida
    capacidad_maxima_sitio : float
        Capacidad máxima por sitio individual
    
    Examples
    --------
    >>> restriccion = restriccion_capacidad(
    ...     capacidad_maxima_total=1000,
    ...     capacidad_maxima_sitio=200
    ... )
    """
    nombre: str = "Capacidad"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.OPERACIONAL
    descripcion: str = "Limita la capacidad total y por sitio"
    
    # Parámetros específicos
    capacidad_maxima_total: float = float('inf')
    capacidad_maxima_sitio: float = float('inf')
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa restricciones de capacidad."""
        # Esta restricción típicamente se evalúa con datos adicionales
        # TODO: Implementar cuando se tenga modelo de capacidad
        return 0.0


def restriccion_capacidad(
    capacidad_maxima_total: float = float('inf'),
    capacidad_maxima_sitio: float = float('inf')
) -> RestriccionCapacidad:
    """Factory function para restricción de capacidad."""
    return RestriccionCapacidad(
        capacidad_maxima_total=capacidad_maxima_total,
        capacidad_maxima_sitio=capacidad_maxima_sitio
    )


# =============================================================================
# RESTRICCIÓN: ZONA PROTEGIDA
# =============================================================================

@dataclass
class RestriccionZonaProtegida(Restriccion):
    """
    Evita ubicaciones en áreas naturales protegidas.
    
    Attributes
    ----------
    areas_protegidas : Any
        GeoDataFrame con polígonos de ANPs
    buffer_km : float
        Distancia de buffer adicional alrededor de las ANPs
    
    Examples
    --------
    >>> restriccion = restriccion_zona_protegida(gdf_anp, buffer_km=1.0)
    """
    nombre: str = "Zona Natural Protegida"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.AMBIENTAL
    descripcion: str = "Evita ubicaciones en áreas naturales protegidas"
    
    # Parámetros específicos
    areas_protegidas: Optional[Any] = None
    buffer_km: float = 0.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si las ubicaciones están fuera de zonas protegidas."""
        if self.areas_protegidas is None:
            return 0.0
        
        # TODO: Implementar verificación de áreas protegidas
        raise NotImplementedError("Evaluación de zona protegida pendiente")


def restriccion_zona_protegida(
    areas_protegidas: Any,
    buffer_km: float = 0.0
) -> RestriccionZonaProtegida:
    """Factory function para restricción de zona protegida."""
    return RestriccionZonaProtegida(
        areas_protegidas=areas_protegidas,
        buffer_km=buffer_km
    )


# =============================================================================
# RESTRICCIÓN: BUFFER FALLAS
# =============================================================================

@dataclass
class RestriccionBufferFallas(Restriccion):
    """
    Mantiene distancia mínima a fallas geológicas.
    
    Attributes
    ----------
    fallas : Any
        GeoDataFrame con geometrías de fallas
    distancia_minima : float
        Distancia mínima a mantener (km)
    
    Examples
    --------
    >>> restriccion = restriccion_buffer_fallas(gdf_fallas, distancia_minima=5.0)
    """
    nombre: str = "Buffer a Fallas"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.GEOGRAFICA
    descripcion: str = "Mantiene distancia mínima a fallas geológicas"
    
    # Parámetros específicos
    fallas: Optional[Any] = None
    distancia_minima: float = 5.0  # km
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si las ubicaciones mantienen distancia a fallas."""
        if self.fallas is None:
            return 0.0
        
        # TODO: Implementar cálculo de distancia a fallas
        raise NotImplementedError("Evaluación de buffer a fallas pendiente")


def restriccion_buffer_fallas(
    fallas: Any,
    distancia_minima: float = 5.0
) -> RestriccionBufferFallas:
    """Factory function para restricción de buffer a fallas."""
    return RestriccionBufferFallas(
        fallas=fallas,
        distancia_minima=distancia_minima
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
    dem : Any
        Modelo Digital de Elevación
    elevacion_minima : float
        Elevación mínima permitida (m)
    elevacion_maxima : float
        Elevación máxima permitida (m)
    
    Examples
    --------
    >>> restriccion = restriccion_elevacion(
    ...     dem,
    ...     elevacion_minima=100,
    ...     elevacion_maxima=2000
    ... )
    """
    nombre: str = "Elevación"
    tipo: TipoRestriccion = TipoRestriccion.DESIGUALDAD
    categoria: CategoriaRestriccion = CategoriaRestriccion.FISICA
    descripcion: str = "Limita el rango de elevación permitido"
    
    # Parámetros específicos
    dem: Optional[Any] = None
    elevacion_minima: float = 0.0
    elevacion_maxima: float = 4000.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa si las elevaciones están dentro del rango."""
        if self.dem is None:
            return 0.0
        
        # TODO: Implementar verificación de elevación
        raise NotImplementedError("Evaluación de elevación pendiente")


def restriccion_elevacion(
    dem: Any,
    elevacion_minima: float = 0.0,
    elevacion_maxima: float = 4000.0
) -> RestriccionElevacion:
    """Factory function para restricción de elevación."""
    return RestriccionElevacion(
        dem=dem,
        elevacion_minima=elevacion_minima,
        elevacion_maxima=elevacion_maxima
    )


# =============================================================================
# RESTRICCIÓN PERSONALIZADA
# =============================================================================

@dataclass
class RestriccionPersonalizada(Restriccion):
    """
    Permite crear una restricción personalizada con una función lambda.
    
    Examples
    --------
    >>> # Restricción: no permitir coordenadas fuera de México
    >>> restriccion = crear_restriccion_personalizada(
    ...     nombre="Dentro de México",
    ...     funcion=lambda coords: sum(
    ...         1 for c in coords 
    ...         if not (14 <= c[0] <= 33 and -118 <= c[1] <= -86)
    ...     )
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
    categoria: CategoriaRestriccion = CategoriaRestriccion.GEOGRAFICA,
    descripcion: str = ""
) -> RestriccionPersonalizada:
    """
    Crea una restricción personalizada.
    
    Parameters
    ----------
    nombre : str
        Nombre de la restricción
    funcion : Callable
        Función que recibe coordenadas y retorna violación (0 = ok)
    tipo : TipoRestriccion
        Tipo de restricción
    categoria : CategoriaRestriccion
        Categoría
    descripcion : str
        Descripción
        
    Returns
    -------
    RestriccionPersonalizada
        Instancia configurada
    """
    return RestriccionPersonalizada(
        nombre=nombre,
        funcion=funcion,
        tipo=tipo,
        categoria=categoria,
        descripcion=descripcion
    )


# =============================================================================
# INFORMACIÓN DEL MÓDULO
# =============================================================================

def listar_restricciones() -> List[str]:
    """Lista todas las restricciones disponibles."""
    return [
        "restriccion_uso_suelo - Limitar a zonas de uso permitido",
        "restriccion_pendiente - Limitar pendiente máxima",
        "restriccion_zona_inundable - Evitar zonas inundables",
        "restriccion_distancia_minima - Distancia mínima entre sitios",
        "restriccion_capacidad - Límites de capacidad",
        "restriccion_zona_protegida - Evitar áreas naturales protegidas",
        "restriccion_buffer_fallas - Distancia mínima a fallas",
        "restriccion_elevacion - Límites de elevación",
        "crear_restriccion_personalizada - Restricción con función lambda",
    ]


def info_modulo():
    """Muestra información del módulo constraints."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              SEISMEX Optimization - constraints.py                   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Restricciones disponibles:                                          ║
║    • restriccion_uso_suelo        - Uso de suelo permitido           ║
║    • restriccion_pendiente        - Pendiente máxima                 ║
║    • restriccion_zona_inundable   - Evitar zonas inundables          ║
║    • restriccion_distancia_minima - Distancia entre sitios           ║
║    • restriccion_capacidad        - Límites de capacidad             ║
║    • restriccion_zona_protegida   - Evitar ANPs                      ║
║    • restriccion_buffer_fallas    - Distancia a fallas               ║
║    • restriccion_elevacion        - Rango de elevación               ║
║    • crear_restriccion_personalizada                                 ║
║                                                                      ║
║  Estado: ESTRUCTURA DEFINIDA - Implementación pendiente              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enumeraciones
    'TipoRestriccion',
    'CategoriaRestriccion',
    'UsoSuelo',
    
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
    'RestriccionPersonalizada',
    
    # Factory functions
    'restriccion_uso_suelo',
    'restriccion_pendiente',
    'restriccion_zona_inundable',
    'restriccion_distancia_minima',
    'restriccion_capacidad',
    'restriccion_zona_protegida',
    'restriccion_buffer_fallas',
    'restriccion_elevacion',
    'crear_restriccion_personalizada',
    
    # Utilidades
    'listar_restricciones',
    'info_modulo',
]
