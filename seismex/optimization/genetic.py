#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Optimization - Motor de Algoritmo Genético NSGA-II
================================================================================

Implementación del algoritmo NSGA-II (Non-dominated Sorting Genetic Algorithm II)
para optimización multiobjetivo de ubicación de infraestructura considerando
riesgo sísmico.

Basado en:
    Deb, K., et al. (2002). "A fast and elitist multiobjective genetic 
    algorithm: NSGA-II." IEEE Transactions on Evolutionary Computation, 
    6(2), 182-197.

Clases principales:
    - ConfiguracionNSGAII: Parámetros del algoritmo
    - Individuo: Representación de una solución candidata
    - Poblacion: Conjunto de individuos
    - OptimizadorNSGAII: Motor principal de optimización

Estado: PLANIFICADO - Estructura definida, implementación pendiente

Autor: SEISMEX Team
Versión: 1.0.0
================================================================================
"""

from __future__ import annotations

import logging
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
import numpy as np

if TYPE_CHECKING:
    from .objectives import FuncionObjetivo
    from .constraints import Restriccion
    from .results import ResultadoOptimizacion

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoCodificacion(Enum):
    """Tipos de codificación para individuos."""
    REAL = "real"           # Coordenadas reales (lat, lon)
    BINARIA = "binaria"     # Representación binaria de grilla
    ENTERA = "entera"       # Índices de celdas en grilla
    PERMUTACION = "permutacion"  # Orden de sitios (para routing)


class TipoSeleccion(Enum):
    """Métodos de selección de padres."""
    TORNEO = "torneo"
    RULETA = "ruleta"
    RANKING = "ranking"


class TipoCruce(Enum):
    """Operadores de cruce."""
    SBX = "sbx"             # Simulated Binary Crossover
    BLX_ALPHA = "blx_alpha" # Blend Crossover
    UN_PUNTO = "un_punto"   # Cruce de un punto
    DOS_PUNTOS = "dos_puntos"  # Cruce de dos puntos
    UNIFORME = "uniforme"   # Cruce uniforme


class TipoMutacion(Enum):
    """Operadores de mutación."""
    POLINOMIAL = "polinomial"  # Polynomial mutation
    GAUSSIANA = "gaussiana"    # Mutación gaussiana
    UNIFORME = "uniforme"      # Mutación uniforme
    INTERCAMBIO = "intercambio"  # Swap mutation (permutaciones)


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
    n_procesos : int
        Número de procesos para evaluación paralela (default: 1)
    
    Examples
    --------
    >>> config = ConfiguracionNSGAII(
    ...     n_generaciones=200,
    ...     tamano_poblacion=150,
    ...     prob_cruce=0.95,
    ...     prob_mutacion=0.05,
    ...     n_sitios=3
    ... )
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
    
    # Paralelización
    n_procesos: int = 1
    
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
    
    Examples
    --------
    >>> # Individuo con 2 sitios (lat, lon cada uno)
    >>> genes = np.array([19.3, -103.5, 19.5, -103.8])
    >>> individuo = Individuo(genes=genes)
    """
    genes: np.ndarray
    objetivos: Optional[np.ndarray] = None
    restricciones: Optional[np.ndarray] = None
    rango: int = 0
    distancia_crowding: float = 0.0
    factible: bool = True
    
    # Metadatos
    generacion_creado: int = 0
    id_individuo: Optional[str] = None
    
    def __post_init__(self):
        """Inicialización adicional."""
        if self.id_individuo is None:
            import uuid
            self.id_individuo = str(uuid.uuid4())[:8]
    
    def __lt__(self, other: 'Individuo') -> bool:
        """
        Comparación para ordenamiento.
        Mejor = menor rango, o mismo rango pero mayor distancia crowding.
        """
        if self.rango != other.rango:
            return self.rango < other.rango
        return self.distancia_crowding > other.distancia_crowding
    
    def domina(self, other: 'Individuo') -> bool:
        """
        Verifica si este individuo domina a otro.
        
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
        
        # Asumiendo minimización de todos los objetivos
        al_menos_igual = np.all(self.objetivos <= other.objetivos)
        estrictamente_mejor = np.any(self.objetivos < other.objetivos)
        
        return al_menos_igual and estrictamente_mejor
    
    def copiar(self) -> 'Individuo':
        """Crea una copia del individuo."""
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
    
    Examples
    --------
    >>> poblacion = Poblacion.generar_aleatoria(
    ...     tamano=100,
    ...     n_genes=4,
    ...     limites=[(18, 21), (-105, -102), (18, 21), (-105, -102)]
    ... )
    """
    individuos: List[Individuo] = field(default_factory=list)
    generacion: int = 0
    
    def __len__(self) -> int:
        return len(self.individuos)
    
    def __iter__(self):
        return iter(self.individuos)
    
    def __getitem__(self, idx) -> Individuo:
        return self.individuos[idx]
    
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
            individuos.append(Individuo(genes=genes))
        
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
    
    def estadisticas(self) -> Dict[str, Any]:
        """Calcula estadísticas de la población."""
        if not self.individuos or self.individuos[0].objetivos is None:
            return {}
        
        objetivos = np.array([ind.objetivos for ind in self.individuos])
        
        return {
            'n_individuos': len(self.individuos),
            'generacion': self.generacion,
            'n_factibles': sum(1 for ind in self.individuos if ind.factible),
            'n_frentes': max(ind.rango for ind in self.individuos) + 1,
            'objetivo_min': objetivos.min(axis=0).tolist(),
            'objetivo_max': objetivos.max(axis=0).tolist(),
            'objetivo_mean': objetivos.mean(axis=0).tolist(),
            'objetivo_std': objetivos.std(axis=0).tolist(),
        }


