#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Analysis - Módulos de Análisis Sísmico
================================================================================

Módulo de análisis sísmico de SEISMEX. Contiene implementaciones de
metodologías para evaluación de peligro y riesgo sísmico.

Módulos disponibles:
    - esd: Energy Space Density (Del Pezzo et al., 2024)
    - gutenberg_richter: Análisis de valor-b y magnitud de completitud
    - isoseismal: Generación de mapas de isosistas (GMPEs/IPEs)
    - source_models: Modelos de fuentes sísmicas
    - psha: Análisis Probabilístico de Peligro Sísmico (Cornell-McGuire)

Uso rápido:

    >>> from seismex.analysis import (
    ...     CalculadoraESD, ConfiguracionESD,
    ...     AnalizadorGutenbergRichter,
    ...     GeneradorIsosistas,
    ...     ModeloFuentes,
    ...     AnalizadorPSHA
    ... )

Estado: ✅ COMPLETO

Autor: SEISMEX Team
Versión: 1.0.0
================================================================================
"""

__version__ = "1.0.0"
__author__ = "SEISMEX Team"
__status__ = "Completo"

# =============================================================================
# IMPORTACIONES - ESD
# =============================================================================

from seismex.analysis.esd import (
    CalculadoraESD,
    ConfiguracionESD,
    ResultadoESD,
)

# =============================================================================
# IMPORTACIONES - GUTENBERG-RICHTER
# =============================================================================

from seismex.analysis.gutenberg_richter import (
    AnalizadorGutenbergRichter,
)

# =============================================================================
# IMPORTACIONES - ISOSISTAS
# =============================================================================

from seismex.analysis.isoseismal import (
    # Enumeraciones
    TipoEvento,
    TipoSuelo,
    EscalaIntensidad,
    
    # Clases base
    GMPE,
    IPE,
    ModeloSitio,
    
    # GMPEs
    GMPEZhao2006,
    GMPEGarcia2005,
    GMPEAtkinsonBoore2003,
    
    # IPEs
    IPEAllen2012,
    IPEAtkinsonWald2007,
    IPECENAPRED2006,
    
    # Generador y resultado
    GeneradorIsosistas,
    ResultadoIsosistas,
    
    # Factories
    crear_generador_mexico,
    crear_generador_subduccion,
    
    # Utilidades
    distancia_hipocentral,
    distancia_joyner_boore,
    pga_a_mmi_wald,
    pgv_a_mmi_wald,
    
    # Constantes
    ESCALA_MMI,
    COLORES_MMI,
)

# =============================================================================
# IMPORTACIONES - MODELOS DE FUENTES
# =============================================================================

from seismex.analysis.source_models import (
    # Enumeraciones
    TipoFuente,
    TipoFalla,
    TipoDistribucionMagnitud,
    TipoDistribucionProfundidad,
    
    # Distribuciones
    DistribucionMagnitud,
    DistribucionGutenbergRichter,
    DistribucionCaracteristica,
    DistribucionProfundidad,
    
    # Fuentes
    FuenteSismica,
    FuenteArea,
    FuenteFalla,
    FuentePuntual,
    
    # Modelo
    ModeloFuentes,
    
    # Factories
    crear_modelo_mexico_simplificado,
)

# =============================================================================
# IMPORTACIONES - PSHA
# =============================================================================

from seismex.analysis.psha import (
    # Enumeraciones
    MedidaIntensidad,
    TipoDistanciaGMPE,
    
    # Clases de resultados
    CurvaPeligro,
    MapaPeligro,
    Desagregacion,
    
    # Árbol lógico
    RamaArbolLogico,
    ArbolLogico,
    
    # GMPE Wrapper
    GMPEWrapper,
    
    # Analizador principal
    AnalizadorPSHA,
    
    # Factories
    crear_analizador_mexico,
    
    # Utilidades
    calcular_probabilidad_poisson,
    periodo_retorno_desde_probabilidad,
    
    # Constantes
    NIVELES_PGA_DEFAULT,
    PERIODOS_RETORNO_DEFAULT,
)


# =============================================================================
# FUNCIÓN DE INFORMACIÓN
# =============================================================================

def info():
    """Muestra información completa del módulo analysis."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SEISMEX Analysis Module                                 ║
