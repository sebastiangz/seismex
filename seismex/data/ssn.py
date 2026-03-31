"""
SEISMEX Data - Conector SSN (Servicio Sismológico Nacional de México)
======================================================================

Conector principal para obtener datos del SSN.
Estrategia de obtención de datos:
1. Web scraping del portal SSN (si está disponible)
2. Fallback a archivos locales descargados por el usuario

El SSN no tiene API pública oficial, por lo que:
- Se intenta web scraping primero
- Si falla, se buscan archivos en el directorio local configurado
- El usuario puede descargar manualmente del portal y colocar en ~/seismex_data/ssn

Uso:
    >>> from seismex.data import ConectorSSN
    >>> ssn = ConectorSSN()
    >>> 
    >>> # Opción 1: Intentar web scraping
    >>> resultado = ssn.descargar(fecha_inicio='2024-01-01', region='colima')
    >>> 
    >>> # Opción 2: Cargar archivo local directamente
    >>> resultado = ssn.cargar_archivo('~/seismex_data/ssn/catalogo_2024.csv')
    >>> 
    >>> # Opción 3: Descargar región predefinida
    >>> resultado = ssn.descargar_region('jalisco', fecha_inicio='2024-01-01')
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


class ConectorSSN(ConectorBase):
    """
    Conector para el Servicio Sismológico Nacional de México.
    
    El SSN es la fuente principal de datos sísmicos para México.
    Este conector intenta obtener datos mediante:
    
    1. **Web Scraping**: Accede al portal del SSN y extrae datos.
       Puede fallar si el sitio cambia su estructura o bloquea requests.
    
    2. **Archivos Locales**: Si el web scraping falla, busca archivos
       en el directorio configurado (default: ~/seismex_data/ssn).
       El usuario puede descargar manualmente del portal SSN.
    
    Configuración en ~/.seismex/config.yaml:
    
        ssn:
          enabled: true
          base_url: http://www2.ssn.unam.mx:8080/catalogo/
          local_data_dir: ~/seismex_data/ssn
          local_format: csv
          user_agent: "Mozilla/5.0 (compatible; SEISMEX/1.0)"
          request_delay: 2
    
    Ejemplos:
    
        # Descargar con web scraping (fallback automático a local)
        >>> ssn = ConectorSSN()
        >>> result = ssn.descargar(
        ...     fecha_inicio='2024-01-01',
        ...     fecha_fin='2024-12-31',
        ...     magnitud_min=4.0
        ... )
        
        # Cargar archivo local directamente
        >>> result = ssn.cargar_archivo('catalogo_ssn_2024.csv')
        
        # Listar archivos locales disponibles
        >>> archivos = ssn.listar_archivos_locales()
        
        # Descargar región de Colima
        >>> result = ssn.descargar_region('colima', fecha_inicio='2024-01-01')
    """
    
    NOMBRE = "ssn"
    
    # Mapeo de columnas SSN a formato estándar SEISMEX
    COLUMN_MAPPING = {
        # Formato típico del SSN
        'Fecha': 'fecha',
        'Hora': 'hora',
        'Magnitud': 'magnitud',
        'Latitud': 'latitud',
        'Longitud': 'longitud',
        'Profundidad': 'profundidad_km',
        'Referencia de localizacion': 'lugar',
        'Referencia de localización': 'lugar',
        'Referencia': 'lugar',
        
        # Variantes en minúsculas
        'fecha': 'fecha',
        'hora': 'hora',
        'magnitud': 'magnitud',
        'latitud': 'latitud',
        'longitud': 'longitud',
        'profundidad': 'profundidad_km',
        
        # Otras variantes
        'Fecha UTC': 'fecha',
        'Fecha Local': 'fecha_local',
        'Mag': 'magnitud',
        'Lat': 'latitud',
        'Lon': 'longitud',
        'Long': 'longitud',
        'Prof': 'profundidad_km',
        'Prof.': 'profundidad_km',
        'Epicentro': 'lugar',
        'Localizacion': 'lugar',
        'Localización': 'lugar',
    }
    
    def __init__(
        self,
        usar_cache: bool = True,
        preferir_local: bool = False,
        timeout: int = 60,
        max_reintentos: int = 3
    ):
        """
        Inicializa el conector SSN.
        
        Args:
            usar_cache: Habilitar caché de datos
            preferir_local: Si True, intenta archivos locales antes de web scraping
            timeout: Timeout para requests HTTP
            max_reintentos: Número máximo de reintentos para web scraping
        """
        super().__init__(
            usar_cache=usar_cache,
            timeout=timeout,
            max_reintentos=max_reintentos
        )
        
        self.preferir_local = preferir_local
        
        # Configuración específica SSN
        self.base_url = self.config.ssn.base_url
        self.local_data_dir = Path(str(self.config.ssn.local_data_dir).replace(
            "~", str(Path.home())
        ))
        self.local_format = self.config.ssn.local_format
        self.user_agent = self.config.ssn.user_agent
        self.request_delay = self.config.ssn.request_delay
        
        # Crear directorio local si no existe
        self.local_data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"ConectorSSN inicializado. Local dir: {self.local_data_dir}")
    
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
        region: Optional[str] = None,
        archivo_local: Optional[str] = None,
        forzar_web: bool = False,
        forzar_local: bool = False,
        **kwargs
    ) -> DownloadResult:
        """
        Descarga datos del SSN.
        
        Estrategia de obtención:
        1. Si archivo_local especificado, carga ese archivo
        2. Si forzar_web=True, intenta solo web scraping
        3. Si forzar_local=True, busca solo en archivos locales
        4. Por defecto: intenta web scraping, fallback a local
        
        Args:
            fecha_inicio: Fecha inicial (YYYY-MM-DD)
            fecha_fin: Fecha final (YYYY-MM-DD), default=hoy
            lat_min, lat_max: Rango de latitudes
            lon_min, lon_max: Rango de longitudes  
            magnitud_min, magnitud_max: Rango de magnitudes
            region: Región predefinida (colima, jalisco, etc.)
            archivo_local: Ruta a archivo local específico
            forzar_web: Usar solo web scraping (sin fallback)
            forzar_local: Usar solo archivos locales
            
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
            region=region
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
        
        # Verificar caché primero
        if self.usar_cache and not forzar_web:
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
        
        # Estrategia de obtención de datos
        df = None
        errores = []
        warnings = []
        from_cache = False
        
        # Opción 1: Archivo local específico
        if archivo_local:
            try:
                df = self._cargar_archivo_local(archivo_local)
                logger.info(f"Datos cargados desde archivo: {archivo_local}")
            except Exception as e:
                errores.append(f"Error al cargar archivo: {e}")
        
        # Opción 2: Forzar local o preferir local
        elif forzar_local or self.preferir_local:
            df = self._buscar_en_locales(params)
            if df is None and not forzar_local:
                # Fallback a web si no se fuerza local
                df = self._intentar_web_scraping(params, errores, warnings)
        
        # Opción 3: Web scraping con fallback a local (default)
        else:
            if not forzar_web:
                # Intentar web scraping primero
                df = self._intentar_web_scraping(params, errores, warnings)
            
            # Fallback a archivos locales
            if df is None and not forzar_web:
                warnings.append("Web scraping falló, buscando en archivos locales...")
                df = self._buscar_en_locales(params)
                
                if df is None:
                    errores.append(
                        f"No se encontraron datos. "
                        f"Descargue archivos del SSN y colóquelos en: {self.local_data_dir}"
                    )
        
        # Procesar datos si se obtuvieron
        if df is not None and len(df) > 0:
            # Normalizar al formato SEISMEX
            df = self._normalizar_datos(df)
            
            # Aplicar filtros
            df = self._aplicar_filtros(df, params)
            
            # Guardar en caché
            if self.usar_cache and len(df) > 0:
                cache_key = self._generar_cache_key(params)
                self._cache.set(
                    cache_key, df, 
                    source=self.NOMBRE,
                    query_params=params.to_dict()
                )
        
        success = df is not None and len(df) > 0
        
        return DownloadResult(
            success=success,
            data=df if success else None,
            source=self.NOMBRE,
            query_params=params,
            events_count=len(df) if df is not None else 0,
            download_time=time.time() - inicio_tiempo,
            from_cache=from_cache,
            errors=errores,
            warnings=warnings
        )
    
    # =========================================================================
    # WEB SCRAPING
    # =========================================================================
    
    def _intentar_web_scraping(
        self,
        params: QueryParams,
        errores: List[str],
        warnings: List[str]
    ) -> Optional[pd.DataFrame]:
        """
        Intenta obtener datos mediante web scraping del portal SSN.
        
        Args:
            params: Parámetros de consulta
            errores: Lista para agregar errores
            warnings: Lista para agregar advertencias
            
        Returns:
            DataFrame con datos o None si falla
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            warnings.append(
                "Paquetes 'requests' y 'beautifulsoup4' no instalados. "
                "Instale con: pip install requests beautifulsoup4"
            )
            return None
        
        logger.info("Intentando web scraping del SSN...")
        
        for intento in range(self.max_reintentos):
            try:
                # Construir URL de consulta
                url = self._construir_url_consulta(params)
                
                headers = {
                    'User-Agent': self.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'es-MX,es;q=0.9,en;q=0.8',
                }
                
                # Realizar request
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Parsear respuesta
                df = self._parsear_respuesta_web(response.text)
                
                if df is not None and len(df) > 0:
                    logger.info(f"Web scraping exitoso: {len(df)} eventos")
                    return df
                else:
                    warnings.append("Web scraping retornó datos vacíos")
                    
            except requests.exceptions.Timeout:
                warnings.append(f"Timeout en intento {intento + 1}")
            except requests.exceptions.RequestException as e:
                warnings.append(f"Error de conexión en intento {intento + 1}: {e}")
            except Exception as e:
                warnings.append(f"Error en web scraping: {e}")
            
            # Esperar antes de reintentar
            if intento < self.max_reintentos - 1:
                time.sleep(self.request_delay)
        
        errores.append("Web scraping falló después de todos los reintentos")
        return None
    
    def _construir_url_consulta(self, params: QueryParams) -> str:
        """Construye la URL de consulta para el SSN."""
        # URL base del catálogo SSN
        base = self.base_url.rstrip('/')
        
        # Parámetros de consulta
        query_params = []
        
        if params.fecha_inicio:
            query_params.append(f"fecha1={params.fecha_inicio.strftime('%Y-%m-%d')}")
        if params.fecha_fin:
            query_params.append(f"fecha2={params.fecha_fin.strftime('%Y-%m-%d')}")
        if params.magnitud_min is not None:
            query_params.append(f"mag1={params.magnitud_min}")
        if params.magnitud_max is not None:
            query_params.append(f"mag2={params.magnitud_max}")
        if params.lat_min is not None:
            query_params.append(f"lat1={params.lat_min}")
        if params.lat_max is not None:
            query_params.append(f"lat2={params.lat_max}")
        if params.lon_min is not None:
            query_params.append(f"lon1={params.lon_min}")
        if params.lon_max is not None:
            query_params.append(f"lon2={params.lon_max}")
        
        if query_params:
            return f"{base}?{'&'.join(query_params)}"
        return base
    
    def _parsear_respuesta_web(self, html: str) -> Optional[pd.DataFrame]:
        """
        Parsea la respuesta HTML del SSN.
        
        El SSN puede devolver datos en diferentes formatos:
        - Tabla HTML
        - CSV embebido
        - Texto plano
        
        Args:
            html: Contenido HTML de la respuesta
            
        Returns:
            DataFrame con datos o None
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Intentar encontrar tabla de datos
        tables = soup.find_all('table')
        
        for table in tables:
            try:
                # Usar pandas para parsear tabla HTML
                df = pd.read_html(str(table))[0]
                
                # Verificar si parece ser una tabla de sismos
                cols_lower = [str(c).lower() for c in df.columns]
                if any('mag' in c or 'magnitud' in c for c in cols_lower):
                    if any('lat' in c or 'latitud' in c for c in cols_lower):
                        return df
            except:
                continue
        
        # Intentar extraer datos de texto/CSV
        text_content = soup.get_text()
        if 'Magnitud' in text_content or 'magnitud' in text_content:
            # Intentar parsear como CSV
            try:
                lines = [l.strip() for l in text_content.split('\n') if l.strip()]
                csv_text = '\n'.join(lines)
                df = pd.read_csv(StringIO(csv_text))
                return df
            except:
                pass
        
        return None
    
    def _fetch_data(self, params: QueryParams) -> pd.DataFrame:
        """Implementación del método abstracto - usa web scraping."""
        errores = []
        warnings = []
        df = self._intentar_web_scraping(params, errores, warnings)
        if df is None:
            raise RuntimeError("No se pudieron obtener datos del SSN")
        return df
    
    # =========================================================================
    # ARCHIVOS LOCALES
    # =========================================================================
    
    def _buscar_en_locales(self, params: QueryParams) -> Optional[pd.DataFrame]:
        """
        Busca y carga datos de archivos locales.
        
        Args:
            params: Parámetros de consulta
            
        Returns:
            DataFrame combinado o None
        """
        archivos = self.listar_archivos_locales()
        
        if not archivos:
            logger.warning(f"No se encontraron archivos en {self.local_data_dir}")
            return None
        
        logger.info(f"Encontrados {len(archivos)} archivos locales")
        
        # Cargar y combinar todos los archivos
        dfs = []
        for archivo in archivos:
            try:
                df = self._cargar_archivo_local(archivo)
                if df is not None and len(df) > 0:
                    dfs.append(df)
            except Exception as e:
                logger.warning(f"Error al cargar {archivo}: {e}")
        
        if not dfs:
            return None
        
        # Combinar DataFrames
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # Eliminar duplicados
        df_combined = df_combined.drop_duplicates()
        
        logger.info(f"Cargados {len(df_combined)} eventos desde archivos locales")
        return df_combined
    
    def _cargar_archivo_local(self, filepath: Union[str, Path]) -> pd.DataFrame:
        """
        Carga un archivo local del SSN.
        
        Soporta formatos:
        - CSV (.csv)
        - Excel (.xlsx, .xls)
        - Texto delimitado (.txt, .dat)
        
        Args:
            filepath: Ruta al archivo
            
        Returns:
            DataFrame con datos
        """
        filepath = Path(str(filepath).replace("~", str(Path.home())))
        
        if not filepath.exists():
            # Buscar en directorio local
            local_path = self.local_data_dir / filepath.name
            if local_path.exists():
                filepath = local_path
            else:
                raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
        
        suffix = filepath.suffix.lower()
        
        # Intentar diferentes métodos de carga
        if suffix == '.csv':
            # Intentar diferentes encodings y separadores
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                for sep in [',', ';', '\t', '|']:
                    try:
                        df = pd.read_csv(
                            filepath, 
                            encoding=encoding, 
                            sep=sep,
                            on_bad_lines='skip'
                        )
                        if len(df.columns) > 1:
                            logger.debug(f"CSV cargado con encoding={encoding}, sep='{sep}'")
                            return df
                    except:
                        continue
            raise ValueError(f"No se pudo parsear CSV: {filepath}")
        
        elif suffix in ['.xlsx', '.xls']:
            return pd.read_excel(filepath)
        
        elif suffix in ['.txt', '.dat']:
            # Intentar como CSV con diferentes separadores
            for sep in ['\t', ',', ';', r'\s+']:
                try:
                    df = pd.read_csv(filepath, sep=sep, on_bad_lines='skip')
                    if len(df.columns) > 1:
                        return df
                except:
                    continue
            raise ValueError(f"No se pudo parsear archivo de texto: {filepath}")
        
        else:
            # Intentar como CSV genérico
            return pd.read_csv(filepath, on_bad_lines='skip')
    
    def cargar_archivo(
        self,
        filepath: Union[str, Path],
        aplicar_filtros: bool = True,
        **filtros
    ) -> DownloadResult:
        """
        Carga un archivo local específico.
        
        Método público para que el usuario cargue archivos directamente
        cuando el web scraping no está disponible.
        
        Args:
            filepath: Ruta al archivo (absoluta o relativa a local_data_dir)
            aplicar_filtros: Aplicar filtros de fecha/magnitud/región
            **filtros: Filtros a aplicar (fecha_inicio, magnitud_min, etc.)
            
        Returns:
            DownloadResult con los datos
        
        Ejemplo:
            >>> ssn.cargar_archivo(
            ...     'catalogo_2024.csv',
            ...     fecha_inicio='2024-06-01',
            ...     magnitud_min=4.0
            ... )
        """
        inicio_tiempo = time.time()
        params = QueryParams(**filtros)
        
        try:
            df = self._cargar_archivo_local(filepath)
            df = self._normalizar_datos(df)
            
            if aplicar_filtros:
                df = self._aplicar_filtros(df, params)
            
            return DownloadResult(
                success=True,
                data=df,
                source=self.NOMBRE,
                query_params=params,
                events_count=len(df),
                download_time=time.time() - inicio_tiempo,
                from_cache=False,
                metadata={'archivo': str(filepath)}
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                data=None,
                source=self.NOMBRE,
                query_params=params,
                events_count=0,
                download_time=time.time() - inicio_tiempo,
                from_cache=False,
                errors=[f"Error al cargar archivo: {e}"]
            )
    
    def listar_archivos_locales(self) -> List[Path]:
        """
        Lista archivos disponibles en el directorio local.
        
        Returns:
            Lista de rutas a archivos válidos
        """
        if not self.local_data_dir.exists():
            return []
        
        extensiones = ['.csv', '.xlsx', '.xls', '.txt', '.dat']
        archivos = []
        
        for ext in extensiones:
            archivos.extend(self.local_data_dir.glob(f'*{ext}'))
            archivos.extend(self.local_data_dir.glob(f'*{ext.upper()}'))
        
        return sorted(archivos)
    
    def info_directorio_local(self) -> str:
        """
        Muestra información sobre el directorio de datos locales.
        
        Returns:
            String con información formateada
        """
        archivos = self.listar_archivos_locales()
        
        lines = [
            "=" * 60,
            "SSN - Directorio de Datos Locales",
            "=" * 60,
            f"Ubicación: {self.local_data_dir}",
            f"Archivos encontrados: {len(archivos)}",
        ]
        
        if archivos:
            lines.append("\nArchivos disponibles:")
            for archivo in archivos:
                size_kb = archivo.stat().st_size / 1024
                lines.append(f"  • {archivo.name} ({size_kb:.1f} KB)")
        else:
            lines.extend([
                "\n⚠️ No se encontraron archivos.",
                "",
                "Para usar datos locales del SSN:",
                f"1. Descargue el catálogo de: {self.base_url}",
                f"2. Guarde los archivos en: {self.local_data_dir}",
                "3. Formatos soportados: CSV, Excel, TXT",
            ])
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    # =========================================================================
    # NORMALIZACIÓN DE DATOS
    # =========================================================================
    
    def _normalizar_datos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza datos del SSN al formato estándar SEISMEX.
        
        Args:
            df: DataFrame con datos crudos del SSN
            
        Returns:
            DataFrame normalizado
        """
        df = df.copy()
        
        # Renombrar columnas al formato estándar
        column_renames = {}
        for col in df.columns:
            col_clean = str(col).strip()
            if col_clean in self.COLUMN_MAPPING:
                column_renames[col] = self.COLUMN_MAPPING[col_clean]
        
        df = df.rename(columns=column_renames)
        
        # Combinar fecha y hora si están separadas
        if 'fecha' in df.columns and 'hora' in df.columns:
            try:
                df['fecha'] = pd.to_datetime(
                    df['fecha'].astype(str) + ' ' + df['hora'].astype(str),
                    format='mixed',
                    dayfirst=True
                )
                df = df.drop(columns=['hora'], errors='ignore')
            except:
                # Si falla, intentar solo con fecha
                df['fecha'] = pd.to_datetime(df['fecha'], format='mixed', dayfirst=True)
        elif 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], format='mixed', errors='coerce')
        
        # Convertir columnas numéricas
        for col in ['latitud', 'longitud', 'magnitud', 'profundidad_km']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Añadir columna de fuente
        df['fuente'] = 'SSN'
        
        # Generar IDs si no existen
        if 'id_evento' not in df.columns:
            df['id_evento'] = [f"ssn_{i:08d}" for i in range(len(df))]
        
        # Añadir tipo de magnitud si no existe
        if 'tipo_magnitud' not in df.columns:
            df['tipo_magnitud'] = 'M'  # SSN reporta magnitud local por defecto
        
        # Añadir columnas faltantes con valores por defecto
        df = self._añadir_columnas_faltantes(df)
        
        # Ordenar por fecha
        if 'fecha' in df.columns:
            df = df.sort_values('fecha').reset_index(drop=True)
        
        return df
    
    # =========================================================================
    # FILTROS
    # =========================================================================
    
    def _aplicar_filtros(
        self, 
        df: pd.DataFrame, 
        params: QueryParams
    ) -> pd.DataFrame:
        """
        Aplica filtros de fecha, magnitud, región a los datos.
        
        Args:
            df: DataFrame a filtrar
            params: Parámetros de consulta con los filtros
            
        Returns:
            DataFrame filtrado
        """
        if df is None or len(df) == 0:
            return df
        
        mask = pd.Series([True] * len(df), index=df.index)
        
        # Filtro temporal
        if params.fecha_inicio and 'fecha' in df.columns:
            fecha_inicio = pd.to_datetime(params.fecha_inicio)
            mask &= pd.to_datetime(df['fecha']) >= fecha_inicio
        
        if params.fecha_fin and 'fecha' in df.columns:
            fecha_fin = pd.to_datetime(params.fecha_fin)
            mask &= pd.to_datetime(df['fecha']) <= fecha_fin
        
        # Filtro espacial
        if params.lat_min is not None and 'latitud' in df.columns:
            mask &= df['latitud'] >= params.lat_min
        if params.lat_max is not None and 'latitud' in df.columns:
            mask &= df['latitud'] <= params.lat_max
        if params.lon_min is not None and 'longitud' in df.columns:
            mask &= df['longitud'] >= params.lon_min
        if params.lon_max is not None and 'longitud' in df.columns:
            mask &= df['longitud'] <= params.lon_max
        
        # Filtro de magnitud
        if params.magnitud_min is not None and 'magnitud' in df.columns:
            mask &= df['magnitud'] >= params.magnitud_min
        if params.magnitud_max is not None and 'magnitud' in df.columns:
            mask &= df['magnitud'] <= params.magnitud_max
        
        # Filtro de profundidad
        if params.profundidad_min is not None and 'profundidad_km' in df.columns:
            mask &= df['profundidad_km'] >= params.profundidad_min
        if params.profundidad_max is not None and 'profundidad_km' in df.columns:
            mask &= df['profundidad_km'] <= params.profundidad_max
        
        return df[mask].reset_index(drop=True)
    
    # =========================================================================
    # MÉTODOS DE CONVENIENCIA
    # =========================================================================
    
    def obtener_ultimo_anio(
        self, 
        region: str = 'nacional',
        magnitud_min: Optional[float] = None
    ) -> DownloadResult:
        """
        Obtiene datos del último año para una región.
        
        Args:
            region: Región de México
            magnitud_min: Magnitud mínima
            
        Returns:
            DownloadResult
        """
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=365)
        
        return self.descargar(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            region=region,
            magnitud_min=magnitud_min
        )
    
    def obtener_sismos_significativos(
        self,
        fecha_inicio: Optional[Union[str, datetime]] = None,
        magnitud_min: float = 5.0
    ) -> DownloadResult:
        """
        Obtiene sismos significativos (M >= 5.0 por defecto).
        
        Args:
            fecha_inicio: Fecha inicial
            magnitud_min: Magnitud mínima (default 5.0)
            
        Returns:
            DownloadResult
        """
        return self.descargar(
            fecha_inicio=fecha_inicio,
            magnitud_min=magnitud_min,
            region='nacional'
        )


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def descargar_ssn(**kwargs) -> DownloadResult:
    """
    Función de conveniencia para descargar datos del SSN.
    
    Args:
        **kwargs: Parámetros para ConectorSSN.descargar()
        
    Returns:
        DownloadResult
    """
    conector = ConectorSSN()
    return conector.descargar(**kwargs)


def cargar_ssn_local(filepath: Union[str, Path], **filtros) -> DownloadResult:
    """
    Función de conveniencia para cargar archivo local del SSN.
    
    Args:
        filepath: Ruta al archivo
        **filtros: Filtros a aplicar
        
    Returns:
        DownloadResult
    """
    conector = ConectorSSN()
    return conector.cargar_archivo(filepath, **filtros)
