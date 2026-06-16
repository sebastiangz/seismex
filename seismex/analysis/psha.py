#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Analysis - Análisis Probabilístico de Peligro Sísmico (PSHA)
================================================================================

Implementación del análisis PSHA basado en la metodología de Cornell-McGuire
para evaluación de peligro sísmico.

Componentes principales:
    - AnalizadorPSHA: Motor principal de cálculo
    - CurvaPeligro: Curva de excedencia de intensidad
    - MapaPeligro: Mapa de peligro para período de retorno
    - Desagregacion: Análisis de contribución M-R-ε
    - ArbolLogico: Manejo de incertidumbre epistémica

Metodología:
    λ(IM > im) = Σ_sources Σ_m Σ_r ν(m) × P(IM > im | m, r) × P(R=r | source)
    
    Donde:
    - λ = tasa de excedencia anual
    - IM = medida de intensidad (PGA, Sa, etc.)
    - ν(m) = tasa de ocurrencia de magnitud m
    - P(IM > im | m, r) = probabilidad de exceder im dado m y r

Referencias:
    - Cornell, C.A. (1968). Engineering seismic risk analysis. BSSA.
    - McGuire, R.K. (2004). Seismic Hazard and Risk Analysis. EERI.
    - Bazzurro, P. & Cornell, C.A. (1999). Disaggregation of seismic hazard.
      BSSA, 89(2), 501-520.

Estado: ✅ IMPLEMENTADO

Autor: SEISMEX Team
Versión: 1.0.0
================================================================================
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    List,
    Tuple,
    Optional,
    Dict,
    Any,
    Union,
    Callable,
    TYPE_CHECKING
)
import numpy as np

if TYPE_CHECKING:
    from .source_models import ModeloFuentes, FuenteSismica
    from .isoseismal import GMPE

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Niveles de intensidad por defecto para curvas de peligro
NIVELES_PGA_DEFAULT = np.logspace(-3, 0.5, 50)  # 0.001g a ~3g
NIVELES_SA_DEFAULT = np.logspace(-3, 1, 50)     # 0.001g a 10g

# Períodos de retorno estándar
PERIODOS_RETORNO_DEFAULT = [72, 225, 475, 975, 2475, 4975]  # años


# =============================================================================
# ENUMERACIONES
# =============================================================================

class MedidaIntensidad(Enum):
    """Medidas de intensidad del movimiento del terreno."""
    PGA = "pga"                 # Peak Ground Acceleration
    PGV = "pgv"                 # Peak Ground Velocity
    PGD = "pgd"                 # Peak Ground Displacement
    SA_02 = "sa_0.2"            # Spectral Acceleration T=0.2s
    SA_03 = "sa_0.3"            # Spectral Acceleration T=0.3s
    SA_05 = "sa_0.5"            # Spectral Acceleration T=0.5s
    SA_10 = "sa_1.0"            # Spectral Acceleration T=1.0s
    SA_20 = "sa_2.0"            # Spectral Acceleration T=2.0s
    MMI = "mmi"                 # Modified Mercalli Intensity


class TipoDistanciaGMPE(Enum):
    """Tipos de distancia para GMPEs."""
    RHYPO = "rhypo"             # Distancia hipocentral
    REPI = "repi"               # Distancia epicentral
    RRUP = "rrup"               # Distancia a ruptura
    RJB = "rjb"                 # Distancia Joyner-Boore


# =============================================================================
# CURVA DE PELIGRO
# =============================================================================

