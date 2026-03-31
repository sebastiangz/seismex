"""
SEISMEX Data - Clase Base para Conectores
==========================================

Define la interfaz común para todos los conectores de datos sísmicos.
Todos los conectores (SSN, USGS, ISC, IRIS) heredan de esta clase.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Union, Tuple
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES Y TIPOS
# =============================================================================

# Columnas estándar del catálogo SEISMEX
CATALOG_COLUMNS = [
    'fecha',           # datetime: Fecha y hora UTC
    'latitud',         # float: Latitud en grados
    'longitud',        # float: Longitud en grados  
    'profundidad_km',  # float: Profundidad en km
    'magnitud',        # float: Magnitud
    'tipo_magnitud',   # str: Tipo de magnitud (Mw, Ml, Mb, Ms, etc.)
    'fuente',          # str: Fuente de datos (SSN, USGS, ISC, etc.)
    'id_evento',       # str: ID único del evento
    'lugar',           # str: Descripción del lugar (opcional)
    'incertidumbre_h', # float: Incertidumbre horizontal en km (opcional)
    'incertidumbre_z', # float: Incertidumbre vertical en km (opcional)
    'incertidumbre_m', # float: Incertidumbre de magnitud (opcional)
    'rms',             # float: RMS del ajuste (opcional)
    'gap',             # float: Gap azimutal en grados (opcional)
    'nst',             # int: Número de estaciones (opcional)
]

# Regiones predefinidas de México
REGIONES_MEXICO = {
    'nacional': {'lat_min': 14.0, 'lat_max': 33.0, 'lon_min': -118.0, 'lon_max': -86.0},
    'colima': {'lat_min': 18.5, 'lat_max': 20.0, 'lon_min': -105.0, 'lon_max': -103.0},
    'jalisco': {'lat_min': 19.0, 'lat_max': 22.5, 'lon_min': -106.0, 'lon_max': -101.5},
    'michoacan': {'lat_min': 17.5, 'lat_max': 20.5, 'lon_min': -104.0, 'lon_max': -100.0},
    'guerrero': {'lat_min': 16.0, 'lat_max': 18.5, 'lon_min': -102.0, 'lon_max': -98.0},
    'oaxaca': {'lat_min': 15.0, 'lat_max': 18.0, 'lon_min': -98.5, 'lon_max': -94.0},
    'chiapas': {'lat_min': 14.0, 'lat_max': 17.5, 'lon_min': -94.5, 'lon_max': -90.0},
    'cdmx': {'lat_min': 18.5, 'lat_max': 20.5, 'lon_min': -100.0, 'lon_max': -98.0},
    'veracruz': {'lat_min': 17.0, 'lat_max': 22.5, 'lon_min': -98.0, 'lon_max': -94.0},
    'baja_california': {'lat_min': 28.0, 'lat_max': 33.0, 'lon_min': -118.0, 'lon_max': -112.0},
    'golfo_california': {'lat_min': 22.0, 'lat_max': 32.0, 'lon_min': -115.0, 'lon_max': -106.0},
    'peninsula_yucatan': {'lat_min': 18.0, 'lat_max': 22.0, 'lon_min': -92.0, 'lon_max': -86.0},
}


# =============================================================================
# DATACLASSES DE RESULTADO
# =============================================================================

@dataclass
class QueryParams:
    """Parámetros de consulta para conectores."""
    fecha_inicio: Optional[Union[str, datetime, date]] = None
    fecha_fin: Optional[Union[str, datetime, date]] = None
    lat_min: Optional[float] = None
    lat_max: Optional[float] = None
    lon_min: Optional[float] = None
    lon_max: Optional[float] = None
    magnitud_min: Optional[float] = None
    magnitud_max: Optional[float] = None
    profundidad_min: Optional[float] = None
    profundidad_max: Optional[float] = None
    region: Optional[str] = None
    limite: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario, excluyendo valores None."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, (datetime, date)):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result
    
    def apply_region(self) -> 'QueryParams':
        """Aplica los límites de una región predefinida."""
        if self.region and self.region.lower() in REGIONES_MEXICO:
            bounds = REGIONES_MEXICO[self.region.lower()]
            if self.lat_min is None:
                self.lat_min = bounds['lat_min']
            if self.lat_max is None:
                self.lat_max = bounds['lat_max']
            if self.lon_min is None:
                self.lon_min = bounds['lon_min']
            if self.lon_max is None:
                self.lon_max = bounds['lon_max']
        return self
    
    def validate(self) -> List[str]:
        """Valida los parámetros y retorna lista de errores."""
        errors = []
        
        if self.lat_min is not None and self.lat_max is not None:
            if self.lat_min >= self.lat_max:
                errors.append("lat_min debe ser menor que lat_max")
        
        if self.lon_min is not None and self.lon_max is not None:
            if self.lon_min >= self.lon_max:
                errors.append("lon_min debe ser menor que lon_max")
        
        if self.magnitud_min is not None and self.magnitud_max is not None:
            if self.magnitud_min >= self.magnitud_max:
                errors.append("magnitud_min debe ser menor que magnitud_max")
        
        if self.lat_min is not None and (self.lat_min < -90 or self.lat_min > 90):
            errors.append("lat_min debe estar entre -90 y 90")
        
        if self.lat_max is not None and (self.lat_max < -90 or self.lat_max > 90):
            errors.append("lat_max debe estar entre -90 y 90")
        
        if self.lon_min is not None and (self.lon_min < -180 or self.lon_min > 180):
            errors.append("lon_min debe estar entre -180 y 180")
        
        if self.lon_max is not None and (self.lon_max < -180 or self.lon_max > 180):
            errors.append("lon_max debe estar entre -180 y 180")
        
        return errors


@dataclass
class DownloadResult:
    """Resultado de una descarga de datos."""
    success: bool
    data: Optional[pd.DataFrame]
    source: str
    query_params: QueryParams
    events_count: int
    download_time: float
    from_cache: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        cache_str = " (desde caché)" if self.from_cache else ""
        return (
            f"{status} {self.source}: {self.events_count} eventos"
            f"{cache_str} ({self.download_time:.2f}s)"
        )


# =============================================================================
# CLASE BASE ABSTRACTA
# =============================================================================

class ConectorBase(ABC):
    """
    Clase base abstracta para conectores de datos sísmicos.
    
    Define la interfaz común que todos los conectores deben implementar.
    Proporciona funcionalidad común como normalización de datos,
    validación y gestión de caché.
    
    Los conectores específicos (SSN, USGS, ISC, IRIS) heredan de esta clase
    e implementan los métodos abstractos.
    """
    
    # Nombre del conector (override en subclases)
    NOMBRE: str = "base"
    
    def __init__(
        self,
        usar_cache: bool = True,
        timeout: int = 60,
        max_reintentos: int = 3,
        delay_reintentos: int = 5
    ):
        """
        Inicializa el conector base.
        
        Args:
            usar_cache: Habilitar caché de datos
            timeout: Timeout para requests HTTP en segundos
            max_reintentos: Número máximo de reintentos
            delay_reintentos: Delay entre reintentos en segundos
        """
        from seismex.data.config import get_config
        from seismex.data.cache import get_cache
        
        self.config = get_config()
        self.usar_cache = usar_cache
        self.timeout = timeout or self.config.general.timeout
        self.max_reintentos = max_reintentos or self.config.general.max_retries
        self.delay_reintentos = delay_reintentos or self.config.general.retry_delay
        
        self._cache = get_cache() if usar_cache else None
        
        logger.debug(f"Conector {self.NOMBRE} inicializado")
    
    # =========================================================================
    # MÉTODOS ABSTRACTOS (deben implementarse en subclases)
    # =========================================================================
    
    @abstractmethod
    def descargar(
        self,
        fecha_inicio: Optional[Union[str, datetime, date]] = None,
        fecha_fin: Optional[Union[str, datetime, date]] = None,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        magnitud_min: Optional[float] = None,
        magnitud_max: Optional[float] = None,
        **kwargs
    ) -> DownloadResult:
        """
        Descarga datos sísmicos de la fuente.
        
        Args:
            fecha_inicio: Fecha inicial (YYYY-MM-DD o datetime)
            fecha_fin: Fecha final (YYYY-MM-DD o datetime)
            lat_min: Latitud mínima
            lat_max: Latitud máxima
            lon_min: Longitud mínima
            lon_max: Longitud máxima
            magnitud_min: Magnitud mínima
            magnitud_max: Magnitud máxima
            **kwargs: Parámetros adicionales específicos del conector
            
        Returns:
            DownloadResult con los datos y metadatos
        """
        pass
    
    @abstractmethod
    def _fetch_data(self, params: QueryParams) -> pd.DataFrame:
        """
        Obtiene datos crudos de la fuente (implementación interna).
        
        Args:
            params: Parámetros de consulta
            
        Returns:
            DataFrame con datos crudos
        """
        pass
    
    @abstractmethod
    def _normalizar_datos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza datos al formato estándar SEISMEX.
        
        Cada fuente tiene su propio formato de columnas.
        Este método mapea al formato común.
        
        Args:
            df: DataFrame con datos crudos
            
        Returns:
            DataFrame normalizado
        """
        pass
    
    # =========================================================================
    # MÉTODOS COMUNES
    # =========================================================================
    
    def descargar_region(
        self,
        region: str,
        fecha_inicio: Optional[Union[str, datetime, date]] = None,
        fecha_fin: Optional[Union[str, datetime, date]] = None,
        magnitud_min: Optional[float] = None,
        **kwargs
    ) -> DownloadResult:
        """
        Descarga datos de una región predefinida de México.
        
        Args:
            region: Nombre de la región (colima, jalisco, nacional, etc.)
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            magnitud_min: Magnitud mínima
            **kwargs: Parámetros adicionales
            
        Returns:
            DownloadResult con los datos
        """
        if region.lower() not in REGIONES_MEXICO:
            available = ", ".join(REGIONES_MEXICO.keys())
            raise ValueError(
                f"Región '{region}' no reconocida. "
                f"Regiones disponibles: {available}"
            )
        
        bounds = REGIONES_MEXICO[region.lower()]
        
        return self.descargar(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            lat_min=bounds['lat_min'],
            lat_max=bounds['lat_max'],
            lon_min=bounds['lon_min'],
            lon_max=bounds['lon_max'],
            magnitud_min=magnitud_min,
            **kwargs
        )
    
    def regiones_disponibles(self) -> List[str]:
        """Retorna lista de regiones predefinidas disponibles."""
        return list(REGIONES_MEXICO.keys())
    
    def actualizar(
        self,
        catalogo_existente: pd.DataFrame,
        **kwargs
    ) -> DownloadResult:
        """
        Descarga solo eventos nuevos desde la última fecha del catálogo.
        
        Args:
            catalogo_existente: DataFrame con catálogo existente
            **kwargs: Parámetros adicionales para descargar()
            
        Returns:
            DownloadResult solo con eventos nuevos
        """
        if catalogo_existente.empty:
            logger.warning("Catálogo vacío, descargando todo")
            return self.descargar(**kwargs)
        
        # Encontrar fecha más reciente
        if 'fecha' in catalogo_existente.columns:
            ultima_fecha = pd.to_datetime(catalogo_existente['fecha']).max()
        else:
            raise ValueError("El catálogo no tiene columna 'fecha'")
        
        logger.info(f"Actualizando desde {ultima_fecha}")
        
        # Descargar eventos nuevos
        result = self.descargar(fecha_inicio=ultima_fecha, **kwargs)
        
        if result.success and result.data is not None:
            # Filtrar duplicados basados en fecha y ubicación
            nuevos = self._filtrar_duplicados(
                result.data, 
                catalogo_existente
            )
            result.data = nuevos
            result.events_count = len(nuevos)
            logger.info(f"Eventos nuevos encontrados: {result.events_count}")
        
        return result
    
    def _filtrar_duplicados(
        self,
        nuevos: pd.DataFrame,
        existentes: pd.DataFrame,
        tolerancia_tiempo_seg: int = 60,
        tolerancia_distancia_km: float = 50
    ) -> pd.DataFrame:
        """
        Filtra eventos duplicados entre dos catálogos.
        
        Args:
            nuevos: DataFrame con eventos nuevos
            existentes: DataFrame con eventos existentes
            tolerancia_tiempo_seg: Tolerancia temporal en segundos
            tolerancia_distancia_km: Tolerancia espacial en km
            
        Returns:
            DataFrame con eventos únicos
        """
        if nuevos.empty or existentes.empty:
            return nuevos
        
        # Convertir fechas
        nuevos_fechas = pd.to_datetime(nuevos['fecha'])
        exist_fechas = pd.to_datetime(existentes['fecha'])
        
        # Marcar duplicados
        es_duplicado = []
        
        for idx, row in nuevos.iterrows():
            fecha_nuevo = pd.to_datetime(row['fecha'])
            lat_nuevo = row['latitud']
            lon_nuevo = row['longitud']
            
            # Buscar coincidencias temporales
            diff_tiempo = abs((exist_fechas - fecha_nuevo).dt.total_seconds())
            candidatos = existentes[diff_tiempo <= tolerancia_tiempo_seg]
            
            if len(candidatos) == 0:
                es_duplicado.append(False)
                continue
            
            # Verificar distancia para candidatos
            duplicado = False
            for _, cand in candidatos.iterrows():
                dist = self._calcular_distancia_aprox(
                    lat_nuevo, lon_nuevo,
                    cand['latitud'], cand['longitud']
                )
                if dist <= tolerancia_distancia_km:
                    duplicado = True
                    break
            
            es_duplicado.append(duplicado)
        
        # Retornar solo no duplicados
        return nuevos[~pd.Series(es_duplicado, index=nuevos.index)]
    
    def _calcular_distancia_aprox(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calcula distancia aproximada en km usando fórmula simplificada.
        
        Args:
            lat1, lon1: Coordenadas del punto 1
            lat2, lon2: Coordenadas del punto 2
            
        Returns:
            Distancia aproximada en km
        """
        # Aproximación para distancias cortas
        lat_rad = np.radians((lat1 + lat2) / 2)
        dx = (lon2 - lon1) * np.cos(lat_rad) * 111.32
        dy = (lat2 - lat1) * 111.32
        return np.sqrt(dx**2 + dy**2)
    
    def _parse_fecha(
        self, 
        fecha: Optional[Union[str, datetime, date]]
    ) -> Optional[datetime]:
        """
        Convierte fecha a datetime.
        
        Args:
            fecha: Fecha en varios formatos posibles
            
        Returns:
            datetime o None
        """
        if fecha is None:
            return None
        
        if isinstance(fecha, datetime):
            return fecha
        
        if isinstance(fecha, date):
            return datetime.combine(fecha, datetime.min.time())
        
        if isinstance(fecha, str):
            # Intentar varios formatos
            formatos = [
                '%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y/%m/%d',
                '%d/%m/%Y',
                '%d-%m-%Y',
            ]
            for fmt in formatos:
                try:
                    return datetime.strptime(fecha, fmt)
                except ValueError:
                    continue
            
            # Último intento con pandas
            try:
                return pd.to_datetime(fecha).to_pydatetime()
            except:
                raise ValueError(f"Formato de fecha no reconocido: {fecha}")
        
        raise TypeError(f"Tipo de fecha no soportado: {type(fecha)}")
    
    def _generar_cache_key(self, params: QueryParams) -> str:
        """
        Genera clave de caché única para los parámetros.
        
        Args:
            params: Parámetros de consulta
            
        Returns:
            Clave de caché
        """
        from seismex.data.cache import get_cache
        cache = get_cache()
        return cache._generate_key(self.NOMBRE, params.to_dict())
    
    def _validar_dataframe(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Valida que el DataFrame tenga las columnas requeridas.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Tupla (es_válido, lista_errores)
        """
        errores = []
        
        columnas_requeridas = ['fecha', 'latitud', 'longitud', 'magnitud']
        
        for col in columnas_requeridas:
            if col not in df.columns:
                errores.append(f"Columna requerida faltante: {col}")
        
        if not errores:
            # Validar tipos de datos
            if not pd.api.types.is_numeric_dtype(df['latitud']):
                errores.append("Columna 'latitud' debe ser numérica")
            if not pd.api.types.is_numeric_dtype(df['longitud']):
                errores.append("Columna 'longitud' debe ser numérica")
            if not pd.api.types.is_numeric_dtype(df['magnitud']):
                errores.append("Columna 'magnitud' debe ser numérica")
        
        return (len(errores) == 0, errores)
    
    def _añadir_columnas_faltantes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade columnas opcionales con valores por defecto.
        
        Args:
            df: DataFrame a completar
            
        Returns:
            DataFrame con todas las columnas estándar
        """
        defaults = {
            'tipo_magnitud': 'M',
            'fuente': self.NOMBRE.upper(),
            'id_evento': None,
            'lugar': None,
            'incertidumbre_h': np.nan,
            'incertidumbre_z': np.nan,
            'incertidumbre_m': np.nan,
            'rms': np.nan,
            'gap': np.nan,
            'nst': np.nan,
        }
        
        for col, default in defaults.items():
            if col not in df.columns:
                df[col] = default
        
        # Generar IDs si faltan
        if df['id_evento'].isna().all():
            df['id_evento'] = [
                f"{self.NOMBRE}_{i:08d}" 
                for i in range(len(df))
            ]
        
        return df
    
    def ultima_actualizacion(self) -> Optional[datetime]:
        """
        Retorna la fecha de la última entrada en caché.
        
        Returns:
            datetime de última actualización o None
        """
        if not self._cache:
            return None
        
        entries = self._cache.find(source=self.NOMBRE)
        if not entries:
            return None
        
        return max(e.created_at for e in entries)
    
    def limpiar_cache(self) -> int:
        """
        Limpia el caché de este conector.
        
        Returns:
            Número de entradas eliminadas
        """
        if not self._cache:
            return 0
        return self._cache.clean_source(self.NOMBRE)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(cache={self.usar_cache})"
