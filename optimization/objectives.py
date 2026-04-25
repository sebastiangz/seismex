#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Optimization - Funciones Objetivo
================================================================================

Funciones objetivo completas para optimización de ubicación de
infraestructura considerando riesgo sísmico y otros factores.

Todas las funciones se definen para MINIMIZACIÓN:
    - Riesgo: menor = mejor
    - Costo: menor = mejor
    - Para maximización (accesibilidad), se retorna el negativo

Funciones disponibles:
    - objetivo_riesgo_esd: Minimizar riesgo sísmico basado en ESD
    - objetivo_costo_construccion: Minimizar costo de construcción
    - objetivo_impacto_ambiental: Minimizar impacto ambiental
    - objetivo_accesibilidad: Maximizar accesibilidad (retorna negativo)
    - objetivo_distancia_fallas: Maximizar distancia a fallas
    - objetivo_distancia_volcanes: Maximizar distancia a volcanes
    - objetivo_pendiente: Minimizar pendiente del terreno

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
    TYPE_CHECKING
)
from enum import Enum
import numpy as np

if TYPE_CHECKING:
    import geopandas as gpd
    from shapely.geometry import Point

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

RADIO_TIERRA_KM = 6371.0


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoOptimizacion(Enum):
    """Tipo de optimización para el objetivo."""
    MINIMIZAR = "minimizar"
    MAXIMIZAR = "maximizar"


class CategoriaObjetivo(Enum):
    """Categorías de objetivos."""
    RIESGO_SISMICO = "riesgo_sismico"
    ECONOMICO = "economico"
    AMBIENTAL = "ambiental"
    SOCIAL = "social"
    GEOLOGICO = "geologico"
    ACCESIBILIDAD = "accesibilidad"


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def distancia_haversine(
    lat1: float, lon1: float, 
    lat2: float, lon2: float
) -> float:
    """
    Calcula la distancia entre dos puntos usando la fórmula de Haversine.
    
    Parameters
    ----------
    lat1, lon1 : float
        Coordenadas del primer punto (grados)
    lat2, lon2 : float
        Coordenadas del segundo punto (grados)
        
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
    
    # Verificar que está dentro de los límites
    if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
        return nodata
    
    # Calcular índices (el raster típicamente tiene origen arriba-izquierda)
    col = int((lon - lon_min) / (lon_max - lon_min) * (ncols - 1))
    row = int((lat_max - lat) / (lat_max - lat_min) * (nrows - 1))
    
    # Verificar límites
    row = np.clip(row, 0, nrows - 1)
    col = np.clip(col, 0, ncols - 1)
    
    valor = raster[row, col]
    
    if np.isnan(valor) or valor == nodata:
        return nodata
    
    return valor


def punto_en_poligono_simple(
    lat: float, lon: float,
    poligono_coords: List[Tuple[float, float]]
) -> bool:
    """
    Verifica si un punto está dentro de un polígono (ray casting).
    
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


# =============================================================================
# CLASE BASE
# =============================================================================

@dataclass
class FuncionObjetivo(ABC):
    """
    Clase base abstracta para funciones objetivo.
    
    Todas las funciones objetivo deben heredar de esta clase e
    implementar el método `evaluar`.
    
    Attributes
    ----------
    nombre : str
        Nombre descriptivo del objetivo
    tipo : TipoOptimizacion
        Si es minimización o maximización
    categoria : CategoriaObjetivo
        Categoría del objetivo
    peso : float
        Peso relativo del objetivo (default: 1.0)
    unidad : str
        Unidad de medida del valor retornado
    descripcion : str
        Descripción detallada del objetivo
    """
    nombre: str
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.RIESGO_SISMICO
    peso: float = 1.0
    unidad: str = ""
    descripcion: str = ""
    
    @abstractmethod
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa el objetivo para las coordenadas dadas.
        
        Parameters
        ----------
        coordenadas : List[Tuple[float, float]]
            Lista de tuplas (latitud, longitud) de los sitios
            
        Returns
        -------
        float
            Valor del objetivo (siempre orientado a minimización)
        """
        pass
    
    def __call__(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Permite usar la instancia como función."""
        return self.evaluar(coordenadas)
    
    def normalizar(self, valor: float, vmin: float, vmax: float) -> float:
        """Normaliza un valor al rango [0, 1]."""
        if vmax == vmin:
            return 0.5
        return (valor - vmin) / (vmax - vmin)


