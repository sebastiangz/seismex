#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Optimization - Motor de Algoritmo Genético NSGA-II
================================================================================

Implementación completa del algoritmo NSGA-II (Non-dominated Sorting Genetic 
Algorithm II) para optimización multiobjetivo de ubicación de infraestructura 
considerando riesgo sísmico.

Basado en:
    Deb, K., et al. (2002). "A fast and elitist multiobjective genetic 
    algorithm: NSGA-II." IEEE Transactions on Evolutionary Computation, 
    6(2), 182-197.

Clases principales:
    - ConfiguracionNSGAII: Parámetros del algoritmo
    - Individuo: Representación de una solución candidata
    - Poblacion: Conjunto de individuos
    - OptimizadorNSGAII: Motor principal de optimización

Estado: ✅ IMPLEMENTADO

Autor: SEISMEX Team
Versión: 1.0.0
================================================================================
"""

from __future__ import annotations

import logging
import time
import warnings
from dataclasses import dataclass, field
from typing import (
    List, 
    Optional, 
    Callable, 
    Tuple, 
    Dict, 
    Any,
    Union,
    TYPE_CHECKING
)
from abc import ABC, abstractmethod
from enum import Enum
from copy import deepcopy
import numpy as np

if TYPE_CHECKING:
    from .objectives import FuncionObjetivo
    from .constraints import Restriccion

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoCodificacion(Enum):
    """Tipos de codificación para individuos."""
    REAL = "real"
    BINARIA = "binaria"
    ENTERA = "entera"
    PERMUTACION = "permutacion"


class TipoSeleccion(Enum):
    """Métodos de selección de padres."""
    TORNEO = "torneo"
    RULETA = "ruleta"
    RANKING = "ranking"


class TipoCruce(Enum):
    """Operadores de cruce."""
    SBX = "sbx"
    BLX_ALPHA = "blx_alpha"
    UN_PUNTO = "un_punto"
    DOS_PUNTOS = "dos_puntos"
    UNIFORME = "uniforme"


class TipoMutacion(Enum):
    """Operadores de mutación."""
    POLINOMIAL = "polinomial"
    GAUSSIANA = "gaussiana"
    UNIFORME = "uniforme"
    INTERCAMBIO = "intercambio"


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

@dataclass
class ConfiguracionNSGAII:
    """
    Configuración del algoritmo NSGA-II.
    
    Attributes
    ----------
    n_generaciones : int
        Número máximo de generaciones (default: 100)
    tamano_poblacion : int
        Tamaño de la población (default: 100, debe ser par)
    prob_cruce : float
        Probabilidad de cruce (default: 0.9)
    prob_mutacion : float
        Probabilidad de mutación (default: 0.1)
    eta_cruce : float
        Índice de distribución para SBX (default: 20)
    eta_mutacion : float
        Índice de distribución para mutación polinomial (default: 20)
    tipo_codificacion : TipoCodificacion
        Tipo de codificación de individuos (default: REAL)
    tipo_seleccion : TipoSeleccion
        Método de selección de padres (default: TORNEO)
    tamano_torneo : int
        Tamaño del torneo para selección (default: 2)
    tipo_cruce : TipoCruce
        Operador de cruce (default: SBX)
    tipo_mutacion : TipoMutacion
        Operador de mutación (default: POLINOMIAL)
    semilla : Optional[int]
        Semilla para reproducibilidad (default: None)
    n_sitios : int
        Número de sitios a optimizar (default: 1)
    verbose : bool
        Mostrar progreso (default: True)
    guardar_historial : bool
        Guardar historial de evolución (default: True)
    criterio_parada_generaciones : int
        Detener si no hay mejora en N generaciones (default: 20)
    tolerancia_convergencia : float
        Tolerancia para considerar convergencia (default: 1e-6)
    penalizacion_restriccion : float
        Factor de penalización para restricciones violadas (default: 1e6)
    """
    # Parámetros principales
    n_generaciones: int = 100
    tamano_poblacion: int = 100
    prob_cruce: float = 0.9
    prob_mutacion: float = 0.1
    
    # Parámetros de operadores
    eta_cruce: float = 20.0
    eta_mutacion: float = 20.0
    
    # Tipos de operadores
    tipo_codificacion: TipoCodificacion = TipoCodificacion.REAL
    tipo_seleccion: TipoSeleccion = TipoSeleccion.TORNEO
    tamano_torneo: int = 2
    tipo_cruce: TipoCruce = TipoCruce.SBX
    tipo_mutacion: TipoMutacion = TipoMutacion.POLINOMIAL
    
    # Control
    semilla: Optional[int] = None
    n_sitios: int = 1
    verbose: bool = True
    guardar_historial: bool = True
    
    # Criterios de parada
    criterio_parada_generaciones: int = 20
    tolerancia_convergencia: float = 1e-6
    
    # Penalización
    penalizacion_restriccion: float = 1e6
    
    def __post_init__(self):
        """Validación de parámetros."""
        if self.tamano_poblacion % 2 != 0:
            self.tamano_poblacion += 1
            logger.warning(
                f"Tamaño de población ajustado a {self.tamano_poblacion} (debe ser par)"
            )
        
        if not 0 <= self.prob_cruce <= 1:
            raise ValueError("prob_cruce debe estar entre 0 y 1")
        
        if not 0 <= self.prob_mutacion <= 1:
            raise ValueError("prob_mutacion debe estar entre 0 y 1")
        
        if self.n_sitios < 1:
            raise ValueError("n_sitios debe ser al menos 1")


# =============================================================================
# INDIVIDUO
# =============================================================================

@dataclass
class Individuo:
    """
    Representa una solución candidata (individuo) en el algoritmo genético.
    
    Attributes
    ----------
    genes : np.ndarray
        Vector de genes (coordenadas, índices, etc.)
    objetivos : Optional[np.ndarray]
        Valores de las funciones objetivo evaluadas
    restricciones : Optional[np.ndarray]
        Valores de violación de restricciones
    rango : int
        Rango de no-dominancia (frente de Pareto)
    distancia_crowding : float
        Distancia de crowding para diversidad
    factible : bool
        Si el individuo cumple todas las restricciones
    """
    genes: np.ndarray
    objetivos: Optional[np.ndarray] = None
    restricciones: Optional[np.ndarray] = None
    rango: int = 0
    distancia_crowding: float = 0.0
    factible: bool = True
    generacion_creado: int = 0
    id_individuo: Optional[str] = None
    
    def __post_init__(self):
        """Inicialización adicional."""
        if self.id_individuo is None:
            import uuid
            self.id_individuo = str(uuid.uuid4())[:8]
    
    def __lt__(self, other: 'Individuo') -> bool:
        """
        Comparación para ordenamiento (crowded comparison operator).
        Mejor = menor rango, o mismo rango pero mayor distancia crowding.
        """
        if self.rango != other.rango:
            return self.rango < other.rango
        return self.distancia_crowding > other.distancia_crowding
    
    def __eq__(self, other: 'Individuo') -> bool:
        """Igualdad basada en genes."""
        if not isinstance(other, Individuo):
            return False
        return np.allclose(self.genes, other.genes)
    
    def __hash__(self) -> int:
        """Hash basado en ID."""
        return hash(self.id_individuo)
    
    def domina(self, other: 'Individuo') -> bool:
        """
        Verifica si este individuo domina a otro (minimización).
        
        Un individuo A domina a B si:
        - A es al menos tan bueno como B en todos los objetivos
        - A es estrictamente mejor en al menos un objetivo
        
        Parameters
        ----------
        other : Individuo
            Otro individuo a comparar
            
        Returns
        -------
        bool
            True si este individuo domina al otro
        """
        if self.objetivos is None or other.objetivos is None:
            return False
        
        # Constraint-domination: factibles dominan a no factibles
        if self.factible and not other.factible:
            return True
        if not self.factible and other.factible:
            return False
        
        # Si ambos son no factibles, comparar por violación total
        if not self.factible and not other.factible:
            if self.restricciones is not None and other.restricciones is not None:
                return np.sum(self.restricciones) < np.sum(other.restricciones)
            return False
        
        # Ambos factibles: comparación por objetivos (minimización)
        al_menos_igual = np.all(self.objetivos <= other.objetivos)
        estrictamente_mejor = np.any(self.objetivos < other.objetivos)
        
        return al_menos_igual and estrictamente_mejor
    
    def copiar(self) -> 'Individuo':
        """Crea una copia profunda del individuo."""
        return Individuo(
            genes=self.genes.copy(),
            objetivos=self.objetivos.copy() if self.objetivos is not None else None,
            restricciones=self.restricciones.copy() if self.restricciones is not None else None,
            rango=self.rango,
            distancia_crowding=self.distancia_crowding,
            factible=self.factible,
            generacion_creado=self.generacion_creado
        )
    
    def decodificar_coordenadas(self) -> List[Tuple[float, float]]:
        """
        Decodifica genes a lista de coordenadas (lat, lon).
        
        Returns
        -------
        List[Tuple[float, float]]
            Lista de tuplas (latitud, longitud)
        """
        coords = []
        for i in range(0, len(self.genes), 2):
            lat = self.genes[i]
            lon = self.genes[i + 1]
            coords.append((lat, lon))
        return coords
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'id': self.id_individuo,
            'genes': self.genes.tolist(),
            'coordenadas': self.decodificar_coordenadas(),
            'objetivos': self.objetivos.tolist() if self.objetivos is not None else None,
            'restricciones': self.restricciones.tolist() if self.restricciones is not None else None,
            'rango': self.rango,
            'distancia_crowding': self.distancia_crowding,
            'factible': self.factible,
            'generacion': self.generacion_creado
        }


# =============================================================================
# POBLACIÓN
# =============================================================================

@dataclass
class Poblacion:
    """
    Representa una población de individuos.
    
    Attributes
    ----------
    individuos : List[Individuo]
        Lista de individuos en la población
    generacion : int
        Número de generación actual
    """
    individuos: List[Individuo] = field(default_factory=list)
    generacion: int = 0
    
    def __len__(self) -> int:
        return len(self.individuos)
    
    def __iter__(self):
        return iter(self.individuos)
    
    def __getitem__(self, idx) -> Individuo:
        return self.individuos[idx]
    
    def agregar(self, individuo: Individuo) -> None:
        """Agrega un individuo a la población."""
        self.individuos.append(individuo)
    
    def extender(self, individuos: List[Individuo]) -> None:
        """Agrega múltiples individuos."""
        self.individuos.extend(individuos)
    
    def limpiar(self) -> None:
        """Elimina todos los individuos."""
        self.individuos.clear()
    
    @classmethod
    def generar_aleatoria(
        cls,
        tamano: int,
        n_genes: int,
        limites: List[Tuple[float, float]],
        semilla: Optional[int] = None
    ) -> 'Poblacion':
        """
        Genera una población inicial aleatoria.
        
        Parameters
        ----------
        tamano : int
            Número de individuos
        n_genes : int
            Número de genes por individuo
        limites : List[Tuple[float, float]]
            Límites (min, max) para cada gen
        semilla : Optional[int]
            Semilla para reproducibilidad
            
        Returns
        -------
        Poblacion
            Población inicial generada
        """
        if semilla is not None:
            np.random.seed(semilla)
        
        individuos = []
        for _ in range(tamano):
            genes = np.array([
                np.random.uniform(limites[i][0], limites[i][1])
                for i in range(n_genes)
            ])
            individuos.append(Individuo(genes=genes, generacion_creado=0))
        
        return cls(individuos=individuos, generacion=0)
    
    def obtener_frente_pareto(self, frente: int = 0) -> List[Individuo]:
        """
        Obtiene individuos del frente de Pareto especificado.
        
        Parameters
        ----------
        frente : int
            Número de frente (0 = primer frente, mejor)
            
        Returns
        -------
        List[Individuo]
            Individuos en ese frente
        """
        return [ind for ind in self.individuos if ind.rango == frente]
    
    def obtener_mejores(self, n: int = 10) -> List[Individuo]:
        """Obtiene los n mejores individuos."""
        ordenados = sorted(self.individuos)
        return ordenados[:n]
    
    def obtener_factibles(self) -> List[Individuo]:
        """Obtiene todos los individuos factibles."""
        return [ind for ind in self.individuos if ind.factible]
    
    def estadisticas(self) -> Dict[str, Any]:
        """Calcula estadísticas de la población."""
        if not self.individuos:
            return {}
        
        factibles = [ind for ind in self.individuos if ind.factible]
        
        stats = {
            'n_individuos': len(self.individuos),
            'generacion': self.generacion,
            'n_factibles': len(factibles),
            'porcentaje_factibles': len(factibles) / len(self.individuos) * 100,
        }
        
        if self.individuos[0].objetivos is not None:
            objetivos = np.array([ind.objetivos for ind in self.individuos])
            stats.update({
                'n_frentes': max(ind.rango for ind in self.individuos) + 1,
                'objetivo_min': objetivos.min(axis=0).tolist(),
                'objetivo_max': objetivos.max(axis=0).tolist(),
                'objetivo_mean': objetivos.mean(axis=0).tolist(),
                'objetivo_std': objetivos.std(axis=0).tolist(),
            })
            
            # Stats solo de factibles
            if factibles and factibles[0].objetivos is not None:
                obj_fact = np.array([ind.objetivos for ind in factibles])
                stats['objetivo_min_factibles'] = obj_fact.min(axis=0).tolist()
        
        return stats


# =============================================================================
# RESULTADO DE OPTIMIZACIÓN
# =============================================================================

@dataclass
class ResultadoOptimizacion:
    """
    Contenedor de resultados de la optimización.
    
    Attributes
    ----------
    frente_pareto : List[Individuo]
        Soluciones no dominadas (primer frente)
    poblacion_final : Poblacion
        Población de la última generación
    historial : List[Dict]
        Historial de estadísticas por generación
    config : ConfiguracionNSGAII
        Configuración utilizada
    tiempo_ejecucion : float
        Tiempo total de ejecución (segundos)
    convergencia : bool
        Si el algoritmo convergió
    generaciones_ejecutadas : int
        Número de generaciones ejecutadas
    nombres_objetivos : List[str]
        Nombres de las funciones objetivo
    """
    frente_pareto: List[Individuo]
    poblacion_final: Poblacion
    historial: List[Dict[str, Any]]
    config: ConfiguracionNSGAII
    tiempo_ejecucion: float
    convergencia: bool
    generaciones_ejecutadas: int
    nombres_objetivos: List[str] = field(default_factory=list)
    nombres_restricciones: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return (
            f"ResultadoOptimizacion(\n"
            f"  soluciones_pareto={len(self.frente_pareto)},\n"
            f"  generaciones={self.generaciones_ejecutadas},\n"
            f"  tiempo={self.tiempo_ejecucion:.2f}s,\n"
            f"  convergencia={self.convergencia}\n"
            f")"
        )
    
    def resumen(self) -> str:
        """Genera un resumen textual de los resultados."""
        lineas = [
            "=" * 60,
            "RESULTADOS DE OPTIMIZACIÓN NSGA-II",
            "=" * 60,
            f"Generaciones ejecutadas: {self.generaciones_ejecutadas}",
            f"Tiempo de ejecución: {self.tiempo_ejecucion:.2f} segundos",
            f"Convergencia alcanzada: {'Sí' if self.convergencia else 'No'}",
            "",
            f"Soluciones en frente de Pareto: {len(self.frente_pareto)}",
            f"Individuos factibles: {len(self.poblacion_final.obtener_factibles())}",
            "",
        ]
        
        if self.frente_pareto:
            lineas.append("Rango de valores objetivo:")
            objetivos = np.array([ind.objetivos for ind in self.frente_pareto])
            for i, nombre in enumerate(self.nombres_objetivos):
                lineas.append(
                    f"  {nombre}: [{objetivos[:, i].min():.4f}, {objetivos[:, i].max():.4f}]"
                )
        
        lineas.append("=" * 60)
        return "\n".join(lineas)
    
    def obtener_solucion_compromiso(
        self, 
        pesos: Optional[List[float]] = None
    ) -> Individuo:
        """
        Obtiene la solución de compromiso del frente de Pareto.
        
        Usa el método de la distancia euclidiana al punto ideal normalizado.
        
        Parameters
        ----------
        pesos : Optional[List[float]]
            Pesos para cada objetivo. Si None, pesos iguales.
            
        Returns
        -------
        Individuo
            Solución de compromiso
        """
        if not self.frente_pareto:
            raise ValueError("No hay soluciones en el frente de Pareto")
        
        objetivos = np.array([ind.objetivos for ind in self.frente_pareto])
        n_objetivos = objetivos.shape[1]
        
        if pesos is None:
            pesos = np.ones(n_objetivos) / n_objetivos
        else:
            pesos = np.array(pesos) / np.sum(pesos)
        
        # Normalizar objetivos
        obj_min = objetivos.min(axis=0)
        obj_max = objetivos.max(axis=0)
        rango = obj_max - obj_min
        rango[rango == 0] = 1  # Evitar división por cero
        
        objetivos_norm = (objetivos - obj_min) / rango
        
        # Punto ideal es (0, 0, ..., 0) en espacio normalizado
        distancias = np.sqrt(np.sum((objetivos_norm ** 2) * pesos, axis=1))
        
        idx_mejor = np.argmin(distancias)
        return self.frente_pareto[idx_mejor]
    
    def to_dataframe(self) -> 'pd.DataFrame':
        """Convierte el frente de Pareto a DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas es necesario para to_dataframe()")
        
        datos = []
        for ind in self.frente_pareto:
            fila = {'id': ind.id_individuo}
            coords = ind.decodificar_coordenadas()
            for i, (lat, lon) in enumerate(coords):
                fila[f'lat_{i}'] = lat
                fila[f'lon_{i}'] = lon
            
            if ind.objetivos is not None:
                for i, nombre in enumerate(self.nombres_objetivos):
                    fila[nombre] = ind.objetivos[i]
            
            fila['factible'] = ind.factible
            fila['rango'] = ind.rango
            datos.append(fila)
        
        return pd.DataFrame(datos)
    
    def to_geodataframe(self) -> 'gpd.GeoDataFrame':
        """Convierte el frente de Pareto a GeoDataFrame."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point, MultiPoint
        except ImportError:
            raise ImportError("geopandas y shapely son necesarios para to_geodataframe()")
        
        datos = []
        geometrias = []
        
        for ind in self.frente_pareto:
            fila = {'id': ind.id_individuo}
            coords = ind.decodificar_coordenadas()
            
            # Geometría: MultiPoint si hay varios sitios, Point si es uno
            if len(coords) == 1:
                geom = Point(coords[0][1], coords[0][0])  # lon, lat para shapely
            else:
                geom = MultiPoint([(lon, lat) for lat, lon in coords])
            geometrias.append(geom)
            
            if ind.objetivos is not None:
                for i, nombre in enumerate(self.nombres_objetivos):
                    fila[nombre] = ind.objetivos[i]
            
            fila['factible'] = ind.factible
            datos.append(fila)
        
        gdf = gpd.GeoDataFrame(datos, geometry=geometrias, crs="EPSG:4326")
        return gdf
    
    def exportar_geojson(self, ruta: str) -> None:
        """Exporta el frente de Pareto a GeoJSON."""
        gdf = self.to_geodataframe()
        gdf.to_file(ruta, driver='GeoJSON')
        logger.info(f"Exportado a {ruta}")
    
    def graficar_pareto(
        self,
        objetivos_xy: Tuple[int, int] = (0, 1),
        ax=None,
        **kwargs
    ):
        """
        Grafica el frente de Pareto (2D).
        
        Parameters
        ----------
        objetivos_xy : Tuple[int, int]
            Índices de los objetivos a graficar (x, y)
        ax : matplotlib.axes.Axes, optional
            Axes existente para graficar
        **kwargs
            Argumentos adicionales para scatter
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib es necesario para graficar_pareto()")
        
        if not self.frente_pareto:
            logger.warning("No hay soluciones en el frente de Pareto")
            return
        
        objetivos = np.array([ind.objetivos for ind in self.frente_pareto])
        i, j = objetivos_xy
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        
        scatter_kwargs = {
            'c': 'blue',
            'alpha': 0.7,
            's': 50,
            'edgecolors': 'white',
            'linewidths': 0.5
        }
        scatter_kwargs.update(kwargs)
        
        ax.scatter(objetivos[:, i], objetivos[:, j], **scatter_kwargs)
        
        # Etiquetas
        xlabel = self.nombres_objetivos[i] if i < len(self.nombres_objetivos) else f'Objetivo {i}'
        ylabel = self.nombres_objetivos[j] if j < len(self.nombres_objetivos) else f'Objetivo {j}'
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(f'Frente de Pareto ({len(self.frente_pareto)} soluciones)')
        ax.grid(True, alpha=0.3)
        
        return ax
    
    def graficar_convergencia(self, ax=None):
        """Grafica la convergencia del algoritmo."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib es necesario para graficar_convergencia()")
        
        if not self.historial:
            logger.warning("No hay historial de convergencia")
            return
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        generaciones = [h['generacion'] for h in self.historial]
        
        if 'objetivo_min' in self.historial[0]:
            n_obj = len(self.historial[0]['objetivo_min'])
            for i in range(n_obj):
                valores = [h['objetivo_min'][i] for h in self.historial]
                nombre = self.nombres_objetivos[i] if i < len(self.nombres_objetivos) else f'Obj {i}'
                ax.plot(generaciones, valores, label=f'{nombre} (min)', marker='o', markersize=2)
        
        ax.set_xlabel('Generación')
        ax.set_ylabel('Valor objetivo')
        ax.set_title('Convergencia del algoritmo')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return ax


# =============================================================================
# OPTIMIZADOR NSGA-II
# =============================================================================

class OptimizadorNSGAII:
    """
    Motor de optimización multiobjetivo NSGA-II.
    
    Implementa el algoritmo NSGA-II completo para optimización de ubicación
    de infraestructura considerando múltiples objetivos conflictivos
    y restricciones.
    
    Attributes
    ----------
    config : ConfiguracionNSGAII
        Configuración del algoritmo
    objetivos : List[FuncionObjetivo]
        Lista de funciones objetivo
    restricciones : List[Restriccion]
        Lista de restricciones
    region : Optional[List[Tuple[float, float]]]
        Región de estudio (bounds)
    
    Examples
    --------
    >>> from seismex.optimization import (
    ...     OptimizadorNSGAII,
    ...     ConfiguracionNSGAII,
    ...     objetivo_riesgo_esd,
    ...     objetivo_costo_construccion
    ... )
    >>> 
    >>> config = ConfiguracionNSGAII(n_generaciones=100)
    >>> optimizador = OptimizadorNSGAII(config)
    >>> 
    >>> # Agregar objetivos (minimización)
    >>> optimizador.agregar_objetivo(objetivo_riesgo_esd(resultado_esd))
    >>> optimizador.agregar_objetivo(objetivo_costo_construccion(mapa_costos))
    >>> 
    >>> # Optimizar
    >>> resultado = optimizador.optimizar(
    ...     region=[(18, 21), (-105, -102)]
    ... )
    >>> 
    >>> # Visualizar
    >>> resultado.graficar_pareto()
    """
    
    def __init__(self, config: Optional[ConfiguracionNSGAII] = None):
        """
        Inicializa el optimizador.
        
        Parameters
        ----------
        config : Optional[ConfiguracionNSGAII]
            Configuración del algoritmo. Si None, usa valores por defecto.
        """
        self.config = config or ConfiguracionNSGAII()
        self.objetivos: List['FuncionObjetivo'] = []
        self.restricciones: List['Restriccion'] = []
        self.region: Optional[List[Tuple[float, float]]] = None
        self._limites: Optional[List[Tuple[float, float]]] = None
        
        # Estado interno
        self._poblacion: Optional[Poblacion] = None
        self._historial: List[Dict[str, Any]] = []
        self._generacion_actual: int = 0
        self._mejor_frente: List[Individuo] = []
        self._rng: np.random.Generator = np.random.default_rng(self.config.semilla)
        
        logger.info(f"OptimizadorNSGAII inicializado")
    
    def agregar_objetivo(self, objetivo: 'FuncionObjetivo') -> 'OptimizadorNSGAII':
        """
        Agrega una función objetivo.
        
        Parameters
        ----------
        objetivo : FuncionObjetivo
            Función objetivo a agregar
            
        Returns
        -------
        OptimizadorNSGAII
            Self para encadenamiento
        """
        self.objetivos.append(objetivo)
        logger.info(f"Objetivo agregado: {objetivo.nombre}")
        return self
    
    def agregar_restriccion(self, restriccion: 'Restriccion') -> 'OptimizadorNSGAII':
        """
        Agrega una restricción.
        
        Parameters
        ----------
        restriccion : Restriccion
            Restricción a agregar
            
        Returns
        -------
        OptimizadorNSGAII
            Self para encadenamiento
        """
        self.restricciones.append(restriccion)
        logger.info(f"Restricción agregada: {restriccion.nombre}")
        return self
    
    def optimizar(
        self,
        region: List[Tuple[float, float]],
        poblacion_inicial: Optional[Poblacion] = None,
        callback: Optional[Callable[[int, Poblacion], bool]] = None
    ) -> ResultadoOptimizacion:
        """
        Ejecuta la optimización NSGA-II.
        
        Parameters
        ----------
        region : List[Tuple[float, float]]
            Región de estudio como [(lat_min, lat_max), (lon_min, lon_max)]
        poblacion_inicial : Optional[Poblacion]
            Población inicial. Si None, genera aleatoriamente.
        callback : Optional[Callable[[int, Poblacion], bool]]
            Función llamada cada generación. Si retorna True, detiene.
            
        Returns
        -------
        ResultadoOptimizacion
            Resultados de la optimización
            
        Raises
        ------
        ValueError
            Si no hay objetivos definidos
        """
        if not self.objetivos:
            raise ValueError("Debe agregar al menos un objetivo antes de optimizar")
        
        tiempo_inicio = time.time()
        self.region = region
        self._configurar_limites()
        self._historial = []
        
        # Inicializar población
        if poblacion_inicial is not None:
            self._poblacion = poblacion_inicial
        else:
            self._poblacion = self._inicializar_poblacion()
        
        # Evaluar población inicial
        self._evaluar_poblacion(self._poblacion)
        
        # Non-dominated sorting inicial
        frentes = self._non_dominated_sorting(self._poblacion)
        self._asignar_crowding_distance(self._poblacion, frentes)
        
        # Variables para detección de convergencia
        generaciones_sin_mejora = 0
        mejor_hipervolumen = float('-inf')
        convergencia = False
        
        # Bucle principal de evolución
        for gen in range(self.config.n_generaciones):
            self._generacion_actual = gen
            
            # Generar descendientes
            hijos = self._generar_descendientes(self._poblacion)
            
            # Evaluar hijos
            self._evaluar_poblacion_lista(hijos)
            
            # Combinar padres e hijos
            poblacion_combinada = Poblacion(
                individuos=self._poblacion.individuos + hijos,
                generacion=gen + 1
            )
            
            # Non-dominated sorting de la población combinada
            frentes = self._non_dominated_sorting(poblacion_combinada)
            self._asignar_crowding_distance(poblacion_combinada, frentes)
            
            # Seleccionar siguiente generación
            self._poblacion = self._seleccionar_siguiente_generacion(
                poblacion_combinada, frentes
            )
            self._poblacion.generacion = gen + 1
            
            # Guardar historial
            if self.config.guardar_historial:
                stats = self._poblacion.estadisticas()
                stats['generacion'] = gen
                self._historial.append(stats)
            
            # Callback
            if callback is not None:
                if callback(gen, self._poblacion):
                    logger.info(f"Optimización detenida por callback en generación {gen}")
                    break
            
            # Verificar convergencia
            frente_actual = self._poblacion.obtener_frente_pareto(0)
            hipervolumen_actual = self._calcular_hipervolumen_aproximado(frente_actual)
            
            if abs(hipervolumen_actual - mejor_hipervolumen) < self.config.tolerancia_convergencia:
                generaciones_sin_mejora += 1
            else:
                generaciones_sin_mejora = 0
                mejor_hipervolumen = max(mejor_hipervolumen, hipervolumen_actual)
            
            if generaciones_sin_mejora >= self.config.criterio_parada_generaciones:
                convergencia = True
                logger.info(f"Convergencia alcanzada en generación {gen}")
                break
            
            # Mostrar progreso
            if self.config.verbose and (gen + 1) % 10 == 0:
                n_factibles = len([i for i in self._poblacion if i.factible])
                n_pareto = len(frente_actual)
                print(f"Generación {gen + 1}/{self.config.n_generaciones}: "
                      f"Pareto={n_pareto}, Factibles={n_factibles}")
        
        tiempo_fin = time.time()
        
        # Construir resultado
        frente_pareto = self._poblacion.obtener_frente_pareto(0)
        
        resultado = ResultadoOptimizacion(
            frente_pareto=frente_pareto,
            poblacion_final=self._poblacion,
            historial=self._historial,
            config=self.config,
            tiempo_ejecucion=tiempo_fin - tiempo_inicio,
            convergencia=convergencia,
            generaciones_ejecutadas=self._generacion_actual + 1,
            nombres_objetivos=[obj.nombre for obj in self.objetivos],
            nombres_restricciones=[r.nombre for r in self.restricciones]
        )
        
        if self.config.verbose:
            print(resultado.resumen())
        
        return resultado
    
    def _configurar_limites(self) -> None:
        """Configura los límites de los genes basado en la región."""
        self._limites = []
        for _ in range(self.config.n_sitios):
            self._limites.append(self.region[0])  # lat
            self._limites.append(self.region[1])  # lon
    
    def _inicializar_poblacion(self) -> Poblacion:
        """Inicializa la población aleatoriamente."""
        n_genes = self.config.n_sitios * 2
        
        individuos = []
        for _ in range(self.config.tamano_poblacion):
            genes = np.array([
                self._rng.uniform(self._limites[i][0], self._limites[i][1])
                for i in range(n_genes)
            ])
            individuos.append(Individuo(genes=genes, generacion_creado=0))
        
        return Poblacion(individuos=individuos, generacion=0)
    
    def _evaluar_poblacion(self, poblacion: Poblacion) -> None:
        """Evalúa objetivos y restricciones para todos los individuos."""
        for individuo in poblacion:
            self._evaluar_individuo(individuo)
    
    def _evaluar_poblacion_lista(self, individuos: List[Individuo]) -> None:
        """Evalúa una lista de individuos."""
        for individuo in individuos:
            self._evaluar_individuo(individuo)
    
    def _evaluar_individuo(self, individuo: Individuo) -> None:
        """Evalúa un individuo."""
        coordenadas = individuo.decodificar_coordenadas()
        
        # Evaluar objetivos
        valores_obj = []
        for objetivo in self.objetivos:
            try:
                valor = objetivo.evaluar(coordenadas)
            except Exception as e:
                logger.warning(f"Error evaluando objetivo {objetivo.nombre}: {e}")
                valor = float('inf')
            valores_obj.append(valor)
        individuo.objetivos = np.array(valores_obj)
        
        # Evaluar restricciones
        valores_rest = []
        individuo.factible = True
        for restriccion in self.restricciones:
            try:
                violacion = restriccion.evaluar(coordenadas)
            except Exception as e:
                logger.warning(f"Error evaluando restricción {restriccion.nombre}: {e}")
                violacion = float('inf')
            valores_rest.append(violacion)
            if violacion > 0:
                individuo.factible = False
        
        individuo.restricciones = np.array(valores_rest) if valores_rest else None
        
        # Penalizar objetivos si no es factible
        if not individuo.factible and individuo.restricciones is not None:
            penalizacion = np.sum(individuo.restricciones) * self.config.penalizacion_restriccion
            individuo.objetivos = individuo.objetivos + penalizacion
    
    def _non_dominated_sorting(self, poblacion: Poblacion) -> List[List[int]]:
        """
        Realiza el ordenamiento por no-dominancia (Fast Non-dominated Sort).
        
        Returns
        -------
        List[List[int]]
            Lista de frentes, cada uno con índices de individuos
        """
        n = len(poblacion)
        dominados_por = [[] for _ in range(n)]  # Qp: soluciones dominadas por p
        contador_dominancia = [0] * n  # np: cuántos dominan a p
        frentes = [[]]
        
        for p in range(n):
            for q in range(n):
                if p != q:
                    if poblacion[p].domina(poblacion[q]):
                        dominados_por[p].append(q)
                    elif poblacion[q].domina(poblacion[p]):
                        contador_dominancia[p] += 1
            
            if contador_dominancia[p] == 0:
                poblacion[p].rango = 0
                frentes[0].append(p)
        
        i = 0
        while frentes[i]:
            siguiente_frente = []
            for p in frentes[i]:
                for q in dominados_por[p]:
                    contador_dominancia[q] -= 1
                    if contador_dominancia[q] == 0:
                        poblacion[q].rango = i + 1
                        siguiente_frente.append(q)
            i += 1
            frentes.append(siguiente_frente)
        
        # Eliminar el último frente vacío
        frentes.pop()
        
        return frentes
    
    def _asignar_crowding_distance(
        self, 
        poblacion: Poblacion, 
        frentes: List[List[int]]
    ) -> None:
        """
        Calcula y asigna la distancia de crowding para cada individuo.
        """
        for frente in frentes:
            self._calcular_crowding_distance_frente(poblacion, frente)
    
    def _calcular_crowding_distance_frente(
        self, 
        poblacion: Poblacion, 
        frente: List[int]
    ) -> None:
        """
        Calcula la distancia de crowding para un frente específico.
        """
        n = len(frente)
        if n == 0:
            return
        
        # Inicializar distancias a 0
        for idx in frente:
            poblacion[idx].distancia_crowding = 0.0
        
        if n <= 2:
            for idx in frente:
                poblacion[idx].distancia_crowding = float('inf')
            return
        
        n_objetivos = len(self.objetivos)
        
        for m in range(n_objetivos):
            # Ordenar frente por objetivo m
            frente_ordenado = sorted(frente, key=lambda i: poblacion[i].objetivos[m])
            
            # Extremos tienen distancia infinita
            poblacion[frente_ordenado[0]].distancia_crowding = float('inf')
            poblacion[frente_ordenado[-1]].distancia_crowding = float('inf')
            
            # Calcular rango del objetivo
            f_min = poblacion[frente_ordenado[0]].objetivos[m]
            f_max = poblacion[frente_ordenado[-1]].objetivos[m]
            rango = f_max - f_min
            
            if rango == 0:
                continue
            
            # Calcular distancia para puntos intermedios
            for i in range(1, n - 1):
                idx = frente_ordenado[i]
                idx_prev = frente_ordenado[i - 1]
                idx_next = frente_ordenado[i + 1]
                
                dist = (poblacion[idx_next].objetivos[m] - 
                       poblacion[idx_prev].objetivos[m]) / rango
                poblacion[idx].distancia_crowding += dist
    
    def _generar_descendientes(self, poblacion: Poblacion) -> List[Individuo]:
        """
        Genera la población de descendientes mediante selección, cruce y mutación.
        
        Returns
        -------
        List[Individuo]
            Lista de individuos descendientes
        """
        hijos = []
        n_hijos = self.config.tamano_poblacion
        
        while len(hijos) < n_hijos:
            # Seleccionar padres
            padre1 = self._seleccion_torneo(poblacion)
            padre2 = self._seleccion_torneo(poblacion)
            
            # Asegurar que sean diferentes
            intentos = 0
            while padre1.id_individuo == padre2.id_individuo and intentos < 10:
                padre2 = self._seleccion_torneo(poblacion)
                intentos += 1
            
            # Cruce
            if self._rng.random() < self.config.prob_cruce:
                hijo1, hijo2 = self._cruce_sbx(padre1, padre2)
            else:
                hijo1 = padre1.copiar()
                hijo2 = padre2.copiar()
            
            # Mutación
            hijo1 = self._mutacion_polinomial(hijo1)
            hijo2 = self._mutacion_polinomial(hijo2)
            
            # Actualizar generación
            hijo1.generacion_creado = poblacion.generacion + 1
            hijo2.generacion_creado = poblacion.generacion + 1
            
            # Nuevos IDs
            import uuid
            hijo1.id_individuo = str(uuid.uuid4())[:8]
            hijo2.id_individuo = str(uuid.uuid4())[:8]
            
            hijos.extend([hijo1, hijo2])
        
        return hijos[:n_hijos]
    
    def _seleccion_torneo(self, poblacion: Poblacion) -> Individuo:
        """
        Selección por torneo binario basada en rango y crowding distance.
        
        Returns
        -------
        Individuo
            Individuo ganador del torneo
        """
        k = self.config.tamano_torneo
        indices = self._rng.choice(len(poblacion), size=k, replace=False)
        
        mejor = poblacion[indices[0]]
        for idx in indices[1:]:
            candidato = poblacion[idx]
            # Crowded comparison operator
            if candidato < mejor:
                mejor = candidato
        
        return mejor
    
    def _cruce_sbx(
        self, 
        padre1: Individuo, 
        padre2: Individuo
    ) -> Tuple[Individuo, Individuo]:
        """
        Simulated Binary Crossover (SBX).
        
        Returns
        -------
        Tuple[Individuo, Individuo]
            Dos individuos descendientes
        """
        eta = self.config.eta_cruce
        genes1 = padre1.genes.copy()
        genes2 = padre2.genes.copy()
        
        for i in range(len(genes1)):
            if self._rng.random() <= 0.5:
                if abs(genes1[i] - genes2[i]) > 1e-14:
                    y1 = min(genes1[i], genes2[i])
                    y2 = max(genes1[i], genes2[i])
                    
                    lb = self._limites[i][0]
                    ub = self._limites[i][1]
                    
                    rand = self._rng.random()
                    
                    # Cálculo de beta
                    beta = 1.0 + (2.0 * (y1 - lb) / (y2 - y1))
                    alpha = 2.0 - beta ** (-(eta + 1))
                    
                    if rand <= 1.0 / alpha:
                        betaq = (rand * alpha) ** (1.0 / (eta + 1))
                    else:
                        betaq = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta + 1))
                    
                    c1 = 0.5 * ((y1 + y2) - betaq * (y2 - y1))
                    
                    beta = 1.0 + (2.0 * (ub - y2) / (y2 - y1))
                    alpha = 2.0 - beta ** (-(eta + 1))
                    
                    if rand <= 1.0 / alpha:
                        betaq = (rand * alpha) ** (1.0 / (eta + 1))
                    else:
                        betaq = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta + 1))
                    
                    c2 = 0.5 * ((y1 + y2) + betaq * (y2 - y1))
                    
                    # Aplicar límites
                    c1 = np.clip(c1, lb, ub)
                    c2 = np.clip(c2, lb, ub)
                    
                    if self._rng.random() <= 0.5:
                        genes1[i] = c1
                        genes2[i] = c2
                    else:
                        genes1[i] = c2
                        genes2[i] = c1
        
        hijo1 = Individuo(genes=genes1)
        hijo2 = Individuo(genes=genes2)
        
        return hijo1, hijo2
    
    def _mutacion_polinomial(self, individuo: Individuo) -> Individuo:
        """
        Mutación polinomial.
        
        Returns
        -------
        Individuo
            Individuo mutado
        """
        eta = self.config.eta_mutacion
        genes = individuo.genes.copy()
        
        for i in range(len(genes)):
            if self._rng.random() < self.config.prob_mutacion:
                y = genes[i]
                lb = self._limites[i][0]
                ub = self._limites[i][1]
                
                delta1 = (y - lb) / (ub - lb)
                delta2 = (ub - y) / (ub - lb)
                
                rand = self._rng.random()
                mut_pow = 1.0 / (eta + 1.0)
                
                if rand < 0.5:
                    xy = 1.0 - delta1
                    val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta + 1.0))
                    deltaq = val ** mut_pow - 1.0
                else:
                    xy = 1.0 - delta2
                    val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta + 1.0))
                    deltaq = 1.0 - val ** mut_pow
                
                y_nuevo = y + deltaq * (ub - lb)
                genes[i] = np.clip(y_nuevo, lb, ub)
        
        individuo.genes = genes
        return individuo
    
    def _seleccionar_siguiente_generacion(
        self, 
        poblacion: Poblacion, 
        frentes: List[List[int]]
    ) -> Poblacion:
        """
        Selecciona la siguiente generación basada en frentes y crowding distance.
        
        Returns
        -------
        Poblacion
            Nueva población de tamaño N
        """
        nueva_poblacion = []
        n_objetivo = self.config.tamano_poblacion
        
        i = 0
        while len(nueva_poblacion) + len(frentes[i]) <= n_objetivo:
            for idx in frentes[i]:
                nueva_poblacion.append(poblacion[idx].copiar())
            i += 1
            if i >= len(frentes):
                break
        
        # Si necesitamos más individuos, ordenar último frente por crowding
        if len(nueva_poblacion) < n_objetivo and i < len(frentes):
            # Ordenar frente i por crowding distance (mayor primero)
            frente_ordenado = sorted(
                frentes[i], 
                key=lambda idx: poblacion[idx].distancia_crowding,
                reverse=True
            )
            
            n_faltantes = n_objetivo - len(nueva_poblacion)
            for idx in frente_ordenado[:n_faltantes]:
                nueva_poblacion.append(poblacion[idx].copiar())
        
        return Poblacion(individuos=nueva_poblacion)
    
    def _calcular_hipervolumen_aproximado(
        self, 
        frente: List[Individuo]
    ) -> float:
        """
        Calcula una aproximación del hipervolumen del frente de Pareto.
        
        Usa el punto de referencia como el peor valor en cada objetivo.
        """
        if not frente or frente[0].objetivos is None:
            return 0.0
        
        objetivos = np.array([ind.objetivos for ind in frente])
        
        # Punto de referencia: peor valor + margen
        ref_point = objetivos.max(axis=0) * 1.1
        
        # Aproximación simple: suma de volúmenes de cajas
        hipervolumen = 0.0
        for obj in objetivos:
            volumen = np.prod(ref_point - obj)
            hipervolumen += volumen
        
        return hipervolumen
    
    def info(self) -> str:
        """Retorna información del optimizador."""
        return f"""
