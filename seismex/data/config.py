"""
SEISMEX Data - Gestión de Configuración
========================================

Sistema de configuración para API keys, rutas de caché y preferencias.
Soporta:
- Archivo de configuración YAML (~/.seismex/config.yaml)
- Variables de entorno (override)
- Parámetros directos (máxima prioridad)
"""

import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

# =============================================================================
# RUTAS POR DEFECTO
# =============================================================================

SEISMEX_HOME = Path.home() / ".seismex"
CONFIG_FILE = SEISMEX_HOME / "config.yaml"
CACHE_DIR = SEISMEX_HOME / "cache"
LOGS_DIR = SEISMEX_HOME / "logs"

# =============================================================================
# PLANTILLA DE CONFIGURACIÓN
# =============================================================================

CONFIG_TEMPLATE = """# =============================================================================
# SEISMEX - Archivo de Configuración
# =============================================================================
# Ubicación: ~/.seismex/config.yaml
#
# Este archivo contiene la configuración para conectores de datos sísmicos.
# Las variables de entorno con prefijo SEISMEX_ tienen prioridad sobre este archivo.
# Ejemplo: SEISMEX_USGS_EMAIL sobrescribe usgs.email
# =============================================================================

# -----------------------------------------------------------------------------
# Configuración General
# -----------------------------------------------------------------------------
general:
  # Directorio de caché para datos descargados
  cache_dir: ~/.seismex/cache
  
  # Tiempo de expiración del caché en días (0 = sin expiración)
  cache_expiration_days: 30
  
  # Tamaño máximo del caché en MB (0 = sin límite)
  cache_max_size_mb: 1000
  
  # Habilitar compresión de caché
  cache_compression: true
  
  # Nivel de logging: DEBUG, INFO, WARNING, ERROR
  log_level: INFO
  
  # Timeout para requests HTTP en segundos
  timeout: 60
  
  # Reintentos en caso de error
  max_retries: 3
  
  # Delay entre reintentos (segundos)
  retry_delay: 5

# -----------------------------------------------------------------------------
# SSN - Servicio Sismológico Nacional de México
# -----------------------------------------------------------------------------
# El SSN no requiere API key. Los datos se obtienen por web scraping
# o cargando archivos descargados manualmente.
ssn:
  # Habilitar conector SSN
  enabled: true
  
  # URL base del SSN (puede cambiar)
  base_url: http://www2.ssn.unam.mx:8080/catalogo/
  
  # Directorio donde el usuario guarda archivos descargados manualmente
  # Si el web scraping falla, se buscarán aquí
  local_data_dir: ~/seismex_data/ssn
  
  # Formato esperado de archivos locales: csv, excel
  local_format: csv
  
  # User-Agent para requests (algunos sitios bloquean bots)
  user_agent: "Mozilla/5.0 (compatible; SEISMEX/1.0; +https://github.com/seismex)"
  
  # Delay entre requests para no sobrecargar el servidor (segundos)
  request_delay: 2

# -----------------------------------------------------------------------------
# USGS - United States Geological Survey
# -----------------------------------------------------------------------------
# La API de USGS es pública pero requiere email para uso intensivo.
# Sin email, hay límites más estrictos de rate limiting.
usgs:
  # Habilitar conector USGS
  enabled: true
  
  # Email para identificación (recomendado, no obligatorio)
  # Proporcionar email aumenta los límites de rate
  email: ""
  
  # URL base de la API ComCat
  base_url: https://earthquake.usgs.gov/fdsnws/event/1/
  
  # Formato de respuesta: geojson, csv, quakeml
  format: geojson
  
  # Límite de eventos por consulta (máximo 20000)
  max_events_per_query: 20000

# -----------------------------------------------------------------------------
# ISC - International Seismological Centre
# -----------------------------------------------------------------------------
# El ISC-GEM es público y no requiere autenticación.
isc:
  # Habilitar conector ISC
  enabled: true
  
  # URL base del ISC
  base_url: http://www.isc.ac.uk/cgi-bin/web-db-run
  
  # Formato de salida: isf, csv, quakeml
  format: isf
  
  # Catálogo a usar: reviewed, isc-gem, comprehensive
  catalog: isc-gem

# -----------------------------------------------------------------------------
# IRIS/FDSN - Incorporated Research Institutions for Seismology
# -----------------------------------------------------------------------------
# Acceso vía ObsPy. No requiere autenticación para catálogos públicos.
iris:
  # Habilitar conector IRIS
  enabled: true
  
  # Cliente FDSN a usar: IRIS, USGS, ISC, EMSC, etc.
  fdsn_client: IRIS
  
  # Incluir llegadas de fases
  include_arrivals: false
  
  # Incluir mecanismos focales
  include_focal_mechanisms: true

# -----------------------------------------------------------------------------
# GCMT - Global Centroid Moment Tensor
# -----------------------------------------------------------------------------
gcmt:
  # Habilitar conector GCMT
  enabled: false
  
  # URL del catálogo GCMT
  base_url: https://www.globalcmt.org/CMTsearch.html

# -----------------------------------------------------------------------------
# Validación y Calidad de Datos
# -----------------------------------------------------------------------------
quality:
  # Ejecutar validación automática al descargar
  auto_validate: true
  
  # Generar reporte de calidad automáticamente
  auto_quality_report: true
  
  # Directorio para reportes de calidad
  reports_dir: ~/.seismex/reports
  
  # Umbrales de calidad
  thresholds:
    # Porcentaje máximo aceptable de valores faltantes
    max_missing_percent: 10
    
    # Rango válido de latitudes
    lat_min: -90
    lat_max: 90
    
    # Rango válido de longitudes
    lon_min: -180
    lon_max: 180
    
    # Rango válido de profundidades (km)
    depth_min: 0
    depth_max: 700
    
    # Rango válido de magnitudes
    mag_min: -2
    mag_max: 10
"""


