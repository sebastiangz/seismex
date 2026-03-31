"""
SEISMEX Data - Conector IRIS/FDSN (via ObsPy)
=============================================

Conector para servicios FDSN usando la librería ObsPy.
Permite acceder a múltiples centros de datos sísmicos internacionales.

Servicios FDSN soportados:
- IRIS (USA): Catálogo global completo
- USGS: Catálogo USGS (alternativa al conector directo)
- ISC: International Seismological Centre
- EMSC: European-Mediterranean Seismological Centre
- GFZ: GeoForschungsZentrum (Alemania)
- INGV: Instituto Nacional de Geofísica (Italia)
- Y muchos más...

Requiere ObsPy: pip install obspy

Configuración en ~/.seismex/config.yaml:

    iris:
      enabled: true
      fdsn_client: IRIS
      include_arrivals: false
      include_focal_mechanisms: true

Uso:
    >>> from seismex.data import ConectorIRIS
    >>> iris = ConectorIRIS()
    >>> 
    >>> # Descargar catálogo
    >>> resultado = iris.descargar(
    ...     fecha_inicio='2024-01-01',
    ...     region='nacional',
    ...     magnitud_min=4.0
    ... )
    >>> 
    >>> # Obtener mecanismos focales
    >>> resultado = iris.descargar_con_mecanismos(
    ...     fecha_inicio='2024-01-01',
    ...     magnitud_min=5.5
    ... )
"""

import logging
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple

import pandas as pd
import numpy as np

from seismex.data.base import (
    ConectorBase, QueryParams, DownloadResult,
    CATALOG_COLUMNS, REGIONES_MEXICO
)

logger = logging.getLogger(__name__)


