#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Optimization - Optimización Multiobjetivo con Algoritmos Genéticos
================================================================================

Módulo de optimización multiobjetivo para SEISMEX, implementando NSGA-II
(Non-dominated Sorting Genetic Algorithm II) para optimización de ubicación
de infraestructura considerando riesgo sísmico.

Componentes:
    - OptimizadorNSGAII: Motor principal de optimización
    - FuncionObjetivo: Clase base para funciones objetivo
    - Restriccion: Clase base para restricciones
    - ResultadoOptimizacion: Contenedor de resultados

Funciones objetivo predefinidas:
    - objetivo_riesgo_esd: Minimizar riesgo sísmico (ESD)
    - objetivo_costo_construccion: Minimizar costo de construcción
    - objetivo_impacto_ambiental: Minimizar impacto ambiental
    - objetivo_accesibilidad: Maximizar accesibilidad a servicios
    - objetivo_distancia_fallas: Maximizar distancia a fallas geológicas
    - objetivo_distancia_volcanes: Maximizar distancia a volcanes
    - objetivo_pendiente: Minimizar pendiente del terreno

Restricciones predefinidas:
    - restriccion_uso_suelo: Limitar a zonas permitidas
    - restriccion_pendiente: Limitar pendiente del terreno
    - restriccion_zona_inundable: Evitar zonas inundables
    - restriccion_distancia_minima: Distancia mínima entre sitios
    - restriccion_capacidad: Límites de capacidad
    - restriccion_zona_protegida: Evitar ANPs
    - restriccion_buffer_fallas: Buffer de fallas geológicas
    - restriccion_elevacion: Rango de elevación

Uso básico:

    >>> from seismex.optimization import (
    ...     OptimizadorNSGAII,
    ...     ConfiguracionNSGAII,
    ...     objetivo_riesgo_esd,
    ...     objetivo_costo_construccion,
    ...     restriccion_uso_suelo,
    ...     restriccion_distancia_minima
    ... )
    >>> 
    >>> # Configurar optimización
    >>> config = ConfiguracionNSGAII(
    ...     n_generaciones=100,
    ...     tamano_poblacion=200,
    ...     prob_cruce=0.9,
    ...     prob_mutacion=0.1,
    ...     n_sitios=3
    ... )
    >>> 
    >>> # Crear optimizador
    >>> optimizador = OptimizadorNSGAII(config)
    >>> 
    >>> # Definir funciones objetivo
    >>> optimizador.agregar_objetivo(objetivo_riesgo_esd(esd_grid, bounds))
    >>> optimizador.agregar_objetivo(objetivo_costo_construccion())
    >>> 
    >>> # Agregar restricciones
    >>> optimizador.agregar_restriccion(restriccion_distancia_minima(distancia_km=5))
    >>> 
    >>> # Ejecutar optimización
    >>> resultado = optimizador.optimizar(region=[(18, 21), (-105, -102)])
    >>> 
    >>> # Visualizar frente de Pareto
    >>> resultado.graficar_pareto()
    >>> 
    >>> # Exportar soluciones
    >>> resultado.exportar_geojson('soluciones_optimas.geojson')
    >>> 
    >>> # Obtener solución de compromiso
    >>> mejor = resultado.obtener_solucion_compromiso()
    >>> print(mejor.decodificar_coordenadas())

Autor: SEISMEX Team
Versión: 1.0.0
Estado: ✅ IMPLEMENTADO
================================================================================
"""

__version__ = "1.0.0"
__author__ = "SEISMEX Team"
__status__ = "Implementado"

# =============================================================================
# IMPORTACIONES - Motor NSGA-II
# =============================================================================

from .genetic import (
    # Configuración
    ConfiguracionNSGAII,
    
    # Enumeraciones
    TipoCodificacion,
    TipoSeleccion,
    TipoCruce,
    TipoMutacion,
    
    # Clases principales
    Individuo,
    Poblacion,
    ResultadoOptimizacion,
    OptimizadorNSGAII,
)

# =============================================================================
# IMPORTACIONES - Funciones Objetivo
# =============================================================================

from .objectives import (
    # Enumeraciones
    TipoOptimizacion,
    CategoriaObjetivo,
    
    # Clase base
    FuncionObjetivo,
    
    # Clases de objetivos
    ObjetivoRiesgoESD,
    ObjetivoCostoConstruccion,
    ObjetivoImpactoAmbiental,
    ObjetivoAccesibilidad,
    ObjetivoDistanciaFallas,
    ObjetivoDistanciaVolcanes,
    ObjetivoPendiente,
    ObjetivoPersonalizado,
    ObjetivoCompuesto,
    
    # Factory functions
    objetivo_riesgo_esd,
    objetivo_costo_construccion,
    objetivo_impacto_ambiental,
    objetivo_accesibilidad,
    objetivo_distancia_fallas,
    objetivo_distancia_volcanes,
    objetivo_pendiente,
    crear_objetivo_personalizado,
    crear_objetivo_compuesto,
)

# =============================================================================
# IMPORTACIONES - Restricciones
# =============================================================================

from .constraints import (
    # Enumeraciones
    TipoRestriccion,
    SeveridadRestriccion,
    CategoriaRestriccion,
    
    # Clase base
    Restriccion,
    
    # Clases de restricciones
    RestriccionUsoSuelo,
    RestriccionPendiente,
    RestriccionZonaInundable,
    RestriccionDistanciaMinima,
    RestriccionCapacidad,
    RestriccionZonaProtegida,
    RestriccionBufferFallas,
    RestriccionElevacion,
    RestriccionRegion,
    RestriccionPersonalizada,
    RestriccionCompuesta,
    
    # Factory functions
    restriccion_uso_suelo,
    restriccion_pendiente,
    restriccion_zona_inundable,
    restriccion_distancia_minima,
    restriccion_capacidad,
    restriccion_zona_protegida,
    restriccion_buffer_fallas,
    restriccion_elevacion,
    restriccion_region,
    crear_restriccion_personalizada,
    crear_restriccion_compuesta,
)


# =============================================================================
# FUNCIONES DE INFORMACIÓN
# =============================================================================

def info():
    """Muestra información completa del módulo optimization."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SEISMEX Optimization Module                               ║
