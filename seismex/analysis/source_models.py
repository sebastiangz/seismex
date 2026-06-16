#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX Analysis - Modelos de Fuentes Sísmicas
================================================================================

Modelos de fuentes sísmicas para análisis probabilístico de peligro sísmico
(PSHA). Implementa fuentes de área, fallas y fuentes puntuales con sus
respectivas distribuciones de magnitud y recurrencia.

Componentes principales:
    - FuenteSismica: Clase base abstracta
    - FuenteArea: Zonas sismogénicas de área
    - FuenteFalla: Fallas activas con geometría
    - FuentePuntual: Fuentes puntuales (volcanes, etc.)
    - ModeloFuentes: Contenedor de múltiples fuentes
    - DistribucionMagnitud: Distribuciones de magnitud (G-R, característico)

Referencias:
    - Cornell, C.A. (1968). Engineering seismic risk analysis. BSSA.
    - Youngs, R.R. & Coppersmith, K.J. (1985). Implications of fault slip
      rates and earthquake recurrence models. BSSA, 75(4), 939-964.
    - Gutenberg, B. & Richter, C.F. (1944). Frequency of earthquakes in
      California. BSSA, 34(4), 185-188.

Estado: ✅ IMPLEMENTADO

Autor: SEISMEX Team
Versión: 1.0.0
================================================================================
"""

from __future__ import annotations

import logging
import json
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
    Iterator,
    TYPE_CHECKING
)
import numpy as np

if TYPE_CHECKING:
    import geopandas as gpd
    from shapely.geometry import Polygon, LineString, Point

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Conversión slip rate a momento sísmico
MU_CORTEZA = 3.0e11  # Rigidez de la corteza (dyn/cm²)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoFuente(Enum):
    """Tipos de fuentes sísmicas."""
    AREA = "area"
    FALLA = "falla"
    PUNTUAL = "puntual"
    SUBDUCCION = "subduccion"


class TipoFalla(Enum):
    """Tipos de mecanismo de falla."""
    NORMAL = "normal"
    INVERSA = "inversa"
    LATERAL_DERECHA = "lateral_derecha"
    LATERAL_IZQUIERDA = "lateral_izquierda"
    OBLICUA = "oblicua"
    DESCONOCIDO = "desconocido"


class TipoDistribucionMagnitud(Enum):
    """Tipos de distribución de magnitud."""
    GUTENBERG_RICHTER = "gutenberg_richter"
    TRUNCADA = "truncada"
    CARACTERISTICA = "caracteristica"
    YOUNGS_COPPERSMITH = "youngs_coppersmith"


class TipoDistribucionProfundidad(Enum):
    """Tipos de distribución de profundidad."""
    UNIFORME = "uniforme"
    TRIANGULAR = "triangular"
    GAUSSIANA = "gaussiana"
    FIJA = "fija"


# =============================================================================
# DISTRIBUCIONES DE MAGNITUD
# =============================================================================

@dataclass
class DistribucionMagnitud(ABC):
    """
    Clase base abstracta para distribuciones de magnitud.
    
    Attributes
    ----------
    mmin : float
        Magnitud mínima
    mmax : float
        Magnitud máxima
    bin_width : float
        Ancho de bin para discretización
    """
    mmin: float
    mmax: float
    bin_width: float = 0.1
    
    @abstractmethod
    def pdf(self, magnitud: float) -> float:
        """Función de densidad de probabilidad."""
        pass
    
    @abstractmethod
    def cdf(self, magnitud: float) -> float:
        """Función de distribución acumulada."""
        pass
    
    @abstractmethod
    def tasa_excedencia(self, magnitud: float) -> float:
        """Tasa de excedencia (eventos/año >= M)."""
        pass
    
    def discretizar(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Discretiza la distribución en bins.
        
        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            (magnitudes centrales, probabilidades)
        """
        magnitudes = np.arange(self.mmin, self.mmax + self.bin_width, self.bin_width)
        probabilidades = np.array([self.pdf(m) for m in magnitudes])
        probabilidades /= probabilidades.sum()  # Normalizar
        return magnitudes, probabilidades