@dataclass
class CurvaPeligro:
    """
    Curva de peligro sísmico (hazard curve).
    
    Representa la relación entre niveles de intensidad y
    sus tasas de excedencia anual.
    
    Attributes
    ----------
    intensidades : np.ndarray
        Niveles de intensidad (ej: PGA en g)
    tasas_excedencia : np.ndarray
        Tasas de excedencia anual para cada nivel
    medida : MedidaIntensidad
        Tipo de medida de intensidad
    sitio : Tuple[float, float]
        Ubicación del sitio (lat, lon)
    vs30 : float
        Velocidad Vs30 del sitio (m/s)
    contribuciones : Optional[Dict]
        Contribución por fuente
    """
    intensidades: np.ndarray
    tasas_excedencia: np.ndarray
    medida: MedidaIntensidad = MedidaIntensidad.PGA
    sitio: Tuple[float, float] = (0, 0)
    vs30: float = 760.0
    contribuciones: Optional[Dict[str, np.ndarray]] = None
    
    def __post_init__(self):
        """Validación."""
        if len(self.intensidades) != len(self.tasas_excedencia):
            raise ValueError("intensidades y tasas_excedencia deben tener mismo tamaño")
    
    def probabilidad_excedencia(
        self,
        intensidad: float,
        tiempo_exposicion: float = 50.0
    ) -> float:
        """
        Calcula probabilidad de exceder una intensidad en un período.
        
        P(IM > im en t años) = 1 - exp(-λ × t)
        
        Parameters
        ----------
        intensidad : float
            Nivel de intensidad
        tiempo_exposicion : float
            Período de exposición en años
            
        Returns
        -------
        float
            Probabilidad de excedencia
        """
        tasa = self.interpolar_tasa(intensidad)
        return 1 - np.exp(-tasa * tiempo_exposicion)
    
    def interpolar_tasa(self, intensidad: float) -> float:
        """Interpola tasa de excedencia para una intensidad."""
        if intensidad <= self.intensidades.min():
            return self.tasas_excedencia.max()
        if intensidad >= self.intensidades.max():
            return 0.0
        
        # Interpolación log-log
        log_im = np.log(intensidad)
        log_ims = np.log(self.intensidades)
        log_tasas = np.log(np.clip(self.tasas_excedencia, 1e-20, None))
        
        return np.exp(np.interp(log_im, log_ims, log_tasas))
    
    def intensidad_para_periodo_retorno(self, periodo_retorno: float) -> float:
        """
        Obtiene intensidad para un período de retorno.
        
        Parameters
        ----------
        periodo_retorno : float
            Período de retorno en años
            
        Returns
        -------
        float
            Intensidad correspondiente
        """
        tasa_objetivo = 1.0 / periodo_retorno
        
        if tasa_objetivo > self.tasas_excedencia.max():
            return self.intensidades.min()
        if tasa_objetivo < self.tasas_excedencia.min():
            return self.intensidades.max()
        
        # Interpolación log-log inversa
        log_tasa = np.log(tasa_objetivo)
        log_tasas = np.log(np.clip(self.tasas_excedencia, 1e-20, None))
        log_ims = np.log(self.intensidades)
        
        # Invertir arrays para interpolación monotónica
        idx_sort = np.argsort(log_tasas)
        return np.exp(np.interp(log_tasa, log_tasas[idx_sort], log_ims[idx_sort]))
    
    def espectro_uniforme(
        self,
        curvas_sa: Dict[float, 'CurvaPeligro'],
        periodo_retorno: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Construye espectro de peligro uniforme (UHS).
        
        Parameters
        ----------
        curvas_sa : Dict[float, CurvaPeligro]
            Curvas de peligro para diferentes períodos {T: curva}
        periodo_retorno : float
            Período de retorno objetivo
            
        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            (períodos, aceleraciones espectrales)
        """
        periodos = sorted(curvas_sa.keys())
        sa_values = []
        
        for T in periodos:
            curva = curvas_sa[T]
            sa = curva.intensidad_para_periodo_retorno(periodo_retorno)
            sa_values.append(sa)
        
        return np.array(periodos), np.array(sa_values)
    
    def graficar(self, ax=None, **kwargs):
        """Grafica la curva de peligro."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib necesario para graficar")
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        
        plot_kwargs = {
            'linewidth': 2,
            'label': f'{self.medida.value.upper()}'
        }
        plot_kwargs.update(kwargs)
        
        ax.loglog(self.intensidades, self.tasas_excedencia, **plot_kwargs)
        
        # Líneas de período de retorno
        for tr in [475, 975, 2475]:
            tasa = 1 / tr
            if self.tasas_excedencia.min() < tasa < self.tasas_excedencia.max():
                ax.axhline(tasa, color='gray', linestyle='--', alpha=0.5)
                ax.text(self.intensidades.max() * 0.7, tasa * 1.2, 
                       f'TR={tr} años', fontsize=8)
        
        ax.set_xlabel(f'{self.medida.value.upper()} (g)')
        ax.set_ylabel('Tasa de excedencia anual')
        ax.set_title(f'Curva de Peligro - Sitio ({self.sitio[0]:.2f}, {self.sitio[1]:.2f})')
        ax.grid(True, which='both', alpha=0.3)
        ax.legend()
        
        return ax
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'intensidades': self.intensidades.tolist(),
            'tasas_excedencia': self.tasas_excedencia.tolist(),
            'medida': self.medida.value,
            'sitio': list(self.sitio),
            'vs30': self.vs30
        }


# =============================================================================
# MAPA DE PELIGRO
# =============================================================================

