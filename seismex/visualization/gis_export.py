#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SEISMEX - Módulo de Exportación GIS
================================================================================
Herramientas para exportar resultados ESD a formatos GIS:
- GeoTIFF (raster georreferenciado)
- GeoJSON (vectores)
- Shapefile (ESRI)
- GeoPackage (GPKG)
- KML/KMZ (Google Earth)
- NetCDF (datos científicos)

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

# Manejo de dependencias opcionales
try:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

try:
    import fiona
    from fiona.crs import from_epsg
    FIONA_AVAILABLE = True
except ImportError:
    FIONA_AVAILABLE = False

try:
    import geopandas as gpd
    from shapely.geometry import Point, LineString, Polygon, mapping
    from shapely.ops import unary_union
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

try:
    import xarray as xr
    XARRAY_AVAILABLE = True
except ImportError:
    XARRAY_AVAILABLE = False


class ExportadorGIS:
    """
    Exportador de resultados ESD a formatos GIS.
    
    Soporta múltiples formatos de salida para integración con
    software GIS (QGIS, ArcGIS) y plataformas web.
    
    Attributes:
        resultado: ResultadoESD con los datos a exportar
        crs: Sistema de referencia de coordenadas
        
    Example:
        >>> exportador = ExportadorGIS(resultado_esd)
        >>> exportador.exportar_geotiff('esd_30km.tif', profundidad_km=30)
        >>> exportador.exportar_geojson('contornos.geojson', profundidad_km=30)
    """
    
    # CRS predefinidos
    CRS_WGS84 = 'EPSG:4326'
    CRS_UTM13N = 'EPSG:32613'  # UTM zona 13N (México occidental)
    CRS_UTM14N = 'EPSG:32614'  # UTM zona 14N (México central)
    
    def __init__(self,
                 resultado_esd: Any,
                 catalogo: Optional[Any] = None,
                 crs: str = 'EPSG:4326'):
        """
        Inicializa el exportador.
        
        Args:
            resultado_esd: ResultadoESD con los datos
            catalogo: CatalogoSismico opcional
            crs: Sistema de referencia (default WGS84)
        """
        self.resultado = resultado_esd
        self.catalogo = catalogo
        self.crs = crs
        
        # Verificar dependencias
        self._verificar_dependencias()
    
    def _verificar_dependencias(self):
        """Verifica que las dependencias necesarias estén instaladas."""
        if not RASTERIO_AVAILABLE:
            warnings.warn("rasterio no disponible. GeoTIFF no funcionará. "
                         "Instale con: pip install rasterio")
        if not GEOPANDAS_AVAILABLE:
            warnings.warn("geopandas/shapely no disponible. Vectores limitados. "
                         "Instale con: pip install geopandas shapely")
    
    # =========================================================================
    # GEOTIFF
    # =========================================================================
    
    def exportar_geotiff(self,
                         ruta: str,
                         profundidad_km: float,
                         crs: Optional[str] = None,
                         resolucion_m: Optional[float] = None,
                         nodata: float = -9999.0,
                         compress: str = 'lzw',
                         metadatos: Optional[Dict] = None) -> str:
        """
        Exporta una sección horizontal a GeoTIFF.
        
        Args:
            ruta: Ruta del archivo de salida
            profundidad_km: Profundidad del corte
            crs: Sistema de referencia (usa el default si None)
            resolucion_m: Resolución en metros (auto si None)
            nodata: Valor para datos faltantes
            compress: Compresión ('lzw', 'deflate', 'none')
            metadatos: Metadatos adicionales
            
        Returns:
            Ruta del archivo generado
        """
        if not RASTERIO_AVAILABLE:
            raise ImportError("rasterio no disponible. Instale con: pip install rasterio")
        
        if crs is None:
            crs = self.crs
        
        # Obtener sección
        iz = np.argmin(np.abs(self.resultado.grid_z - profundidad_km))
        prof_real = self.resultado.grid_z[iz]
        
        # Datos (transponer para formato raster: filas=lat, cols=lon)
        datos = self.resultado.esd_log10[:, :, iz].T.astype(np.float32)
        
        # Reemplazar NaN con nodata
        datos = np.where(np.isfinite(datos), datos, nodata)
        
        # Calcular transformación
        lon_min, lon_max = self.resultado.grid_x.min(), self.resultado.grid_x.max()
        lat_min, lat_max = self.resultado.grid_y.min(), self.resultado.grid_y.max()
        
        transform = from_bounds(
            lon_min, lat_min, lon_max, lat_max,
            datos.shape[1], datos.shape[0]
        )
        
        # Metadatos del raster
        meta_default = {
            'driver': 'GTiff',
            'dtype': 'float32',
            'nodata': nodata,
            'width': datos.shape[1],
            'height': datos.shape[0],
            'count': 1,
            'crs': crs,
            'transform': transform,
            'compress': compress if compress != 'none' else None,
        }
        
        # Escribir GeoTIFF
        with rasterio.open(ruta, 'w', **meta_default) as dst:
            dst.write(datos, 1)
            
            # Añadir metadatos personalizados
            dst.update_tags(
                SEISMEX_VERSION='1.0.0',
                PROFUNDIDAD_KM=str(prof_real),
                FECHA_CREACION=datetime.now().isoformat(),
                DESCRIPCION=f'ESD log10 normalizado a {prof_real:.1f} km',
                **(metadatos or {})
            )
        
        print(f"✓ GeoTIFF exportado: {ruta}")
        print(f"  Profundidad: {prof_real:.1f} km")
        print(f"  Dimensiones: {datos.shape[1]} x {datos.shape[0]}")
        print(f"  CRS: {crs}")
        
        return ruta
    
    def exportar_geotiff_stack(self,
                               ruta: str,
                               profundidades: List[float],
                               crs: Optional[str] = None,
                               metadatos: Optional[Dict] = None) -> str:
        """
        Exporta múltiples profundidades como un stack de bandas.
        
        Args:
            ruta: Ruta del archivo de salida
            profundidades: Lista de profundidades en km
            crs: Sistema de referencia
            metadatos: Metadatos adicionales
            
        Returns:
            Ruta del archivo generado
        """
        if not RASTERIO_AVAILABLE:
            raise ImportError("rasterio no disponible")
        
        if crs is None:
            crs = self.crs
        
        # Preparar datos
        bandas = []
        profs_reales = []
        
        for prof in profundidades:
            iz = np.argmin(np.abs(self.resultado.grid_z - prof))
            prof_real = self.resultado.grid_z[iz]
            profs_reales.append(prof_real)
            
            datos = self.resultado.esd_log10[:, :, iz].T.astype(np.float32)
            datos = np.where(np.isfinite(datos), datos, -9999.0)
            bandas.append(datos)
        
        # Stack
        stack = np.stack(bandas, axis=0)
        
        # Transformación
        lon_min, lon_max = self.resultado.grid_x.min(), self.resultado.grid_x.max()
        lat_min, lat_max = self.resultado.grid_y.min(), self.resultado.grid_y.max()
        
        transform = from_bounds(
            lon_min, lat_min, lon_max, lat_max,
            stack.shape[2], stack.shape[1]
        )
        
        # Escribir
        with rasterio.open(
            ruta, 'w',
            driver='GTiff',
            dtype='float32',
            nodata=-9999.0,
            width=stack.shape[2],
            height=stack.shape[1],
            count=len(profundidades),
            crs=crs,
            transform=transform,
            compress='lzw'
        ) as dst:
            for i, (banda, prof) in enumerate(zip(stack, profs_reales), 1):
                dst.write(banda, i)
                dst.set_band_description(i, f'ESD {prof:.1f} km')
            
            dst.update_tags(
                SEISMEX_VERSION='1.0.0',
                PROFUNDIDADES=','.join([f'{p:.1f}' for p in profs_reales]),
                N_BANDAS=str(len(profundidades)),
                FECHA_CREACION=datetime.now().isoformat(),
                **(metadatos or {})
            )
        
        print(f"✓ GeoTIFF stack exportado: {ruta}")
        print(f"  Profundidades: {profs_reales}")
        print(f"  Bandas: {len(profundidades)}")
        
        return ruta
    
    # =========================================================================
    # GEOJSON
    # =========================================================================
    
    def exportar_geojson(self,
                         ruta: str,
                         profundidad_km: float,
                         niveles: Optional[List[float]] = None,
                         tipo: str = 'contornos',
                         propiedades_extra: Optional[Dict] = None) -> str:
        """
        Exporta a GeoJSON.
        
        Args:
            ruta: Ruta del archivo de salida
            profundidad_km: Profundidad del corte
            niveles: Niveles de contorno (auto si None)
            tipo: 'contornos', 'puntos', o 'grid'
            propiedades_extra: Propiedades adicionales
            
        Returns:
            Ruta del archivo generado
        """
        if tipo == 'contornos':
            return self._exportar_contornos_geojson(ruta, profundidad_km, niveles, propiedades_extra)
        elif tipo == 'puntos':
            return self._exportar_puntos_geojson(ruta, profundidad_km, propiedades_extra)
        elif tipo == 'grid':
            return self._exportar_grid_geojson(ruta, profundidad_km, propiedades_extra)
        else:
            raise ValueError(f"Tipo no válido: {tipo}. Use 'contornos', 'puntos', o 'grid'")
    
    def _exportar_contornos_geojson(self, ruta, profundidad_km, niveles, propiedades_extra):
        """Exporta contornos a GeoJSON."""
        import matplotlib.pyplot as plt
        
        if niveles is None:
            niveles = [-7, -4.5, -3, -2.5, -2, -1, -0.5, 0]
        
        # Obtener sección
        iz = np.argmin(np.abs(self.resultado.grid_z - profundidad_km))
        prof_real = self.resultado.grid_z[iz]
        
        X, Y = np.meshgrid(self.resultado.grid_x, self.resultado.grid_y, indexing='ij')
        Z = self.resultado.esd_log10[:, :, iz]
        
        # Generar contornos
        fig, ax = plt.subplots()
        cs = ax.contour(X, Y, Z, levels=niveles)
        plt.close(fig)
        
        # Convertir a features
        features = []
        
        for i, nivel in enumerate(cs.levels):
            if i < len(cs.collections):
                for path in cs.collections[i].get_paths():
                    if len(path.vertices) > 1:
                        coords = [[float(x), float(y)] for x, y in path.vertices]
                        
                        feature = {
                            'type': 'Feature',
                            'geometry': {
                                'type': 'LineString',
                                'coordinates': coords
                            },
                            'properties': {
                                'nivel_esd': float(nivel),
                                'profundidad_km': float(prof_real),
                                **(propiedades_extra or {})
                            }
                        }
                        features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'name': f'ESD_contornos_{prof_real:.0f}km',
            'crs': {
                'type': 'name',
                'properties': {'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'}
            },
            'features': features
        }
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        print(f"✓ GeoJSON contornos exportado: {ruta}")
        print(f"  Features: {len(features)}")
        
        return ruta
    
    def _exportar_puntos_geojson(self, ruta, profundidad_km, propiedades_extra):
        """Exporta puntos de grid a GeoJSON."""
        iz = np.argmin(np.abs(self.resultado.grid_z - profundidad_km))
        prof_real = self.resultado.grid_z[iz]
        
        features = []
        
        for i, lon in enumerate(self.resultado.grid_x):
            for j, lat in enumerate(self.resultado.grid_y):
                valor = self.resultado.esd_log10[i, j, iz]
                
                if np.isfinite(valor):
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [float(lon), float(lat)]
                        },
                        'properties': {
                            'esd_log10': float(valor),
                            'profundidad_km': float(prof_real),
                            'lon': float(lon),
                            'lat': float(lat),
                            **(propiedades_extra or {})
                        }
                    }
                    features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'name': f'ESD_puntos_{prof_real:.0f}km',
            'features': features
        }
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        print(f"✓ GeoJSON puntos exportado: {ruta}")
        print(f"  Features: {len(features)}")
        
        return ruta
    
    def _exportar_grid_geojson(self, ruta, profundidad_km, propiedades_extra):
        """Exporta celdas del grid como polígonos."""
        iz = np.argmin(np.abs(self.resultado.grid_z - profundidad_km))
        prof_real = self.resultado.grid_z[iz]
        
        # Calcular tamaño de celda
        dx = (self.resultado.grid_x[1] - self.resultado.grid_x[0]) / 2 if len(self.resultado.grid_x) > 1 else 0.1
        dy = (self.resultado.grid_y[1] - self.resultado.grid_y[0]) / 2 if len(self.resultado.grid_y) > 1 else 0.1
        
        features = []
        
        for i, lon in enumerate(self.resultado.grid_x):
            for j, lat in enumerate(self.resultado.grid_y):
                valor = self.resultado.esd_log10[i, j, iz]
                
                if np.isfinite(valor):
                    # Crear polígono de la celda
                    coords = [
                        [lon - dx, lat - dy],
                        [lon + dx, lat - dy],
                        [lon + dx, lat + dy],
                        [lon - dx, lat + dy],
                        [lon - dx, lat - dy]
                    ]
                    
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [coords]
                        },
                        'properties': {
                            'esd_log10': float(valor),
                            'profundidad_km': float(prof_real),
                            'lon_centro': float(lon),
                            'lat_centro': float(lat),
                            **(propiedades_extra or {})
                        }
                    }
                    features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'name': f'ESD_grid_{prof_real:.0f}km',
            'features': features
        }
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        print(f"✓ GeoJSON grid exportado: {ruta}")
        print(f"  Celdas: {len(features)}")
        
        return ruta
    
    # =========================================================================
    # SHAPEFILE
    # =========================================================================
    
    def exportar_shapefile(self,
                           ruta_base: str,
                           profundidad_km: float,
                           niveles: Optional[List[float]] = None,
                           tipo: str = 'contornos') -> str:
        """
        Exporta a Shapefile.
        
        Args:
            ruta_base: Ruta base (sin extensión)
            profundidad_km: Profundidad del corte
            niveles: Niveles de contorno
            tipo: 'contornos' o 'puntos'
            
        Returns:
            Ruta del archivo .shp generado
        """
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("geopandas no disponible. Instale con: pip install geopandas")
        
        # Primero exportar a GeoJSON temporal
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.geojson', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            self.exportar_geojson(tmp_path, profundidad_km, niveles, tipo)
            
            # Leer con geopandas y exportar a shapefile
            gdf = gpd.read_file(tmp_path)
            
            ruta_shp = f"{ruta_base}.shp"
            gdf.to_file(ruta_shp)
            
            print(f"✓ Shapefile exportado: {ruta_shp}")
            
            return ruta_shp
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    # =========================================================================
    # GEOPACKAGE
    # =========================================================================
    
    def exportar_catalogo_gpkg(self,
                               ruta: str,
                               catalogo: Optional[Any] = None,
                               incluir_esd: bool = True,
                               capas_adicionales: Optional[Dict[str, Any]] = None) -> str:
        """
        Exporta catálogo sísmico a GeoPackage.
        
        Args:
            ruta: Ruta del archivo .gpkg
            catalogo: CatalogoSismico (usa el del exportador si None)
            incluir_esd: Agregar valor ESD a cada evento
            capas_adicionales: Dict de capas adicionales {nombre: GeoDataFrame}
            
        Returns:
            Ruta del archivo generado
        """
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("geopandas no disponible")
        
        if catalogo is None:
            catalogo = self.catalogo
        
        if catalogo is None:
            raise ValueError("No hay catálogo disponible")
        
        datos = catalogo.datos.copy()
        
        # Crear geometrías
        geometrias = [Point(lon, lat) for lon, lat in zip(datos['longitud'], datos['latitud'])]
        gdf = gpd.GeoDataFrame(datos, geometry=geometrias, crs=self.crs)
        
        # Agregar valores ESD si se solicita
        if incluir_esd:
            esd_valores = []
            for _, row in datos.iterrows():
                # Encontrar índice más cercano
                ix = np.argmin(np.abs(self.resultado.grid_x - row['longitud']))
                iy = np.argmin(np.abs(self.resultado.grid_y - row['latitud']))
                iz = np.argmin(np.abs(self.resultado.grid_z - abs(row['profundidad_km'])))
                
                if (0 <= ix < len(self.resultado.grid_x) and
                    0 <= iy < len(self.resultado.grid_y) and
                    0 <= iz < len(self.resultado.grid_z)):
                    esd_valores.append(self.resultado.esd_log10[ix, iy, iz])
                else:
                    esd_valores.append(np.nan)
            
            gdf['esd_log10'] = esd_valores
        
        # Guardar capa principal
        gdf.to_file(ruta, layer='eventos', driver='GPKG')
        
        # Agregar capas adicionales
        if capas_adicionales:
            for nombre, gdf_capa in capas_adicionales.items():
                gdf_capa.to_file(ruta, layer=nombre, driver='GPKG')
        
        print(f"✓ GeoPackage exportado: {ruta}")
        print(f"  Eventos: {len(gdf)}")
        
        return ruta
    
    # =========================================================================
    # KML/KMZ
    # =========================================================================
    
    def exportar_kml(self,
                     ruta: str,
                     profundidad_km: float,
                     niveles: Optional[List[float]] = None,
                     nombre_doc: str = 'SEISMEX ESD') -> str:
        """
        Exporta a KML para Google Earth.
        
        Args:
            ruta: Ruta del archivo .kml
            profundidad_km: Profundidad del corte
            niveles: Niveles de contorno
            nombre_doc: Nombre del documento KML
            
        Returns:
            Ruta del archivo generado
        """
        if niveles is None:
            niveles = [-7, -4.5, -3, -2, -1, 0]
        
        # Colores para cada nivel (AABBGGRR en KML)
        colores = [
            'FF4B0082',  # Índigo
            'FF0000CD',  # Azul
            'FF00BFFF',  # Azul cielo
            'FF00FF7F',  # Verde
            'FFFFB6C1',  # Rosa
            'FF8B0000',  # Rojo oscuro
        ]
        
        iz = np.argmin(np.abs(self.resultado.grid_z - profundidad_km))
        prof_real = self.resultado.grid_z[iz]
        
        # Generar contornos
        import matplotlib.pyplot as plt
        
        X, Y = np.meshgrid(self.resultado.grid_x, self.resultado.grid_y, indexing='ij')
        Z = self.resultado.esd_log10[:, :, iz]
        
        fig, ax = plt.subplots()
        cs = ax.contour(X, Y, Z, levels=niveles)
        plt.close(fig)
        
        # Construir KML
        kml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<kml xmlns="http://www.opengis.net/kml/2.2">',
            '<Document>',
            f'  <name>{nombre_doc}</name>',
            f'  <description>ESD a {prof_real:.1f} km de profundidad</description>',
        ]
        
        # Estilos
        for i, (nivel, color) in enumerate(zip(niveles, colores)):
            kml_lines.extend([
                f'  <Style id="nivel{i}">',
                '    <LineStyle>',
                f'      <color>{color}</color>',
                '      <width>2</width>',
                '    </LineStyle>',
                '  </Style>',
            ])
        
        # Placemarks
        for i, nivel in enumerate(cs.levels):
            if i < len(cs.collections):
                for j, path in enumerate(cs.collections[i].get_paths()):
                    if len(path.vertices) > 1:
                        coords_str = ' '.join([f'{x},{y},0' for x, y in path.vertices])
                        
                        kml_lines.extend([
                            '  <Placemark>',
                            f'    <name>ESD = {nivel:.1f}</name>',
                            f'    <description>Contorno ESD log10 = {nivel:.1f}</description>',
                            f'    <styleUrl>#nivel{i}</styleUrl>',
                            '    <LineString>',
                            '      <coordinates>',
                            f'        {coords_str}',
                            '      </coordinates>',
                            '    </LineString>',
                            '  </Placemark>',
                        ])
        
        kml_lines.extend([
            '</Document>',
            '</kml>'
        ])
        
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write('\n'.join(kml_lines))
        
        print(f"✓ KML exportado: {ruta}")
        
        return ruta
    
    # =========================================================================
    # NETCDF
    # =========================================================================
    
    def exportar_netcdf(self,
                        ruta: str,
                        metadatos: Optional[Dict] = None) -> str:
        """
        Exporta el volumen ESD completo a NetCDF.
        
        Args:
            ruta: Ruta del archivo .nc
            metadatos: Metadatos adicionales
            
        Returns:
            Ruta del archivo generado
        """
        if not XARRAY_AVAILABLE:
            raise ImportError("xarray no disponible. Instale con: pip install xarray netcdf4")
        
        # Crear Dataset
        ds = xr.Dataset(
            {
                'esd_log10': (['lon', 'lat', 'depth'], self.resultado.esd_log10),
                'esd_3d': (['lon', 'lat', 'depth'], self.resultado.esd_3d) if hasattr(self.resultado, 'esd_3d') else None,
            },
            coords={
                'lon': self.resultado.grid_x,
                'lat': self.resultado.grid_y,
                'depth': self.resultado.grid_z,
            },
            attrs={
                'title': 'SEISMEX Energy Space Density',
                'institution': 'SEISMEX Project',
                'source': 'ESD Analysis',
                'history': f'Created {datetime.now().isoformat()}',
                'Conventions': 'CF-1.6',
                'crs': self.crs,
                **(metadatos or {})
            }
        )
        
        # Añadir atributos a variables
        ds['esd_log10'].attrs = {
            'long_name': 'Log10 Normalized Energy Space Density',
            'units': 'log10(ESD/ESD_max)',
            'valid_min': -12.0,
            'valid_max': 1.0,
        }
        
        ds['lon'].attrs = {'long_name': 'Longitude', 'units': 'degrees_east'}
        ds['lat'].attrs = {'long_name': 'Latitude', 'units': 'degrees_north'}
        ds['depth'].attrs = {'long_name': 'Depth', 'units': 'km', 'positive': 'down'}
        
        # Guardar
        ds.to_netcdf(ruta)
        
        print(f"✓ NetCDF exportado: {ruta}")
        print(f"  Dimensiones: {dict(ds.dims)}")
        
        return ruta
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def obtener_extent(self) -> Tuple[float, float, float, float]:
        """
        Obtiene la extensión geográfica del resultado.
        
        Returns:
            Tupla (lon_min, lon_max, lat_min, lat_max)
        """
        return (
            self.resultado.grid_x.min(),
            self.resultado.grid_x.max(),
            self.resultado.grid_y.min(),
            self.resultado.grid_y.max()
        )
    
    def obtener_resolucion(self) -> Tuple[float, float]:
        """
        Obtiene la resolución del grid.
        
        Returns:
            Tupla (res_lon, res_lat) en grados
        """
        dx = (self.resultado.grid_x[1] - self.resultado.grid_x[0]) if len(self.resultado.grid_x) > 1 else 0.1
        dy = (self.resultado.grid_y[1] - self.resultado.grid_y[0]) if len(self.resultado.grid_y) > 1 else 0.1
        return (abs(dx), abs(dy))
    
    def listar_profundidades(self) -> List[float]:
        """
        Lista las profundidades disponibles.
        
        Returns:
            Lista de profundidades en km
        """
        return self.resultado.grid_z.tolist()


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