class ConectorIRIS(ConectorBase):
    """
    Conector FDSN usando ObsPy.
    
    Este conector utiliza la librería ObsPy para acceder a servicios
    FDSN (Federation of Digital Seismograph Networks) estándar.
    
    Ventajas de usar ObsPy/FDSN:
    
    - **Múltiples fuentes**: Acceso a IRIS, USGS, ISC, EMSC y más
    - **Formato estándar**: Datos en formato QuakeML
    - **Datos completos**: Mecanismos focales, tensores de momento, fases
    - **Formas de onda**: Posibilidad de descargar sismogramas
    - **Bien mantenido**: ObsPy es el estándar de facto en sismología
    
    Servicios FDSN disponibles:
    
        IRIS, USGS, ISC, EMSC, GFZ, INGV, RESIF, ORFEUS,
        NCEDC, SCEDC, TEXNET, RASPISHAKE, y más...
    
    Ejemplos:
    
        # Usar servicio IRIS (default)
        >>> iris = ConectorIRIS()
        >>> result = iris.descargar(region='nacional', magnitud_min=4.0)
        
        # Usar servicio EMSC (Europa)
        >>> emsc = ConectorIRIS(cliente='EMSC')
        >>> result = emsc.descargar(lat_min=35, lat_max=45)
        
        # Obtener con mecanismos focales
        >>> result = iris.descargar_con_mecanismos(magnitud_min=5.5)
        
        # Ver clientes disponibles
        >>> print(ConectorIRIS.clientes_disponibles())
    """
    
    NOMBRE = "iris"
    
    # Clientes FDSN disponibles en ObsPy
    CLIENTES_FDSN = {
        'IRIS': 'IRIS Data Management Center (USA)',
        'USGS': 'US Geological Survey',
        'ISC': 'International Seismological Centre',
        'EMSC': 'European-Mediterranean Seismological Centre',
        'GFZ': 'GeoForschungsZentrum Potsdam',
        'INGV': 'Istituto Nazionale di Geofisica e Vulcanologia',
        'RESIF': 'French Seismological Network',
        'ORFEUS': 'ORFEUS Data Center',
        'NCEDC': 'Northern California Earthquake Data Center',
        'SCEDC': 'Southern California Earthquake Data Center',
        'TEXNET': 'Texas Seismological Network',
        'BGR': 'Bundesanstalt für Geowissenschaften (Germany)',
        'KOERI': 'Kandilli Observatory (Turkey)',
        'RASPISHAKE': 'Raspberry Shake Community',
    }
    
    def __init__(
        self,
        cliente: str = 'IRIS',
        usar_cache: bool = True,
        incluir_llegadas: bool = False,
        incluir_mecanismos: bool = True,
        timeout: int = 120
    ):
        """
        Inicializa el conector IRIS/FDSN.
        
        Args:
            cliente: Cliente FDSN a usar (IRIS, USGS, ISC, EMSC, etc.)
            usar_cache: Habilitar caché
            incluir_llegadas: Incluir tiempos de llegada de fases
            incluir_mecanismos: Incluir mecanismos focales si disponibles
            timeout: Timeout para requests
        """
        super().__init__(
            usar_cache=usar_cache,
            timeout=timeout
        )
        
        self.cliente_nombre = cliente.upper()
        self.incluir_llegadas = incluir_llegadas or self.config.iris.include_arrivals
        self.incluir_mecanismos = incluir_mecanismos or self.config.iris.include_focal_mechanisms
        
        # Verificar que ObsPy está instalado
        self._verificar_obspy()
        
        # Inicializar cliente FDSN
        self._cliente = None
        
        logger.debug(f"ConectorIRIS inicializado: cliente={self.cliente_nombre}")
    
    def _verificar_obspy(self) -> None:
        """Verifica que ObsPy está instalado."""
        try:
            import obspy
            from obspy.clients.fdsn import Client
            logger.debug(f"ObsPy versión {obspy.__version__} disponible")
        except ImportError:
            raise ImportError(
                "ObsPy no está instalado. Instale con:\n"
                "  pip install obspy\n"
                "  o\n"
                "  conda install -c conda-forge obspy"
            )
    
    @property
    def cliente(self):
        """Cliente FDSN (lazy initialization)."""
        if self._cliente is None:
            from obspy.clients.fdsn import Client
            self._cliente = Client(self.cliente_nombre)
            logger.info(f"Cliente FDSN '{self.cliente_nombre}' inicializado")
        return self._cliente
    
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
        limite: Optional[int] = None,
        **kwargs
    ) -> DownloadResult:
        """
        Descarga datos del servicio FDSN.
        
        Args:
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            lat_min, lat_max: Rango de latitudes
            lon_min, lon_max: Rango de longitudes
            magnitud_min, magnitud_max: Rango de magnitudes
            profundidad_min, profundidad_max: Rango de profundidades
            region: Región predefinida de México
            limite: Límite de eventos
            
        Returns:
            DownloadResult con datos
        """
        inicio_tiempo = time.time()
        
        # Construir parámetros
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
            limite=limite
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
                metadata={'cliente': self.cliente_nombre}
            )
            
        except Exception as e:
            logger.error(f"Error al descargar de FDSN: {e}")
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
        """Realiza la consulta al servicio FDSN."""
        from obspy import UTCDateTime
        
        logger.info(f"Consultando FDSN ({self.cliente_nombre})...")
        
        # Construir parámetros para ObsPy
        kwargs = {}
        
        if params.fecha_inicio:
            kwargs['starttime'] = UTCDateTime(params.fecha_inicio)
        if params.fecha_fin:
            kwargs['endtime'] = UTCDateTime(params.fecha_fin)
        
        if params.lat_min is not None:
            kwargs['minlatitude'] = params.lat_min
        if params.lat_max is not None:
            kwargs['maxlatitude'] = params.lat_max
        if params.lon_min is not None:
            kwargs['minlongitude'] = params.lon_min
        if params.lon_max is not None:
            kwargs['maxlongitude'] = params.lon_max
        
        if params.magnitud_min is not None:
            kwargs['minmagnitude'] = params.magnitud_min
        if params.magnitud_max is not None:
            kwargs['maxmagnitude'] = params.magnitud_max
        
        if params.profundidad_min is not None:
            kwargs['mindepth'] = params.profundidad_min
        if params.profundidad_max is not None:
            kwargs['maxdepth'] = params.profundidad_max
        
        if params.limite:
            kwargs['limit'] = params.limite
        
        # Incluir mecanismos focales
        if self.incluir_mecanismos:
            kwargs['includefocalmechanism'] = True
        
        # Realizar consulta
        try:
            catalog = self.cliente.get_events(**kwargs)
            logger.info(f"FDSN: {len(catalog)} eventos obtenidos")
            
            # Convertir a DataFrame
            return self._catalog_to_dataframe(catalog)
            
        except Exception as e:
            if "No data available" in str(e):
                logger.warning("No se encontraron eventos para los parámetros dados")
                return pd.DataFrame()
            raise
    
    def _catalog_to_dataframe(self, catalog) -> pd.DataFrame:
        """
        Convierte un catálogo ObsPy a DataFrame.
        
        Args:
            catalog: obspy.core.event.Catalog
            
        Returns:
            DataFrame con eventos
        """
        eventos = []
        
        for event in catalog:
            evento = self._extraer_evento(event)
            if evento:
                eventos.append(evento)
        
        return pd.DataFrame(eventos)
    
    def _extraer_evento(self, event) -> Optional[Dict[str, Any]]:
        """
        Extrae información de un evento ObsPy.
        
        Args:
            event: obspy.core.event.Event
            
        Returns:
            Diccionario con datos del evento
        """
        try:
            # Obtener origen preferido
            origin = event.preferred_origin() or (event.origins[0] if event.origins else None)
            if origin is None:
                return None
            
            # Obtener magnitud preferida
            magnitude = event.preferred_magnitude() or (event.magnitudes[0] if event.magnitudes else None)
            
            evento = {
                'id_evento': str(event.resource_id).split('/')[-1],
                'fecha': origin.time.datetime if origin.time else None,
                'latitud': origin.latitude,
                'longitud': origin.longitude,
                'profundidad_km': origin.depth / 1000.0 if origin.depth else None,
            }
            
            # Magnitud
            if magnitude:
                evento['magnitud'] = magnitude.mag
                evento['tipo_magnitud'] = magnitude.magnitude_type or 'M'
            
            # Incertidumbres
            if origin.latitude_errors:
                evento['incertidumbre_h'] = origin.latitude_errors.uncertainty
            if origin.depth_errors:
                evento['incertidumbre_z'] = origin.depth_errors.uncertainty / 1000.0 if origin.depth_errors.uncertainty else None
            
            # Calidad
            if origin.quality:
                evento['gap'] = origin.quality.azimuthal_gap
                evento['rms'] = origin.quality.standard_error
                evento['nst'] = origin.quality.used_station_count
            
            # Descripción del lugar
            if event.event_descriptions:
                for desc in event.event_descriptions:
                    if desc.type == 'region name':
                        evento['lugar'] = desc.text
                        break
            
            # Mecanismo focal
            if self.incluir_mecanismos and event.focal_mechanisms:
                fm = event.preferred_focal_mechanism() or event.focal_mechanisms[0]
                if fm.nodal_planes:
                    np1 = fm.nodal_planes.nodal_plane_1
                    if np1:
                        evento['strike'] = np1.strike
                        evento['dip'] = np1.dip
                        evento['rake'] = np1.rake
                
                if fm.moment_tensor:
                    mt = fm.moment_tensor
                    if mt.scalar_moment:
                        evento['momento_escalar'] = mt.scalar_moment
            
            return evento
            
        except Exception as e:
            logger.warning(f"Error al extraer evento: {e}")
            return None
    
    # =========================================================================
    # NORMALIZACIÓN
    # =========================================================================
    
    def _normalizar_datos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza datos al formato SEISMEX."""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Asegurar tipos
        for col in ['latitud', 'longitud', 'magnitud', 'profundidad_km']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Fecha
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        
        # Fuente
        df['fuente'] = f'FDSN-{self.cliente_nombre}'
        
        # Prefijo para IDs
        if 'id_evento' in df.columns:
            df['id_evento'] = f'fdsn_{self.cliente_nombre.lower()}_' + df['id_evento'].astype(str)
        
        # Columnas faltantes
        df = self._añadir_columnas_faltantes(df)
        
        # Ordenar
        if 'fecha' in df.columns:
            df = df.sort_values('fecha').reset_index(drop=True)
        
        return df
    
    # =========================================================================
    # MÉTODOS ESPECIALIZADOS
    # =========================================================================
    
    def descargar_con_mecanismos(
        self,
        fecha_inicio: Optional[Union[str, datetime]] = None,
        fecha_fin: Optional[Union[str, datetime]] = None,
        region: str = 'nacional',
        magnitud_min: float = 5.5,
        **kwargs
    ) -> DownloadResult:
        """
        Descarga eventos con mecanismos focales.
        
        Los mecanismos focales generalmente solo están disponibles
        para sismos M >= 5.0-5.5.
        
        Args:
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            region: Región de México
            magnitud_min: Magnitud mínima (default 5.5)
            
        Returns:
            DownloadResult con mecanismos focales
        """
        original_setting = self.incluir_mecanismos
        self.incluir_mecanismos = True
        
        try:
            result = self.descargar(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                region=region,
                magnitud_min=magnitud_min,
                **kwargs
            )
            
            # Filtrar solo eventos con mecanismos
            if result.success and result.data is not None:
                if 'strike' in result.data.columns:
                    con_mecanismo = result.data['strike'].notna()
                    result.data = result.data[con_mecanismo].reset_index(drop=True)
                    result.events_count = len(result.data)
                    logger.info(f"Eventos con mecanismo focal: {result.events_count}")
            
            return result
            
        finally:
            self.incluir_mecanismos = original_setting
    
    def cambiar_cliente(self, cliente: str) -> None:
        """
        Cambia el cliente FDSN.
        
        Args:
            cliente: Nombre del cliente (IRIS, USGS, EMSC, etc.)
        """
        cliente = cliente.upper()
        if cliente not in self.CLIENTES_FDSN:
            available = ', '.join(self.CLIENTES_FDSN.keys())
            raise ValueError(
                f"Cliente '{cliente}' no reconocido. "
                f"Disponibles: {available}"
            )
        
        self.cliente_nombre = cliente
        self._cliente = None  # Reset para lazy init
        logger.info(f"Cliente FDSN cambiado a: {cliente}")
    
    @classmethod
    def clientes_disponibles(cls) -> Dict[str, str]:
        """Retorna diccionario de clientes FDSN disponibles."""
        return cls.CLIENTES_FDSN.copy()
    
    def verificar_conexion(self) -> bool:
        """
        Verifica conectividad con el servicio FDSN.
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            from obspy import UTCDateTime
            
            # Consulta mínima
            self.cliente.get_events(
                starttime=UTCDateTime() - 86400,
                endtime=UTCDateTime(),
                minmagnitude=7.0,
                limit=1
            )
            
            logger.info(f"Conexión FDSN ({self.cliente_nombre}) verificada")
            return True
            
        except Exception as e:
            logger.error(f"Error de conexión FDSN: {e}")
            return False
    
    def info_servicio(self) -> str:
        """
        Muestra información sobre el servicio FDSN actual.
        
        Returns:
            String con información
        """
        lines = [
            "=" * 60,
            f"FDSN Service - {self.cliente_nombre}",
            "=" * 60,
            "",
            f"Cliente: {self.cliente_nombre}",
            f"Descripción: {self.CLIENTES_FDSN.get(self.cliente_nombre, 'N/A')}",
            f"Incluir mecanismos focales: {self.incluir_mecanismos}",
            f"Incluir llegadas: {self.incluir_llegadas}",
            "",
            "Clientes FDSN disponibles:",
        ]
        
        for cliente, desc in sorted(self.CLIENTES_FDSN.items()):
            marker = "→" if cliente == self.cliente_nombre else " "
            lines.append(f"  {marker} {cliente}: {desc}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def descargar_iris(**kwargs) -> DownloadResult:
    """Función de conveniencia para descargar de IRIS."""
    conector = ConectorIRIS()
    return conector.descargar(**kwargs)


def descargar_fdsn(cliente: str = 'IRIS', **kwargs) -> DownloadResult:
    """
    Descarga de cualquier servicio FDSN.
    
    Args:
        cliente: Nombre del cliente FDSN
        **kwargs: Parámetros de descarga
        
    Returns:
        DownloadResult
    """
    conector = ConectorIRIS(cliente=cliente)
    return conector.descargar(**kwargs)


def obtener_mecanismos_focales(
    region: str = 'nacional',
    magnitud_min: float = 5.5,
    **kwargs
) -> DownloadResult:
    """
    Obtiene mecanismos focales para México.
    
    Args:
        region: Región de México
        magnitud_min: Magnitud mínima
        
    Returns:
        DownloadResult con mecanismos focales
    """
    conector = ConectorIRIS()
    return conector.descargar_con_mecanismos(
        region=region,
        magnitud_min=magnitud_min,
        **kwargs
    )