# =============================================================================
# DATACLASSES DE CONFIGURACIÓN
# =============================================================================

@dataclass
class GeneralConfig:
    """Configuración general del sistema."""
    cache_dir: Path = CACHE_DIR
    cache_expiration_days: int = 30
    cache_max_size_mb: int = 1000
    cache_compression: bool = True
    log_level: str = "INFO"
    timeout: int = 60
    max_retries: int = 3
    retry_delay: int = 5


@dataclass
class SSNConfig:
    """Configuración del conector SSN."""
    enabled: bool = True
    base_url: str = "http://www2.ssn.unam.mx:8080/catalogo/"
    local_data_dir: Path = Path.home() / "seismex_data" / "ssn"
    local_format: str = "csv"
    user_agent: str = "Mozilla/5.0 (compatible; SEISMEX/1.0)"
    request_delay: float = 2.0


@dataclass
class USGSConfig:
    """Configuración del conector USGS."""
    enabled: bool = True
    email: str = ""
    base_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/"
    format: str = "geojson"
    max_events_per_query: int = 20000


@dataclass
class ISCConfig:
    """Configuración del conector ISC."""
    enabled: bool = True
    base_url: str = "http://www.isc.ac.uk/cgi-bin/web-db-run"
    format: str = "isf"
    catalog: str = "isc-gem"


@dataclass
class IRISConfig:
    """Configuración del conector IRIS/FDSN."""
    enabled: bool = True
    fdsn_client: str = "IRIS"
    include_arrivals: bool = False
    include_focal_mechanisms: bool = True


@dataclass
class QualityThresholds:
    """Umbrales para validación de calidad."""
    max_missing_percent: float = 10.0
    lat_min: float = -90.0
    lat_max: float = 90.0
    lon_min: float = -180.0
    lon_max: float = 180.0
    depth_min: float = 0.0
    depth_max: float = 700.0
    mag_min: float = -2.0
    mag_max: float = 10.0


@dataclass
class QualityConfig:
    """Configuración de validación y calidad."""
    auto_validate: bool = True
    auto_quality_report: bool = True
    reports_dir: Path = SEISMEX_HOME / "reports"
    thresholds: QualityThresholds = field(default_factory=QualityThresholds)


