"""
SEISMEX Data - Módulo de Conectores de Datos Sísmicos
======================================================

Este módulo proporciona conectores para obtener datos sísmicos de múltiples
fuentes, con prioridad para México.

Conectores disponibles (en orden de prioridad):

1. **SSN** (Servicio Sismológico Nacional de México) - PRIORIDAD
   - Fuente principal para México
   - Web scraping con fallback a archivos locales
   - Permite al usuario proporcionar archivos descargados manualmente

2. **USGS** (United States Geological Survey)
   - API pública, no requiere autenticación
   - Email opcional pero recomendado para mejor rate limit
   - Excelente cobertura global y para México

3. **ISC** (International Seismological Centre)
   - Catálogo ISC-GEM para sismos históricos significativos
   - Datos revisados de alta calidad
   - No requiere autenticación

4. **IRIS/FDSN** (vía ObsPy)
   - Acceso a múltiples servicios FDSN internacionales
   - Mecanismos focales y tensores de momento
   - Requiere ObsPy instalado

Configuración:
    
    La configuración se almacena en ~/.seismex/config.yaml
    
    Ejemplo de configuración:
    
        general:
          cache_enabled: true
          cache_expiration_days: 30
        
        ssn:
          local_data_dir: ~/seismex_data/ssn
        
        usgs:
          email: "mi@email.com"  # Opcional pero recomendado
        
        quality:
          auto_validate: true

Uso básico:

    >>> from seismex.data import descargar_ssn, descargar_usgs
    >>> 
    >>> # Descargar del SSN (prioridad)
    >>> resultado = descargar_ssn(
    ...     fecha_inicio='2024-01-01',
    ...     region='colima',
    ...     magnitud_min=3.5
    ... )
    >>> 
    >>> # O cargar archivo local del SSN
    >>> from seismex.data import cargar_ssn_local
    >>> resultado = cargar_ssn_local('~/seismex_data/ssn/catalogo_2024.csv')
    >>> 
    >>> # Descargar de USGS
    >>> resultado = descargar_usgs(
    ...     fecha_inicio='2024-01-01',
    ...     region='nacional',
    ...     magnitud_min=4.0
    ... )

Configuración programática:

    >>> from seismex.data import configure, get_config
    >>> 
    >>> # Configurar email para USGS
    >>> configure(usgs_email='mi@email.com')
    >>> 
    >>> # Configurar directorio local SSN
    >>> configure(ssn_local_data_dir='~/mis_datos/ssn')
    >>> 
    >>> # Ver configuración actual
    >>> print(get_config().show())

Validación de calidad:

    >>> from seismex.data import validar_catalogo
    >>> 
    >>> reporte = validar_catalogo(resultado.data)
    >>> print(reporte)
    >>> reporte.exportar_json('reporte_calidad.json')
"""

__version__ = "1.0.0"
__author__ = "SEISMEX Team"

# =============================================================================
# IMPORTACIONES PRINCIPALES
# =============================================================================

# Configuración (importar primero)
from seismex.data.config import (
    # Clases de configuración
    SeismexConfig,
    ConfigManager,
    GeneralConfig,
    SSNConfig,
    USGSConfig,
    ISCConfig,
    IRISConfig,
    QualityConfig,
    
    # Funciones de conveniencia
    get_config,
    configure,
)

# Sistema de caché
from seismex.data.cache import (
    CacheManager,
    CacheEntry,
    CacheStats,
    get_cache,
    clear_cache,
)

# Clases base
from seismex.data.base import (
    ConectorBase,
    QueryParams,
    DownloadResult,
    CATALOG_COLUMNS,
    REGIONES_MEXICO,
)

# Validación de calidad
from seismex.data.quality import (
    QualityValidator,
    QualityReport,
    QualityIssue,
    ColumnStats,
    validar_catalogo,
    validacion_rapida,
)

# =============================================================================
# CONECTORES (en orden de prioridad para México)
# =============================================================================

# 1. SSN - Servicio Sismológico Nacional (PRIORIDAD para SEISMEX)
from seismex.data.ssn import (
    ConectorSSN,
    descargar_ssn,
    cargar_ssn_local,
)

# 2. USGS - US Geological Survey
from seismex.data.usgs import (
    ConectorUSGS,
    descargar_usgs,
    descargar_usgs_mexico,
)

# 3. ISC - International Seismological Centre
from seismex.data.isc import (
    ConectorISC,
    descargar_isc,
    descargar_isc_gem_mexico,
)

# 4. IRIS/FDSN - ObsPy
from seismex.data.iris import (
    ConectorIRIS,
    descargar_iris,
    descargar_fdsn,
    obtener_mecanismos_focales,
)

# =============================================================================
# FUNCIONES DE ALTO NIVEL
# =============================================================================

