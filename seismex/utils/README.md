# 📦 seismex.core

Módulo central de SEISMEX que contiene las funcionalidades base para el manejo de catálogos sísmicos, conversión de magnitudes y preprocesamiento de datos.

---

## 📋 Contenido

- [Clases Principales](#clases-principales)
- [CatalogoSismico](#catalogosismico)
- [Carga de Datos](#carga-de-datos)
- [Validación](#validación)
- [Filtrado](#filtrado)
- [Transformación](#transformación)
- [Exportación](#exportación)
- [Conversión de Magnitudes](#conversión-de-magnitudes)
- [Ejemplos](#ejemplos)

---

## Clases Principales

| Clase | Archivo | Descripción | Estado |
|-------|---------|-------------|--------|
| `CatalogoSismico` | `catalog.py` | Manejo de catálogos sísmicos | ✅ Completo |
| `MetadataCatalogo` | `catalog.py` | Metadatos del catálogo | ✅ Completo |
| `ResultadoValidacion` | `catalog.py` | Resultado de validación | ✅ Completo |

---

## CatalogoSismico

Clase principal para el manejo de catálogos sísmicos de múltiples fuentes.

### Atributos

```python
class CatalogoSismico:
    """
    Contenedor para catálogos sísmicos con soporte para múltiples formatos.
    
    Attributes:
        eventos: pd.DataFrame
            DataFrame con columnas: fecha, latitud, longitud, profundidad_km, 
            magnitud, tipo_magnitud, fuente
        metadata: MetadataCatalogo
            Información del catálogo (fuente, región, etc.)
    
    Properties (solo lectura):
        n_eventos: int - Número total de eventos
        rango_fechas: tuple - (fecha_min, fecha_max)
        rango_magnitudes: tuple - (mag_min, mag_max)
        rango_profundidades: tuple - (prof_min, prof_max)
        extension_geografica: dict - Límites lat/lon
        columnas: list - Lista de columnas disponibles
        esta_validado: bool - Si el catálogo ha sido validado
    """
```

---

## Carga de Datos

### Desde CSV

```python
from seismex.core import CatalogoSismico

# Formato SSN (Servicio Sismológico Nacional)
catalogo = CatalogoSismico.desde_csv(
    'sismos_ssn.csv',
    formato='ssn'
)

# Formato USGS
catalogo = CatalogoSismico.desde_csv(
    'usgs_catalog.csv',
    formato='usgs'
)

# Formato ISC
catalogo = CatalogoSismico.desde_csv(
    'isc_gem.csv',
    formato='isc'
)

# Formato personalizado con mapeo de columnas
catalogo = CatalogoSismico.desde_csv(
    'mi_catalogo.csv',
    formato='custom',
    mapeo_columnas={
        'date': 'fecha',
        'lat': 'latitud',
        'lon': 'longitud',
        'depth': 'profundidad_km',
        'mag': 'magnitud'
    }
)
```

### Desde Excel

```python
catalogo = CatalogoSismico.desde_excel(
    'sismos.xlsx',
    hoja='Datos',
    formato='ssn'
)
```

### Desde DataFrame

```python
import pandas as pd

df = pd.DataFrame({
    'fecha': pd.date_range('2020-01-01', periods=100, freq='D'),
    'latitud': np.random.uniform(18.5, 20.5, 100),
    'longitud': np.random.uniform(-104.5, -103.0, 100),
    'profundidad_km': np.random.exponential(30, 100),
    'magnitud': np.random.exponential(1.5, 100) + 2.0
})

catalogo = CatalogoSismico.desde_dataframe(df, fuente='ejemplo')
```

### Desde APIs (métodos de conveniencia)

```python
# Desde datos del SSN
catalogo = CatalogoSismico.desde_ssn(datos_ssn)

# Desde datos de USGS
catalogo = CatalogoSismico.desde_usgs(datos_usgs)

# Desde datos de ISC
catalogo = CatalogoSismico.desde_isc(datos_isc)
```

### Función de Conveniencia

```python
from seismex.core import cargar_catalogo

# Detección automática de formato
catalogo = cargar_catalogo('sismos.csv')  # Detecta SSN/USGS/custom
catalogo = cargar_catalogo('sismos.xlsx')  # Detecta Excel
```

### Combinar Catálogos

```python
# Cargar múltiples fuentes
ssn = CatalogoSismico.desde_csv('ssn.csv', formato='ssn')
isc = CatalogoSismico.desde_csv('isc.csv', formato='isc')
usgs = CatalogoSismico.desde_csv('usgs.csv', formato='usgs')

# Combinar con detección de duplicados
catalogo_combinado = CatalogoSismico.combinar(
    [ssn, isc, usgs],
    tolerancia_km=50,        # Distancia máxima para considerar duplicado
    tolerancia_seg=60        # Diferencia temporal máxima
)

print(f"Total eventos: {len(catalogo_combinado)}")
```

---

## Validación

```python
# Validar catálogo
resultado = catalogo.validar(estricto=False)

print(resultado)
# ResultadoValidacion:
#   válido: True
#   errores: 0
#   advertencias: 3
#   Advertencias:
#     - 5 eventos sin tipo de magnitud

# Acceder a detalles
print(f"Es válido: {resultado.valido}")
print(f"Errores: {resultado.errores}")
print(f"Advertencias: {resultado.advertencias}")
```

---

## Filtrado

El filtrado soporta **encadenamiento de métodos** (fluent interface):

### Por Región Rectangular

```python
catalogo_colima = catalogo.filtrar_region(
    lat_min=18.5,
    lat_max=20.0,
    lon_min=-104.5,
    lon_max=-103.0
)
```

### Por Círculo

```python
# Filtrar por distancia a un punto
catalogo_cercanos = catalogo.filtrar_circulo(
    lat_centro=19.24,
    lon_centro=-103.72,
    radio_km=100
)
```

### Por Magnitud

```python
# Solo eventos M >= 4.0
catalogo_significativos = catalogo.filtrar_magnitud(mag_min=4.0)

# Rango de magnitudes
catalogo_rango = catalogo.filtrar_magnitud(mag_min=3.0, mag_max=5.0)
```

### Por Profundidad

```python
# Eventos someros (< 30 km)
catalogo_someros = catalogo.filtrar_profundidad(prof_max=30)

# Eventos de subducción (30-150 km)
catalogo_subduccion = catalogo.filtrar_profundidad(prof_min=30, prof_max=150)
```

### Por Fechas

```python
from datetime import datetime

catalogo_reciente = catalogo.filtrar_fechas(
    fecha_inicio=datetime(2020, 1, 1),
    fecha_fin=datetime(2024, 12, 31)
)

# También acepta strings
catalogo_2023 = catalogo.filtrar_fechas(
    fecha_inicio='2023-01-01',
    fecha_fin='2023-12-31'
)
```

### Filtro Personalizado

```python
# Filtro con función lambda
catalogo_custom = catalogo.filtrar(
    lambda df: (df['magnitud'] > 4.0) & (df['profundidad_km'] < 50)
)
```

### Encadenamiento

```python
# Pipeline de filtros
catalogo_final = (
    catalogo
    .filtrar_region(lat_min=18.5, lat_max=20.0, lon_min=-104.5, lon_max=-103.0)
    .filtrar_magnitud(mag_min=3.0)
    .filtrar_profundidad(prof_max=100)
    .filtrar_fechas(fecha_inicio='2010-01-01')
)

print(catalogo_final.resumen())
```

---

## Transformación

### Homogeneizar Magnitudes

```python
# Convertir todas las magnitudes a Mw
catalogo_mw = catalogo.homogeneizar_magnitudes('Mw')

# O modificar in-place
catalogo.homogeneizar_magnitudes('Mw', inplace=True)
```

**Conversiones soportadas:**
- `Ml → Mw` (magnitud local)
- `mb → Mw` (magnitud de ondas de cuerpo)
- `Ms → Mw` (magnitud de ondas superficiales)
- `Mc → Mw` (magnitud de coda)

### Ordenar

```python
# Por fecha (ascendente)
catalogo.ordenar('fecha', inplace=True)

# Por magnitud (descendente)
catalogo.ordenar('magnitud', ascendente=False, inplace=True)

# Por múltiples columnas
catalogo.ordenar(['fecha', 'magnitud'], inplace=True)
```

### Copiar

```python
# Copia profunda
catalogo_copia = catalogo.copiar()
```

---

## Exportación

### A CSV

```python
catalogo.to_csv('catalogo_procesado.csv')
```

### A Excel

```python
catalogo.to_excel('catalogo_procesado.xlsx', hoja='Sismos')
```

### A GeoJSON

```python
# Para uso en GIS/mapas web
catalogo.to_geojson('catalogo.geojson')
```

### A DataFrame

```python
df = catalogo.to_dataframe()
```

---

## Conversión de Magnitudes

El módulo incluye conversiones estándar entre escalas de magnitud:

```python
from seismex.core import CONVERSIONES_MAGNITUD

# Relaciones implementadas:
# Ml → Mw: Mw = 0.804 * Ml + 0.664 (México, SSN)
# mb → Mw: Mw = 1.131 * mb - 0.556 (Global)
# Ms → Mw: Mw = 0.646 * Ms + 2.16  (Global)
# Mc → Mw: Mw ≈ Ml (aproximación vía Ml)
```

---

## Propiedades y Resumen

```python
# Propiedades de solo lectura
print(f"Eventos: {catalogo.n_eventos}")
print(f"Fechas: {catalogo.rango_fechas}")
print(f"Magnitudes: {catalogo.rango_magnitudes}")
print(f"Profundidades: {catalogo.rango_profundidades}")
print(f"Extensión: {catalogo.extension_geografica}")

# Resumen completo
print(catalogo.resumen())

# Resumen detallado
print(catalogo.resumen(detallado=True))

# Métodos de inspección (similares a pandas)
catalogo.head(10)
catalogo.tail(5)
catalogo.sample(10)
catalogo.describe()
```

---

## Ejemplos

### Ejemplo 1: Pipeline Completo

```python
from seismex.core import CatalogoSismico

# Cargar
catalogo = CatalogoSismico.desde_csv('ssn_2024.csv', formato='ssn')

# Validar
resultado = catalogo.validar()
if not resultado.valido:
    print(f"Errores: {resultado.errores}")

# Procesar
catalogo_procesado = (
    catalogo
    .filtrar_region(lat_min=18.5, lat_max=20.5, lon_min=-104.5, lon_max=-103.0)
    .filtrar_magnitud(mag_min=2.5)
    .filtrar_profundidad(prof_max=100)
)

# Homogeneizar
catalogo_procesado.homogeneizar_magnitudes('Mw', inplace=True)

# Exportar
catalogo_procesado.to_csv('catalogo_colima_mw.csv')
catalogo_procesado.to_geojson('catalogo_colima.geojson')

# Resumen final
print(catalogo_procesado.resumen(detallado=True))
```

### Ejemplo 2: Combinar Catálogos

```python
# Cargar múltiples fuentes
ssn = CatalogoSismico.desde_csv('ssn.csv', formato='ssn')
isc = CatalogoSismico.desde_csv('isc_gem.csv', formato='isc')
usgs = CatalogoSismico.desde_csv('usgs.csv', formato='usgs')

# Combinar con prioridad
catalogo_combinado = CatalogoSismico.combinar(
    [ssn, isc, usgs],
    tolerancia_km=50,
    tolerancia_seg=60
)

print(f"SSN: {len(ssn)} eventos")
print(f"ISC: {len(isc)} eventos")
print(f"USGS: {len(usgs)} eventos")
print(f"Combinado: {len(catalogo_combinado)} eventos (sin duplicados)")
```

---

## Archivos del Módulo

```
seismex/core/
├── __init__.py           # Exportaciones del módulo
├── catalog.py            # Clase CatalogoSismico (~1000 líneas)
└── README.md             # Este archivo
```

---

## Dependencias

```python
# Core (requerido)
numpy>=1.21.0
pandas>=1.3.0

# Opcional
geopandas>=0.10.0   # Para exportación GeoJSON mejorada
```

---

## Estado de Desarrollo

| Componente | Estado | Descripción |
|------------|--------|-------------|
| CatalogoSismico | ✅ Completo | Clase principal funcional |
| Carga CSV/Excel | ✅ Completo | Formatos SSN, USGS, ISC, custom |
| Conversión magnitudes | ✅ Completo | Ml, mb, Ms, Mc → Mw |
| Filtrado espacial/temporal | ✅ Completo | Región, círculo, fechas |
| Detección duplicados | ✅ Completo | Por distancia + tiempo |
| Validación | ✅ Completo | Columnas, rangos, valores |
| Exportación | ✅ Completo | CSV, Excel, GeoJSON, DataFrame |
| Homogeneización | ✅ Completo | Conversión automática de magnitudes |

---

## Véase También

- [`seismex.data`](../data/README.md) - Conectores de datos (SSN, USGS, ISC, IRIS)
- [`seismex.analysis`](../analysis/README.md) - Módulos de análisis (ESD, Gutenberg-Richter)
- [`seismex.visualization`](../visualization/README.md) - Visualización y mapas
