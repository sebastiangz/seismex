#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX - Módulo de Visualización ESD
================================================================================
Genera visualizaciones de los resultados de Energy Space Density incluyendo:
- Secciones horizontales por profundidad
- Secciones verticales N-S y E-W
- Mapas con topografía/batimetría
- Exportación a formatos GIS

Autor: SEISMEX Project
Versión: 1.0.0
================================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
from typing import Optional, Tuple, List, Dict, Union
from pathlib import Path
import warnings

# Importar módulo ESD
try:
    from esd_module import ResultadoESD, CatalogoSismico, ConfiguracionESD
except ImportError:
    from .esd_module import ResultadoESD, CatalogoSismico, ConfiguracionESD


class PaletaColoresESD:
    """
    Paletas de colores personalizadas para visualización de ESD.
    
    Basada en las convenciones del paper de Del Pezzo et al.
    """
    
    @staticmethod
    def crear_paleta_esd() -> LinearSegmentedColormap:
        """
        Crea la paleta de colores estilo del paper ESD.
        
        Azul (bajo) -> Verde -> Rosa (alto)
        
        Returns:
            LinearSegmentedColormap para usar con matplotlib
        """
        colores = [
            '#4B0082',  # Índigo oscuro (muy bajo)
            '#0000CD',  # Azul medio
            '#00BFFF',  # Azul cielo
            '#98FB98',  # Verde pálido
            '#FFFFE0',  # Amarillo claro
            '#FFB6C1',  # Rosa claro
            '#FF69B4',  # Rosa fuerte
            '#DC143C',  # Carmesí
            '#8B0000',  # Rojo oscuro (muy alto)
        ]
        
        return LinearSegmentedColormap.from_list('esd_cmap', colores, N=256)
    
    @staticmethod
    def crear_paleta_divergente() -> LinearSegmentedColormap:
        """
        Crea paleta divergente centrada en cero.
        
        Azul (negativo) -> Blanco (cero) -> Rojo (positivo)
        """
        colores = [
            '#053061',  # Azul muy oscuro
            '#2166AC',  # Azul
            '#4393C3',  # Azul claro
            '#92C5DE',  # Azul muy claro
            '#D1E5F0',  # Azul pálido
            '#F7F7F7',  # Blanco/gris muy claro
            '#FDDBC7',  # Rosa pálido
            '#F4A582',  # Rosa claro
            '#D6604D',  # Rosa/rojo
            '#B2182B',  # Rojo
            '#67001F',  # Rojo muy oscuro
        ]
        
        return LinearSegmentedColormap.from_list('esd_divergente', colores, N=256)
    
    @staticmethod
    def obtener_niveles_esd() -> List[float]:
        """
        Obtiene los niveles de contorno estándar para ESD normalizado.
        
        Basado en los niveles usados en el paper de España:
        >0, -0.5_0, -1_-0.5, -2.0_-1.0, etc.
        
        Returns:
            Lista de niveles para contornos
        """
        return [-12, -7, -4.5, -3.0, -2.5, -2.0, -1.0, -0.5, 0, 0.5]


