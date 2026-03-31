#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX - Módulo de Visualización ESD
================================================================================
Genera visualizaciones de alta calidad de los resultados de Energy Space Density:
- Secciones horizontales por profundidad
- Secciones verticales N-S y E-W
- Perfiles personalizados
- Paneles multi-vista
- Gráficos Gutenberg-Richter
- Visualización 3D
- Exportación a formatos GIS

Autor: SEISMEX Project
Versión: 1.0.0
================================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle, Circle
from matplotlib.collections import PatchCollection
from mpl_toolkits.mplot3d import Axes3D
from typing import Optional, Tuple, List, Dict, Union, Any
from pathlib import Path
from dataclasses import dataclass
import warnings

# Importaciones internas
try:
    from .colormaps import PaletaColoresESD, PaletaColoresSismicidad
except ImportError:
    from colormaps import PaletaColoresESD, PaletaColoresSismicidad

# Tipos para compatibilidad
try:
    from ..analysis.esd import ResultadoESD, ConfiguracionESD
    from ..core.catalog import CatalogoSismico
except ImportError:
    # Definiciones mínimas para standalone
    ResultadoESD = Any
    ConfiguracionESD = Any
    CatalogoSismico = Any


# =============================================================================
# CONFIGURACIÓN DE ESTILOS
# =============================================================================

ESTILOS_MATPLOTLIB = {
    'paper': {
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.titlesize': 14,
        'axes.linewidth': 0.8,
        'lines.linewidth': 1.0,
        'axes.grid': True,
        'grid.alpha': 0.3,
    },
    'presentacion': {
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
        'axes.grid': True,
        'grid.alpha': 0.4,
    },
    'minimal': {
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'DejaVu Serif'],
        'font.size': 9,
        'axes.labelsize': 10,
        'axes.titlesize': 11,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'legend.fontsize': 8,
        'figure.titlesize': 12,
        'axes.linewidth': 0.5,
        'lines.linewidth': 0.8,
        'axes.grid': False,
    },
    'dark': {
        'figure.facecolor': '#1a1a2e',
        'axes.facecolor': '#16213e',
        'axes.edgecolor': '#e94560',
        'axes.labelcolor': '#eaeaea',
        'text.color': '#eaeaea',
        'xtick.color': '#eaeaea',
        'ytick.color': '#eaeaea',
        'grid.color': '#0f3460',
        'font.family': 'sans-serif',
        'font.size': 10,
        'axes.grid': True,
        'grid.alpha': 0.5,
    },
    'seismex': {
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica'],
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'axes.titleweight': 'bold',
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'legend.framealpha': 0.9,
        'figure.titlesize': 14,
        'figure.titleweight': 'bold',
        'axes.linewidth': 1.0,
        'lines.linewidth': 1.2,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
    },
}


@dataclass
class ConfigVisualizacion:
    """Configuración para visualización."""
    fuente_titulo: str = 'Arial'
    tamano_titulo: int = 14
    fuente_ejes: str = 'Arial'
    tamano_ejes: int = 12
    colorbar_orientacion: str = 'vertical'
    colorbar_shrink: float = 0.8
    grid_alpha: float = 0.3
    linea_costa: bool = True
    color_oceano: str = '#e6f3ff'
    mostrar_escala: bool = True
    idioma: str = 'es'


