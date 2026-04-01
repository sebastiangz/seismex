#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Optimization - Funciones Objetivo
================================================================================

Funciones objetivo predefinidas para optimización de ubicación de
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
    TYPE_CHECKING
)
from enum import Enum
import numpy as np

if TYPE_CHECKING:
    from seismex.analysis.esd import ResultadoESD
    import geopandas as gpd

logger = logging.getLogger(__name__)


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
    
    Examples
    --------
    >>> class MiObjetivo(FuncionObjetivo):
    ...     def evaluar(self, coordenadas):
    ...         # Implementar lógica
    ...         return valor
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
            Valor del objetivo (siempre para minimización)
        """
        pass
    
    def __call__(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Permite usar la instancia como función."""
        return self.evaluar(coordenadas)
    
    def normalizar(self, valor: float, vmin: float, vmax: float) -> float:
        """
        Normaliza un valor al rango [0, 1].
        
        Parameters
        ----------
        valor : float
            Valor a normalizar
        vmin : float
            Valor mínimo esperado
        vmax : float
            Valor máximo esperado
            
        Returns
        -------
        float
            Valor normalizado entre 0 y 1
        """
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
    en cada ubicación candidata.
    
    Attributes
    ----------
    resultado_esd : ResultadoESD
        Resultado del análisis ESD
    profundidad_km : float
        Profundidad para evaluación (default: 30 km)
    metodo_agregacion : str
        Cómo agregar múltiples sitios: 'max', 'mean', 'sum'
    
    Examples
    --------
    >>> from seismex.analysis import CalculadoraESD
    >>> resultado = calculadora.calcular_esd(catalogo)
    >>> objetivo = objetivo_riesgo_esd(resultado, profundidad_km=30)
    >>> riesgo = objetivo.evaluar([(19.3, -103.5)])
    """
    nombre: str = "Riesgo Sísmico (ESD)"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.RIESGO_SISMICO
    unidad: str = "log₁₀(ESD)"
    descripcion: str = "Minimiza la densidad de energía sísmica en la ubicación"
    
    # Parámetros específicos
    resultado_esd: Optional['ResultadoESD'] = None
    profundidad_km: float = 30.0
    metodo_agregacion: str = "max"
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa el riesgo ESD para las coordenadas dadas.
        
        Parameters
        ----------
        coordenadas : List[Tuple[float, float]]
            Lista de tuplas (latitud, longitud)
            
        Returns
        -------
        float
            Valor ESD (mayor = más riesgo)
        """
        if self.resultado_esd is None:
            raise ValueError("resultado_esd no configurado")
        
        # TODO: Implementar interpolación del valor ESD
        raise NotImplementedError(
            "Evaluación de ESD pendiente de implementación.\n"
            "Requiere interpolación del grid ESD en las coordenadas dadas."
        )