@dataclass
class SeismexConfig:
    """Configuración completa de SEISMEX."""
    general: GeneralConfig = field(default_factory=GeneralConfig)
    ssn: SSNConfig = field(default_factory=SSNConfig)
    usgs: USGSConfig = field(default_factory=USGSConfig)
    isc: ISCConfig = field(default_factory=ISCConfig)
    iris: IRISConfig = field(default_factory=IRISConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)


# =============================================================================
# GESTOR DE CONFIGURACIÓN
# =============================================================================

class ConfigManager:
    """
    Gestor de configuración de SEISMEX.
    
    Prioridad de configuración (mayor a menor):
    1. Parámetros directos en código
    2. Variables de entorno (SEISMEX_*)
    3. Archivo de configuración (~/.seismex/config.yaml)
    4. Valores por defecto
    
    Ejemplo de uso:
    
        >>> config = ConfigManager()
        >>> print(config.usgs.email)
        >>> config.set('usgs.email', 'mi@email.com')
        >>> config.save()
    """
    
    _instance: Optional['ConfigManager'] = None
    _config: SeismexConfig
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el gestor de configuración."""
        if self._initialized:
            return
        
        self._config = SeismexConfig()
        self._config_file = CONFIG_FILE
        
        # Crear directorios necesarios
        self._ensure_directories()
        
        # Cargar configuración
        self._load_config()
        
        self._initialized = True
    
    def _ensure_directories(self) -> None:
        """Crea los directorios necesarios si no existen."""
        directories = [
            SEISMEX_HOME,
            CACHE_DIR,
            LOGS_DIR,
            self._config.quality.reports_dir,
        ]
        
        for directory in directories:
            directory = Path(str(directory).replace("~", str(Path.home())))
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> None:
        """Carga la configuración desde archivo y variables de entorno."""
        # 1. Cargar desde archivo YAML si existe
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f) or {}
                self._apply_yaml_config(yaml_config)
                logger.info(f"Configuración cargada desde {self._config_file}")
            except Exception as e:
                logger.warning(f"Error al cargar configuración: {e}")
        else:
            logger.info("Archivo de configuración no encontrado, usando valores por defecto")
            self._create_default_config()
        
        # 2. Override con variables de entorno
        self._apply_env_overrides()
    
    def _apply_yaml_config(self, yaml_config: Dict[str, Any]) -> None:
        """Aplica configuración desde diccionario YAML."""
        # General
        if 'general' in yaml_config:
            gen = yaml_config['general']
            if 'cache_dir' in gen:
                self._config.general.cache_dir = Path(
                    str(gen['cache_dir']).replace("~", str(Path.home()))
                )
            if 'cache_expiration_days' in gen:
                self._config.general.cache_expiration_days = gen['cache_expiration_days']
            if 'cache_max_size_mb' in gen:
                self._config.general.cache_max_size_mb = gen['cache_max_size_mb']
            if 'cache_compression' in gen:
                self._config.general.cache_compression = gen['cache_compression']
            if 'log_level' in gen:
                self._config.general.log_level = gen['log_level']
            if 'timeout' in gen:
                self._config.general.timeout = gen['timeout']
            if 'max_retries' in gen:
                self._config.general.max_retries = gen['max_retries']
            if 'retry_delay' in gen:
                self._config.general.retry_delay = gen['retry_delay']
        
        # SSN
        if 'ssn' in yaml_config:
            ssn = yaml_config['ssn']
            if 'enabled' in ssn:
                self._config.ssn.enabled = ssn['enabled']
            if 'base_url' in ssn:
                self._config.ssn.base_url = ssn['base_url']
            if 'local_data_dir' in ssn:
                self._config.ssn.local_data_dir = Path(
                    str(ssn['local_data_dir']).replace("~", str(Path.home()))
                )
            if 'local_format' in ssn:
                self._config.ssn.local_format = ssn['local_format']
            if 'user_agent' in ssn:
                self._config.ssn.user_agent = ssn['user_agent']
            if 'request_delay' in ssn:
                self._config.ssn.request_delay = ssn['request_delay']
        
        # USGS
        if 'usgs' in yaml_config:
            usgs = yaml_config['usgs']
            if 'enabled' in usgs:
                self._config.usgs.enabled = usgs['enabled']
            if 'email' in usgs:
                self._config.usgs.email = usgs['email']
            if 'base_url' in usgs:
                self._config.usgs.base_url = usgs['base_url']
            if 'format' in usgs:
                self._config.usgs.format = usgs['format']
            if 'max_events_per_query' in usgs:
                self._config.usgs.max_events_per_query = usgs['max_events_per_query']
        
        # ISC
        if 'isc' in yaml_config:
            isc = yaml_config['isc']
            if 'enabled' in isc:
                self._config.isc.enabled = isc['enabled']
            if 'base_url' in isc:
                self._config.isc.base_url = isc['base_url']
            if 'format' in isc:
                self._config.isc.format = isc['format']
            if 'catalog' in isc:
                self._config.isc.catalog = isc['catalog']
        
        # IRIS
        if 'iris' in yaml_config:
            iris = yaml_config['iris']
            if 'enabled' in iris:
                self._config.iris.enabled = iris['enabled']
            if 'fdsn_client' in iris:
                self._config.iris.fdsn_client = iris['fdsn_client']
            if 'include_arrivals' in iris:
                self._config.iris.include_arrivals = iris['include_arrivals']
            if 'include_focal_mechanisms' in iris:
                self._config.iris.include_focal_mechanisms = iris['include_focal_mechanisms']
        
        # Quality
        if 'quality' in yaml_config:
            quality = yaml_config['quality']
            if 'auto_validate' in quality:
                self._config.quality.auto_validate = quality['auto_validate']
            if 'auto_quality_report' in quality:
                self._config.quality.auto_quality_report = quality['auto_quality_report']
            if 'reports_dir' in quality:
                self._config.quality.reports_dir = Path(
                    str(quality['reports_dir']).replace("~", str(Path.home()))
                )
            if 'thresholds' in quality:
                th = quality['thresholds']
                for key in ['max_missing_percent', 'lat_min', 'lat_max', 
                           'lon_min', 'lon_max', 'depth_min', 'depth_max',
                           'mag_min', 'mag_max']:
                    if key in th:
                        setattr(self._config.quality.thresholds, key, th[key])
    
    def _apply_env_overrides(self) -> None:
        """Aplica overrides desde variables de entorno."""
        env_mappings = {
            'SEISMEX_CACHE_DIR': ('general', 'cache_dir', Path),
            'SEISMEX_LOG_LEVEL': ('general', 'log_level', str),
            'SEISMEX_TIMEOUT': ('general', 'timeout', int),
            
            'SEISMEX_SSN_ENABLED': ('ssn', 'enabled', lambda x: x.lower() == 'true'),
            'SEISMEX_SSN_LOCAL_DIR': ('ssn', 'local_data_dir', Path),
            
            'SEISMEX_USGS_EMAIL': ('usgs', 'email', str),
            'SEISMEX_USGS_ENABLED': ('usgs', 'enabled', lambda x: x.lower() == 'true'),
            
            'SEISMEX_ISC_ENABLED': ('isc', 'enabled', lambda x: x.lower() == 'true'),
            'SEISMEX_ISC_CATALOG': ('isc', 'catalog', str),
            
            'SEISMEX_IRIS_ENABLED': ('iris', 'enabled', lambda x: x.lower() == 'true'),
            'SEISMEX_IRIS_CLIENT': ('iris', 'fdsn_client', str),
        }
        
        for env_var, (section, key, converter) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    section_obj = getattr(self._config, section)
                    setattr(section_obj, key, converter(value))
                    logger.debug(f"Override desde {env_var}: {section}.{key} = {value}")
                except Exception as e:
                    logger.warning(f"Error aplicando {env_var}: {e}")
    
    def _create_default_config(self) -> None:
        """Crea archivo de configuración con valores por defecto."""
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, 'w', encoding='utf-8') as f:
                f.write(CONFIG_TEMPLATE)
            logger.info(f"Archivo de configuración creado: {self._config_file}")
        except Exception as e:
            logger.warning(f"No se pudo crear archivo de configuración: {e}")
    
    # =========================================================================
    # PROPIEDADES DE ACCESO
    # =========================================================================
    
    @property
    def general(self) -> GeneralConfig:
        """Acceso a configuración general."""
        return self._config.general
    
    @property
    def ssn(self) -> SSNConfig:
        """Acceso a configuración SSN."""
        return self._config.ssn
    
    @property
    def usgs(self) -> USGSConfig:
        """Acceso a configuración USGS."""
        return self._config.usgs
    
    @property
    def isc(self) -> ISCConfig:
        """Acceso a configuración ISC."""
        return self._config.isc
    
    @property
    def iris(self) -> IRISConfig:
        """Acceso a configuración IRIS."""
        return self._config.iris
    
    @property
    def quality(self) -> QualityConfig:
        """Acceso a configuración de calidad."""
        return self._config.quality
    
    @property
    def cache_expiration(self) -> timedelta:
        """Retorna el tiempo de expiración del caché como timedelta."""
        return timedelta(days=self._config.general.cache_expiration_days)
    
    # =========================================================================
    # MÉTODOS PÚBLICOS
    # =========================================================================
    
    def set(self, key: str, value: Any) -> None:
        """
        Establece un valor de configuración.
        
        Args:
            key: Clave en formato 'section.attribute' (ej: 'usgs.email')
            value: Valor a establecer
        """
        parts = key.split('.')
        if len(parts) != 2:
            raise ValueError(f"Formato de clave inválido: {key}. Use 'section.attribute'")
        
        section_name, attr_name = parts
        section = getattr(self._config, section_name, None)
        
        if section is None:
            raise ValueError(f"Sección no encontrada: {section_name}")
        
        if not hasattr(section, attr_name):
            raise ValueError(f"Atributo no encontrado: {attr_name} en {section_name}")
        
        setattr(section, attr_name, value)
        logger.debug(f"Configuración actualizada: {key} = {value}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración.
        
        Args:
            key: Clave en formato 'section.attribute'
            default: Valor por defecto si no existe
            
        Returns:
            Valor de configuración
        """
        try:
            parts = key.split('.')
            obj = self._config
            for part in parts:
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            return default
    
    def save(self) -> None:
        """Guarda la configuración actual al archivo YAML."""
        config_dict = {
            'general': {
                'cache_dir': str(self._config.general.cache_dir),
                'cache_expiration_days': self._config.general.cache_expiration_days,
                'cache_max_size_mb': self._config.general.cache_max_size_mb,
                'cache_compression': self._config.general.cache_compression,
                'log_level': self._config.general.log_level,
                'timeout': self._config.general.timeout,
                'max_retries': self._config.general.max_retries,
                'retry_delay': self._config.general.retry_delay,
            },
            'ssn': {
                'enabled': self._config.ssn.enabled,
                'base_url': self._config.ssn.base_url,
                'local_data_dir': str(self._config.ssn.local_data_dir),
                'local_format': self._config.ssn.local_format,
                'user_agent': self._config.ssn.user_agent,
                'request_delay': self._config.ssn.request_delay,
            },
            'usgs': {
                'enabled': self._config.usgs.enabled,
                'email': self._config.usgs.email,
                'base_url': self._config.usgs.base_url,
                'format': self._config.usgs.format,
                'max_events_per_query': self._config.usgs.max_events_per_query,
            },
            'isc': {
                'enabled': self._config.isc.enabled,
                'base_url': self._config.isc.base_url,
                'format': self._config.isc.format,
                'catalog': self._config.isc.catalog,
            },
            'iris': {
                'enabled': self._config.iris.enabled,
                'fdsn_client': self._config.iris.fdsn_client,
                'include_arrivals': self._config.iris.include_arrivals,
                'include_focal_mechanisms': self._config.iris.include_focal_mechanisms,
            },
            'quality': {
                'auto_validate': self._config.quality.auto_validate,
                'auto_quality_report': self._config.quality.auto_quality_report,
                'reports_dir': str(self._config.quality.reports_dir),
                'thresholds': {
                    'max_missing_percent': self._config.quality.thresholds.max_missing_percent,
                    'lat_min': self._config.quality.thresholds.lat_min,
                    'lat_max': self._config.quality.thresholds.lat_max,
                    'lon_min': self._config.quality.thresholds.lon_min,
                    'lon_max': self._config.quality.thresholds.lon_max,
                    'depth_min': self._config.quality.thresholds.depth_min,
                    'depth_max': self._config.quality.thresholds.depth_max,
                    'mag_min': self._config.quality.thresholds.mag_min,
                    'mag_max': self._config.quality.thresholds.mag_max,
                }
            }
        }
        
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, 'w', encoding='utf-8') as f:
                f.write("# SEISMEX Configuration - Auto-generated\n")
                f.write("# Edite este archivo para personalizar la configuración\n\n")
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Configuración guardada en {self._config_file}")
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            raise
    
    def reset(self) -> None:
        """Restablece la configuración a valores por defecto."""
        self._config = SeismexConfig()
        self._ensure_directories()
        logger.info("Configuración restablecida a valores por defecto")
    
    def show(self) -> str:
        """
        Muestra la configuración actual de forma legible.
        
        Returns:
            String con la configuración formateada
        """
        lines = [
            "=" * 60,
            "SEISMEX - Configuración Actual",
            "=" * 60,
            "",
            "General:",
            f"  Cache Dir: {self._config.general.cache_dir}",
            f"  Cache Expiración: {self._config.general.cache_expiration_days} días",
            f"  Log Level: {self._config.general.log_level}",
            f"  Timeout: {self._config.general.timeout}s",
            "",
            "SSN (México):",
            f"  Habilitado: {self._config.ssn.enabled}",
            f"  URL Base: {self._config.ssn.base_url}",
            f"  Datos Locales: {self._config.ssn.local_data_dir}",
            "",
            "USGS:",
            f"  Habilitado: {self._config.usgs.enabled}",
            f"  Email: {self._config.usgs.email or '(no configurado)'}",
            f"  Formato: {self._config.usgs.format}",
            "",
            "ISC:",
            f"  Habilitado: {self._config.isc.enabled}",
            f"  Catálogo: {self._config.isc.catalog}",
            "",
            "IRIS/FDSN:",
            f"  Habilitado: {self._config.iris.enabled}",
            f"  Cliente: {self._config.iris.fdsn_client}",
            "",
            "Calidad:",
            f"  Auto-validación: {self._config.quality.auto_validate}",
            f"  Auto-reporte: {self._config.quality.auto_quality_report}",
            "=" * 60,
        ]
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"ConfigManager(config_file='{self._config_file}')"


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def get_config() -> ConfigManager:
    """
    Obtiene la instancia global del gestor de configuración.
    
    Returns:
        ConfigManager singleton
    """
    return ConfigManager()


def configure(**kwargs) -> None:
    """
    Configura SEISMEX con los parámetros proporcionados.
    
    Args:
        **kwargs: Pares clave-valor en formato 'section_attribute'
                  Ejemplo: usgs_email='mi@email.com'
    """
    config = get_config()
    for key, value in kwargs.items():
        # Convertir underscore a punto: usgs_email -> usgs.email
        key_parts = key.split('_', 1)
        if len(key_parts) == 2:
            config.set(f"{key_parts[0]}.{key_parts[1]}", value)
        else:
            logger.warning(f"Formato de clave no reconocido: {key}")


# =============================================================================
# INICIALIZACIÓN AL IMPORTAR
# =============================================================================

# No inicializar automáticamente para evitar efectos secundarios
# El usuario debe llamar get_config() explícitamente
