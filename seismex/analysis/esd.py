#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX - Módulo ESD (Energy Space Density)
================================================================================
Implementación de la técnica Energy Space Density para mapeo de la distribución
espacial de energía sísmica liberada.

Basado en:
    Del Pezzo, E. (2023). Space distribution of the seismic source energy at 
    Campi Flegrei caldera. Physics of the Earth and Planetary Interiors, 336.
    
    Del Pezzo, E., & Bianco, F. (2024). Space and time distribution of seismic 
    source energy at Campi Flegrei. Physics of the Earth and Planetary Interiors.
    
    Del Pezzo, E., Ibáñez, J.M., et al. (2025). Seismo-Genetic Structures of 
    Southern Spain Revealed by ESD Analysis. Geophysical Research Letters.

Autor: SEISMEX Project
Versión: 1.0.0
Licencia: MIT
================================================================================
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Union
from enum import Enum
import warnings
from datetime import datetime
import json

# Constantes físicas y parámetros del modelo
class Constantes:
    """Constantes utilizadas en el cálculo de ESD."""
    
    # Relación energía-magnitud (Kanamori & Brodsky, 2004)
    # E = 10^(1.5*Mw + 11.8) en ergios
    COEF_ENERGIA_A = 1.5
    COEF_ENERGIA_B = 11.8
    
    # Radio de la Tierra en metros
    RADIO_TIERRA_M = 6_371_000
    
    # Conversión de grados a metros (aproximación en el ecuador)
    GRADOS_A_METROS = 111_320
    
    # Valor por defecto para incertidumbre de magnitud
    INCERTIDUMBRE_MAGNITUD = 0.3
    
    # Profundidad máxima considerada (metros)
    PROFUNDIDAD_MAX = 150_000


class TipoMagnitud(Enum):
    """Tipos de magnitud sísmica soportados."""
    MW = "Mw"  # Magnitud momento
    ML = "Ml"  # Magnitud local
    MS = "Ms"  # Magnitud de ondas superficiales
    MB = "mb"  # Magnitud de ondas de cuerpo


@dataclass
class ConfiguracionESD:
    """
    Configuración para el cálculo de ESD.
    
    Attributes:
        tamano_celda_km: Tamaño de la celda cúbica en km (default: 10)
        paso_deslizamiento_km: Paso de deslizamiento de la malla en km (default: 2.5)
        profundidad_max_km: Profundidad máxima a analizar en km (default: 150)
        magnitud_minima: Magnitud mínima a considerar (default: 2.0)
        usar_mw: Si True, asume que las magnitudes son Mw (default: True)
        correccion_ml_mw: Aplicar conversión Ml a Mw (default: False)
        normalizar_por_capa: Normalizar ESD por cada capa de profundidad (default: True)
        suavizado_rms: Valor RMS para suavizado de profundidad (default: 0.3)
    """
    tamano_celda_km: float = 10.0
    paso_deslizamiento_km: float = 2.5
    profundidad_max_km: float = 150.0
    magnitud_minima: float = 2.0
    usar_mw: bool = True
    correccion_ml_mw: bool = False
    normalizar_por_capa: bool = True
    suavizado_rms: float = 0.3
    
    def __post_init__(self):
        """Validar configuración."""
        if self.tamano_celda_km <= 0:
            raise ValueError("El tamaño de celda debe ser positivo")
        if self.paso_deslizamiento_km <= 0:
            raise ValueError("El paso de deslizamiento debe ser positivo")
        if self.paso_deslizamiento_km > self.tamano_celda_km:
            warnings.warn("El paso de deslizamiento es mayor que el tamaño de celda")


@dataclass
class ResultadoGutenbergRichter:
    """
    Resultado del análisis Gutenberg-Richter.
    
    Attributes:
        b_value: Valor b de la distribución
        b_error: Error estándar del valor b
        a_value: Valor a (intercepto)
        a_error: Error estándar del valor a
        magnitud_completitud: Magnitud de completitud (Mc)
        n_eventos: Número de eventos utilizados
    """
    b_value: float
    b_error: float
    a_value: float
    a_error: float
    magnitud_completitud: float
    n_eventos: int


