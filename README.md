# 🌋 SEISMEX - Sistema de Análisis Sísmico para México

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Active](https://img.shields.io/badge/status-active-brightgreen.svg)]()

**SEISMEX** es una plataforma integral para el análisis de riesgo sísmico en México, que integra metodologías avanzadas de sismología, optimización multiobjetivo y visualización geoespacial.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Instalación](#-instalación)
- [Uso Rápido](#-uso-rápido)
- [Módulos](#-módulos)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Ejemplos](#-ejemplos)
- [Contribuir](#-contribuir)
- [Licencia](#-licencia)
- [Referencias](#-referencias)

---

## ✨ Características

### Metodologías Implementadas

| Metodología | Descripción | Estado |
|-------------|-------------|--------|
| **ESD** | Energy Space Density - Densidad de energía sísmica 3D | ✅ Completo |
| **Gutenberg-Richter** | Análisis de valor-b y magnitud de completitud | ✅ Completo |
| **Isosistas** | Mapas de intensidad sísmica (GMPEs/IPEs) | ✅ Completo |
| **Modelos de Fuentes** | Fuentes de área, falla y puntuales | ✅ Completo |
| **PSHA** | Análisis Probabilístico de Peligro Sísmico | ✅ Completo |
| **Optimización NSGA-II** | Algoritmos genéticos multiobjetivo | ✅ Completo |

### Fuentes de Datos Soportadas

- **SSN** - Servicio Sismológico Nacional de México
- **ISC-GEM** - International Seismological Centre
- **USGS** - United States Geological Survey
- **IRIS/FDSN** - Mecanismos focales

### Capacidades de Visualización

- Secciones horizontales y verticales de ESD
- Mapas interactivos con Folium
- Exportación a GeoTIFF/GeoJSON/Shapefile
- Integración con Google Earth Engine

---

## 🏗 Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Folium    │  │  Matplotlib │  │  Google Earth Engine    │  │
│  │   (Mapas)   │  │  (Gráficos) │  │  (Visualización Web)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE ANÁLISIS                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐  │
│  │     ESD     │  │  Isosistas  │  │   PSHA   │  │ Gutenberg │  │
│  │  Del Pezzo  │  │   IPE/GMPE  │  │ Cornell  │  │  Richter  │  │
│  └─────────────┘  └─────────────┘  └──────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE OPTIMIZACIÓN                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      NSGA-II                            │    │
│  │  Funciones Objetivo: Costo | Impacto | Riesgo | Social  │    │
│  │  Restricciones: Uso suelo | Pendiente | Fallas | ANPs   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE DATOS                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐  │
│  │     SSN     │  │   ISC-GEM   │  │   USGS   │  │   IRIS    │  │
│  │  (México)   │  │  (Global)   │  │ (Global) │  │  (FDSN)   │  │
│  └─────────────┘  └─────────────┘  └──────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Instalación

### Requisitos

- Python 3.10+
- NumPy, Pandas, SciPy
- Matplotlib, Folium
- GDAL (opcional, para GeoTIFF)

### Desde pip (próximamente)

```bash
pip install seismex
```

### Desde código fuente

```bash
git clone https://github.com/sebastiangz/seismex.git
cd seismex
pip install -e .
```

### Con conda

```bash
conda env create -f environment.yml
conda activate seismex
```

---

## 🎯 Uso Rápido

### Análisis ESD

```python
from seismex.core import CatalogoSismico
from seismex.analysis import CalculadoraESD, ConfiguracionESD

# Cargar catálogo
catalogo = CatalogoSismico.desde_csv('catalogo_ssn.csv')

# Configurar y calcular ESD
config = ConfiguracionESD(tamano_celda_km=10.0, magnitud_minima=2.4)
calculadora = CalculadoraESD(config)
resultado = calculadora.calcular_esd(catalogo)

# Exportar
resultado.exportar_geotiff('esd_colima.tif', profundidad_km=30)
```

### Análisis Gutenberg-Richter

```python
from seismex.analysis import AnalizadorGutenbergRichter

gr = AnalizadorGutenbergRichter()
resultado = gr.analizar(catalogo)
print(f"Mc = {resultado.mc:.2f}, b = {resultado.b_value:.3f}")
```

### Generación de Isosistas

```python
from seismex.analysis.isoseismal import GeneradorIsosistas

gen = GeneradorIsosistas(ipe='cenapred_2006', gmpe='garcia_2005')
isosistas = gen.calcular(
    latitud=19.32, longitud=-103.64,
    profundidad_km=15, magnitud=6.5
)
isosistas.graficar()
isosistas.exportar_geojson('isosistas_m65.geojson')
```

### Análisis PSHA

```python
from seismex.analysis.psha import crear_analizador_mexico

# Analizador preconfigurado para México
psha = crear_analizador_mexico(vs30=400)

# Curva de peligro
curva = psha.calcular_curva_peligro(sitio=(19.4, -99.1))
pga_475 = curva.intensidad_para_periodo_retorno(475)
print(f"PGA 475 años: {pga_475:.3f} g")

# Mapa de peligro
mapa = psha.calcular_mapa_peligro(
    region={'lat': (14, 20), 'lon': (-105, -95)},
    periodo_retorno=475,
    resolucion=0.5
)
mapa.exportar_geotiff('peligro_mexico_475.tif')
```

### Optimización de Ubicación (NSGA-II)

```python
from seismex.optimization import (
    OptimizadorNSGAII, ConfiguracionNSGAII,
    objetivo_riesgo_esd, objetivo_costo_construccion,
    restriccion_distancia_minima
)

# Configurar optimizador
config = ConfiguracionNSGAII(
    n_generaciones=100,
    tamano_poblacion=200,
    n_sitios=3
)
optimizador = OptimizadorNSGAII(config)

# Agregar objetivos y restricciones
optimizador.agregar_objetivo(objetivo_riesgo_esd(esd_grid, bounds))
optimizador.agregar_objetivo(objetivo_costo_construccion())
optimizador.agregar_restriccion(restriccion_distancia_minima(distancia_km=5))

# Optimizar
resultado = optimizador.optimizar(region=[(18, 21), (-105, -102)])
resultado.graficar_pareto()
resultado.exportar_geojson('ubicaciones_optimas.geojson')
```

---

## 📦 Módulos

### `seismex.core`
Funcionalidades base: catálogos sísmicos, conversión de magnitudes, preprocesamiento.

### `seismex.analysis`
Módulos de análisis sísmico:

| Módulo | Descripción | Estado |
|--------|-------------|--------|
| `esd.py` | Energy Space Density | ✅ |
| `gutenberg_richter.py` | Análisis valor-b y Mc | ✅ |
| `isoseismal.py` | Isosistas con GMPEs/IPEs | ✅ |
| `source_models.py` | Modelos de fuentes sísmicas | ✅ |
| `psha.py` | PSHA Cornell-McGuire | ✅ |

### `seismex.optimization`
Optimización multiobjetivo NSGA-II:

| Módulo | Descripción | Estado |
|--------|-------------|--------|
| `genetic.py` | Motor NSGA-II | ✅ |
| `objectives.py` | 9 funciones objetivo | ✅ |
| `constraints.py` | 11 restricciones | ✅ |

### `seismex.visualization`
Visualización: gráficos Matplotlib, mapas Folium, exportación GeoTIFF.

### `seismex.data`
Conectores de datos: SSN, ISC-GEM, USGS, IRIS/FDSN.

### `seismex.utils`
Utilidades: cálculos geodésicos, I/O, validadores.

---

## 📁 Estructura del Proyecto

```
seismex/
├── seismex/                    # Paquete principal
│   ├── core/                   # Funcionalidades base
│   │   ├── catalog.py          # Manejo de catálogos
│   │   └── __init__.py
│   ├── analysis/               # Módulos de análisis
│   │   ├── esd.py              # Energy Space Density
│   │   ├── gutenberg_richter.py
│   │   ├── isoseismal.py       # Isosistas GMPEs/IPEs
│   │   ├── source_models.py    # Modelos de fuentes
│   │   ├── psha.py             # PSHA
│   │   └── README.md
│   ├── optimization/           # Optimización NSGA-II
│   │   ├── genetic.py          # Motor NSGA-II
│   │   ├── objectives.py       # Funciones objetivo
│   │   ├── constraints.py      # Restricciones
│   │   └── README.md
│   ├── visualization/          # Visualización
│   │   ├── plotter.py
│   │   ├── interactive.py
│   │   └── gis_export.py
│   ├── data/                   # Conectores de datos
│   │   ├── ssn_connector.py
│   │   ├── usgs_connector.py
│   │   ├── isc_connector.py
│   │   └── iris_connector.py
│   └── utils/                  # Utilidades
│       ├── geo.py
│       ├── io.py
│       └── validators.py
├── tests/                      # Pruebas
├── notebooks/                  # Jupyter notebooks
├── docs/                       # Documentación
├── README.md
├── requirements.txt
├── environment.yml
├── setup.py
├── pyproject.toml
├── CONTRIBUTING.md
└── LICENSE
```

---

## 📚 Ejemplos

### Pipeline Completo

```python
from seismex.core import CatalogoSismico
from seismex.analysis import AnalizadorGutenbergRichter, CalculadoraESD, ConfiguracionESD
from seismex.analysis.isoseismal import GeneradorIsosistas
from seismex.analysis.source_models import ModeloFuentes
from seismex.analysis.psha import AnalizadorPSHA

# 1. Cargar catálogo
catalogo = CatalogoSismico.desde_csv('ssn_colima.csv')

# 2. Análisis Gutenberg-Richter
gr = AnalizadorGutenbergRichter()
resultado_gr = gr.analizar(catalogo)
print(f"Mc = {resultado_gr.mc:.2f}, b = {resultado_gr.b_value:.3f}")

# 3. Crear modelo de fuentes calibrado
modelo = ModeloFuentes(nombre="Colima")
modelo.agregar_zona_area(
    nombre="Zona Colima",
    poligono=[(18.5, -105.0), (20.0, -104.0), (20.0, -102.5), (18.5, -103.0)],
    a_value=resultado_gr.a_value,
    b_value=resultado_gr.b_value,
    mmin=resultado_gr.mc,
    mmax=8.0
)

# 4. Análisis PSHA
from seismex.analysis.isoseismal import GMPEGarcia2005
psha = AnalizadorPSHA(fuentes=modelo, vs30=400)
psha.agregar_gmpe(GMPEGarcia2005(), peso=1.0)

curva = psha.calcular_curva_peligro(sitio=(19.3, -103.7))
print(f"PGA 475 años: {curva.intensidad_para_periodo_retorno(475):.3f} g")

# 5. Desagregación
desag = psha.desagregar(sitio=(19.3, -103.7), nivel_intensidad=0.2)
print(f"Magnitud modal: {desag.magnitud_modal:.1f}")
print(f"Distancia modal: {desag.distancia_modal:.0f} km")
```

### Notebooks disponibles

```bash
jupyter notebook notebooks/01_analisis_esd_colima.ipynb
jupyter notebook notebooks/02_psha_mexico.ipynb
jupyter notebook notebooks/03_optimizacion_ubicacion.ipynb
```

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor lee [CONTRIBUTING.md](CONTRIBUTING.md) para detalles.

### Desarrollo local

```bash
git clone https://github.com/sebastiangz/seismex.git
cd seismex
conda env create -f environment.yml
conda activate seismex
pip install -e ".[dev]"
pytest tests/
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver [LICENSE](LICENSE) para detalles.

---

## 📖 Referencias

### Metodología ESD
- Del Pezzo, E., et al. (2024). "Energy Space Density: A new approach to seismic hazard assessment." *Geophysical Research Letters*.

### Gutenberg-Richter
- Aki, K. (1965). "Maximum likelihood estimate of b in the formula log N = a - bM." *BERI*, 43, 237-239.
- Woessner, J., & Wiemer, S. (2005). "Assessing the quality of earthquake catalogues." *BSSA*, 95(2), 684-698.

### GMPEs / IPEs
- García, D., et al. (2005). "A predictive ground motion model for Mexico." *GJI*, 162(3), 908-924.
- Zhao, J.X., et al. (2006). "Attenuation relations of strong ground motion in Japan." *BSSA*, 96(3), 898-913.
- Allen, T.I., et al. (2012). "Intensity attenuation for active crustal regions." *J. Seismology*, 16, 409-433.

### PSHA
- Cornell, C.A. (1968). "Engineering seismic risk analysis." *BSSA*, 58(5), 1583-1606.
- McGuire, R.K. (2004). "Seismic Hazard and Risk Analysis." *EERI Monograph*.

### Modelos de Fuentes
- Youngs, R.R. & Coppersmith, K.J. (1985). "Implications of fault slip rates and earthquake recurrence models." *BSSA*, 75(4), 939-964.
- Wells, D.L. & Coppersmith, K.J. (1994). "New empirical relationships among magnitude, rupture length, rupture width, rupture area, and surface displacement." *BSSA*, 84(4), 974-1002.

### Optimización Multiobjetivo
- Deb, K., et al. (2002). "A fast and elitist multiobjective genetic algorithm: NSGA-II." *IEEE Trans. Evolutionary Computation*, 6(2), 182-197.

---

## 👥 Autores

- **sgz** - *Desarrollo inicial* - [GitHub](https://github.com/sebastiangz)
- **mbg** - *Desarrollo funcional*

## 🙏 Agradecimientos

- Servicio Sismológico Nacional de México (SSN)
- Centro de Geociencias, UNAM
- Colaboradores del proyecto

---

<p align="center">
  <strong>SEISMEX</strong> - Análisis Sísmico para México 🇲🇽
</p>
