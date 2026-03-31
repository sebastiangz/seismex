#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX - Módulo de Paletas de Colores para ESD
================================================================================
Paletas de colores personalizadas para visualización de Energy Space Density.
Basadas en las convenciones del paper de Del Pezzo et al. y estándares
de visualización sísmica.

Autor: SEISMEX Project
Versión: 1.0.0
================================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import (
    LinearSegmentedColormap,
    BoundaryNorm,
    Normalize,
    ListedColormap
)
from typing import List, Tuple, Optional, Dict, Union


class PaletaColoresESD:
    """
    Paletas de colores personalizadas para visualización de ESD.
    
    Proporciona colormaps optimizados para representar valores de
    Energy Space Density, tanto continuos como discretos.
    
    Basada en las convenciones del paper de Del Pezzo et al. (2016)
    y estándares de visualización en sismología.
    
    Attributes:
        niveles_estandar: Lista de niveles de contorno estándar
        colores_hex: Lista de colores en formato hexadecimal
        
    Example:
        >>> paleta = PaletaColoresESD()
        >>> cmap = paleta.obtener_colormap()
        >>> norm = paleta.obtener_normalizacion()
        >>> plt.contourf(X, Y, Z, cmap=cmap, norm=norm, levels=paleta.niveles_estandar)
    """
    
    # Niveles de contorno estándar para ESD normalizado (log10)
    # Basados en el paper de España (Del Pezzo et al.)
    NIVELES_ESTANDAR: List[float] = [
        -12.0, -7.0, -4.5, -3.0, -2.5, -2.0, -1.0, -0.5, 0.0, 0.5
    ]
    
    # Colores para la paleta ESD principal
    # Transición: Índigo → Azul → Verde → Amarillo → Rosa → Rojo
    COLORES_ESD: List[str] = [
        '#4B0082',  # Índigo oscuro (muy bajo)
        '#0000CD',  # Azul medio
        '#00BFFF',  # Azul cielo
        '#00FF7F',  # Verde primavera
        '#98FB98',  # Verde pálido
        '#FFFFE0',  # Amarillo claro
        '#FFB6C1',  # Rosa claro
        '#FF69B4',  # Rosa fuerte
        '#DC143C',  # Carmesí
        '#8B0000',  # Rojo oscuro (muy alto)
    ]
    
    # Colores para paleta divergente (anomalías)
    COLORES_DIVERGENTE: List[str] = [
        '#053061',  # Azul muy oscuro
        '#2166AC',  # Azul
        '#4393C3',  # Azul claro
        '#92C5DE',  # Azul muy claro
        '#D1E5F0',  # Azul pálido
        '#F7F7F7',  # Blanco/gris muy claro (centro)
        '#FDDBC7',  # Rosa pálido
        '#F4A582',  # Rosa claro
        '#D6604D',  # Rosa/rojo
        '#B2182B',  # Rojo
        '#67001F',  # Rojo muy oscuro
    ]
    
    # Colores para paleta secuencial (magnitudes, profundidades)
    COLORES_SECUENCIAL: List[str] = [
        '#FFFFCC',  # Amarillo muy claro
        '#FFEDA0',  # Amarillo claro
        '#FED976',  # Amarillo
        '#FEB24C',  # Naranja claro
        '#FD8D3C',  # Naranja
        '#FC4E2A',  # Naranja rojizo
        '#E31A1C',  # Rojo
        '#BD0026',  # Rojo oscuro
        '#800026',  # Rojo muy oscuro
    ]
    
    # Colores para sismicidad (profundidad)
    COLORES_PROFUNDIDAD: List[str] = [
        '#FF0000',  # 0-20 km (rojo - superficial)
        '#FF8C00',  # 20-40 km (naranja)
        '#FFD700',  # 40-70 km (amarillo)
        '#32CD32',  # 70-100 km (verde)
        '#1E90FF',  # 100-150 km (azul)
        '#0000CD',  # 150-300 km (azul oscuro)
        '#4B0082',  # >300 km (índigo - profundo)
    ]
    
    def __init__(self):
        """Inicializa la paleta de colores ESD."""
        self.niveles_estandar = self.NIVELES_ESTANDAR.copy()
        self.colores_hex = self.COLORES_ESD.copy()
        
        # Crear colormaps principales
        self._cmap_esd = self._crear_colormap(self.COLORES_ESD, 'esd_cmap')
        self._cmap_divergente = self._crear_colormap(self.COLORES_DIVERGENTE, 'esd_divergente')
        self._cmap_secuencial = self._crear_colormap(self.COLORES_SECUENCIAL, 'esd_secuencial')
        self._cmap_profundidad = self._crear_colormap(self.COLORES_PROFUNDIDAD, 'esd_profundidad')
    
    @staticmethod
    def _crear_colormap(colores: List[str], nombre: str, N: int = 256) -> LinearSegmentedColormap:
        """
        Crea un colormap a partir de una lista de colores hexadecimales.
        
        Args:
            colores: Lista de colores en formato hexadecimal
            nombre: Nombre del colormap
            N: Número de niveles de discretización
            
        Returns:
            LinearSegmentedColormap
        """
        return LinearSegmentedColormap.from_list(nombre, colores, N=N)
    
    @staticmethod
    def crear_paleta_esd() -> LinearSegmentedColormap:
        """
        Crea la paleta de colores principal para ESD.
        
        Transición suave de colores fríos (baja energía) a cálidos (alta energía):
        Índigo → Azul → Verde → Amarillo → Rosa → Rojo
        
        Returns:
            LinearSegmentedColormap para usar con matplotlib
        """
        return LinearSegmentedColormap.from_list(
            'esd_cmap',
            PaletaColoresESD.COLORES_ESD,
            N=256
        )
    
    @staticmethod
    def crear_paleta_divergente() -> LinearSegmentedColormap:
        """
        Crea paleta divergente centrada en cero.
        
        Ideal para representar anomalías o diferencias:
        Azul (negativo) → Blanco (cero) → Rojo (positivo)
        
        Returns:
            LinearSegmentedColormap
        """
        return LinearSegmentedColormap.from_list(
            'esd_divergente',
            PaletaColoresESD.COLORES_DIVERGENTE,
            N=256
        )
    
    @staticmethod
    def crear_paleta_profundidad() -> LinearSegmentedColormap:
        """
        Crea paleta para representar profundidad de sismos.
        
        Colores cálidos para eventos superficiales, fríos para profundos.
        
        Returns:
            LinearSegmentedColormap
        """
        return LinearSegmentedColormap.from_list(
            'esd_profundidad',
            PaletaColoresESD.COLORES_PROFUNDIDAD,
            N=256
        )
    
    @staticmethod
    def obtener_niveles_esd() -> List[float]:
        """
        Obtiene los niveles de contorno estándar para ESD normalizado.
        
        Basado en los niveles usados en el paper de España (Del Pezzo et al.):
        >0, -0.5_0, -1_-0.5, -2.0_-1.0, etc.
        
        Returns:
            Lista de niveles para contornos
        """
        return PaletaColoresESD.NIVELES_ESTANDAR.copy()
    
    def obtener_colormap(self, tipo: str = 'esd') -> LinearSegmentedColormap:
        """
        Obtiene un colormap por tipo.
        
        Args:
            tipo: Tipo de colormap ('esd', 'divergente', 'secuencial', 'profundidad')
            
        Returns:
            LinearSegmentedColormap correspondiente
        """
        mapas = {
            'esd': self._cmap_esd,
            'divergente': self._cmap_divergente,
            'secuencial': self._cmap_secuencial,
            'profundidad': self._cmap_profundidad,
        }
        
        if tipo not in mapas:
            raise ValueError(f"Tipo de colormap no válido: {tipo}. "
                           f"Opciones: {list(mapas.keys())}")
        
        return mapas[tipo]
    
    def obtener_normalizacion(self,
                               vmin: float = -12.0,
                               vmax: float = 0.5,
                               tipo: str = 'lineal') -> Normalize:
        """
        Obtiene la normalización para los valores ESD.
        
        Args:
            vmin: Valor mínimo
            vmax: Valor máximo
            tipo: Tipo de normalización ('lineal', 'log', 'discreto')
            
        Returns:
            Normalize o BoundaryNorm para matplotlib
        """
        if tipo == 'lineal':
            return Normalize(vmin=vmin, vmax=vmax)
        elif tipo == 'log':
            # Para valores positivos únicamente
            return mcolors.LogNorm(vmin=max(vmin, 1e-12), vmax=vmax)
        elif tipo == 'discreto':
            return BoundaryNorm(self.niveles_estandar, len(self.niveles_estandar) - 1)
        else:
            raise ValueError(f"Tipo de normalización no válido: {tipo}")
    
    def obtener_colores_discretos(self, n_colores: int = 10) -> ListedColormap:
        """
        Obtiene un colormap discreto con n colores.
        
        Args:
            n_colores: Número de colores discretos
            
        Returns:
            ListedColormap
        """
        cmap = self._cmap_esd
        colores = [cmap(i / (n_colores - 1)) for i in range(n_colores)]
        return ListedColormap(colores, name='esd_discreto')
    
    def obtener_color_por_valor(self, valor: float,
                                 vmin: float = -12.0,
                                 vmax: float = 0.5) -> Tuple[float, float, float, float]:
        """
        Obtiene el color RGBA correspondiente a un valor.
        
        Args:
            valor: Valor de ESD
            vmin: Valor mínimo de la escala
            vmax: Valor máximo de la escala
            
        Returns:
            Tupla (R, G, B, A) con valores entre 0 y 1
        """
        norm = Normalize(vmin=vmin, vmax=vmax)
        return self._cmap_esd(norm(valor))
    
    def obtener_hex_por_valor(self, valor: float,
                               vmin: float = -12.0,
                               vmax: float = 0.5) -> str:
        """
        Obtiene el color hexadecimal correspondiente a un valor.
        
        Args:
            valor: Valor de ESD
            vmin: Valor mínimo de la escala
            vmax: Valor máximo de la escala
            
        Returns:
            String con color hexadecimal (#RRGGBB)
        """
        rgba = self.obtener_color_por_valor(valor, vmin, vmax)
        return mcolors.rgb2hex(rgba[:3])
    
    def obtener_lista_hex(self) -> List[str]:
        """
        Obtiene la lista de colores en formato hexadecimal.
        
        Returns:
            Lista de strings con colores hexadecimales
        """
        return self.colores_hex.copy()
    
    def obtener_colores_para_niveles(self) -> Dict[float, str]:
        """
        Obtiene un diccionario de colores para cada nivel estándar.
        
        Returns:
            Dict con nivel como clave y color hex como valor
        """
        colores = {}
        for i, nivel in enumerate(self.niveles_estandar):
            if i < len(self.colores_hex):
                colores[nivel] = self.colores_hex[i]
        return colores
    
    def crear_colorbar(self,
                       ax: plt.Axes,
                       mappable: Optional[plt.cm.ScalarMappable] = None,
                       orientacion: str = 'vertical',
                       label: str = 'log₁₀(ESD normalizado)',
                       shrink: float = 0.8,
                       pad: float = 0.02) -> plt.colorbar:
        """
        Crea una barra de colores con formato estándar ESD.
        
        Args:
            ax: Axes de matplotlib
            mappable: ScalarMappable (contourf, pcolormesh, etc.)
            orientacion: 'vertical' u 'horizontal'
            label: Etiqueta de la barra de colores
            shrink: Factor de reducción
            pad: Espacio entre el gráfico y la barra
            
        Returns:
            Colorbar de matplotlib
        """
        if mappable is None:
            # Crear un mappable dummy si no se proporciona
            norm = self.obtener_normalizacion()
            sm = plt.cm.ScalarMappable(cmap=self._cmap_esd, norm=norm)
            sm.set_array([])
            mappable = sm
        
        cbar = plt.colorbar(
            mappable,
            ax=ax,
            orientation=orientacion,
            shrink=shrink,
            pad=pad
        )
        cbar.set_label(label, fontsize=10)
        
        return cbar
    
    def mostrar_paletas(self, guardar: Optional[str] = None):
        """
        Muestra todas las paletas disponibles.
        
        Args:
            guardar: Ruta para guardar la figura (opcional)
        """
        fig, axes = plt.subplots(4, 1, figsize=(10, 6))
        
        paletas = [
            (self._cmap_esd, 'ESD Principal'),
            (self._cmap_divergente, 'Divergente'),
            (self._cmap_secuencial, 'Secuencial'),
            (self._cmap_profundidad, 'Profundidad'),
        ]
        
        gradient = np.linspace(0, 1, 256).reshape(1, -1)
        
        for ax, (cmap, nombre) in zip(axes, paletas):
            ax.imshow(gradient, aspect='auto', cmap=cmap)
            ax.set_title(nombre, fontsize=10)
            ax.set_yticks([])
            ax.set_xticks([0, 64, 128, 192, 255])
            ax.set_xticklabels(['0.0', '0.25', '0.5', '0.75', '1.0'])
        
        plt.suptitle('Paletas de Colores SEISMEX', fontsize=12, fontweight='bold')
        plt.tight_layout()
        
        if guardar:
            fig.savefig(guardar, dpi=150, bbox_inches='tight')
            print(f"Figura guardada: {guardar}")
        
        return fig


