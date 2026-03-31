# 📦 seismex.core

Módulo central de SEISMEX que contiene las funcionalidades base para el manejo de catálogos sísmicos, conversión de magnitudes y preprocesamiento de datos.

---

## 📋 Contenido

- [Clases Principales](#clases-principales)
- [CatalogoSismico](#catalogosismico)
- [Conversión de Magnitudes](#conversión-de-magnitudes)
- [Validación](#validación)
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

### Inicialización

```python
from seismex.core import CatalogoSismico, cargar_catalogo

# Desde CSV (detección automática de formato)
catalogo = CatalogoSismico.desde_csv('sismos.csv', formato='ssn')

# Desde Excel
catalogo = CatalogoSismico.desde_excel('sismos.xlsx', hoja=0)

# Desde DataFrame
catalogo = CatalogoSismico.desde_dataframe(df, fuente='personalizado')

# Función de conveniencia (detecta formato automáticamente)
catalogo = cargar_catalogo('sismos.csv')
```

### Formatos Soportados

| Formato | Código | Descripción |
|---------|--------|-------------|
| SSN | `'ssn'` | Servicio Sismológico Nacional de México |
| USGS | `'usgs'` | United States Geological Survey |
| ISC | `'isc'` | International Seismological Centre |
| ISC-GEM | `'isc-gem'` | ISC-GEM Global Instrumental Catalogue |
| IRIS | `'iris'` | IRIS FDSN Web Services |
| Custom | `'custom'` | Formato personalizado con mapeo de columnas |

### Atributos y Propiedades

```python
# Propiedades del catálogo
catalogo.n_eventos           # Número total de eventos
catalogo.rango_fechas        # (fecha_min, fecha_max)
catalogo.rango_magnitudes    # (mag_min, mag_max)
catalogo.rango_profundidades # (prof_min, prof_max)
catalogo.extension_geografica # (lat_min, lat_max, lon_min, lon_max)
catalogo.centro_geografico   # (lat_centro, lon_centro)
catalogo.metadata            # MetadataCatalogo con información adicional
catalogo.columnas            # Lista de columnas disponibles
catalogo.esta_validado       # True si ha pasado validación
```

---

## Filtrado

### Filtrado Espacial

```python
# Por región rectangular
filtrado = catalogo.filtrar_region(
    lat_min=18.5, lat_max=20.5,
    lon_min=-104.5, lon_max=-103.0
)

# Por círculo (radio desde un punto)
filtrado = catalogo.filtrar_circulo(
    lat_centro=19.24, lon_centro=-103.72,
    radio_km=100
)
```

### Filtrado por Magnitud y Profundidad

```python
# Por magnitud
filtrado = catalogo.filtrar_magnitud(mag_min=4.0, mag_max=7.0)

# Por profundidad
filtrado = catalogo.filtrar_profundidad(prof_min=0, prof_max=50)
```

### Filtrado Temporal

```python
# Por rango de fechas
filtrado = catalogo.filtrar_fechas(
    fecha_inicio='2020-01-01',
    fecha_fin='2024-12-31'
)
```

### Filtro Personalizado

```python
# Filtro con función lambda
filtrado = catalogo.filtrar(
    lambda df: (df['magnitud'] > 4.0) & (df['profundidad_km'] < 50)
)
```

### Encadenamiento de Métodos (Fluent Interface)

```python
# Aplicar múltiples filtros en cadena
resultado = (
    catalogo
    .filtrar_region(lat_min=18.5, lat_max=20.5, lon_min=-104.5, lon_max=-103.0)
    .filtrar_magnitud(mag_min=4.0)
    .filtrar_profundidad(prof_max=70)
    .filtrar_fechas(fecha_inicio='2020-01-01')
)
```

---

## Conversión de Magnitudes

### Homogeneización a Mw

```python
# Convertir todas las magnitudes a Mw
catalogo_mw = catalogo.homogeneizar_magnitudes('Mw')

# Modificar in-place
catalogo.homogeneizar_magnitudes('Mw', inplace=True)

# Verificar estado
print(catalogo.metadata.homogeneizado)  # True
print(catalogo.metadata.tipo_magnitud_homogeneizada)  # 'Mw'
```

### Conversiones Soportadas

| Origen | Destino | Relación |
|--------|---------|----------|
| Ml | Mw | Mw = 0.85 × Ml + 0.58 |
| mb | Mw | Mw = 1.17 × mb - 0.76 |
| Ms | Mw | Mw = 0.67 × Ms + 2.07 |
| Mc | Mw | Mw ≈ Mc (aproximación) |

---

## Validación

### Validar Catálogo

```python
# Validación completa
resultado = catalogo.validar(estricto=False)

# Verificar resultado
print(resultado.es_valido)    # True/False
print(resultado.n_errores)    # Número de errores
print(resultado.n_advertencias)  # Número de advertencias

# Detalles
for error in resultado.errores:
    print(f"ERROR: {error}")
for adv in resultado.advertencias:
    print(f"ADVERTENCIA: {adv}")
```

### Validaciones Realizadas

| Validación | Tipo | Descripción |
|------------|------|-------------|
| Columnas requeridas | Error | fecha, latitud, longitud, profundidad_km, magnitud |
| Rango de latitudes | Error | -90 a +90 |
| Rango de longitudes | Error | -180 a +180 |
| Rango de profundidades | Advertencia | 0 a 700 km |
| Rango de magnitudes | Advertencia | -2 a 10 |
| Fechas válidas | Error | Formato datetime válido |
| Valores faltantes | Advertencia | NaN en columnas críticas |

---

## Detección de Duplicados

```python
# Combinar catálogos con detección de duplicados
from seismex.core import CatalogoSismico

catalogo_combinado = CatalogoSismico.combinar(
    [catalogo_ssn, catalogo_usgs, catalogo_isc],
    prioridad=['ssn', 'usgs', 'isc'],  # Orden de preferencia
    tolerancia_duplicados_km=50,        # Distancia máxima entre duplicados
    tolerancia_duplicados_seg=60        # Diferencia temporal máxima
)

print(f"Eventos únicos: {len(catalogo_combinado)}")
```

---

## Exportación

### Formatos de Salida

```python
# A CSV
catalogo.to_csv('salida.csv', index=False)

# A Excel
catalogo.to_excel('salida.xlsx', sheet_name='Sismos')

# A GeoJSON (para GIS)
catalogo.to_geojson('salida.geojson')

# A DataFrame
df = catalogo.to_dataframe()
```

---

## Métodos de Inspección

```python
# Resumen del catálogo
print(catalogo.resumen())           # Resumen básico
print(catalogo.resumen(detallado=True))  # Resumen completo

# Vista de datos
catalogo.head(10)     # Primeros 10 eventos
catalogo.tail(5)      # Últimos 5 eventos
catalogo.sample(20)   # Muestra aleatoria
catalogo.describe()   # Estadísticas descriptivas

# Información
len(catalogo)         # Número de eventos
catalogo.columnas     # Lista de columnas
```

---

## Ejemplos Completos

### Ejemplo 1: Pipeline de Preprocesamiento

```python
from seismex.core import CatalogoSismico

# Cargar catálogo
catalogo = CatalogoSismico.desde_csv('ssn_2024.csv', formato='ssn')

# Validar
resultado = catalogo.validar()
if not resultado.es_valido:
    print("Errores encontrados:")
    for e in resultado.errores:
        print(f"  - {e}")

# Filtrar región de interés (Colima)
colima = catalogo.filtrar_region(
    lat_min=18.5, lat_max=20.5,
    lon_min=-104.5, lon_max=-103.0
)

# Filtrar por magnitud y profundidad
filtrado = (
    colima
    .filtrar_magnitud(mag_min=3.0)
    .filtrar_profundidad(prof_max=100)
)

# Homogeneizar magnitudes
filtrado.homogeneizar_magnitudes('Mw', inplace=True)

# Resumen final
print(filtrado.resumen(detallado=True))

# Exportar
filtrado.to_csv('colima_procesado.csv')
filtrado.to_geojson('colima_sismos.geojson')
```

### Ejemplo 2: Combinar Múltiples Fuentes

```python
from seismex.core import CatalogoSismico

# Cargar de múltiples fuentes
ssn = CatalogoSismico.desde_csv('ssn.csv', formato='ssn')
isc = CatalogoSismico.desde_csv('isc.csv', formato='isc')
usgs = CatalogoSismico.desde_csv('usgs.csv', formato='usgs')

# Combinar con detección de duplicados
combinado = CatalogoSismico.combinar(
    [ssn, isc, usgs],
    prioridad=['ssn', 'isc', 'usgs'],
    tolerancia_duplicados_km=50,
    tolerancia_duplicados_seg=60
)

print(f"SSN: {len(ssn)} eventos")
print(f"ISC: {len(isc)} eventos")
print(f"USGS: {len(usgs)} eventos")
print(f"Combinado (sin duplicados): {len(combinado)} eventos")
```

---

## Archivos del Módulo

```
seismex/core/
├── __init__.py           # Exportaciones del módulo
├── catalog.py            # CatalogoSismico, MetadataCatalogo, ResultadoValidacion
└── README.md             # Este archivo
```

---

## Columnas Estándar

### Requeridas

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | datetime | Fecha y hora UTC del evento |
| `latitud` | float | Latitud en grados decimales |
| `longitud` | float | Longitud en grados decimales |
| `profundidad_km` | float | Profundidad hipocentral en km |
| `magnitud` | float | Magnitud del evento |

### Opcionales

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `tipo_magnitud` | str | Tipo de magnitud (Mw, Ml, mb, Ms, Mc) |
| `fuente` | str | Fuente del dato (SSN, USGS, ISC) |
| `id_evento` | str | Identificador único del evento |
| `lugar` | str | Descripción del lugar |
| `incertidumbre_h` | float | Incertidumbre horizontal (km) |
| `incertidumbre_z` | float | Incertidumbre vertical (km) |
| `incertidumbre_m` | float | Incertidumbre de magnitud |
| `rms` | float | RMS del ajuste |
| `gap` | float | Gap azimutal (grados) |
| `nst` | int | Número de estaciones |

---

## Dependencias

```python
# Core (requeridas)
numpy>=1.21.0
pandas>=1.3.0

# Opcionales
geopandas>=0.10.0   # Para exportación GeoJSON avanzada
```

---

## Estado de Desarrollo

| Componente | Estado | Descripción |
|------------|--------|-------------|
| CatalogoSismico | ✅ Completo | Clase principal funcional |
| Carga CSV/Excel | ✅ Completo | Múltiples formatos soportados |
| Filtrado espacial/temporal | ✅ Completo | Región, círculo, fechas |
| Conversión de magnitudes | ✅ Completo | Ml, mb, Ms, Mc → Mw |
| Detección de duplicados | ✅ Completo | Por distancia y tiempo |
| Validación | ✅ Completo | Errores y advertencias |
| Exportación | ✅ Completo | CSV, Excel, GeoJSON |
| Encadenamiento de métodos | ✅ Completo | Fluent interface |

---

## Véase También

- [`seismex.analysis`](../analysis/README.md) - Módulos de análisis (ESD, Gutenberg-Richter)
- [`seismex.data`](../data/README.md) - Conectores de datos (SSN, USGS, ISC)
- [`seismex.visualization`](../visualization/README.md) - Visualización de resultados
