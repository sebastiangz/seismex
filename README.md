# 🌋 SEISMEX - Sistema de Análisis Sísmico para México

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Development](https://img.shields.io/badge/status-development-orange.svg)]()

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
| **Isosistas** | Mapas de intensidad sísmica | 🔄 En desarrollo |
| **PSHA** | Análisis Probabilístico de Peligro Sísmico | 📋 Planificado |
| **Optimización GA** | Algoritmos genéticos multiobjetivo (NSGA-II) | 📋 Planificado |

### Fuentes de Datos Soportadas

- **SSN** - Servicio Sismológico Nacional de México
- **ISC-GEM** - International Seismological Centre
- **USGS** - United States Geological Survey
- **GCMT** - Global Centroid Moment Tensor

### Capacidades de Visualización

- Secciones horizontales y verticales de ESD
- Mapas interactivos con Folium
- Exportación a GeoTIFF/GeoJSON
- Integración con Google Earth Engine (planificado)

---

## 🏗 Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Folium    │  │  Matplotlib │  │  Google Earth Engine    │ │
│  │   (Mapas)   │  │  (Gráficos) │  │  (Visualización Web)    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE ANÁLISIS                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐ │
│  │     ESD     │  │  Isosistas  │  │   PSHA   │  │ Gutenberg │ │
│  │ Del Pezzo  │  │   IPE/GMPE  │  │ Cornell  │  │  Richter  │ │
│  └─────────────┘  └─────────────┘  └──────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE OPTIMIZACIÓN                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      NSGA-II                             │   │
│  │  Funciones Objetivo: Costo | Impacto | Riesgo | Social  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE DATOS                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │     SSN     │  │   ISC-GEM   │  │         USGS            │ │
│  │  (México)   │  │  (Global)   │  │       (Global)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
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
from seismex.visualization import VisualizadorESD

# 1. Cargar catálogo sísmico
catalogo = CatalogoSismico.desde_csv('catalogo_ssn.csv')
catalogo.validar()
print(catalogo.resumen())

# 2. Configurar análisis ESD
config = ConfiguracionESD(
    tamano_celda_km=10.0,        # Celdas de 10×10×10 km
    paso_deslizamiento_km=2.5,   # Paso de 2.5 km
    magnitud_minima=2.4,         # Magnitud mínima
    profundidad_maxima_km=150.0  # Profundidad máxima
)

# 3. Calcular ESD
calculadora = CalculadoraESD(config)
resultado = calculadora.calcular_esd(catalogo)

# 4. Visualizar
viz = VisualizadorESD(resultado)
viz.graficar_secciones_horizontales([10, 30, 50, 70])
viz.exportar_geotiff('esd_colima.tif', profundidad_km=30)
```

### Análisis Gutenberg-Richter

```python
from seismex.analysis import AnalizadorGutenbergRichter

# Calcular parámetros G-R
gr = AnalizadorGutenbergRichter()
resultado_gr = gr.analizar(catalogo)

print(f"Mc = {resultado_gr.mc:.2f}")
print(f"b = {resultado_gr.b_value:.3f} ± {resultado_gr.b_error:.3f}")
print(f"a = {resultado_gr.a_value:.3f} ± {resultado_gr.a_error:.3f}")

# Graficar
gr.graficar_fmd(guardar='gutenberg_richter.png')
```

---

## 📦 Módulos

### `seismex.core`
Funcionalidades base: catálogos sísmicos, conversión de magnitudes, preprocesamiento.

### `seismex.analysis`
Módulos de análisis: ESD, Gutenberg-Richter, isosistas, PSHA.

### `seismex.visualization`
Visualización: gráficos Matplotlib, mapas Folium, exportación GeoTIFF.

### `seismex.optimization`
Optimización multiobjetivo: NSGA-II, funciones objetivo, restricciones.

### `seismex.data`
Conectores de datos: SSN, ISC-GEM, USGS.

### `seismex.utils`
Utilidades: cálculos geodésicos, I/O, validadores.

Consulta los README individuales en cada subcarpeta para documentación detallada.

---

## 📁 Estructura del Proyecto

```
seismex/
├── seismex/                    # Paquete principal
│   ├── core/                   # Funcionalidades base
│   ├── analysis/               # Módulos de análisis
│   ├── visualization/          # Visualización
│   ├── optimization/           # Optimización GA
│   ├── data/                   # Conectores de datos
│   └── utils/                  # Utilidades
├── docs/                       # Documentación
│   ├── api/                    # Documentación API
│   ├── tutorials/              # Tutoriales
│   └── examples/               # Ejemplos
├── tests/                      # Pruebas
│   ├── unit/                   # Pruebas unitarias
│   └── integration/            # Pruebas de integración
├── data/                       # Datos
│   ├── raw/                    # Datos crudos
│   ├── processed/              # Datos procesados
│   └── catalogs/               # Catálogos sísmicos
├── outputs/                    # Salidas
│   ├── maps/                   # Mapas generados
│   ├── reports/                # Reportes
│   └── exports/                # Exportaciones GIS
├── notebooks/                  # Jupyter notebooks
├── scripts/                    # Scripts de utilidad
├── resources/                  # Recursos
│   ├── shapefiles/             # Shapefiles de México
│   ├── colormaps/              # Paletas de colores
│   └── config/                 # Configuraciones
├── README.md                   # Este archivo
├── requirements.txt            # Dependencias pip
├── environment.yml             # Entorno conda
├── setup.py                    # Configuración de instalación
├── pyproject.toml              # Configuración del proyecto
├── CONTRIBUTING.md             # Guía de contribución
├── LICENSE                     # Licencia MIT
└── .gitignore                  # Archivos ignorados
```

---

## 📚 Ejemplos

### Notebook: Análisis ESD de la región de Colima

```bash
jupyter notebook notebooks/01_analisis_esd_colima.ipynb
```

### Script: Descarga automática del catálogo SSN

```bash
python scripts/descargar_catalogo_ssn.py --region colima --desde 2000 --hasta 2024
```

### Pipeline completo

```bash
python scripts/pipeline_analisis.py --config resources/config/colima.yaml
```

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor lee [CONTRIBUTING.md](CONTRIBUTING.md) para detalles sobre nuestro código de conducta y el proceso para enviar pull requests.

### Desarrollo local

```bash
# Clonar
git clone https://github.com/tu-usuario/seismex.git
cd seismex

# Crear entorno
conda env create -f environment.yml
conda activate seismex

# Instalar en modo desarrollo
pip install -e ".[dev]"

# Ejecutar pruebas
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
- Aki, K. (1965). "Maximum likelihood estimate of b in the formula log N = a - bM and its confidence limits." *Bulletin of the Earthquake Research Institute*, 43, 237-239.
- Woessner, J., & Wiemer, S. (2005). "Assessing the quality of earthquake catalogues: Estimating the magnitude of completeness and its uncertainty." *BSSA*, 95(2), 684-698.

### PSHA
- Cornell, C.A. (1968). "Engineering seismic risk analysis." *BSSA*, 58(5), 1583-1606.

### Optimización Multiobjetivo
- Deb, K., et al. (2002). "A fast and elitist multiobjective genetic algorithm: NSGA-II." *IEEE Transactions on Evolutionary Computation*, 6(2), 182-197.

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