class PaletaColoresSismicidad:
    """
    Paletas de colores especializadas para visualización de sismicidad.
    
    Proporciona colormaps para magnitudes, profundidades, tiempo, y otros
    atributos sísmicos comunes.
    """
    
    # Rangos de profundidad estándar (km)
    RANGOS_PROFUNDIDAD = [0, 20, 40, 70, 100, 150, 300, 700]
    
    # Colores para magnitud (de menor a mayor)
    COLORES_MAGNITUD = [
        '#FFFFB2',  # M < 2 (amarillo claro)
        '#FECC5C',  # M 2-3 (naranja claro)
        '#FD8D3C',  # M 3-4 (naranja)
        '#F03B20',  # M 4-5 (rojo-naranja)
        '#BD0026',  # M 5-6 (rojo oscuro)
        '#800026',  # M > 6 (rojo muy oscuro)
    ]
    
    def __init__(self):
        """Inicializa las paletas de sismicidad."""
        self._cmap_magnitud = LinearSegmentedColormap.from_list(
            'sismex_magnitud', self.COLORES_MAGNITUD, N=256
        )
        self._cmap_profundidad = PaletaColoresESD.crear_paleta_profundidad()
    
    def obtener_colormap_magnitud(self) -> LinearSegmentedColormap:
        """Obtiene el colormap para magnitudes."""
        return self._cmap_magnitud
    
    def obtener_colormap_profundidad(self) -> LinearSegmentedColormap:
        """Obtiene el colormap para profundidades."""
        return self._cmap_profundidad
    
    def color_por_magnitud(self, magnitud: float,
                           m_min: float = 0.0,
                           m_max: float = 8.0) -> str:
        """
        Obtiene el color hexadecimal para una magnitud.
        
        Args:
            magnitud: Valor de magnitud
            m_min: Magnitud mínima de la escala
            m_max: Magnitud máxima de la escala
            
        Returns:
            Color en formato hexadecimal
        """
        norm = Normalize(vmin=m_min, vmax=m_max)
        rgba = self._cmap_magnitud(norm(magnitud))
        return mcolors.rgb2hex(rgba[:3])
    
    def color_por_profundidad(self, profundidad_km: float) -> str:
        """
        Obtiene el color hexadecimal para una profundidad.
        
        Args:
            profundidad_km: Profundidad en kilómetros
            
        Returns:
            Color en formato hexadecimal
        """
        # Encontrar el rango correspondiente
        for i, (p_min, p_max) in enumerate(zip(self.RANGOS_PROFUNDIDAD[:-1],
                                                self.RANGOS_PROFUNDIDAD[1:])):
            if p_min <= profundidad_km < p_max:
                return PaletaColoresESD.COLORES_PROFUNDIDAD[i]
        
        # Si es más profundo que el último rango
        return PaletaColoresESD.COLORES_PROFUNDIDAD[-1]
    
    def tamanio_por_magnitud(self, magnitud: float,
                              escala: float = 5.0,
                              minimo: float = 2.0) -> float:
        """
        Calcula el tamaño de marcador proporcional a la magnitud.
        
        Args:
            magnitud: Valor de magnitud
            escala: Factor de escala
            minimo: Tamaño mínimo
            
        Returns:
            Tamaño del marcador
        """
        return max(minimo, (magnitud ** 2) * escala)


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def crear_leyenda_profundidad(ax: plt.Axes,
                               rangos: Optional[List[float]] = None,
                               colores: Optional[List[str]] = None,
                               titulo: str = 'Profundidad (km)'):
    """
    Crea una leyenda de profundidad con colores.
    
    Args:
        ax: Axes de matplotlib
        rangos: Lista de rangos de profundidad
        colores: Lista de colores correspondientes
        titulo: Título de la leyenda
    """
    if rangos is None:
        rangos = PaletaColoresSismicidad.RANGOS_PROFUNDIDAD
    if colores is None:
        colores = PaletaColoresESD.COLORES_PROFUNDIDAD
    
    from matplotlib.patches import Patch
    
    handles = []
    for i in range(len(rangos) - 1):
        label = f'{rangos[i]}-{rangos[i+1]}'
        handles.append(Patch(color=colores[i], label=label))
    
    ax.legend(handles=handles, title=titulo, loc='best')