# =============================================================================
# OBJETIVO: RIESGO SÍSMICO (ESD)
# =============================================================================

@dataclass
class ObjetivoRiesgoESD(FuncionObjetivo):
    """
    Minimiza el riesgo sísmico basado en valores de ESD.
    
    Utiliza el resultado del análisis ESD para evaluar el riesgo
    en cada ubicación candidata mediante interpolación.
    
    Attributes
    ----------
    esd_grid : np.ndarray
        Grilla de valores ESD (log10)
    bounds : Tuple[float, float, float, float]
        Límites (lon_min, lat_min, lon_max, lat_max)
    profundidad_idx : int
        Índice de profundidad en el grid 3D
    metodo_agregacion : str
        Cómo agregar múltiples sitios: 'max', 'mean', 'sum'
    """
    nombre: str = "Riesgo Sísmico (ESD)"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.RIESGO_SISMICO
    unidad: str = "log₁₀(ESD)"
    descripcion: str = "Minimiza la densidad de energía sísmica en la ubicación"
    
    # Parámetros específicos
    esd_grid: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    profundidad_idx: int = 0
    metodo_agregacion: str = "max"
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa el riesgo ESD para las coordenadas dadas.
        """
        if self.esd_grid is None or self.bounds is None:
            raise ValueError("esd_grid y bounds deben estar configurados")
        
        valores = []
        for lat, lon in coordenadas:
            # Si es grid 3D, seleccionar profundidad
            if self.esd_grid.ndim == 3:
                grid_2d = self.esd_grid[self.profundidad_idx, :, :]
            else:
                grid_2d = self.esd_grid
            
            valor = interpolar_raster(lat, lon, grid_2d, self.bounds, nodata=0.0)
            valores.append(valor)
        
        valores = np.array(valores)
        
        if self.metodo_agregacion == 'max':
            return float(np.max(valores))
        elif self.metodo_agregacion == 'mean':
            return float(np.mean(valores))
        elif self.metodo_agregacion == 'sum':
            return float(np.sum(valores))
        else:
            return float(np.max(valores))


def objetivo_riesgo_esd(
    esd_grid: np.ndarray,
    bounds: Tuple[float, float, float, float],
    profundidad_idx: int = 0,
    metodo_agregacion: str = "max"
) -> ObjetivoRiesgoESD:
    """
    Factory function para crear objetivo de riesgo ESD.
    
    Parameters
    ----------
    esd_grid : np.ndarray
        Grilla de valores ESD
    bounds : Tuple[float, float, float, float]
        Límites (lon_min, lat_min, lon_max, lat_max)
    profundidad_idx : int
        Índice de profundidad para grids 3D
    metodo_agregacion : str
        'max', 'mean', o 'sum'
        
    Returns
    -------
    ObjetivoRiesgoESD
        Instancia configurada
        
    Examples
    --------
    >>> objetivo = objetivo_riesgo_esd(
    ...     esd_grid=resultado.esd_grid,
    ...     bounds=(-106, 17, -102, 21)
    ... )
    """
    return ObjetivoRiesgoESD(
        esd_grid=esd_grid,
        bounds=bounds,
        profundidad_idx=profundidad_idx,
        metodo_agregacion=metodo_agregacion
    )


# =============================================================================
# OBJETIVO: COSTO DE CONSTRUCCIÓN
# =============================================================================

@dataclass
class ObjetivoCostoConstruccion(FuncionObjetivo):
    """
    Minimiza el costo de construcción basado en un mapa de costos.
    
    Attributes
    ----------
    mapa_costos : np.ndarray
        Grilla de costos por m²
    bounds : Tuple[float, float, float, float]
        Límites (lon_min, lat_min, lon_max, lat_max)
    costo_base : float
        Costo base de construcción (USD/m²)
    area_construccion : float
        Área de construcción en m² (para escalar)
    """
    nombre: str = "Costo de Construcción"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.ECONOMICO
    unidad: str = "USD"
    descripcion: str = "Minimiza el costo de construcción en la ubicación"
    
    mapa_costos: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    costo_base: float = 1000.0
    area_construccion: float = 1000.0  # m²
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa el costo total para todas las ubicaciones."""
        costo_total = 0.0
        
        for lat, lon in coordenadas:
            if self.mapa_costos is not None and self.bounds is not None:
                factor = interpolar_raster(lat, lon, self.mapa_costos, self.bounds, nodata=1.0)
            else:
                factor = 1.0
            
            costo_sitio = self.costo_base * factor * self.area_construccion
            costo_total += costo_sitio
        
        return costo_total