@dataclass
class ResultadoESD:
    """
    Resultado del cálculo de ESD.
    
    Attributes:
        grid_x: Coordenadas X de la malla (longitud en grados o UTM)
        grid_y: Coordenadas Y de la malla (latitud en grados o UTM)
        grid_z: Coordenadas Z de la malla (profundidad en km, negativa)
        esd_3d: Array 3D con valores de ESD
        esd_log10: Array 3D con log10(ESD) normalizado
        energia_total: Energía total liberada en la región
        configuracion: Configuración utilizada
        metadata: Diccionario con metadatos adicionales
    """
    grid_x: np.ndarray
    grid_y: np.ndarray
    grid_z: np.ndarray
    esd_3d: np.ndarray
    esd_log10: np.ndarray
    energia_total: float
    configuracion: ConfiguracionESD
    metadata: Dict = field(default_factory=dict)


class CatalogoSismico:
    """
    Clase para manejo del catálogo sísmico.
    
    Maneja la carga, validación y preprocesamiento de datos sísmicos
    desde múltiples fuentes (SSN, ISC-GEM, USGS, etc.)
    """
    
    COLUMNAS_REQUERIDAS = ['fecha', 'latitud', 'longitud', 'profundidad_km', 'magnitud']
    COLUMNAS_OPCIONALES = ['tipo_magnitud', 'fuente', 'id_evento']
    
    def __init__(self, datos: Optional[pd.DataFrame] = None):
        """
        Inicializa el catálogo sísmico.
        
        Args:
            datos: DataFrame con los datos sísmicos (opcional)
        """
        self.datos = datos if datos is not None else pd.DataFrame()
        self._validado = False
        
    @classmethod
    def desde_csv(cls, ruta: str, **kwargs) -> 'CatalogoSismico':
        """
        Carga un catálogo desde archivo CSV.
        
        Args:
            ruta: Ruta al archivo CSV
            **kwargs: Argumentos adicionales para pd.read_csv
            
        Returns:
            CatalogoSismico con los datos cargados
        """
        datos = pd.read_csv(ruta, **kwargs)
        return cls(datos)
    
    @classmethod
    def desde_ssn(cls, datos_ssn: pd.DataFrame) -> 'CatalogoSismico':
        """
        Crea catálogo a partir de datos del SSN México.
        
        Realiza el mapeo de columnas del formato SSN al formato interno.
        
        Args:
            datos_ssn: DataFrame con datos del SSN
            
        Returns:
            CatalogoSismico normalizado
        """
        # Mapeo de columnas SSN
        mapeo_columnas = {
            'Fecha': 'fecha',
            'Latitud': 'latitud',
            'Longitud': 'longitud',
            'Profundidad': 'profundidad_km',
            'Magnitud': 'magnitud'
        }
        
        datos = datos_ssn.rename(columns=mapeo_columnas)
        catalogo = cls(datos)
        catalogo.metadata = {'fuente': 'SSN_Mexico'}
        return catalogo
    
    @classmethod
    def desde_isc(cls, datos_isc: pd.DataFrame) -> 'CatalogoSismico':
        """
        Crea catálogo a partir de datos del ISC-GEM.
        
        Args:
            datos_isc: DataFrame con datos del ISC
            
        Returns:
            CatalogoSismico normalizado
        """
        # El ISC-GEM ya proporciona Mw homogeneizado
        mapeo_columnas = {
            'date': 'fecha',
            'lat': 'latitud',
            'lon': 'longitud',
            'depth': 'profundidad_km',
            'mw': 'magnitud'
        }
        
        datos = datos_isc.rename(columns=mapeo_columnas)
        datos['tipo_magnitud'] = 'Mw'
        catalogo = cls(datos)
        catalogo.metadata = {'fuente': 'ISC-GEM', 'homogeneizado': True}
        return catalogo
    
    def validar(self) -> bool:
        """
        Valida que el catálogo tenga las columnas requeridas y datos válidos.
        
        Returns:
            True si el catálogo es válido
            
        Raises:
            ValueError: Si faltan columnas o hay datos inválidos
        """
        # Verificar columnas requeridas
        columnas_faltantes = set(self.COLUMNAS_REQUERIDAS) - set(self.datos.columns)
        if columnas_faltantes:
            raise ValueError(f"Columnas faltantes: {columnas_faltantes}")
        
        # Verificar rangos válidos
        if (self.datos['latitud'].abs() > 90).any():
            raise ValueError("Latitudes fuera de rango [-90, 90]")
        
        if (self.datos['longitud'].abs() > 180).any():
            raise ValueError("Longitudes fuera de rango [-180, 180]")
        
        if (self.datos['profundidad_km'] < 0).any():
            warnings.warn("Profundidades negativas detectadas, se tomarán valores absolutos")
        
        if (self.datos['magnitud'] < 0).any():
            raise ValueError("Magnitudes negativas detectadas")
        
        self._validado = True
        return True
    
    def filtrar_region(self, 
                       lat_min: float, lat_max: float,
                       lon_min: float, lon_max: float,
                       prof_min: float = 0, prof_max: float = 150) -> 'CatalogoSismico':
        """
        Filtra eventos por región geográfica.
        
        Args:
            lat_min, lat_max: Límites de latitud
            lon_min, lon_max: Límites de longitud
            prof_min, prof_max: Límites de profundidad en km
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
        """
        mascara = (
            (self.datos['latitud'] >= lat_min) &
            (self.datos['latitud'] <= lat_max) &
            (self.datos['longitud'] >= lon_min) &
            (self.datos['longitud'] <= lon_max) &
            (self.datos['profundidad_km'].abs() >= prof_min) &
            (self.datos['profundidad_km'].abs() <= prof_max)
        )
        
        return CatalogoSismico(self.datos[mascara].copy())
    
    def filtrar_magnitud(self, magnitud_minima: float) -> 'CatalogoSismico':
        """
        Filtra eventos por magnitud mínima.
        
        Args:
            magnitud_minima: Magnitud mínima a considerar
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
        """
        mascara = self.datos['magnitud'] >= magnitud_minima
        return CatalogoSismico(self.datos[mascara].copy())
    
    def filtrar_periodo(self, 
                        fecha_inicio: str, 
                        fecha_fin: str) -> 'CatalogoSismico':
        """
        Filtra eventos por período temporal.
        
        Args:
            fecha_inicio: Fecha de inicio (formato ISO)
            fecha_fin: Fecha de fin (formato ISO)
            
        Returns:
            Nuevo CatalogoSismico con eventos filtrados
        """
        self.datos['fecha'] = pd.to_datetime(self.datos['fecha'])
        mascara = (
            (self.datos['fecha'] >= fecha_inicio) &
            (self.datos['fecha'] <= fecha_fin)
        )
        return CatalogoSismico(self.datos[mascara].copy())
    
    @property
    def n_eventos(self) -> int:
        """Número de eventos en el catálogo."""
        return len(self.datos)
    
    @property
    def rango_magnitudes(self) -> Tuple[float, float]:
        """Rango de magnitudes (min, max)."""
        return (self.datos['magnitud'].min(), self.datos['magnitud'].max())
    
    @property
    def rango_profundidades(self) -> Tuple[float, float]:
        """Rango de profundidades (min, max) en km."""
        return (
            self.datos['profundidad_km'].abs().min(),
            self.datos['profundidad_km'].abs().max()
        )
    
    def resumen(self) -> str:
        """Genera un resumen del catálogo."""
        return f"""
        === Resumen del Catálogo Sísmico ===
        Número de eventos: {self.n_eventos}
        Rango de magnitudes: {self.rango_magnitudes[0]:.1f} - {self.rango_magnitudes[1]:.1f}
        Rango de profundidades: {self.rango_profundidades[0]:.1f} - {self.rango_profundidades[1]:.1f} km
        Extensión espacial:
          Latitud:  {self.datos['latitud'].min():.2f}° - {self.datos['latitud'].max():.2f}°
          Longitud: {self.datos['longitud'].min():.2f}° - {self.datos['longitud'].max():.2f}°
        """