def objetivo_riesgo_esd(
    resultado_esd: 'ResultadoESD',
    profundidad_km: float = 30.0,
    metodo_agregacion: str = "max"
) -> ObjetivoRiesgoESD:
    """
    Factory function para crear objetivo de riesgo ESD.
    
    Parameters
    ----------
    resultado_esd : ResultadoESD
        Resultado del análisis ESD
    profundidad_km : float
        Profundidad para evaluación (default: 30 km)
    metodo_agregacion : str
        Cómo agregar múltiples sitios: 'max', 'mean', 'sum'
        
    Returns
    -------
    ObjetivoRiesgoESD
        Instancia configurada del objetivo
        
    Examples
    --------
    >>> objetivo = objetivo_riesgo_esd(resultado, profundidad_km=30)
    >>> optimizador.agregar_objetivo(objetivo)
    """
    return ObjetivoRiesgoESD(
        resultado_esd=resultado_esd,
        profundidad_km=profundidad_km,
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
    mapa_costos : Union[np.ndarray, Any]
        Grilla de costos o raster con precios por m²
    bounds : Tuple[float, float, float, float]
        Límites del mapa (lon_min, lat_min, lon_max, lat_max)
    costo_base : float
        Costo base de construcción (USD/m²)
    
    Examples
    --------
    >>> objetivo = objetivo_costo_construccion(mapa_costos, bounds)
    >>> costo = objetivo.evaluar([(19.3, -103.5)])
    """
    nombre: str = "Costo de Construcción"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.ECONOMICO
    unidad: str = "USD/m²"
    descripcion: str = "Minimiza el costo de construcción en la ubicación"
    
    # Parámetros específicos
    mapa_costos: Optional[np.ndarray] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    costo_base: float = 1000.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa el costo para las coordenadas dadas."""
        # TODO: Implementar interpolación del mapa de costos
        raise NotImplementedError("Evaluación de costos pendiente")


def objetivo_costo_construccion(
    mapa_costos: np.ndarray,
    bounds: Tuple[float, float, float, float],
    costo_base: float = 1000.0
) -> ObjetivoCostoConstruccion:
    """
    Factory function para crear objetivo de costo de construcción.
    
    Parameters
    ----------
    mapa_costos : np.ndarray
        Grilla de costos
    bounds : Tuple[float, float, float, float]
        Límites (lon_min, lat_min, lon_max, lat_max)
    costo_base : float
        Costo base (default: 1000 USD/m²)
        
    Returns
    -------
    ObjetivoCostoConstruccion
        Instancia configurada
    """
    return ObjetivoCostoConstruccion(
        mapa_costos=mapa_costos,
        bounds=bounds,
        costo_base=costo_base
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
    capas_sensibilidad : Dict[str, Any]
        Diccionario de capas (áreas protegidas, humedales, etc.)
    pesos_capas : Dict[str, float]
        Pesos relativos de cada capa
    
    Examples
    --------
    >>> objetivo = objetivo_impacto_ambiental({
    ...     'areas_protegidas': gdf_anp,
    ...     'humedales': gdf_humedales
    ... })
    """
    nombre: str = "Impacto Ambiental"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.AMBIENTAL
    unidad: str = "índice (0-1)"
    descripcion: str = "Minimiza el impacto ambiental en zonas sensibles"
    
    # Parámetros específicos
    capas_sensibilidad: Dict[str, Any] = field(default_factory=dict)
    pesos_capas: Dict[str, float] = field(default_factory=dict)
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa el impacto ambiental."""
        # TODO: Implementar evaluación de capas de sensibilidad
        raise NotImplementedError("Evaluación de impacto ambiental pendiente")


def objetivo_impacto_ambiental(
    capas_sensibilidad: Dict[str, Any],
    pesos_capas: Optional[Dict[str, float]] = None
) -> ObjetivoImpactoAmbiental:
    """Factory function para objetivo de impacto ambiental."""
    if pesos_capas is None:
        pesos_capas = {k: 1.0 for k in capas_sensibilidad}
    
    return ObjetivoImpactoAmbiental(
        capas_sensibilidad=capas_sensibilidad,
        pesos_capas=pesos_capas
    )


# =============================================================================
# OBJETIVO: ACCESIBILIDAD
# =============================================================================

@dataclass
class ObjetivoAccesibilidad(FuncionObjetivo):
    """
    Maximiza la accesibilidad a servicios y vías de comunicación.
    
    NOTA: Se implementa como minimización del negativo.
    
    Attributes
    ----------
    red_vial : Any
        GeoDataFrame o similar con la red vial
    puntos_interes : List[Tuple[float, float]]
        Lista de puntos de interés a considerar
    tipo_distancia : str
        'euclidiana' o 'red' (distancia en red)
    
    Examples
    --------
    >>> objetivo = objetivo_accesibilidad(red_vial, hospitales)
    """
    nombre: str = "Accesibilidad"
    tipo: TipoOptimizacion = TipoOptimizacion.MAXIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.ACCESIBILIDAD
    unidad: str = "km (negativo)"
    descripcion: str = "Maximiza accesibilidad (minimiza distancia a servicios)"
    
    # Parámetros específicos
    red_vial: Optional[Any] = None
    puntos_interes: List[Tuple[float, float]] = field(default_factory=list)
    tipo_distancia: str = "euclidiana"
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """
        Evalúa la accesibilidad (retorna negativo para minimización).
        """
        # TODO: Implementar cálculo de accesibilidad
        raise NotImplementedError("Evaluación de accesibilidad pendiente")


def objetivo_accesibilidad(
    red_vial: Optional[Any] = None,
    puntos_interes: Optional[List[Tuple[float, float]]] = None,
    tipo_distancia: str = "euclidiana"
) -> ObjetivoAccesibilidad:
    """Factory function para objetivo de accesibilidad."""
    return ObjetivoAccesibilidad(
        red_vial=red_vial,
        puntos_interes=puntos_interes or [],
        tipo_distancia=tipo_distancia
    )


# =============================================================================
# OBJETIVO: DISTANCIA A FALLAS
# =============================================================================

@dataclass
class ObjetivoDistanciaFallas(FuncionObjetivo):
    """
    Maximiza la distancia a fallas geológicas activas.
    
    Se implementa como minimización del negativo.
    
    Attributes
    ----------
    fallas : Any
        GeoDataFrame con geometrías de fallas
    distancia_critica : float
        Distancia mínima considerada segura (km)
    
    Examples
    --------
    >>> objetivo = objetivo_distancia_fallas(gdf_fallas, distancia_critica=5)
    """
    nombre: str = "Distancia a Fallas"
    tipo: TipoOptimizacion = TipoOptimizacion.MAXIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.GEOLOGICO
    unidad: str = "km (negativo)"
    descripcion: str = "Maximiza distancia a fallas geológicas activas"
    
    # Parámetros específicos
    fallas: Optional[Any] = None
    distancia_critica: float = 5.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa la distancia a fallas (retorna negativo)."""
        # TODO: Implementar cálculo de distancia a fallas
        raise NotImplementedError("Evaluación de distancia a fallas pendiente")


def objetivo_distancia_fallas(
    fallas: Any,
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
        Lista de volcanes con 'lat', 'lon', 'tipo', 'radio_peligro'
    considerar_tipo : bool
        Si True, ajusta radio según tipo de volcán
    
    Examples
    --------
    >>> volcanes = [
    ...     {'lat': 19.514, 'lon': -103.617, 'nombre': 'Colima', 'radio_peligro': 15}
    ... ]
    >>> objetivo = objetivo_distancia_volcanes(volcanes)
    """
    nombre: str = "Distancia a Volcanes"
    tipo: TipoOptimizacion = TipoOptimizacion.MAXIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.GEOLOGICO
    unidad: str = "km (negativo)"
    descripcion: str = "Maximiza distancia a volcanes activos"
    
    # Parámetros específicos
    volcanes: List[Dict[str, Any]] = field(default_factory=list)
    considerar_tipo: bool = True
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa la distancia a volcanes."""
        # TODO: Implementar cálculo de distancia a volcanes
        raise NotImplementedError("Evaluación de distancia a volcanes pendiente")


def objetivo_distancia_volcanes(
    volcanes: List[Dict[str, Any]],
    considerar_tipo: bool = True
) -> ObjetivoDistanciaVolcanes:
    """Factory function para objetivo de distancia a volcanes."""
    return ObjetivoDistanciaVolcanes(
        volcanes=volcanes,
        considerar_tipo=considerar_tipo
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
    dem : Any
        Modelo Digital de Elevación (raster)
    pendiente_maxima : float
        Pendiente máxima permitida (grados)
    
    Examples
    --------
    >>> objetivo = objetivo_pendiente(dem_raster, pendiente_maxima=15)
    """
    nombre: str = "Pendiente del Terreno"
    tipo: TipoOptimizacion = TipoOptimizacion.MINIMIZAR
    categoria: CategoriaObjetivo = CategoriaObjetivo.GEOLOGICO
    unidad: str = "grados"
    descripcion: str = "Minimiza la pendiente del terreno"
    
    # Parámetros específicos
    dem: Optional[Any] = None
    pendiente_maxima: float = 15.0
    
    def evaluar(self, coordenadas: List[Tuple[float, float]]) -> float:
        """Evalúa la pendiente en las coordenadas."""
        # TODO: Implementar cálculo de pendiente desde DEM
        raise NotImplementedError("Evaluación de pendiente pendiente")


def objetivo_pendiente(
    dem: Any,
    pendiente_maxima: float = 15.0
) -> ObjetivoPendiente:
    """Factory function para objetivo de pendiente."""
    return ObjetivoPendiente(
        dem=dem,
        pendiente_maxima=pendiente_maxima
    )


# =============================================================================
# OBJETIVO PERSONALIZADO
# =============================================================================

@dataclass
class ObjetivoPersonalizado(FuncionObjetivo):
    """
    Permite crear un objetivo personalizado con una función lambda.
    
    Attributes
    ----------
    funcion : Callable
        Función que recibe coordenadas y retorna un valor
    
    Examples
    --------
    >>> # Objetivo: minimizar distancia al centro (19.4, -103.6)
    >>> objetivo = crear_objetivo_personalizado(
    ...     nombre="Distancia al centro",
    ...     funcion=lambda coords: np.mean([
    ...         np.sqrt((c[0]-19.4)**2 + (c[1]+103.6)**2) 
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
        
    Examples
    --------
    >>> objetivo = crear_objetivo_personalizado(
    ...     nombre="Mi objetivo",
    ...     funcion=lambda coords: sum(c[0] + c[1] for c in coords),
    ...     tipo=TipoOptimizacion.MINIMIZAR
    ... )
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
    ]


def info_modulo():
    """Muestra información del módulo objectives."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              SEISMEX Optimization - objectives.py                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Funciones objetivo disponibles:                                     ║
║    • objetivo_riesgo_esd          - Riesgo sísmico (ESD)             ║
║    • objetivo_costo_construccion  - Costo económico                  ║
║    • objetivo_impacto_ambiental   - Impacto ambiental                ║
║    • objetivo_accesibilidad       - Accesibilidad a servicios        ║
║    • objetivo_distancia_fallas    - Distancia a fallas               ║
║    • objetivo_distancia_volcanes  - Distancia a volcanes             ║
║    • objetivo_pendiente           - Pendiente del terreno            ║
║    • crear_objetivo_personalizado - Objetivo con función lambda      ║
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
    
    # Factory functions
    'objetivo_riesgo_esd',
    'objetivo_costo_construccion',
    'objetivo_impacto_ambiental',
    'objetivo_accesibilidad',
    'objetivo_distancia_fallas',
    'objetivo_distancia_volcanes',
    'objetivo_pendiente',
    'crear_objetivo_personalizado',
    
    # Utilidades
    'listar_objetivos',
    'info_modulo',
]