def objetivo_costo_construccion(
    mapa_costos: Optional[np.ndarray] = None,
    bounds: Optional[Tuple[float, float, float, float]] = None,
    costo_base: float = 1000.0,
    area_construccion: float = 1000.0
) -> ObjetivoCostoConstruccion:
    """Factory function para crear objetivo de costo de construcción."""
    return ObjetivoCostoConstruccion(
        mapa_costos=mapa_costos,
        bounds=bounds,
        costo_base=costo_base,
        area_construccion=area_construccion
    )


# =============================================================================
# OBJETIVO: IMPACTO AMBIENTAL
# =============================================================================

@dataclass
class ObjetivoImpactoAmbiental(FuncionObjetivo):
    """
    Minimiza el impacto ambiental basado en capas de sensibilidad.
    
    Attributes
    ----------
    mapa_sensibilidad : np.ndarray
        Grilla de índice de sensibilidad ambiental (0-1)
    bounds : Tuple[float, float, float, float]
        Límites del mapa
    zonas_protegidas : List[List[Tuple[float, float]]]
        Lista de polígonos de zonas protegidas
    penalizacion_zona_protegida : float
        Penalización por estar en zona protegida
    """
    nombre: str = "Impacto Ambiental"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.AMBIENTAL
    unidad: str = "índice (0-1)"
    descripcion: str = "Minimiza el impacto ambiental en zonas sensibles"
    
    mapa_sensibilidad: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    zonas_protegidas: List[List[Tuple[float, float]]] = field(default_factory=list)
    penalizacion_zona_protegida: float = 10.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa el impacto ambiental total."""
        impacto_total = 0.0
        
        for lat, lon in coordenadas:
            # Sensibilidad del mapa
            if self.mapa_sensibilidad is not None and self.bounds is not None:
                sensibilidad = interpolar_raster(
                    lat, lon, self.mapa_sensibilidad, self.bounds, nodata=0.5
                )
            else:
                sensibilidad = 0.0
            
            # Verificar zonas protegidas
            en_zona_protegida = False
            for zona in self.zonas_protegidas:
                if punto_en_poligono_simple(lat, lon, zona):
                    en_zona_protegida = True
                    break
            
            if en_zona_protegida:
                sensibilidad += self.penalizacion_zona_protegida
            
            impacto_total += sensibilidad
        
        return impacto_total / len(coordenadas) if coordenadas else 0.0


def objetivo_impacto_ambiental(
    mapa_sensibilidad: Optional[np.ndarray] = None,
    bounds: Optional[Tuple[float, float, float, float]] = None,
    zonas_protegidas: Optional[List[List[Tuple[float, float]]]] = None,
    penalizacion_zona_protegida: float = 10.0
) -> ObjetivoImpactoAmbiental:
    """Factory function para objetivo de impacto ambiental."""
    return ObjetivoImpactoAmbiental(
        mapa_sensibilidad=mapa_sensibilidad,
        bounds=bounds,
        zonas_protegidas=zonas_protegidas or [],
        penalizacion_zona_protegida=penalizacion_zona_protegida
    )


# =============================================================================
# OBJETIVO: ACCESIBILIDAD
# =============================================================================

@dataclass
class ObjetivoAccesibilidad(FuncionObjetivo):
    """
    Maximiza la accesibilidad a servicios y vías de comunicación.
    
    NOTA: Retorna valores negativos (minimizar negativo = maximizar).
    
    Attributes
    ----------
    puntos_interes : List[Tuple[float, float]]
        Lista de puntos de interés (lat, lon)
    pesos_puntos : List[float]
        Pesos de importancia para cada punto
    distancia_referencia : float
        Distancia de referencia para normalización (km)
    """
    nombre: str = "Accesibilidad"
    tipo: TipoOptimizacion = TipoOptimizacion.MAXIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.ACCESIBILIDAD
    unidad: str = "índice (negativo)"
    descripcion: str = "Maximiza accesibilidad (minimiza distancia a servicios)"
    
    puntos_interes: List[Tuple[float, float]] = field(default_factory=list)
    pesos_puntos: Optional[List[float]] = None
    distancia_referencia: float = 50.0  # km
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa la accesibilidad (retorna negativo para minimización).
        
        Calcula la suma ponderada de las distancias inversas a puntos de interés.
        """
        if not self.puntos_interes:
            return 0.0
        
        pesos = self.pesos_puntos or [1.0] * len(self.puntos_interes)
        
        accesibilidad_total = 0.0
        for lat, lon in coordenadas:
            for (poi_lat, poi_lon), peso in zip(self.puntos_interes, pesos):
                distancia = distancia_haversine(lat, lon, poi_lat, poi_lon)
                # Función de accesibilidad inversa
                accesibilidad = peso / (1 + distancia / self.distancia_referencia)
                accesibilidad_total += accesibilidad
        
        # Retornar negativo porque queremos maximizar
        return -accesibilidad_total


