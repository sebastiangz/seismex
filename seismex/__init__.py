"""
SEISMEX - Sistema de Análisis Sísmico para México
=================================================

Herramientas avanzadas para análisis de riesgo sísmico incluyendo:
- Energy Space Density (ESD)
- Análisis de Gutenberg-Richter
- Mapas isosistas
- Análisis probabilístico de amenaza sísmica (PSHA)
- Optimización multiobjetivo con algoritmos genéticos

Ejemplo de uso rápido
---------------------
>>> from seismex import CatalogoSismico, CalculadoraESD, ConfiguracionESD
>>> 
>>> # Cargar catálogo
>>> catalogo = CatalogoSismico.desde_csv("sismos_mexico.csv")
>>> 
>>> # Calcular ESD
>>> config = ConfiguracionESD(tamano_celda=10.0)
>>> calculadora = CalculadoraESD(config)
>>> resultado = calculadora.calcular(catalogo)
>>> 
>>> # Visualizar
>>> from seismex.visualization import VisualizadorESD
>>> viz = VisualizadorESD()
>>> viz.graficar_secciones_horizontales(resultado)
"""

__version__ = "0.1.0"
__author__ = "SEISMEX Team"
__email__ = "sebastiangz@ucol.mx"
__license__ = "MIT"

# Imports principales para acceso conveniente
from seismex.core.catalog import CatalogoSismico
from seismex.analysis.esd import (
    CalculadoraESD,
    ConfiguracionESD,
    ResultadoESD,
)
from seismex.analysis.gutenberg_richter import AnalizadorGutenbergRichter

__all__ = [
    # Versión
    "__version__",
    # Core
    "CatalogoSismico",
    # Analysis
    "CalculadoraESD",
    "ConfiguracionESD",
    "ResultadoESD",
    "AnalizadorGutenbergRichter",
]