OptimizadorNSGAII
=================
Estado: ✅ IMPLEMENTADO

Configuración:
  - Generaciones: {self.config.n_generaciones}
  - Población: {self.config.tamano_poblacion}
  - P(cruce): {self.config.prob_cruce}
  - P(mutación): {self.config.prob_mutacion}
  - η cruce: {self.config.eta_cruce}
  - η mutación: {self.config.eta_mutacion}
  - N° sitios: {self.config.n_sitios}

Objetivos: {len(self.objetivos)}
  {chr(10).join(['  - ' + o.nombre for o in self.objetivos]) if self.objetivos else '  (ninguno)'}

Restricciones: {len(self.restricciones)}
  {chr(10).join(['  - ' + r.nombre for r in self.restricciones]) if self.restricciones else '  (ninguna)'}
"""


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def verificar_deap() -> bool:
    """Verifica si DEAP está instalado."""
    try:
        import deap
        return True
    except ImportError:
        return False


def info_modulo():
    """Muestra información del módulo genetic."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              SEISMEX Optimization - genetic.py                       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Clases implementadas:                                               ║
║    ✅ ConfiguracionNSGAII  - Parámetros del algoritmo                ║
║    ✅ Individuo            - Solución candidata                      ║
║    ✅ Poblacion            - Conjunto de individuos                  ║
║    ✅ ResultadoOptimizacion - Resultados y visualización             ║
║    ✅ OptimizadorNSGAII    - Motor principal NSGA-II                 ║
║                                                                      ║
║  Operadores implementados:                                           ║
║    ✅ Fast Non-dominated Sorting                                     ║
║    ✅ Crowding Distance                                              ║
║    ✅ Selección por Torneo                                           ║
║    ✅ Simulated Binary Crossover (SBX)                               ║
║    ✅ Mutación Polinomial                                            ║
║                                                                      ║
║  Estado: ✅ COMPLETAMENTE IMPLEMENTADO                               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Configuración
    'ConfiguracionNSGAII',
    
    # Enumeraciones
    'TipoCodificacion',
    'TipoSeleccion',
    'TipoCruce',
    'TipoMutacion',
    
    # Clases principales
    'Individuo',
    'Poblacion',
    'ResultadoOptimizacion',
    'OptimizadorNSGAII',
    
    # Utilidades
    'verificar_deap',
    'info_modulo',
]