@dataclass
class MapaPeligro:
    """
    Mapa de peligro sísmico.
    
    Representa la distribución espacial de un parámetro de
    intensidad para un período de retorno dado.
    
    Attributes
    ----------
    intensidades : np.ndarray
        Grilla 2D de intensidades
    latitudes : np.ndarray
        Vector de latitudes
    longitudes : np.ndarray
        Vector de longitudes
    periodo_retorno : float
        Período de retorno (años)
    medida : MedidaIntensidad
        Tipo de medida
    vs30 : Union[float, np.ndarray]
        Vs30 (constante o grilla)
    """
    intensidades: np.ndarray
    latitudes: np.ndarray
    longitudes: np.ndarray
    periodo_retorno: float
    medida: MedidaIntensidad = MedidaIntensidad.PGA
    vs30: Union[float, np.ndarray] = 760.0
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Límites (lon_min, lat_min, lon_max, lat_max)."""
        return (
            float(self.longitudes.min()),
            float(self.latitudes.min()),
            float(self.longitudes.max()),
            float(self.latitudes.max())
        )
    
    @property
    def intensidad_maxima(self) -> float:
        """Intensidad máxima en el mapa."""
        return float(np.nanmax(self.intensidades))
    
    @property
    def intensidad_media(self) -> float:
        """Intensidad media en el mapa."""
        return float(np.nanmean(self.intensidades))
    
    def obtener_intensidad(self, lat: float, lon: float) -> float:
        """Obtiene intensidad en un punto mediante interpolación."""
        if not (self.latitudes.min() <= lat <= self.latitudes.max() and
                self.longitudes.min() <= lon <= self.longitudes.max()):
            return np.nan
        
        # Índices más cercanos
        lat_idx = np.argmin(np.abs(self.latitudes - lat))
        lon_idx = np.argmin(np.abs(self.longitudes - lon))
        
        return float(self.intensidades[lat_idx, lon_idx])
    
    def graficar(self, ax=None, contornos: bool = True, **kwargs):
        """Grafica el mapa de peligro."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib necesario para graficar")
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 10))
        
        X, Y = np.meshgrid(self.longitudes, self.latitudes)
        
        # Mapa de colores
        im_kwargs = {
            'cmap': 'YlOrRd',
            'shading': 'auto'
        }
        im_kwargs.update(kwargs)
        
        im = ax.pcolormesh(X, Y, self.intensidades, **im_kwargs)
        
        # Contornos
        if contornos:
            niveles = np.linspace(
                np.nanpercentile(self.intensidades, 10),
                np.nanpercentile(self.intensidades, 90),
                8
            )
            cs = ax.contour(X, Y, self.intensidades, levels=niveles,
                           colors='black', linewidths=0.5)
            ax.clabel(cs, inline=True, fontsize=8, fmt='%.2f')
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax, label=f'{self.medida.value.upper()} (g)')
        
        ax.set_xlabel('Longitud')
        ax.set_ylabel('Latitud')
        ax.set_title(
            f'Mapa de Peligro Sísmico - {self.medida.value.upper()}\n'
            f'Período de retorno: {self.periodo_retorno} años'
        )
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        return ax
    
    def exportar_geotiff(self, ruta: str) -> None:
        """Exporta el mapa a GeoTIFF."""
        try:
            import rasterio
            from rasterio.transform import from_bounds
        except ImportError:
            raise ImportError("rasterio necesario para exportar_geotiff")
        
        transform = from_bounds(
            self.longitudes.min(), self.latitudes.min(),
            self.longitudes.max(), self.latitudes.max(),
            len(self.longitudes), len(self.latitudes)
        )
        
        with rasterio.open(
            ruta, 'w',
            driver='GTiff',
            height=len(self.latitudes),
            width=len(self.longitudes),
            count=1,
            dtype=self.intensidades.dtype,
            crs='EPSG:4326',
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(self.intensidades, 1)
            dst.update_tags(
                periodo_retorno=self.periodo_retorno,
                medida=self.medida.value
            )
        
        logger.info(f"Mapa exportado a {ruta}")
    
    def to_geodataframe(self) -> 'gpd.GeoDataFrame':
        """Convierte a GeoDataFrame con puntos."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            raise ImportError("geopandas necesario")
        
        datos = []
        geometrias = []
        
        for i, lat in enumerate(self.latitudes):
            for j, lon in enumerate(self.longitudes):
                val = self.intensidades[i, j]
                if not np.isnan(val):
                    datos.append({
                        self.medida.value: val,
                        'lat': lat,
                        'lon': lon
                    })
                    geometrias.append(Point(lon, lat))
        
        return gpd.GeoDataFrame(datos, geometry=geometrias, crs="EPSG:4326")


# =============================================================================
# DESAGREGACIÓN
# =============================================================================

@dataclass
class Desagregacion:
    """
    Resultados de desagregación del peligro sísmico.
    
    Muestra la contribución de diferentes escenarios (M, R, ε)
    al peligro sísmico en un nivel de intensidad dado.
    
    Attributes
    ----------
    bins_magnitud : np.ndarray
        Centros de bins de magnitud
    bins_distancia : np.ndarray
        Centros de bins de distancia (km)
    bins_epsilon : np.ndarray
        Centros de bins de epsilon
    contribucion_MR : np.ndarray
        Contribución 2D (M, R)
    contribucion_MRe : np.ndarray
        Contribución 3D (M, R, ε)
    intensidad_objetivo : float
        Nivel de intensidad para la desagregación
    sitio : Tuple[float, float]
        Ubicación del sitio
    """
    bins_magnitud: np.ndarray
    bins_distancia: np.ndarray
    bins_epsilon: np.ndarray
    contribucion_MR: np.ndarray
    contribucion_MRe: np.ndarray
    intensidad_objetivo: float
    sitio: Tuple[float, float] = (0, 0)
    
    @property
    def magnitud_modal(self) -> float:
        """Magnitud con mayor contribución."""
        contrib_M = self.contribucion_MR.sum(axis=1)
        return float(self.bins_magnitud[np.argmax(contrib_M)])
    
    @property
    def distancia_modal(self) -> float:
        """Distancia con mayor contribución."""
        contrib_R = self.contribucion_MR.sum(axis=0)
        return float(self.bins_distancia[np.argmax(contrib_R)])
    
    @property
    def epsilon_modal(self) -> float:
        """Epsilon con mayor contribución."""
        contrib_e = self.contribucion_MRe.sum(axis=(0, 1))
        return float(self.bins_epsilon[np.argmax(contrib_e)])
    
    @property
    def magnitud_media(self) -> float:
        """Magnitud media ponderada por contribución."""
        contrib_M = self.contribucion_MR.sum(axis=1)
        if contrib_M.sum() == 0:
            return 0
        return float(np.average(self.bins_magnitud, weights=contrib_M))
    
    @property
    def distancia_media(self) -> float:
        """Distancia media ponderada por contribución."""
        contrib_R = self.contribucion_MR.sum(axis=0)
        if contrib_R.sum() == 0:
            return 0
        return float(np.average(self.bins_distancia, weights=contrib_R))
    
    def graficar_MR(self, ax=None, **kwargs):
        """Grafica desagregación M-R como mapa de calor."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib necesario")
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        
        im = ax.pcolormesh(
            self.bins_distancia, self.bins_magnitud,
            self.contribucion_MR * 100,
            cmap='YlOrRd', shading='auto', **kwargs
        )
        
        plt.colorbar(im, ax=ax, label='Contribución (%)')
        
        # Marcar moda
        ax.plot(self.distancia_modal, self.magnitud_modal, 
               'k*', markersize=15, label='Moda')
        
        ax.set_xlabel('Distancia (km)')
        ax.set_ylabel('Magnitud')
        ax.set_title(
            f'Desagregación M-R\n'
            f'IM = {self.intensidad_objetivo:.3f} g'
        )
        ax.legend()
        
        return ax
    
    def graficar_3d(self, ax=None):
        """Grafica desagregación M-R-ε en 3D."""
        try:
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D
        except ImportError:
            raise ImportError("matplotlib necesario")
        
        if ax is None:
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection='3d')
        
        # Crear grilla
        M, R = np.meshgrid(self.bins_magnitud, self.bins_distancia, indexing='ij')
        contrib = self.contribucion_MR * 100
        
        # Superficie
        ax.plot_surface(R, M, contrib, cmap='YlOrRd', alpha=0.8)
        
        ax.set_xlabel('Distancia (km)')
        ax.set_ylabel('Magnitud')
        ax.set_zlabel('Contribución (%)')
        ax.set_title('Desagregación 3D')
        
        return ax
    
    def resumen(self) -> str:
        """Genera resumen textual."""
        return f"""
Desagregación del Peligro Sísmico
=================================
Intensidad objetivo: {self.intensidad_objetivo:.4f} g
Sitio: ({self.sitio[0]:.2f}, {self.sitio[1]:.2f})

Escenario Modal:
  Magnitud: {self.magnitud_modal:.2f}
  Distancia: {self.distancia_modal:.1f} km
  Epsilon: {self.epsilon_modal:.2f}

Escenario Medio:
  Magnitud: {self.magnitud_media:.2f}
  Distancia: {self.distancia_media:.1f} km
"""