def crear_leyenda_magnitud(ax: plt.Axes,
                           magnitudes: List[float] = [2, 3, 4, 5, 6],
                           escala: float = 5.0,
                           titulo: str = 'Magnitud'):
    """
    Crea una leyenda de magnitud con tamaños de marcador.
    
    Args:
        ax: Axes de matplotlib
        magnitudes: Lista de magnitudes para la leyenda
        escala: Factor de escala para el tamaño
        titulo: Título de la leyenda
    """
    from matplotlib.lines import Line2D
    
    handles = []
    for m in magnitudes:
        size = (m ** 2) * escala
        handles.append(
            Line2D([0], [0], marker='o', color='w',
                   markerfacecolor='gray', markersize=np.sqrt(size),
                   label=f'M{m:.0f}')
        )
    
    ax.legend(handles=handles, title=titulo, loc='best')


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

def ejemplo_colormaps():
    """Ejemplo de uso de las paletas de colores."""
    print("=" * 70)
    print("SEISMEX - Ejemplo de Paletas de Colores")
    print("=" * 70)
    
    # Crear instancia
    paleta = PaletaColoresESD()
    
    # Mostrar niveles
    print(f"\nNiveles estándar: {paleta.niveles_estandar}")
    
    # Obtener colores
    print(f"\nColores hexadecimales:")
    for nivel, color in paleta.obtener_colores_para_niveles().items():
        print(f"  {nivel:6.1f} → {color}")
    
    # Color para un valor específico
    valor_test = -3.5
    color = paleta.obtener_hex_por_valor(valor_test)
    print(f"\nColor para ESD={valor_test}: {color}")
    
    # Mostrar todas las paletas
    fig = paleta.mostrar_paletas()
    
    print("\n✓ Ejemplo completado")
    
    return paleta


if __name__ == "__main__":
    paleta = ejemplo_colormaps()
    plt.show()