║                      Estado: ✅ COMPLETO                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Módulos disponibles:                                                        ║
║                                                                              ║
║  📊 ESD (esd.py)                                                             ║
║     ✅ CalculadoraESD, ConfiguracionESD, ResultadoESD                        ║
║     Energy Space Density - Del Pezzo et al. (2024)                           ║
║                                                                              ║
║  📈 Gutenberg-Richter (gutenberg_richter.py)                                 ║
║     ✅ AnalizadorGutenbergRichter                                            ║
║     Análisis de valor-b y magnitud de completitud                            ║
║                                                                              ║
║  🗺️  Isosistas (isoseismal.py)                                               ║
║     ✅ GeneradorIsosistas, ResultadoIsosistas                                ║
║     ✅ GMPEs: Zhao2006, Garcia2005, AtkinsonBoore2003                        ║
║     ✅ IPEs: Allen2012, AtkinsonWald2007, CENAPRED2006                       ║
║                                                                              ║
║  🎯 Modelos de Fuentes (source_models.py)                                    ║
║     ✅ FuenteArea, FuenteFalla, FuentePuntual                                ║
║     ✅ DistribucionGutenbergRichter, DistribucionCaracteristica              ║
║     ✅ ModeloFuentes                                                         ║
║                                                                              ║
║  📉 PSHA (psha.py)                                                           ║
║     ✅ AnalizadorPSHA - Motor Cornell-McGuire                                ║
║     ✅ CurvaPeligro, MapaPeligro, Desagregacion                              ║
║     ✅ ArbolLogico para incertidumbre epistémica                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Uso rápido:
    >>> from seismex.analysis import AnalizadorPSHA, crear_analizador_mexico
    >>> psha = crear_analizador_mexico(vs30=400)
    >>> curva = psha.calcular_curva_peligro(sitio=(19.4, -99.1))
    >>> print(f"PGA 475 años: {curva.intensidad_para_periodo_retorno(475):.3f} g")
    """)


def listar_componentes() -> dict:
    """
    Lista todos los componentes disponibles del módulo.
    
    Returns
    -------
    dict
        Diccionario con módulos y sus componentes
    """
    return {
        'esd': [
            'CalculadoraESD',
            'ConfiguracionESD',
            'ResultadoESD',
        ],
        'gutenberg_richter': [
            'AnalizadorGutenbergRichter',
        ],
        'isoseismal': [
            'GeneradorIsosistas',
            'ResultadoIsosistas',
            'GMPEZhao2006',
            'GMPEGarcia2005',
            'GMPEAtkinsonBoore2003',
            'IPEAllen2012',
            'IPEAtkinsonWald2007',
            'IPECENAPRED2006',
            'ModeloSitio',
            'crear_generador_mexico',
            'crear_generador_subduccion',
        ],
        'source_models': [
            'FuenteArea',
            'FuenteFalla',
            'FuentePuntual',
            'ModeloFuentes',
            'DistribucionGutenbergRichter',
            'DistribucionCaracteristica',
            'DistribucionProfundidad',
            'crear_modelo_mexico_simplificado',
        ],
        'psha': [
            'AnalizadorPSHA',
            'CurvaPeligro',
            'MapaPeligro',
            'Desagregacion',
            'ArbolLogico',
            'GMPEWrapper',
            'crear_analizador_mexico',
            'calcular_probabilidad_poisson',
            'periodo_retorno_desde_probabilidad',
        ],
    }


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
    
    # ESD
    'CalculadoraESD',
    'ConfiguracionESD',
    'ResultadoESD',
    
    # Gutenberg-Richter
    'AnalizadorGutenbergRichter',
    
    # Isosistas - Enums
    'TipoEvento',
    'TipoSuelo',
    'EscalaIntensidad',
    
    # Isosistas - Clases base
    'GMPE',
    'IPE',
    'ModeloSitio',
    
    # Isosistas - GMPEs
    'GMPEZhao2006',
    'GMPEGarcia2005',
    'GMPEAtkinsonBoore2003',
    
    # Isosistas - IPEs
    'IPEAllen2012',
    'IPEAtkinsonWald2007',
    'IPECENAPRED2006',
    
    # Isosistas - Principal
    'GeneradorIsosistas',
    'ResultadoIsosistas',
    'crear_generador_mexico',
    'crear_generador_subduccion',
    
    # Isosistas - Utilidades
    'distancia_hipocentral',
    'distancia_joyner_boore',
    'pga_a_mmi_wald',
    'pgv_a_mmi_wald',
    'ESCALA_MMI',
    'COLORES_MMI',
    
    # Source Models - Enums
    'TipoFuente',
    'TipoFalla',
    'TipoDistribucionMagnitud',
    'TipoDistribucionProfundidad',
    
    # Source Models - Distribuciones
    'DistribucionMagnitud',
    'DistribucionGutenbergRichter',
    'DistribucionCaracteristica',
    'DistribucionProfundidad',
    
    # Source Models - Fuentes
    'FuenteSismica',
    'FuenteArea',
    'FuenteFalla',
    'FuentePuntual',
    'ModeloFuentes',
    'crear_modelo_mexico_simplificado',
    
    # PSHA - Enums
    'MedidaIntensidad',
    'TipoDistanciaGMPE',
    
    # PSHA - Resultados
    'CurvaPeligro',
    'MapaPeligro',
    'Desagregacion',
    
    # PSHA - Árbol lógico
    'RamaArbolLogico',
    'ArbolLogico',
    
    # PSHA - Principal
    'GMPEWrapper',
    'AnalizadorPSHA',
    'crear_analizador_mexico',
    
    # PSHA - Utilidades
    'calcular_probabilidad_poisson',
    'periodo_retorno_desde_probabilidad',
    'NIVELES_PGA_DEFAULT',
    'PERIODOS_RETORNO_DEFAULT',
]