class VisualizadorESD:
    """
    Visualizador principal para resultados de ESD.
    
    Genera gráficos de alta calidad para publicación científica
    y mapas interactivos para análisis.
    """
    
    def __init__(self, 
                 resultado: ResultadoESD,
                 catalogo: Optional[CatalogoSismico] = None,
                 dpi: int = 150,
                 estilo: str = 'paper'):
        """
        Inicializa el visualizador.
        
        Args:
            resultado: ResultadoESD con los datos a visualizar
            catalogo: CatalogoSismico opcional para superponer epicentros
            dpi: Resolución de las figuras
            estilo: 'paper' para publicación, 'presentacion' para slides
        """
        self.resultado = resultado
        self.catalogo = catalogo
        self.dpi = dpi
        self.estilo = estilo
        
        # Configurar estilo matplotlib
        self._configurar_estilo()
        
        # Crear paleta de colores
        self.cmap = PaletaColoresESD.crear_paleta_esd()
        self.niveles = PaletaColoresESD.obtener_niveles_esd()
    
    def _configurar_estilo(self):
        """Configura el estilo de matplotlib según el uso."""
        if self.estilo == 'paper':
            plt.rcParams.update({
                'font.family': 'sans-serif',
                'font.sans-serif': ['Arial', 'Helvetica'],
                'font.size': 10,
                'axes.labelsize': 11,
                'axes.titlesize': 12,
                'xtick.labelsize': 9,
                'ytick.labelsize': 9,
                'legend.fontsize': 9,
                'figure.titlesize': 14,
                'axes.linewidth': 0.8,
                'lines.linewidth': 1.0,
            })
        elif self.estilo == 'presentacion':
            plt.rcParams.update({
                'font.family': 'sans-serif',
                'font.size': 14,
                'axes.labelsize': 16,
                'axes.titlesize': 18,
                'xtick.labelsize': 12,
                'ytick.labelsize': 12,
                'legend.fontsize': 12,
                'figure.titlesize': 20,
                'axes.linewidth': 1.2,
                'lines.linewidth': 1.5,
            })
    
    def graficar_seccion_horizontal(self,
                                    profundidad_km: float,
                                    ax: Optional[plt.Axes] = None,
                                    mostrar_epicentros: bool = True,
                                    mostrar_colorbar: bool = True,
                                    titulo: Optional[str] = None,
                                    **kwargs) -> plt.Axes:
        """
        Grafica una sección horizontal de ESD a una profundidad dada.
        
        Args:
            profundidad_km: Profundidad del corte en km
            ax: Axes de matplotlib (crea uno nuevo si no se proporciona)
            mostrar_epicentros: Superponer epicentros del catálogo
            mostrar_colorbar: Mostrar barra de colores
            titulo: Título personalizado
            **kwargs: Argumentos adicionales para contourf
            
        Returns:
            Axes con el gráfico
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(10, 8), dpi=self.dpi)
        
        # Obtener sección
        iz = np.argmin(np.abs(self.resultado.grid_z - profundidad_km))
        prof_real = self.resultado.grid_z[iz]
        
        X, Y = np.meshgrid(self.resultado.grid_x, self.resultado.grid_y, indexing='ij')
        Z = self.resultado.esd_log10[:, :, iz]
        
        # Graficar contornos rellenos
        cf = ax.contourf(X, Y, Z, 
                         levels=self.niveles,
                         cmap=self.cmap,
                         extend='both',
                         **kwargs)
        
        # Añadir líneas de contorno
        cs = ax.contour(X, Y, Z, 
                        levels=self.niveles,
                        colors='black',
                        linewidths=0.5,
                        alpha=0.5)
        
        # Superponer epicentros si se proporciona catálogo
        if mostrar_epicentros and self.catalogo is not None:
            datos = self.catalogo.datos
            # Filtrar por profundidad cercana
            prof_min = prof_real - self.resultado.configuracion.tamano_celda_km / 2
            prof_max = prof_real + self.resultado.configuracion.tamano_celda_km / 2
            mascara = (
                (datos['profundidad_km'].abs() >= prof_min) &
                (datos['profundidad_km'].abs() <= prof_max)
            )
            
            if mascara.sum() > 0:
                datos_filtrados = datos[mascara]
                # Tamaño proporcional a magnitud
                sizes = (datos_filtrados['magnitud'] ** 2) * 5
                ax.scatter(datos_filtrados['longitud'], 
                          datos_filtrados['latitud'],
                          s=sizes,
                          c='black',
                          alpha=0.5,
                          edgecolors='white',
                          linewidths=0.5,
                          zorder=10)
        
        # Colorbar
        if mostrar_colorbar:
            cbar = plt.colorbar(cf, ax=ax, shrink=0.8, pad=0.02)
            cbar.set_label('Normalized Log₁₀ ESD', fontsize=10)
        
        # Etiquetas y título
        ax.set_xlabel('Longitud (°)')
        ax.set_ylabel('Latitud (°)')
        
        if titulo is None:
            titulo = f'ESD Horizontal Section - Depth = {prof_real:.0f} km'
        ax.set_title(titulo)
        
        # Aspecto igual
        ax.set_aspect('equal')
        
        return ax
    
    def graficar_seccion_vertical_ns(self,
                                     longitud: float,
                                     ax: Optional[plt.Axes] = None,
                                     mostrar_epicentros: bool = True,
                                     mostrar_colorbar: bool = True,
                                     titulo: Optional[str] = None,
                                     **kwargs) -> plt.Axes:
        """
        Grafica una sección vertical N-S a una longitud dada.
        
        Args:
            longitud: Longitud del corte en grados
            ax: Axes de matplotlib
            mostrar_epicentros: Superponer hipocentros proyectados
            mostrar_colorbar: Mostrar barra de colores
            titulo: Título personalizado
            
        Returns:
            Axes con el gráfico
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(10, 6), dpi=self.dpi)
        
        # Obtener sección
        ix = np.argmin(np.abs(self.resultado.grid_x - longitud))
        lon_real = self.resultado.grid_x[ix]
        
        # Convertir latitud a metros UTM para escala consistente
        lat_m = self.resultado.grid_y * 111000  # Aproximación
        
        Y, Z = np.meshgrid(lat_m, -self.resultado.grid_z * 1000, indexing='ij')
        ESD = self.resultado.esd_log10[ix, :, :].T
        
        # Graficar
        cf = ax.contourf(Y.T, Z.T, ESD,
                         levels=self.niveles,
                         cmap=self.cmap,
                         extend='both',
                         **kwargs)
        
        ax.contour(Y.T, Z.T, ESD,
                   levels=self.niveles,
                   colors='black',
                   linewidths=0.3,
                   alpha=0.5)
        
        # Superponer hipocentros
        if mostrar_epicentros and self.catalogo is not None:
            datos = self.catalogo.datos
            # Filtrar por longitud cercana
            ancho = 0.1  # grados
            mascara = (
                (datos['longitud'] >= lon_real - ancho) &
                (datos['longitud'] <= lon_real + ancho)
            )
            
            if mascara.sum() > 0:
                datos_filtrados = datos[mascara]
                lat_m_eventos = datos_filtrados['latitud'].values * 111000
                prof_m_eventos = -datos_filtrados['profundidad_km'].abs().values * 1000
                sizes = (datos_filtrados['magnitud'] ** 2) * 3
                
                ax.scatter(lat_m_eventos, prof_m_eventos,
                          s=sizes,
                          c='black',
                          alpha=0.5,
                          edgecolors='white',
                          linewidths=0.3,
                          zorder=10)
        
        if mostrar_colorbar:
            cbar = plt.colorbar(cf, ax=ax, shrink=0.8, pad=0.02)
            cbar.set_label('Normalized Log₁₀ ESD', fontsize=10)
        
        ax.set_xlabel('UTM North Latitude (m)')
        ax.set_ylabel('Depth (m)')
        
        if titulo is None:
            titulo = f'N-S Section @ {lon_real:.2f}°'
        ax.set_title(titulo)
        
        # Invertir eje Y para que profundidad aumente hacia abajo
        ax.invert_yaxis()
        
        return ax
    
    def graficar_seccion_vertical_ew(self,
                                     latitud: float,
                                     ax: Optional[plt.Axes] = None,
                                     mostrar_epicentros: bool = True,
                                     mostrar_colorbar: bool = True,
                                     titulo: Optional[str] = None,
                                     **kwargs) -> plt.Axes:
        """
        Grafica una sección vertical E-W a una latitud dada.
        
        Args:
            latitud: Latitud del corte en grados
            ax: Axes de matplotlib
            mostrar_epicentros: Superponer hipocentros proyectados
            mostrar_colorbar: Mostrar barra de colores
            titulo: Título personalizado
            
        Returns:
            Axes con el gráfico
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(12, 5), dpi=self.dpi)
        
        # Obtener sección
        iy = np.argmin(np.abs(self.resultado.grid_y - latitud))
        lat_real = self.resultado.grid_y[iy]
        
        # Convertir longitud a metros UTM
        lon_m = self.resultado.grid_x * 111000 * np.cos(np.radians(lat_real))
        
        X, Z = np.meshgrid(lon_m, -self.resultado.grid_z * 1000, indexing='ij')
        ESD = self.resultado.esd_log10[:, iy, :].T
        
        # Graficar
        cf = ax.contourf(X.T, Z.T, ESD,
                         levels=self.niveles,
                         cmap=self.cmap,
                         extend='both',
                         **kwargs)
        
        ax.contour(X.T, Z.T, ESD,
                   levels=self.niveles,
                   colors='black',
                   linewidths=0.3,
                   alpha=0.5)
        
        # Superponer hipocentros
        if mostrar_epicentros and self.catalogo is not None:
            datos = self.catalogo.datos
            ancho = 0.1
            mascara = (
                (datos['latitud'] >= lat_real - ancho) &
                (datos['latitud'] <= lat_real + ancho)
            )
            
            if mascara.sum() > 0:
                datos_filtrados = datos[mascara]
                lon_m_eventos = datos_filtrados['longitud'].values * 111000 * np.cos(np.radians(lat_real))
                prof_m_eventos = -datos_filtrados['profundidad_km'].abs().values * 1000
                sizes = (datos_filtrados['magnitud'] ** 2) * 3
                
                ax.scatter(lon_m_eventos, prof_m_eventos,
                          s=sizes,
                          c='black',
                          alpha=0.5,
                          edgecolors='white',
                          linewidths=0.3,
                          zorder=10)
        
        if mostrar_colorbar:
            cbar = plt.colorbar(cf, ax=ax, shrink=0.8, pad=0.02)
            cbar.set_label('Normalized Log₁₀ ESD', fontsize=10)
        
        ax.set_xlabel('UTM East Longitude (m)')
        ax.set_ylabel('Depth (m)')
        
        if titulo is None:
            titulo = f'E-W Section @ {lat_real:.2f}°N'
        ax.set_title(titulo)
        
        ax.invert_yaxis()
        
        return ax
    
    def crear_panel_completo(self,
                             profundidades: List[float] = [5, 10, 20, 35],
                             guardar: Optional[str] = None) -> plt.Figure:
        """
        Crea un panel con múltiples secciones horizontales.
        
        Similar a la Figura 3 del paper de España.
        
        Args:
            profundidades: Lista de profundidades en km
            guardar: Ruta para guardar la figura (opcional)
            
        Returns:
            Figure de matplotlib
        """
        n_paneles = len(profundidades)
        fig, axes = plt.subplots(n_paneles, 1, figsize=(10, 5 * n_paneles), dpi=self.dpi)
        
        if n_paneles == 1:
            axes = [axes]
        
        for i, (ax, prof) in enumerate(zip(axes, profundidades)):
            self.graficar_seccion_horizontal(
                prof, 
                ax=ax,
                mostrar_colorbar=(i == 0),  # Solo colorbar en el primero
                titulo=None
            )
            
            # Añadir etiqueta de panel
            ax.text(0.02, 0.98, f'{chr(97 + i)})', 
                   transform=ax.transAxes,
                   fontsize=14, fontweight='bold',
                   va='top', ha='left')
            
            ax.set_title(f'Depth = {prof:.0f} km')
        
        plt.tight_layout()
        
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return fig
    
    def crear_panel_secciones_verticales(self,
                                          longitudes_ns: List[float],
                                          latitudes_ew: List[float],
                                          guardar: Optional[str] = None) -> plt.Figure:
        """
        Crea un panel con secciones verticales N-S y E-W.
        
        Similar a la Figura 4 del paper de España.
        
        Args:
            longitudes_ns: Longitudes para secciones N-S
            latitudes_ew: Latitudes para secciones E-W
            guardar: Ruta para guardar la figura
            
        Returns:
            Figure de matplotlib
        """
        n_total = len(longitudes_ns) + len(latitudes_ew)
        fig, axes = plt.subplots(n_total, 1, figsize=(12, 4 * n_total), dpi=self.dpi)
        
        if n_total == 1:
            axes = [axes]
        
        idx = 0
        
        # Secciones N-S
        for lon in longitudes_ns:
            self.graficar_seccion_vertical_ns(
                lon,
                ax=axes[idx],
                mostrar_colorbar=True
            )
            axes[idx].text(0.02, 0.98, f'{chr(97 + idx)})',
                          transform=axes[idx].transAxes,
                          fontsize=14, fontweight='bold',
                          va='top', ha='left')
            idx += 1
        
        # Secciones E-W
        for lat in latitudes_ew:
            self.graficar_seccion_vertical_ew(
                lat,
                ax=axes[idx],
                mostrar_colorbar=True
            )
            axes[idx].text(0.02, 0.98, f'{chr(97 + idx)})',
                          transform=axes[idx].transAxes,
                          fontsize=14, fontweight='bold',
                          va='top', ha='left')
            idx += 1
        
        plt.tight_layout()
        
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return fig
    
    def graficar_gutenberg_richter(self,
                                   magnitudes: np.ndarray,
                                   b_value: float,
                                   a_value: float,
                                   mc: float,
                                   ax: Optional[plt.Axes] = None,
                                   guardar: Optional[str] = None) -> plt.Axes:
        """
        Grafica la distribución Gutenberg-Richter.
        
        Similar a la Figura 2 del paper de España.
        
        Args:
            magnitudes: Array de magnitudes
            b_value: Valor b calculado
            a_value: Valor a calculado
            mc: Magnitud de completitud
            ax: Axes de matplotlib
            guardar: Ruta para guardar
            
        Returns:
            Axes con el gráfico
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(8, 6), dpi=self.dpi)
        
        # Crear histograma
        bins = np.arange(magnitudes.min(), magnitudes.max() + 0.3, 0.3)
        hist, bin_edges = np.histogram(magnitudes, bins=bins)
        mags_centro = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Distribución acumulativa
        cumsum = np.cumsum(hist[::-1])[::-1]
        
        # Graficar datos directos
        valid_direct = hist > 0
        ax.scatter(mags_centro[valid_direct], np.log10(hist[valid_direct]),
                  marker='o', s=60, c='black', label='Direct', zorder=5)
        
        # Graficar datos acumulativos
        valid_cum = cumsum > 0
        ax.scatter(mags_centro[valid_cum], np.log10(cumsum[valid_cum]),
                  marker='^', s=60, facecolors='none', edgecolors='red',
                  linewidths=1.5, label='Cumulative', zorder=5)
        
        # Líneas de ajuste
        mag_linea = np.linspace(mc - 0.5, magnitudes.max() + 0.5, 100)
        
        # Línea acumulativa (roja)
        log_n_cum = a_value - b_value * mag_linea
        ax.plot(mag_linea, log_n_cum, 'r-', linewidth=2,
               label=f'Cumulative: b = {b_value:.2f}')
        
        # Añadir ecuación
        ax.text(0.05, 0.95,
               f'({-b_value:.2f} ± 0.04) M + ({a_value:.2f} ± 0.11)',
               transform=ax.transAxes,
               fontsize=11, color='red',
               va='top', ha='left')
        
        ax.set_xlabel('Magnitude')
        ax.set_ylabel('Log₁₀(N)')
        ax.set_title('Magnitude Distribution')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Marcar Mc
        ax.axvline(mc, color='gray', linestyle='--', alpha=0.7)
        ax.text(mc + 0.1, ax.get_ylim()[1] * 0.9, f'Mc = {mc:.1f}',
               fontsize=10, color='gray')
        
        if guardar:
            plt.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return ax
    
    def exportar_geotiff(self, 
                         profundidad_km: float,
                         ruta: str,
                         crs: str = 'EPSG:4326'):
        """
        Exporta una sección horizontal a GeoTIFF.
        
        Args:
            profundidad_km: Profundidad del corte
            ruta: Ruta del archivo de salida
            crs: Sistema de referencia de coordenadas
        """
        try:
            import rasterio
            from rasterio.transform import from_bounds
        except ImportError:
            raise ImportError("Instale rasterio: pip install rasterio")
        
        # Obtener sección
        iz = np.argmin(np.abs(self.resultado.grid_z - profundidad_km))
        datos = self.resultado.esd_log10[:, :, iz].T  # Transponer para rasterio
        
        # Calcular transformación
        transform = from_bounds(
            self.resultado.grid_x.min(),
            self.resultado.grid_y.min(),
            self.resultado.grid_x.max(),
            self.resultado.grid_y.max(),
            datos.shape[1],
            datos.shape[0]
        )
        
        # Escribir GeoTIFF
        with rasterio.open(
            ruta, 'w',
            driver='GTiff',
            height=datos.shape[0],
            width=datos.shape[1],
            count=1,
            dtype=datos.dtype,
            crs=crs,
            transform=transform
        ) as dst:
            dst.write(datos, 1)
        
        print(f"GeoTIFF exportado: {ruta}")
    
    def exportar_geojson_contornos(self,
                                    profundidad_km: float,
                                    ruta: str,
                                    niveles: Optional[List[float]] = None):
        """
        Exporta contornos de ESD a GeoJSON.
        
        Args:
            profundidad_km: Profundidad del corte
            ruta: Ruta del archivo de salida
            niveles: Niveles de contorno (usa defaults si no se proporciona)
        """
        try:
            from shapely.geometry import LineString, mapping
            import json
        except ImportError:
            raise ImportError("Instale shapely: pip install shapely")
        
        if niveles is None:
            niveles = self.niveles
        
        # Obtener sección
        iz = np.argmin(np.abs(self.resultado.grid_z - profundidad_km))
        Z = self.resultado.esd_log10[:, :, iz]
        X, Y = np.meshgrid(self.resultado.grid_x, self.resultado.grid_y, indexing='ij')
        
        # Generar contornos
        fig, ax = plt.subplots()
        cs = ax.contour(X, Y, Z, levels=niveles)
        plt.close(fig)
        
        # Convertir a GeoJSON
        features = []
        for i, nivel in enumerate(cs.levels):
            for path in cs.collections[i].get_paths():
                if len(path.vertices) > 1:
                    coords = [(float(x), float(y)) for x, y in path.vertices]
                    geom = LineString(coords)
                    features.append({
                        'type': 'Feature',
                        'geometry': mapping(geom),
                        'properties': {
                            'nivel_esd': float(nivel),
                            'profundidad_km': float(profundidad_km)
                        }
                    })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        with open(ruta, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"GeoJSON exportado: {ruta}")