def objetivo_accesibilidad(
    puntos_interes: List[Tuple[float, float]],
    pesos_puntos: Optional[List[float]] = None,
    distancia_referencia: float = 50.0
) -> ObjetivoAccesibilidad:
    """Factory function para objetivo de accesibilidad."""
    return ObjetivoAccesibilidad(
        puntos_interes=puntos_interes,
        pesos_puntos=pesos_puntos,
        distancia_referencia=distancia_referencia
    )


# =============================================================================
# OBJETIVO: DISTANCIA A FALLAS
# =============================================================================

@dataclass
class ObjetivoDistanciaFallas(FuncionObjetivo):
    """
    Maximiza la distancia a fallas geológicas activas.
    
    Retorna el negativo de la distancia mínima.
    
    Attributes
    ----------
    fallas : List[List[Tuple[float, float]]]
        Lista de fallas como líneas [(lat, lon), ...]
    distancia_critica : float
        Distancia mínima considerada segura (km)
    """
    nombre: str = "Distancia a Fallas"
    tipo: TipoOptimizacion = TipoOptimizacion.MAXIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.GEOLOGICO
    unidad: str = "km (negativo)"
    descripcion: str = "Maximiza distancia a fallas geológicas activas"
    
    fallas: List[List[Tuple[float, float]]] = field(default_factory=list)
    distancia_critica: float = 5.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa la distancia mínima a fallas (retorna negativo)."""
        if not self.fallas:
            return 0.0
        
        distancia_min_total = float('inf')
        
        for lat, lon in coordenadas:
            for falla in self.fallas:
                for falla_lat, falla_lon in falla:
                    dist = distancia_haversine(lat, lon, falla_lat, falla_lon)
                    distancia_min_total = min(distancia_min_total, dist)
        
        # Retornar negativo (queremos maximizar distancia)
        return -distancia_min_total


def objetivo_distancia_fallas(
    fallas: List[List[Tuple[float, float]]],
    distancia_critica: float = 5.0
) -> ObjetivoDistanciaFallas:
    """Factory function para objetivo de distancia a fallas."""
    return ObjetivoDistanciaFallas(
        fallas=fallas,
        distancia_critica=distancia_critica
    )


# =============================================================================
# OBJETIVO: DISTANCIA A VOLCANES
# =============================================================================

@dataclass
class ObjetivoDistanciaVolcanes(FuncionObjetivo):
    """
    Maximiza la distancia a volcanes activos.
    
    Attributes
    ----------
    volcanes : List[Dict[str, Any]]
        Lista de volcanes con 'lat', 'lon', y opcionalmente 'radio_peligro'
    usar_radio_peligro : bool
        Si True, penaliza más fuertemente dentro del radio de peligro
    """
    nombre: str = "Distancia a Volcanes"
    tipo: TipoOptimizacion = TipoOptimizacion.MAXIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.GEOLOGICO
    unidad: str = "km (negativo)"
    descripcion: str = "Maximiza distancia a volcanes activos"
    
    volcanes: List[Dict[str, Any]] = field(default_factory=list)
    usar_radio_peligro: bool = True
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa la distancia a volcanes."""
        if not self.volcanes:
            return 0.0
        
        penalizacion_total = 0.0
        
        for lat, lon in coordenadas:
            for volcan in self.volcanes:
                v_lat = volcan['lat']
                v_lon = volcan['lon']
                radio = volcan.get('radio_peligro', 15.0)  # km por defecto
                
                dist = distancia_haversine(lat, lon, v_lat, v_lon)
                
                if self.usar_radio_peligro and dist < radio:
                    # Penalización exponencial dentro del radio
                    penalizacion = (radio - dist) ** 2
                else:
                    penalizacion = -dist
                
                penalizacion_total += penalizacion
        
        return penalizacion_total


