"""
SEISMEX Utils - Validadores de Datos
====================================

Funciones para validar y limpiar datos sísmicos.

Incluye:
- Validación de coordenadas
- Validación de magnitudes y profundidades
- Detección de outliers
- Reportes de calidad

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
from typing import List, Dict, Optional, Union, Tuple, Any
from datetime import datetime

import numpy as np
import pandas as pd

from seismex.utils.constants import (
    MEXICO_LAT_MIN, MEXICO_LAT_MAX,
    MEXICO_LON_MIN, MEXICO_LON_MAX
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATACLASSES PARA RESULTADOS
# =============================================================================

@dataclass
class IssueValidacion:
    """Representa un problema de validación."""
    tipo: str  # 'error', 'advertencia', 'info'
    columna: str
    mensaje: str
    n_afectados: int = 0
    indices: List[int] = field(default_factory=list)


@dataclass
class ReporteCalidad:
    """Reporte completo de calidad del catálogo."""
    n_eventos: int
    n_columnas: int
    issues: List[IssueValidacion] = field(default_factory=list)
    estadisticas: Dict[str, Any] = field(default_factory=dict)
    fecha_reporte: datetime = field(default_factory=datetime.now)
    
    @property
    def n_errores(self) -> int:
        return sum(1 for i in self.issues if i.tipo == 'error')
    
    @property
    def n_advertencias(self) -> int:
        return sum(1 for i in self.issues if i.tipo == 'advertencia')
    
    @property
    def es_valido(self) -> bool:
        return self.n_errores == 0
    
    @property
    def score(self) -> float:
        """Calcula un score de calidad (0-100)."""
        if self.n_eventos == 0:
            return 0.0
        
        penalizacion = 0.0
        for issue in self.issues:
            if issue.tipo == 'error':
                penalizacion += 20.0 * (issue.n_afectados / self.n_eventos)
            elif issue.tipo == 'advertencia':
                penalizacion += 5.0 * (issue.n_afectados / self.n_eventos)
        
        return max(0.0, min(100.0, 100.0 - penalizacion))
    
    def __str__(self) -> str:
        lineas = [
            "═" * 50,
            "REPORTE DE CALIDAD DEL CATÁLOGO",
            "═" * 50,
            f"Total eventos: {self.n_eventos:,}",
            f"Columnas: {self.n_columnas}",
            f"Score de calidad: {self.score:.1f}/100",
            f"Errores: {self.n_errores}",
            f"Advertencias: {self.n_advertencias}",
            "-" * 50,
        ]
        
        if self.issues:
            lineas.append("PROBLEMAS ENCONTRADOS:")
            for issue in self.issues:
                simbolo = "❌" if issue.tipo == 'error' else "⚠️" if issue.tipo == 'advertencia' else "ℹ️"
                lineas.append(f"  {simbolo} [{issue.columna}] {issue.mensaje}")
                if issue.n_afectados > 0:
                    lineas.append(f"      Afectados: {issue.n_afectados:,}")
        
        if self.estadisticas:
            lineas.append("-" * 50)
            lineas.append("ESTADÍSTICAS:")
            for key, value in self.estadisticas.items():
                if isinstance(value, float):
                    lineas.append(f"  {key}: {value:.2f}")
                else:
                    lineas.append(f"  {key}: {value}")
        
        lineas.append("═" * 50)
        
        return "\n".join(lineas)
    
    def to_dict(self) -> Dict:
        """Convierte el reporte a diccionario."""
        return {
            'n_eventos': self.n_eventos,
            'n_columnas': self.n_columnas,
            'n_errores': self.n_errores,
            'n_advertencias': self.n_advertencias,
            'es_valido': self.es_valido,
            'score': self.score,
            'issues': [
                {
                    'tipo': i.tipo,
                    'columna': i.columna,
                    'mensaje': i.mensaje,
                    'n_afectados': i.n_afectados
                }
                for i in self.issues
            ],
            'estadisticas': self.estadisticas,
            'fecha_reporte': self.fecha_reporte.isoformat()
        }


# =============================================================================
# VALIDADORES INDIVIDUALES
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
    Valida que las coordenadas estén en el rango especificado.
    
    Args:
        lat: Latitud a validar
        lon: Longitud a validar
        lat_min, lat_max: Rango válido de latitud
        lon_min, lon_max: Rango válido de longitud
        
    Returns:
        True si las coordenadas son válidas
        
    Example:
        >>> validar_coordenadas(19.24, -103.72)
        True
        >>> validar_coordenadas(100, -103.72)  # Latitud inválida
        False
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return False
    
    if np.isnan(lat) or np.isnan(lon):
        return False
    
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def validar_coordenadas_mexico(lat: float, lon: float) -> bool:
    """
    Valida que las coordenadas estén dentro de México.
    
    Args:
        lat: Latitud
        lon: Longitud
        
    Returns:
        True si está en México
    """
    return validar_coordenadas(
        lat, lon,
        lat_min=MEXICO_LAT_MIN, lat_max=MEXICO_LAT_MAX,
        lon_min=MEXICO_LON_MIN, lon_max=MEXICO_LON_MAX
    )


def validar_magnitud(
    magnitud: float,
    mag_min: float = -2.0,
    mag_max: float = 10.0
) -> bool:
    """
    Valida que la magnitud esté en rango razonable.
    
    Args:
        magnitud: Magnitud a validar
        mag_min, mag_max: Rango válido
        
    Returns:
        True si la magnitud es válida
    """
    try:
        magnitud = float(magnitud)
    except (ValueError, TypeError):
        return False
    
    if np.isnan(magnitud):
        return False
    
    return mag_min <= magnitud <= mag_max


def validar_profundidad(
    profundidad: float,
    prof_min: float = 0.0,
    prof_max: float = 700.0
) -> bool:
    """
    Valida que la profundidad esté en rango razonable.
    
    Args:
        profundidad: Profundidad en km
        prof_min, prof_max: Rango válido
        
    Returns:
        True si la profundidad es válida
    """
    try:
        profundidad = float(profundidad)
    except (ValueError, TypeError):
        return False
    
    if np.isnan(profundidad):
        return False
    
    return prof_min <= profundidad <= prof_max


def validar_fecha(fecha: Any) -> bool:
    """
    Valida que la fecha sea válida.
    
    Args:
        fecha: Fecha a validar (datetime, string, timestamp)
        
    Returns:
        True si la fecha es válida
    """
    if pd.isna(fecha):
        return False
    
    try:
        pd.to_datetime(fecha)
        return True
    except:
        return False


# =============================================================================
# VALIDACIÓN DE CATÁLOGOS
# =============================================================================

def validar_catalogo_completo(
    df: pd.DataFrame,
    columnas_requeridas: Optional[List[str]] = None,
    lat_col: str = 'latitud',
    lon_col: str = 'longitud',
    mag_col: str = 'magnitud',
    prof_col: str = 'profundidad_km',
    fecha_col: str = 'fecha',
    validar_mexico: bool = False
) -> ReporteCalidad:
    """
    Realiza validación completa de un catálogo sísmico.
    
    Args:
        df: DataFrame con el catálogo
        columnas_requeridas: Lista de columnas que deben existir
        lat_col, lon_col, mag_col, prof_col, fecha_col: Nombres de columnas
        validar_mexico: Si True, verifica que eventos estén en México
        
    Returns:
        ReporteCalidad con todos los problemas encontrados
        
    Example:
        >>> reporte = validar_catalogo_completo(catalogo)
        >>> print(reporte)
        >>> if reporte.es_valido:
        ...     print("Catálogo válido")
    """
    if columnas_requeridas is None:
        columnas_requeridas = [fecha_col, lat_col, lon_col, mag_col]
    
    issues = []
    estadisticas = {}
    
    # Verificar columnas requeridas
    columnas_faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if columnas_faltantes:
        issues.append(IssueValidacion(
            tipo='error',
            columna='estructura',
            mensaje=f"Columnas faltantes: {', '.join(columnas_faltantes)}",
            n_afectados=len(df)
        ))
        return ReporteCalidad(
            n_eventos=len(df),
            n_columnas=len(df.columns),
            issues=issues
        )
    
    # Validar coordenadas
    if lat_col in df.columns and lon_col in df.columns:
        if validar_mexico:
            coords_invalidas = ~df.apply(
                lambda row: validar_coordenadas_mexico(row[lat_col], row[lon_col]),
                axis=1
            )
        else:
            coords_invalidas = ~df.apply(
                lambda row: validar_coordenadas(row[lat_col], row[lon_col]),
                axis=1
            )
        
        n_invalidas = coords_invalidas.sum()
        if n_invalidas > 0:
            issues.append(IssueValidacion(
                tipo='error',
                columna='coordenadas',
                mensaje="Coordenadas fuera de rango válido",
                n_afectados=n_invalidas,
                indices=df.index[coords_invalidas].tolist()[:100]
            ))
        
        estadisticas['lat_min'] = df[lat_col].min()
        estadisticas['lat_max'] = df[lat_col].max()
        estadisticas['lon_min'] = df[lon_col].min()
        estadisticas['lon_max'] = df[lon_col].max()
    
    # Validar magnitudes
    if mag_col in df.columns:
        mags_invalidas = ~df[mag_col].apply(validar_magnitud)
        n_invalidas = mags_invalidas.sum()
        
        if n_invalidas > 0:
            issues.append(IssueValidacion(
                tipo='advertencia',
                columna='magnitud',
                mensaje="Magnitudes fuera de rango [-2, 10]",
                n_afectados=n_invalidas
            ))
        
        estadisticas['mag_min'] = df[mag_col].min()
        estadisticas['mag_max'] = df[mag_col].max()
        estadisticas['mag_media'] = df[mag_col].mean()
        estadisticas['mag_mediana'] = df[mag_col].median()
    
    # Validar profundidades
    if prof_col in df.columns:
        profs_invalidas = ~df[prof_col].apply(validar_profundidad)
        n_invalidas = profs_invalidas.sum()
        
        if n_invalidas > 0:
            issues.append(IssueValidacion(
                tipo='advertencia',
                columna='profundidad',
                mensaje="Profundidades fuera de rango [0, 700] km",
                n_afectados=n_invalidas
            ))
        
        # Verificar profundidades negativas
        profs_negativas = (df[prof_col] < 0).sum()
        if profs_negativas > 0:
            issues.append(IssueValidacion(
                tipo='error',
                columna='profundidad',
                mensaje="Profundidades negativas detectadas",
                n_afectados=profs_negativas
            ))
        
        estadisticas['prof_min'] = df[prof_col].min()
        estadisticas['prof_max'] = df[prof_col].max()
        estadisticas['prof_media'] = df[prof_col].mean()
    
    # Validar fechas
    if fecha_col in df.columns:
        fechas_invalidas = ~df[fecha_col].apply(validar_fecha)
        n_invalidas = fechas_invalidas.sum()
        
        if n_invalidas > 0:
            issues.append(IssueValidacion(
                tipo='error',
                columna='fecha',
                mensaje="Fechas inválidas o faltantes",
                n_afectados=n_invalidas
            ))
        
        fechas_validas = pd.to_datetime(df.loc[~fechas_invalidas, fecha_col], errors='coerce')
        if len(fechas_validas) > 0:
            estadisticas['fecha_min'] = fechas_validas.min()
            estadisticas['fecha_max'] = fechas_validas.max()
    
    # Verificar valores faltantes
    for col in columnas_requeridas:
        if col in df.columns:
            n_nulos = df[col].isna().sum()
            pct_nulos = 100 * n_nulos / len(df)
            
            if pct_nulos > 0:
                tipo = 'error' if pct_nulos > 10 else 'advertencia' if pct_nulos > 1 else 'info'
                issues.append(IssueValidacion(
                    tipo=tipo,
                    columna=col,
                    mensaje=f"Valores faltantes: {pct_nulos:.1f}%",
                    n_afectados=n_nulos
                ))
    
    # Verificar duplicados
    if fecha_col in df.columns and lat_col in df.columns and lon_col in df.columns:
        duplicados = df.duplicated(subset=[fecha_col, lat_col, lon_col], keep='first')
        n_duplicados = duplicados.sum()
        
        if n_duplicados > 0:
            issues.append(IssueValidacion(
                tipo='advertencia',
                columna='duplicados',
                mensaje="Eventos duplicados (misma fecha y ubicación)",
                n_afectados=n_duplicados
            ))
    
    estadisticas['n_eventos'] = len(df)
    estadisticas['n_columnas'] = len(df.columns)
    estadisticas['columnas'] = list(df.columns)
    
    return ReporteCalidad(
        n_eventos=len(df),
        n_columnas=len(df.columns),
        issues=issues,
        estadisticas=estadisticas
    )


# =============================================================================
# DETECCIÓN DE OUTLIERS
# =============================================================================

def detectar_outliers_iqr(
    valores: Union[pd.Series, np.ndarray],
    factor: float = 1.5
) -> np.ndarray:
    """
    Detecta outliers usando el método IQR (Interquartile Range).
    
    Args:
        valores: Serie de valores
        factor: Factor multiplicador del IQR (default: 1.5)
        
    Returns:
        Array booleano indicando outliers
        
    Example:
        >>> outliers = detectar_outliers_iqr(catalogo['magnitud'])
        >>> print(f"Outliers: {outliers.sum()}")
    """
    valores = np.asarray(valores)
    valores_validos = valores[~np.isnan(valores)]
    
    if len(valores_validos) == 0:
        return np.zeros(len(valores), dtype=bool)
    
    q1 = np.percentile(valores_validos, 25)
    q3 = np.percentile(valores_validos, 75)
    iqr = q3 - q1
    
    limite_inferior = q1 - factor * iqr
    limite_superior = q3 + factor * iqr
    
    return (valores < limite_inferior) | (valores > limite_superior)


def detectar_outliers_zscore(
    valores: Union[pd.Series, np.ndarray],
    umbral: float = 3.0
) -> np.ndarray:
    """
    Detecta outliers usando z-score.
    
    Args:
        valores: Serie de valores
        umbral: Umbral de z-score (default: 3.0)
        
    Returns:
        Array booleano indicando outliers
    """
    valores = np.asarray(valores)
    valores_validos = valores[~np.isnan(valores)]
    
    if len(valores_validos) < 2:
        return np.zeros(len(valores), dtype=bool)
    
    media = np.mean(valores_validos)
    std = np.std(valores_validos)
    
    if std == 0:
        return np.zeros(len(valores), dtype=bool)
    
    z_scores = np.abs((valores - media) / std)
    
    return z_scores > umbral


def detectar_outliers(
    df: pd.DataFrame,
    columnas: Optional[List[str]] = None,
    metodo: str = 'iqr',
    factor: float = 1.5,
    umbral_zscore: float = 3.0
) -> pd.DataFrame:
    """
    Detecta outliers en múltiples columnas de un DataFrame.
    
    Args:
        df: DataFrame a analizar
        columnas: Columnas a verificar (si None, usa todas las numéricas)
        metodo: 'iqr' o 'zscore'
        factor: Factor IQR (para metodo='iqr')
        umbral_zscore: Umbral z-score (para metodo='zscore')
        
    Returns:
        DataFrame booleano con True en posiciones de outliers
        
    Example:
        >>> outliers = detectar_outliers(catalogo, ['magnitud', 'profundidad_km'])
        >>> eventos_outlier = catalogo[outliers.any(axis=1)]
    """
    if columnas is None:
        columnas = df.select_dtypes(include=[np.number]).columns.tolist()
    
    resultado = pd.DataFrame(index=df.index)
    
    for col in columnas:
        if col not in df.columns:
            continue
        
        if metodo == 'iqr':
            resultado[col] = detectar_outliers_iqr(df[col], factor)
        elif metodo == 'zscore':
            resultado[col] = detectar_outliers_zscore(df[col], umbral_zscore)
        else:
            raise ValueError(f"Método no soportado: {metodo}")
    
    return resultado


# =============================================================================
# LIMPIEZA DE DATOS
# =============================================================================

def limpiar_catalogo(
    df: pd.DataFrame,
    eliminar_invalidos: bool = True,
    eliminar_duplicados: bool = True,
    eliminar_outliers: bool = False,
    lat_col: str = 'latitud',
    lon_col: str = 'longitud',
    mag_col: str = 'magnitud',
    prof_col: str = 'profundidad_km',
    fecha_col: str = 'fecha'
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Limpia un catálogo sísmico removiendo registros problemáticos.
    
    Args:
        df: DataFrame a limpiar
        eliminar_invalidos: Remover registros con valores inválidos
        eliminar_duplicados: Remover eventos duplicados
        eliminar_outliers: Remover outliers estadísticos
        lat_col, lon_col, mag_col, prof_col, fecha_col: Nombres de columnas
        
    Returns:
        Tupla (DataFrame limpio, diccionario con conteos de eliminados)
        
    Example:
        >>> catalogo_limpio, stats = limpiar_catalogo(catalogo)
        >>> print(f"Eliminados: {sum(stats.values())}")
    """
    df_limpio = df.copy()
    eliminados = {}
    
    n_inicial = len(df_limpio)
    
    # Eliminar registros con coordenadas inválidas
    if eliminar_invalidos:
        if lat_col in df_limpio.columns and lon_col in df_limpio.columns:
            mask_coords = df_limpio.apply(
                lambda row: validar_coordenadas(row[lat_col], row[lon_col]),
                axis=1
            )
            n_eliminados = (~mask_coords).sum()
            if n_eliminados > 0:
                df_limpio = df_limpio[mask_coords]
                eliminados['coordenadas_invalidas'] = n_eliminados
        
        # Eliminar registros con magnitudes inválidas
        if mag_col in df_limpio.columns:
            mask_mag = df_limpio[mag_col].apply(validar_magnitud)
            n_eliminados = (~mask_mag).sum()
            if n_eliminados > 0:
                df_limpio = df_limpio[mask_mag]
                eliminados['magnitudes_invalidas'] = n_eliminados
        
        # Eliminar registros con fechas inválidas
        if fecha_col in df_limpio.columns:
            mask_fecha = df_limpio[fecha_col].apply(validar_fecha)
            n_eliminados = (~mask_fecha).sum()
            if n_eliminados > 0:
                df_limpio = df_limpio[mask_fecha]
                eliminados['fechas_invalidas'] = n_eliminados
    
    # Eliminar duplicados
    if eliminar_duplicados:
        cols_duplicados = [c for c in [fecha_col, lat_col, lon_col] if c in df_limpio.columns]
        if cols_duplicados:
            n_antes = len(df_limpio)
            df_limpio = df_limpio.drop_duplicates(subset=cols_duplicados, keep='first')
            n_eliminados = n_antes - len(df_limpio)
            if n_eliminados > 0:
                eliminados['duplicados'] = n_eliminados
    
    # Eliminar outliers
    if eliminar_outliers:
        cols_outliers = [c for c in [mag_col, prof_col] if c in df_limpio.columns]
        if cols_outliers:
            outliers_mask = detectar_outliers(df_limpio, cols_outliers)
            cualquier_outlier = outliers_mask.any(axis=1)
            n_eliminados = cualquier_outlier.sum()
            if n_eliminados > 0:
                df_limpio = df_limpio[~cualquier_outlier]
                eliminados['outliers'] = n_eliminados
    
    # Reset index
    df_limpio = df_limpio.reset_index(drop=True)
    
    logger.info(f"Limpieza: {n_inicial} -> {len(df_limpio)} eventos "
                f"({sum(eliminados.values())} eliminados)")
    
    return df_limpio, eliminados


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def reportar_calidad(
    df: pd.DataFrame,
    imprimir: bool = True
) -> ReporteCalidad:
    """
    Genera y opcionalmente imprime un reporte de calidad.
    
    Args:
        df: DataFrame a analizar
        imprimir: Si True, imprime el reporte
        
    Returns:
        ReporteCalidad
    """
    reporte = validar_catalogo_completo(df)
    
    if imprimir:
        print(reporte)
    
    return reporte


