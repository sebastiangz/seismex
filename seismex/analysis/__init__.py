"""
SEISMEX Analysis - Módulos de análisis sísmico
==============================================

Módulos disponibles:
- esd: Cálculo de Energy Space Density
- gutenberg_richter: Análisis de relación frecuencia-magnitud
- isoseismal: Generación de mapas isosistas (en desarrollo)
- psha: Análisis probabilístico de amenaza sísmica (planificado)
"""

from seismex.analysis.esd import (
    CalculadoraESD,
    ConfiguracionESD,
    ResultadoESD,
)
from seismex.analysis.gutenberg_richter import AnalizadorGutenbergRichter

__all__ = [
    # ESD
    "CalculadoraESD",
    "ConfiguracionESD",
    "ResultadoESD",
    # Gutenberg-Richter
    "AnalizadorGutenbergRichter",
]
