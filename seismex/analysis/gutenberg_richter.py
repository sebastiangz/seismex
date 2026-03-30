"""
SEISMEX Analysis - Gutenberg-Richter
====================================

Análisis de la relación frecuencia-magnitud.

La implementación completa está en esd.py (clase AnalizadorGutenbergRichter)
Este archivo sirve como punto de entrada del módulo.
"""

# Re-exportar desde esd.py donde está la implementación
from seismex.analysis.esd import AnalizadorGutenbergRichter

__all__ = ['AnalizadorGutenbergRichter']
