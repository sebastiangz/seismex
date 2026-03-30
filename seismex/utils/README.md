# 🔧 SEISMEX Utils

Utilidades y funciones auxiliares para el sistema SEISMEX.

## Contenido

- [geo.py](#geopy---utilidades-geográficas)
- [io.py](#iopy---entrada-y-salida)
- [validators.py](#validatorspy---validación-de-datos)
- [constants.py](#constantspy---constantes-del-sistema)

---

## `geo.py` - Utilidades Geográficas

Funciones para cálculos geográficos y transformaciones de coordenadas.

### Funciones Disponibles

```python
from seismex.utils.geo import (
    calcular_distancia_haversine,
    calcular_distancia_vincenty,
    convertir_utm_a_latlon,
    convertir_latlon_a_utm,
    calcular_azimut,
    punto_en_poligono,
    crear_grilla_regular,
    obtener_zona_utm
)
```

### Ejemplos de Uso

#### Distancia entre dos puntos

```python
from seismex.utils.geo import calcular_distancia_haversine

# Distancia Colima - Ciudad de México
distancia = calcular_distancia_haversine(
    lat1=19.2433, lon1=-103.7250,  # Colima
    lat2=19.4326, lon2=-99.1332    # CDMX
)
print(f"Distancia: {distancia:.2f} km")
# Output: Distancia: 465.23 km
```

#### Conversión UTM ↔ Lat/Lon

```python
from seismex.utils.geo import convertir_latlon_a_utm, convertir_utm_a_latlon

# Lat/Lon a UTM
x, y, zona, hemisferio = convertir_latlon_a_utm(19.2433, -103.7250)
print(f"UTM: {x:.2f} E, {y:.2f} N, Zona {zona}{hemisferio}")

# UTM a Lat/Lon
lat, lon = convertir_utm_a_latlon(x, y, zona, hemisferio)
```

#### Crear grilla regular

```python
from seismex.utils.geo import crear_grilla_regular

# Grilla de 0.1° sobre Colima
grilla = crear_grilla_regular(
    lat_min=18.5, lat_max=20.0,
    lon_min=-104.5, lon_max=-103.0,
    paso=0.1
)
print(f"Puntos en grilla: {len(grilla)}")
```

---

## `io.py` - Entrada y Salida

Funciones para lectura/escritura de archivos y formatos especializados.

### Funciones Disponibles

```python
from seismex.utils.io import (
    leer_catalogo_ssn,
    leer_catalogo_isc,
    exportar_geojson,
    exportar_geotiff,
    exportar_kml,
    guardar_pickle,
    cargar_pickle,
    comprimir_directorio,
    descomprimir_archivo
)
```

### Ejemplos de Uso

#### Leer catálogo del SSN

```python
from seismex.utils.io import leer_catalogo_ssn

# Lee formato nativo del SSN
catalogo = leer_catalogo_ssn("sismos_2024.csv")
print(f"Eventos cargados: {len(catalogo)}")
```

#### Exportar a GeoJSON

```python
from seismex.utils.io import exportar_geojson

exportar_geojson(
    datos=catalogo,
    archivo_salida="sismos_colima.geojson",
    propiedades=['fecha', 'magnitud', 'profundidad']
)
```

#### Exportar resultados ESD a GeoTIFF

```python
from seismex.utils.io import exportar_geotiff

exportar_geotiff(
    grilla=resultado_esd.grilla,
    valores=resultado_esd.valores_log,
    archivo_salida="esd_colima.tif",
    crs="EPSG:4326",
    nodata=-999
)
```

---

## `validators.py` - Validación de Datos

Funciones para validar y limpiar datos sísmicos.

### Funciones Disponibles

```python
from seismex.utils.validators import (
    validar_coordenadas,
    validar_magnitud,
    validar_profundidad,
    validar_fecha,
    validar_catalogo_completo,
    detectar_outliers,
    reportar_calidad
)
```

### Ejemplos de Uso

#### Validar coordenadas

```python
from seismex.utils.validators import validar_coordenadas

# Validar que esté en México
es_valido = validar_coordenadas(
    lat=19.24, lon=-103.72,
    lat_min=14.0, lat_max=33.0,
    lon_min=-118.0, lon_max=-86.0
)
```

#### Reporte de calidad del catálogo

```python
from seismex.utils.validators import reportar_calidad

reporte = reportar_calidad(catalogo)
print(reporte)
# Output:
# ═══════════════════════════════════════
# REPORTE DE CALIDAD DEL CATÁLOGO
# ═══════════════════════════════════════
# Total eventos: 15,432
# Coordenadas válidas: 99.8%
# Magnitudes válidas: 98.5%
# Profundidades válidas: 97.2%
# Fechas válidas: 100.0%
# Duplicados detectados: 23
# Outliers potenciales: 45
# ═══════════════════════════════════════
```

#### Detectar outliers

```python
from seismex.utils.validators import detectar_outliers

outliers = detectar_outliers(
    catalogo,
    metodo='iqr',           # 'iqr', 'zscore', 'isolation_forest'
    columnas=['magnitud', 'profundidad'],
    factor=1.5
)
print(f"Outliers detectados: {len(outliers)}")
```

---

## `constants.py` - Constantes del Sistema

Constantes físicas, geográficas y de configuración.

### Constantes Disponibles

```python
from seismex.utils.constants import (
    # Constantes físicas
    COEF_ENERGIA_A,        # 1.5 (log E = a*M + b)
    COEF_ENERGIA_B,        # 11.8 (ergios)
    
    # Límites geográficos de México
    MEXICO_LAT_MIN,        # 14.5°
    MEXICO_LAT_MAX,        # 32.7°
    MEXICO_LON_MIN,        # -117.1°
    MEXICO_LON_MAX,        # -86.7°
    
    # Zonas sísmicas principales
    ZONAS_SISMICAS,        # Dict con límites de cada zona
    
    # Configuración por defecto
    DEFAULT_CELL_SIZE,     # 10 km
    DEFAULT_DEPTH_RANGE,   # (0, 150) km
    DEFAULT_MC_METHOD,     # 'maxc'
    DEFAULT_B_METHOD,      # 'mle'
    
    # Paleta de colores ESD
    COLORES_ESD,           # Lista de colores
    NIVELES_ESD,           # Niveles de contorno
    
    # Rutas por defecto
    DIR_CACHE,             # ~/.seismex/cache
    DIR_CONFIG             # ~/.seismex/config
)
```

### Uso

```python
from seismex.utils.constants import MEXICO_LAT_MIN, MEXICO_LAT_MAX

# Validar que un punto esté en México
def en_mexico(lat, lon):
    from seismex.utils.constants import (
        MEXICO_LAT_MIN, MEXICO_LAT_MAX,
        MEXICO_LON_MIN, MEXICO_LON_MAX
    )
    return (MEXICO_LAT_MIN <= lat <= MEXICO_LAT_MAX and
            MEXICO_LON_MIN <= lon <= MEXICO_LON_MAX)
```

---

## Dependencias Internas

```
utils/
├── geo.py          # Sin dependencias internas
├── io.py           # Usa: geo.py, constants.py
├── validators.py   # Usa: constants.py
└── constants.py    # Sin dependencias internas
```

## Dependencias Externas

| Módulo | Dependencias |
|--------|-------------|
| `geo.py` | numpy, pyproj |
| `io.py` | pandas, geopandas, rasterio |
| `validators.py` | numpy, pandas, scipy |
| `constants.py` | (ninguna) |

---

## Estado de Desarrollo

| Componente | Estado |
|------------|--------|
| `geo.py` | 🔄 En desarrollo |
| `io.py` | 🔄 En desarrollo |
| `validators.py` | 📋 Planificado |
| `constants.py` | ✅ Completo |

---

## Contribuir

Para agregar nuevas utilidades:

1. Identifica el módulo apropiado (geo, io, validators)
2. Sigue el estilo de código existente
3. Incluye docstrings con ejemplos
4. Agrega tests unitarios
5. Actualiza este README

Ver [CONTRIBUTING.md](../../CONTRIBUTING.md) para guías detalladas.