class CalculadoraESD:
    """
    Calculadora de Energy Space Density.
    
    Implementa el algoritmo ESD para mapear la distribución espacial
    de energía sísmica liberada en una región.
    """
    
    def __init__(self, config: Optional[ConfiguracionESD] = None):
        """
        Inicializa la calculadora ESD.
        
        Args:
            config: Configuración para el cálculo (usa defaults si no se proporciona)
        """
        self.config = config if config is not None else ConfiguracionESD()
        self._catalogo = None
        self._resultado = None
        
    def calcular_energia(self, magnitud: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Calcula la energía sísmica a partir de la magnitud.
        
        Utiliza la relación de Kanamori & Brodsky (2004):
        E = 10^(1.5*Mw + 11.8) ergios
        
        Args:
            magnitud: Magnitud del evento (o array de magnitudes)
            
        Returns:
            Energía en ergios
        """
        return np.power(10, Constantes.COEF_ENERGIA_A * magnitud + Constantes.COEF_ENERGIA_B)
    
    def convertir_ml_a_mw(self, ml: Union[float, np.ndarray], 
                          region: str = 'mexico_occidente') -> Union[float, np.ndarray]:
        """
        Convierte magnitud local (Ml) a magnitud momento (Mw).
        
        Utiliza relaciones empíricas específicas para cada región.
        
        Args:
            ml: Magnitud local
            region: Región para seleccionar la relación empírica
            
        Returns:
            Magnitud momento estimada
        """
        # Relaciones empíricas por región
        # Basadas en literatura para México y subducción
        relaciones = {
            'mexico_occidente': (0.92, 0.59),  # Mw = 0.92*Ml + 0.59 (estimación)
            'mexico_centro': (0.95, 0.48),
            'mexico_sur': (0.90, 0.65),
            'global': (0.85, 0.70)  # Relación general conservadora
        }
        
        if region not in relaciones:
            warnings.warn(f"Región '{region}' no reconocida, usando relación global")
            region = 'global'
        
        a, b = relaciones[region]
        return a * ml + b
    
    def crear_malla_3d(self, catalogo: CatalogoSismico) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Crea la malla 3D para el cálculo de ESD.
        
        La malla utiliza celdas cúbicas con desplazamiento para mayor resolución.
        
        Args:
            catalogo: Catálogo sísmico con los eventos
            
        Returns:
            Tupla (grid_x, grid_y, grid_z) con las coordenadas de la malla
        """
        # Obtener límites del catálogo con margen
        margen = self.config.tamano_celda_km * 2
        
        lat_min = catalogo.datos['latitud'].min() - margen / 111
        lat_max = catalogo.datos['latitud'].max() + margen / 111
        lon_min = catalogo.datos['longitud'].min() - margen / 111
        lon_max = catalogo.datos['longitud'].max() + margen / 111
        
        prof_min = 0
        prof_max = min(
            catalogo.datos['profundidad_km'].abs().max() + self.config.tamano_celda_km,
            self.config.profundidad_max_km
        )
        
        # Crear vectores de coordenadas
        paso = self.config.paso_deslizamiento_km
        
        # Convertir paso a grados (aproximación)
        paso_grados = paso / 111  # ~111 km por grado
        
        x = np.arange(lon_min, lon_max, paso_grados)
        y = np.arange(lat_min, lat_max, paso_grados)
        z = np.arange(prof_min, prof_max, paso)
        
        return x, y, z
    
    def calcular_esd(self, catalogo: CatalogoSismico, 
                     verbose: bool = True) -> ResultadoESD:
        """
        Calcula la Energy Space Density para el catálogo dado.
        
        Este es el método principal que implementa el algoritmo ESD completo:
        1. Crea la malla 3D
        2. Calcula la energía de cada evento
        3. Acumula energía en cada celda
        4. Normaliza por energía total
        5. Calcula log10(ESD)
        
        Args:
            catalogo: Catálogo sísmico preprocesado
            verbose: Si True, muestra progreso
            
        Returns:
            ResultadoESD con los mapas de ESD
        """
        self._catalogo = catalogo
        
        if not catalogo._validado:
            catalogo.validar()
        
        if verbose:
            print(f"Calculando ESD para {catalogo.n_eventos} eventos...")
        
        # Filtrar por magnitud mínima
        catalogo_filtrado = catalogo.filtrar_magnitud(self.config.magnitud_minima)
        
        if verbose:
            print(f"  Eventos después de filtrar (M >= {self.config.magnitud_minima}): {catalogo_filtrado.n_eventos}")
        
        # Crear malla 3D
        grid_x, grid_y, grid_z = self.crear_malla_3d(catalogo_filtrado)
        
        if verbose:
            print(f"  Malla 3D: {len(grid_x)} x {len(grid_y)} x {len(grid_z)} celdas")
        
        # Inicializar array de ESD
        esd_3d = np.zeros((len(grid_x), len(grid_y), len(grid_z)))
        
        # Calcular energía de cada evento
        datos = catalogo_filtrado.datos
        
        # Convertir Ml a Mw si es necesario
        if self.config.correccion_ml_mw:
            magnitudes = self.convertir_ml_a_mw(datos['magnitud'].values)
        else:
            magnitudes = datos['magnitud'].values
        
        energias = self.calcular_energia(magnitudes)
        energia_total = energias.sum()
        
        if verbose:
            print(f"  Energía total: {energia_total:.2e} ergios")
        
        # Tamaño de celda en grados y km
        tamano_grados = self.config.tamano_celda_km / 111
        tamano_km = self.config.tamano_celda_km
        
        # Acumular energía en celdas
        for idx in range(len(datos)):
            lon = datos['longitud'].iloc[idx]
            lat = datos['latitud'].iloc[idx]
            prof = abs(datos['profundidad_km'].iloc[idx])
            energia = energias[idx]
            
            # Encontrar índices de celda
            ix = np.searchsorted(grid_x, lon) - 1
            iy = np.searchsorted(grid_y, lat) - 1
            iz = np.searchsorted(grid_z, prof) - 1
            
            # Verificar que está dentro de la malla
            if 0 <= ix < len(grid_x) and 0 <= iy < len(grid_y) and 0 <= iz < len(grid_z):
                # Acumular energía considerando el tamaño de la celda
                # y aplicar suavizado por incertidumbre de profundidad
                if self.config.suavizado_rms > 0:
                    # Distribuir energía en celdas cercanas según incertidumbre
                    sigma_z = self.config.suavizado_rms * tamano_km
                    for dz in range(-2, 3):
                        iz_adj = iz + dz
                        if 0 <= iz_adj < len(grid_z):
                            peso = np.exp(-0.5 * (dz * self.config.paso_deslizamiento_km / sigma_z) ** 2)
                            esd_3d[ix, iy, iz_adj] += energia * peso
                else:
                    esd_3d[ix, iy, iz] += energia
        
        # Normalizar por energía total
        if energia_total > 0:
            esd_3d_norm = esd_3d / energia_total
        else:
            esd_3d_norm = esd_3d
        
        # Calcular log10(ESD) evitando log(0)
        esd_log10 = np.log10(esd_3d_norm + 1e-20)
        
        # Normalizar por capa si está configurado
        if self.config.normalizar_por_capa:
            for iz in range(len(grid_z)):
                capa = esd_log10[:, :, iz]
                max_capa = capa.max()
                if max_capa > -15:  # Solo normalizar si hay energía significativa
                    esd_log10[:, :, iz] = capa - max_capa
        
        # Crear resultado
        self._resultado = ResultadoESD(
            grid_x=grid_x,
            grid_y=grid_y,
            grid_z=grid_z,
            esd_3d=esd_3d_norm,
            esd_log10=esd_log10,
            energia_total=energia_total,
            configuracion=self.config,
            metadata={
                'n_eventos': catalogo_filtrado.n_eventos,
                'fecha_calculo': datetime.now().isoformat(),
                'rango_magnitudes': catalogo_filtrado.rango_magnitudes,
                'rango_profundidades': catalogo_filtrado.rango_profundidades
            }
        )
        
        if verbose:
            print("  ✓ Cálculo ESD completado")
        
        return self._resultado
    
    def obtener_seccion_horizontal(self, 
                                   profundidad_km: float,
                                   resultado: Optional[ResultadoESD] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Obtiene una sección horizontal (slice) a una profundidad dada.
        
        Args:
            profundidad_km: Profundidad del corte en km
            resultado: ResultadoESD (usa el último calculado si no se proporciona)
            
        Returns:
            Tupla (X, Y, ESD) para graficar
        """
        if resultado is None:
            resultado = self._resultado
        
        if resultado is None:
            raise ValueError("No hay resultado ESD disponible. Ejecute calcular_esd primero.")
        
        # Encontrar índice de profundidad más cercano
        iz = np.argmin(np.abs(resultado.grid_z - profundidad_km))
        
        # Crear meshgrid para plotting
        X, Y = np.meshgrid(resultado.grid_x, resultado.grid_y, indexing='ij')
        Z = resultado.esd_log10[:, :, iz]
        
        return X, Y, Z
    
    def obtener_seccion_vertical_ns(self, 
                                    longitud: float,
                                    resultado: Optional[ResultadoESD] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Obtiene una sección vertical N-S a una longitud dada.
        
        Args:
            longitud: Longitud del corte en grados
            resultado: ResultadoESD (usa el último calculado si no se proporciona)
            
        Returns:
            Tupla (Y, Z, ESD) para graficar (Y=latitud, Z=profundidad)
        """
        if resultado is None:
            resultado = self._resultado
        
        if resultado is None:
            raise ValueError("No hay resultado ESD disponible. Ejecute calcular_esd primero.")
        
        # Encontrar índice de longitud más cercano
        ix = np.argmin(np.abs(resultado.grid_x - longitud))
        
        # Crear meshgrid para plotting
        Y, Z = np.meshgrid(resultado.grid_y, -resultado.grid_z, indexing='ij')
        ESD = resultado.esd_log10[ix, :, :].T
        
        return Y, Z, ESD
    
    def obtener_seccion_vertical_ew(self, 
                                    latitud: float,
                                    resultado: Optional[ResultadoESD] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Obtiene una sección vertical E-W a una latitud dada.
        
        Args:
            latitud: Latitud del corte en grados
            resultado: ResultadoESD (usa el último calculado si no se proporciona)
            
        Returns:
            Tupla (X, Z, ESD) para graficar (X=longitud, Z=profundidad)
        """
        if resultado is None:
            resultado = self._resultado
        
        if resultado is None:
            raise ValueError("No hay resultado ESD disponible. Ejecute calcular_esd primero.")
        
        # Encontrar índice de latitud más cercano
        iy = np.argmin(np.abs(resultado.grid_y - latitud))
        
        # Crear meshgrid para plotting
        X, Z = np.meshgrid(resultado.grid_x, -resultado.grid_z, indexing='ij')
        ESD = resultado.esd_log10[:, iy, :].T
        
        return X, Z, ESD


class AnalizadorGutenbergRichter:
    """
    Analizador de la distribución Gutenberg-Richter.
    
    Calcula el valor b y la magnitud de completitud usando
    método de Monte Carlo para estimar incertidumbres.
    """
    
    def __init__(self, n_simulaciones: int = 1000):
        """
        Inicializa el analizador.
        
        Args:
            n_simulaciones: Número de simulaciones Monte Carlo
        """
        self.n_simulaciones = n_simulaciones
        
    def calcular_b_value(self, 
                         magnitudes: np.ndarray,
                         mc: Optional[float] = None,
                         incertidumbre_mag: float = 0.3) -> ResultadoGutenbergRichter:
        """
        Calcula el valor b de la distribución Gutenberg-Richter.
        
        Utiliza el método de máxima verosimilitud (Aki, 1965) con
        corrección de Shi & Bolt (1982) para magnitudes discretas.
        
        Args:
            magnitudes: Array de magnitudes
            mc: Magnitud de completitud (se estima si no se proporciona)
            incertidumbre_mag: Incertidumbre de las magnitudes
            
        Returns:
            ResultadoGutenbergRichter con los parámetros estimados
        """
        if mc is None:
            mc = self.estimar_mc(magnitudes)
        
        # Filtrar por magnitud de completitud
        mags = magnitudes[magnitudes >= mc]
        n = len(mags)
        
        if n < 10:
            raise ValueError(f"Muy pocos eventos ({n}) por encima de Mc={mc}")
        
        # Método de máxima verosimilitud (Aki, 1965)
        delta_m = 0.1  # Bin de magnitud
        mean_mag = mags.mean()
        
        b = (1 / (mean_mag - (mc - delta_m/2))) * np.log10(np.e)
        
        # Error estándar (Shi & Bolt, 1982)
        b_error = 2.3 * b**2 * np.sqrt(np.sum((mags - mean_mag)**2) / (n * (n-1)))
        
        # Calcular valor a
        # log10(N) = a - b*M
        bins = np.arange(mc, mags.max() + delta_m, delta_m)
        hist, _ = np.histogram(mags, bins=bins)
        cumsum = np.cumsum(hist[::-1])[::-1]
        
        # Ajuste lineal para obtener a
        mags_bin = (bins[:-1] + bins[1:]) / 2
        valid = cumsum > 0
        if valid.sum() > 2:
            log_n = np.log10(cumsum[valid])
            m_valid = mags_bin[valid]
            
            # Regresión lineal simple
            A = np.vstack([m_valid, np.ones(len(m_valid))]).T
            coef, residuals, rank, s = np.linalg.lstsq(A, log_n, rcond=None)
            a = coef[1]
            a_error = np.sqrt(residuals[0] / (len(m_valid) - 2)) if len(residuals) > 0 else 0.1
        else:
            a = np.log10(n) + b * mc
            a_error = 0.1
        
        return ResultadoGutenbergRichter(
            b_value=b,
            b_error=b_error,
            a_value=a,
            a_error=a_error,
            magnitud_completitud=mc,
            n_eventos=n
        )
    
    def estimar_mc(self, magnitudes: np.ndarray) -> float:
        """
        Estima la magnitud de completitud (Mc).
        
        Utiliza el método MAXC (Maximum Curvature) que identifica
        el punto de máxima curvatura en la distribución de frecuencias.
        
        Args:
            magnitudes: Array de magnitudes
            
        Returns:
            Magnitud de completitud estimada
        """
        # Crear histograma de magnitudes
        bins = np.arange(magnitudes.min(), magnitudes.max() + 0.1, 0.1)
        hist, bin_edges = np.histogram(magnitudes, bins=bins)
        
        # Mc es donde el histograma tiene su máximo
        idx_max = np.argmax(hist)
        mc = (bin_edges[idx_max] + bin_edges[idx_max + 1]) / 2
        
        # Añadir 0.2 como corrección conservadora (Woessner & Wiemer, 2005)
        return mc + 0.2
    
    def monte_carlo_b_value(self, 
                            magnitudes: np.ndarray,
                            mc: float,
                            incertidumbre_mag: float = 0.3) -> Tuple[float, float]:
        """
        Estima el valor b con incertidumbre usando Monte Carlo.
        
        Args:
            magnitudes: Array de magnitudes
            mc: Magnitud de completitud
            incertidumbre_mag: Incertidumbre de las magnitudes
            
        Returns:
            Tupla (b_medio, b_std)
        """
        mags_base = magnitudes[magnitudes >= mc]
        b_values = []
        
        for _ in range(self.n_simulaciones):
            # Perturbar magnitudes con error gaussiano
            mags_pert = mags_base + np.random.normal(0, incertidumbre_mag, len(mags_base))
            
            # Calcular b para esta realización
            try:
                resultado = self.calcular_b_value(mags_pert, mc)
                b_values.append(resultado.b_value)
            except ValueError:
                continue
        
        b_values = np.array(b_values)
        return b_values.mean(), b_values.std()


def ejemplo_uso():
    """
    Ejemplo de uso del módulo ESD.
    
    Genera datos sintéticos y calcula ESD para demostración.
    """
    print("=" * 70)
    print("SEISMEX - Ejemplo de uso del módulo ESD")
    print("=" * 70)
    
    # Generar catálogo sintético para demostración
    np.random.seed(42)
    n_eventos = 500
    
    # Simular zona de subducción con sismicidad concentrada
    datos_sinteticos = pd.DataFrame({
        'fecha': pd.date_range('2020-01-01', periods=n_eventos, freq='D'),
        'latitud': np.random.normal(19.0, 0.5, n_eventos),
        'longitud': np.random.normal(-104.0, 0.5, n_eventos),
        'profundidad_km': np.abs(np.random.exponential(20, n_eventos)),
        'magnitud': np.random.exponential(0.8, n_eventos) + 2.0  # Gutenberg-Richter aproximado
    })
    
    # Crear catálogo
    catalogo = CatalogoSismico(datos_sinteticos)
    catalogo.validar()
    
    print(catalogo.resumen())
    
    # Análisis Gutenberg-Richter
    print("\n--- Análisis Gutenberg-Richter ---")
    analizador_gr = AnalizadorGutenbergRichter()
    resultado_gr = analizador_gr.calcular_b_value(catalogo.datos['magnitud'].values)
    
    print(f"  Magnitud de completitud (Mc): {resultado_gr.magnitud_completitud:.2f}")
    print(f"  Valor b: {resultado_gr.b_value:.3f} ± {resultado_gr.b_error:.3f}")
    print(f"  Valor a: {resultado_gr.a_value:.3f} ± {resultado_gr.a_error:.3f}")
    print(f"  Eventos utilizados: {resultado_gr.n_eventos}")
    
    # Calcular ESD
    print("\n--- Cálculo de ESD ---")
    config = ConfiguracionESD(
        tamano_celda_km=10.0,
        paso_deslizamiento_km=2.5,
        magnitud_minima=2.4,
        normalizar_por_capa=True
    )
    
    calculadora = CalculadoraESD(config)
    resultado_esd = calculadora.calcular_esd(catalogo)
    
    print(f"\n  Energía total liberada: {resultado_esd.energia_total:.2e} ergios")
    print(f"  Dimensiones de la malla: {resultado_esd.esd_3d.shape}")
    
    # Obtener secciones
    print("\n--- Secciones disponibles ---")
    print(f"  Profundidades: {resultado_esd.grid_z.min():.1f} - {resultado_esd.grid_z.max():.1f} km")
    print(f"  Latitudes: {resultado_esd.grid_y.min():.2f}° - {resultado_esd.grid_y.max():.2f}°")
    print(f"  Longitudes: {resultado_esd.grid_x.min():.2f}° - {resultado_esd.grid_x.max():.2f}°")
    
    # Ejemplo de sección horizontal a 10 km
    X, Y, ESD = calculadora.obtener_seccion_horizontal(10)
    print(f"\n  Sección horizontal a 10 km: {ESD.shape}")
    print(f"  Rango log10(ESD): {ESD.min():.2f} a {ESD.max():.2f}")
    
    print("\n" + "=" * 70)
    print("✓ Ejemplo completado. Use visualizador_esd.py para graficar resultados.")
    print("=" * 70)
    
    return resultado_esd, resultado_gr


if __name__ == "__main__":
    resultado_esd, resultado_gr = ejemplo_uso()
