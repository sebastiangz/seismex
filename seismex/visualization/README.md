# 🎨 seismex.visualization

Módulo de visualización de SEISMEX. Proporciona herramientas para crear gráficos de alta calidad, mapas interactivos y exportación a formatos GIS.

---

## 📋 Contenido

- [Componentes](#componentes)
- [VisualizadorESD](#visualizadoresd)
- [Paleta de Colores](#paleta-de-colores)
- [Mapas Interactivos](#mapas-interactivos)
- [Exportación GIS](#exportación-gis)
- [Google Earth Engine](#google-earth-engine)
- [Estilos](#estilos)
- [Personalización](#personalización)

---

## Componentes

| Clase | Archivo | Descripción | Estado |
|-------|---------|-------------|--------|
| `VisualizadorESD` | `plotter.py` | Visualización de resultados ESD | ✅ Completo |
| `PaletaColoresESD` | `colormaps.py` | Paleta de colores ESD | ✅ Completo |
| `PaletaColoresSismicidad` | `colormaps.py` | Colores para sismicidad | ✅ Completo |
| `MapaInteractivo` | `interactive.py` | Mapas con Folium | ✅ Completo |
| `ExportadorGIS` | `gis_export.py` | Exportación GeoTIFF/GeoJSON/Shapefile | ✅ Completo |
| `IntegradorGEE` | `gee_integration.py` | Google Earth Engine | ✅ Completo |

---

## VisualizadorESD

Clase principal para visualizar resultados del análisis ESD.

### Inicialización

```python
from seismex.visualization import VisualizadorESD
from seismex.analysis import CalculadoraESD

# Calcular ESD primero
resultado = calculadora.calcular_esd(catalogo)

# Crear visualizador
viz = VisualizadorESD(
    resultado,
    catalogo=catalogo,          # Opcional: para epicentros
    dpi=150,                    # Resolución de figuras
    estilo='seismex',           # Estilo: 'seismex', 'paper', 'minimal', 'dark', 'presentacion'
    idioma='es'                 # Idioma: 'es', 'en'
)
```

### Secciones Horizontales

```python
# Una sola profundidad
fig = viz.graficar_seccion_horizontal(
    profundidad_km=30,
    mostrar_epicentros=True,    # Mostrar epicentros
    mostrar_colorbar=True,
    guardar='esd_30km.png'
)

# Múltiples profundidades (panel)
fig = viz.graficar_secciones_horizontales(
    profundidades=[10, 30, 50, 70],
    columnas=2,                 # Columnas del panel
    guardar='esd_horizontales.png'
)

# Panel completo (estilo Del Pezzo et al.)
fig = viz.crear_panel_completo(
    profundidades=[5, 10, 20, 35],
    guardar='panel_esd.png'
)
```

### Secciones Verticales

```python
# Perfil N-S a longitud fija
fig = viz.graficar_seccion_vertical_ns(
    longitud=-103.5,
    mostrar_epicentros=True,
    guardar='perfil_ns.png'
)

# Perfil E-W a latitud fija
fig = viz.graficar_seccion_vertical_ew(
    latitud=19.3,
    guardar='perfil_ew.png'
)

# Panel de secciones verticales
fig = viz.crear_panel_secciones_verticales(
    longitudes_ns=[-104.0, -103.5, -103.0],
    latitudes_ew=[19.0, 19.5],
    guardar='perfiles_verticales.png'
)

# Múltiples perfiles personalizados
fig = viz.graficar_secciones_verticales(
    perfiles=[
        {'tipo': 'ns', 'valor': -104.0},
        {'tipo': 'ns', 'valor': -103.5},
        {'tipo': 'ew', 'valor': 19.0},
        {'tipo': 'ew', 'valor': 19.5}
    ],
    guardar='perfiles_custom.png'
)
```

### Gutenberg-Richter

```python
# Graficar distribución frecuencia-magnitud
fig = viz.graficar_gutenberg_richter(
    magnitudes=catalogo.datos['magnitud'].values,
    b_value=1.0,
    a_value=4.5,
    mc=2.5,
    b_error=0.05,
    a_error=0.1,
    guardar='gutenberg_richter.png'
)
```

### Vista 3D

```python
# Visualización 3D del volumen ESD
fig = viz.graficar_3d(
    umbral_esd=-3,              # Solo mostrar ESD > umbral
    opacidad=0.7,
    azimuth=-60,
    elevacion=30,
    guardar='esd_3d.png'
)
```

### Exportación desde Visualizador

```python
# Exportar a GeoTIFF
viz.exportar_geotiff(
    profundidad_km=30,
    ruta='esd_30km.tif',
    crs='EPSG:4326'
)

# Exportar contornos a GeoJSON
viz.exportar_geojson_contornos(
    profundidad_km=30,
    ruta='contornos.geojson',
    niveles=[-3, -2, -1, 0]
)
```

---

## Paleta de Colores

### PaletaColoresESD

Reproduce la paleta del artículo de Del Pezzo et al.

```python
from seismex.visualization import PaletaColoresESD

paleta = PaletaColoresESD()

# Niveles estándar
niveles = paleta.niveles_estandar
# [-12, -7, -4.5, -3.0, -2.5, -2.0, -1.0, -0.5, 0, 0.5]

# Colormap para matplotlib
cmap = paleta.obtener_colormap('esd')  # 'esd', 'divergente', 'secuencial', 'profundidad'

# Normalización
norm = paleta.obtener_normalizacion(vmin=-12, vmax=0.5)

# Color para un valor específico
color_hex = paleta.obtener_hex_por_valor(-3.5)

# Mostrar todas las paletas
paleta.mostrar_paletas(guardar='paletas.png')

# Usar en matplotlib
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
im = ax.pcolormesh(X, Y, ESD, cmap=cmap, norm=norm)
paleta.crear_colorbar(ax, im, label='log₁₀(ESD)')
```

### PaletaColoresSismicidad

```python
from seismex.visualization import PaletaColoresSismicidad

paleta_sism = PaletaColoresSismicidad()

# Color por magnitud
color = paleta_sism.color_por_magnitud(5.2)

# Color por profundidad
color = paleta_sism.color_por_profundidad(45)  # km

# Tamaño de marcador por magnitud
size = paleta_sism.tamanio_por_magnitud(5.2)
```

### Colores por Nivel

| Rango | Color | Hex | Interpretación |
|-------|-------|-----|----------------|
| < -7 | Índigo | #4B0082 | Muy bajo |
| -7 a -4.5 | Azul | #0000CD | Bajo |
| -4.5 a -3 | Azul cielo | #00BFFF | Bajo-moderado |
| -3 a -2 | Verde | #00FF7F | Moderado |
| -2 a -1 | Verde pálido | #98FB98 | Moderado-alto |
| -1 a -0.5 | Rosa claro | #FFB6C1 | Alto |
| -0.5 a 0 | Rosa fuerte | #FF69B4 | Alto |
| > 0 | Rojo | #DC143C | Muy alto |

---

## Mapas Interactivos

### MapaInteractivo (Folium)

```python
from seismex.visualization import MapaInteractivo

# Crear mapa base
mapa = MapaInteractivo(
    centro=(19.3, -103.5),
    zoom=8,
    tiles='CartoDB positron'    # 'OpenStreetMap', 'Stamen Terrain', 'Esri WorldImagery'
)

# Agregar capa ESD (heatmap o contornos)
mapa.agregar_capa_esd(
    resultado_esd,
    profundidad_km=30,
    opacidad=0.7,
    metodo='heatmap'            # 'heatmap' o 'contornos'
)

# Agregar epicentros
mapa.agregar_epicentros(
    catalogo,
    color_por='magnitud',       # 'magnitud', 'profundidad'
    tamanio_por='magnitud',     # 'magnitud', 'fijo'
    popup=True,                 # Información al hacer clic
    clustering=False            # Agrupar marcadores cercanos
)

# Agregar capas adicionales
mapa.agregar_fallas('mexico_fallas.geojson')
mapa.agregar_volcanes(volcanes=[
    {'nombre': 'Volcán de Colima', 'lat': 19.514, 'lon': -103.617}
])
mapa.agregar_ciudades(['Colima', 'Guadalajara', 'Manzanillo'])

# Controles
mapa.agregar_control_capas()
mapa.agregar_fullscreen()
mapa.agregar_coordenadas_mouse()
mapa.agregar_escala()

# Guardar
mapa.guardar('mapa_esd_interactivo.html')
```

### Animación Temporal

```python
# Crear animación de evolución temporal
mapa.crear_animacion_temporal(
    catalogo,
    ventana_dias=365,
    paso_dias=30
)
mapa.guardar('animacion_esd.html')
```

### Funciones Rápidas

```python
from seismex.visualization import crear_mapa_rapido, crear_mapa_esd_completo

# Mapa rápido solo con epicentros
mapa = crear_mapa_rapido(catalogo, zoom=8)

# Mapa completo con ESD y epicentros
mapa = crear_mapa_esd_completo(
    resultado_esd,
    catalogo,
    profundidad_km=30,
    guardar='mapa_completo.html'
)
```

---

## Exportación GIS

### ExportadorGIS

```python
from seismex.visualization import ExportadorGIS

exportador = ExportadorGIS(resultado_esd, catalogo)

# Exportar a GeoTIFF
exportador.exportar_geotiff(
    'esd_30km.tif',
    profundidad_km=30,
    crs='EPSG:4326',
    compress='lzw',
    metadatos={'autor': 'SEISMEX'}
)

# Exportar múltiples profundidades como stack
exportador.exportar_geotiff_stack(
    'esd_stack.tif',
    profundidades=[10, 20, 30, 40, 50]
)

# Exportar a GeoJSON
exportador.exportar_geojson(
    'esd_contornos.geojson',
    profundidad_km=30,
    niveles=[-3, -2, -1, 0],
    tipo='contornos'            # 'contornos', 'puntos', 'grid'
)

# Exportar a Shapefile
exportador.exportar_shapefile(
    'esd_contornos',
    profundidad_km=30
)

# Exportar catálogo a GeoPackage
exportador.exportar_catalogo_gpkg(
    'catalogo.gpkg',
    catalogo,
    incluir_esd=True            # Agregar valor ESD a cada evento
)

# Exportar a KML (Google Earth)
exportador.exportar_kml(
    'esd.kml',
    profundidad_km=30
)

# Exportar a NetCDF (volumen completo)
exportador.exportar_netcdf('esd_volumen.nc')
```

### Formatos Soportados

| Formato | Extensión | Descripción | Estado |
|---------|-----------|-------------|--------|
| GeoTIFF | .tif | Raster georreferenciado | ✅ |
| GeoTIFF Stack | .tif | Múltiples bandas | ✅ |
| GeoJSON | .geojson | Vectores JSON | ✅ |
| Shapefile | .shp | ESRI Shapefile | ✅ |
| GeoPackage | .gpkg | Base de datos espacial | ✅ |
| KML | .kml | Google Earth | ✅ |
| NetCDF | .nc | Datos científicos | ✅ |

---

## Google Earth Engine

### IntegradorGEE

```python
from seismex.visualization import IntegradorGEE

# Inicializar (requiere autenticación GEE)
gee = IntegradorGEE(proyecto='mi-proyecto-gee')
gee.autenticar()

# Crear mapa interactivo con geemap
mapa = gee.crear_mapa(centro=(19.0, -104.0), zoom=8, basemap='SATELLITE')

# Agregar capas
region = gee.crear_region(resultado_esd)
gee.agregar_topografia(mapa, region)
gee.agregar_pendiente(mapa, region)
gee.agregar_capa_esd(mapa, resultado_esd, profundidad_km=30)
gee.agregar_puntos(mapa, catalogo)
gee.agregar_limites(mapa, nivel=1, pais='Mexico')

# Colorbar
gee.agregar_colorbar(mapa, {'min': -12, 'max': 0, 'palette': gee.PALETAS['esd']})

# Guardar
gee.guardar_mapa(mapa, 'mapa_gee.html')

# Exportar a Google Drive
gee.exportar_a_drive(
    imagen=imagen_esd,
    nombre='esd_export',
    carpeta='SEISMEX_Exports',
    region=region,
    escala=100
)
```

### Capas Base Disponibles

| Capa | ID | Descripción |
|------|----|-------------|
| SRTM | `USGS/SRTMGL1_003` | Topografía 30m |
| NASADEM | `NASA/NASADEM_HGT/001` | Topografía mejorada |
| Sentinel-2 | `COPERNICUS/S2_SR_HARMONIZED` | Imágenes ópticas |
| JRC Water | `JRC/GSW1_4/GlobalSurfaceWater` | Agua superficial |
| GAUL | `FAO/GAUL/2015/level1` | Límites administrativos |

---

## Estilos

### Estilos Predefinidos

```python
# Estilo 'seismex' (default) - Balance entre claridad y estética
viz = VisualizadorESD(resultado, estilo='seismex')

# Estilo 'paper' - Para publicaciones científicas
viz = VisualizadorESD(resultado, estilo='paper')

# Estilo 'minimal' - Diseño limpio, sin grid
viz = VisualizadorESD(resultado, estilo='minimal')

# Estilo 'dark' - Fondo oscuro para presentaciones
viz = VisualizadorESD(resultado, estilo='dark')

# Estilo 'presentacion' - Texto grande para proyección
viz = VisualizadorESD(resultado, estilo='presentacion')
```

### Archivos de Estilo

Los estilos están definidos en archivos `.mplstyle`:

```
seismex/visualization/styles/
├── seismex.mplstyle      # Estilo principal
├── paper.mplstyle        # Para publicaciones
├── minimal.mplstyle      # Minimalista
├── dark.mplstyle         # Modo oscuro
└── presentacion.mplstyle # Para slides
```

### Usar Estilos Directamente

```python
import matplotlib.pyplot as plt

# Usar estilo de archivo
plt.style.use('seismex/visualization/styles/seismex.mplstyle')

# Cambiar estilo en tiempo de ejecución
viz.cambiar_estilo('dark')
```

---

## Personalización

### ConfigVisualizacion

```python
from seismex.visualization import ConfigVisualizacion, VisualizadorESD

# Configuración personalizada
config = ConfigVisualizacion(
    fuente_titulo='Arial',
    tamano_titulo=14,
    fuente_ejes='Arial',
    tamano_ejes=12,
    colorbar_orientacion='vertical',
    colorbar_shrink=0.8,
    grid_alpha=0.3,
    linea_costa=True,
    color_oceano='#e6f3ff',
    mostrar_escala=True,
    idioma='es'
)

viz = VisualizadorESD(resultado, config=config)
```

### Agregar Elementos Personalizados

```python
# Obtener axes para personalización
fig, ax = viz.crear_figura_base(profundidad_km=30)

# Agregar elementos personalizados
ax.plot(-103.617, 19.514, 'k^', markersize=10, label='Volcán Colima')
ax.annotate('Volcán de Fuego', (-103.617, 19.514), fontsize=8)

# Agregar escala (requiere matplotlib-scalebar)
from matplotlib_scalebar.scalebar import ScaleBar
ax.add_artist(ScaleBar(111.32, location='lower left'))

# Guardar
fig.savefig('esd_personalizado.png', dpi=300, bbox_inches='tight')
```

### Cambiar Idioma

```python
# Español (default)
viz = VisualizadorESD(resultado, idioma='es')

# Inglés
viz = VisualizadorESD(resultado, idioma='en')

# Cambiar en tiempo de ejecución
viz.cambiar_idioma('en')
```

---

## Archivos del Módulo

```
seismex/visualization/
├── __init__.py               # Exportaciones
├── plotter.py                # VisualizadorESD
├── colormaps.py              # PaletaColoresESD, PaletaColoresSismicidad
├── interactive.py            # MapaInteractivo (Folium)
├── gis_export.py             # ExportadorGIS
├── gee_integration.py        # IntegradorGEE
├── styles/                   # Estilos matplotlib
│   ├── seismex.mplstyle
│   ├── paper.mplstyle
│   ├── minimal.mplstyle
│   ├── dark.mplstyle
│   └── presentacion.mplstyle
└── README.md                 # Este archivo
```

---

## Dependencias

```bash
# Core (requerido)
pip install matplotlib>=3.5.0 numpy>=1.21.0

# Mapas interactivos
pip install folium>=0.12.0 branca>=0.4.0

# Exportación GIS
pip install rasterio>=1.2.0 fiona>=1.8.0 geopandas>=0.10.0 shapely>=1.8.0

# NetCDF
pip install xarray netcdf4

# Google Earth Engine (opcional)
pip install earthengine-api>=0.1.300 geemap>=0.15.0
```

### Verificar Dependencias

```python
from seismex.visualization import verificar_dependencias, mostrar_info

# Ver estado de dependencias
estado = verificar_dependencias()
print(estado)

# Mostrar información completa
mostrar_info()
```

---

## Ejemplos de Salida

### Secciones Horizontales
![Secciones horizontales ESD](../../docs/examples/esd_horizontales.png)

### Perfiles Verticales
![Perfiles verticales ESD](../../docs/examples/esd_verticales.png)

### Mapa Interactivo
Ver ejemplo en `notebooks/visualizacion_interactiva.ipynb`

---

## Véase También

- [`seismex.analysis`](../analysis/README.md) - Análisis ESD
- [`seismex.core`](../core/README.md) - Catálogos sísmicos
- [Documentación completa](../../docs/README.md)