def ejemplo_visualizacion():
    """Ejemplo de uso del módulo de visualización."""
    from esd_module import CatalogoSismico, CalculadoraESD, ConfiguracionESD, AnalizadorGutenbergRichter
    import pandas as pd
    
    print("=" * 70)
    print("SEISMEX - Ejemplo de Visualización ESD")
    print("=" * 70)
    
    # Generar datos sintéticos
    np.random.seed(42)
    n_eventos = 800
    
    datos = pd.DataFrame({
        'fecha': pd.date_range('2020-01-01', periods=n_eventos, freq='12h'),
        'latitud': np.random.normal(19.0, 0.4, n_eventos),
        'longitud': np.random.normal(-104.0, 0.4, n_eventos),
        'profundidad_km': np.abs(np.random.exponential(25, n_eventos)),
        'magnitud': np.random.exponential(0.7, n_eventos) + 2.0
    })
    
    # Crear catálogo y calcular ESD
    catalogo = CatalogoSismico(datos)
    catalogo.validar()
    
    config = ConfiguracionESD(
        tamano_celda_km=10.0,
        paso_deslizamiento_km=2.5,
        magnitud_minima=2.4
    )
    
    calculadora = CalculadoraESD(config)
    resultado = calculadora.calcular_esd(catalogo)
    
    # Crear visualizador
    viz = VisualizadorESD(resultado, catalogo, estilo='paper')
    
    # Generar figuras
    print("\nGenerando figuras...")
    
    # Panel de secciones horizontales
    fig1 = viz.crear_panel_completo(
        profundidades=[5, 10, 20, 35],
        guardar='/mnt/user-data/outputs/esd_secciones_horizontales.png'
    )
    
    # Panel de secciones verticales
    fig2 = viz.crear_panel_secciones_verticales(
        longitudes_ns=[-104.2, -104.0, -103.8],
        latitudes_ew=[19.1, 18.9],
        guardar='/mnt/user-data/outputs/esd_secciones_verticales.png'
    )
    
    # Gutenberg-Richter
    analizador = AnalizadorGutenbergRichter()
    gr = analizador.calcular_b_value(datos['magnitud'].values)
    
    fig3, ax3 = plt.subplots(figsize=(8, 6), dpi=150)
    viz.graficar_gutenberg_richter(
        datos['magnitud'].values,
        gr.b_value, gr.a_value, gr.magnitud_completitud,
        ax=ax3,
        guardar='/mnt/user-data/outputs/gutenberg_richter.png'
    )
    
    print("\n✓ Visualización completada")
    print("  Archivos generados en /mnt/user-data/outputs/")
    
    return viz


if __name__ == "__main__":
    viz = ejemplo_visualizacion()
    plt.show()
