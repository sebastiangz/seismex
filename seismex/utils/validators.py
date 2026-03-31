"""
SEISMEX Utils - Validadores de Datos
====================================

Funciones para validar y limpiar datos sísmicos.

Incluye:
- Validación de coordenadas
- Validación de magnitudes y profundidades
- Detección de outliers
- Reporte de calidad de catálogos
- Limpieza de datos

Ejemplo de uso:
    >>> from seismex.utils.validators import validar_catalogo_completo
    >>> reporte = validar_catalogo_completo(catalogo)
    >>> print(reporte)

Autor: SEISMEX Team
Licencia: MIT
"""

from __future__ import annotations

import warnings
import logging
from dataclasses import dataclass, field
from typing import (
    Optional, List, Dict, Any, Union, Tuple,
    Callable, Literal
)
from datetime import datetime

import numpy as np
import pandas as pd

from seismex.utils.constants import (
    MEXICO_LAT_MIN, MEXICO_LAT_MAX,
    MEXICO_LON_MIN, MEXICO_LON_MAX
)

logger = logging.getLogger(__name__)

# =============================================================================
# DATACLASSES PARA REPORTES
# =============================================================================

@dataclass
class ProblemaValidacion:
    """Representa un problema encontrado durante la validación."""
    tipo: Literal['error', 'advertencia', 'info']
    mensaje: str
    columna: Optional[str] = None
    indices: Optional[List[int]] = None
    n_afectados: int = 0