@dataclass
class DistribucionGutenbergRichter(DistribucionMagnitud):
    """
    Distribución Gutenberg-Richter truncada.
    
    N(M) = 10^(a - b*M) para Mmin <= M <= Mmax
    
    Attributes
    ----------
    a_value : float
        Parámetro a (log10 de tasa de sismicidad)
    b_value : float
        Parámetro b (pendiente, típicamente ~1.0)
    """
    a_value: float = 4.0
    b_value: float = 1.0
    
    def __post_init__(self):
        """Calcula constante de normalización."""
        beta = self.b_value * np.log(10)
        self._beta = beta
        # Factor de normalización para distribución truncada
        self._norm = (1 - np.exp(-beta * (self.mmax - self.mmin)))
    
    def pdf(self, magnitud: float) -> float:
        """PDF de G-R truncada."""
        if magnitud < self.mmin or magnitud > self.mmax:
            return 0.0
        
        beta = self._beta
        return (beta * np.exp(-beta * (magnitud - self.mmin))) / self._norm
    
    def cdf(self, magnitud: float) -> float:
        """CDF de G-R truncada."""
        if magnitud <= self.mmin:
            return 0.0
        if magnitud >= self.mmax:
            return 1.0
        
        beta = self._beta
        return (1 - np.exp(-beta * (magnitud - self.mmin))) / self._norm
    
    def tasa_excedencia(self, magnitud: float) -> float:
        """Tasa de excedencia N(M) = eventos/año con mag >= M."""
        if magnitud < self.mmin:
            magnitud = self.mmin
        if magnitud > self.mmax:
            return 0.0
        
        # N(M) = 10^(a - b*M)
        return 10 ** (self.a_value - self.b_value * magnitud)
    
    def tasa_total(self) -> float:
        """Tasa total de eventos (>= Mmin) por año."""
        return self.tasa_excedencia(self.mmin)


@dataclass
class DistribucionCaracteristica(DistribucionMagnitud):
    """
    Distribución de magnitud característica (Youngs & Coppersmith, 1985).
    
    Combina G-R para magnitudes bajas con un pico característico
    para magnitudes cercanas a Mmax.
    
    Attributes
    ----------
    a_value : float
        Parámetro a de G-R
    b_value : float
        Parámetro b de G-R
    m_char : float
        Magnitud característica
    sigma_char : float
        Desviación estándar de la magnitud característica
    peso_char : float
        Peso relativo del componente característico (0-1)
    """
    a_value: float = 4.0
    b_value: float = 1.0
    m_char: float = 7.0
    sigma_char: float = 0.2
    peso_char: float = 0.5
    
    def __post_init__(self):
        """Inicializa componentes."""
        self._gr = DistribucionGutenbergRichter(
            mmin=self.mmin,
            mmax=self.m_char - 0.5,
            a_value=self.a_value,
            b_value=self.b_value
        )
    
    def pdf(self, magnitud: float) -> float:
        """PDF combinada G-R + característica."""
        if magnitud < self.mmin or magnitud > self.mmax:
            return 0.0
        
        # Componente G-R
        pdf_gr = self._gr.pdf(magnitud) if magnitud < self.m_char - 0.5 else 0.0
        
        # Componente característico (gaussiano)
        pdf_char = np.exp(-0.5 * ((magnitud - self.m_char) / self.sigma_char) ** 2)
        pdf_char /= (self.sigma_char * np.sqrt(2 * np.pi))
        
        return (1 - self.peso_char) * pdf_gr + self.peso_char * pdf_char
    
    def cdf(self, magnitud: float) -> float:
        """CDF aproximada."""
        if magnitud <= self.mmin:
            return 0.0
        if magnitud >= self.mmax:
            return 1.0
        
        # Integración numérica simple
        mags = np.linspace(self.mmin, magnitud, 100)
        pdfs = np.array([self.pdf(m) for m in mags])
        return np.trapz(pdfs, mags)
    
    def tasa_excedencia(self, magnitud: float) -> float:
        """Tasa de excedencia combinada."""
        tasa_gr = self._gr.tasa_excedencia(magnitud)
        
        # Tasa del componente característico
        from scipy import stats
        p_char = 1 - stats.norm.cdf(magnitud, self.m_char, self.sigma_char)
        tasa_char = self.tasa_total() * self.peso_char * p_char
        
        return (1 - self.peso_char) * tasa_gr + tasa_char
    
    def tasa_total(self) -> float:
        """Tasa total de eventos por año."""
        return 10 ** (self.a_value - self.b_value * self.mmin)


# =============================================================================
# DISTRIBUCIONES DE PROFUNDIDAD
# =============================================================================