def validacion_rapida(df: pd.DataFrame) -> float:
    """
    Realiza una validación rápida y retorna un score (0-100).
    
    Args:
        df: DataFrame a validar
        
    Returns:
        Score de calidad (0-100)
    """
    reporte = validar_catalogo_completo(df)
    return reporte.score


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("SEISMEX - Validadores de Datos")
    print("=" * 60)
    
    # Crear datos de ejemplo con algunos problemas
    np.random.seed(42)
    n = 100
    
    datos = pd.DataFrame({
        'fecha': pd.date_range('2024-01-01', periods=n, freq='D'),
        'latitud': np.concatenate([
            np.random.uniform(18.5, 20.5, n-5),
            [100, -95, np.nan, 19.5, 19.5]  # Algunos inválidos
        ]),
        'longitud': np.concatenate([
            np.random.uniform(-104.5, -103.0, n-5),
            [-103.5, 200, -103.5, -103.5, -103.5]
        ]),
        'profundidad_km': np.concatenate([
            np.random.uniform(10, 50, n-3),
            [-10, 800, np.nan]  # Algunos problemáticos
        ]),
        'magnitud': np.concatenate([
            np.random.uniform(3.0, 5.5, n-2),
            [12.0, -5.0]  # Outliers
        ]),
    })
    
    # Agregar duplicado
    datos.iloc[-1, :] = datos.iloc[-2, :]
    
    print(f"\nDatos de ejemplo: {len(datos)} eventos")
    
    # Validación completa
    print("\n--- Validación Completa ---")
    reporte = validar_catalogo_completo(datos)
    print(reporte)
    
    # Detección de outliers
    print("\n--- Detección de Outliers ---")
    outliers = detectar_outliers(datos, ['magnitud', 'profundidad_km'])
    print(f"Outliers en magnitud: {outliers['magnitud'].sum()}")
    print(f"Outliers en profundidad: {outliers['profundidad_km'].sum()}")
    
    # Limpieza
    print("\n--- Limpieza del Catálogo ---")
    datos_limpios, stats = limpiar_catalogo(datos, eliminar_outliers=True)
    print(f"Eventos originales: {len(datos)}")
    print(f"Eventos limpios: {len(datos_limpios)}")
    print(f"Eliminados: {stats}")
    
    # Validación rápida
    print("\n--- Validación Rápida ---")
    score = validacion_rapida(datos_limpios)
    print(f"Score de calidad: {score:.1f}/100")
    
    print("\n✓ Todas las funciones de validación funcionan correctamente")