║                    Estado: ✅ IMPLEMENTADO                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Motor de Optimización (genetic.py):                                         ║
║    ✅ ConfiguracionNSGAII    - Parámetros del algoritmo                      ║
║    ✅ Individuo              - Solución candidata                            ║
║    ✅ Poblacion              - Conjunto de individuos                        ║
║    ✅ ResultadoOptimizacion  - Resultados y visualización                    ║
║    ✅ OptimizadorNSGAII      - Motor principal NSGA-II                       ║
║                                                                              ║
║  Operadores Genéticos:                                                       ║
║    ✅ Fast Non-dominated Sorting                                             ║
║    ✅ Crowding Distance                                                      ║
║    ✅ Selección por Torneo                                                   ║
║    ✅ Simulated Binary Crossover (SBX)                                       ║
║    ✅ Mutación Polinomial                                                    ║
║                                                                              ║
║  Funciones Objetivo (objectives.py):                                         ║
║    ✅ objetivo_riesgo_esd           - Riesgo sísmico (ESD)                   ║
║    ✅ objetivo_costo_construccion   - Costo económico                        ║
║    ✅ objetivo_impacto_ambiental    - Impacto ambiental                      ║
║    ✅ objetivo_accesibilidad        - Accesibilidad a servicios              ║
║    ✅ objetivo_distancia_fallas     - Distancia a fallas                     ║
║    ✅ objetivo_distancia_volcanes   - Distancia a volcanes                   ║
║    ✅ objetivo_pendiente            - Pendiente del terreno                  ║
║    ✅ crear_objetivo_personalizado  - Objetivo con función lambda            ║
║    ✅ crear_objetivo_compuesto      - Combinación de objetivos               ║
║                                                                              ║
║  Restricciones (constraints.py):                                             ║
║    ✅ restriccion_uso_suelo         - Uso de suelo permitido                 ║
║    ✅ restriccion_pendiente         - Pendiente máxima                       ║
║    ✅ restriccion_zona_inundable    - Zonas inundables                       ║
║    ✅ restriccion_distancia_minima  - Distancia entre sitios                 ║
║    ✅ restriccion_capacidad         - Capacidad del terreno                  ║
║    ✅ restriccion_zona_protegida    - Áreas naturales protegidas             ║
║    ✅ restriccion_buffer_fallas     - Buffer de fallas                       ║
║    ✅ restriccion_elevacion         - Rango de elevación                     ║
║    ✅ restriccion_region            - Límites de región                      ║
║    ✅ crear_restriccion_personalizada - Función lambda                       ║
║    ✅ crear_restriccion_compuesta   - Combinar restricciones                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Uso rápido:
    >>> from seismex.optimization import OptimizadorNSGAII, ConfiguracionNSGAII
    >>> from seismex.optimization import objetivo_riesgo_esd, restriccion_distancia_minima
    >>> 
    >>> config = ConfiguracionNSGAII(n_generaciones=50, n_sitios=2)
    >>> opt = OptimizadorNSGAII(config)
    >>> opt.agregar_objetivo(objetivo_riesgo_esd(esd_grid, bounds))
    >>> opt.agregar_restriccion(restriccion_distancia_minima(distancia_km=10))
    >>> resultado = opt.optimizar(region=[(18, 21), (-105, -102)])
    >>> resultado.graficar_pareto()
    """)


def listar_componentes() -> dict:
    """
    Lista todos los componentes disponibles del módulo.
    
    Returns
    -------
    dict
        Diccionario con categorías y componentes
    """
    return {
        'motor': [
            'OptimizadorNSGAII',
            'ConfiguracionNSGAII',
            'Individuo',
            'Poblacion',
            'ResultadoOptimizacion',
        ],
        'objetivos': [
            'objetivo_riesgo_esd',
            'objetivo_costo_construccion',
            'objetivo_impacto_ambiental',
            'objetivo_accesibilidad',
            'objetivo_distancia_fallas',
            'objetivo_distancia_volcanes',
            'objetivo_pendiente',
            'crear_objetivo_personalizado',
            'crear_objetivo_compuesto',
        ],
        'restricciones': [
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
        ],
    }


def ejemplo_basico():
    """
    Muestra un ejemplo básico de uso del módulo.
    
    Este ejemplo crea un problema de optimización simple
    con objetivos sintéticos para demostrar el flujo de trabajo.
    """
    import numpy as np
    
    print("=" * 60)
    print("EJEMPLO BÁSICO DE OPTIMIZACIÓN NSGA-II")
    print("=" * 60)
    
    # Configuración
    config = ConfiguracionNSGAII(
        n_generaciones=20,
        tamano_poblacion=50,
        prob_cruce=0.9,
        prob_mutacion=0.1,
        n_sitios=2,
        verbose=True
    )
    
    # Crear optimizador
    optimizador = OptimizadorNSGAII(config)
    
    # Crear objetivos sintéticos
    # Objetivo 1: Minimizar distancia al centro (19.5, -103.5)
    objetivo1 = crear_objetivo_personalizado(
        nombre="Distancia al centro",
        funcion=lambda coords: np.mean([
            np.sqrt((lat - 19.5)**2 + (lon + 103.5)**2)
            for lat, lon in coords
        ]),
        unidad="grados"
    )
    
    # Objetivo 2: Minimizar cercanía entre sitios (queremos dispersión)
    def dispersion(coords):
        if len(coords) < 2:
            return 0
        total = 0
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[j]
                dist = np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)
                total += 1 / (dist + 0.01)  # Menor distancia = mayor penalización
        return total
    
    objetivo2 = crear_objetivo_personalizado(
        nombre="Penalización por proximidad",
        funcion=dispersion,
        unidad="índice"
    )
    
    # Agregar objetivos
    optimizador.agregar_objetivo(objetivo1)
    optimizador.agregar_objetivo(objetivo2)
    
    # Agregar restricción
    optimizador.agregar_restriccion(
        restriccion_distancia_minima(distancia_km=20)
    )
    
    # Optimizar
    print("\nIniciando optimización...")
    resultado = optimizador.optimizar(
        region=[(18.5, 20.5), (-104.5, -102.5)]
    )
    
    # Mostrar resultados
    print("\n" + resultado.resumen())
    
    # Mostrar mejor solución
    mejor = resultado.obtener_solucion_compromiso()
    print("\nMejor solución de compromiso:")
    for i, (lat, lon) in enumerate(mejor.decodificar_coordenadas()):
        print(f"  Sitio {i + 1}: ({lat:.4f}, {lon:.4f})")
    
    return resultado


# =============================================================================
# EXPORTACIONES PÚBLICAS
# =============================================================================

__all__ = [
    # Información
    '__version__',
    '__author__',
    '__status__',
    'info',
    'listar_componentes',
    'ejemplo_basico',
    
    # Motor NSGA-II
    'ConfiguracionNSGAII',
    'TipoCodificacion',
    'TipoSeleccion',
    'TipoCruce',
    'TipoMutacion',
    'Individuo',
    'Poblacion',
    'ResultadoOptimizacion',
    'OptimizadorNSGAII',
    
    # Objetivos - Enums y base
    'TipoOptimizacion',
    'CategoriaObjetivo',
    'FuncionObjetivo',
    
    # Objetivos - Clases
    'ObjetivoRiesgoESD',
    'ObjetivoCostoConstruccion',
    'ObjetivoImpactoAmbiental',
    'ObjetivoAccesibilidad',
    'ObjetivoDistanciaFallas',
    'ObjetivoDistanciaVolcanes',
    'ObjetivoPendiente',
    'ObjetivoPersonalizado',
    'ObjetivoCompuesto',
    
    # Objetivos - Factory functions
    'objetivo_riesgo_esd',
    'objetivo_costo_construccion',
    'objetivo_impacto_ambiental',
    'objetivo_accesibilidad',
    'objetivo_distancia_fallas',
    'objetivo_distancia_volcanes',
    'objetivo_pendiente',
    'crear_objetivo_personalizado',
    'crear_objetivo_compuesto',
    
    # Restricciones - Enums y base
    'TipoRestriccion',
    'SeveridadRestriccion',
    'CategoriaRestriccion',
    'Restriccion',
    
    # Restricciones - Clases
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
    
    # Restricciones - Factory functions
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
]