@dataclass
class DistribucionProfundidad:
    """
    Distribución de profundidad hipocentral.
    
    Attributes
    ----------
    tipo : TipoDistribucionProfundidad
        Tipo de distribución
    prof_min : float
        Profundidad mínima (km)
    prof_max : float
        Profundidad máxima (km)
    prof_media : float
        Profundidad media (km)
    prof_sigma : float
        Desviación estándar (km)
    """
    tipo: TipoDistribucionProfundidad = TipoDistribucionProfundidad.UNIFORME
    prof_min: float = 0.0
    prof_max: float = 30.0
    prof_media: float = 15.0
    prof_sigma: float = 5.0
    
    def muestrear(self, n: int = 1, seed: Optional[int] = None) -> np.ndarray:
        """
        Muestrea n profundidades de la distribución.
        
        Parameters
        ----------
        n : int
            Número de muestras
        seed : int, optional
            Semilla para reproducibilidad
            
        Returns
        -------
        np.ndarray
            Profundidades muestreadas (km)
        """
        rng = np.random.default_rng(seed)
        
        if self.tipo == TipoDistribucionProfundidad.FIJA:
            return np.full(n, self.prof_media)
        
        elif self.tipo == TipoDistribucionProfundidad.UNIFORME:
            return rng.uniform(self.prof_min, self.prof_max, n)
        
        elif self.tipo == TipoDistribucionProfundidad.TRIANGULAR:
            return rng.triangular(self.prof_min, self.prof_media, self.prof_max, n)
        
        elif self.tipo == TipoDistribucionProfundidad.GAUSSIANA:
            profs = rng.normal(self.prof_media, self.prof_sigma, n)
            return np.clip(profs, self.prof_min, self.prof_max)
        
        return np.full(n, self.prof_media)
    
    def pdf(self, profundidad: float) -> float:
        """Función de densidad de probabilidad."""
        if profundidad < self.prof_min or profundidad > self.prof_max:
            return 0.0
        
        if self.tipo == TipoDistribucionProfundidad.FIJA:
            return 1.0 if np.isclose(profundidad, self.prof_media) else 0.0
        
        elif self.tipo == TipoDistribucionProfundidad.UNIFORME:
            return 1.0 / (self.prof_max - self.prof_min)
        
        elif self.tipo == TipoDistribucionProfundidad.TRIANGULAR:
            h = self.prof_media
            a, b = self.prof_min, self.prof_max
            if profundidad < h:
                return 2 * (profundidad - a) / ((b - a) * (h - a))
            else:
                return 2 * (b - profundidad) / ((b - a) * (b - h))
        
        elif self.tipo == TipoDistribucionProfundidad.GAUSSIANA:
            return np.exp(-0.5 * ((profundidad - self.prof_media) / self.prof_sigma) ** 2)
        
        return 0.0


# =============================================================================
# FUENTES SÍSMICAS
# =============================================================================

@dataclass
class FuenteSismica(ABC):
    """
    Clase base abstracta para fuentes sísmicas.
    
    Attributes
    ----------
    nombre : str
        Nombre identificador de la fuente
    tipo : TipoFuente
        Tipo de fuente
    distribucion_magnitud : DistribucionMagnitud
        Distribución de magnitud
    distribucion_profundidad : DistribucionProfundidad
        Distribución de profundidad
    activa : bool
        Si la fuente está activa en el modelo
    peso : float
        Peso en árbol lógico (0-1)
    metadata : Dict
        Metadatos adicionales
    """
    nombre: str
    tipo: TipoFuente
    distribucion_magnitud: DistribucionMagnitud
    distribucion_profundidad: DistribucionProfundidad = field(
        default_factory=DistribucionProfundidad
    )
    activa: bool = True
    peso: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @abstractmethod
    def contiene_punto(self, lat: float, lon: float) -> bool:
        """Verifica si un punto está dentro de la fuente."""
        pass
    
    @abstractmethod
    def distancia_a_punto(self, lat: float, lon: float) -> float:
        """Calcula distancia mínima a un punto (km)."""
        pass
    
    @abstractmethod
    def muestrear_ubicaciones(self, n: int, seed: Optional[int] = None) -> np.ndarray:
        """Muestrea n ubicaciones dentro de la fuente."""
        pass
    
    @abstractmethod
    def area_km2(self) -> float:
        """Retorna el área de la fuente en km²."""
        pass
    
    def tasa_total(self) -> float:
        """Retorna la tasa total de eventos por año."""
        return self.distribucion_magnitud.tasa_total()
    
    def muestrear_eventos(
        self,
        n: int,
        seed: Optional[int] = None
    ) -> List[Dict[str, float]]:
        """
        Muestrea n eventos sintéticos de la fuente.
        
        Returns
        -------
        List[Dict]
            Lista de eventos con 'lat', 'lon', 'profundidad', 'magnitud'
        """
        rng = np.random.default_rng(seed)
        
        # Muestrear ubicaciones
        ubicaciones = self.muestrear_ubicaciones(n, seed)
        
        # Muestrear profundidades
        profundidades = self.distribucion_profundidad.muestrear(n, seed)
        
        # Muestrear magnitudes
        mags, probs = self.distribucion_magnitud.discretizar()
        magnitudes = rng.choice(mags, size=n, p=probs)
        
        eventos = []
        for i in range(n):
            eventos.append({
                'lat': ubicaciones[i, 0],
                'lon': ubicaciones[i, 1],
                'profundidad_km': profundidades[i],
                'magnitud': magnitudes[i],
                'fuente': self.nombre
            })
        
        return eventos
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'nombre': self.nombre,
            'tipo': self.tipo.value,
            'mmin': self.distribucion_magnitud.mmin,
            'mmax': self.distribucion_magnitud.mmax,
            'tasa_total': self.tasa_total(),
            'area_km2': self.area_km2(),
            'activa': self.activa,
            'peso': self.peso,
            'metadata': self.metadata
        }


