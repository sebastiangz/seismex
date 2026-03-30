# 📡 seismex.data

Módulo de conectores de datos de SEISMEX. Proporciona interfaces para acceder a catálogos sísmicos de múltiples fuentes nacionales e internacionales.

---

## 📋 Contenido

- [Fuentes Disponibles](#fuentes-disponibles)
- [Conector SSN](#conector-ssn)
- [Conector ISC-GEM](#conector-isc-gem)
- [Conector USGS](#conector-usgs)
- [Conector GCMT](#conector-gcmt)
- [Gestión de Caché](#gestión-de-caché)
- [Actualización Automática](#actualización-automática)

---

## Estado: 📋 Planificado

Este módulo está en fase de diseño. Los conectores permitirán descargar y actualizar catálogos sísmicos automáticamente.

---

## Fuentes Disponibles

| Fuente | Código | Cobertura | Magnitud Mín | Estado |
|--------|--------|-----------|--------------|--------|
| **SSN** | `ssn` | México | ~2.0 | 📋 Planificado |
| **ISC-GEM** | `isc` | Global | ~5.0 (histórico) | 📋 Planificado |
| **USGS** | `usgs` | Global | ~2.5 | 📋 Planificado |
| **GCMT** | `gcmt` | Global (CMT) | ~5.0 | 📋 Planificado |
| **IRIS** | `iris` | Global | Variable | 📋 Planificado |

---

## Conector SSN

### Servicio Sismológico Nacional de México

```python
from seismex.data import ConectorSSN

# Inicializar conector
ssn = ConectorSSN(
    cache_dir='~/.seismex/cache/ssn',
    timeout=30
)

# Descargar catálogo por región
catalogo = ssn.descargar(
    fecha_inicio='2020-01-01',
    fecha_fin='2024-12-31',
    lat_min=18.0,
    lat_max=21.0,
    lon_min=-106.0,
    lon_max=-102.0,
    magnitud_min=3.0
)

print(f"Eventos descargados: {len(catalogo)}")
print(catalogo.resumen())
```

### Regiones Predefinidas

```python
# Usar región predefinida
catalogo_colima = ssn.descargar_region(
    region='colima',
    fecha_inicio='2020-01-01',
    fecha_fin='2024-12-31'
)

# Regiones disponibles
print(ssn.regiones_disponibles())
# ['colima', 'jalisco', 'michoacan', 'guerrero', 'oaxaca', 
#  'chiapas', 'cdmx', 'golfo', 'peninsula_yucatan', 'nacional']
```

### Descargar Catálogo Completo

```python
# Catálogo histórico completo de México
catalogo_historico = ssn.descargar_historico(
    desde_ano=1900,
    hasta_ano=2024,
    solo_instrumentales=False,  # Incluir históricos
    magnitud_min=5.0
)
```

### Actualización Incremental

```python
# Verificar última actualización
ultima = ssn.ultima_actualizacion()
print(f"Última actualización: {ultima}")

# Descargar solo eventos nuevos
nuevos = ssn.actualizar(catalogo_existente)
print(f"Nuevos eventos: {len(nuevos)}")

# Combinar
catalogo_actualizado = catalogo_existente.combinar(nuevos)
```

---

## Conector ISC-GEM

### International Seismological Centre - Global Earthquake Model

```python
from seismex.data import ConectorISC

isc = ConectorISC()

# Descargar catálogo ISC-GEM (histórico de alta calidad)
catalogo_isc = isc.descargar_gem(
    fecha_inicio='1900-01-01',
    fecha_fin='2020-12-31',
    lat_min=14.0,
    lat_max=33.0,
    lon_min=-118.0,
    lon_max=-86.0,
    magnitud_min=5.5
)

# Descargar del ISC Bulletin (más completo, menos revisado)
catalogo_bulletin = isc.descargar_bulletin(
    fecha_inicio='2020-01-01',
    fecha_fin='2024-12-31',
    tipo='reviewed'  # 'reviewed', 'all'
)
```

### Acceso a Mecanismos Focales

```python
# Descargar con mecanismos focales
catalogo_cmt = isc.descargar_con_mecanismos(
    fecha_inicio='2000-01-01',
    magnitud_min=5.0
)

# Acceder a tensores
for evento in catalogo_cmt:
    if evento.tiene_mecanismo:
        print(f"{evento.fecha}: Strike={evento.strike}°, "
              f"Dip={evento.dip}°, Rake={evento.rake}°")
```

---

## Conector USGS

### United States Geological Survey

```python
from seismex.data import ConectorUSGS

usgs = ConectorUSGS()

# API de ComCat
catalogo_usgs = usgs.descargar(
    fecha_inicio='2020-01-01',
    fecha_fin='2024-12-31',
    lat_min=14.0,
    lat_max=33.0,
    lon_min=-118.0,
    lon_max=-86.0,
    magnitud_min=4.0
)

# Búsqueda por círculo
catalogo_cerca = usgs.descargar_circulo(
    lat_centro=19.32,
    lon_centro=-103.64,
    radio_km=200,
    fecha_inicio='2020-01-01',
    magnitud_min=3.0
)
```

### ShakeMaps y Productos Derivados

```python
# Descargar ShakeMap para un evento específico
shakemap = usgs.descargar_shakemap(
    event_id='us7000abcd',
    producto='pga'  # 'pga', 'pgv', 'mmi', 'psa03', 'psa10', 'psa30'
)

# Guardar como GeoTIFF
shakemap.guardar('shakemap_pga.tif')

# Descargar DYFI (Did You Feel It)
dyfi = usgs.descargar_dyfi(event_id='us7000abcd')
```

---

## Conector GCMT

### Global Centroid Moment Tensor

```python
from seismex.data import ConectorGCMT

gcmt = ConectorGCMT()

# Descargar catálogo CMT
catalogo_cmt = gcmt.descargar(
    fecha_inicio='1976-01-01',  # Inicio del proyecto GCMT
    fecha_fin='2024-12-31',
    lat_min=14.0,
    lat_max=33.0,
    lon_min=-118.0,
    lon_max=-86.0
)

# Filtrar por tipo de falla
thrust = catalogo_cmt.filtrar_mecanismo(tipo='thrust')
normal = catalogo_cmt.filtrar_mecanismo(tipo='normal')
strike_slip = catalogo_cmt.filtrar_mecanismo(tipo='strike_slip')
```

### Análisis de Mecanismos

```python
# Estadísticas de mecanismos
stats = catalogo_cmt.estadisticas_mecanismos()
print(f"Thrust: {stats['thrust']}%")
print(f"Normal: {stats['normal']}%")
print(f"Strike-slip: {stats['strike_slip']}%")

# Diagramas de bola de playa
from seismex.visualization import DiagramasMecanismos

diag = DiagramasMecanismos(catalogo_cmt)
diag.graficar_mapa_mecanismos(guardar='mecanismos_mexico.png')
```

---

## Gestión de Caché

### Configuración de Caché

```python
from seismex.data import ConfiguracionCache

# Configurar caché global
cache = ConfiguracionCache(
    directorio='~/.seismex/cache',
    tamano_max_mb=1000,
    expiracion_dias=30,
    compresion=True
)

# Aplicar a conectores
ssn = ConectorSSN(cache=cache)
usgs = ConectorUSGS(cache=cache)
```

### Operaciones de Caché

```python
from seismex.data import GestorCache

gestor = GestorCache('~/.seismex/cache')

# Ver estado
print(gestor.estado())
# Tamaño: 245 MB
# Archivos: 127
# Última limpieza: 2024-01-15

# Limpiar caché expirado
gestor.limpiar_expirados()

# Limpiar todo
gestor.limpiar_todo()

# Precargar catálogos
gestor.precargar([
    {'fuente': 'ssn', 'region': 'colima', 'desde': '2010'},
    {'fuente': 'usgs', 'lat_min': 14, 'lat_max': 33, 'desde': '2010'}
])
```

---

## Actualización Automática

### Programar Actualizaciones

```python
from seismex.data import ActualizadorAutomatico

# Crear actualizador
actualizador = ActualizadorAutomatico(
    catalogos=['ssn', 'usgs'],
    directorio_salida='./datos/catalogos',
    intervalo_horas=24
)

# Configurar notificaciones
actualizador.configurar_notificaciones(
    email='usuario@ejemplo.com',
    en_nuevos_eventos=True,
    magnitud_minima_notificar=5.0
)

# Ejecutar (normalmente como servicio)
actualizador.iniciar()
```

### Script de Actualización (Cron)

```bash
# Archivo: scripts/actualizar_catalogos.py
#!/usr/bin/env python
"""Script para actualización programada de catálogos."""

from seismex.data import ConectorSSN, ConectorUSGS
from seismex.core import CatalogoSismico
import logging

logging.basicConfig(level=logging.INFO)

def main():
    # Cargar catálogo existente
    catalogo = CatalogoSismico.cargar('catalogos/mexico_completo.pkl')
    
    # Actualizar desde SSN
    ssn = ConectorSSN()
    nuevos_ssn = ssn.actualizar(catalogo)
    logging.info(f"SSN: {len(nuevos_ssn)} nuevos eventos")
    
    # Actualizar desde USGS
    usgs = ConectorUSGS()
    nuevos_usgs = usgs.actualizar(catalogo)
    logging.info(f"USGS: {len(nuevos_usgs)} nuevos eventos")
    
    # Combinar y guardar
    catalogo.agregar(nuevos_ssn)
    catalogo.agregar(nuevos_usgs)
    catalogo.eliminar_duplicados()
    catalogo.guardar('catalogos/mexico_completo.pkl')
    
    logging.info(f"Total eventos: {len(catalogo)}")

if __name__ == '__main__':
    main()
```

---

## Formatos de Datos

### Formatos de Entrada Soportados

| Formato | Extensión | Descripción |
|---------|-----------|-------------|
| CSV | .csv | Valores separados por comas |
| Excel | .xlsx, .xls | Microsoft Excel |
| QuakeML | .xml | Estándar internacional |
| ISF | .isf | ISC Seismic Format |
| ZMAP | .zmap | Formato ZMAP |
| JSON | .json | JavaScript Object Notation |
| Pickle | .pkl | Serialización Python |

### Mapeo de Columnas

```python
# Definir mapeo personalizado
mapeo = {
    'fecha': 'FECHA_UTC',
    'latitud': 'LAT',
    'longitud': 'LON',
    'profundidad': 'PROF_KM',
    'magnitud': 'MAG',
    'tipo_magnitud': 'TIPO_MAG',
    'fuente': 'AGENCIA'
}

catalogo = CatalogoSismico.desde_csv(
    'catalogo_custom.csv',
    mapeo_columnas=mapeo,
    formato_fecha='%Y-%m-%d %H:%M:%S'
)
```

---

## Archivos del Módulo

```
seismex/data/
├── __init__.py               # Exportaciones
├── base.py                   # Clase base ConectorBase
├── ssn.py                    # Conector SSN México
├── isc.py                    # Conector ISC-GEM
├── usgs.py                   # Conector USGS ComCat
├── gcmt.py                   # Conector GCMT
├── iris.py                   # Conector IRIS (planificado)
├── cache.py                  # Gestión de caché
├── updater.py                # Actualización automática
├── parsers/                  # Parsers de formatos
│   ├── __init__.py
│   ├── csv_parser.py
│   ├── quakeml_parser.py
│   ├── isf_parser.py
│   └── zmap_parser.py
└── README.md                 # Este archivo
```

---

## Dependencias

```python
# Core
requests>=2.25.0
pandas>=1.3.0

# Parsing
obspy>=1.3.0            # QuakeML
lxml>=4.6.0             # XML

# Caché
diskcache>=5.2.0

# Compresión
gzip
lzma
```

---

## API Reference

### ConectorBase (Clase Abstracta)

```python
class ConectorBase(ABC):
    """Clase base para conectores de datos sísmicos."""
    
    @abstractmethod
    def descargar(self, **kwargs) -> CatalogoSismico:
        """Descargar datos de la fuente."""
        pass
    
    @abstractmethod
    def actualizar(self, catalogo_existente) -> CatalogoSismico:
        """Descargar solo eventos nuevos."""
        pass
    
    def ultima_actualizacion(self) -> datetime:
        """Fecha de última actualización del caché."""
        pass
    
    def limpiar_cache(self):
        """Eliminar datos en caché."""
        pass
```

---

## Véase También

- [`seismex.core`](../core/README.md) - Clase CatalogoSismico
- [`seismex.analysis`](../analysis/README.md) - Análisis de catálogos
