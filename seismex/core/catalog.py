"""
SEISMEX Core - Catálogo Sísmico
================================

Clase principal para gestión de catálogos sísmicos de múltiples fuentes.

Este módulo proporciona la clase CatalogoSismico que permite:
- Cargar catálogos desde CSV, Excel, DataFrame o APIs
- Validar y normalizar datos sísmicos
- Filtrar por región, magnitud, profundidad y tiempo
- Combinar múltiples catálogos con detección de duplicados
- Homogeneizar magnitudes a Mw
- Exportar a múltiples formatos

Ejemplo de uso:
    >>> from seismex.core import CatalogoSismico
    >>> catalogo = CatalogoSismico.desde_csv('sismos.csv', formato='ssn')
    >>> catalogo.validar()
    >>> catalogo_filtrado = catalogo.filtrar_region(
    ...     lat_min=18.5, lat_max=20.0,
    ...     lon_min=-104.5, lon_max=-103.0
    ... ).filtrar_magnitud(mag_min=4.0)
    >>> print(catalogo_filtrado.resumen())

Autor: SEISMEX Team
Licencia: MIT
"""

from __future__ import annotations

import warnings
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import (
    Optional, List, Dict, Tuple, Union, Any, 
    Callable, Literal, TYPE_CHECKING
)

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import geopandas as gpd

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES Y CONFIGURACIÓN
# =============================================================================

# Columnas estándar del catálogo
COLUMNAS_REQUERIDAS = ['fecha', 'latitud', 'longitud', 'profundidad_km', 'magnitud']
COLUMNAS_OPCIONALES = [
    'tipo_magnitud', 'fuente', 'id_evento', 'lugar',
    'incertidumbre_h', 'incertidumbre_z', 'incertidumbre_m',
    'rms', 'gap', 'nst'
]

# Mapeos de columnas por formato
MAPEOS_COLUMNAS = {
    'ssn': {
        'Fecha': 'fecha',
        'Latitud': 'latitud',
        'Longitud': 'longitud',
        'Profundidad': 'profundidad_km',
        'Magnitud': 'magnitud',
        'Referencia de localizacion': 'lugar',
        'Fecha UTC': 'fecha',
    },
    'usgs': {
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
    },
    'isc': {
        'date': 'fecha',
        'lat': 'latitud',
        'lon': 'longitud',
        'depth': 'profundidad_km',
        'mw': 'magnitud',
        'smaj': 'incertidumbre_h',
        'q': 'calidad',
    },
    'isc-gem': {
        'date': 'fecha',
        'lat': 'latitud',
        'lon': 'longitud',
        'depth': 'profundidad_km',
        'mw': 'magnitud',
    },
    'iris': {
        'time': 'fecha',
        'latitude': 'latitud',
        'longitude': 'longitud',
        'depth': 'profundidad_km',
        'magnitude': 'magnitud',
        'magnitude_type': 'tipo_magnitud',
    },
}

# Coeficientes de conversión de magnitud
# Relaciones empíricas para México y globales
CONVERSIONES_MAGNITUD = {
    # Ml a Mw (México, Zúñiga et al.)
    ('ml', 'mw'): lambda m: 0.85 * m + 0.58,
    ('ML', 'Mw'): lambda m: 0.85 * m + 0.58,
    
    # mb a Mw (Scordilis 2006)
    ('mb', 'mw'): lambda m: 1.03 * m - 0.20 if m < 6.2 else 0.85 * m + 1.03,
    ('Mb', 'Mw'): lambda m: 1.03 * m - 0.20 if m < 6.2 else 0.85 * m + 1.03,
    
    # Ms a Mw (Scordilis 2006)
    ('ms', 'mw'): lambda m: 0.67 * m + 2.13 if m < 6.1 else 0.99 * m + 0.08,
    ('Ms', 'Mw'): lambda m: 0.67 * m + 2.13 if m < 6.1 else 0.99 * m + 0.08,
    ('MS', 'Mw'): lambda m: 0.67 * m + 2.13 if m < 6.1 else 0.99 * m + 0.08,
    
    # Md a Mw (aproximación)
    ('md', 'mw'): lambda m: 0.85 * m + 0.40,
    ('Md', 'Mw'): lambda m: 0.85 * m + 0.40,
    
    # Mc a Mw (coda, aproximación)
    ('mc', 'mw'): lambda m: 0.90 * m + 0.30,
    ('Mc', 'Mw'): lambda m: 0.90 * m + 0.30,
}


# =============================================================================
# DATACLASSES AUXILIARES
# =============================================================================

