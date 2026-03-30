# 📦 seismex.core

Módulo central de SEISMEX que contiene las funcionalidades base para el manejo de catálogos sísmicos, conversión de magnitudes y preprocesamiento de datos.

---

## 📋 Contenido

- [Clases Principales](#clases-principales)
- [CatalogoSismico](#catalogosismico)
- [Conversión de Magnitudes](#conversión-de-magnitudes)
- [Preprocesamiento](#preprocesamiento)
- [Ejemplos](#ejemplos)

---

## Clases Principales

| Clase | Archivo | Descripción | Estado |
|-------|---------|-------------|--------|
| `CatalogoSismico` | `catalog.py` | Manejo de catálogos sísmicos | ✅ Completo |
| `EventoSismico` | `evento.py` | Representación de un evento | ✅ Completo |
| `ConvertidorMagnitud` | `magnitudes.py` | Conversión entre escalas | ✅ Completo |
| `Preprocesador` | `preprocessing.py` | Limpieza y filtrado | 🔄 En desarrollo |

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
            DataFrame con columnas: fecha, latitud, longitud, profundidad, 
            magnitud, tipo_magnitud, fuente
        metadata: dict
            Información del catálogo (fuente, región, etc.)
        es_valido: bool
            Indica si el catálogo pasó validación
    """
```

### Métodos de Carga

```python
# Desde archivo CSV
catalogo = CatalogoSismico.desde_csv(
    'catalogo.csv',
    formato='ssn',           # 'ssn', 'isc', 'usgs', 'custom'
    encoding='utf-8'
)

# Desde archivo Excel
catalogo = CatalogoSismico.desde_excel(
    'catalogo.xlsx',
    hoja='Eventos'
)

# Desde DataFrame de pandas
catalogo = CatalogoSismico.desde_dataframe(
    df,
    mapeo_columnas={
        'fecha': 'FECHA',
        'latitud': 'LAT',
        'longitud': 'LON',
        'profundidad': 'PROF_KM',
        'magnitud': 'MAG',
        'tipo_magnitud': 'TIPO_MAG'
    }
)

# Desde API del SSN (planificado)
catalogo = CatalogoSismico.desde_ssn(
    fecha_inicio='2020-01-01',
    fecha_fin='2024-12-31',
    region='colima'
)
```

### Métodos de Validación

```python
# Validar catálogo
es_valido, errores = catalogo.validar()

if not es_valido:
    for error in errores:
        print(f"Error: {error}")

# Obtener resumen
print(catalogo.resumen())
# Output:
# === Resumen del Catálogo Sísmico ===
# Número de eventos: 5,432
# Rango de magnitudes: 2.0 - 7.8
# Rango de profundidades: 0.1 - 148.5 km
# Extensión espacial:
#   Latitud:  17.50° - 20.90°
#   Longitud: -105.40° - -102.50°
```

### Métodos de Filtrado

```python
# Filtrar por región geográfica
catalogo_colima = catalogo.filtrar_region(
    lat_min=18.5, lat_max=20.0,
    lon_min=-104.5, lon_max=-103.0
)

# Filtrar por magnitud
catalogo_m4 = catalogo.filtrar_magnitud(mag_min=4.0)

# Filtrar por profundidad
catalogo_superficial = catalogo.filtrar_profundidad(
    prof_min=0, prof_max=30
)

# Filtrar por fecha
catalogo_2023 = catalogo.filtrar_fechas(
    fecha_inicio='2023-01-01',
    fecha_fin='2023-12-31'
)

# Encadenar filtros
catalogo_final = (catalogo
    .filtrar_region(lat_min=18, lat_max=20, lon_min=-105, lon_max=-103)
    .filtrar_magnitud(mag_min=3.0)
    .filtrar_profundidad(prof_max=100)
)
```

### Métodos de Conversión

```python
# Homogeneizar magnitudes a Mw
catalogo.homogeneizar_magnitudes(escala_destino='Mw')

# Ver distribución de tipos de magnitud
print(catalogo.distribucion_magnitudes())
# Output:
# Ml: 3,245 (59.8%)
# Mw: 1,876 (34.5%)
# mb: 311 (5.7%)
```

### Exportación

```python
# A CSV
catalogo.exportar_csv('catalogo_procesado.csv')

# A formato ISC
catalogo.exportar_isc('catalogo.isf')

# A GeoJSON
catalogo.exportar_geojson('catalogo.geojson')

# A formato QuakeML
catalogo.exportar_quakeml('catalogo.xml')
```

---

## Conversión de Magnitudes

### Relaciones Empíricas Implementadas

| Conversión | Ecuación | Referencia |
|------------|----------|------------|
| Ml → Mw | Mw = 0.884 × Ml + 0.667 | Hanks & Boore (1984) |
| mb → Mw | Mw = 1.182 × mb - 1.213 | Scordilis (2006) |
| Ms → Mw | Mw = 0.670 × Ms + 2.070 | Scordilis (2006) |
| Md → Ml | Ml = 0.950 × Md + 0.150 | Regional México |

### Uso

```python
from seismex.core import ConvertidorMagnitud

convertidor = ConvertidorMagnitud()

# Conversión simple
mw = convertidor.ml_a_mw(5.5)
print(f"Ml 5.5 → Mw {mw:.2f}")

# Conversión con incertidumbre
mw, sigma = convertidor.ml_a_mw(5.5, con_incertidumbre=True)
print(f"Mw = {mw:.2f} ± {sigma:.2f}")

# Conversión automática
mw = convertidor.convertir_a_mw(
    magnitud=5.5,
    tipo_origen='Ml'
)
```

### Agregar Relación Personalizada

```python
# Definir relación regional
convertidor.agregar_relacion(
    nombre='Ml_regional_Mw',
    coef_a=0.90,
    coef_b=0.55,
    sigma=0.15,
    referencia='Estudio regional Colima (2024)'
)

# Usar relación personalizada
mw = convertidor.convertir(5.5, relacion='Ml_regional_Mw')
```

---

## Preprocesamiento

### Limpieza de Datos

```python
from seismex.core import Preprocesador

prep = Preprocesador()

# Detectar duplicados
duplicados = prep.detectar_duplicados(
    catalogo,
    tolerancia_tiempo_seg=60,
    tolerancia_distancia_km=50,
    tolerancia_magnitud=0.3
)

print(f"Duplicados detectados: {len(duplicados)}")

# Eliminar duplicados
catalogo_limpio = prep.eliminar_duplicados(catalogo, duplicados)

# Detectar outliers
outliers = prep.detectar_outliers(
    catalogo,
    metodo='iqr',  # 'iqr', 'zscore', 'isolation_forest'
    columnas=['profundidad', 'magnitud']
)
```

### Declustering

```python
# Remover réplicas (Gardner & Knopoff, 1974)
catalogo_principal = prep.declustering(
    catalogo,
    metodo='gardner_knopoff',
    ventana_espacial='original',  # 'original', 'gruenthal'
    ventana_temporal='original'
)

print(f"Eventos principales: {len(catalogo_principal)}")
print(f"Réplicas removidas: {len(catalogo) - len(catalogo_principal)}")

# Método alternativo: Reasenberg
catalogo_principal = prep.declustering(
    catalogo,
    metodo='reasenberg',
    parametros={
        'tmin': 1.0,
        'tmax': 10.0,
        'xmeff': 1.5,
        'rfact': 10.0
    }
)
```

---

## Ejemplos

### Ejemplo 1: Pipeline Básico

```python
from seismex.core import CatalogoSismico, Preprocesador

# Cargar
catalogo = CatalogoSismico.desde_csv('ssn_2020_2024.csv', formato='ssn')

# Validar
valido, errores = catalogo.validar()
if not valido:
    raise ValueError(f"Catálogo inválido: {errores}")

# Filtrar región de interés
catalogo = catalogo.filtrar_region(
    lat_min=18.0, lat_max=20.5,
    lon_min=-105.0, lon_max=-102.5
)

# Homogeneizar magnitudes
catalogo.homogeneizar_magnitudes('Mw')

# Limpiar
prep = Preprocesador()
catalogo = prep.eliminar_duplicados(catalogo)
catalogo = prep.declustering(catalogo, metodo='gardner_knopoff')

# Resumen final
print(catalogo.resumen())
```

### Ejemplo 2: Combinar Catálogos

```python
# Cargar múltiples fuentes
ssn = CatalogoSismico.desde_csv('ssn.csv', formato='ssn')
isc = CatalogoSismico.desde_csv('isc.csv', formato='isc')
usgs = CatalogoSismico.desde_csv('usgs.csv', formato='usgs')

# Combinar
catalogo_combinado = CatalogoSismico.combinar(
    [ssn, isc, usgs],
    prioridad=['ssn', 'isc', 'usgs'],  # Orden de prioridad
    tolerancia_duplicados_km=50,
    tolerancia_duplicados_seg=60
)

print(f"Total eventos: {len(catalogo_combinado)}")
print(catalogo_combinado.resumen())
```

---

## Archivos del Módulo

```
seismex/core/
├── __init__.py           # Exportaciones del módulo
├── catalog.py            # Clase CatalogoSismico
├── evento.py             # Clase EventoSismico
├── magnitudes.py         # Conversión de magnitudes
├── preprocessing.py      # Preprocesamiento
├── validators.py         # Validadores de datos
└── README.md             # Este archivo
```

---

## Dependencias

```python
# Core
numpy>=1.21.0
pandas>=1.3.0
scipy>=1.7.0

# Opcional
obspy>=1.3.0        # Para formato QuakeML
geopandas>=0.10.0   # Para exportación GIS
```

---

## Estado de Desarrollo

| Componente | Estado | Prioridad |
|------------|--------|-----------|
| CatalogoSismico básico | ✅ Completo | Alta |
| Carga CSV/Excel | ✅ Completo | Alta |
| Conversión magnitudes | ✅ Completo | Alta |
| Filtrado espacial/temporal | ✅ Completo | Alta |
| Detección duplicados | 🔄 En desarrollo | Media |
| Declustering | 📋 Planificado | Media |
| Conectores API (SSN) | 📋 Planificado | Baja |
| Exportación QuakeML | 📋 Planificado | Baja |

---

## Véase También

- [`seismex.analysis`](../analysis/README.md) - Módulos de análisis
- [`seismex.data`](../data/README.md) - Conectores de datos
