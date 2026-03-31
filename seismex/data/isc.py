"""
SEISMEX Data - Conector ISC (International Seismological Centre)
================================================================

Conector para el catálogo ISC-GEM y bases de datos del ISC.

El ISC proporciona:
- ISC-GEM: Catálogo revisado de sismos históricos significativos (M >= 5.5)
- ISC Bulletin: Catálogo completo revisado
- ISC-EHB: Catálogo con localizaciones de alta precisión

No requiere autenticación.

Configuración en ~/.seismex/config.yaml:

    isc:
      enabled: true
      base_url: http://www.isc.ac.uk/cgi-bin/web-db-run
      format: isf
      catalog: isc-gem

Uso:
    >>> from seismex.data import ConectorISC
    >>> isc = ConectorISC()
    >>> 
    >>> # Descargar catálogo ISC-GEM para México
    >>> resultado = isc.descargar(
    ...     fecha_inicio='1900-01-01',
    ...     region='nacional',
    ...     magnitud_min=6.0
    ... )
"""

import logging
import time
import re
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


class ConectorISC(ConectorBase):
    """
    Conector para International Seismological Centre.
    
    El ISC mantiene varios catálogos importantes:
    
    - **ISC-GEM**: Catálogo de referencia global de sismos instrumentales
      significativos desde 1904. Contiene sismos M >= 5.5 con localizaciones
      y magnitudes revisadas manualmente. Ideal para estudios de sismicidad
      histórica.
    
    - **ISC Bulletin**: Catálogo completo con todos los sismos reportados.
      Mayor cobertura pero menor control de calidad que ISC-GEM.
    
    - **ISC-EHB**: Catálogo con localizaciones de alta precisión usando
      el algoritmo EHB.
    
    Características:
    - No requiere autenticación
    - Formatos: ISF (nativo), CSV, QuakeML
    - Excelente para estudios históricos
    - Datos completamente revisados
    
    Ejemplos:
    
        # Sismos históricos significativos en México
        >>> isc = ConectorISC(catalogo='isc-gem')
        >>> result = isc.descargar(
        ...     fecha_inicio='1900-01-01',
        ...     region='nacional',
        ...     magnitud_min=6.0
        ... )
        
        # Catálogo completo de una región
        >>> isc = ConectorISC(catalogo='reviewed')
        >>> result = isc.descargar_region('colima', magnitud_min=4.0)
    """
    
    NOMBRE = "isc"
    
    # URLs para diferentes servicios ISC
    URLS = {
        'bulletin': 'http://www.isc.ac.uk/cgi-bin/web-db-run',
        'isc-gem': 'http://www.isc.ac.uk/cgi-bin/web-db-run',
        'gem-cat': 'https://www.globalquakemodel.org/gem',
    }
    
    # Catálogos disponibles
    CATALOGOS = {
        'isc-gem': 'ISC-GEM Global Instrumental Earthquake Catalogue',
        'reviewed': 'ISC Bulletin (Reviewed)',
        'comprehensive': 'ISC Comprehensive Bulletin',
        'ehb': 'ISC-EHB Bulletin',
    }
    
    # Mapeo de columnas ISF a formato SEISMEX
    ISF_MAPPING = {
        'Date': 'fecha',
        'Time': 'hora',
        'Lat': 'latitud',
        'Lon': 'longitud',
        'Depth': 'profundidad_km',
        'Mag': 'magnitud',
        'MagType': 'tipo_magnitud',
        'MagAuth': 'autor_magnitud',
        'EventID': 'id_evento',
        'Author': 'autor',
        'Region': 'lugar',
        'Err': 'error',
        'Smaj': 'error_semieje_mayor',
        'Smin': 'error_semieje_menor',
        'Az': 'azimut_error',
        'DepthErr': 'incertidumbre_z',
        'nPhases': 'nst',
        'Gap': 'gap',
        'RMS': 'rms',
    }
    
    def __init__(
        self,
        catalogo: str = 'isc-gem',
        formato: str = 'isf',
        usar_cache: bool = True,
        timeout: int = 120,
        max_reintentos: int = 3
    ):
        """
        Inicializa el conector ISC.
        
        Args:
            catalogo: Catálogo a usar ('isc-gem', 'reviewed', 'comprehensive')
            formato: Formato de salida ('isf', 'csv')
            usar_cache: Habilitar caché
            timeout: Timeout para requests (ISC puede ser lento)
            max_reintentos: Número de reintentos
        """
        super().__init__(
            usar_cache=usar_cache,
            timeout=timeout,
            max_reintentos=max_reintentos
        )
        
        self.catalogo = catalogo.lower()
        self.formato = formato
        
        if self.catalogo not in self.CATALOGOS:
            available = ', '.join(self.CATALOGOS.keys())
            raise ValueError(
                f"Catálogo '{catalogo}' no reconocido. "
                f"Disponibles: {available}"
            )
        
        self.base_url = self.config.isc.base_url
        
        logger.debug(f"ConectorISC inicializado: catalogo={self.catalogo}")
    
    # =========================================================================
    # MÉTODO PRINCIPAL
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
        **kwargs
    ) -> DownloadResult:
        """
        Descarga datos del catálogo ISC.
        
        Args:
            fecha_inicio: Fecha inicial (YYYY-MM-DD)
            fecha_fin: Fecha final
            lat_min, lat_max: Rango de latitudes
            lon_min, lon_max: Rango de longitudes
            magnitud_min, magnitud_max: Rango de magnitudes
            profundidad_min, profundidad_max: Rango de profundidades
            region: Región predefinida de México
            
        Returns:
            DownloadResult con datos
        """
        inicio_tiempo = time.time()
        
        # Construir parámetros
        params = QueryParams(
            fecha_inicio=self._parse_fecha(fecha_inicio) or datetime(1900, 1, 1),
            fecha_fin=self._parse_fecha(fecha_fin) or datetime.now(),
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
            magnitud_min=magnitud_min,
            magnitud_max=magnitud_max,
            profundidad_min=profundidad_min,
            profundidad_max=profundidad_max,
            region=region
        )
        
        if region:
            params = params.apply_region()
        
        # Validar
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
                logger.info(f"Datos desde caché: {len(cached_data)} eventos")
                return DownloadResult(
                    success=True,
                    data=cached_data,
                    source=self.NOMBRE,
                    query_params=params,
                    events_count=len(cached_data),
                    download_time=time.time() - inicio_tiempo,
                    from_cache=True
                )
        
        # Descargar
        try:
            df = self._fetch_data(params)
            df = self._normalizar_datos(df)
            
            # Cachear
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
                from_cache=False,
                metadata={'catalogo': self.catalogo}
            )
            
        except Exception as e:
            logger.error(f"Error al descargar de ISC: {e}")
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
        """Realiza la consulta al ISC."""
        try:
            import requests
        except ImportError:
            raise ImportError("Instale 'requests': pip install requests")
        
        # Construir URL
        url = self._construir_url(params)
        
        headers = {
            'User-Agent': 'SEISMEX/1.0 (https://github.com/seismex)',
            'Accept': 'text/plain',
        }
        
        logger.info(f"Consultando ISC ({self.catalogo})...")
        logger.debug(f"URL: {url}")
        
        for intento in range(self.max_reintentos):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Parsear respuesta
                df = self._parsear_respuesta(response.text)
                
                logger.info(f"ISC: {len(df)} eventos obtenidos")
                return df
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout (intento {intento + 1})")
                time.sleep(self.delay_reintentos)
                
            except Exception as e:
                logger.warning(f"Error en intento {intento + 1}: {e}")
                time.sleep(self.delay_reintentos)
        
        raise RuntimeError(f"Error después de {self.max_reintentos} intentos")
    
    def _construir_url(self, params: QueryParams) -> str:
        """Construye la URL de consulta ISC."""
        base = self.base_url
        
        # Parámetros comunes
        query_parts = [
            'request=STNARRIVALS' if self.catalogo != 'isc-gem' else 'request=COMPREHENSIVE',
            f"out_format={'ISF' if self.formato == 'isf' else 'CSV'}",
            'ttime=on',
            'ttres=on',
            'iscreview=on' if self.catalogo == 'reviewed' else '',
        ]
        
        # Fechas
        if params.fecha_inicio:
            query_parts.append(f"start_year={params.fecha_inicio.year}")
            query_parts.append(f"start_month={params.fecha_inicio.month}")
            query_parts.append(f"start_day={params.fecha_inicio.day}")
        
        if params.fecha_fin:
            query_parts.append(f"end_year={params.fecha_fin.year}")
            query_parts.append(f"end_month={params.fecha_fin.month}")
            query_parts.append(f"end_day={params.fecha_fin.day}")
        
        # Región
        if params.lat_min is not None:
            query_parts.append(f"bot_lat={params.lat_min}")
        if params.lat_max is not None:
            query_parts.append(f"top_lat={params.lat_max}")
        if params.lon_min is not None:
            query_parts.append(f"left_lon={params.lon_min}")
        if params.lon_max is not None:
            query_parts.append(f"right_lon={params.lon_max}")
        
        # Magnitud
        if params.magnitud_min is not None:
            query_parts.append(f"min_mag={params.magnitud_min}")
        if params.magnitud_max is not None:
            query_parts.append(f"max_mag={params.magnitud_max}")
        
        # Profundidad
        if params.profundidad_min is not None:
            query_parts.append(f"min_dep={params.profundidad_min}")
        if params.profundidad_max is not None:
            query_parts.append(f"max_dep={params.profundidad_max}")
        
        # Filtrar partes vacías
        query_parts = [p for p in query_parts if p]
        
        return f"{base}?{'&'.join(query_parts)}"
    
    def _parsear_respuesta(self, texto: str) -> pd.DataFrame:
        """
        Parsea la respuesta del ISC.
        
        El formato ISF es texto estructurado con secciones.
        """
        if self.formato == 'csv':
            return pd.read_csv(StringIO(texto))
        
        # Parsear formato ISF
        return self._parsear_isf(texto)
    
    def _parsear_isf(self, texto: str) -> pd.DataFrame:
        """
        Parsea formato ISF (IASPEI Seismic Format).
        
        El ISF tiene secciones:
        - DATA_TYPE: Tipo de datos
        - Event: Información del evento
        - Origin: Origen del sismo
        - Magnitude: Magnitudes
        """
        eventos = []
        evento_actual = {}
        
        lines = texto.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            # Detectar línea de evento (contiene fecha y coordenadas)
            # Formato típico: "2024/01/15 10:30:45.2  19.123  -104.456  15.0  4.5  ..."
            if re.match(r'\d{4}/\d{2}/\d{2}', line):
                try:
                    partes = line.split()
                    if len(partes) >= 5:
                        evento = {
                            'fecha_str': partes[0],
                            'hora_str': partes[1] if len(partes) > 1 else '00:00:00',
                            'latitud': float(partes[2]) if len(partes) > 2 else None,
                            'longitud': float(partes[3]) if len(partes) > 3 else None,
                            'profundidad_km': float(partes[4]) if len(partes) > 4 else None,
                            'magnitud': float(partes[5]) if len(partes) > 5 else None,
                        }
                        eventos.append(evento)
                except (ValueError, IndexError):
                    continue
        
        if not eventos:
            # Intentar parsear como tabla simple
            try:
                # Buscar líneas con datos numéricos
                data_lines = []
                for line in lines:
                    if re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', line):
                        data_lines.append(line)
                
                if data_lines:
                    # Intentar parsear como CSV
                    df = pd.read_csv(
                        StringIO('\n'.join(data_lines)),
                        delim_whitespace=True,
                        header=None,
                        error_bad_lines=False
                    )
                    return df
            except:
                pass
        
        return pd.DataFrame(eventos)
    
    # =========================================================================
    # NORMALIZACIÓN
    # =========================================================================
    
    def _normalizar_datos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza datos ISC al formato SEISMEX."""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Renombrar columnas
        column_renames = {}
        for col in df.columns:
            col_str = str(col)
            if col_str in self.ISF_MAPPING:
                column_renames[col] = self.ISF_MAPPING[col_str]
        
        df = df.rename(columns=column_renames)
        
        # Combinar fecha y hora si están separadas
        if 'fecha_str' in df.columns:
            try:
                if 'hora_str' in df.columns:
                    df['fecha'] = pd.to_datetime(
                        df['fecha_str'] + ' ' + df['hora_str'],
                        format='%Y/%m/%d %H:%M:%S.%f',
                        errors='coerce'
                    )
                else:
                    df['fecha'] = pd.to_datetime(df['fecha_str'], errors='coerce')
                
                df = df.drop(columns=['fecha_str', 'hora_str'], errors='ignore')
            except:
                pass
        elif 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        
        # Tipos numéricos
        for col in ['latitud', 'longitud', 'magnitud', 'profundidad_km']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Fuente
        df['fuente'] = f'ISC-{self.catalogo.upper()}'
        
        # IDs
        if 'id_evento' not in df.columns:
            df['id_evento'] = [f"isc_{i:08d}" for i in range(len(df))]
        else:
            df['id_evento'] = 'isc_' + df['id_evento'].astype(str)
        
        # Columnas faltantes
        df = self._añadir_columnas_faltantes(df)
        
        # Ordenar
        if 'fecha' in df.columns:
            df = df.sort_values('fecha').reset_index(drop=True)
        
        return df
    
    # =========================================================================
    # MÉTODOS DE CONVENIENCIA
    # =========================================================================
    
    def catalogos_disponibles(self) -> Dict[str, str]:
        """Retorna catálogos disponibles con descripción."""
        return self.CATALOGOS.copy()
    
    def descargar_gem_historico(
        self,
        region: str = 'nacional',
        magnitud_min: float = 6.0
    ) -> DownloadResult:
        """
        Descarga catálogo ISC-GEM histórico para México.
        
        El ISC-GEM contiene sismos M >= 5.5 desde 1904 con
        localizaciones y magnitudes uniformes.
        
        Args:
            region: Región de México
            magnitud_min: Magnitud mínima (default 6.0)
            
        Returns:
            DownloadResult
        """
        return self.descargar(
            fecha_inicio='1900-01-01',
            region=region,
            magnitud_min=magnitud_min
        )


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def descargar_isc(**kwargs) -> DownloadResult:
    """Función de conveniencia para descargar del ISC."""
    conector = ConectorISC()
    return conector.descargar(**kwargs)


def descargar_isc_gem_mexico(magnitud_min: float = 6.0) -> DownloadResult:
    """Descarga catálogo ISC-GEM para México."""
    conector = ConectorISC(catalogo='isc-gem')
    return conector.descargar_gem_historico(magnitud_min=magnitud_min)