def objetivo_distancia_volcanes(
    volcanes: List[Dict[str, Any]],
    usar_radio_peligro: bool = True
) -> ObjetivoDistanciaVolcanes:
    """Factory function para objetivo de distancia a volcanes."""
    return ObjetivoDistanciaVolcanes(
        volcanes=volcanes,
        usar_radio_peligro=usar_radio_peligro
    )


# =============================================================================
# OBJETIVO: PENDIENTE DEL TERRENO
# =============================================================================

@dataclass
class ObjetivoPendiente(FuncionObjetivo):
    """
    Minimiza la pendiente del terreno.
    
    Attributes
    ----------
    dem : np.ndarray
        Modelo Digital de Elevación
    bounds : Tuple[float, float, float, float]
        Límites del DEM
    resolucion : float
        Resolución del DEM en metros
    pendiente_cache : Optional[np.ndarray]
        Grilla de pendientes pre-calculada
    """
    nombre: str = "Pendiente del Terreno"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.GEOLOGICO
    unidad: str = "grados"
    descripcion: str = "Minimiza la pendiente del terreno"
    
    dem: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    resolucion: float = 30.0  # metros
    pendiente_cache: Optional[np.ndarray] = None
    
    def __post_init__(self):
        """Calcula la grilla de pendientes si no existe."""
        if self.dem is not None and self.pendiente_cache is None:
            self._calcular_pendiente()
    
    def _calcular_pendiente(self) -> None:
        """Calcula la pendiente del DEM usando gradientes."""
        if self.dem is None:
            return
        
        # Calcular gradientes
        gy, gx = np.gradient(self.dem, self.resolucion)
        
        # Pendiente en grados
        self.pendiente_cache = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa la pendiente promedio en las coordenadas."""
        if self.pendiente_cache is None or self.bounds is None:
            return 0.0
        
        pendientes = []
        for lat, lon in coordenadas:
            pendiente = interpolar_raster(
                lat, lon, self.pendiente_cache, self.bounds, nodata=0.0
            )
            pendientes.append(pendiente)
        
        return float(np.mean(pendientes))


def objetivo_pendiente(
    dem: np.ndarray,
    bounds: Tuple[float, float, float, float],
    resolucion: float = 30.0
) -> ObjetivoPendiente:
    """Factory function para objetivo de pendiente."""
    return ObjetivoPendiente(
        dem=dem,
        bounds=bounds,
        resolucion=resolucion
    )


# =============================================================================
# OBJETIVO PERSONALIZADO
# =============================================================================

@dataclass
class ObjetivoPersonalizado(FuncionObjetivo):
    """
    Permite crear un objetivo personalizado con una función lambda.
    
    Examples
    --------
    >>> # Objetivo: minimizar distancia al centro (19.4, -103.6)
    >>> objetivo = crear_objetivo_personalizado(
    ...     nombre="Distancia al centro",
    ...     funcion=lambda coords: np.mean([
    ...         distancia_haversine(c[0], c[1], 19.4, -103.6) 
    ...         for c in coords
    ...     ]),
    ...     tipo=TipoOptimizacion.MINIMIZAR
    ... )
    """
    funcion: Optional[Callable[[List[Tuple[float, float]]], float]] = None
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa usando la función personalizada."""
        if self.funcion is None:
            raise ValueError("Función no configurada")
        return self.funcion(coordenadas)


def crear_objetivo_personalizado(
    nombre: str,
    funcion: Callable[[List[Tuple[float, float]]], float],
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR,
    categoria: CategoriaObjetivo = CategoriaObjetivo.RIESGO_SISMICO,
    unidad: str = "",
    descripcion: str = ""
) -> ObjetivoPersonalizado:
    """
    Crea un objetivo personalizado con una función arbitraria.
    
    Parameters
    ----------
    nombre : str
        Nombre del objetivo
    funcion : Callable
        Función que recibe List[Tuple[lat, lon]] y retorna float
    tipo : TipoOptimizacion
        Minimizar o maximizar
    categoria : CategoriaObjetivo
        Categoría del objetivo
    unidad : str
        Unidad de medida
    descripcion : str
        Descripción detallada
        
    Returns
    -------
    ObjetivoPersonalizado
        Instancia configurada
    """
    return ObjetivoPersonalizado(
        nombre=nombre,
        funcion=funcion,
        tipo=tipo,
        categoria=categoria,
        unidad=unidad,
        descripcion=descripcion
    )