@dataclass
class FuenteArea(FuenteSismica):
    """
    Fuente sísmica de área (zona sismogénica).
    
    Representa una región donde los sismos se distribuyen uniformemente.
    
    Attributes
    ----------
    poligono : List[Tuple[float, float]]
        Vértices del polígono [(lat, lon), ...]
    """
    poligono: List[Tuple[float, float]] = field(default_factory=list)
    tipo: TipoFuente = TipoFuente.AREA
    
    def __post_init__(self):
        """Calcula bounding box."""
        if self.poligono:
            lats = [p[0] for p in self.poligono]
            lons = [p[1] for p in self.poligono]
            self._bbox = (min(lats), max(lats), min(lons), max(lons))
        else:
            self._bbox = (0, 0, 0, 0)
    
    def contiene_punto(self, lat: float, lon: float) -> bool:
        """Ray casting algorithm."""
        if not self.poligono:
            return False
        
        n = len(self.poligono)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = self.poligono[i]
            xj, yj = self.poligono[j]
            
            if ((yi > lon) != (yj > lon)) and \
               (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    def distancia_a_punto(self, lat: float, lon: float) -> float:
        """Distancia mínima al borde del polígono."""
        if self.contiene_punto(lat, lon):
            return 0.0
        
        # Distancia mínima a cualquier vértice
        dist_min = float('inf')
        for plat, plon in self.poligono:
            dist = self._distancia_haversine(lat, lon, plat, plon)
            dist_min = min(dist_min, dist)
        
        return dist_min
    
    def muestrear_ubicaciones(self, n: int, seed: Optional[int] = None) -> np.ndarray:
        """Muestrea ubicaciones uniformemente dentro del polígono."""
        rng = np.random.default_rng(seed)
        
        lat_min, lat_max, lon_min, lon_max = self._bbox
        
        ubicaciones = []
        intentos = 0
        max_intentos = n * 100
        
        while len(ubicaciones) < n and intentos < max_intentos:
            lat = rng.uniform(lat_min, lat_max)
            lon = rng.uniform(lon_min, lon_max)
            
            if self.contiene_punto(lat, lon):
                ubicaciones.append([lat, lon])
            
            intentos += 1
        
        # Si no se logró, llenar con centroide
        if len(ubicaciones) < n:
            centroide = self._centroide()
            while len(ubicaciones) < n:
                ubicaciones.append(list(centroide))
        
        return np.array(ubicaciones)
    
    def area_km2(self) -> float:
        """Calcula área aproximada usando fórmula del polígono."""
        if len(self.poligono) < 3:
            return 0.0
        
        # Aproximación usando grados a km
        n = len(self.poligono)
        area = 0.0
        
        for i in range(n):
            j = (i + 1) % n
            lat1, lon1 = self.poligono[i]
            lat2, lon2 = self.poligono[j]
            area += lon1 * lat2 - lon2 * lat1
        
        area = abs(area) / 2.0
        
        # Convertir grados² a km² (aproximación)
        lat_media = np.mean([p[0] for p in self.poligono])
        km_por_grado_lat = 111.0
        km_por_grado_lon = 111.0 * np.cos(np.radians(lat_media))
        
        return area * km_por_grado_lat * km_por_grado_lon
    
    def _centroide(self) -> Tuple[float, float]:
        """Calcula centroide del polígono."""
        if not self.poligono:
            return (0, 0)
        lats = [p[0] for p in self.poligono]
        lons = [p[1] for p in self.poligono]
        return (np.mean(lats), np.mean(lons))
    
    @staticmethod
    def _distancia_haversine(lat1, lon1, lat2, lon2) -> float:
        """Distancia Haversine en km."""
        R = 6371.0
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))