def descargar(
    fuente: str = 'ssn',
    **kwargs
) -> DownloadResult:
    """
    Función unificada para descargar datos sísmicos.
    
    Args:
        fuente: Fuente de datos ('ssn', 'usgs', 'isc', 'iris')
        **kwargs: Parámetros de descarga (fecha_inicio, region, magnitud_min, etc.)
        
    Returns:
        DownloadResult con los datos
        
    Ejemplo:
        >>> resultado = descargar('ssn', region='colima', magnitud_min=3.5)
        >>> resultado = descargar('usgs', fecha_inicio='2024-01-01')
    """
    fuente = fuente.lower()
    
    conectores = {
        'ssn': ConectorSSN,
        'usgs': ConectorUSGS,
        'isc': ConectorISC,
        'iris': ConectorIRIS,
        'fdsn': ConectorIRIS,
    }
    
    if fuente not in conectores:
        available = ', '.join(conectores.keys())
        raise ValueError(
            f"Fuente '{fuente}' no reconocida. "
            f"Disponibles: {available}"
        )
    
    conector = conectores[fuente]()
    return conector.descargar(**kwargs)


def descargar_mexico(
    fuente: str = 'ssn',
    magnitud_min: float = 3.5,
    **kwargs
) -> DownloadResult:
    """
    Descarga datos sísmicos para México completo.
    
    Args:
        fuente: Fuente de datos (default 'ssn' por ser SEISMEX)
        magnitud_min: Magnitud mínima
        **kwargs: Parámetros adicionales
        
    Returns:
        DownloadResult
    """
    return descargar(
        fuente=fuente,
        region='nacional',
        magnitud_min=magnitud_min,
        **kwargs
    )


def info_conectores() -> str:
    """
    Muestra información sobre los conectores disponibles.
    
    Returns:
        String formateado con información de conectores
    """
    lines = [
        "=" * 70,
        "SEISMEX - Conectores de Datos Sísmicos",
        "=" * 70,
        "",
        "Conectores disponibles (en orden de prioridad):",
        "",
        "1. SSN (Servicio Sismológico Nacional de México) ⭐ PRIORIDAD",
        "   • Fuente principal para datos sísmicos de México",
        "   • Web scraping del portal SSN",
        "   • Fallback a archivos locales descargados por el usuario",
        f"   • Directorio local: {get_config().ssn.local_data_dir}",
        "",
        "2. USGS (US Geological Survey)",
        "   • API pública, no requiere autenticación",
        "   • Email opcional pero recomendado para mejor rate limit",
        f"   • Email configurado: {'✓' if get_config().usgs.email else '✗'}",
        "",
        "3. ISC (International Seismological Centre)",
        "   • Catálogo ISC-GEM para sismos históricos (M >= 5.5)",
        "   • Datos revisados de alta calidad",
        "   • No requiere autenticación",
        "",
        "4. IRIS/FDSN (vía ObsPy)",
        "   • Múltiples servicios FDSN internacionales",
        "   • Mecanismos focales disponibles",
        "   • Requiere ObsPy instalado",
        "",
        "=" * 70,
        "Uso:",
        "",
        "  # Descargar del SSN (prioridad para SEISMEX)",
        "  resultado = descargar_ssn(region='colima', magnitud_min=3.5)",
        "",
        "  # Cargar archivo local del SSN",
        "  resultado = cargar_ssn_local('catalogo_2024.csv')",
        "",
        "  # Función unificada",
        "  resultado = descargar('ssn', region='nacional')",
        "",
        "=" * 70,
    ]
    
    return "\n".join(lines)


def estado_cache() -> str:
    """Muestra estado del caché."""
    cache = get_cache()
    stats = cache.stats()
    
    lines = [
        "=" * 50,
        "SEISMEX - Estado del Caché",
        "=" * 50,
        f"Directorio: {cache.cache_dir}",
        f"Entradas totales: {stats.total_entries}",
        f"Tamaño total: {stats.total_size_mb:.2f} MB",
        f"Hits totales: {stats.total_hits}",
        f"Entradas expiradas: {stats.expired_entries}",
        "=" * 50,
    ]
    
    return "\n".join(lines)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Versión
    '__version__',
    
    # Configuración
    'SeismexConfig',
    'ConfigManager',
    'GeneralConfig',
    'SSNConfig',
    'USGSConfig',
    'ISCConfig',
    'IRISConfig',
    'QualityConfig',
    'get_config',
    'configure',
    
    # Caché
    'CacheManager',
    'CacheEntry',
    'CacheStats',
    'get_cache',
    'clear_cache',
    
    # Base
    'ConectorBase',
    'QueryParams',
    'DownloadResult',
    'CATALOG_COLUMNS',
    'REGIONES_MEXICO',
    
    # Calidad
    'QualityValidator',
    'QualityReport',
    'QualityIssue',
    'ColumnStats',
    'validar_catalogo',
    'validacion_rapida',
    
    # SSN (PRIORIDAD)
    'ConectorSSN',
    'descargar_ssn',
    'cargar_ssn_local',
    
    # USGS
    'ConectorUSGS',
    'descargar_usgs',
    'descargar_usgs_mexico',
    
    # ISC
    'ConectorISC',
    'descargar_isc',
    'descargar_isc_gem_mexico',
    
    # IRIS/FDSN
    'ConectorIRIS',
    'descargar_iris',
    'descargar_fdsn',
    'obtener_mecanismos_focales',
    
    # Funciones de alto nivel
    'descargar',
    'descargar_mexico',
    'info_conectores',
    'estado_cache',
]