def ejemplo_exportacion():
    """Ejemplo de uso del módulo de exportación."""
    print("=" * 70)
    print("SEISMEX - Ejemplo de Exportación GIS")
    print("=" * 70)
    
    # Simular resultado ESD
    np.random.seed(42)
    
    grid_x = np.linspace(-104.5, -103.5, 30)
    grid_y = np.linspace(18.5, 19.5, 30)
    grid_z = np.linspace(0, 100, 15)
    
    # Crear ESD simulado
    X, Y, Z = np.meshgrid(grid_x, grid_y, grid_z, indexing='ij')
    centro_x, centro_y, centro_z = -104.0, 19.0, 30
    
    distancia = np.sqrt(
        ((X - centro_x) * 111) ** 2 +
        ((Y - centro_y) * 111) ** 2 +
        (Z - centro_z) ** 2
    )
    
    esd_log10 = -12 + 12 * np.exp(-distancia ** 2 / (2 * 40 ** 2))
    esd_log10 += np.random.normal(0, 0.3, esd_log10.shape)
    
    # Crear objeto simulado
    class ResultadoSimulado:
        def __init__(self):
            self.grid_x = grid_x
            self.grid_y = grid_y
            self.grid_z = grid_z
            self.esd_log10 = esd_log10
    
    resultado = ResultadoSimulado()
    
    # Crear exportador
    exportador = ExportadorGIS(resultado)
    
    print(f"\nExtent: {exportador.obtener_extent()}")
    print(f"Resolución: {exportador.obtener_resolucion()}")
    print(f"Profundidades: {exportador.listar_profundidades()}")
    
    # Exportar a diferentes formatos
    print("\n--- Exportando a GeoJSON ---")
    exportador.exportar_geojson('/tmp/esd_contornos.geojson', profundidad_km=30)
    
    if RASTERIO_AVAILABLE:
        print("\n--- Exportando a GeoTIFF ---")
        exportador.exportar_geotiff('/tmp/esd_30km.tif', profundidad_km=30)
    
    print("\n✓ Exportación completada")
    
    return exportador


if __name__ == "__main__":
    exportador = ejemplo_exportacion()