@dataclass
class FuenteFalla(FuenteSismica):
    """
    Fuente sísmica de falla.
    
    Representa una falla activa con geometría y características
    para cálculo de momento sísmico y recurrencia.
    
    Attributes
    ----------
    traza : List[Tuple[float, float]]
        Puntos de la traza de falla [(lat, lon), ...]
    longitud_km : float
        Longitud de la falla (km)
    ancho_km : float
        Ancho de la falla (km) - down-dip
    buzamiento : float
        Ángulo de buzamiento (grados)
    rake : float
        Ángulo de rake (grados)
    tipo_falla : TipoFalla
        Mecanismo de falla
    slip_rate_mm_yr : float
        Tasa de deslizamiento (mm/año)
    """
    traza: List[Tuple[float, float]] = field(default_factory=list)
    longitud_km: float = 50.0
    ancho_km: float = 15.0
    buzamiento: float = 45.0
    rake: float = 90.0
    tipo_falla: TipoFalla = TipoFalla.INVERSA
    slip_rate_mm_yr: float = 1.0
    tipo: TipoFuente = TipoFuente.FALLA
    
    def contiene_punto(self, lat: float, lon: float) -> bool:
        """Una falla no 'contiene' puntos, retorna False."""
        return False
    
    def distancia_a_punto(self, lat: float, lon: float) -> float:
        """Distancia mínima a la traza de falla."""
        if not self.traza:
            return float('inf')
        
        dist_min = float('inf')
        for i in range(len(self.traza) - 1):
            lat1, lon1 = self.traza[i]
            lat2, lon2 = self.traza[i + 1]
            
            # Distancia a segmento (simplificado: distancia a puntos)
            d1 = self._distancia_haversine(lat, lon, lat1, lon1)
            d2 = self._distancia_haversine(lat, lon, lat2, lon2)
            dist_min = min(dist_min, d1, d2)
        
        return dist_min
    
    def muestrear_ubicaciones(self, n: int, seed: Optional[int] = None) -> np.ndarray:
        """Muestrea ubicaciones a lo largo de la traza."""
        rng = np.random.default_rng(seed)
        
        if len(self.traza) < 2:
            return np.zeros((n, 2))
        
        # Muestrear puntos a lo largo de la traza
        ubicaciones = []
        for _ in range(n):
            # Seleccionar segmento aleatorio
            idx = rng.integers(0, len(self.traza) - 1)
            lat1, lon1 = self.traza[idx]
            lat2, lon2 = self.traza[idx + 1]
            
            # Punto aleatorio en el segmento
            t = rng.random()
            lat = lat1 + t * (lat2 - lat1)
            lon = lon1 + t * (lon2 - lon1)
            
            ubicaciones.append([lat, lon])
        
        return np.array(ubicaciones)
    
    def area_km2(self) -> float:
        """Área de ruptura de la falla."""
        return self.longitud_km * self.ancho_km
    
    def momento_sismico_anual(self) -> float:
        """
        Calcula momento sísmico liberado anualmente.
        
        M0 = μ × A × slip_rate
        
        Returns
        -------
        float
            Momento sísmico en dyn·cm/año
        """
        area_cm2 = self.area_km2() * 1e10  # km² a cm²
        slip_cm = self.slip_rate_mm_yr / 10  # mm/año a cm/año
        return MU_CORTEZA * area_cm2 * slip_cm
    
    def magnitud_maxima_wells_coppersmith(self) -> float:
        """
        Estima Mmax usando relaciones de Wells & Coppersmith (1994).
        
        Returns
        -------
        float
            Magnitud máxima estimada
        """
        # Mw = a + b × log10(L) para diferentes mecanismos
        L = self.longitud_km
        
        if self.tipo_falla == TipoFalla.NORMAL:
            a, b = 4.86, 1.32
        elif self.tipo_falla == TipoFalla.INVERSA:
            a, b = 4.33, 1.49
        elif self.tipo_falla in [TipoFalla.LATERAL_DERECHA, TipoFalla.LATERAL_IZQUIERDA]:
            a, b = 5.16, 1.12
        else:
            a, b = 5.08, 1.16  # All types
        
        return a + b * np.log10(L)
    
    @staticmethod
    def _distancia_haversine(lat1, lon1, lat2, lon2) -> float:
        R = 6371.0
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))


@dataclass
class FuentePuntual(FuenteSismica):
    """
    Fuente sísmica puntual.
    
    Representa una fuente concentrada (volcán, zona específica).
    
    Attributes
    ----------
    latitud : float
        Latitud de la fuente
    longitud : float
        Longitud de la fuente
    radio_km : float
        Radio de influencia para muestreo
    """
    latitud: float = 0.0
    longitud: float = 0.0
    radio_km: float = 10.0
    tipo: TipoFuente = TipoFuente.PUNTUAL
    
    def contiene_punto(self, lat: float, lon: float) -> bool:
        """Verifica si el punto está dentro del radio."""
        dist = self.distancia_a_punto(lat, lon)
        return dist <= self.radio_km
    
    def distancia_a_punto(self, lat: float, lon: float) -> float:
        """Distancia al centro de la fuente."""
        return self._distancia_haversine(lat, lon, self.latitud, self.longitud)
    
    def muestrear_ubicaciones(self, n: int, seed: Optional[int] = None) -> np.ndarray:
        """Muestrea ubicaciones alrededor del punto central."""
        rng = np.random.default_rng(seed)
        
        ubicaciones = []
        for _ in range(n):
            # Muestrear distancia y ángulo
            r = rng.uniform(0, self.radio_km)
            theta = rng.uniform(0, 2 * np.pi)
            
            # Convertir a desplazamiento en grados
            dlat = (r * np.cos(theta)) / 111.0
            dlon = (r * np.sin(theta)) / (111.0 * np.cos(np.radians(self.latitud)))
            
            ubicaciones.append([self.latitud + dlat, self.longitud + dlon])
        
        return np.array(ubicaciones)
    
    def area_km2(self) -> float:
        """Área del círculo de influencia."""
        return np.pi * self.radio_km ** 2
    
    @staticmethod
    def _distancia_haversine(lat1, lon1, lat2, lon2) -> float:
        R = 6371.0
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))


