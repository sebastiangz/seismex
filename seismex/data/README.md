# 📡 seismex.data

Módulo de conectores de datos de SEISMEX. Proporciona interfaces para acceder a catálogos sísmicos de múltiples fuentes nacionales e internacionales.

---

## 📋 Contenido

- [Fuentes Disponibles](#fuentes-disponibles)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Conector SSN](#conector-ssn)
- [Conector USGS](#conector-usgs)
- [Conector ISC](#conector-isc)
- [Conector IRIS/FDSN](#conector-irisfdsn)
- [Validación de Calidad](#validación-de-calidad)
- [Gestión de Caché](#gestión-de-caché)
- [Regiones Predefinidas](#regiones-predefinidas)

---

## Estado: ✅ Implementado

Este módulo está completamente implementado con conectores para SSN, USGS, ISC e IRIS/FDSN.

---

## Fuentes Disponibles

| Fuente | Código | Cobertura | Autenticación | Estado |
|--------|--------|-----------|---------------|--------|
| **SSN** | `ssn` | México | No requerida | ✅ Implementado |
| **USGS** | `usgs` | Global | Email opcional | ✅ Implementado |
| **ISC** | `isc` | Global (histórico) | No requerida | ✅ Implementado |
| **IRIS** | `iris` | Global (FDSN) | No requerida | ✅ Implementado |

### Prioridad de Fuentes

Para datos de México, la prioridad recomendada es:

1. **SSN** - Fuente principal y más completa para México
2. **USGS** - Excelente cobertura, API robusta
3. **ISC** - Ideal para datos históricos (ISC-GEM)
4. **IRIS** - Para mecanismos focales y datos FDSN

---

## Instalación

```bash
pip install seismex
```

### Dependencias opcionales

```bash
# Para el conector IRIS/FDSN (mecanismos focales)
pip install obspy
```

---

## Configuración

La configuración se almacena en `~/.seismex/config.yaml`:

```yaml
general:
  cache_enabled: true
  cache_expiration_days: 30
  timeout: 60
  max_retries: 3

ssn:
  enabled: true
  # Directorio para archivos descargados manualmente del SSN
  local_data_dir: ~/seismex_data/ssn
  request_delay: 2

usgs:
  enabled: true
  # Email OPCIONAL pero recomendado para mejor rate limit
  # Sin email: ~5 req/s | Con email: ~20 req/s
  email: ""  # tu@email.com

isc:
  enabled: true
  catalog: isc-gem

iris:
  enabled: true
  fdsn_client: IRIS
  include_focal_mechanisms: true

quality:
  auto_validate: true
  min_score: 70
```

### Variables de Entorno

Las variables con prefijo `SEISMEX_` tienen prioridad sobre el archivo YAML:

```bash
export SEISMEX_USGS_EMAIL="mi@email.com"
export SEISMEX_SSN_LOCAL_DATA_DIR="~/mis_datos/ssn"
```

### Configuración Programática

```python
from seismex.data import configure, get_config

# Configurar
configure(usgs_email='mi@email.com')
configure(ssn_local_data_dir='~/seismex_data/ssn')

# Ver configuración actual
print(get_config().show())
```

---

## Conector SSN

### Servicio Sismológico Nacional de México

El SSN es la **fuente prioritaria** para SEISMEX. Como el SSN no tiene API pública oficial, este conector implementa:

1. **Web scraping** del portal SSN (intenta primero)
2. **Fallback a archivos locales** en `~/seismex_data/ssn`

```python
from seismex.data import ConectorSSN, descargar_ssn, cargar_ssn_local

# Inicializar conector
ssn = ConectorSSN()

# Opción 1: Descargar (web scraping con fallback automático a local)
resultado = ssn.descargar(
    fecha_inicio='2024-01-01',
    fecha_fin='2024-12-31',
    region='colima',
    magnitud_min=3.5
)

# Opción 2: Cargar archivo local directamente
resultado = ssn.cargar_archivo('~/seismex_data/ssn/catalogo_2024.csv')

# Opción 3: Función de conveniencia
resultado = descargar_ssn(region='jalisco', magnitud_min=4.0)

# Acceder a los datos
if resultado.success:
    df = resultado.data
    print(f"Eventos descargados: {resultado.events_count}")
    print(f"Tiempo de descarga: {resultado.download_time:.2f}s")
    print(f"Desde caché: {resultado.from_cache}")
```

### Uso de Archivos Locales

Cuando el web scraping no está disponible:

```python
# Ver información del directorio local
print(ssn.info_directorio_local())

# Listar archivos disponibles
archivos = ssn.listar_archivos_locales()
for archivo in archivos:
    print(f"  • {archivo.name}")

# Cargar archivo específico con filtros
resultado = ssn.cargar_archivo(
    'catalogo_ssn_2024.csv',
    fecha_inicio='2024-06-01',
    magnitud_min=4.0
)
```

### Regiones Predefinidas

```python
# Descargar por región
resultado = ssn.descargar_region('colima', fecha_inicio='2024-01-01')

# Sismos significativos (M >= 5.0)
resultado = ssn.obtener_sismos_significativos(magnitud_min=5.0)

# Último año
resultado = ssn.obtener_ultimo_anio(region='nacional')
```

---

## Conector USGS

### United States Geological Survey

La API USGS es **pública y gratuita**. El email es **opcional pero recomendado**:

- **Sin email**: ~5 requests/segundo
- **Con email**: ~20 requests/segundo

```python
from seismex.data import ConectorUSGS, descargar_usgs, configure

# Configurar email para mejor rate limit (opcional)
configure(usgs_email='mi@email.com')

# Inicializar conector
usgs = ConectorUSGS()

# Descargar catálogo
resultado = usgs.descargar(
    fecha_inicio='2024-01-01',
    fecha_fin='2024-12-31',
    region='nacional',  # Región de México
    magnitud_min=4.0
)

# Función de conveniencia
resultado = descargar_usgs(region='colima', magnitud_min=3.5)

# Descargar específicamente para México
resultado = usgs.descargar_mexico(
    fecha_inicio='2024-01-01',
    magnitud_min=4.0
)

# Sismos recientes
resultado = usgs.descargar_recientes(dias=30, magnitud_min=4.0)
```

### Obtener Evento Específico

```python
# Información detallada de un evento
evento = usgs.obtener_evento('us7000abcd')
if evento is not None:
    print(f"Fecha: {evento['fecha']}")
    print(f"Magnitud: {evento['magnitud']} {evento['tipo_magnitud']}")
    print(f"Lugar: {evento['lugar']}")
```

### Verificar Conexión y Rate Limits

```python
# Verificar conectividad
if usgs.verificar_conexion():
    print("Conexión OK")

# Ver información de rate limits
print(usgs.info_rate_limit())
```

---

## Conector ISC

### International Seismological Centre

El ISC proporciona catálogos de alta calidad, especialmente el **ISC-GEM** para sismos históricos significativos (M ≥ 5.5 desde 1904).

```python
from seismex.data import ConectorISC, descargar_isc, descargar_isc_gem_mexico

# Catálogos disponibles
isc = ConectorISC(catalogo='isc-gem')  # 'isc-gem', 'reviewed', 'comprehensive'
print(isc.catalogos_disponibles())

# Descargar catálogo ISC-GEM histórico para México
resultado = isc.descargar(
    fecha_inicio='1900-01-01',
    fecha_fin='2024-12-31',
    region='nacional',
    magnitud_min=6.0
)

# Función de conveniencia para ISC-GEM México
resultado = descargar_isc_gem_mexico(magnitud_min=6.5)

# Método especializado para históricos
resultado = isc.descargar_gem_historico(
    region='nacional',
    magnitud_min=7.0
)
```

---

## Conector IRIS/FDSN

### Federation of Digital Seismograph Networks (via ObsPy)

Este conector usa ObsPy para acceder a múltiples servicios FDSN internacionales.

**Requiere**: `pip install obspy`

```python
from seismex.data import ConectorIRIS, descargar_iris, obtener_mecanismos_focales

# Inicializar (cliente IRIS por defecto)
iris = ConectorIRIS()

# Ver clientes FDSN disponibles
print(ConectorIRIS.clientes_disponibles())
# IRIS, USGS, ISC, EMSC, GFZ, INGV, RESIF, ORFEUS, NCEDC, SCEDC, TEXNET...

# Descargar catálogo
resultado = iris.descargar(
    fecha_inicio='2024-01-01',
    region='nacional',
    magnitud_min=4.5
)

# Cambiar cliente FDSN
iris.cambiar_cliente('EMSC')  # European-Mediterranean Seismological Centre
```

### Mecanismos Focales

```python
# Descargar con mecanismos focales (generalmente M >= 5.5)
resultado = iris.descargar_con_mecanismos(
    fecha_inicio='2020-01-01',
    region='nacional',
    magnitud_min=5.5
)

# Los datos incluyen: strike, dip, rake, momento_escalar
df = resultado.data
print(df[['fecha', 'magnitud', 'strike', 'dip', 'rake']])

# Función de conveniencia
resultado = obtener_mecanismos_focales(
    region='nacional',
    magnitud_min=5.5
)
```

### Verificar Servicio

```python
# Verificar conexión
if iris.verificar_conexion():
    print("Servicio FDSN disponible")

# Información del servicio actual
print(iris.info_servicio())
```

---

## Validación de Calidad

El módulo incluye validación automática de catálogos con score de calidad 0-100.

```python
from seismex.data import validar_catalogo, validacion_rapida, QualityValidator

# Validación completa
reporte = validar_catalogo(resultado.data)

print(f"Score de calidad: {reporte.score}/100")
print(f"Eventos válidos: {reporte.valid_events}/{reporte.total_events}")
print(reporte)

# Validación rápida (solo score)
score = validacion_rapida(resultado.data)
print(f"Score: {score}")

# Exportar reporte
reporte.exportar_json('reporte_calidad.json')

# Validador personalizado
validator = QualityValidator(config=get_config().quality)
reporte = validator.validar(df)
```

### Checks de Calidad

- Columnas requeridas (fecha, latitud, longitud, magnitud)
- Valores faltantes
- Rangos válidos (coordenadas, profundidad, magnitud)
- Detección de duplicados
- Detección de outliers
- Consistencia temporal

---

## Gestión de Caché

### Configuración de Caché

El caché se almacena en `~/.seismex/cache` con compresión gzip.

```python
from seismex.data import get_cache, clear_cache, estado_cache

# Ver estado del caché
print(estado_cache())

# Obtener gestor de caché
cache = get_cache()
stats = cache.stats()
print(f"Entradas: {stats.total_entries}")
print(f"Tamaño: {stats.total_size_mb:.2f} MB")
print(f"Hits: {stats.total_hits}")

# Limpiar caché expirado
cache.clean_expired()

# Limpiar caché de una fuente específica
cache.clean_source('ssn')

# Limpiar todo
clear_cache()
```

### Uso de Caché en Conectores

```python
# Deshabilitar caché para una consulta
ssn = ConectorSSN(usar_cache=False)

# Verificar si datos vienen de caché
resultado = ssn.descargar(region='colima')
if resultado.from_cache:
    print("Datos obtenidos desde caché")
```

---

## Regiones Predefinidas

```python
from seismex.data import REGIONES_MEXICO

# Ver todas las regiones disponibles
for nombre, limites in REGIONES_MEXICO.items():
    print(f"{nombre}: lat [{limites['lat_min']}, {limites['lat_max']}], "
          f"lon [{limites['lon_min']}, {limites['lon_max']}]")
```

### Regiones Disponibles

| Región | Descripción |
|--------|-------------|
| `nacional` | Todo México |
| `colima` | Estado de Colima y alrededores |
| `jalisco` | Estado de Jalisco |
| `michoacan` | Estado de Michoacán |
| `guerrero` | Estado de Guerrero |
| `oaxaca` | Estado de Oaxaca |
| `chiapas` | Estado de Chiapas |
| `cdmx` | Ciudad de México y área metropolitana |
| `veracruz` | Estado de Veracruz |
| `baja_california` | Península de Baja California |
| `golfo_california` | Golfo de California |
| `peninsula_yucatan` | Península de Yucatán |

---

## Formato de Datos Estándar

Todos los conectores normalizan los datos al mismo formato:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | datetime | Fecha y hora UTC del evento |
| `latitud` | float | Latitud del epicentro |
| `longitud` | float | Longitud del epicentro |
| `profundidad_km` | float | Profundidad en kilómetros |
| `magnitud` | float | Magnitud del evento |
| `tipo_magnitud` | str | Tipo de magnitud (Mw, ML, mb, etc.) |
| `fuente` | str | Fuente de los datos (SSN, USGS, etc.) |
| `id_evento` | str | Identificador único |
| `lugar` | str | Descripción del lugar |
| `incertidumbre_h` | float | Incertidumbre horizontal (km) |
| `incertidumbre_z` | float | Incertidumbre en profundidad (km) |
| `incertidumbre_m` | float | Incertidumbre en magnitud |
| `rms` | float | RMS del ajuste |
| `gap` | float | Gap azimutal (grados) |
| `nst` | int | Número de estaciones |

---

## Archivos del Módulo

```
seismex/data/
├── __init__.py          # Exportaciones y funciones de alto nivel
├── config.py            # Sistema de configuración YAML
├── cache.py             # Gestión de caché con compresión
├── base.py              # Clase base ConectorBase y regiones
├── quality.py           # Validación y reportes de calidad
├── ssn.py               # Conector SSN (prioridad para México)
├── usgs.py              # Conector USGS
├── isc.py               # Conector ISC/ISC-GEM
├── iris.py              # Conector IRIS/FDSN (via ObsPy)
└── README.md            # Este archivo
```

---

## Dependencias

```
# Core
pandas>=1.3.0
numpy>=1.20.0
pyyaml>=5.4.0
requests>=2.25.0
beautifulsoup4>=4.9.0

# Opcional (para IRIS/FDSN)
obspy>=1.3.0
```

---

## API Reference

### Funciones de Alto Nivel

```python
from seismex.data import (
    # Función unificada
    descargar,              # descargar(fuente, **kwargs)
    descargar_mexico,       # descargar_mexico(fuente, magnitud_min)
    
    # SSN (prioridad)
    descargar_ssn,          # descargar_ssn(**kwargs)
    cargar_ssn_local,       # cargar_ssn_local(filepath, **filtros)
    
    # USGS
    descargar_usgs,         # descargar_usgs(**kwargs)
    descargar_usgs_mexico,  # descargar_usgs_mexico(fecha_inicio, magnitud_min)
    
    # ISC
    descargar_isc,          # descargar_isc(**kwargs)
    descargar_isc_gem_mexico,  # descargar_isc_gem_mexico(magnitud_min)
    
    # IRIS/FDSN
    descargar_iris,         # descargar_iris(**kwargs)
    descargar_fdsn,         # descargar_fdsn(cliente, **kwargs)
    obtener_mecanismos_focales,  # obtener_mecanismos_focales(region, magnitud_min)
    
    # Validación
    validar_catalogo,       # validar_catalogo(df) -> QualityReport
    validacion_rapida,      # validacion_rapida(df) -> float
    
    # Configuración
    get_config,             # get_config() -> SeismexConfig
    configure,              # configure(**kwargs)
    
    # Caché
    get_cache,              # get_cache() -> CacheManager
    clear_cache,            # clear_cache()
    estado_cache,           # estado_cache() -> str
    info_conectores,        # info_conectores() -> str
)
```

### Clases Principales

```python
from seismex.data import (
    # Conectores
    ConectorSSN,
    ConectorUSGS,
    ConectorISC,
    ConectorIRIS,
    
    # Base
    ConectorBase,
    QueryParams,
    DownloadResult,
    
    # Configuración
    SeismexConfig,
    ConfigManager,
    
    # Caché
    CacheManager,
    CacheEntry,
    
    # Calidad
    QualityValidator,
    QualityReport,
    
    # Constantes
    CATALOG_COLUMNS,
    REGIONES_MEXICO,
)
```

---

## Véase También

- [`seismex.core`](../core/README.md) - Clase CatalogoSismico
- [`seismex.analysis`](../analysis/README.md) - Análisis de catálogos
- [`seismex.visualization`](../visualization/README.md) - Visualización
