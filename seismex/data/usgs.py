"""
SEISMEX Data - Conector USGS (United States Geological Survey)
===============================================================

Conector para la API pública del USGS Earthquake Catalog (ComCat).

Sobre el uso de email:
- La API USGS es **pública y gratuita**, no requiere API key
- Proporcionar email es **opcional pero recomendado**
- Con email: rate limits más generosos (~20 requests/segundo)
- Sin email: rate limits más estrictos (~5 requests/segundo)
- El email se envía en el header User-Agent, no se almacena

Configuración en ~/.seismex/config.yaml:

    usgs:
      enabled: true
      email: "tu@email.com"  # Opcional pero recomendado
      base_url: https://earthquake.usgs.gov/fdsnws/event/1/
      format: geojson
      max_events_per_query: 20000

Uso:
    >>> from seismex.data import ConectorUSGS
    >>> usgs = ConectorUSGS()
    >>> 
    >>> # Descargar sismos en México
    >>> resultado = usgs.descargar(
    ...     fecha_inicio='2024-01-01',
    ...     region='nacional',
    ...     magnitud_min=4.0
    ... )
    >>> 
    >>> # Descargar región específica
    >>> resultado = usgs.descargar_region('colima', magnitud_min=3.5)
"""

import logging
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from io import StringIO

import pandas as pd
import numpy as np

from seismex.data.base import (
    ConectorBase, QueryParams, DownloadResult, 
    CATALOG_COLUMNS, REGIONES_MEXICO
)

logger = logging.getLogger(__name__)