# =============================================================================
# MODELO DE FUENTES
# =============================================================================

@dataclass
class ModeloFuentes:
    """
    Contenedor de múltiples fuentes sísmicas.
    
    Gestiona un conjunto de fuentes para análisis PSHA,
    incluyendo pesos de árbol lógico.
    
    Attributes
    ----------
    nombre : str
        Nombre del modelo
    fuentes : List[FuenteSismica]
        Lista de fuentes sísmicas
    descripcion : str
        Descripción del modelo
    version : str
        Versión del modelo
    """
    nombre: str = "Modelo de Fuentes"
    fuentes: List[FuenteSismica] = field(default_factory=list)
    descripcion: str = ""
    version: str = "1.0"
    
    def __len__(self) -> int:
        return len(self.fuentes)
    
    def __iter__(self) -> Iterator[FuenteSismica]:
        return iter(self.fuentes)
    
    def __getitem__(self, idx) -> FuenteSismica:
        if isinstance(idx, str):
            for f in self.fuentes:
                if f.nombre == idx:
                    return f
            raise KeyError(f"Fuente '{idx}' no encontrada")
        return self.fuentes[idx]
    
    def agregar_fuente(self, fuente: FuenteSismica) -> 'ModeloFuentes':
        """Agrega una fuente al modelo."""
        self.fuentes.append(fuente)
        logger.info(f"Fuente '{fuente.nombre}' agregada al modelo")
        return self
    
    def agregar_zona_area(
        self,
        nombre: str,
        poligono: List[Tuple[float, float]],
        a_value: float,
        b_value: float,
        mmin: float = 4.0,
        mmax: float = 8.0,
        profundidad_media: float = 15.0,
        **kwargs
    ) -> 'ModeloFuentes':
        """
        Agrega una zona de área al modelo.
        
        Parameters
        ----------
        nombre : str
            Nombre de la zona
        poligono : List[Tuple[float, float]]
            Vértices del polígono
        a_value, b_value : float
            Parámetros G-R
        mmin, mmax : float
            Rango de magnitudes
        profundidad_media : float
            Profundidad media (km)
            
        Returns
        -------
        ModeloFuentes
            Self para encadenamiento
        """
        dist_mag = DistribucionGutenbergRichter(
            mmin=mmin, mmax=mmax, a_value=a_value, b_value=b_value
        )
        dist_prof = DistribucionProfundidad(
            prof_media=profundidad_media,
            prof_min=profundidad_media - 10,
            prof_max=profundidad_media + 10
        )
        
        fuente = FuenteArea(
            nombre=nombre,
            poligono=poligono,
            distribucion_magnitud=dist_mag,
            distribucion_profundidad=dist_prof,
            **kwargs
        )
        
        return self.agregar_fuente(fuente)
    
    def agregar_falla(
        self,
        nombre: str,
        traza: List[Tuple[float, float]],
        longitud_km: float,
        ancho_km: float,
        buzamiento: float,
        slip_rate_mm_yr: float,
        tipo_falla: TipoFalla,
        mmin: float = 5.0,
        mmax: Optional[float] = None,
        a_value: float = 3.5,
        b_value: float = 1.0,
        **kwargs
    ) -> 'ModeloFuentes':
        """
        Agrega una falla al modelo.
        
        Parameters
        ----------
        nombre : str
            Nombre de la falla
        traza : List[Tuple[float, float]]
            Puntos de la traza
        longitud_km, ancho_km : float
            Dimensiones de la falla
        buzamiento : float
            Ángulo de buzamiento (grados)
        slip_rate_mm_yr : float
            Tasa de deslizamiento (mm/año)
        tipo_falla : TipoFalla
            Mecanismo de falla
        mmin, mmax : float
            Rango de magnitudes (mmax se estima si None)
            
        Returns
        -------
        ModeloFuentes
            Self para encadenamiento
        """
        # Crear fuente temporal para estimar mmax
        fuente_temp = FuenteFalla(
            nombre=nombre,
            traza=traza,
            longitud_km=longitud_km,
            ancho_km=ancho_km,
            buzamiento=buzamiento,
            tipo_falla=tipo_falla,
            slip_rate_mm_yr=slip_rate_mm_yr,
            distribucion_magnitud=DistribucionGutenbergRichter(mmin=mmin, mmax=8.0)
        )
        
        if mmax is None:
            mmax = fuente_temp.magnitud_maxima_wells_coppersmith()
        
        dist_mag = DistribucionGutenbergRichter(
            mmin=mmin, mmax=mmax, a_value=a_value, b_value=b_value
        )
        
        # Profundidad basada en ancho y buzamiento
        prof_max = ancho_km * np.sin(np.radians(buzamiento))
        dist_prof = DistribucionProfundidad(
            tipo=TipoDistribucionProfundidad.UNIFORME,
            prof_min=0,
            prof_max=prof_max,
            prof_media=prof_max / 2
        )
        
        fuente = FuenteFalla(
            nombre=nombre,
            traza=traza,
            longitud_km=longitud_km,
            ancho_km=ancho_km,
            buzamiento=buzamiento,
            tipo_falla=tipo_falla,
            slip_rate_mm_yr=slip_rate_mm_yr,
            distribucion_magnitud=dist_mag,
            distribucion_profundidad=dist_prof,
            **kwargs
        )
        
        return self.agregar_fuente(fuente)
    
    def obtener_fuentes_activas(self) -> List[FuenteSismica]:
        """Retorna solo las fuentes activas."""
        return [f for f in self.fuentes if f.activa]
    
    def obtener_fuentes_por_tipo(self, tipo: TipoFuente) -> List[FuenteSismica]:
        """Retorna fuentes de un tipo específico."""
        return [f for f in self.fuentes if f.tipo == tipo]
    
    def fuente_para_punto(self, lat: float, lon: float) -> Optional[FuenteSismica]:
        """Encuentra la fuente que contiene un punto."""
        for fuente in self.fuentes:
            if fuente.contiene_punto(lat, lon):
                return fuente
        return None
    
    def tasa_total(self) -> float:
        """Tasa total de eventos de todas las fuentes."""
        return sum(f.tasa_total() for f in self.fuentes if f.activa)
    
    def muestrear_catalogo(
        self,
        n_eventos: int,
        seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Genera un catálogo sintético.
        
        Parameters
        ----------
        n_eventos : int
            Número de eventos a generar
        seed : int, optional
            Semilla para reproducibilidad
            
        Returns
        -------
        List[Dict]
            Catálogo sintético
        """
        rng = np.random.default_rng(seed)
        
        # Distribuir eventos según tasa de cada fuente
        tasas = np.array([f.tasa_total() for f in self.fuentes if f.activa])
        if tasas.sum() == 0:
            return []
        
        probs = tasas / tasas.sum()
        fuentes_activas = [f for f in self.fuentes if f.activa]
        
        catalogo = []
        for _ in range(n_eventos):
            # Seleccionar fuente
            idx = rng.choice(len(fuentes_activas), p=probs)
            fuente = fuentes_activas[idx]
            
            # Muestrear evento
            eventos = fuente.muestrear_eventos(1, seed=rng.integers(0, 2**31))
            catalogo.extend(eventos)
        
        return catalogo
    
    def resumen(self) -> str:
        """Genera resumen textual del modelo."""
        lineas = [
            "=" * 60,
            f"MODELO DE FUENTES: {self.nombre}",
            "=" * 60,
            f"Versión: {self.version}",
            f"Descripción: {self.descripcion}",
            "",
            f"Total de fuentes: {len(self.fuentes)}",
            f"Fuentes activas: {len(self.obtener_fuentes_activas())}",
            f"Tasa total: {self.tasa_total():.2f} eventos/año",
            "",
            "Fuentes:",
        ]
        
        for f in self.fuentes:
            estado = "✅" if f.activa else "❌"
            lineas.append(
                f"  {estado} {f.nombre} ({f.tipo.value}): "
                f"M{f.distribucion_magnitud.mmin:.1f}-{f.distribucion_magnitud.mmax:.1f}, "
                f"tasa={f.tasa_total():.3f}/año"
            )
        
        lineas.append("=" * 60)
        return "\n".join(lineas)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'nombre': self.nombre,
            'version': self.version,
            'descripcion': self.descripcion,
            'n_fuentes': len(self.fuentes),
            'tasa_total': self.tasa_total(),
            'fuentes': [f.to_dict() for f in self.fuentes]
        }
    
    def exportar_json(self, ruta: str) -> None:
        """Exporta el modelo a JSON."""
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Modelo exportado a {ruta}")
    
    @classmethod
    def desde_json(cls, ruta: str) -> 'ModeloFuentes':
        """Carga un modelo desde JSON."""
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modelo = cls(
            nombre=data['nombre'],
            version=data.get('version', '1.0'),
            descripcion=data.get('descripcion', '')
        )
        
        # Reconstruir fuentes (simplificado)
        logger.info(f"Modelo cargado desde {ruta}")
        return modelo
    
    def to_geodataframe(self) -> 'gpd.GeoDataFrame':
        """Convierte fuentes a GeoDataFrame."""
        try:
            import geopandas as gpd
            from shapely.geometry import Polygon, LineString, Point
        except ImportError:
            raise ImportError("geopandas y shapely necesarios")
        
        datos = []
        geometrias = []
        
        for fuente in self.fuentes:
            fila = fuente.to_dict()
            
            if isinstance(fuente, FuenteArea) and fuente.poligono:
                # Convertir a (lon, lat) para shapely
                coords = [(p[1], p[0]) for p in fuente.poligono]
                if len(coords) >= 3:
                    geom = Polygon(coords)
                else:
                    continue
            elif isinstance(fuente, FuenteFalla) and fuente.traza:
                coords = [(p[1], p[0]) for p in fuente.traza]
                if len(coords) >= 2:
                    geom = LineString(coords)
                else:
                    continue
            elif isinstance(fuente, FuentePuntual):
                geom = Point(fuente.longitud, fuente.latitud)
            else:
                continue
            
            geometrias.append(geom)
            datos.append(fila)
        
        return gpd.GeoDataFrame(datos, geometry=geometrias, crs="EPSG:4326")


# =============================================================================
# MODELOS PREDEFINIDOS
# =============================================================================

def crear_modelo_mexico_simplificado() -> ModeloFuentes:
    """
    Crea un modelo simplificado de fuentes para México.
    
    Incluye zonas principales de subducción y sismicidad cortical.
    
    Returns
    -------
    ModeloFuentes
        Modelo con fuentes predefinidas
    """
    modelo = ModeloFuentes(
        nombre="México Simplificado",
        descripcion="Modelo simplificado de fuentes sísmicas para México",
        version="1.0"
    )
    
    # Zona de subducción - Fosa Mesoamericana
    modelo.agregar_zona_area(
        nombre="Subducción Pacífico",
        poligono=[
            (14.5, -98.0), (16.0, -95.0), (16.5, -93.0),
            (15.5, -92.0), (14.0, -94.0), (14.0, -97.0)
        ],
        a_value=5.0,
        b_value=0.9,
        mmin=5.0,
        mmax=8.2,
        profundidad_media=30
    )
    
    # Zona Jalisco-Colima
    modelo.agregar_zona_area(
        nombre="Jalisco-Colima",
        poligono=[
            (18.5, -105.5), (20.0, -105.0), (20.5, -103.5),
            (19.5, -102.5), (18.0, -103.5), (18.0, -105.0)
        ],
        a_value=4.5,
        b_value=1.0,
        mmin=4.5,
        mmax=8.0,
        profundidad_media=25
    )
    
    # Zona Oaxaca
    modelo.agregar_zona_area(
        nombre="Oaxaca",
        poligono=[
            (15.5, -98.5), (17.0, -96.0), (17.5, -95.0),
            (16.5, -94.5), (15.0, -96.0), (15.0, -98.0)
        ],
        a_value=4.8,
        b_value=0.95,
        mmin=5.0,
        mmax=8.0,
        profundidad_media=35
    )
    
    # Faja Volcánica Transmexicana
    modelo.agregar_zona_area(
        nombre="Faja Volcánica",
        poligono=[
            (18.5, -103.0), (19.5, -99.0), (20.0, -97.0),
            (19.5, -96.5), (18.5, -99.0), (18.0, -102.0)
        ],
        a_value=3.5,
        b_value=1.1,
        mmin=4.0,
        mmax=7.0,
        profundidad_media=10
    )
    
    return modelo


# =============================================================================
# INFORMACIÓN DEL MÓDULO
# =============================================================================

def info_modulo():
    """Muestra información del módulo source_models."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              SEISMEX Analysis - source_models.py                     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Fuentes sísmicas:                                                   ║
║    ✅ FuenteArea      - Zonas sismogénicas de área                   ║
║    ✅ FuenteFalla     - Fallas activas con geometría                 ║
║    ✅ FuentePuntual   - Fuentes puntuales                            ║
║                                                                      ║
║  Distribuciones de magnitud:                                         ║
║    ✅ Gutenberg-Richter truncada                                     ║
║    ✅ Característica (Youngs-Coppersmith)                            ║
║                                                                      ║
║  Distribuciones de profundidad:                                      ║
║    ✅ Uniforme, Triangular, Gaussiana, Fija                          ║
║                                                                      ║
║  ModeloFuentes:                                                      ║
║    ✅ Contenedor de múltiples fuentes                                ║
║    ✅ Muestreo de catálogos sintéticos                               ║
║    ✅ Exportación JSON/GeoDataFrame                                  ║
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
    'TipoFuente',
    'TipoFalla',
    'TipoDistribucionMagnitud',
    'TipoDistribucionProfundidad',
    
    # Distribuciones
    'DistribucionMagnitud',
    'DistribucionGutenbergRichter',
    'DistribucionCaracteristica',
    'DistribucionProfundidad',
    
    # Fuentes
    'FuenteSismica',
    'FuenteArea',
    'FuenteFalla',
    'FuentePuntual',
    
    # Modelo
    'ModeloFuentes',
    
    # Factories
    'crear_modelo_mexico_simplificado',
    
    # Utilidades
    'info_modulo',
]