@dataclass
class MetadataCatalogo:
    """
    Metadatos del catálogo sísmico.
    
    Attributes:
        fuente: Fuente de los datos (SSN, USGS, ISC, etc.)
        region: Nombre de la región geográfica
        fecha_descarga: Fecha de descarga de los datos
        fecha_inicio: Fecha del primer evento
        fecha_fin: Fecha del último evento
        homogeneizado: Si las magnitudes están homogeneizadas a Mw
        declustered: Si se aplicó declustering
        version: Versión del catálogo
        notas: Notas adicionales
    """
    fuente: str = 'desconocida'
    region: Optional[str] = None
    fecha_descarga: Optional[datetime] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    homogeneizado: bool = False
    tipo_magnitud_homogeneizada: Optional[str] = None
    declustered: bool = False
    metodo_declustering: Optional[str] = None
    version: str = '1.0'
    notas: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte metadatos a diccionario."""
        return {
            'fuente': self.fuente,
            'region': self.region,
            'fecha_descarga': self.fecha_descarga.isoformat() if self.fecha_descarga else None,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'homogeneizado': self.homogeneizado,
            'tipo_magnitud_homogeneizada': self.tipo_magnitud_homogeneizada,
            'declustered': self.declustered,
            'metodo_declustering': self.metodo_declustering,
            'version': self.version,
            'notas': self.notas,
        }


@dataclass
class ResultadoValidacion:
    """
    Resultado de la validación del catálogo.
    
    Attributes:
        es_valido: True si el catálogo es válido
        errores: Lista de errores críticos encontrados
        advertencias: Lista de advertencias
        estadisticas: Estadísticas de la validación
    """
    es_valido: bool
    errores: List[str] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)
    estadisticas: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        status = "✓ VÁLIDO" if self.es_valido else "✗ INVÁLIDO"
        lines = [f"Resultado de Validación: {status}"]
        
        if self.errores:
            lines.append("\nErrores:")
            for e in self.errores:
                lines.append(f"  ✗ {e}")
        
        if self.advertencias:
            lines.append("\nAdvertencias:")
            for w in self.advertencias:
                lines.append(f"  ⚠ {w}")
        
        return "\n".join(lines)


# =============================================================================
# CLASE PRINCIPAL: CatalogoSismico
# =============================================================================

class CatalogoSismico:
    """
    Contenedor para catálogos sísmicos con soporte para múltiples formatos.
    
    Esta clase proporciona una interfaz unificada para trabajar con catálogos
    sísmicos de diversas fuentes (SSN, USGS, ISC, IRIS, etc.), incluyendo
    carga, validación, filtrado, combinación y exportación.
    
    Attributes:
        datos: DataFrame con los eventos sísmicos
        metadata: Metadatos del catálogo
        es_valido: Indica si el catálogo pasó validación
        
    Example:
        >>> catalogo = CatalogoSismico.desde_csv('ssn_2024.csv', formato='ssn')
        >>> catalogo.validar()
        >>> print(catalogo.resumen())
        >>> catalogo_filtrado = catalogo.filtrar_magnitud(mag_min=4.0)
    """
    
    # Constantes de clase
    COLUMNAS_REQUERIDAS = COLUMNAS_REQUERIDAS
    COLUMNAS_OPCIONALES = COLUMNAS_OPCIONALES
    
    def __init__(
        self, 
        datos: Optional[pd.DataFrame] = None,
        metadata: Optional[Union[MetadataCatalogo, Dict[str, Any]]] = None
    ):
        """
        Inicializa el catálogo sísmico.
        
        Args:
            datos: DataFrame con los eventos sísmicos
            metadata: Metadatos del catálogo (MetadataCatalogo o dict)
        """
        self._datos = datos.copy() if datos is not None else pd.DataFrame()
        self._validado = False
        self._resultado_validacion: Optional[ResultadoValidacion] = None
        
        # Procesar metadata
        if metadata is None:
            self._metadata = MetadataCatalogo()
        elif isinstance(metadata, dict):
            self._metadata = MetadataCatalogo(**metadata)
        else:
            self._metadata = metadata
        
        # Normalizar columnas si hay datos
        if not self._datos.empty:
            self._normalizar_columnas()
    
    # =========================================================================
    # PROPIEDADES
    # =========================================================================
    
    @property
    def datos(self) -> pd.DataFrame:
        """DataFrame con los eventos sísmicos."""
        return self._datos
    
    @datos.setter
    def datos(self, value: pd.DataFrame) -> None:
        """Setter que invalida la validación al modificar datos."""
        self._datos = value.copy() if value is not None else pd.DataFrame()
        self._validado = False
        self._resultado_validacion = None
    
    @property
    def metadata(self) -> MetadataCatalogo:
        """Metadatos del catálogo."""
        return self._metadata
    
    @metadata.setter
    def metadata(self, value: Union[MetadataCatalogo, Dict[str, Any]]) -> None:
        """Setter para metadatos."""
        if isinstance(value, dict):
            self._metadata = MetadataCatalogo(**value)
        else:
            self._metadata = value
    
    @property
    def es_valido(self) -> bool:
        """Indica si el catálogo está validado y es válido."""
        return self._validado and (
            self._resultado_validacion is not None and 
            self._resultado_validacion.es_valido
        )
    
    @property
    def n_eventos(self) -> int:
        """Número de eventos en el catálogo."""
        return len(self._datos)
    
    @property
    def rango_fechas(self) -> Optional[Tuple[datetime, datetime]]:
        """Rango de fechas (min, max)."""
        if self._datos.empty or 'fecha' not in self._datos.columns:
            return None
        fechas = pd.to_datetime(self._datos['fecha'])
        return (fechas.min().to_pydatetime(), fechas.max().to_pydatetime())
    
    @property
    def rango_magnitudes(self) -> Optional[Tuple[float, float]]:
        """Rango de magnitudes (min, max)."""
        if self._datos.empty or 'magnitud' not in self._datos.columns:
            return None
        return (float(self._datos['magnitud'].min()), 
                float(self._datos['magnitud'].max()))
    
    @property
    def rango_profundidades(self) -> Optional[Tuple[float, float]]:
        """Rango de profundidades (min, max) en km."""
        if self._datos.empty or 'profundidad_km' not in self._datos.columns:
            return None
        profs = self._datos['profundidad_km'].abs()
        return (float(profs.min()), float(profs.max()))
    
    @property
    def extension_espacial(self) -> Optional[Dict[str, Tuple[float, float]]]:
        """Extensión espacial del catálogo."""
        if self._datos.empty:
            return None
        return {
            'latitud': (float(self._datos['latitud'].min()), 
                       float(self._datos['latitud'].max())),
            'longitud': (float(self._datos['longitud'].min()), 
                        float(self._datos['longitud'].max())),
        }
    
    @property
    def columnas(self) -> List[str]:
        """Lista de columnas disponibles."""
        return list(self._datos.columns)
    
    # =========================================================================
    # MÉTODOS MÁGICOS
    # =========================================================================
    
    def __len__(self) -> int:
        """Número de eventos."""
        return self.n_eventos
    
    def __repr__(self) -> str:
        """Representación del catálogo."""
        estado = "✓" if self.es_valido else "○"
        return f"CatalogoSismico({self.n_eventos} eventos, fuente='{self._metadata.fuente}') [{estado}]"
    
    def __str__(self) -> str:
        """Representación legible."""
        return self.resumen()
    
    def __getitem__(self, key: Union[str, int, slice]) -> Union[pd.Series, pd.DataFrame]:
        """Acceso a columnas o filas."""
        if isinstance(key, str):
            return self._datos[key]
        return self._datos.iloc[key]
    
    def __iter__(self):
        """Iterador sobre eventos."""
        return self._datos.itertuples(index=False)
    
    def __contains__(self, item: str) -> bool:
        """Verifica si una columna existe."""
        return item in self._datos.columns
    
    # =========================================================================
    # MÉTODOS DE CLASE - CARGA DE DATOS
    # =========================================================================
    
    @classmethod
    def desde_csv(
        cls,
        ruta: Union[str, Path],
        formato: Literal['ssn', 'usgs', 'isc', 'isc-gem', 'iris', 'custom'] = 'custom',
        mapeo_columnas: Optional[Dict[str, str]] = None,
        encoding: str = 'utf-8',
        **kwargs
    ) -> 'CatalogoSismico':
        """
        Carga un catálogo desde archivo CSV.
        
        Args:
            ruta: Ruta al archivo CSV
            formato: Formato del archivo ('ssn', 'usgs', 'isc', 'isc-gem', 'iris', 'custom')
            mapeo_columnas: Diccionario personalizado de mapeo de columnas
            encoding: Codificación del archivo
            **kwargs: Argumentos adicionales para pd.read_csv
            
        Returns:
            CatalogoSismico con los datos cargados
            
        Example:
            >>> catalogo = CatalogoSismico.desde_csv('ssn_2024.csv', formato='ssn')
            >>> catalogo = CatalogoSismico.desde_csv(
            ...     'custom.csv',
            ...     formato='custom',
            ...     mapeo_columnas={'LAT': 'latitud', 'LON': 'longitud'}
            ... )
        """
        ruta = Path(ruta)
        if not ruta.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
        
        logger.info(f"Cargando catálogo desde {ruta} (formato: {formato})")
        
        # Cargar datos
        datos = pd.read_csv(ruta, encoding=encoding, **kwargs)
        
        # Obtener mapeo de columnas
        if mapeo_columnas:
            mapeo = mapeo_columnas
        elif formato in MAPEOS_COLUMNAS:
            mapeo = MAPEOS_COLUMNAS[formato]
        else:
            mapeo = {}
        
        # Aplicar mapeo
        if mapeo:
            columnas_existentes = {k: v for k, v in mapeo.items() if k in datos.columns}
            datos = datos.rename(columns=columnas_existentes)
        
        # Crear metadata
        metadata = MetadataCatalogo(
            fuente=formato.upper(),
            fecha_descarga=datetime.now(),
        )
        
        catalogo = cls(datos, metadata)
        logger.info(f"Catálogo cargado: {len(catalogo)} eventos")
        
        return catalogo
    
    @classmethod
    def desde_excel(
        cls,
        ruta: Union[str, Path],
        hoja: Union[str, int] = 0,
        formato: str = 'custom',
        mapeo_columnas: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> 'CatalogoSismico':
        """
        Carga un catálogo desde archivo Excel.
        
        Args:
            ruta: Ruta al archivo Excel
            hoja: Nombre o índice de la hoja
            formato: Formato del archivo
            mapeo_columnas: Diccionario de mapeo de columnas
            **kwargs: Argumentos adicionales para pd.read_excel
            
        Returns:
            CatalogoSismico con los datos cargados
        """
        ruta = Path(ruta)
        if not ruta.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
        
        logger.info(f"Cargando catálogo desde {ruta} (hoja: {hoja})")
        
        datos = pd.read_excel(ruta, sheet_name=hoja, **kwargs)
        
        # Aplicar mapeo
        if mapeo_columnas:
            columnas_existentes = {k: v for k, v in mapeo_columnas.items() if k in datos.columns}
            datos = datos.rename(columns=columnas_existentes)
        elif formato in MAPEOS_COLUMNAS:
            mapeo = MAPEOS_COLUMNAS[formato]
            columnas_existentes = {k: v for k, v in mapeo.items() if k in datos.columns}
            datos = datos.rename(columns=columnas_existentes)
        
        metadata = MetadataCatalogo(
            fuente=formato.upper(),
            fecha_descarga=datetime.now(),
        )
        
        return cls(datos, metadata)
    
    @classmethod
    def desde_dataframe(
        cls,
        df: pd.DataFrame,
        mapeo_columnas: Optional[Dict[str, str]] = None,
        fuente: str = 'dataframe'
    ) -> 'CatalogoSismico':
        """
        Crea un catálogo desde un DataFrame de pandas.
        
        Args:
            df: DataFrame con los datos sísmicos
            mapeo_columnas: Diccionario de mapeo de columnas
            fuente: Nombre de la fuente de datos
            
        Returns:
            CatalogoSismico con los datos
        """
        datos = df.copy()
        
        if mapeo_columnas:
            columnas_existentes = {k: v for k, v in mapeo_columnas.items() if k in datos.columns}
            datos = datos.rename(columns=columnas_existentes)
        
        metadata = MetadataCatalogo(fuente=fuente)
        
        return cls(datos, metadata)
    
    @classmethod
    def desde_ssn(cls, datos_ssn: pd.DataFrame) -> 'CatalogoSismico':
        """
        Crea catálogo a partir de datos del SSN México.
        
        Args:
            datos_ssn: DataFrame con datos del SSN
            
        Returns:
            CatalogoSismico normalizado
        """
        mapeo = MAPEOS_COLUMNAS['ssn']
        datos = datos_ssn.copy()
        
        columnas_existentes = {k: v for k, v in mapeo.items() if k in datos.columns}
        datos = datos.rename(columns=columnas_existentes)
        
        # Agregar tipo de magnitud si no existe
        if 'tipo_magnitud' not in datos.columns:
            datos['tipo_magnitud'] = 'Mc'  # SSN usa magnitud de coda por defecto
        
        metadata = MetadataCatalogo(
            fuente='SSN',
            region='México',
        )
        
        return cls(datos, metadata)
    
    @classmethod
    def desde_usgs(cls, datos_usgs: pd.DataFrame) -> 'CatalogoSismico':
        """
        Crea catálogo a partir de datos del USGS.
        
        Args:
            datos_usgs: DataFrame con datos del USGS
            
        Returns:
            CatalogoSismico normalizado
        """
        mapeo = MAPEOS_COLUMNAS['usgs']
        datos = datos_usgs.copy()
        
        columnas_existentes = {k: v for k, v in mapeo.items() if k in datos.columns}
        datos = datos.rename(columns=columnas_existentes)
        
        datos['fuente'] = 'USGS'
        
        metadata = MetadataCatalogo(fuente='USGS')
        
        return cls(datos, metadata)
    
    @classmethod
    def desde_isc(
        cls, 
        datos_isc: pd.DataFrame,
        catalogo: str = 'isc-gem'
    ) -> 'CatalogoSismico':
        """
        Crea catálogo a partir de datos del ISC.
        
        Args:
            datos_isc: DataFrame con datos del ISC
            catalogo: Tipo de catálogo ('isc', 'isc-gem')
            
        Returns:
            CatalogoSismico normalizado
        """
        mapeo = MAPEOS_COLUMNAS.get(catalogo, MAPEOS_COLUMNAS['isc'])
        datos = datos_isc.copy()
        
        columnas_existentes = {k: v for k, v in mapeo.items() if k in datos.columns}
        datos = datos.rename(columns=columnas_existentes)
        
        # ISC-GEM ya tiene Mw homogeneizado
        if catalogo == 'isc-gem':
            datos['tipo_magnitud'] = 'Mw'
        
        datos['fuente'] = catalogo.upper()
        
        metadata = MetadataCatalogo(
            fuente=catalogo.upper(),
            homogeneizado=(catalogo == 'isc-gem'),
            tipo_magnitud_homogeneizada='Mw' if catalogo == 'isc-gem' else None,
        )
        
        return cls(datos, metadata)
    
    @classmethod
    def combinar(
        cls,
        catalogos: List['CatalogoSismico'],
        prioridad: Optional[List[str]] = None,
        tolerancia_duplicados_km: float = 50.0,
        tolerancia_duplicados_seg: int = 60,
        detectar_duplicados: bool = True
    ) -> 'CatalogoSismico':
        """
        Combina múltiples catálogos en uno solo.
        
        Args:
            catalogos: Lista de catálogos a combinar
            prioridad: Lista de fuentes en orden de prioridad
            tolerancia_duplicados_km: Distancia máxima para considerar duplicados
            tolerancia_duplicados_seg: Tiempo máximo para considerar duplicados
            detectar_duplicados: Si True, elimina eventos duplicados
            
        Returns:
            CatalogoSismico combinado
            
        Example:
            >>> combinado = CatalogoSismico.combinar(
            ...     [ssn, usgs, isc],
            ...     prioridad=['SSN', 'ISC', 'USGS'],
            ...     tolerancia_duplicados_km=50
            ... )
        """
        if not catalogos:
            raise ValueError("Se requiere al menos un catálogo")
        
        if len(catalogos) == 1:
            return catalogos[0].copiar()
        
        logger.info(f"Combinando {len(catalogos)} catálogos...")
        
        # Agregar columna de fuente si no existe
        dfs = []
        for cat in catalogos:
            df = cat.datos.copy()
            if 'fuente' not in df.columns:
                df['fuente'] = cat.metadata.fuente
            dfs.append(df)
        
        # Concatenar
        datos_combinados = pd.concat(dfs, ignore_index=True)
        
        # Ordenar por prioridad si se especifica
        if prioridad:
            prioridad_map = {f: i for i, f in enumerate(prioridad)}
            datos_combinados['_prioridad'] = datos_combinados['fuente'].map(
                lambda x: prioridad_map.get(x.upper(), 999)
            )
            datos_combinados = datos_combinados.sort_values('_prioridad')
            datos_combinados = datos_combinados.drop(columns=['_prioridad'])
        
        # Detectar y eliminar duplicados
        if detectar_duplicados:
            n_antes = len(datos_combinados)
            datos_combinados = cls._eliminar_duplicados(
                datos_combinados,
                tolerancia_km=tolerancia_duplicados_km,
                tolerancia_seg=tolerancia_duplicados_seg
            )
            n_eliminados = n_antes - len(datos_combinados)
            if n_eliminados > 0:
                logger.info(f"Eliminados {n_eliminados} eventos duplicados")
        
        # Ordenar por fecha
        if 'fecha' in datos_combinados.columns:
            datos_combinados['fecha'] = pd.to_datetime(datos_combinados['fecha'])
            datos_combinados = datos_combinados.sort_values('fecha').reset_index(drop=True)
        
        metadata = MetadataCatalogo(
            fuente='COMBINADO',
            notas=[f"Combinación de: {', '.join(c.metadata.fuente for c in catalogos)}"]
        )
        
        return cls(datos_combinados, metadata)
    
    @staticmethod
    def _eliminar_duplicados(
        df: pd.DataFrame,
        tolerancia_km: float = 50.0,
        tolerancia_seg: int = 60
    ) -> pd.DataFrame:
        """
        Elimina eventos duplicados basándose en proximidad espaciotemporal.
        
        Mantiene el primer evento encontrado (según el orden del DataFrame).
        """
        if df.empty:
            return df
        
        # Asegurar que fecha es datetime
        df = df.copy()
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.sort_values('fecha').reset_index(drop=True)
        
        # Marcar duplicados
        duplicados = set()
        
        for i in range(len(df)):
            if i in duplicados:
                continue
            
            for j in range(i + 1, len(df)):
                if j in duplicados:
                    continue
                
                # Verificar tiempo
                dt = abs((df.loc[j, 'fecha'] - df.loc[i, 'fecha']).total_seconds())
                if dt > tolerancia_seg:
                    break  # Ya ordenado por fecha, no hay más candidatos
                
                # Verificar distancia (aproximación rápida)
                dlat = df.loc[j, 'latitud'] - df.loc[i, 'latitud']
                dlon = df.loc[j, 'longitud'] - df.loc[i, 'longitud']
                dist_aprox = np.sqrt(dlat**2 + dlon**2) * 111.0  # km aproximado
                
                if dist_aprox < tolerancia_km:
                    duplicados.add(j)
        
        return df.drop(index=list(duplicados)).reset_index(drop=True)
    
    # =========================================================================
    # MÉTODOS DE VALIDACIÓN
    # =========================================================================
    
    def validar(self, estricto: bool = False) -> ResultadoValidacion:
        """
        Valida que el catálogo tenga estructura y datos correctos.
        
        Args:
            estricto: Si True, advertencias se tratan como errores
            
        Returns:
            ResultadoValidacion con detalles de la validación
            
        Example:
            >>> resultado = catalogo.validar()
            >>> if resultado.es_valido:
            ...     print("Catálogo válido")
            >>> else:
            ...     for error in resultado.errores:
            ...         print(f"Error: {error}")
        """
        errores = []
        advertencias = []
        estadisticas = {}
        
        # Verificar que no está vacío
        if self._datos.empty:
            errores.append("El catálogo está vacío")
            self._resultado_validacion = ResultadoValidacion(False, errores)
            return self._resultado_validacion
        
        # Verificar columnas requeridas
        columnas_faltantes = set(self.COLUMNAS_REQUERIDAS) - set(self._datos.columns)
        if columnas_faltantes:
            errores.append(f"Columnas requeridas faltantes: {columnas_faltantes}")
        
        # Verificar tipos de datos y rangos
        if 'latitud' in self._datos.columns:
            lat_invalidas = (self._datos['latitud'].abs() > 90).sum()
            if lat_invalidas > 0:
                errores.append(f"{lat_invalidas} latitudes fuera de rango [-90, 90]")
            estadisticas['lat_rango'] = (
                float(self._datos['latitud'].min()),
                float(self._datos['latitud'].max())
            )
        
        if 'longitud' in self._datos.columns:
            lon_invalidas = (self._datos['longitud'].abs() > 180).sum()
            if lon_invalidas > 0:
                errores.append(f"{lon_invalidas} longitudes fuera de rango [-180, 180]")
            estadisticas['lon_rango'] = (
                float(self._datos['longitud'].min()),
                float(self._datos['longitud'].max())
            )
        
        if 'profundidad_km' in self._datos.columns:
            prof_negativas = (self._datos['profundidad_km'] < 0).sum()
            if prof_negativas > 0:
                advertencias.append(
                    f"{prof_negativas} profundidades negativas (se usarán valores absolutos)"
                )
            prof_extremas = (self._datos['profundidad_km'].abs() > 700).sum()
            if prof_extremas > 0:
                advertencias.append(f"{prof_extremas} profundidades > 700 km")
            estadisticas['prof_rango'] = (
                float(self._datos['profundidad_km'].abs().min()),
                float(self._datos['profundidad_km'].abs().max())
            )
        
        if 'magnitud' in self._datos.columns:
            mag_negativas = (self._datos['magnitud'] < 0).sum()
            if mag_negativas > 0:
                errores.append(f"{mag_negativas} magnitudes negativas")
            mag_extremas = (self._datos['magnitud'] > 10).sum()
            if mag_extremas > 0:
                advertencias.append(f"{mag_extremas} magnitudes > 10")
            estadisticas['mag_rango'] = (
                float(self._datos['magnitud'].min()),
                float(self._datos['magnitud'].max())
            )
        
        # Verificar valores nulos
        for col in self.COLUMNAS_REQUERIDAS:
            if col in self._datos.columns:
                nulos = self._datos[col].isna().sum()
                if nulos > 0:
                    pct = 100 * nulos / len(self._datos)
                    if pct > 10:
                        advertencias.append(f"{nulos} ({pct:.1f}%) valores nulos en '{col}'")
                    estadisticas[f'{col}_nulos'] = int(nulos)
        
        # Verificar fechas
        if 'fecha' in self._datos.columns:
            try:
                fechas = pd.to_datetime(self._datos['fecha'])
                estadisticas['fecha_rango'] = (
                    str(fechas.min()),
                    str(fechas.max())
                )
            except Exception as e:
                advertencias.append(f"Problema al parsear fechas: {e}")
        
        # Determinar validez
        es_valido = len(errores) == 0
        if estricto and advertencias:
            es_valido = False
            errores.extend(advertencias)
            advertencias = []
        
        self._resultado_validacion = ResultadoValidacion(
            es_valido=es_valido,
            errores=errores,
            advertencias=advertencias,
            estadisticas=estadisticas
        )
        self._validado = True
        
        return self._resultado_validacion
    
    def _normalizar_columnas(self) -> None:
        """Normaliza los nombres de columnas a minúsculas."""
        self._datos.columns = [c.lower().strip() for c in self._datos.columns]
        
        # Renombrar variantes comunes
        renombres = {
            'lat': 'latitud',
            'latitude': 'latitud',
            'lon': 'longitud',
            'long': 'longitud',
            'longitude': 'longitud',
            'depth': 'profundidad_km',
            'profundidad': 'profundidad_km',
            'prof': 'profundidad_km',
            'mag': 'magnitud',
            'magnitude': 'magnitud',
            'time': 'fecha',
            'date': 'fecha',
            'datetime': 'fecha',
            'origen': 'fecha',
        }
        
        columnas_existentes = {k: v for k, v in renombres.items() 
                             if k in self._datos.columns and v not in self._datos.columns}
        if columnas_existentes:
            self._datos = self._datos.rename(columns=columnas_existentes)
    
    # =========================================================================
    # MÉTODOS DE FILTRADO
    # =========================================================================
    
    def filtrar_region(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        prof_min: float = 0,
        prof_max: float = 700
    ) -> 'CatalogoSismico':
        """
        Filtra eventos por región geográfica rectangular.
        
        Args:
            lat_min, lat_max: Límites de latitud
            lon_min, lon_max: Límites de longitud
            prof_min, prof_max: Límites de profundidad en km
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
            
        Example:
            >>> colima = catalogo.filtrar_region(
            ...     lat_min=18.5, lat_max=20.0,
            ...     lon_min=-104.5, lon_max=-103.0
            ... )
        """
        mascara = (
            (self._datos['latitud'] >= lat_min) &
            (self._datos['latitud'] <= lat_max) &
            (self._datos['longitud'] >= lon_min) &
            (self._datos['longitud'] <= lon_max) &
            (self._datos['profundidad_km'].abs() >= prof_min) &
            (self._datos['profundidad_km'].abs() <= prof_max)
        )
        
        nuevo = CatalogoSismico(
            self._datos[mascara].copy(),
            self._metadata
        )
        nuevo._metadata.region = f"lat:[{lat_min},{lat_max}], lon:[{lon_min},{lon_max}]"
        
        return nuevo
    
    def filtrar_circulo(
        self,
        lat_centro: float,
        lon_centro: float,
        radio_km: float
    ) -> 'CatalogoSismico':
        """
        Filtra eventos dentro de un radio circular.
        
        Args:
            lat_centro: Latitud del centro
            lon_centro: Longitud del centro
            radio_km: Radio en kilómetros
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
        """
        # Calcular distancias usando fórmula de Haversine simplificada
        lat_rad = np.radians(self._datos['latitud'])
        lon_rad = np.radians(self._datos['longitud'])
        lat_c = np.radians(lat_centro)
        lon_c = np.radians(lon_centro)
        
        dlat = lat_rad - lat_c
        dlon = lon_rad - lon_c
        
        a = np.sin(dlat/2)**2 + np.cos(lat_c) * np.cos(lat_rad) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        distancia_km = 6371 * c  # Radio de la Tierra
        
        mascara = distancia_km <= radio_km
        
        nuevo = CatalogoSismico(
            self._datos[mascara].copy(),
            self._metadata
        )
        nuevo._metadata.region = f"círculo({lat_centro}, {lon_centro}, r={radio_km}km)"
        
        return nuevo
    
    def filtrar_magnitud(
        self,
        mag_min: Optional[float] = None,
        mag_max: Optional[float] = None
    ) -> 'CatalogoSismico':
        """
        Filtra eventos por rango de magnitud.
        
        Args:
            mag_min: Magnitud mínima (inclusive)
            mag_max: Magnitud máxima (inclusive)
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
        """
        mascara = pd.Series([True] * len(self._datos), index=self._datos.index)
        
        if mag_min is not None:
            mascara &= self._datos['magnitud'] >= mag_min
        if mag_max is not None:
            mascara &= self._datos['magnitud'] <= mag_max
        
        return CatalogoSismico(self._datos[mascara].copy(), self._metadata)
    
    def filtrar_profundidad(
        self,
        prof_min: float = 0,
        prof_max: float = 700
    ) -> 'CatalogoSismico':
        """
        Filtra eventos por rango de profundidad.
        
        Args:
            prof_min: Profundidad mínima en km
            prof_max: Profundidad máxima en km
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
        """
        mascara = (
            (self._datos['profundidad_km'].abs() >= prof_min) &
            (self._datos['profundidad_km'].abs() <= prof_max)
        )
        
        return CatalogoSismico(self._datos[mascara].copy(), self._metadata)
    
    def filtrar_fechas(
        self,
        fecha_inicio: Optional[Union[str, datetime]] = None,
        fecha_fin: Optional[Union[str, datetime]] = None
    ) -> 'CatalogoSismico':
        """
        Filtra eventos por rango de fechas.
        
        Args:
            fecha_inicio: Fecha de inicio (str ISO o datetime)
            fecha_fin: Fecha de fin (str ISO o datetime)
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
        """
        datos = self._datos.copy()
        datos['_fecha_tmp'] = pd.to_datetime(datos['fecha'])
        
        mascara = pd.Series([True] * len(datos), index=datos.index)
        
        if fecha_inicio is not None:
            fecha_inicio = pd.to_datetime(fecha_inicio)
            mascara &= datos['_fecha_tmp'] >= fecha_inicio
        
        if fecha_fin is not None:
            fecha_fin = pd.to_datetime(fecha_fin)
            mascara &= datos['_fecha_tmp'] <= fecha_fin
        
        datos = datos.drop(columns=['_fecha_tmp'])
        
        return CatalogoSismico(datos[mascara].copy(), self._metadata)
    
    def filtrar_periodo(
        self, 
        fecha_inicio: str, 
        fecha_fin: str
    ) -> 'CatalogoSismico':
        """
        Alias para filtrar_fechas (compatibilidad con esd.py).
        """
        return self.filtrar_fechas(fecha_inicio, fecha_fin)
    
    def filtrar(
        self,
        condicion: Union[pd.Series, Callable[[pd.DataFrame], pd.Series]]
    ) -> 'CatalogoSismico':
        """
        Filtrado flexible con condición personalizada.
        
        Args:
            condicion: Serie booleana o función que retorna Serie booleana
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
            
        Example:
            >>> # Con Serie booleana
            >>> filtrado = catalogo.filtrar(catalogo['magnitud'] > 5)
            >>> 
            >>> # Con función
            >>> filtrado = catalogo.filtrar(
            ...     lambda df: (df['magnitud'] > 4) & (df['profundidad_km'] < 50)
            ... )
        """
        if callable(condicion):
            mascara = condicion(self._datos)
        else:
            mascara = condicion
        
        return CatalogoSismico(self._datos[mascara].copy(), self._metadata)
    
    # =========================================================================
    # MÉTODOS DE TRANSFORMACIÓN
    # =========================================================================
    
    def homogeneizar_magnitudes(
        self,
        tipo_destino: str = 'Mw',
        inplace: bool = False
    ) -> Optional['CatalogoSismico']:
        """
        Convierte todas las magnitudes a un tipo común (por defecto Mw).
        
        Args:
            tipo_destino: Tipo de magnitud destino ('Mw', 'ML', etc.)
            inplace: Si True, modifica el catálogo actual
            
        Returns:
            Nuevo CatalogoSismico si inplace=False, None si inplace=True
            
        Example:
            >>> catalogo.homogeneizar_magnitudes('Mw', inplace=True)
        """
        if inplace:
            datos = self._datos
        else:
            datos = self._datos.copy()
        
        # Verificar columna de tipo de magnitud
        if 'tipo_magnitud' not in datos.columns:
            warnings.warn("No hay columna 'tipo_magnitud', asumiendo magnitudes ya homogéneas")
            if inplace:
                return None
            return CatalogoSismico(datos, self._metadata)
        
        tipo_destino_lower = tipo_destino.lower()
        
        # Convertir cada magnitud
        for idx, row in datos.iterrows():
            tipo_origen = str(row.get('tipo_magnitud', 'M')).lower()
            
            if tipo_origen == tipo_destino_lower:
                continue
            
            key = (tipo_origen, tipo_destino_lower)
            
            if key in CONVERSIONES_MAGNITUD:
                datos.loc[idx, 'magnitud'] = CONVERSIONES_MAGNITUD[key](row['magnitud'])
                datos.loc[idx, 'tipo_magnitud'] = tipo_destino
            else:
                # Si no hay conversión disponible, mantener original
                pass
        
        if inplace:
            self._metadata.homogeneizado = True
            self._metadata.tipo_magnitud_homogeneizada = tipo_destino
            self._validado = False
            return None
        else:
            metadata = MetadataCatalogo(
                **{k: v for k, v in self._metadata.to_dict().items() if k not in ['homogeneizado', 'tipo_magnitud_homogeneizada']}
            )
            metadata.homogeneizado = True
            metadata.tipo_magnitud_homogeneizada = tipo_destino
            return CatalogoSismico(datos, metadata)
    
    def ordenar(
        self,
        por: Union[str, List[str]] = 'fecha',
        ascendente: bool = True,
        inplace: bool = False
    ) -> Optional['CatalogoSismico']:
        """
        Ordena el catálogo por una o más columnas.
        
        Args:
            por: Columna(s) para ordenar
            ascendente: Orden ascendente o descendente
            inplace: Si True, modifica el catálogo actual
            
        Returns:
            Nuevo CatalogoSismico si inplace=False
        """
        if inplace:
            self._datos = self._datos.sort_values(por, ascending=ascendente).reset_index(drop=True)
            return None
        else:
            datos = self._datos.sort_values(por, ascending=ascendente).reset_index(drop=True)
            return CatalogoSismico(datos, self._metadata)
    
    def copiar(self) -> 'CatalogoSismico':
        """
        Crea una copia profunda del catálogo.
        
        Returns:
            Copia del CatalogoSismico
        """
        return CatalogoSismico(
            self._datos.copy(),
            MetadataCatalogo(**self._metadata.to_dict())
        )
    
    # =========================================================================
    # MÉTODOS DE SALIDA
    # =========================================================================
    
    def resumen(self, detallado: bool = False) -> str:
        """
        Genera un resumen legible del catálogo.
        
        Args:
            detallado: Si True, incluye más estadísticas
            
        Returns:
            String con el resumen
        """
        lineas = [
            "=" * 50,
            "    RESUMEN DEL CATÁLOGO SÍSMICO",
            "=" * 50,
            f"Fuente: {self._metadata.fuente}",
        ]
        
        if self._metadata.region:
            lineas.append(f"Región: {self._metadata.region}")
        
        lineas.extend([
            f"Número de eventos: {self.n_eventos:,}",
            "",
        ])
        
        if self.rango_magnitudes:
            lineas.append(
                f"Magnitudes: {self.rango_magnitudes[0]:.1f} - {self.rango_magnitudes[1]:.1f}"
            )
        
        if self.rango_profundidades:
            lineas.append(
                f"Profundidades: {self.rango_profundidades[0]:.1f} - {self.rango_profundidades[1]:.1f} km"
            )
        
        if self.rango_fechas:
            lineas.extend([
                "",
                f"Período: {self.rango_fechas[0].strftime('%Y-%m-%d')} a {self.rango_fechas[1].strftime('%Y-%m-%d')}"
            ])
        
        if self.extension_espacial:
            ext = self.extension_espacial
            lineas.extend([
                "",
                "Extensión espacial:",
                f"  Latitud:  {ext['latitud'][0]:.2f}° a {ext['latitud'][1]:.2f}°",
                f"  Longitud: {ext['longitud'][0]:.2f}° a {ext['longitud'][1]:.2f}°",
            ])
        
        if detallado and 'tipo_magnitud' in self._datos.columns:
            tipos = self._datos['tipo_magnitud'].value_counts()
            lineas.extend([
                "",
                "Tipos de magnitud:",
            ])
            for tipo, count in tipos.items():
                lineas.append(f"  {tipo}: {count:,}")
        
        if self._metadata.homogeneizado:
            lineas.append(f"\n✓ Magnitudes homogeneizadas a {self._metadata.tipo_magnitud_homogeneizada}")
        
        if self._metadata.declustered:
            lineas.append(f"✓ Declustering aplicado ({self._metadata.metodo_declustering})")
        
        lineas.append("=" * 50)
        
        return "\n".join(lineas)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Retorna copia del DataFrame interno."""
        return self._datos.copy()
    
    def to_csv(
        self,
        ruta: Union[str, Path],
        incluir_metadata: bool = False,
        **kwargs
    ) -> None:
        """
        Exporta el catálogo a archivo CSV.
        
        Args:
            ruta: Ruta del archivo de salida
            incluir_metadata: Si True, guarda metadata en archivo separado
            **kwargs: Argumentos adicionales para DataFrame.to_csv
        """
        ruta = Path(ruta)
        self._datos.to_csv(ruta, index=False, **kwargs)
        logger.info(f"Catálogo exportado a {ruta}")
        
        if incluir_metadata:
            import json
            ruta_meta = ruta.with_suffix('.meta.json')
            with open(ruta_meta, 'w', encoding='utf-8') as f:
                json.dump(self._metadata.to_dict(), f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Metadatos exportados a {ruta_meta}")
    
    def to_excel(
        self,
        ruta: Union[str, Path],
        hoja: str = 'Eventos',
        **kwargs
    ) -> None:
        """
        Exporta el catálogo a archivo Excel.
        
        Args:
            ruta: Ruta del archivo de salida
            hoja: Nombre de la hoja
            **kwargs: Argumentos adicionales para DataFrame.to_excel
        """
        ruta = Path(ruta)
        self._datos.to_excel(ruta, sheet_name=hoja, index=False, **kwargs)
        logger.info(f"Catálogo exportado a {ruta}")
    
    def to_geojson(
        self,
        ruta: Union[str, Path],
        propiedades: Optional[List[str]] = None
    ) -> None:
        """
        Exporta el catálogo a GeoJSON.
        
        Args:
            ruta: Ruta del archivo de salida
            propiedades: Lista de columnas a incluir como propiedades
        """
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            raise ImportError("Se requiere geopandas para exportar a GeoJSON")
        
        if propiedades is None:
            propiedades = [c for c in self._datos.columns 
                          if c not in ['latitud', 'longitud']]
        
        geometria = [
            Point(lon, lat) 
            for lon, lat in zip(self._datos['longitud'], self._datos['latitud'])
        ]
        
        gdf = gpd.GeoDataFrame(
            self._datos[propiedades],
            geometry=geometria,
            crs='EPSG:4326'
        )
        
        gdf.to_file(ruta, driver='GeoJSON')
        logger.info(f"Catálogo exportado a {ruta}")
    
    def head(self, n: int = 5) -> pd.DataFrame:
        """Retorna los primeros n eventos."""
        return self._datos.head(n)
    
    def tail(self, n: int = 5) -> pd.DataFrame:
        """Retorna los últimos n eventos."""
        return self._datos.tail(n)
    
    def sample(self, n: int = 5, random_state: Optional[int] = None) -> pd.DataFrame:
        """Retorna una muestra aleatoria de n eventos."""
        return self._datos.sample(n=min(n, len(self._datos)), random_state=random_state)
    
    def describe(self) -> pd.DataFrame:
        """Retorna estadísticas descriptivas de las columnas numéricas."""
        return self._datos.describe()


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def cargar_catalogo(
    ruta: Union[str, Path],
    formato: str = 'auto',
    **kwargs
) -> CatalogoSismico:
    """
    Función de conveniencia para cargar catálogos.
    
    Detecta automáticamente el formato basándose en la extensión
    y el contenido del archivo.
    
    Args:
        ruta: Ruta al archivo
        formato: Formato del archivo ('auto' para detección automática)
        **kwargs: Argumentos adicionales
        
    Returns:
        CatalogoSismico cargado
    """
    ruta = Path(ruta)
    
    if formato == 'auto':
        # Detectar por extensión
        ext = ruta.suffix.lower()
        if ext in ['.xlsx', '.xls']:
            return CatalogoSismico.desde_excel(ruta, **kwargs)
        elif ext == '.csv':
            # Intentar detectar formato por contenido
            with open(ruta, 'r', encoding='utf-8') as f:
                header = f.readline().lower()
            
            if 'fecha' in header and 'latitud' in header:
                formato = 'ssn'
            elif 'time' in header and 'latitude' in header:
                formato = 'usgs'
            else:
                formato = 'custom'
            
            return CatalogoSismico.desde_csv(ruta, formato=formato, **kwargs)
        else:
            return CatalogoSismico.desde_csv(ruta, formato='custom', **kwargs)
    else:
        if ruta.suffix.lower() in ['.xlsx', '.xls']:
            return CatalogoSismico.desde_excel(ruta, formato=formato, **kwargs)
        else:
            return CatalogoSismico.desde_csv(ruta, formato=formato, **kwargs)


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Crear datos de ejemplo
    np.random.seed(42)
    n_eventos = 500
    
    datos_ejemplo = pd.DataFrame({
        'fecha': pd.date_range('2020-01-01', periods=n_eventos, freq='12h'),
        'latitud': np.random.uniform(18.5, 20.5, n_eventos),
        'longitud': np.random.uniform(-104.5, -103.0, n_eventos),
        'profundidad_km': np.random.exponential(30, n_eventos),
        'magnitud': np.random.exponential(1.5, n_eventos) + 2.0,
        'tipo_magnitud': np.random.choice(['Mc', 'Ml', 'Mw'], n_eventos, p=[0.6, 0.3, 0.1]),
    })
    
    # Crear catálogo
    catalogo = CatalogoSismico.desde_dataframe(datos_ejemplo, fuente='ejemplo')
    
    # Validar
    resultado = catalogo.validar()
    print(resultado)
    
    # Mostrar resumen
    print(catalogo.resumen(detallado=True))
    
    # Filtrar
    catalogo_filtrado = (
        catalogo
        .filtrar_magnitud(mag_min=3.0)
        .filtrar_profundidad(prof_max=50)
    )
    
    print(f"\nDespués de filtrar: {len(catalogo_filtrado)} eventos")
    print(catalogo_filtrado.resumen())
    
    # Homogeneizar magnitudes
    catalogo_mw = catalogo.homogeneizar_magnitudes('Mw')
    print(f"\nMagnitudes homogeneizadas: {catalogo_mw.metadata.homogeneizado}")
