"""
SEISMEX Data - Validación y Calidad de Datos
=============================================

Sistema de validación, diagnóstico y generación de reportes de calidad
para catálogos sísmicos. Incluye:
- Validación de rangos y tipos de datos
- Detección de valores faltantes y outliers
- Detección de duplicados
- Análisis exploratorio automático (EDA)
- Generación de reportes de calidad
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union
from pathlib import Path
import json

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class QualityIssue:
    """Representa un problema de calidad detectado."""
    tipo: str  # 'error', 'warning', 'info'
    categoria: str  # 'missing', 'range', 'duplicate', 'format', 'outlier'
    columna: Optional[str]
    descripcion: str
    filas_afectadas: int
    porcentaje: float
    ejemplos: List[Any] = field(default_factory=list)
    
    def __str__(self) -> str:
        icon = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(self.tipo, '•')
        return f"{icon} [{self.categoria}] {self.descripcion} ({self.filas_afectadas} filas, {self.porcentaje:.1f}%)"


@dataclass
class ColumnStats:
    """Estadísticas de una columna."""
    nombre: str
    dtype: str
    total: int
    no_nulos: int
    nulos: int
    pct_nulos: float
    unicos: int
    min_val: Any = None
    max_val: Any = None
    mean: float = None
    std: float = None
    median: float = None
    q25: float = None
    q75: float = None


@dataclass
class QualityReport:
    """Reporte completo de calidad de datos."""
    nombre_catalogo: str
    fecha_analisis: datetime
    total_filas: int
    total_columnas: int
    issues: List[QualityIssue]
    column_stats: Dict[str, ColumnStats]
    summary: Dict[str, Any]
    recommendations: List[str]
    score: float  # 0-100
    
    def __str__(self) -> str:
        lines = [
            "=" * 70,
            f"REPORTE DE CALIDAD - {self.nombre_catalogo}",
            "=" * 70,
            f"Fecha de análisis: {self.fecha_analisis.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total de filas: {self.total_filas:,}",
            f"Total de columnas: {self.total_columnas}",
            f"Score de calidad: {self.score:.1f}/100",
            "",
            "-" * 70,
            "RESUMEN",
            "-" * 70,
        ]
        
        for key, value in self.summary.items():
            lines.append(f"  {key}: {value}")
        
        lines.extend([
            "",
            "-" * 70,
            f"PROBLEMAS DETECTADOS ({len(self.issues)})",
            "-" * 70,
        ])
        
        errors = [i for i in self.issues if i.tipo == 'error']
        warnings = [i for i in self.issues if i.tipo == 'warning']
        infos = [i for i in self.issues if i.tipo == 'info']
        
        if errors:
            lines.append("\nErrores:")
            for issue in errors:
                lines.append(f"  {issue}")
        
        if warnings:
            lines.append("\nAdvertencias:")
            for issue in warnings:
                lines.append(f"  {issue}")
        
        if infos:
            lines.append("\nInformación:")
            for issue in infos:
                lines.append(f"  {issue}")
        
        if self.recommendations:
            lines.extend([
                "",
                "-" * 70,
                "RECOMENDACIONES",
                "-" * 70,
            ])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"  {i}. {rec}")
        
        lines.append("=" * 70)
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el reporte a diccionario."""
        return {
            'nombre_catalogo': self.nombre_catalogo,
            'fecha_analisis': self.fecha_analisis.isoformat(),
            'total_filas': self.total_filas,
            'total_columnas': self.total_columnas,
            'score': self.score,
            'summary': self.summary,
            'issues': [
                {
                    'tipo': i.tipo,
                    'categoria': i.categoria,
                    'columna': i.columna,
                    'descripcion': i.descripcion,
                    'filas_afectadas': i.filas_afectadas,
                    'porcentaje': i.porcentaje,
                }
                for i in self.issues
            ],
            'recommendations': self.recommendations,
        }
    
    def to_json(self, filepath: Optional[Path] = None) -> str:
        """Exporta el reporte a JSON."""
        data = self.to_dict()
        json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        
        if filepath:
            Path(filepath).write_text(json_str, encoding='utf-8')
            logger.info(f"Reporte guardado en {filepath}")
        
        return json_str
    
    @property
    def tiene_errores(self) -> bool:
        """Verifica si hay errores críticos."""
        return any(i.tipo == 'error' for i in self.issues)
    
    @property
    def es_valido(self) -> bool:
        """Verifica si el catálogo es válido para análisis."""
        return self.score >= 50 and not self.tiene_errores