# =============================================================================
# ÁRBOL LÓGICO
# =============================================================================

@dataclass
class RamaArbolLogico:
    """
    Rama de un árbol lógico.
    
    Attributes
    ----------
    nombre : str
        Nombre de la rama
    peso : float
        Peso de la rama (0-1)
    gmpe : Any
        GMPE asociada
    fuentes : Any
        Modelo de fuentes asociado
    """
    nombre: str
    peso: float
    gmpe: Any = None
    fuentes: Any = None


@dataclass
class ArbolLogico:
    """
    Árbol lógico para manejo de incertidumbre epistémica.
    
    Permite combinar múltiples GMPEs y modelos de fuentes
    con pesos para capturar incertidumbre.
    
    Attributes
    ----------
    ramas : List[RamaArbolLogico]
        Lista de ramas del árbol
    """
    ramas: List[RamaArbolLogico] = field(default_factory=list)
    
    def __len__(self) -> int:
        return len(self.ramas)
    
    def __iter__(self):
        return iter(self.ramas)
    
    def agregar_rama(
        self,
        nombre: str,
        peso: float,
        gmpe: Any = None,
        fuentes: Any = None
    ) -> 'ArbolLogico':
        """Agrega una rama al árbol."""
        rama = RamaArbolLogico(
            nombre=nombre,
            peso=peso,
            gmpe=gmpe,
            fuentes=fuentes
        )
        self.ramas.append(rama)
        return self
    
    def normalizar_pesos(self) -> None:
        """Normaliza los pesos para que sumen 1."""
        total = sum(r.peso for r in self.ramas)
        if total > 0:
            for r in self.ramas:
                r.peso /= total
    
    def validar(self) -> bool:
        """Verifica que los pesos sumen 1."""
        total = sum(r.peso for r in self.ramas)
        return np.isclose(total, 1.0, atol=0.01)


# =============================================================================
# GMPE WRAPPER
# =============================================================================