# =============================================================================
# OBJETIVOS COMPUESTOS
# =============================================================================

@dataclass
class ObjetivoCompuesto(FuncionObjetivo):
    """
    Combina múltiples objetivos en uno solo con pesos.
    
    Attributes
    ----------
    objetivos : List[FuncionObjetivo]
        Lista de objetivos a combinar
    pesos : List[float]
        Pesos para cada objetivo
    normalizar : bool
        Si normalizar los valores antes de combinar
    """
    nombre: str = "Objetivo Compuesto"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    
    objetivos: List[FuncionObjetivo] = field(default_factory=list)
    pesos: Optional[List[float]] = None
    normalizar_valores: bool = True
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa la combinación ponderada de objetivos."""
        if not self.objetivos:
            return 0.0
        
        pesos = self.pesos or [1.0] * len(self.objetivos)
        pesos = np.array(pesos) / np.sum(pesos)
        
        valores = []
        for obj in self.objetivos:
            valor = obj.evaluar(coordenadas)
            valores.append(valor)
        
        valores = np.array(valores)
        
        return float(np.dot(valores, pesos))


def crear_objetivo_compuesto(
    objetivos: List[FuncionObjetivo],
    pesos: Optional[List[float]] = None,
    nombre: str = "Objetivo Compuesto"
) -> ObjetivoCompuesto:
    """Crea un objetivo que combina múltiples objetivos."""
    return ObjetivoCompuesto(
        nombre=nombre,
        objetivos=objetivos,
        pesos=pesos
    )


# =============================================================================
# INFORMACIÓN DEL MÓDULO
# =============================================================================

def listar_objetivos() -> List[str]:
    """Lista todos los objetivos disponibles."""
    return [
        "objetivo_riesgo_esd - Minimizar riesgo sísmico (ESD)",
        "objetivo_costo_construccion - Minimizar costo de construcción",
        "objetivo_impacto_ambiental - Minimizar impacto ambiental",
        "objetivo_accesibilidad - Maximizar accesibilidad",
        "objetivo_distancia_fallas - Maximizar distancia a fallas",
        "objetivo_distancia_volcanes - Maximizar distancia a volcanes",
        "objetivo_pendiente - Minimizar pendiente del terreno",
        "crear_objetivo_personalizado - Crear objetivo con función lambda",
        "crear_objetivo_compuesto - Combinar múltiples objetivos",
    ]


def info_modulo():
    """Muestra información del módulo objectives."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              SEISMEX Optimization - objectives.py                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Funciones objetivo implementadas:                                   ║
║    ✅ objetivo_riesgo_esd          - Riesgo sísmico (ESD)            ║
║    ✅ objetivo_costo_construccion  - Costo económico                 ║
║    ✅ objetivo_impacto_ambiental   - Impacto ambiental               ║
║    ✅ objetivo_accesibilidad       - Accesibilidad a servicios       ║
║    ✅ objetivo_distancia_fallas    - Distancia a fallas              ║
║    ✅ objetivo_distancia_volcanes  - Distancia a volcanes            ║
║    ✅ objetivo_pendiente           - Pendiente del terreno           ║
║    ✅ crear_objetivo_personalizado - Objetivo con función lambda     ║
║    ✅ crear_objetivo_compuesto     - Combinación de objetivos        ║
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
    'TipoOptimizacion',
    'CategoriaObjetivo',
    
    # Clase base
    'FuncionObjetivo',
    
    # Clases de objetivos
    'ObjetivoRiesgoESD',
    'ObjetivoCostoConstruccion',
    'ObjetivoImpactoAmbiental',
    'ObjetivoAccesibilidad',
    'ObjetivoDistanciaFallas',
    'ObjetivoDistanciaVolcanes',
    'ObjetivoPendiente',
    'ObjetivoPersonalizado',
    'ObjetivoCompuesto',
    
    # Factory functions
    'objetivo_riesgo_esd',
    'objetivo_costo_construccion',
    'objetivo_impacto_ambiental',
    'objetivo_accesibilidad',
    'objetivo_distancia_fallas',
    'objetivo_distancia_volcanes',
    'objetivo_pendiente',
    'crear_objetivo_personalizado',
    'crear_objetivo_compuesto',
    
    # Utilidades
    'distancia_haversine',
    'interpolar_raster',
    'listar_objetivos',
    'info_modulo',
]