# =============================================================================
# VALIDADOR DE CALIDAD
# =============================================================================

class QualityValidator:
    """
    Validador y analizador de calidad de datos sísmicos.
    
    Realiza validación completa de catálogos sísmicos incluyendo:
    - Verificación de columnas requeridas
    - Validación de rangos de valores
    - Detección de valores faltantes
    - Detección de duplicados
    - Identificación de outliers
    - Análisis exploratorio básico
    
    Ejemplo de uso:
    
        >>> validator = QualityValidator()
        >>> report = validator.analizar(catalogo)
        >>> print(report)
        >>> report.to_json('reporte_calidad.json')
    """
    
    # Columnas requeridas para análisis sísmico
    COLUMNAS_REQUERIDAS = ['fecha', 'latitud', 'longitud', 'magnitud']
    
    # Columnas opcionales pero recomendadas
    COLUMNAS_RECOMENDADAS = ['profundidad_km', 'tipo_magnitud', 'fuente', 'id_evento']
    
    def __init__(
        self,
        lat_min: float = -90.0,
        lat_max: float = 90.0,
        lon_min: float = -180.0,
        lon_max: float = 180.0,
        depth_min: float = 0.0,
        depth_max: float = 700.0,
        mag_min: float = -2.0,
        mag_max: float = 10.0,
        max_missing_pct: float = 10.0
    ):
        """
        Inicializa el validador con umbrales personalizados.
        
        Args:
            lat_min, lat_max: Rango válido de latitudes
            lon_min, lon_max: Rango válido de longitudes
            depth_min, depth_max: Rango válido de profundidades (km)
            mag_min, mag_max: Rango válido de magnitudes
            max_missing_pct: Porcentaje máximo aceptable de valores faltantes
        """
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.lon_min = lon_min
        self.lon_max = lon_max
        self.depth_min = depth_min
        self.depth_max = depth_max
        self.mag_min = mag_min
        self.mag_max = mag_max
        self.max_missing_pct = max_missing_pct
    
    def analizar(
        self,
        df: pd.DataFrame,
        nombre: str = "catalogo",
        incluir_eda: bool = True
    ) -> QualityReport:
        """
        Realiza análisis completo de calidad del catálogo.
        
        Args:
            df: DataFrame con el catálogo sísmico
            nombre: Nombre identificador del catálogo
            incluir_eda: Incluir análisis exploratorio detallado
            
        Returns:
            QualityReport con el análisis completo
        """
        logger.info(f"Iniciando análisis de calidad para '{nombre}'")
        
        issues: List[QualityIssue] = []
        recommendations: List[str] = []
        
        # 1. Verificar estructura básica
        issues.extend(self._verificar_estructura(df))
        
        # 2. Validar columnas requeridas
        issues.extend(self._validar_columnas_requeridas(df))
        
        # 3. Validar valores faltantes
        issues.extend(self._validar_valores_faltantes(df))
        
        # 4. Validar rangos de valores
        issues.extend(self._validar_rangos(df))
        
        # 5. Detectar duplicados
        issues.extend(self._detectar_duplicados(df))
        
        # 6. Detectar outliers
        issues.extend(self._detectar_outliers(df))
        
        # 7. Validar consistencia temporal
        issues.extend(self._validar_temporal(df))
        
        # 8. Calcular estadísticas por columna
        column_stats = self._calcular_estadisticas(df) if incluir_eda else {}
        
        # 9. Generar resumen
        summary = self._generar_resumen(df, issues)
        
        # 10. Generar recomendaciones
        recommendations = self._generar_recomendaciones(issues, df)
        
        # 11. Calcular score de calidad
        score = self._calcular_score(issues, df)
        
        report = QualityReport(
            nombre_catalogo=nombre,
            fecha_analisis=datetime.now(),
            total_filas=len(df),
            total_columnas=len(df.columns),
            issues=issues,
            column_stats=column_stats,
            summary=summary,
            recommendations=recommendations,
            score=score
        )
        
        logger.info(f"Análisis completado. Score: {score:.1f}/100, Issues: {len(issues)}")
        return report
    
    def validar_rapido(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validación rápida sin análisis completo.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Tupla (es_válido, lista_errores)
        """
        errores = []
        
        # Verificar columnas requeridas
        for col in self.COLUMNAS_REQUERIDAS:
            if col not in df.columns:
                errores.append(f"Columna requerida faltante: {col}")
        
        if errores:
            return False, errores
        
        # Verificar que no esté vacío
        if len(df) == 0:
            errores.append("El catálogo está vacío")
            return False, errores
        
        # Verificar tipos básicos
        try:
            pd.to_datetime(df['fecha'])
        except:
            errores.append("La columna 'fecha' no tiene formato válido")
        
        for col in ['latitud', 'longitud', 'magnitud']:
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    pd.to_numeric(df[col])
                except:
                    errores.append(f"La columna '{col}' no es numérica")
        
        return len(errores) == 0, errores
    
    # =========================================================================
    # MÉTODOS DE VALIDACIÓN
    # =========================================================================
    
    def _verificar_estructura(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Verifica la estructura básica del DataFrame."""
        issues = []
        
        if len(df) == 0:
            issues.append(QualityIssue(
                tipo='error',
                categoria='format',
                columna=None,
                descripcion='El catálogo está vacío',
                filas_afectadas=0,
                porcentaje=100.0
            ))
        
        if len(df.columns) == 0:
            issues.append(QualityIssue(
                tipo='error',
                categoria='format',
                columna=None,
                descripcion='El catálogo no tiene columnas',
                filas_afectadas=0,
                porcentaje=100.0
            ))
        
        return issues
    
    def _validar_columnas_requeridas(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Valida presencia de columnas requeridas."""
        issues = []
        
        for col in self.COLUMNAS_REQUERIDAS:
            if col not in df.columns:
                issues.append(QualityIssue(
                    tipo='error',
                    categoria='format',
                    columna=col,
                    descripcion=f"Columna requerida '{col}' no encontrada",
                    filas_afectadas=len(df),
                    porcentaje=100.0
                ))
        
        for col in self.COLUMNAS_RECOMENDADAS:
            if col not in df.columns:
                issues.append(QualityIssue(
                    tipo='warning',
                    categoria='format',
                    columna=col,
                    descripcion=f"Columna recomendada '{col}' no encontrada",
                    filas_afectadas=0,
                    porcentaje=0.0
                ))
        
        return issues
    
    def _validar_valores_faltantes(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Detecta valores faltantes por columna."""
        issues = []
        
        for col in df.columns:
            n_missing = df[col].isna().sum()
            if n_missing > 0:
                pct = (n_missing / len(df)) * 100
                
                # Determinar severidad
                if col in self.COLUMNAS_REQUERIDAS:
                    tipo = 'error' if pct > self.max_missing_pct else 'warning'
                else:
                    tipo = 'warning' if pct > 50 else 'info'
                
                issues.append(QualityIssue(
                    tipo=tipo,
                    categoria='missing',
                    columna=col,
                    descripcion=f"Valores faltantes en '{col}'",
                    filas_afectadas=n_missing,
                    porcentaje=pct,
                    ejemplos=df[df[col].isna()].index[:5].tolist()
                ))
        
        return issues
    
    def _validar_rangos(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Valida que los valores estén dentro de rangos válidos."""
        issues = []
        
        # Latitud
        if 'latitud' in df.columns:
            fuera_rango = df[
                (df['latitud'] < self.lat_min) | 
                (df['latitud'] > self.lat_max)
            ]
            if len(fuera_rango) > 0:
                issues.append(QualityIssue(
                    tipo='error',
                    categoria='range',
                    columna='latitud',
                    descripcion=f"Latitudes fuera de rango [{self.lat_min}, {self.lat_max}]",
                    filas_afectadas=len(fuera_rango),
                    porcentaje=(len(fuera_rango) / len(df)) * 100,
                    ejemplos=fuera_rango['latitud'].head(5).tolist()
                ))
        
        # Longitud
        if 'longitud' in df.columns:
            fuera_rango = df[
                (df['longitud'] < self.lon_min) | 
                (df['longitud'] > self.lon_max)
            ]
            if len(fuera_rango) > 0:
                issues.append(QualityIssue(
                    tipo='error',
                    categoria='range',
                    columna='longitud',
                    descripcion=f"Longitudes fuera de rango [{self.lon_min}, {self.lon_max}]",
                    filas_afectadas=len(fuera_rango),
                    porcentaje=(len(fuera_rango) / len(df)) * 100,
                    ejemplos=fuera_rango['longitud'].head(5).tolist()
                ))
        
        # Profundidad
        if 'profundidad_km' in df.columns:
            valid_depth = df['profundidad_km'].dropna()
            fuera_rango = valid_depth[
                (valid_depth < self.depth_min) | 
                (valid_depth > self.depth_max)
            ]
            if len(fuera_rango) > 0:
                issues.append(QualityIssue(
                    tipo='warning',
                    categoria='range',
                    columna='profundidad_km',
                    descripcion=f"Profundidades fuera de rango [{self.depth_min}, {self.depth_max}] km",
                    filas_afectadas=len(fuera_rango),
                    porcentaje=(len(fuera_rango) / len(df)) * 100,
                    ejemplos=fuera_rango.head(5).tolist()
                ))
        
        # Magnitud
        if 'magnitud' in df.columns:
            valid_mag = df['magnitud'].dropna()
            fuera_rango = valid_mag[
                (valid_mag < self.mag_min) | 
                (valid_mag > self.mag_max)
            ]
            if len(fuera_rango) > 0:
                issues.append(QualityIssue(
                    tipo='warning',
                    categoria='range',
                    columna='magnitud',
                    descripcion=f"Magnitudes fuera de rango [{self.mag_min}, {self.mag_max}]",
                    filas_afectadas=len(fuera_rango),
                    porcentaje=(len(fuera_rango) / len(df)) * 100,
                    ejemplos=fuera_rango.head(5).tolist()
                ))
        
        return issues
    
    def _detectar_duplicados(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Detecta eventos duplicados."""
        issues = []
        
        # Duplicados exactos
        cols_check = [c for c in ['fecha', 'latitud', 'longitud', 'magnitud'] 
                      if c in df.columns]
        
        if cols_check:
            duplicados = df.duplicated(subset=cols_check, keep='first')
            n_dups = duplicados.sum()
            
            if n_dups > 0:
                issues.append(QualityIssue(
                    tipo='warning',
                    categoria='duplicate',
                    columna=None,
                    descripcion='Eventos duplicados exactos detectados',
                    filas_afectadas=n_dups,
                    porcentaje=(n_dups / len(df)) * 100,
                    ejemplos=df[duplicados].index[:5].tolist()
                ))
        
        # Duplicados potenciales (cercanos en tiempo y espacio)
        if all(c in df.columns for c in ['fecha', 'latitud', 'longitud']):
            try:
                df_sorted = df.sort_values('fecha').reset_index(drop=True)
                fechas = pd.to_datetime(df_sorted['fecha'])
                
                # Detectar eventos muy cercanos (< 1 minuto y < 10 km)
                posibles_dups = 0
                for i in range(1, min(len(df_sorted), 1000)):  # Limitar para rendimiento
                    dt = (fechas.iloc[i] - fechas.iloc[i-1]).total_seconds()
                    if dt < 60:  # Menos de 1 minuto
                        dlat = abs(df_sorted.iloc[i]['latitud'] - df_sorted.iloc[i-1]['latitud'])
                        dlon = abs(df_sorted.iloc[i]['longitud'] - df_sorted.iloc[i-1]['longitud'])
                        if dlat < 0.1 and dlon < 0.1:  # ~10 km
                            posibles_dups += 1
                
                if posibles_dups > 0:
                    issues.append(QualityIssue(
                        tipo='info',
                        categoria='duplicate',
                        columna=None,
                        descripcion='Posibles duplicados (eventos muy cercanos en tiempo y espacio)',
                        filas_afectadas=posibles_dups,
                        porcentaje=(posibles_dups / len(df)) * 100
                    ))
            except Exception as e:
                logger.warning(f"Error al detectar duplicados potenciales: {e}")
        
        return issues
    
    def _detectar_outliers(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Detecta valores atípicos usando IQR."""
        issues = []
        
        columnas_numericas = ['magnitud', 'profundidad_km', 'latitud', 'longitud']
        
        for col in columnas_numericas:
            if col not in df.columns:
                continue
            
            datos = df[col].dropna()
            if len(datos) < 10:
                continue
            
            q1 = datos.quantile(0.25)
            q3 = datos.quantile(0.75)
            iqr = q3 - q1
            
            lower = q1 - 3 * iqr  # Usar 3*IQR para outliers extremos
            upper = q3 + 3 * iqr
            
            outliers = datos[(datos < lower) | (datos > upper)]
            
            if len(outliers) > 0:
                issues.append(QualityIssue(
                    tipo='info',
                    categoria='outlier',
                    columna=col,
                    descripcion=f"Valores atípicos extremos en '{col}'",
                    filas_afectadas=len(outliers),
                    porcentaje=(len(outliers) / len(df)) * 100,
                    ejemplos=outliers.head(5).tolist()
                ))
        
        return issues
    
    def _validar_temporal(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Valida consistencia temporal de los datos."""
        issues = []
        
        if 'fecha' not in df.columns:
            return issues
        
        try:
            fechas = pd.to_datetime(df['fecha'])
            
            # Verificar fechas futuras
            futuras = fechas > datetime.now()
            if futuras.any():
                issues.append(QualityIssue(
                    tipo='error',
                    categoria='range',
                    columna='fecha',
                    descripcion='Fechas en el futuro detectadas',
                    filas_afectadas=futuras.sum(),
                    porcentaje=(futuras.sum() / len(df)) * 100
                ))
            
            # Verificar fechas muy antiguas (antes de 1900)
            muy_antiguas = fechas < datetime(1900, 1, 1)
            if muy_antiguas.any():
                issues.append(QualityIssue(
                    tipo='warning',
                    categoria='range',
                    columna='fecha',
                    descripcion='Fechas anteriores a 1900 detectadas',
                    filas_afectadas=muy_antiguas.sum(),
                    porcentaje=(muy_antiguas.sum() / len(df)) * 100
                ))
            
            # Verificar orden cronológico
            if not fechas.is_monotonic_increasing:
                issues.append(QualityIssue(
                    tipo='info',
                    categoria='format',
                    columna='fecha',
                    descripcion='Los datos no están ordenados cronológicamente',
                    filas_afectadas=0,
                    porcentaje=0.0
                ))
            
        except Exception as e:
            issues.append(QualityIssue(
                tipo='error',
                categoria='format',
                columna='fecha',
                descripcion=f'Error al parsear fechas: {str(e)}',
                filas_afectadas=len(df),
                porcentaje=100.0
            ))
        
        return issues
    
    # =========================================================================
    # ESTADÍSTICAS Y RESUMEN
    # =========================================================================
    
    def _calcular_estadisticas(self, df: pd.DataFrame) -> Dict[str, ColumnStats]:
        """Calcula estadísticas descriptivas por columna."""
        stats = {}
        
        for col in df.columns:
            serie = df[col]
            
            stat = ColumnStats(
                nombre=col,
                dtype=str(serie.dtype),
                total=len(serie),
                no_nulos=serie.notna().sum(),
                nulos=serie.isna().sum(),
                pct_nulos=(serie.isna().sum() / len(serie)) * 100,
                unicos=serie.nunique()
            )
            
            # Estadísticas numéricas
            if pd.api.types.is_numeric_dtype(serie):
                datos = serie.dropna()
                if len(datos) > 0:
                    stat.min_val = datos.min()
                    stat.max_val = datos.max()
                    stat.mean = datos.mean()
                    stat.std = datos.std()
                    stat.median = datos.median()
                    stat.q25 = datos.quantile(0.25)
                    stat.q75 = datos.quantile(0.75)
            
            # Estadísticas de fecha
            elif col == 'fecha':
                try:
                    fechas = pd.to_datetime(serie.dropna())
                    if len(fechas) > 0:
                        stat.min_val = fechas.min()
                        stat.max_val = fechas.max()
                except:
                    pass
            
            stats[col] = stat
        
        return stats
    
    def _generar_resumen(
        self, 
        df: pd.DataFrame, 
        issues: List[QualityIssue]
    ) -> Dict[str, Any]:
        """Genera resumen del análisis."""
        summary = {
            'total_eventos': len(df),
            'total_columnas': len(df.columns),
            'columnas': list(df.columns),
            'errores': len([i for i in issues if i.tipo == 'error']),
            'advertencias': len([i for i in issues if i.tipo == 'warning']),
            'informacion': len([i for i in issues if i.tipo == 'info']),
        }
        
        # Rango temporal
        if 'fecha' in df.columns:
            try:
                fechas = pd.to_datetime(df['fecha'].dropna())
                if len(fechas) > 0:
                    summary['fecha_inicio'] = str(fechas.min())
                    summary['fecha_fin'] = str(fechas.max())
                    summary['rango_temporal'] = str(fechas.max() - fechas.min())
            except:
                pass
        
        # Rango espacial
        if all(c in df.columns for c in ['latitud', 'longitud']):
            summary['lat_min'] = df['latitud'].min()
            summary['lat_max'] = df['latitud'].max()
            summary['lon_min'] = df['longitud'].min()
            summary['lon_max'] = df['longitud'].max()
        
        # Rango de magnitudes
        if 'magnitud' in df.columns:
            summary['mag_min'] = df['magnitud'].min()
            summary['mag_max'] = df['magnitud'].max()
            summary['mag_promedio'] = df['magnitud'].mean()
        
        # Rango de profundidades
        if 'profundidad_km' in df.columns:
            prof = df['profundidad_km'].dropna()
            if len(prof) > 0:
                summary['prof_min_km'] = prof.min()
                summary['prof_max_km'] = prof.max()
                summary['prof_promedio_km'] = prof.mean()
        
        # Fuentes
        if 'fuente' in df.columns:
            summary['fuentes'] = df['fuente'].value_counts().to_dict()
        
        return summary
    
    def _generar_recomendaciones(
        self, 
        issues: List[QualityIssue],
        df: pd.DataFrame
    ) -> List[str]:
        """Genera recomendaciones basadas en los problemas detectados."""
        recomendaciones = []
        
        # Por categoría de problema
        categorias = set(i.categoria for i in issues)
        
        if 'missing' in categorias:
            missing_issues = [i for i in issues if i.categoria == 'missing' and i.tipo == 'error']
            if missing_issues:
                cols = [i.columna for i in missing_issues]
                recomendaciones.append(
                    f"Completar valores faltantes en columnas críticas: {', '.join(cols)}"
                )
        
        if 'range' in categorias:
            recomendaciones.append(
                "Revisar y corregir valores fuera de rango geográfico o físico"
            )
        
        if 'duplicate' in categorias:
            recomendaciones.append(
                "Ejecutar eliminación de duplicados antes del análisis"
            )
        
        if 'outlier' in categorias:
            recomendaciones.append(
                "Revisar valores atípicos - podrían ser errores o eventos genuinos excepcionales"
            )
        
        # Recomendaciones generales
        if 'profundidad_km' not in df.columns:
            recomendaciones.append(
                "Añadir columna 'profundidad_km' para análisis 3D completo"
            )
        
        if 'tipo_magnitud' not in df.columns:
            recomendaciones.append(
                "Añadir columna 'tipo_magnitud' para homogeneización de magnitudes"
            )
        
        # Si hay muchos errores
        n_errors = len([i for i in issues if i.tipo == 'error'])
        if n_errors >= 3:
            recomendaciones.insert(0, 
                "⚠️ Se detectaron múltiples errores críticos. "
                "Revisar datos antes de continuar con el análisis."
            )
        
        return recomendaciones
    
    def _calcular_score(
        self, 
        issues: List[QualityIssue],
        df: pd.DataFrame
    ) -> float:
        """
        Calcula score de calidad de 0-100.
        
        Criterios:
        - Errores: -20 puntos cada uno
        - Advertencias: -5 puntos cada una
        - Info: -1 punto cada uno
        - Columnas faltantes: -10 por requerida, -2 por recomendada
        """
        score = 100.0
        
        # Penalizar por issues
        for issue in issues:
            if issue.tipo == 'error':
                score -= 20
            elif issue.tipo == 'warning':
                score -= 5
            elif issue.tipo == 'info':
                score -= 1
        
        # Penalizar por % de valores faltantes en columnas críticas
        for col in self.COLUMNAS_REQUERIDAS:
            if col in df.columns:
                pct_missing = df[col].isna().mean() * 100
                score -= pct_missing * 0.5  # 0.5 puntos por cada % faltante
        
        # Asegurar rango [0, 100]
        return max(0.0, min(100.0, score))


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def validar_catalogo(
    df: pd.DataFrame,
    nombre: str = "catalogo",
    generar_reporte: bool = True,
    guardar_reporte: Optional[Path] = None
) -> QualityReport:
    """
    Función de conveniencia para validar un catálogo.
    
    Args:
        df: DataFrame con el catálogo
        nombre: Nombre identificador
        generar_reporte: Imprimir reporte en consola
        guardar_reporte: Ruta para guardar reporte JSON
        
    Returns:
        QualityReport con el análisis
    """
    validator = QualityValidator()
    report = validator.analizar(df, nombre)
    
    if generar_reporte:
        print(report)
    
    if guardar_reporte:
        report.to_json(guardar_reporte)
    
    return report


def validacion_rapida(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validación rápida sin análisis completo.
    
    Args:
        df: DataFrame a validar
        
    Returns:
        Tupla (es_válido, lista_errores)
    """
    validator = QualityValidator()
    return validator.validar_rapido(df)