# =============================================================================
# OPTIMIZADOR NSGA-II
# =============================================================================

class OptimizadorNSGAII:
    """
    Motor de optimización multiobjetivo NSGA-II.
    
    Implementa el algoritmo NSGA-II para optimización de ubicación
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
    region : Optional[Any]
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
    ...     region=[(18, 21), (-105, -102)],  # lat_min, lat_max, lon_min, lon_max
    ... )
    >>> 
    >>> # Visualizar
    >>> resultado.graficar_pareto()
    
    Notes
    -----
    Estado: PLANIFICADO - La implementación completa está pendiente.
    Los métodos actuales son placeholders que definen la interfaz.
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
        
        # Estado interno
        self._poblacion: Optional[Poblacion] = None
        self._historial: List[Dict[str, Any]] = []
        self._generacion_actual: int = 0
        self._mejor_frente: List[Individuo] = []
        
        # Configurar semilla
        if self.config.semilla is not None:
            np.random.seed(self.config.semilla)
        
        logger.info(f"OptimizadorNSGAII inicializado con config: {self.config}")
    
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
    ) -> 'ResultadoOptimizacion':
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
        NotImplementedError
            Método aún no implementado
        """
        if not self.objetivos:
            raise ValueError("Debe agregar al menos un objetivo antes de optimizar")
        
        self.region = region
        
        # TODO: Implementar algoritmo NSGA-II completo
        raise NotImplementedError(
            "El método optimizar() está planificado pero aún no implementado.\n"
            "La estructura del algoritmo incluirá:\n"
            "  1. Inicialización de población\n"
            "  2. Evaluación de objetivos y restricciones\n"
            "  3. Non-dominated sorting\n"
            "  4. Cálculo de crowding distance\n"
            "  5. Selección por torneo\n"
            "  6. Cruce (SBX)\n"
            "  7. Mutación (polinomial)\n"
            "  8. Reemplazo elitista\n"
            "  9. Iteración hasta convergencia\n"
            "\nPara contribuir, ver CONTRIBUTING.md"
        )
    
    def _inicializar_poblacion(self) -> Poblacion:
        """Inicializa la población aleatoriamente."""
        n_genes = self.config.n_sitios * 2  # lat, lon por sitio
        
        limites = []
        for _ in range(self.config.n_sitios):
            limites.extend([
                self.region[0],  # lat_min, lat_max
                self.region[1],  # lon_min, lon_max
            ])
        
        return Poblacion.generar_aleatoria(
            tamano=self.config.tamano_poblacion,
            n_genes=n_genes,
            limites=limites,
            semilla=self.config.semilla
        )
    
    def _evaluar_poblacion(self, poblacion: Poblacion) -> None:
        """Evalúa objetivos y restricciones para todos los individuos."""
        # TODO: Implementar evaluación paralela opcional
        for individuo in poblacion:
            self._evaluar_individuo(individuo)
    
    def _evaluar_individuo(self, individuo: Individuo) -> None:
        """Evalúa un individuo."""
        coordenadas = individuo.decodificar_coordenadas()
        
        # Evaluar objetivos
        valores_obj = []
        for objetivo in self.objetivos:
            valor = objetivo.evaluar(coordenadas)
            valores_obj.append(valor)
        individuo.objetivos = np.array(valores_obj)
        
        # Evaluar restricciones
        valores_rest = []
        individuo.factible = True
        for restriccion in self.restricciones:
            violacion = restriccion.evaluar(coordenadas)
            valores_rest.append(violacion)
            if violacion > 0:
                individuo.factible = False
        individuo.restricciones = np.array(valores_rest) if valores_rest else None
    
    def _non_dominated_sorting(self, poblacion: Poblacion) -> List[List[int]]:
        """
        Realiza el ordenamiento por no-dominancia.
        
        Returns
        -------
        List[List[int]]
            Lista de frentes, cada uno con índices de individuos
        """
        # TODO: Implementar fast non-dominated sorting
        raise NotImplementedError("Non-dominated sorting pendiente")
    
    def _calcular_crowding_distance(self, frente: List[Individuo]) -> None:
        """Calcula la distancia de crowding para un frente."""
        # TODO: Implementar crowding distance
        raise NotImplementedError("Crowding distance pendiente")
    
    def _seleccion_torneo(self, poblacion: Poblacion) -> Individuo:
        """Selección por torneo binario."""
        # TODO: Implementar selección por torneo
        raise NotImplementedError("Selección por torneo pendiente")
    
    def _cruce_sbx(
        self, 
        padre1: Individuo, 
        padre2: Individuo
    ) -> Tuple[Individuo, Individuo]:
        """Simulated Binary Crossover."""
        # TODO: Implementar SBX crossover
        raise NotImplementedError("Cruce SBX pendiente")
    
    def _mutacion_polinomial(self, individuo: Individuo) -> Individuo:
        """Mutación polinomial."""
        # TODO: Implementar polynomial mutation
        raise NotImplementedError("Mutación polinomial pendiente")
    
    def info(self) -> str:
        """Retorna información del optimizador."""
        return f"""
OptimizadorNSGAII
=================
Estado: PLANIFICADO (no implementado)

Configuración:
  - Generaciones: {self.config.n_generaciones}
  - Población: {self.config.tamano_poblacion}
  - P(cruce): {self.config.prob_cruce}
  - P(mutación): {self.config.prob_mutacion}
  - N° sitios: {self.config.n_sitios}

Objetivos: {len(self.objetivos)}
Restricciones: {len(self.restricciones)}
"""


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def verificar_deap() -> bool:
    """
    Verifica si DEAP está instalado.
    
    DEAP (Distributed Evolutionary Algorithms in Python) es una
    dependencia opcional que puede acelerar la optimización.
    
    Returns
    -------
    bool
        True si DEAP está disponible
    """
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
║  Clases definidas:                                                   ║
║    • ConfiguracionNSGAII  - Parámetros del algoritmo                 ║
║    • Individuo            - Solución candidata                       ║
║    • Poblacion            - Conjunto de individuos                   ║
║    • OptimizadorNSGAII    - Motor principal                          ║
║                                                                      ║
║  Estado: ESTRUCTURA DEFINIDA - Implementación pendiente              ║
║                                                                      ║
║  DEAP disponible: """ + ("✅ Sí" if verificar_deap() else "❌ No") + """
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
    'OptimizadorNSGAII',
    
    # Utilidades
    'verificar_deap',
    'info_modulo',
]