class VisualizadorESD:
    """
    Visualizador principal para resultados de ESD.
    
    Genera gráficos de alta calidad para publicación científica,
    presentaciones y análisis interactivo.
    
    Attributes:
        resultado: ResultadoESD con los datos a visualizar
        catalogo: CatalogoSismico opcional para superponer epicentros
        dpi: Resolución de las figuras
        estilo: Estilo visual ('paper', 'presentacion', 'minimal', 'dark', 'seismex')
        
    Example:
        >>> viz = VisualizadorESD(resultado_esd, catalogo, estilo='seismex')
        >>> fig = viz.graficar_seccion_horizontal(profundidad_km=30)
        >>> viz.crear_panel_completo([10, 30, 50], guardar='panel_esd.png')
    """
    
    # Etiquetas en español e inglés
    ETIQUETAS = {
        'es': {
            'profundidad': 'Profundidad (km)',
            'latitud': 'Latitud (°)',
            'longitud': 'Longitud (°)',
            'magnitud': 'Magnitud',
            'esd_label': 'log₁₀(ESD normalizado)',
            'titulo_horizontal': 'Sección Horizontal ESD - Profundidad = {prof:.0f} km',
            'titulo_ns': 'Sección N-S @ {lon:.2f}°',
            'titulo_ew': 'Sección E-W @ {lat:.2f}°N',
            'titulo_gr': 'Distribución de Magnitudes',
            'eventos': 'Eventos',
            'acumulativo': 'Acumulativo',
            'directo': 'Directo',
        },
        'en': {
            'profundidad': 'Depth (km)',
            'latitud': 'Latitude (°)',
            'longitud': 'Longitude (°)',
            'magnitud': 'Magnitude',
            'esd_label': 'Normalized Log₁₀ ESD',
            'titulo_horizontal': 'ESD Horizontal Section - Depth = {prof:.0f} km',
            'titulo_ns': 'N-S Section @ {lon:.2f}°',
            'titulo_ew': 'E-W Section @ {lat:.2f}°N',
            'titulo_gr': 'Magnitude Distribution',
            'eventos': 'Events',
            'acumulativo': 'Cumulative',
            'directo': 'Direct',
        }
    }
    
    def __init__(self,
                 resultado: ResultadoESD,
                 catalogo: Optional[CatalogoSismico] = None,
                 dpi: int = 150,
                 estilo: str = 'seismex',
                 idioma: str = 'es',
                 config: Optional[Union[ConfigVisualizacion, Dict]] = None):
        """
        Inicializa el visualizador.
        
        Args:
            resultado: ResultadoESD con los datos a visualizar
            catalogo: CatalogoSismico opcional para superponer epicentros
            dpi: Resolución de las figuras
            estilo: Estilo de visualización
            idioma: Idioma ('es' o 'en')
            config: Configuración personalizada
        """
        self.resultado = resultado
        self.catalogo = catalogo
        self.dpi = dpi
        self.estilo = estilo
        self.idioma = idioma
        
        # Configuración
        if config is None:
            self.config = ConfigVisualizacion(idioma=idioma)
        elif isinstance(config, dict):
            self.config = ConfigVisualizacion(**config)
        else:
            self.config = config
        
        # Configurar estilo matplotlib
        self._configurar_estilo()
        
        # Crear paleta de colores
        self._paleta = PaletaColoresESD()
        self.cmap = self._paleta.obtener_colormap('esd')
        self.niveles = self._paleta.obtener_niveles_esd()
        
        # Etiquetas según idioma
        self._etiquetas = self.ETIQUETAS.get(idioma, self.ETIQUETAS['en'])
    
    def _configurar_estilo(self):
        """Configura el estilo de matplotlib según el uso."""
        if self.estilo in ESTILOS_MATPLOTLIB:
            plt.rcParams.update(ESTILOS_MATPLOTLIB[self.estilo])
        else:
            warnings.warn(f"Estilo '{self.estilo}' no reconocido. Usando 'seismex'.")
            plt.rcParams.update(ESTILOS_MATPLOTLIB['seismex'])
    
    def _obtener_etiqueta(self, clave: str) -> str:
        """Obtiene una etiqueta en el idioma configurado."""
        return self._etiquetas.get(clave, clave)
    
    # =========================================================================
    # SECCIONES HORIZONTALES
    # =========================================================================
    
    def graficar_seccion_horizontal(self,
                                    profundidad_km: float,
                                    ax: Optional[plt.Axes] = None,
                                    mostrar_epicentros: bool = True,
                                    mostrar_colorbar: bool = True,
                                    titulo: Optional[str] = None,
                                    mostrar_fallas: bool = False,
                                    mostrar_volcanes: bool = False,
                                    guardar: Optional[str] = None,
                                    **kwargs) -> plt.Axes:
        """
        Grafica una sección horizontal de ESD a una profundidad dada.
        
        Args:
            profundidad_km: Profundidad del corte en km
            ax: Axes de matplotlib (crea uno nuevo si no se proporciona)
            mostrar_epicentros: Superponer epicentros del catálogo
            mostrar_colorbar: Mostrar barra de colores
            titulo: Título personalizado
            mostrar_fallas: Mostrar trazas de fallas (si disponible)
            mostrar_volcanes: Mostrar ubicación de volcanes (si disponible)
            guardar: Ruta para guardar la figura
            **kwargs: Argumentos adicionales para contourf
            
        Returns:
            Axes con el gráfico
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(10, 8), dpi=self.dpi)
        else:
            fig = ax.get_figure()
        
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
            self._agregar_epicentros_horizontal(ax, prof_real)
        
        # Colorbar
        if mostrar_colorbar:
            cbar = plt.colorbar(cf, ax=ax, shrink=self.config.colorbar_shrink, pad=0.02)
            cbar.set_label(self._obtener_etiqueta('esd_label'), fontsize=10)
        
        # Etiquetas y título
        ax.set_xlabel(self._obtener_etiqueta('longitud'))
        ax.set_ylabel(self._obtener_etiqueta('latitud'))
        
        if titulo is None:
            titulo = self._obtener_etiqueta('titulo_horizontal').format(prof=prof_real)
        ax.set_title(titulo)
        
        # Aspecto igual
        ax.set_aspect('equal')
        
        # Guardar si se especifica
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return ax
    
    def _agregar_epicentros_horizontal(self, ax: plt.Axes, profundidad_km: float):
        """Agrega epicentros a una sección horizontal."""
        if self.catalogo is None:
            return
        
        datos = self.catalogo.datos
        
        # Filtrar por profundidad cercana
        tamano_celda = getattr(self.resultado.configuracion, 'tamano_celda_km', 10.0)
        prof_min = profundidad_km - tamano_celda / 2
        prof_max = profundidad_km + tamano_celda / 2
        
        mascara = (
            (datos['profundidad_km'].abs() >= prof_min) &
            (datos['profundidad_km'].abs() <= prof_max)
        )
        
        if mascara.sum() > 0:
            datos_filtrados = datos[mascara]
            sizes = (datos_filtrados['magnitud'] ** 2) * 5
            
            ax.scatter(
                datos_filtrados['longitud'],
                datos_filtrados['latitud'],
                s=sizes,
                c='black',
                alpha=0.5,
                edgecolors='white',
                linewidths=0.5,
                zorder=10,
                label=f'Sismos (n={mascara.sum()})'
            )
    
    def graficar_secciones_horizontales(self,
                                        profundidades: List[float],
                                        columnas: int = 2,
                                        tamanio_figura: Optional[Tuple[float, float]] = None,
                                        guardar: Optional[str] = None) -> plt.Figure:
        """
        Grafica múltiples secciones horizontales en un panel.
        
        Args:
            profundidades: Lista de profundidades en km
            columnas: Número de columnas del panel
            tamanio_figura: Tamaño de la figura (ancho, alto)
            guardar: Ruta para guardar la figura
            
        Returns:
            Figure de matplotlib
        """
        n_paneles = len(profundidades)
        filas = int(np.ceil(n_paneles / columnas))
        
        if tamanio_figura is None:
            tamanio_figura = (5 * columnas, 4 * filas)
        
        fig, axes = plt.subplots(filas, columnas, figsize=tamanio_figura, dpi=self.dpi)
        
        # Aplanar axes si es necesario
        if n_paneles == 1:
            axes = np.array([axes])
        axes = axes.flatten()
        
        for i, prof in enumerate(profundidades):
            if i < len(axes):
                self.graficar_seccion_horizontal(
                    prof,
                    ax=axes[i],
                    mostrar_colorbar=(i == 0),
                    titulo=None
                )
                
                # Etiqueta de panel
                axes[i].text(0.02, 0.98, f'{chr(97 + i)})',
                            transform=axes[i].transAxes,
                            fontsize=14, fontweight='bold',
                            va='top', ha='left',
                            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                axes[i].set_title(f'{self._obtener_etiqueta("profundidad").split()[0]} = {prof:.0f} km')
        
        # Ocultar axes vacíos
        for i in range(n_paneles, len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return fig
    
    # =========================================================================
    # SECCIONES VERTICALES
    # =========================================================================
    
    def graficar_seccion_vertical_ns(self,
                                     longitud: float,
                                     ax: Optional[plt.Axes] = None,
                                     mostrar_epicentros: bool = True,
                                     mostrar_colorbar: bool = True,
                                     mostrar_moho: bool = False,
                                     mostrar_slab: bool = False,
                                     titulo: Optional[str] = None,
                                     guardar: Optional[str] = None,
                                     **kwargs) -> plt.Axes:
        """
        Grafica una sección vertical N-S a una longitud dada.
        
        Args:
            longitud: Longitud del corte en grados
            ax: Axes de matplotlib
            mostrar_epicentros: Superponer hipocentros proyectados
            mostrar_colorbar: Mostrar barra de colores
            mostrar_moho: Mostrar línea de Moho (si disponible)
            mostrar_slab: Mostrar contornos de subducción (si disponible)
            titulo: Título personalizado
            guardar: Ruta para guardar la figura
            
        Returns:
            Axes con el gráfico
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(10, 6), dpi=self.dpi)
        else:
            fig = ax.get_figure()
        
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
            self._agregar_hipocentros_ns(ax, lon_real)
        
        if mostrar_colorbar:
            cbar = plt.colorbar(cf, ax=ax, shrink=0.8, pad=0.02)
            cbar.set_label(self._obtener_etiqueta('esd_label'), fontsize=10)
        
        ax.set_xlabel('UTM North (m)')
        ax.set_ylabel(self._obtener_etiqueta('profundidad').replace('(km)', '(m)'))
        
        if titulo is None:
            titulo = self._obtener_etiqueta('titulo_ns').format(lon=lon_real)
        ax.set_title(titulo)
        
        ax.invert_yaxis()
        
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return ax
    
    def _agregar_hipocentros_ns(self, ax: plt.Axes, longitud: float):
        """Agrega hipocentros a una sección N-S."""
        if self.catalogo is None:
            return
        
        datos = self.catalogo.datos
        ancho = 0.1  # grados
        
        mascara = (
            (datos['longitud'] >= longitud - ancho) &
            (datos['longitud'] <= longitud + ancho)
        )
        
        if mascara.sum() > 0:
            datos_filtrados = datos[mascara]
            lat_m_eventos = datos_filtrados['latitud'].values * 111000
            prof_m_eventos = -datos_filtrados['profundidad_km'].abs().values * 1000
            sizes = (datos_filtrados['magnitud'] ** 2) * 3
            
            ax.scatter(lat_m_eventos, prof_m_eventos,
                      s=sizes, c='black', alpha=0.5,
                      edgecolors='white', linewidths=0.3, zorder=10)
    
    def graficar_seccion_vertical_ew(self,
                                     latitud: float,
                                     ax: Optional[plt.Axes] = None,
                                     mostrar_epicentros: bool = True,
                                     mostrar_colorbar: bool = True,
                                     mostrar_moho: bool = False,
                                     mostrar_slab: bool = False,
                                     titulo: Optional[str] = None,
                                     guardar: Optional[str] = None,
                                     **kwargs) -> plt.Axes:
        """
        Grafica una sección vertical E-W a una latitud dada.
        
        Args:
            latitud: Latitud del corte en grados
            ax: Axes de matplotlib
            mostrar_epicentros: Superponer hipocentros proyectados
            mostrar_colorbar: Mostrar barra de colores
            mostrar_moho: Mostrar línea de Moho
            mostrar_slab: Mostrar contornos de subducción
            titulo: Título personalizado
            guardar: Ruta para guardar la figura
            
        Returns:
            Axes con el gráfico
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(12, 5), dpi=self.dpi)
        else:
            fig = ax.get_figure()
        
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
            self._agregar_hipocentros_ew(ax, lat_real)
        
        if mostrar_colorbar:
            cbar = plt.colorbar(cf, ax=ax, shrink=0.8, pad=0.02)
            cbar.set_label(self._obtener_etiqueta('esd_label'), fontsize=10)
        
        ax.set_xlabel('UTM East (m)')
        ax.set_ylabel(self._obtener_etiqueta('profundidad').replace('(km)', '(m)'))
        
        if titulo is None:
            titulo = self._obtener_etiqueta('titulo_ew').format(lat=lat_real)
        ax.set_title(titulo)
        
        ax.invert_yaxis()
        
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return ax
    
    def _agregar_hipocentros_ew(self, ax: plt.Axes, latitud: float):
        """Agrega hipocentros a una sección E-W."""
        if self.catalogo is None:
            return
        
        datos = self.catalogo.datos
        ancho = 0.1
        
        mascara = (
            (datos['latitud'] >= latitud - ancho) &
            (datos['latitud'] <= latitud + ancho)
        )
        
        if mascara.sum() > 0:
            datos_filtrados = datos[mascara]
            lon_m_eventos = (datos_filtrados['longitud'].values * 111000 *
                            np.cos(np.radians(latitud)))
            prof_m_eventos = -datos_filtrados['profundidad_km'].abs().values * 1000
            sizes = (datos_filtrados['magnitud'] ** 2) * 3
            
            ax.scatter(lon_m_eventos, prof_m_eventos,
                      s=sizes, c='black', alpha=0.5,
                      edgecolors='white', linewidths=0.3, zorder=10)
    
    def graficar_secciones_verticales(self,
                                      perfiles: List[Dict[str, Union[str, float]]],
                                      guardar: Optional[str] = None) -> plt.Figure:
        """
        Grafica múltiples perfiles verticales.
        
        Args:
            perfiles: Lista de diccionarios con 'tipo' ('ns' o 'ew') y 'valor'
            guardar: Ruta para guardar la figura
            
        Returns:
            Figure de matplotlib
        """
        n_total = len(perfiles)
        fig, axes = plt.subplots(n_total, 1, figsize=(12, 4 * n_total), dpi=self.dpi)
        
        if n_total == 1:
            axes = [axes]
        
        for i, perfil in enumerate(perfiles):
            tipo = perfil.get('tipo', 'ns')
            valor = perfil.get('valor', 0)
            
            if tipo.lower() == 'ns':
                self.graficar_seccion_vertical_ns(
                    valor, ax=axes[i], mostrar_colorbar=True)
            else:
                self.graficar_seccion_vertical_ew(
                    valor, ax=axes[i], mostrar_colorbar=True)
            
            axes[i].text(0.02, 0.98, f'{chr(97 + i)})',
                        transform=axes[i].transAxes,
                        fontsize=14, fontweight='bold',
                        va='top', ha='left',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return fig
    
    # =========================================================================
    # PANELES COMPLETOS
    # =========================================================================
    
    def crear_panel_completo(self,
                             profundidades: List[float] = [5, 10, 20, 35],
                             guardar: Optional[str] = None) -> plt.Figure:
        """
        Crea un panel con múltiples secciones horizontales.
        
        Similar a la Figura 3 del paper de España (Del Pezzo et al.).
        
        Args:
            profundidades: Lista de profundidades en km
            guardar: Ruta para guardar la figura
            
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
                mostrar_colorbar=(i == 0),
                titulo=None
            )
            
            ax.text(0.02, 0.98, f'{chr(97 + i)})',
                   transform=ax.transAxes,
                   fontsize=14, fontweight='bold',
                   va='top', ha='left',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            ax.set_title(f'{self._obtener_etiqueta("profundidad").split()[0]} = {prof:.0f} km')
        
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
        perfiles = []
        for lon in longitudes_ns:
            perfiles.append({'tipo': 'ns', 'valor': lon})
        for lat in latitudes_ew:
            perfiles.append({'tipo': 'ew', 'valor': lat})
        
        return self.graficar_secciones_verticales(perfiles, guardar=guardar)
    
    # =========================================================================
    # GUTENBERG-RICHTER
    # =========================================================================
    
    def graficar_gutenberg_richter(self,
                                   magnitudes: np.ndarray,
                                   b_value: float,
                                   a_value: float,
                                   mc: float,
                                   b_error: float = 0.0,
                                   a_error: float = 0.0,
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
            b_error: Error del valor b
            a_error: Error del valor a
            ax: Axes de matplotlib
            guardar: Ruta para guardar
            
        Returns:
            Axes con el gráfico
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(8, 6), dpi=self.dpi)
        else:
            fig = ax.get_figure()
        
        # Crear histograma
        bin_width = 0.1
        bins = np.arange(magnitudes.min(), magnitudes.max() + bin_width, bin_width)
        hist, bin_edges = np.histogram(magnitudes, bins=bins)
        mags_centro = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Distribución acumulativa
        cumsum = np.cumsum(hist[::-1])[::-1]
        
        # Graficar datos directos
        valid_direct = hist > 0
        ax.scatter(mags_centro[valid_direct], np.log10(hist[valid_direct]),
                  marker='o', s=60, c='black',
                  label=self._obtener_etiqueta('directo'), zorder=5)
        
        # Graficar datos acumulativos
        valid_cum = cumsum > 0
        ax.scatter(mags_centro[valid_cum], np.log10(cumsum[valid_cum]),
                  marker='^', s=60, facecolors='none', edgecolors='red',
                  linewidths=1.5,
                  label=self._obtener_etiqueta('acumulativo'), zorder=5)
        
        # Línea de ajuste
        mag_linea = np.linspace(mc - 0.5, magnitudes.max() + 0.5, 100)
        log_n_cum = a_value - b_value * mag_linea
        ax.plot(mag_linea, log_n_cum, 'r-', linewidth=2,
               label=f'b = {b_value:.2f}')
        
        # Añadir ecuación
        ecuacion = f'log₁₀(N) = ({a_value:.2f}±{a_error:.2f}) - ({b_value:.2f}±{b_error:.2f})M'
        ax.text(0.05, 0.95, ecuacion,
               transform=ax.transAxes,
               fontsize=10, color='red',
               va='top', ha='left',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.set_xlabel(self._obtener_etiqueta('magnitud'))
        ax.set_ylabel('log₁₀(N)')
        ax.set_title(self._obtener_etiqueta('titulo_gr'))
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Marcar Mc
        ax.axvline(mc, color='gray', linestyle='--', alpha=0.7)
        ax.text(mc + 0.1, ax.get_ylim()[1] * 0.9, f'Mc = {mc:.1f}',
               fontsize=10, color='gray')
        
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return ax
    
    # =========================================================================
    # VISUALIZACIÓN 3D
    # =========================================================================
    
    def graficar_3d(self,
                    umbral_esd: float = -3.0,
                    opacidad: float = 0.7,
                    azimuth: float = -60,
                    elevacion: float = 30,
                    guardar: Optional[str] = None) -> plt.Figure:
        """
        Crea una visualización 3D del campo ESD.
        
        Args:
            umbral_esd: Solo mostrar ESD > umbral
            opacidad: Opacidad de los puntos (0-1)
            azimuth: Ángulo de azimut de la vista
            elevacion: Ángulo de elevación de la vista
            guardar: Ruta para guardar
            
        Returns:
            Figure de matplotlib
        """
        fig = plt.figure(figsize=(12, 10), dpi=self.dpi)
        ax = fig.add_subplot(111, projection='3d')
        
        # Crear meshgrid 3D
        X, Y, Z = np.meshgrid(
            self.resultado.grid_x,
            self.resultado.grid_y,
            -self.resultado.grid_z,
            indexing='ij'
        )
        
        # Filtrar por umbral
        mascara = self.resultado.esd_log10 > umbral_esd
        
        if mascara.sum() > 0:
            # Obtener valores
            x_plot = X[mascara]
            y_plot = Y[mascara]
            z_plot = Z[mascara]
            esd_plot = self.resultado.esd_log10[mascara]
            
            # Normalizar para colores
            norm = plt.Normalize(vmin=umbral_esd, vmax=self.resultado.esd_log10.max())
            colors = self.cmap(norm(esd_plot))
            colors[:, 3] = opacidad
            
            # Graficar
            scatter = ax.scatter(x_plot, y_plot, z_plot,
                               c=esd_plot, cmap=self.cmap,
                               s=5, alpha=opacidad)
            
            # Colorbar
            cbar = fig.colorbar(scatter, ax=ax, shrink=0.6, pad=0.1)
            cbar.set_label(self._obtener_etiqueta('esd_label'))
        
        ax.set_xlabel(self._obtener_etiqueta('longitud'))
        ax.set_ylabel(self._obtener_etiqueta('latitud'))
        ax.set_zlabel(self._obtener_etiqueta('profundidad'))
        ax.set_title('ESD 3D')
        
        ax.view_init(elev=elevacion, azim=azimuth)
        
        if guardar:
            fig.savefig(guardar, dpi=self.dpi, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return fig
    
    # =========================================================================
    # MÉTODOS DE EXPORTACIÓN
    # =========================================================================
    
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
        datos = self.resultado.esd_log10[:, :, iz].T
        
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
            niveles: Niveles de contorno
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
            if i < len(cs.collections):
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
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def crear_figura_base(self,
                          profundidad_km: float,
                          figsize: Tuple[float, float] = (10, 8)) -> Tuple[plt.Figure, plt.Axes]:
        """
        Crea una figura base con la sección ESD para personalización.
        
        Args:
            profundidad_km: Profundidad de la sección
            figsize: Tamaño de la figura
            
        Returns:
            Tupla (Figure, Axes) para personalización adicional
        """
        fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=self.dpi)
        self.graficar_seccion_horizontal(profundidad_km, ax=ax)
        return fig, ax
    
    def cambiar_estilo(self, estilo: str):
        """
        Cambia el estilo de visualización.
        
        Args:
            estilo: Nuevo estilo a aplicar
        """
        self.estilo = estilo
        self._configurar_estilo()
    
    def cambiar_idioma(self, idioma: str):
        """
        Cambia el idioma de las etiquetas.
        
        Args:
            idioma: 'es' o 'en'
        """
        self.idioma = idioma
        self._etiquetas = self.ETIQUETAS.get(idioma, self.ETIQUETAS['en'])


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

def ejemplo_visualizacion():
    """Ejemplo de uso del módulo de visualización."""
    import pandas as pd
    
    print("=" * 70)
    print("SEISMEX - Ejemplo de Visualización ESD")
    print("=" * 70)
    
    # Simular datos (normalmente vendrían de CalculadoraESD)
    np.random.seed(42)
    
    # Crear grids simulados
    grid_x = np.linspace(-104.5, -103.5, 40)
    grid_y = np.linspace(18.5, 19.5, 40)
    grid_z = np.linspace(0, 100, 20)
    
    # Crear ESD simulado (zona de alta energía centrada)
    X, Y, Z = np.meshgrid(grid_x, grid_y, grid_z, indexing='ij')
    centro_x, centro_y, centro_z = -104.0, 19.0, 40
    
    distancia = np.sqrt(
        ((X - centro_x) * 111) ** 2 +
        ((Y - centro_y) * 111) ** 2 +
        (Z - centro_z) ** 2
    )
    
    esd_log10 = -12 + 12 * np.exp(-distancia ** 2 / (2 * 30 ** 2))
    esd_log10 += np.random.normal(0, 0.5, esd_log10.shape)
    
    # Crear objeto ResultadoESD simulado
    class ResultadoSimulado:
        def __init__(self):
            self.grid_x = grid_x
            self.grid_y = grid_y
            self.grid_z = grid_z
            self.esd_log10 = esd_log10
            self.configuracion = type('obj', (object,), {'tamano_celda_km': 10.0})()
    
    resultado = ResultadoSimulado()
    
    # Crear catálogo simulado
    n_eventos = 200
    datos_cat = pd.DataFrame({
        'fecha': pd.date_range('2020-01-01', periods=n_eventos, freq='D'),
        'latitud': np.random.normal(19.0, 0.3, n_eventos),
        'longitud': np.random.normal(-104.0, 0.3, n_eventos),
        'profundidad_km': np.abs(np.random.exponential(30, n_eventos)),
        'magnitud': np.random.exponential(0.7, n_eventos) + 2.0
    })
    
    class CatalogoSimulado:
        def __init__(self, datos):
            self.datos = datos
    
    catalogo = CatalogoSimulado(datos_cat)
    
    # Crear visualizador
    viz = VisualizadorESD(resultado, catalogo, estilo='seismex', idioma='es')
    
    print("\nGenerando figuras...")
    
    # Sección horizontal
    fig1, ax1 = plt.subplots(figsize=(10, 8))
    viz.graficar_seccion_horizontal(30, ax=ax1)
    
    # Panel de secciones
    fig2 = viz.crear_panel_completo([10, 30, 50, 70])
    
    # Gutenberg-Richter
    fig3, ax3 = plt.subplots(figsize=(8, 6))
    mags = datos_cat['magnitud'].values
    viz.graficar_gutenberg_richter(
        mags,
        b_value=1.0,
        a_value=4.5,
        mc=2.5,
        b_error=0.05,
        a_error=0.1,
        ax=ax3
    )
    
    print("\n✓ Visualización completada")
    
    return viz


if __name__ == "__main__":
    viz = ejemplo_visualizacion()
    plt.show()