class ConectorUSGS(ConectorBase):
    """
    Conector para USGS Earthquake Catalog (ComCat API).
    
    La API del USGS es una de las más completas y confiables para datos
    sísmicos globales. Características:
    
    - **API pública**: No requiere autenticación
    - **Rate limits**: Más generosos con email configurado
    - **Formatos**: GeoJSON (recomendado), CSV, QuakeML
    - **Cobertura**: Global, excelente para México
    - **Datos**: Incluye incertidumbres, fases, tensores de momento
    
    Sobre el email (USGS solicita pero no requiere):
    
        "We request that you provide an email address so we can contact
        you in case of changes to the API or if there are issues with
        your requests."
    
    Beneficios de proporcionar email:
    - Rate limits más generosos
    - USGS puede contactar si hay problemas
    - Buena práctica para usuarios frecuentes
    
    Sin email funciona perfectamente para uso moderado.
    
    Ejemplos:
    
        # Configurar email para mejor rendimiento
        >>> from seismex.data import configure
        >>> configure(usgs_email='mi@email.com')
        
        # Descargar datos
        >>> usgs = ConectorUSGS()
        >>> result = usgs.descargar(
        ...     fecha_inicio='2024-01-01',
        ...     lat_min=14, lat_max=33,
        ...     lon_min=-118, lon_max=-86,
        ...     magnitud_min=4.0
        ... )
        
        # Usar región predefinida
        >>> result = usgs.descargar_region('colima', magnitud_min=3.5)
    """
    
    NOMBRE = "usgs"
    
    # Mapeo de columnas USGS GeoJSON a formato SEISMEX
    GEOJSON_MAPPING = {
        'time': 'fecha',
        'latitude': 'latitud',
        'longitude': 'longitud',
        'depth': 'profundidad_km',
        'mag': 'magnitud',
        'magType': 'tipo_magnitud',
        'place': 'lugar',
        'id': 'id_evento',
        'horizontalError': 'incertidumbre_h',
        'depthError': 'incertidumbre_z',
        'magError': 'incertidumbre_m',
        'rms': 'rms',
        'gap': 'gap',
        'nst': 'nst',
        'net': 'red',
        'type': 'tipo_evento',
        'status': 'estado',
        'updated': 'actualizado',
        'felt': 'sentido',
        'cdi': 'cdi',
        'mmi': 'mmi',
        'alert': 'alerta',
        'tsunami': 'tsunami',
        'sig': 'significancia',
    }
    
    # Mapeo para formato CSV
    CSV_MAPPING = {
        'time': 'fecha',
        'latitude': 'latitud',
        'longitude': 'longitud',
        'depth': 'profundidad_km',
        'mag': 'magnitud',
        'magType': 'tipo_magnitud',
        'place': 'lugar',
        'id': 'id_evento',
        'horizontalError': 'incertidumbre_h',
        'depthError': 'incertidumbre_z',
        'magError': 'incertidumbre_m',
        'rms': 'rms',
        'gap': 'gap',
        'nst': 'nst',
    }
    
    def __init__(
        self,
        email: Optional[str] = None,
        usar_cache: bool = True,
        formato: str = 'geojson',
        timeout: int = 60,
        max_reintentos: int = 3
    ):
        """
        Inicializa el conector USGS.
        
        Args:
            email: Email para identificación (recomendado, no obligatorio)
            usar_cache: Habilitar caché de datos
            formato: Formato de respuesta ('geojson', 'csv', 'quakeml')
            timeout: Timeout para requests HTTP
            max_reintentos: Número máximo de reintentos
        """
        super().__init__(
            usar_cache=usar_cache,
            timeout=timeout,
            max_reintentos=max_reintentos
        )
        
        # Configuración USGS
        self.base_url = self.config.usgs.base_url.rstrip('/')
        self.formato = formato or self.config.usgs.format
        self.max_events = self.config.usgs.max_events_per_query
        
        # Email: usar parámetro, config, o None
        self.email = email or self.config.usgs.email or None
        
        if self.email:
            logger.info(f"USGS: Email configurado para mejor rate limit")
        else:
            logger.info(
                "USGS: Sin email configurado. Para mejor rendimiento, "
                "configure 'usgs.email' en ~/.seismex/config.yaml"
            )
    
    # =========================================================================
    # MÉTODO PRINCIPAL DE DESCARGA
    # =========================================================================
    
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
        profundidad_min: Optional[float] = None,
        profundidad_max: Optional[float] = None,
        region: Optional[str] = None,
        limite: Optional[int] = None,
        incluir_todos_magnitudes: bool = False,
        ordenar_por: str = 'time-asc',
        **kwargs
    ) -> DownloadResult:
        """
        Descarga datos del catálogo USGS.
        
        Args:
            fecha_inicio: Fecha inicial (YYYY-MM-DD o datetime)
            fecha_fin: Fecha final (default: ahora)
            lat_min, lat_max: Rango de latitudes
            lon_min, lon_max: Rango de longitudes
            magnitud_min, magnitud_max: Rango de magnitudes
            profundidad_min, profundidad_max: Rango de profundidades (km)
            region: Región predefinida de México
            limite: Límite de eventos (default: 20000)
            incluir_todos_magnitudes: Incluir eventos sin magnitud
            ordenar_por: Orden de resultados ('time', 'time-asc', 'magnitude')
            
        Returns:
            DownloadResult con datos y metadatos
        """
        inicio_tiempo = time.time()
        
        # Construir parámetros de consulta
        params = QueryParams(
            fecha_inicio=self._parse_fecha(fecha_inicio),
            fecha_fin=self._parse_fecha(fecha_fin) or datetime.now(),
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
            magnitud_min=magnitud_min,
            magnitud_max=magnitud_max,
            profundidad_min=profundidad_min,
            profundidad_max=profundidad_max,
            region=region,
            limite=limite or self.max_events
        )
        
        # Aplicar límites de región si se especificó
        if region:
            params = params.apply_region()
        
        # Validar parámetros
        errores = params.validate()
        if errores:
            return DownloadResult(
                success=False,
                data=None,
                source=self.NOMBRE,
                query_params=params,
                events_count=0,
                download_time=time.time() - inicio_tiempo,
                from_cache=False,
                errors=errores
            )
        
        # Verificar caché
        if self.usar_cache:
            cache_key = self._generar_cache_key(params)
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                logger.info(f"Datos obtenidos desde caché: {len(cached_data)} eventos")
                return DownloadResult(
                    success=True,
                    data=cached_data,
                    source=self.NOMBRE,
                    query_params=params,
                    events_count=len(cached_data),
                    download_time=time.time() - inicio_tiempo,
                    from_cache=True
                )
        
        # Descargar datos
        try:
            df = self._fetch_data(params)
            df = self._normalizar_datos(df)
            
            # Guardar en caché
            if self.usar_cache and len(df) > 0:
                cache_key = self._generar_cache_key(params)
                self._cache.set(
                    cache_key, df,
                    source=self.NOMBRE,
                    query_params=params.to_dict()
                )
            
            return DownloadResult(
                success=True,
                data=df,
                source=self.NOMBRE,
                query_params=params,
                events_count=len(df),
                download_time=time.time() - inicio_tiempo,
                from_cache=False
            )
            
        except Exception as e:
            logger.error(f"Error al descargar de USGS: {e}")
            return DownloadResult(
                success=False,
                data=None,
                source=self.NOMBRE,
                query_params=params,
                events_count=0,
                download_time=time.time() - inicio_tiempo,
                from_cache=False,
                errors=[str(e)]
            )
    
    # =========================================================================
    # FETCH DATA
    # =========================================================================
    
    def _fetch_data(self, params: QueryParams) -> pd.DataFrame:
        """
        Realiza la consulta a la API USGS.
        
        Args:
            params: Parámetros de consulta
            
        Returns:
            DataFrame con datos crudos
        """
        try:
            import requests
        except ImportError:
            raise ImportError("Instale 'requests': pip install requests")
        
        # Construir URL
        url = self._construir_url(params)
        
        # Headers con email si está configurado
        headers = self._construir_headers()
        
        logger.info(f"Consultando USGS API...")
        logger.debug(f"URL: {url}")
        
        # Realizar request con reintentos
        response = None
        last_error = None
        
        for intento in range(self.max_reintentos):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                break
                
            except requests.exceptions.HTTPError as e:
                if response and response.status_code == 400:
                    # Error de parámetros - no reintentar
                    raise ValueError(f"Parámetros inválidos: {response.text}")
                elif response and response.status_code == 503:
                    # Servicio no disponible - esperar y reintentar
                    logger.warning(f"USGS no disponible, reintentando...")
                    time.sleep(self.delay_reintentos * (intento + 1))
                    last_error = e
                else:
                    raise
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en intento {intento + 1}")
                last_error = "Timeout"
                time.sleep(self.delay_reintentos)
                
            except requests.exceptions.RequestException as e:
                last_error = e
                time.sleep(self.delay_reintentos)
        
        if response is None:
            raise RuntimeError(f"Error después de {self.max_reintentos} intentos: {last_error}")
        
        # Parsear respuesta según formato
        if self.formato == 'geojson':
            return self._parsear_geojson(response.json())
        elif self.formato == 'csv':
            return pd.read_csv(StringIO(response.text))
        else:
            raise ValueError(f"Formato no soportado: {self.formato}")
    
    def _construir_url(self, params: QueryParams) -> str:
        """Construye la URL de la API USGS."""
        endpoint = f"{self.base_url}/query"
        
        query_params = [f"format={self.formato}"]
        
        # Fechas (requeridas por USGS)
        if params.fecha_inicio:
            query_params.append(f"starttime={params.fecha_inicio.isoformat()}")
        if params.fecha_fin:
            query_params.append(f"endtime={params.fecha_fin.isoformat()}")
        
        # Límites geográficos
        if params.lat_min is not None:
            query_params.append(f"minlatitude={params.lat_min}")
        if params.lat_max is not None:
            query_params.append(f"maxlatitude={params.lat_max}")
        if params.lon_min is not None:
            query_params.append(f"minlongitude={params.lon_min}")
        if params.lon_max is not None:
            query_params.append(f"maxlongitude={params.lon_max}")
        
        # Magnitud
        if params.magnitud_min is not None:
            query_params.append(f"minmagnitude={params.magnitud_min}")
        if params.magnitud_max is not None:
            query_params.append(f"maxmagnitude={params.magnitud_max}")
        
        # Profundidad
        if params.profundidad_min is not None:
            query_params.append(f"mindepth={params.profundidad_min}")
        if params.profundidad_max is not None:
            query_params.append(f"maxdepth={params.profundidad_max}")
        
        # Límite de resultados
        if params.limite:
            query_params.append(f"limit={min(params.limite, 20000)}")
        
        # Ordenar por tiempo ascendente por defecto
        query_params.append("orderby=time-asc")
        
        return f"{endpoint}?{'&'.join(query_params)}"
    
    def _construir_headers(self) -> Dict[str, str]:
        """Construye headers para la request, incluyendo email si está configurado."""
        headers = {
            'Accept': 'application/json' if self.formato == 'geojson' else 'text/csv',
        }
        
        # USGS recomienda incluir email en User-Agent
        if self.email:
            headers['User-Agent'] = f"SEISMEX/1.0 ({self.email})"
        else:
            headers['User-Agent'] = "SEISMEX/1.0 (https://github.com/seismex)"
        
        return headers
    
    def _parsear_geojson(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Parsea respuesta GeoJSON de USGS.
        
        Args:
            data: Diccionario GeoJSON
            
        Returns:
            DataFrame con datos
        """
        features = data.get('features', [])
        
        if not features:
            logger.warning("Respuesta USGS vacía")
            return pd.DataFrame()
        
        records = []
        
        for feature in features:
            props = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coords = geometry.get('coordinates', [None, None, None])
            
            record = {
                'id': feature.get('id'),
                'longitude': coords[0] if len(coords) > 0 else None,
                'latitude': coords[1] if len(coords) > 1 else None,
                'depth': coords[2] if len(coords) > 2 else None,
            }
            
            # Añadir propiedades
            for key, value in props.items():
                record[key] = value
            
            records.append(record)
        
        df = pd.DataFrame(records)
        
        logger.info(f"USGS: {len(df)} eventos obtenidos")
        return df
    
    # =========================================================================
    # NORMALIZACIÓN
    # =========================================================================
    
    def _normalizar_datos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza datos USGS al formato estándar SEISMEX.
        
        Args:
            df: DataFrame con datos crudos
            
        Returns:
            DataFrame normalizado
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Seleccionar mapeo según formato
        mapping = self.GEOJSON_MAPPING if self.formato == 'geojson' else self.CSV_MAPPING
        
        # Renombrar columnas
        column_renames = {}
        for col in df.columns:
            if col in mapping:
                column_renames[col] = mapping[col]
        
        df = df.rename(columns=column_renames)
        
        # Convertir timestamp a datetime
        if 'fecha' in df.columns:
            # USGS usa milliseconds desde epoch
            if df['fecha'].dtype in ['int64', 'float64']:
                df['fecha'] = pd.to_datetime(df['fecha'], unit='ms', utc=True)
            else:
                df['fecha'] = pd.to_datetime(df['fecha'], utc=True)
            
            # Convertir a timezone naive para consistencia
            df['fecha'] = df['fecha'].dt.tz_localize(None)
        
        # Asegurar tipos numéricos
        for col in ['latitud', 'longitud', 'magnitud', 'profundidad_km']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Añadir fuente
        df['fuente'] = 'USGS'
        
        # Prefijo para IDs
        if 'id_evento' in df.columns:
            df['id_evento'] = 'usgs_' + df['id_evento'].astype(str)
        
        # Añadir columnas faltantes
        df = self._añadir_columnas_faltantes(df)
        
        # Ordenar por fecha
        if 'fecha' in df.columns:
            df = df.sort_values('fecha').reset_index(drop=True)
        
        return df
    
    # =========================================================================
    # MÉTODOS DE CONVENIENCIA
    # =========================================================================
    
    def descargar_mexico(
        self,
        fecha_inicio: Optional[Union[str, datetime]] = None,
        fecha_fin: Optional[Union[str, datetime]] = None,
        magnitud_min: float = 3.0,
        **kwargs
    ) -> DownloadResult:
        """
        Descarga sismos en México (región nacional completa).
        
        Args:
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            magnitud_min: Magnitud mínima (default 3.0)
            **kwargs: Parámetros adicionales
            
        Returns:
            DownloadResult
        """
        return self.descargar(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            region='nacional',
            magnitud_min=magnitud_min,
            **kwargs
        )
    
    def descargar_recientes(
        self,
        dias: int = 30,
        magnitud_min: float = 4.0,
        region: str = 'nacional'
    ) -> DownloadResult:
        """
        Descarga sismos recientes.
        
        Args:
            dias: Número de días hacia atrás
            magnitud_min: Magnitud mínima
            region: Región de México
            
        Returns:
            DownloadResult
        """
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=dias)
        
        return self.descargar(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            region=region,
            magnitud_min=magnitud_min
        )
    
    def obtener_evento(self, event_id: str) -> Optional[pd.Series]:
        """
        Obtiene información detallada de un evento específico.
        
        Args:
            event_id: ID del evento USGS (ej: 'us7000abcd')
            
        Returns:
            Series con datos del evento o None
        """
        try:
            import requests
        except ImportError:
            raise ImportError("Instale 'requests': pip install requests")
        
        url = f"{self.base_url}/query?eventid={event_id}&format=geojson"
        headers = self._construir_headers()
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            df = self._parsear_geojson(data)
            df = self._normalizar_datos(df)
            
            if len(df) > 0:
                return df.iloc[0]
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener evento {event_id}: {e}")
            return None
    
    def verificar_conexion(self) -> bool:
        """
        Verifica conectividad con la API USGS.
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            import requests
            
            url = f"{self.base_url}/count?starttime=2024-01-01&endtime=2024-01-02"
            headers = self._construir_headers()
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.info("Conexión USGS verificada correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error de conexión USGS: {e}")
            return False
    
    def info_rate_limit(self) -> str:
        """
        Muestra información sobre rate limits y configuración.
        
        Returns:
            String con información
        """
        lines = [
            "=" * 60,
            "USGS API - Información de Rate Limits",
            "=" * 60,
            "",
            f"Email configurado: {'✓ ' + self.email if self.email else '✗ No configurado'}",
            "",
        ]
        
        if self.email:
            lines.extend([
                "Estado: Rate limits extendidos activos",
                "  • Hasta 20 requests/segundo",
                "  • Consultas más grandes permitidas",
                "  • USGS puede contactarlo si hay problemas",
            ])
        else:
            lines.extend([
                "Estado: Rate limits estándar",
                "  • Aproximadamente 5 requests/segundo",
                "  • Funciona bien para uso moderado",
                "",
                "💡 Para mejor rendimiento, configure su email:",
                "   En ~/.seismex/config.yaml:",
                "     usgs:",
                "       email: 'su@email.com'",
                "",
                "   O con variable de entorno:",
                "     export SEISMEX_USGS_EMAIL='su@email.com'",
            ])
        
        lines.append("=" * 60)
        return "\n".join(lines)


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def descargar_usgs(**kwargs) -> DownloadResult:
    """
    Función de conveniencia para descargar datos USGS.
    
    Args:
        **kwargs: Parámetros para ConectorUSGS.descargar()
        
    Returns:
        DownloadResult
    """
    conector = ConectorUSGS()
    return conector.descargar(**kwargs)


def descargar_usgs_mexico(
    fecha_inicio: Optional[str] = None,
    magnitud_min: float = 3.0
) -> DownloadResult:
    """
    Descarga sismos de USGS para México.
    
    Args:
        fecha_inicio: Fecha inicial
        magnitud_min: Magnitud mínima
        
    Returns:
        DownloadResult
    """
    conector = ConectorUSGS()
    return conector.descargar_mexico(
        fecha_inicio=fecha_inicio,
        magnitud_min=magnitud_min
    )