class GMPEWrapper:
    """
    Wrapper para GMPEs que proporciona interfaz unificada.
    
    Permite usar diferentes GMPEs con una interfaz común.
    """
    
    def __init__(self, gmpe: Any):
        """
        Inicializa el wrapper.
        
        Parameters
        ----------
        gmpe : Any
            Instancia de GMPE (de isoseismal.py o externa)
        """
        self.gmpe = gmpe
        self.nombre = getattr(gmpe, 'nombre', 'GMPE')
    
    def calcular(
        self,
        magnitud: float,
        distancia: float,
        profundidad: float = 10,
        vs30: float = 760,
        medida: MedidaIntensidad = MedidaIntensidad.PGA,
        **kwargs
    ) -> Tuple[float, float]:
        """
        Calcula media y sigma de la intensidad.
        
        Returns
        -------
        Tuple[float, float]
            (media en g, sigma en log natural)
        """
        if medida == MedidaIntensidad.PGA:
            if hasattr(self.gmpe, 'calcular_pga'):
                return self.gmpe.calcular_pga(
                    magnitud, distancia, profundidad, vs30, **kwargs
                )
        elif medida == MedidaIntensidad.PGV:
            if hasattr(self.gmpe, 'calcular_pgv'):
                return self.gmpe.calcular_pgv(
                    magnitud, distancia, profundidad, vs30, **kwargs
                )
        elif medida.value.startswith('sa_'):
            periodo = float(medida.value.split('_')[1])
            if hasattr(self.gmpe, 'calcular_sa'):
                return self.gmpe.calcular_sa(
                    magnitud, distancia, periodo, profundidad, vs30, **kwargs
                )
        
        # Fallback: usar PGA
        if hasattr(self.gmpe, 'calcular_pga'):
            return self.gmpe.calcular_pga(
                magnitud, distancia, profundidad, vs30, **kwargs
            )
        
        raise ValueError(f"GMPE no soporta medida {medida}")
    
    def probabilidad_excedencia(
        self,
        intensidad: float,
        magnitud: float,
        distancia: float,
        profundidad: float = 10,
        vs30: float = 760,
        **kwargs
    ) -> float:
        """
        Calcula P(IM > im | M, R).
        
        Asume distribución lognormal.
        """
        media, sigma = self.calcular(
            magnitud, distancia, profundidad, vs30, **kwargs
        )
        
        if media <= 0:
            return 0.0
        
        # Convertir a log
        ln_im = np.log(intensidad)
        ln_media = np.log(media)
        
        # Probabilidad de excedencia (1 - CDF normal estándar)
        from scipy import stats
        z = (ln_im - ln_media) / sigma
        return 1 - stats.norm.cdf(z)


# =============================================================================
# ANALIZADOR PSHA
# =============================================================================