@dataclass
class ReporteCalidad:
    """
    Reporte completo de calidad de un catálogo sísmico.
    
    Attributes:
        n_eventos: Número total de eventos
        n_validos: Eventos que pasan todas las validaciones
        pct_coordenadas_validas: Porcentaje de coordenadas válidas
        pct_magnitudes_validas: Porcentaje de magnitudes válidas
        pct_profundidades_validas: Porcentaje de profundidades válidas
        pct_fechas_validas: Porcentaje de fechas válidas
        n_duplicados: Número de duplicados detectados
        n_outliers: Número de outliers potenciales
        problemas: Lista de problemas encontrados
        estadisticas: Diccionario con estadísticas adicionales
    """
    n_eventos: int
    n_validos: int = 0
    pct_coordenadas_validas: float = 0.0
    pct_magnitudes_validas: float = 0.0
    pct_profundidades_validas: float = 0.0
    pct_fechas_validas: float = 0.0
    n_duplicados: int = 0
    n_outliers: int = 0
    problemas: List[ProblemaValidacion] = field(default_factory=list)
    estadisticas: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def puntuacion(self) -> float:
        """Puntuación de calidad (0-100)."""
        if self.n_eventos == 0:
            return 0.0
        
        pesos = {
            'coordenadas': 0.3,
            'magnitudes': 0.25,
            'profundidades': 0.2,
            'fechas': 0.15,
            'duplicados': 0.1
        }
        
        pct_sin_duplicados = 100 * (1 - self.n_duplicados / self.n_eventos)
        
        score = (
            pesos['coordenadas'] * self.pct_coordenadas_validas +
            pesos['magnitudes'] * self.pct_magnitudes_validas +
            pesos['profundidades'] * self.pct_profundidades_validas +
            pesos['fechas'] * self.pct_fechas_validas +
            pesos['duplicados'] * pct_sin_duplicados
        )
        
        return round(score, 1)
    
    @property
    def es_valido(self) -> bool:
        """El catálogo es usable si tiene puntuación >= 70."""
        return self.puntuacion >= 70
    
    def __str__(self) -> str:
        lineas = [
            "═" * 50,
            "REPORTE DE CALIDAD DEL CATÁLOGO",
            "═" * 50,
            f"Total eventos: {self.n_eventos:,}",
            f"Eventos válidos: {self.n_validos:,} ({100*self.n_validos/self.n_eventos:.1f}%)" if self.n_eventos > 0 else "Eventos válidos: 0",
            "",
            "─" * 50,
            "VALIDACIONES",
            "─" * 50,
            f"Coordenadas válidas: {self.pct_coordenadas_validas:.1f}%",
            f"Magnitudes válidas: {self.pct_magnitudes_validas:.1f}%",
            f"Profundidades válidas: {self.pct_profundidades_validas:.1f}%",
            f"Fechas válidas: {self.pct_fechas_validas:.1f}%",
            "",
            f"Duplicados detectados: {self.n_duplicados}",
            f"Outliers potenciales: {self.n_outliers}",
            "",
            "─" * 50,
            f"PUNTUACIÓN DE CALIDAD: {self.puntuacion}/100",
            f"Estado: {'✅ VÁLIDO' if self.es_valido else '⚠️ REVISAR'}",
            "═" * 50,
        ]
        
        if self.problemas:
            lineas.append("")
            lineas.append("PROBLEMAS ENCONTRADOS:")
            for p in self.problemas[:10]:  # Mostrar máximo 10
                icono = "❌" if p.tipo == 'error' else "⚠️" if p.tipo == 'advertencia' else "ℹ️"
                lineas.append(f"  {icono} {p.mensaje}")
            if len(self.problemas) > 10:
                lineas.append(f"  ... y {len(self.problemas) - 10} más")
        
        return "\n".join(lineas)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el reporte a diccionario."""
        return {
            'n_eventos': self.n_eventos,
            'n_validos': self.n_validos,
            'pct_coordenadas_validas': self.pct_coordenadas_validas,
            'pct_magnitudes_validas': self.pct_magnitudes_validas,
            'pct_profundidades_validas': self.pct_profundidades_validas,
            'pct_fechas_validas': self.pct_fechas_validas,
            'n_duplicados': self.n_duplicados,
            'n_outliers': self.n_outliers,
            'puntuacion': self.puntuacion,
            'es_valido': self.es_valido,
            'problemas': [
                {'tipo': p.tipo, 'mensaje': p.mensaje, 'columna': p.columna, 'n_afectados': p.n_afectados}
                for p in self.problemas
            ],
            'estadisticas': self.estadisticas
        }


# =============================================================================
# VALIDACIÓN DE COORDENADAS
# =============================================================================

def validar_coordenadas(
    lat: float,
    lon: float,
    lat_min: float = -90.0,
    lat_max: float = 90.0,
    lon_min: float = -180.0,
    lon_max: float = 180.0
) -> bool:
    """
    Valida que las coordenadas estén dentro de rangos válidos.
    
    Args:
        lat: Latitud a validar
        lon: Longitud a validar
        lat_min, lat_max: Rango de latitud permitido
        lon_min, lon_max: Rango de longitud permitido
        
    Returns:
        True si las coordenadas son válidas
    """
    if pd.isna(lat) or pd.isna(lon):
        return False
    
    return (lat_min <= lat <= lat_max) and (lon_min <= lon <= lon_max)


def validar_coordenadas_mexico(
    lat: float,
    lon: float,
    buffer_grados: float = 1.0
) -> bool:
    """
    Valida que las coordenadas estén dentro de México (con buffer).
    
    Args:
        lat, lon: Coordenadas a validar
        buffer_grados: Margen adicional alrededor de México
        
    Returns:
        True si está dentro de México (± buffer)
    """
    return validar_coordenadas(
        lat, lon,
        lat_min=MEXICO_LAT_MIN - buffer_grados,
        lat_max=MEXICO_LAT_MAX + buffer_grados,
        lon_min=MEXICO_LON_MIN - buffer_grados,
        lon_max=MEXICO_LON_MAX + buffer_grados
    )


def validar_coordenadas_array(
    lats: np.ndarray,
    lons: np.ndarray,
    lat_min: float = -90.0,
    lat_max: float = 90.0,
    lon_min: float = -180.0,
    lon_max: float = 180.0
) -> np.ndarray:
    """
    Versión vectorizada de validación de coordenadas.
    
    Returns:
        Array booleano con True para coordenadas válidas
    """
    lats = np.asarray(lats)
    lons = np.asarray(lons)
    
    validos = (
        ~np.isnan(lats) & ~np.isnan(lons) &
        (lats >= lat_min) & (lats <= lat_max) &
        (lons >= lon_min) & (lons <= lon_max)
    )
    
    return validos


# =============================================================================
# VALIDACIÓN DE MAGNITUD
# =============================================================================

def validar_magnitud(
    magnitud: float,
    mag_min: float = -2.0,
    mag_max: float = 10.0
) -> bool:
    """
    Valida que una magnitud esté en rango razonable.
    
    Args:
        magnitud: Valor de magnitud
        mag_min: Magnitud mínima permitida
        mag_max: Magnitud máxima permitida
        
    Returns:
        True si la magnitud es válida
    """
    if pd.isna(magnitud):
        return False
    
    return mag_min <= magnitud <= mag_max


def validar_magnitud_array(
    magnitudes: np.ndarray,
    mag_min: float = -2.0,
    mag_max: float = 10.0
) -> np.ndarray:
    """
    Versión vectorizada de validación de magnitudes.
    """
    magnitudes = np.asarray(magnitudes)
    return ~np.isnan(magnitudes) & (magnitudes >= mag_min) & (magnitudes <= mag_max)


# =============================================================================
# VALIDACIÓN DE PROFUNDIDAD
# =============================================================================

def validar_profundidad(
    profundidad: float,
    prof_min: float = 0.0,
    prof_max: float = 700.0
) -> bool:
    """
    Valida que una profundidad esté en rango razonable.
    
    La profundidad máxima de sismos en la Tierra es ~700 km
    (zona de transición del manto).
    
    Args:
        profundidad: Profundidad en km
        prof_min: Profundidad mínima permitida
        prof_max: Profundidad máxima permitida
        
    Returns:
        True si la profundidad es válida
    """
    if pd.isna(profundidad):
        return False
    
    return prof_min <= profundidad <= prof_max


def validar_profundidad_array(
    profundidades: np.ndarray,
    prof_min: float = 0.0,
    prof_max: float = 700.0
) -> np.ndarray:
    """
    Versión vectorizada de validación de profundidades.
    """
    profundidades = np.asarray(profundidades)
    return ~np.isnan(profundidades) & (profundidades >= prof_min) & (profundidades <= prof_max)


# =============================================================================
# VALIDACIÓN DE FECHAS
# =============================================================================

def validar_fecha(
    fecha: Any,
    fecha_min: Optional[datetime] = None,
    fecha_max: Optional[datetime] = None
) -> bool:
    """
    Valida que una fecha sea válida y esté en rango.
    
    Args:
        fecha: Fecha a validar (datetime, Timestamp, o string)
        fecha_min: Fecha mínima permitida
        fecha_max: Fecha máxima permitida (default: ahora)
        
    Returns:
        True si la fecha es válida
    """
    if pd.isna(fecha):
        return False
    
    try:
        fecha_dt = pd.to_datetime(fecha)
        
        if fecha_min and fecha_dt < pd.to_datetime(fecha_min):
            return False
        
        if fecha_max:
            if fecha_dt > pd.to_datetime(fecha_max):
                return False
        else:
            # No permitir fechas futuras
            if fecha_dt > pd.Timestamp.now():
                return False
        
        return True
    except Exception:
        return False


def validar_fechas_array(
    fechas: pd.Series,
    fecha_min: Optional[datetime] = None,
    fecha_max: Optional[datetime] = None
) -> np.ndarray:
    """
    Versión vectorizada de validación de fechas.
    """
    # Convertir a datetime
    fechas_dt = pd.to_datetime(fechas, errors='coerce')
    
    validos = ~fechas_dt.isna()
    
    if fecha_min:
        validos &= fechas_dt >= pd.to_datetime(fecha_min)
    
    if fecha_max:
        validos &= fechas_dt <= pd.to_datetime(fecha_max)
    else:
        validos &= fechas_dt <= pd.Timestamp.now()
    
    return validos.values


# =============================================================================
# DETECCIÓN DE DUPLICADOS
# =============================================================================

def detectar_duplicados(
    df: pd.DataFrame,
    tolerancia_km: float = 50.0,
    tolerancia_seg: float = 60.0,
    columna_lat: str = 'latitud',
    columna_lon: str = 'longitud',
    columna_fecha: str = 'fecha'
) -> np.ndarray:
    """
    Detecta eventos duplicados por proximidad espacial y temporal.
    
    Args:
        df: DataFrame con eventos
        tolerancia_km: Distancia máxima para considerar duplicado (km)
        tolerancia_seg: Diferencia temporal máxima (segundos)
        columna_lat, columna_lon: Nombres de columnas de coordenadas
        columna_fecha: Nombre de columna de fecha
        
    Returns:
        Array booleano donde True indica un duplicado
    """
    n = len(df)
    es_duplicado = np.zeros(n, dtype=bool)
    
    if n < 2:
        return es_duplicado
    
    # Ordenar por fecha
    df_sorted = df.sort_values(columna_fecha).reset_index(drop=True)
    
    # Convertir a arrays
    lats = df_sorted[columna_lat].values
    lons = df_sorted[columna_lon].values
    fechas = pd.to_datetime(df_sorted[columna_fecha])
    
    # Factor de conversión aproximado
    deg_to_km = 111.0
    tol_deg = tolerancia_km / deg_to_km
    
    for i in range(n):
        if es_duplicado[i]:
            continue
        
        for j in range(i + 1, n):
            # Verificar tiempo primero (más rápido)
            dt = abs((fechas.iloc[j] - fechas.iloc[i]).total_seconds())
            if dt > tolerancia_seg:
                break  # Ya ordenado, no hay más candidatos
            
            # Verificar distancia aproximada
            dlat = abs(lats[j] - lats[i])
            dlon = abs(lons[j] - lons[i])
            
            if dlat < tol_deg and dlon < tol_deg:
                dist_aprox = np.sqrt(dlat**2 + dlon**2) * deg_to_km
                if dist_aprox < tolerancia_km:
                    es_duplicado[j] = True
    
    return es_duplicado


def contar_duplicados(
    df: pd.DataFrame,
    **kwargs
) -> int:
    """
    Cuenta el número de duplicados en un DataFrame.
    """
    return np.sum(detectar_duplicados(df, **kwargs))


# =============================================================================
# DETECCIÓN DE OUTLIERS
# =============================================================================

def detectar_outliers_iqr(
    valores: np.ndarray,
    factor: float = 1.5
) -> np.ndarray:
    """
    Detecta outliers usando el método del rango intercuartil (IQR).
    
    Args:
        valores: Array de valores numéricos
        factor: Multiplicador del IQR (1.5 = outliers moderados, 3.0 = extremos)
        
    Returns:
        Array booleano donde True indica un outlier
    """
    valores = np.asarray(valores)
    
    # Ignorar NaN para calcular cuartiles
    valores_validos = valores[~np.isnan(valores)]
    
    if len(valores_validos) < 4:
        return np.zeros(len(valores), dtype=bool)
    
    q1 = np.percentile(valores_validos, 25)
    q3 = np.percentile(valores_validos, 75)
    iqr = q3 - q1
    
    limite_inferior = q1 - factor * iqr
    limite_superior = q3 + factor * iqr
    
    es_outlier = (valores < limite_inferior) | (valores > limite_superior)
    
    return es_outlier


def detectar_outliers_zscore(
    valores: np.ndarray,
    umbral: float = 3.0
) -> np.ndarray:
    """
    Detecta outliers usando Z-score.
    
    Args:
        valores: Array de valores numéricos
        umbral: Número de desviaciones estándar para considerar outlier
        
    Returns:
        Array booleano donde True indica un outlier
    """
    valores = np.asarray(valores)
    
    # Calcular media y std ignorando NaN
    media = np.nanmean(valores)
    std = np.nanstd(valores)
    
    if std == 0:
        return np.zeros(len(valores), dtype=bool)
    
    zscore = np.abs((valores - media) / std)
    
    return zscore > umbral


def detectar_outliers(
    df: pd.DataFrame,
    columnas: Optional[List[str]] = None,
    metodo: Literal['iqr', 'zscore'] = 'iqr',
    **kwargs
) -> pd.DataFrame:
    """
    Detecta outliers en múltiples columnas de un DataFrame.
    
    Args:
        df: DataFrame con datos
        columnas: Lista de columnas a analizar (default: numéricas)
        metodo: 'iqr' o 'zscore'
        **kwargs: Argumentos para el método de detección
        
    Returns:
        DataFrame con columnas booleanas indicando outliers
    """
    if columnas is None:
        columnas = df.select_dtypes(include=[np.number]).columns.tolist()
    
    resultado = pd.DataFrame(index=df.index)
    
    detector = detectar_outliers_iqr if metodo == 'iqr' else detectar_outliers_zscore
    
    for col in columnas:
        if col in df.columns:
            resultado[f'{col}_outlier'] = detector(df[col].values, **kwargs)
    
    return resultado


# =============================================================================
# VALIDACIÓN COMPLETA DE CATÁLOGO
# =============================================================================

def validar_catalogo_completo(
    df: pd.DataFrame,
    columna_lat: str = 'latitud',
    columna_lon: str = 'longitud',
    columna_mag: str = 'magnitud',
    columna_prof: str = 'profundidad_km',
    columna_fecha: str = 'fecha',
    region: str = 'global',
    detectar_dups: bool = True,
    detectar_outs: bool = True
) -> ReporteCalidad:
    """
    Realiza validación completa de un catálogo sísmico.
    
    Args:
        df: DataFrame con catálogo
        columna_lat, columna_lon: Columnas de coordenadas
        columna_mag: Columna de magnitud
        columna_prof: Columna de profundidad
        columna_fecha: Columna de fecha
        region: 'global' o 'mexico' (ajusta validación de coordenadas)
        detectar_dups: Si detectar duplicados
        detectar_outs: Si detectar outliers
        
    Returns:
        ReporteCalidad con resultados de validación
    """
    n_eventos = len(df)
    problemas = []
    estadisticas = {}
    
    if n_eventos == 0:
        return ReporteCalidad(
            n_eventos=0,
            problemas=[ProblemaValidacion('error', 'Catálogo vacío')]
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Validar coordenadas
    # ─────────────────────────────────────────────────────────────────────────
    if columna_lat in df.columns and columna_lon in df.columns:
        if region == 'mexico':
            coord_validas = validar_coordenadas_array(
                df[columna_lat].values,
                df[columna_lon].values,
                lat_min=MEXICO_LAT_MIN - 1,
                lat_max=MEXICO_LAT_MAX + 1,
                lon_min=MEXICO_LON_MIN - 1,
                lon_max=MEXICO_LON_MAX + 1
            )
        else:
            coord_validas = validar_coordenadas_array(
                df[columna_lat].values,
                df[columna_lon].values
            )
        
        pct_coord = 100 * np.sum(coord_validas) / n_eventos
        n_coord_invalidas = n_eventos - np.sum(coord_validas)
        
        if n_coord_invalidas > 0:
            problemas.append(ProblemaValidacion(
                'advertencia' if pct_coord > 90 else 'error',
                f'{n_coord_invalidas} eventos con coordenadas inválidas',
                columna=columna_lat,
                n_afectados=n_coord_invalidas
            ))
        
        # Estadísticas
        estadisticas['lat_min'] = float(df[columna_lat].min())
        estadisticas['lat_max'] = float(df[columna_lat].max())
        estadisticas['lon_min'] = float(df[columna_lon].min())
        estadisticas['lon_max'] = float(df[columna_lon].max())
    else:
        pct_coord = 0.0
        problemas.append(ProblemaValidacion(
            'error',
            'Columnas de coordenadas no encontradas',
            n_afectados=n_eventos
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Validar magnitudes
    # ─────────────────────────────────────────────────────────────────────────
    if columna_mag in df.columns:
        mag_validas = validar_magnitud_array(df[columna_mag].values)
        pct_mag = 100 * np.sum(mag_validas) / n_eventos
        n_mag_invalidas = n_eventos - np.sum(mag_validas)
        
        if n_mag_invalidas > 0:
            problemas.append(ProblemaValidacion(
                'advertencia' if pct_mag > 95 else 'error',
                f'{n_mag_invalidas} eventos con magnitud inválida',
                columna=columna_mag,
                n_afectados=n_mag_invalidas
            ))
        
        estadisticas['mag_min'] = float(df[columna_mag].min())
        estadisticas['mag_max'] = float(df[columna_mag].max())
        estadisticas['mag_media'] = float(df[columna_mag].mean())
    else:
        pct_mag = 0.0
        problemas.append(ProblemaValidacion(
            'error',
            'Columna de magnitud no encontrada',
            n_afectados=n_eventos
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Validar profundidades
    # ─────────────────────────────────────────────────────────────────────────
    if columna_prof in df.columns:
        prof_validas = validar_profundidad_array(df[columna_prof].values)
        pct_prof = 100 * np.sum(prof_validas) / n_eventos
        n_prof_invalidas = n_eventos - np.sum(prof_validas)
        
        if n_prof_invalidas > 0:
            problemas.append(ProblemaValidacion(
                'advertencia' if pct_prof > 90 else 'error',
                f'{n_prof_invalidas} eventos con profundidad inválida',
                columna=columna_prof,
                n_afectados=n_prof_invalidas
            ))
        
        estadisticas['prof_min'] = float(df[columna_prof].min())
        estadisticas['prof_max'] = float(df[columna_prof].max())
        estadisticas['prof_media'] = float(df[columna_prof].mean())
    else:
        pct_prof = 0.0
        problemas.append(ProblemaValidacion(
            'advertencia',
            'Columna de profundidad no encontrada',
            n_afectados=n_eventos
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Validar fechas
    # ─────────────────────────────────────────────────────────────────────────
    if columna_fecha in df.columns:
        fechas_validas = validar_fechas_array(df[columna_fecha])
        pct_fechas = 100 * np.sum(fechas_validas) / n_eventos
        n_fechas_invalidas = n_eventos - np.sum(fechas_validas)
        
        if n_fechas_invalidas > 0:
            problemas.append(ProblemaValidacion(
                'advertencia' if pct_fechas > 95 else 'error',
                f'{n_fechas_invalidas} eventos con fecha inválida',
                columna=columna_fecha,
                n_afectados=n_fechas_invalidas
            ))
        
        fechas_dt = pd.to_datetime(df[columna_fecha], errors='coerce')
        estadisticas['fecha_min'] = str(fechas_dt.min())
        estadisticas['fecha_max'] = str(fechas_dt.max())
    else:
        pct_fechas = 0.0
        problemas.append(ProblemaValidacion(
            'error',
            'Columna de fecha no encontrada',
            n_afectados=n_eventos
        ))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Detectar duplicados
    # ─────────────────────────────────────────────────────────────────────────
    if detectar_dups and columna_lat in df.columns and columna_fecha in df.columns:
        try:
            n_duplicados = contar_duplicados(
                df,
                columna_lat=columna_lat,
                columna_lon=columna_lon,
                columna_fecha=columna_fecha
            )
            
            if n_duplicados > 0:
                problemas.append(ProblemaValidacion(
                    'advertencia',
                    f'{n_duplicados} posibles eventos duplicados',
                    n_afectados=n_duplicados
                ))
        except Exception as e:
            n_duplicados = 0
            logger.warning(f"Error detectando duplicados: {e}")
    else:
        n_duplicados = 0
    
    # ─────────────────────────────────────────────────────────────────────────
    # Detectar outliers
    # ─────────────────────────────────────────────────────────────────────────
    if detectar_outs and columna_mag in df.columns:
        try:
            outliers_mag = detectar_outliers_iqr(df[columna_mag].values)
            n_outliers = np.sum(outliers_mag)
            
            if n_outliers > 0:
                problemas.append(ProblemaValidacion(
                    'info',
                    f'{n_outliers} outliers de magnitud detectados',
                    columna=columna_mag,
                    n_afectados=n_outliers
                ))
        except Exception:
            n_outliers = 0
    else:
        n_outliers = 0
    
    # ─────────────────────────────────────────────────────────────────────────
    # Calcular eventos válidos
    # ─────────────────────────────────────────────────────────────────────────
    try:
        todos_validos = np.ones(n_eventos, dtype=bool)
        
        if columna_lat in df.columns:
            todos_validos &= validar_coordenadas_array(
                df[columna_lat].values, df[columna_lon].values
            )
        if columna_mag in df.columns:
            todos_validos &= validar_magnitud_array(df[columna_mag].values)
        if columna_fecha in df.columns:
            todos_validos &= validar_fechas_array(df[columna_fecha])
        
        n_validos = np.sum(todos_validos)
    except Exception:
        n_validos = 0
    
    # ─────────────────────────────────────────────────────────────────────────
    # Crear reporte
    # ─────────────────────────────────────────────────────────────────────────
    return ReporteCalidad(
        n_eventos=n_eventos,
        n_validos=n_validos,
        pct_coordenadas_validas=pct_coord,
        pct_magnitudes_validas=pct_mag,
        pct_profundidades_validas=pct_prof,
        pct_fechas_validas=pct_fechas,
        n_duplicados=n_duplicados,
        n_outliers=n_outliers,
        problemas=problemas,
        estadisticas=estadisticas
    )


# Alias para compatibilidad
reportar_calidad = validar_catalogo_completo


# =============================================================================
# FUNCIONES DE LIMPIEZA
# =============================================================================

def limpiar_catalogo(
    df: pd.DataFrame,
    remover_nulos: bool = True,
    remover_duplicados: bool = False,
    remover_outliers: bool = False,
    columnas_requeridas: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Limpia un catálogo sísmico removiendo filas problemáticas.
    
    Args:
        df: DataFrame a limpiar
        remover_nulos: Remover filas con valores nulos en columnas clave
        remover_duplicados: Remover duplicados espaciotemporales
        remover_outliers: Remover outliers de magnitud
        columnas_requeridas: Columnas que deben tener valores
        
    Returns:
        DataFrame limpio
    """
    df_limpio = df.copy()
    n_original = len(df_limpio)
    
    # Remover nulos en columnas requeridas
    if remover_nulos:
        if columnas_requeridas is None:
            columnas_requeridas = ['latitud', 'longitud', 'magnitud', 'fecha']
        
        cols_existentes = [c for c in columnas_requeridas if c in df_limpio.columns]
        if cols_existentes:
            df_limpio = df_limpio.dropna(subset=cols_existentes)
    
    # Remover duplicados
    if remover_duplicados:
        duplicados = detectar_duplicados(df_limpio)
        df_limpio = df_limpio[~duplicados]
    
    # Remover outliers
    if remover_outliers and 'magnitud' in df_limpio.columns:
        outliers = detectar_outliers_iqr(df_limpio['magnitud'].values, factor=3.0)
        df_limpio = df_limpio[~outliers]
    
    n_final = len(df_limpio)
    logger.info(f"Limpieza: {n_original} → {n_final} eventos ({n_original - n_final} removidos)")
    
    return df_limpio.reset_index(drop=True)


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("SEISMEX Utils - Ejemplos de uso de validators.py")
    print("=" * 60)
    
    # Crear datos de ejemplo con algunos problemas
    np.random.seed(42)
    n = 100
    
    datos = pd.DataFrame({
        'fecha': pd.date_range('2024-01-01', periods=n, freq='12h'),
        'latitud': np.concatenate([
            np.random.uniform(18.5, 20.5, n-5),
            [np.nan, 200, -95, 19.5, 19.5]  # Algunos inválidos
        ]),
        'longitud': np.concatenate([
            np.random.uniform(-104.5, -103.0, n-5),
            [-103.5, -103.5, -103.5, np.nan, -103.5]
        ]),
        'profundidad_km': np.concatenate([
            np.random.exponential(30, n-3),
            [-10, 800, np.nan]  # Algunos inválidos
        ]),
        'magnitud': np.concatenate([
            np.random.exponential(1.5, n-2) + 2.0,
            [15, -5]  # Outliers
        ])
    })
    
    print("\n--- Validación individual ---")
    print(f"validar_coordenadas(19.2, -103.7): {validar_coordenadas(19.2, -103.7)}")
    print(f"validar_coordenadas(200, -103.7): {validar_coordenadas(200, -103.7)}")
    print(f"validar_magnitud(4.5): {validar_magnitud(4.5)}")
    print(f"validar_magnitud(15): {validar_magnitud(15)}")
    
    print("\n--- Reporte de calidad ---")
    reporte = validar_catalogo_completo(datos, region='mexico')
    print(reporte)
    
    print("\n--- Limpieza ---")
    datos_limpio = limpiar_catalogo(datos, remover_nulos=True, remover_outliers=True)
    print(f"Eventos después de limpieza: {len(datos_limpio)}")
    
    print("\n✓ Todos los ejemplos ejecutados correctamente")
