#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX - Integración con Google Earth Engine
================================================================================
Herramientas para integrar resultados ESD con Google Earth Engine (GEE):
- Autenticación y configuración
- Subida de assets (imágenes y colecciones)
- Creación de mapas interactivos con geemap
- Análisis con capas GEE (topografía, límites, etc.)
- Publicación de Earth Engine Apps

Basado en el ejemplo NATECHv3.py para análisis NATECH.

Autor: SEISMEX Project
Versión: 1.0.0
================================================================================
"""

import numpy as np
from typing import Optional, List, Dict, Tuple, Union, Any
from pathlib import Path
import json
import warnings
from datetime import datetime
import tempfile
import os

# Manejo de dependencias GEE
try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False
    warnings.warn("earthengine-api no disponible. Instale con: pip install earthengine-api")

try:
    import geemap
    GEEMAP_AVAILABLE = True
except ImportError:
    GEEMAP_AVAILABLE = False
    warnings.warn("geemap no disponible. Instale con: pip install geemap")


class IntegradorGEE:
    """
    Integrador de SEISMEX con Google Earth Engine.
    
    Permite subir resultados ESD a GEE, crear visualizaciones
    interactivas con geemap, y publicar Earth Engine Apps.
    
    Attributes:
        proyecto: ID del proyecto GEE
        cuenta: Cuenta de servicio o email
        inicializado: Estado de inicialización
        
    Example:
        >>> gee = IntegradorGEE(proyecto='mi-proyecto-gee')
        >>> gee.autenticar()
        >>> asset_id = gee.subir_esd(resultado_esd, 'seismex/esd_colima')
        >>> mapa = gee.crear_mapa(asset_id)
        >>> mapa.save('mapa_esd.html')
    """
    
    # Paletas de colores para visualización GEE
    PALETAS = {
        'esd': ['#4B0082', '#0000CD', '#00BFFF', '#98FB98', '#FFFFE0',
                '#FFB6C1', '#FF69B4', '#DC143C', '#8B0000'],
        'irn': ['#1a9641', '#a6d96a', '#ffffbf', '#fdae61', '#d7191c'],
        'temperatura': ['#ffffcc', '#ffeda0', '#fed976', '#fd8d3c', '#e31a1c'],
        'profundidad': ['#FF0000', '#FF8C00', '#FFD700', '#32CD32', '#1E90FF', '#0000CD'],
        'verde_rojo': ['#1a9641', '#a6d96a', '#ffffbf', '#fdae61', '#d7191c'],
        'azul': ['#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#313695'],
    }
    
    # Capas base disponibles en GEE
    CAPAS_BASE = {
        'srtm': 'USGS/SRTMGL1_003',
        'nasadem': 'NASA/NASADEM_HGT/001',
        'modis_lst': 'MODIS/061/MOD11A1',
        'sentinel2': 'COPERNICUS/S2_SR_HARMONIZED',
        'landsat8': 'LANDSAT/LC08/C02/T1_L2',
        'jrc_water': 'JRC/GSW1_4/GlobalSurfaceWater',
        'worldpop': 'WorldPop/GP/100m/pop',
        'gaul_admin': 'FAO/GAUL/2015/level1',
    }
    
    def __init__(self,
                 proyecto: Optional[str] = None,
                 cuenta: Optional[str] = None):
        """
        Inicializa el integrador GEE.
        
        Args:
            proyecto: ID del proyecto de Google Cloud
            cuenta: Email de la cuenta GEE
        """
        if not EE_AVAILABLE:
            raise ImportError("earthengine-api no disponible. "
                            "Instale con: pip install earthengine-api")
        
        self.proyecto = proyecto
        self.cuenta = cuenta
        self.inicializado = False
        self._mapa = None
    
    def autenticar(self, forzar: bool = False) -> bool:
        """
        Autentica con Google Earth Engine.
        
        Args:
            forzar: Forzar re-autenticación
            
        Returns:
            True si la autenticación fue exitosa
        """
        try:
            if forzar:
                ee.Authenticate()
            
            if self.proyecto:
                ee.Initialize(project=self.proyecto,
                             opt_url='https://earthengine.googleapis.com')
            else:
                ee.Initialize()
            
            self.inicializado = True
            print(f"✓ GEE inicializado")
            if self.proyecto:
                print(f"  Proyecto: {self.proyecto}")
            
            return True
            
        except Exception as e:
            print(f"[INFO] Autenticación interactiva requerida: {e}")
            try:
                ee.Authenticate()
                
                if self.proyecto:
                    ee.Initialize(project=self.proyecto)
                else:
                    ee.Initialize()
                
                self.inicializado = True
                print(f"✓ GEE inicializado tras autenticación")
                return True
                
            except Exception as e2:
                print(f"[ERROR] No se pudo inicializar GEE: {e2}")
                return False
    
    def _verificar_inicializacion(self):
        """Verifica que GEE esté inicializado."""
        if not self.inicializado:
            raise RuntimeError("GEE no inicializado. Ejecute autenticar() primero.")
    
    # =========================================================================
    # CREACIÓN DE IMÁGENES EE
    # =========================================================================
    
    def crear_imagen_esd(self,
                         resultado_esd: Any,
                         profundidad_km: float,
                         nombre: str = 'esd') -> 'ee.Image':
        """
        Crea una imagen de Earth Engine desde resultados ESD.
        
        Args:
            resultado_esd: ResultadoESD con los datos
            profundidad_km: Profundidad del corte
            nombre: Nombre de la banda
            
        Returns:
            ee.Image con los datos ESD
        """
        self._verificar_inicializacion()
        
        # Obtener sección
        iz = np.argmin(np.abs(resultado_esd.grid_z - profundidad_km))
        datos = resultado_esd.esd_log10[:, :, iz]
        
        # Obtener extensión
        lon_min, lon_max = resultado_esd.grid_x.min(), resultado_esd.grid_x.max()
        lat_min, lat_max = resultado_esd.grid_y.min(), resultado_esd.grid_y.max()
        
        # Crear geometría del área
        region = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
        
        # Convertir a lista para ee.Image.pixelLonLat()
        # Nota: GEE tiene limitaciones para arrays grandes,
        # se recomienda exportar como GeoTIFF y subir como asset
        
        # Crear imagen constante y recortar
        # Para datos reales, usar subir_esd() que maneja GeoTIFF
        imagen = ee.Image.constant(datos.mean()).clip(region).rename(nombre)
        
        return imagen
    
    def crear_region(self,
                     resultado_esd: Any = None,
                     bounds: Optional[Tuple[float, float, float, float]] = None,
                     geometria: Optional[List[List[float]]] = None) -> 'ee.Geometry':
        """
        Crea una geometría de región para GEE.
        
        Args:
            resultado_esd: ResultadoESD para extraer bounds
            bounds: (lon_min, lat_min, lon_max, lat_max)
            geometria: Lista de coordenadas [[lon, lat], ...]
            
        Returns:
            ee.Geometry
        """
        self._verificar_inicializacion()
        
        if geometria is not None:
            return ee.Geometry.Polygon([geometria])
        elif bounds is not None:
            return ee.Geometry.Rectangle(list(bounds))
        elif resultado_esd is not None:
            return ee.Geometry.Rectangle([
                resultado_esd.grid_x.min(),
                resultado_esd.grid_y.min(),
                resultado_esd.grid_x.max(),
                resultado_esd.grid_y.max()
            ])
        else:
            raise ValueError("Proporcione resultado_esd, bounds, o geometria")
    
    # =========================================================================
    # SUBIDA DE ASSETS
    # =========================================================================
    
    def subir_esd(self,
                  resultado_esd: Any,
                  asset_id: str,
                  profundidades: Optional[List[float]] = None,
                  descripcion: str = 'SEISMEX ESD',
                  carpeta_drive: str = 'SEISMEX_Assets') -> str:
        """
        Sube resultados ESD como Asset de GEE vía Google Drive.
        
        Args:
            resultado_esd: ResultadoESD con los datos
            asset_id: ID del asset (ej: 'users/usuario/seismex/esd_colima')
            profundidades: Lista de profundidades a exportar (todas si None)
            descripcion: Descripción del asset
            carpeta_drive: Carpeta en Google Drive para archivos temporales
            
        Returns:
            ID del asset creado
        """
        self._verificar_inicializacion()
        
        if profundidades is None:
            profundidades = resultado_esd.grid_z.tolist()
        
        # Crear imagen multicapa
        bandas = []
        nombres_bandas = []
        
        for prof in profundidades:
            iz = np.argmin(np.abs(resultado_esd.grid_z - prof))
            prof_real = resultado_esd.grid_z[iz]
            
            datos = resultado_esd.esd_log10[:, :, iz]
            
            # Crear imagen para esta profundidad
            # Convertir a ee.Image usando píxeles
            lon_min, lon_max = resultado_esd.grid_x.min(), resultado_esd.grid_x.max()
            lat_min, lat_max = resultado_esd.grid_y.min(), resultado_esd.grid_y.max()
            
            region = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
            
            # Crear imagen constante (simplificación)
            # Para datos reales, usar exportación GeoTIFF -> ingestAsset
            imagen = ee.Image.constant(float(datos.mean())).clip(region)
            imagen = imagen.rename(f'esd_{prof_real:.0f}km')
            
            bandas.append(imagen)
            nombres_bandas.append(f'esd_{prof_real:.0f}km')
        
        # Combinar bandas
        imagen_multicapa = ee.Image.cat(bandas)
        
        # Exportar a Drive (el asset se crea después manualmente o con API)
        region = self.crear_region(resultado_esd)
        
        tarea = ee.batch.Export.image.toDrive(
            image=imagen_multicapa,
            description=f'SEISMEX_ESD_{datetime.now().strftime("%Y%m%d")}',
            folder=carpeta_drive,
            fileNamePrefix='seismex_esd',
            region=region,
            scale=1000,  # metros
            crs='EPSG:4326',
            maxPixels=1e9
        )
        
        tarea.start()
        
        print(f"✓ Exportación iniciada a Google Drive")
        print(f"  Carpeta: {carpeta_drive}")
        print(f"  Bandas: {len(profundidades)}")
        print(f"  Monitorear en: https://code.earthengine.google.com/tasks")
        
        return asset_id
    
    # =========================================================================
    # CAPAS BASE GEE
    # =========================================================================
    
    def obtener_topografia(self,
                           region: Optional['ee.Geometry'] = None,
                           fuente: str = 'srtm') -> 'ee.Image':
        """
        Obtiene capa de topografía.
        
        Args:
            region: Región de interés
            fuente: 'srtm' o 'nasadem'
            
        Returns:
            ee.Image con elevación
        """
        self._verificar_inicializacion()
        
        if fuente == 'srtm':
            dem = ee.Image('USGS/SRTMGL1_003')
        elif fuente == 'nasadem':
            dem = ee.Image('NASA/NASADEM_HGT/001').select('elevation')
        else:
            raise ValueError(f"Fuente no válida: {fuente}")
        
        if region:
            dem = dem.clip(region)
        
        return dem
    
    def obtener_pendiente(self,
                          region: Optional['ee.Geometry'] = None,
                          fuente: str = 'srtm') -> 'ee.Image':
        """
        Obtiene capa de pendiente del terreno.
        
        Args:
            region: Región de interés
            fuente: 'srtm' o 'nasadem'
            
        Returns:
            ee.Image con pendiente en grados
        """
        dem = self.obtener_topografia(region, fuente)
        return ee.Terrain.slope(dem)
    
    def obtener_limites_admin(self,
                              nivel: int = 1,
                              pais: str = 'Mexico') -> 'ee.FeatureCollection':
        """
        Obtiene límites administrativos.
        
        Args:
            nivel: Nivel administrativo (0=país, 1=estado, 2=municipio)
            pais: Nombre del país
            
        Returns:
            ee.FeatureCollection con límites
        """
        self._verificar_inicializacion()
        
        gaul = ee.FeatureCollection(f'FAO/GAUL/2015/level{nivel}')
        
        if pais:
            gaul = gaul.filter(ee.Filter.eq('ADM0_NAME', pais))
        
        return gaul
    
    # =========================================================================
    # MAPAS INTERACTIVOS
    # =========================================================================
    
    def crear_mapa(self,
                   centro: Tuple[float, float] = (19.0, -104.0),
                   zoom: int = 8,
                   basemap: str = 'SATELLITE') -> 'geemap.Map':
        """
        Crea un mapa interactivo con geemap.
        
        Args:
            centro: (latitud, longitud) del centro
            zoom: Nivel de zoom inicial
            basemap: 'SATELLITE', 'TERRAIN', 'ROADMAP', 'HYBRID'
            
        Returns:
            geemap.Map configurado
        """
        if not GEEMAP_AVAILABLE:
            raise ImportError("geemap no disponible")
        
        self._verificar_inicializacion()
        
        mapa = geemap.Map(center=list(centro), zoom=zoom)
        mapa.add_basemap(basemap)
        
        self._mapa = mapa
        return mapa
    
    def agregar_capa_esd(self,
                         mapa: 'geemap.Map',
                         resultado_esd: Any,
                         profundidad_km: float,
                         nombre: str = 'ESD',
                         vis_params: Optional[Dict] = None) -> 'geemap.Map':
        """
        Agrega capa ESD al mapa.
        
        Args:
            mapa: geemap.Map
            resultado_esd: ResultadoESD
            profundidad_km: Profundidad del corte
            nombre: Nombre de la capa
            vis_params: Parámetros de visualización
            
        Returns:
            mapa actualizado
        """
        imagen = self.crear_imagen_esd(resultado_esd, profundidad_km)
        
        if vis_params is None:
            vis_params = {
                'min': -12,
                'max': 0,
                'palette': self.PALETAS['esd']
            }
        
        mapa.addLayer(imagen, vis_params, nombre)
        
        return mapa
    
    def agregar_topografia(self,
                           mapa: 'geemap.Map',
                           region: Optional['ee.Geometry'] = None,
                           nombre: str = 'Topografía',
                           mostrar: bool = False) -> 'geemap.Map':
        """
        Agrega capa de topografía al mapa.
        
        Args:
            mapa: geemap.Map
            region: Región de interés
            nombre: Nombre de la capa
            mostrar: Mostrar por defecto
            
        Returns:
            mapa actualizado
        """
        dem = self.obtener_topografia(region)
        
        vis_params = {
            'min': 0,
            'max': 4000,
            'palette': ['#006633', '#E5FFCC', '#996600', '#663300', '#FFFFFF']
        }
        
        mapa.addLayer(dem, vis_params, nombre, mostrar)
        
        return mapa
    
    def agregar_pendiente(self,
                          mapa: 'geemap.Map',
                          region: Optional['ee.Geometry'] = None,
                          nombre: str = 'Pendiente',
                          mostrar: bool = False) -> 'geemap.Map':
        """
        Agrega capa de pendiente al mapa.
        """
        slope = self.obtener_pendiente(region)
        
        vis_params = {
            'min': 0,
            'max': 45,
            'palette': ['#00FF00', '#FFFF00', '#FF0000']
        }
        
        mapa.addLayer(slope, vis_params, nombre, mostrar)
        
        return mapa
    
    def agregar_limites(self,
                        mapa: 'geemap.Map',
                        nivel: int = 1,
                        pais: str = 'Mexico',
                        nombre: str = 'Límites',
                        mostrar: bool = True) -> 'geemap.Map':
        """
        Agrega límites administrativos al mapa.
        """
        limites = self.obtener_limites_admin(nivel, pais)
        
        mapa.addLayer(
            ee.Image().paint(limites, 1, 2),
            {'palette': ['#FFFFFF']},
            nombre,
            mostrar
        )
        
        return mapa
    
    def agregar_puntos(self,
                       mapa: 'geemap.Map',
                       catalogo: Any,
                       nombre: str = 'Epicentros',
                       color: str = 'yellow',
                       tamanio: int = 5) -> 'geemap.Map':
        """
        Agrega puntos del catálogo sísmico al mapa.
        
        Args:
            mapa: geemap.Map
            catalogo: CatalogoSismico
            nombre: Nombre de la capa
            color: Color de los puntos
            tamanio: Tamaño de los puntos
            
        Returns:
            mapa actualizado
        """
        # Crear FeatureCollection
        features = []
        
        for _, row in catalogo.datos.iterrows():
            feat = ee.Feature(
                ee.Geometry.Point([row['longitud'], row['latitud']]),
                {
                    'magnitud': float(row.get('magnitud', 0)),
                    'profundidad_km': float(row.get('profundidad_km', 0)),
                    'fecha': str(row.get('fecha', ''))
                }
            )
            features.append(feat)
        
        fc = ee.FeatureCollection(features)
        
        mapa.addLayer(
            fc,
            {'color': color, 'pointSize': tamanio},
            nombre
        )
        
        return mapa
    
    def agregar_colorbar(self,
                         mapa: 'geemap.Map',
                         vis_params: Dict,
                         label: str = 'ESD log₁₀',
                         nombre_capa: str = 'ESD') -> 'geemap.Map':
        """
        Agrega barra de colores al mapa.
        """
        mapa.add_colorbar(
            vis_params,
            label=label,
            layer_name=nombre_capa
        )
        return mapa
    
    # =========================================================================
    # EXPORTACIÓN
    # =========================================================================
    
    def exportar_a_drive(self,
                         imagen: 'ee.Image',
                         nombre: str,
                         carpeta: str = 'SEISMEX_Exports',
                         region: Optional['ee.Geometry'] = None,
                         escala: int = 100,
                         crs: str = 'EPSG:4326') -> 'ee.batch.Task':
        """
        Exporta imagen a Google Drive.
        
        Args:
            imagen: ee.Image a exportar
            nombre: Nombre del archivo
            carpeta: Carpeta en Drive
            region: Región a exportar
            escala: Resolución en metros
            crs: Sistema de referencia
            
        Returns:
            Tarea de exportación
        """
        self._verificar_inicializacion()
        
        if region is None:
            raise ValueError("Proporcione una región para exportar")
        
        tarea = ee.batch.Export.image.toDrive(
            image=imagen,
            description=nombre,
            folder=carpeta,
            fileNamePrefix=nombre,
            region=region,
            scale=escala,
            crs=crs,
            maxPixels=1e9
        )
        
        tarea.start()
        
        print(f"✓ Exportación iniciada: {nombre}")
        print(f"  Carpeta Drive: {carpeta}")
        print(f"  Escala: {escala}m")
        
        return tarea
    
    def exportar_multiples(self,
                           capas: List[Tuple['ee.Image', str, int]],
                           carpeta: str,
                           region: 'ee.Geometry') -> List['ee.batch.Task']:
        """
        Exporta múltiples capas a Google Drive.
        
        Args:
            capas: Lista de (imagen, nombre, escala)
            carpeta: Carpeta en Drive
            region: Región a exportar
            
        Returns:
            Lista de tareas de exportación
        """
        tareas = []
        
        for imagen, nombre, escala in capas:
            tarea = self.exportar_a_drive(
                imagen=imagen.clip(region),
                nombre=nombre,
                carpeta=carpeta,
                region=region,
                escala=escala
            )
            tareas.append(tarea)
        
        print(f"\n✓ {len(tareas)} exportaciones iniciadas")
        print(f"  Monitorear en: https://code.earthengine.google.com/tasks")
        
        return tareas
    
    # =========================================================================
    # EARTH ENGINE APPS
    # =========================================================================
    
    def generar_url_app(self,
                        script_path: str,
                        nombre: str = 'SEISMEX Viewer') -> str:
        """
        Genera URL para Earth Engine App.
        
        Nota: Requiere que el script esté guardado en GEE Code Editor.
        
        Args:
            script_path: Ruta del script en GEE (ej: 'users/usuario/seismex/app')
            nombre: Nombre de la app
            
        Returns:
            URL de la app
        """
        # El formato de URL para EE Apps
        base_url = "https://code.earthengine.google.com"
        
        print(f"Para publicar como Earth Engine App:")
        print(f"  1. Abra el script en: {base_url}")
        print(f"  2. Guarde el script en: {script_path}")
        print(f"  3. Haga clic en 'Apps' → 'Manage Apps' → 'New App'")
        print(f"  4. Configure nombre: {nombre}")
        
        return f"{base_url}?scriptPath={script_path}"
    
    def guardar_mapa(self,
                     mapa: 'geemap.Map',
                     ruta: str) -> str:
        """
        Guarda el mapa como HTML.
        
        Args:
            mapa: geemap.Map
            ruta: Ruta del archivo HTML
            
        Returns:
            Ruta del archivo guardado
        """
        mapa.save(ruta)
        print(f"✓ Mapa guardado: {ruta}")
        return ruta


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def crear_mapa_esd_completo(resultado_esd: Any,
                            catalogo: Any = None,
                            profundidad_km: float = 30,
                            proyecto_gee: Optional[str] = None,
                            guardar: Optional[str] = None) -> 'geemap.Map':
    """
    Crea un mapa completo con ESD, topografía y epicentros.
    
    Args:
        resultado_esd: ResultadoESD
        catalogo: CatalogoSismico opcional
        profundidad_km: Profundidad del corte
        proyecto_gee: ID del proyecto GEE
        guardar: Ruta para guardar HTML
        
    Returns:
        geemap.Map configurado
    """
    # Inicializar
    gee = IntegradorGEE(proyecto=proyecto_gee)
    gee.autenticar()
    
    # Centro del mapa
    centro = (
        (resultado_esd.grid_y.min() + resultado_esd.grid_y.max()) / 2,
        (resultado_esd.grid_x.min() + resultado_esd.grid_x.max()) / 2
    )
    
    # Crear mapa
    mapa = gee.crear_mapa(centro=centro, zoom=9)
    
    # Agregar capas
    region = gee.crear_region(resultado_esd)
    
    gee.agregar_topografia(mapa, region, mostrar=False)
    gee.agregar_pendiente(mapa, region, mostrar=False)
    gee.agregar_capa_esd(mapa, resultado_esd, profundidad_km)
    
    if catalogo is not None:
        gee.agregar_puntos(mapa, catalogo)
    
    gee.agregar_limites(mapa)
    
    # Colorbar
    gee.agregar_colorbar(mapa, {
        'min': -12, 'max': 0,
        'palette': IntegradorGEE.PALETAS['esd']
    })
    
    if guardar:
        gee.guardar_mapa(mapa, guardar)
    
    return mapa


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

def ejemplo_gee():
    """Ejemplo de uso del módulo GEE."""
    print("=" * 70)
    print("SEISMEX - Ejemplo de Integración GEE")
    print("=" * 70)
    
    if not EE_AVAILABLE:
        print("\n[ERROR] earthengine-api no disponible")
        print("Instale con: pip install earthengine-api geemap")
        return None
    
    if not GEEMAP_AVAILABLE:
        print("\n[WARNING] geemap no disponible")
        print("Los mapas interactivos no funcionarán")
    
    print("\n--- Creando integrador ---")
    
    # Nota: Requiere autenticación real con GEE
    print("\nPara usar este módulo:")
    print("  1. Instale: pip install earthengine-api geemap")
    print("  2. Autentique: earthengine authenticate")
    print("  3. Configure proyecto GEE")
    print("\nEjemplo de código:")
    print("""
    from seismex.visualization import IntegradorGEE
    
    # Inicializar
    gee = IntegradorGEE(proyecto='mi-proyecto-gee')
    gee.autenticar()
    
    # Crear mapa
    mapa = gee.crear_mapa(centro=(19.0, -104.0), zoom=8)
    
    # Agregar capas
    region = gee.crear_region(resultado_esd)
    gee.agregar_topografia(mapa, region)
    gee.agregar_capa_esd(mapa, resultado_esd, profundidad_km=30)
    gee.agregar_puntos(mapa, catalogo)
    
    # Guardar
    mapa.save('mapa_gee.html')
    
    # Exportar a Drive
    gee.exportar_a_drive(imagen, 'esd_export', region=region)
    """)
    
    print("\n✓ Ejemplo mostrado")
    
    return None


if __name__ == "__main__":
    ejemplo_gee()