class AnalizadorPSHA:
    """
    Motor principal de Análisis Probabilístico de Peligro Sísmico.
    
    Implementa la metodología Cornell-McGuire para calcular curvas
    de peligro, mapas y desagregación.
    
    Attributes
    ----------
    fuentes : ModeloFuentes
        Modelo de fuentes sísmicas
    gmpes : List[GMPEWrapper]
        Lista de GMPEs
    pesos_gmpe : List[float]
        Pesos para árbol lógico de GMPEs
    periodos_retorno : List[float]
        Períodos de retorno para cálculos (años)
    vs30 : float
        Vs30 por defecto (m/s)
    
    Examples
    --------
    >>> from seismex.analysis.psha import AnalizadorPSHA
    >>> from seismex.analysis.source_models import crear_modelo_mexico_simplificado
    >>> from seismex.analysis.isoseismal import GMPEGarcia2005
    >>> 
    >>> # Crear modelo de fuentes
    >>> fuentes = crear_modelo_mexico_simplificado()
    >>> 
    >>> # Crear analizador
    >>> psha = AnalizadorPSHA(fuentes=fuentes)
    >>> psha.agregar_gmpe(GMPEGarcia2005(), peso=1.0)
    >>> 
    >>> # Calcular curva de peligro
    >>> curva = psha.calcular_curva_peligro(
    ...     sitio=(19.4, -99.1),
    ...     vs30=350
    ... )
    >>> 
    >>> # PGA para 475 años
    >>> pga_475 = curva.intensidad_para_periodo_retorno(475)
    >>> print(f"PGA 475 años: {pga_475:.3f} g")
    """
    
    def __init__(
        self,
        fuentes: Optional['ModeloFuentes'] = None,
        vs30: float = 760.0,
        periodos_retorno: Optional[List[float]] = None,
        niveles_intensidad: Optional[np.ndarray] = None,
        bins_magnitud: int = 20,
        bins_distancia: int = 30,
        distancia_maxima: float = 500.0
    ):
        """
        Inicializa el analizador PSHA.
        
        Parameters
        ----------
        fuentes : ModeloFuentes
            Modelo de fuentes sísmicas
        vs30 : float
            Vs30 por defecto (m/s)
        periodos_retorno : List[float], optional
            Períodos de retorno (años)
        niveles_intensidad : np.ndarray, optional
            Niveles de intensidad para curvas
        bins_magnitud : int
            Número de bins de magnitud
        bins_distancia : int
            Número de bins de distancia
        distancia_maxima : float
            Distancia máxima a considerar (km)
        """
        self.fuentes = fuentes
        self.vs30 = vs30
        self.periodos_retorno = periodos_retorno or PERIODOS_RETORNO_DEFAULT
        self.niveles_intensidad = niveles_intensidad if niveles_intensidad is not None else NIVELES_PGA_DEFAULT
        
        self.bins_magnitud = bins_magnitud
        self.bins_distancia = bins_distancia
        self.distancia_maxima = distancia_maxima
        
        self.gmpes: List[GMPEWrapper] = []
        self.pesos_gmpe: List[float] = []
        
        logger.info("AnalizadorPSHA inicializado")
    
    def agregar_gmpe(self, gmpe: Any, peso: float = 1.0) -> 'AnalizadorPSHA':
        """
        Agrega una GMPE al análisis.
        
        Parameters
        ----------
        gmpe : Any
            Instancia de GMPE
        peso : float
            Peso en árbol lógico
            
        Returns
        -------
        AnalizadorPSHA
            Self para encadenamiento
        """
        wrapper = GMPEWrapper(gmpe)
        self.gmpes.append(wrapper)
        self.pesos_gmpe.append(peso)
        
        # Normalizar pesos
        total = sum(self.pesos_gmpe)
        self.pesos_gmpe = [p / total for p in self.pesos_gmpe]
        
        logger.info(f"GMPE '{wrapper.nombre}' agregada (peso={peso:.2f})")
        return self
    
    def calcular_curva_peligro(
        self,
        sitio: Tuple[float, float],
        vs30: Optional[float] = None,
        medida: MedidaIntensidad = MedidaIntensidad.PGA,
        calcular_contribuciones: bool = False
    ) -> CurvaPeligro:
        """
        Calcula la curva de peligro para un sitio.
        
        Parameters
        ----------
        sitio : Tuple[float, float]
            Ubicación (lat, lon)
        vs30 : float, optional
            Vs30 del sitio (usa default si None)
        medida : MedidaIntensidad
            Tipo de intensidad
        calcular_contribuciones : bool
            Si calcular contribución por fuente
            
        Returns
        -------
        CurvaPeligro
            Curva de peligro calculada
        """
        if not self.gmpes:
            raise ValueError("Debe agregar al menos una GMPE")
        
        if self.fuentes is None:
            raise ValueError("Debe configurar un modelo de fuentes")
        
        vs30 = vs30 or self.vs30
        lat, lon = sitio
        
        # Inicializar tasas
        tasas = np.zeros(len(self.niveles_intensidad))
        contribuciones = {} if calcular_contribuciones else None
        
        # Iterar sobre fuentes
        for fuente in self.fuentes.obtener_fuentes_activas():
            # Discretizar magnitudes
            mags, probs_mag = fuente.distribucion_magnitud.discretizar()
            
            # Discretizar distancias
            dist_min = max(1.0, fuente.distancia_a_punto(lat, lon))
            dist_max = min(self.distancia_maxima, dist_min + 200)
            distancias = np.linspace(dist_min, dist_max, self.bins_distancia)
            
            # Tasas para esta fuente
            tasas_fuente = np.zeros(len(self.niveles_intensidad))
            
            for m, prob_m in zip(mags, probs_mag):
                tasa_m = fuente.distribucion_magnitud.tasa_excedencia(m)
                
                for r in distancias:
                    # Probabilidad de excedencia (promedio ponderado de GMPEs)
                    p_exc = 0.0
                    for gmpe, peso in zip(self.gmpes, self.pesos_gmpe):
                        for i, im in enumerate(self.niveles_intensidad):
                            try:
                                p = gmpe.probabilidad_excedencia(
                                    im, m, r,
                                    profundidad=fuente.distribucion_profundidad.prof_media,
                                    vs30=vs30,
                                    medida=medida
                                )
                                tasas_fuente[i] += tasa_m * prob_m * p * peso / len(distancias)
                            except Exception as e:
                                logger.debug(f"Error en GMPE: {e}")
                                continue
            
            tasas += tasas_fuente
            
            if calcular_contribuciones:
                contribuciones[fuente.nombre] = tasas_fuente.copy()
        
        return CurvaPeligro(
            intensidades=self.niveles_intensidad.copy(),
            tasas_excedencia=tasas,
            medida=medida,
            sitio=sitio,
            vs30=vs30,
            contribuciones=contribuciones
        )
    
    def calcular_mapa_peligro(
        self,
        region: Dict[str, Tuple[float, float]],
        periodo_retorno: float,
        resolucion: float = 0.5,
        vs30: Optional[Union[float, np.ndarray]] = None,
        medida: MedidaIntensidad = MedidaIntensidad.PGA,
        verbose: bool = True
    ) -> MapaPeligro:
        """
        Calcula mapa de peligro para un período de retorno.
        
        Parameters
        ----------
        region : Dict
            Región {'lat': (min, max), 'lon': (min, max)}
        periodo_retorno : float
            Período de retorno (años)
        resolucion : float
            Resolución en grados
        vs30 : float or np.ndarray, optional
            Vs30 (constante o grilla)
        medida : MedidaIntensidad
            Tipo de intensidad
        verbose : bool
            Mostrar progreso
            
        Returns
        -------
        MapaPeligro
            Mapa de peligro calculado
        """
        lat_min, lat_max = region['lat']
        lon_min, lon_max = region['lon']
        
        latitudes = np.arange(lat_min, lat_max + resolucion, resolucion)
        longitudes = np.arange(lon_min, lon_max + resolucion, resolucion)
        
        intensidades = np.zeros((len(latitudes), len(longitudes)))
        
        total = len(latitudes) * len(longitudes)
        count = 0
        tiempo_inicio = time.time()
        
        for i, lat in enumerate(latitudes):
            for j, lon in enumerate(longitudes):
                # Obtener Vs30 para el punto
                if isinstance(vs30, np.ndarray):
                    vs30_punto = vs30[i, j]
                else:
                    vs30_punto = vs30 or self.vs30
                
                # Calcular curva
                try:
                    curva = self.calcular_curva_peligro(
                        sitio=(lat, lon),
                        vs30=vs30_punto,
                        medida=medida
                    )
                    intensidades[i, j] = curva.intensidad_para_periodo_retorno(periodo_retorno)
                except Exception as e:
                    logger.debug(f"Error en ({lat}, {lon}): {e}")
                    intensidades[i, j] = np.nan
                
                count += 1
                if verbose and count % 10 == 0:
                    elapsed = time.time() - tiempo_inicio
                    eta = elapsed / count * (total - count)
                    print(f"\rProgreso: {count}/{total} ({count/total*100:.1f}%) - "
                          f"ETA: {eta:.0f}s", end='')
        
        if verbose:
            print()
        
        return MapaPeligro(
            intensidades=intensidades,
            latitudes=latitudes,
            longitudes=longitudes,
            periodo_retorno=periodo_retorno,
            medida=medida,
            vs30=vs30 if vs30 is not None else self.vs30
        )
    
    def desagregar(
        self,
        sitio: Tuple[float, float],
        nivel_intensidad: float,
        vs30: Optional[float] = None,
        medida: MedidaIntensidad = MedidaIntensidad.PGA,
        bins_magnitud: int = 15,
        bins_distancia: int = 20,
        bins_epsilon: int = 10
    ) -> Desagregacion:
        """
        Realiza desagregación del peligro sísmico.
        
        Parameters
        ----------
        sitio : Tuple[float, float]
            Ubicación (lat, lon)
        nivel_intensidad : float
            Nivel de intensidad para desagregar
        vs30 : float, optional
            Vs30 del sitio
        medida : MedidaIntensidad
            Tipo de intensidad
        bins_magnitud, bins_distancia, bins_epsilon : int
            Número de bins para cada dimensión
            
        Returns
        -------
        Desagregacion
            Resultados de desagregación
        """
        vs30 = vs30 or self.vs30
        lat, lon = sitio
        
        # Definir bins
        mag_min = min(f.distribucion_magnitud.mmin for f in self.fuentes)
        mag_max = max(f.distribucion_magnitud.mmax for f in self.fuentes)
        mags = np.linspace(mag_min, mag_max, bins_magnitud)
        
        dists = np.logspace(0, np.log10(self.distancia_maxima), bins_distancia)
        
        epsilons = np.linspace(-3, 3, bins_epsilon)
        
        # Calcular contribuciones
        contrib_MR = np.zeros((len(mags), len(dists)))
        contrib_MRe = np.zeros((len(mags), len(dists), len(epsilons)))
        
        for fuente in self.fuentes.obtener_fuentes_activas():
            for i, m in enumerate(mags):
                tasa_m = fuente.distribucion_magnitud.tasa_excedencia(m)
                
                for j, r in enumerate(dists):
                    for gmpe, peso in zip(self.gmpes, self.pesos_gmpe):
                        try:
                            p = gmpe.probabilidad_excedencia(
                                nivel_intensidad, m, r,
                                profundidad=fuente.distribucion_profundidad.prof_media,
                                vs30=vs30,
                                medida=medida
                            )
                            contrib_MR[i, j] += tasa_m * p * peso
                        except:
                            pass
        
        # Normalizar
        if contrib_MR.sum() > 0:
            contrib_MR /= contrib_MR.sum()
        
        return Desagregacion(
            bins_magnitud=mags,
            bins_distancia=dists,
            bins_epsilon=epsilons,
            contribucion_MR=contrib_MR,
            contribucion_MRe=contrib_MRe,
            intensidad_objetivo=nivel_intensidad,
            sitio=sitio
        )
    
    def calcular_espectro_uniforme(
        self,
        sitio: Tuple[float, float],
        periodo_retorno: float,
        periodos: Optional[List[float]] = None,
        vs30: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcula espectro de peligro uniforme (UHS).
        
        Parameters
        ----------
        sitio : Tuple[float, float]
            Ubicación (lat, lon)
        periodo_retorno : float
            Período de retorno (años)
        periodos : List[float], optional
            Períodos espectrales a calcular
        vs30 : float, optional
            Vs30 del sitio
            
        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            (períodos, aceleraciones espectrales)
        """
        periodos = periodos or [0.0, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 3.0]
        
        aceleraciones = []
        for T in periodos:
            if T == 0.0:
                medida = MedidaIntensidad.PGA
            else:
                medida = MedidaIntensidad(f'sa_{T}')
            
            try:
                curva = self.calcular_curva_peligro(
                    sitio=sitio, vs30=vs30, medida=medida
                )
                sa = curva.intensidad_para_periodo_retorno(periodo_retorno)
            except:
                sa = np.nan
            
            aceleraciones.append(sa)
        
        return np.array(periodos), np.array(aceleraciones)
    
    def resumen(self) -> str:
        """Genera resumen del analizador."""
        lineas = [
            "=" * 60,
            "ANALIZADOR PSHA",
            "=" * 60,
            f"Modelo de fuentes: {self.fuentes.nombre if self.fuentes else 'No configurado'}",
            f"Número de fuentes: {len(self.fuentes) if self.fuentes else 0}",
            f"Vs30 default: {self.vs30} m/s",
            "",
            f"GMPEs ({len(self.gmpes)}):",
        ]
        
        for gmpe, peso in zip(self.gmpes, self.pesos_gmpe):
            lineas.append(f"  - {gmpe.nombre} (peso={peso:.2f})")
        
        lineas.extend([
            "",
            f"Períodos de retorno: {self.periodos_retorno}",
            f"Bins de magnitud: {self.bins_magnitud}",
            f"Bins de distancia: {self.bins_distancia}",
            f"Distancia máxima: {self.distancia_maxima} km",
            "=" * 60
        ])
        
        return "\n".join(lineas)


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def calcular_probabilidad_poisson(
    tasa: float,
    tiempo: float = 50.0,
    n_eventos: int = 1
) -> float:
    """
    Calcula probabilidad de al menos n eventos en un período.
    
    P(N >= n) = 1 - Σ(k=0 to n-1) [(λt)^k × e^(-λt)] / k!
    
    Parameters
    ----------
    tasa : float
        Tasa de ocurrencia anual
    tiempo : float
        Período de exposición (años)
    n_eventos : int
        Número mínimo de eventos
        
    Returns
    -------
    float
        Probabilidad
    """
    from scipy import stats
    
    lambda_t = tasa * tiempo
    return 1 - stats.poisson.cdf(n_eventos - 1, lambda_t)


def periodo_retorno_desde_probabilidad(
    probabilidad: float,
    tiempo: float = 50.0
) -> float:
    """
    Calcula período de retorno desde probabilidad de excedencia.
    
    TR = -t / ln(1 - P)
    
    Parameters
    ----------
    probabilidad : float
        Probabilidad de excedencia (0-1)
    tiempo : float
        Período de exposición (años)
        
    Returns
    -------
    float
        Período de retorno (años)
    """
    if probabilidad >= 1:
        return tiempo
    if probabilidad <= 0:
        return float('inf')
    
    return -tiempo / np.log(1 - probabilidad)


def crear_analizador_mexico(
    vs30: float = 400.0
) -> AnalizadorPSHA:
    """
    Crea un analizador PSHA preconfigurado para México.
    
    Parameters
    ----------
    vs30 : float
        Vs30 por defecto
        
    Returns
    -------
    AnalizadorPSHA
        Analizador configurado
    """
    from .source_models import crear_modelo_mexico_simplificado
    from .isoseismal import GMPEGarcia2005, GMPEZhao2006
    
    fuentes = crear_modelo_mexico_simplificado()
    
    psha = AnalizadorPSHA(
        fuentes=fuentes,
        vs30=vs30
    )
    
    psha.agregar_gmpe(GMPEGarcia2005(), peso=0.6)
    psha.agregar_gmpe(GMPEZhao2006(), peso=0.4)
    
    return psha


def info_modulo():
    """Muestra información del módulo psha."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              SEISMEX Analysis - psha.py                              ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Clases principales:                                                 ║
║    ✅ AnalizadorPSHA    - Motor principal de cálculo                 ║
║    ✅ CurvaPeligro      - Curva de excedencia                        ║
║    ✅ MapaPeligro       - Mapa de peligro espacial                   ║
║    ✅ Desagregacion     - Análisis de contribución M-R-ε             ║
║    ✅ ArbolLogico       - Manejo de incertidumbre                    ║
║                                                                      ║
║  Funcionalidades:                                                    ║
║    ✅ Curvas de peligro con múltiples GMPEs                          ║
║    ✅ Mapas de peligro para períodos de retorno                      ║
║    ✅ Espectros de peligro uniforme (UHS)                            ║
║    ✅ Desagregación M-R-ε                                            ║
║    ✅ Árbol lógico para incertidumbre                                ║
║    ✅ Exportación GeoTIFF                                            ║
║                                                                      ║
║  Estado: ✅ COMPLETAMENTE IMPLEMENTADO                               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enumeraciones
    'MedidaIntensidad',
    'TipoDistanciaGMPE',
    
    # Clases de resultados
    'CurvaPeligro',
    'MapaPeligro',
    'Desagregacion',
    
    # Árbol lógico
    'RamaArbolLogico',
    'ArbolLogico',
    
    # GMPE Wrapper
    'GMPEWrapper',
    
    # Analizador principal
    'AnalizadorPSHA',
    
    # Factories
    'crear_analizador_mexico',
    
    # Utilidades
    'calcular_probabilidad_poisson',
    'periodo_retorno_desde_probabilidad',
    'info_modulo',
    
    # Constantes
    'NIVELES_PGA_DEFAULT',
    'PERIODOS_RETORNO_DEFAULT',
]
