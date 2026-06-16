# 📊 seismex.analysis

Módulo de análisis sísmico de SEISMEX. Contiene implementaciones de metodologías para evaluación de peligro y riesgo sísmico.

---

## 📋 Contenido

- [Módulos Disponibles](#módulos-disponibles)
- [ESD - Energy Space Density](#esd---energy-space-density)
- [Gutenberg-Richter](#gutenberg-richter)
- [Isosistas](#isosistas)
- [PSHA](#psha)
- [Ejemplos Integrados](#ejemplos-integrados)

---

## Módulos Disponibles

| Módulo | Descripción | Estado |
|--------|-------------|--------|
| `esd` | Energy Space Density (Del Pezzo et al.) | ✅ Completo |
| `gutenberg_richter` | Análisis de valor-b y Mc | ✅ Completo |
| `isoseismal` | Mapas de isosistas (GMPEs/IPEs) | ✅ Completo |
| `psha` | Probabilistic Seismic Hazard Analysis | 📋 Planificado |
| `source_models` | Modelos de fuentes sísmicas | 📋 Planificado |

---

## ESD - Energy Space Density

Implementación de la metodología **Energy Space Density** basada en Del Pezzo et al. (2024), publicada en Geophysical Research Letters.

### Fundamento Teórico

La ESD representa la densidad de energía sísmica liberada en un volumen tridimensional:

```
ESD(x,y,z) = Σ E_i × K(d_i, σ)
```

Donde:
- `E_i = 10^(1.5 × Mw + 11.8)` ergios (energía del evento i)
- `K(d, σ)` = kernel gaussiano 3D
- `d_i` = distancia al centro de la celda

### Clases

```python
from seismex.analysis.esd import (
    ConfiguracionESD,
    CalculadoraESD,
    ResultadoESD
)
```

#### ConfiguracionESD

```python
config = ConfiguracionESD(
    # Parámetros de malla
    tamano_celda_km=10.0,           # Tamaño de celda (km)
    paso_deslizamiento_km=2.5,      # Paso de deslizamiento (km)
    
    # Filtros
    magnitud_minima=2.4,            # Magnitud mínima (Mc)
    profundidad_maxima_km=150.0,    # Profundidad máxima
    
    # Suavizado
    suavizado_horizontal=1.0,       # Factor de suavizado XY
    suavizado_vertical=0.5,         # Factor de suavizado Z
    suavizado_rms=0.5,              # RMS para profundidad
    
    # Normalización
    normalizar=True,                # Normalizar por máximo
    escala_log=True                 # Usar escala logarítmica
)
```

#### CalculadoraESD

```python
from seismex.analysis import CalculadoraESD
from seismex.core import CatalogoSismico

# Cargar datos
catalogo = CatalogoSismico.desde_csv('catalogo.csv')

# Crear calculadora
calculadora = CalculadoraESD(config)

# Calcular ESD
resultado = calculadora.calcular_esd(catalogo)

# Información del resultado
print(f"Energía total: {resultado.energia_total:.2e} ergios")
print(f"Dimensiones malla: {resultado.dimensiones}")
print(f"Rango log10(ESD): {resultado.esd_min:.2f} a {resultado.esd_max:.2f}")
```

#### Obtener Secciones

```python
# Sección horizontal (mapa a profundidad fija)
X, Y, ESD = calculadora.obtener_seccion_horizontal(profundidad_km=30)

# Sección vertical N-S (perfil latitudinal)
Y, Z, ESD = calculadora.obtener_seccion_vertical_ns(longitud=-103.5)

# Sección vertical E-W (perfil longitudinal)
X, Z, ESD = calculadora.obtener_seccion_vertical_ew(latitud=19.3)

# Sección a lo largo de perfil personalizado
puntos = [(19.0, -104.0), (19.5, -103.5), (20.0, -103.0)]
D, Z, ESD = calculadora.obtener_seccion_perfil(puntos)
```

### Paleta de Colores

La paleta reproduce los colores del artículo de Del Pezzo et al.:

```python
from seismex.analysis.esd import PaletaColoresESD

paleta = PaletaColoresESD()

# Niveles de contorno estándar (log10 ESD normalizado)
niveles = [-12, -7, -4.5, -3.0, -2.5, -2.0, -1.0, -0.5, 0, 0.5]

# Obtener colormap matplotlib
cmap = paleta.obtener_colormap()
norm = paleta.obtener_normalizacion()
```

| Nivel | Color | Interpretación |
|-------|-------|----------------|
| < -7 | Índigo | Muy baja energía |
| -7 a -4 | Azul | Baja energía |
| -4 a -2 | Verde | Moderada |
| -2 a -0.5 | Rosa | Alta |
| > -0.5 | Rojo | Muy alta energía |

---

## Gutenberg-Richter

Análisis de la relación frecuencia-magnitud para estimar la magnitud de completitud (Mc) y el valor-b.

### Fundamento Teórico

```
log₁₀(N) = a - b × M
```

Donde:
- `N` = número de eventos con magnitud ≥ M
- `a` = tasa de sismicidad
- `b` = pendiente (~1.0 para tectónica global)

### Métodos para Mc

| Método | Código | Descripción |
|--------|--------|-------------|
| MAXC | `'maxc'` | Máximo de la curva (+ 0.2 corrección) |
| GFT | `'gft'` | Goodness-of-fit test |
| MBS | `'mbs'` | Método b-value stability |
| EMR | `'emr'` | Entire magnitude range |

### Métodos para valor-b

| Método | Código | Descripción |
|--------|--------|-------------|
| MLE | `'mle'` | Maximum Likelihood (Aki, 1965) |
| LSQ | `'lsq'` | Mínimos cuadrados |
| BPOS | `'bpos'` | b-positive (Herrmann, 1979) |

### Uso

```python
from seismex.analysis import AnalizadorGutenbergRichter

# Crear analizador
gr = AnalizadorGutenbergRichter(
    metodo_mc='maxc',           # Método para Mc
    metodo_b='mle',             # Método para b
    correccion_mc=0.2,          # Corrección conservadora (Woessner)
    bin_magnitud=0.1,           # Ancho de bin
    bootstrap_n=1000            # Iteraciones Monte Carlo
)

# Analizar
resultado = gr.analizar(catalogo)

# Resultados
print(f"Mc = {resultado.mc:.2f}")
print(f"b = {resultado.b_value:.3f} ± {resultado.b_error:.3f}")
print(f"a = {resultado.a_value:.3f} ± {resultado.a_error:.3f}")
print(f"N(M≥Mc) = {resultado.n_eventos}")

# Graficar
fig = gr.graficar_fmd(
    mostrar_ajuste=True,
    mostrar_mc=True,
    guardar='gutenberg_richter.png'
)
```

### Análisis Espacio-Temporal

```python
# Variación temporal del valor-b
resultados_temporales = gr.analizar_temporal(
    catalogo,
    ventana_años=2.0,
    paso_meses=6
)

# Graficar evolución
gr.graficar_evolucion_b(resultados_temporales)

# Variación espacial (mapa de valor-b)
mapa_b = gr.analizar_espacial(
    catalogo,
    tamano_celda_grados=0.5,
    min_eventos=50
)

gr.graficar_mapa_b(mapa_b, guardar='mapa_b_value.png')
```

---

## Isosistas

Generación de mapas de intensidad sísmica (isosistas) basados en ecuaciones de predicción del movimiento del terreno (GMPE) y ecuaciones de predicción de intensidad (IPE).

### Estado: ✅ Completo

### Componentes Implementados

#### GMPEs (Ground Motion Prediction Equations)

| Modelo | Clase | Región | Referencia |
|--------|-------|--------|------------|
| Zhao (2006) | `GMPEZhao2006` | Subducción (Global) | Zhao et al., BSSA 2006 |
| García (2005) | `GMPEGarcia2005` | México | García et al., GJI 2005 |
| Atkinson-Boore (2003) | `GMPEAtkinsonBoore2003` | Intraplaca | Atkinson & Boore, BSSA 2003 |

#### IPEs (Intensity Prediction Equations)

| Modelo | Clase | Región | Referencia |
|--------|-------|--------|------------|
| Allen (2012) | `IPEAllen2012` | Global (corteza activa) | Allen et al., J. Seismology 2012 |
| Atkinson-Wald (2007) | `IPEAtkinsonWald2007` | Global (desde PGM) | Atkinson & Wald, SRL 2007 |
| CENAPRED (2006) | `IPECENAPRED2006` | México | CENAPRED 2006 |

### Uso Básico

```python
from seismex.analysis.isoseismal import (
    GeneradorIsosistas,
    crear_generador_mexico,
    crear_generador_subduccion
)

# Opción 1: Generador genérico
gen = GeneradorIsosistas(
    ipe='allen_2012',           # Intensity Prediction Equation
    gmpe='zhao_2006',           # Ground Motion Prediction Equation (opcional)
    vs30_default=760            # Velocidad Vs30 por defecto (m/s)
)

# Opción 2: Generador preconfigurado para México
gen = crear_generador_mexico()  # Usa CENAPRED + García

# Opción 3: Generador para subducción
gen = crear_generador_subduccion()  # Usa Allen + Zhao

# Generar isosistas para un evento
resultado = gen.calcular(
    latitud=19.32,
    longitud=-103.64,
    profundidad_km=15,
    magnitud=6.5,
    resolucion_km=5.0,          # Resolución espacial
    radio_max_km=300            # Radio máximo de cálculo
)

# Información del resultado
print(f"Intensidad máxima: {resultado.intensidad_maxima:.1f} MMI")
print(f"Intensidad en epicentro: {resultado.intensidad_epicentro:.1f} MMI")
```

### Visualización

```python
# Graficar mapa de isosistas
resultado.graficar(
    mostrar_epicentro=True,
    mostrar_contornos=True,
    colorbar=True
)

# Obtener contornos como lista de diccionarios
contornos = resultado.obtener_contornos(niveles=[4, 5, 6, 7, 8])
for c in contornos:
    print(f"MMI {c['nivel']}: {c['descripcion']} - {c['color']}")
```

### Exportación

```python
# Exportar a GeoJSON (contornos vectoriales)
resultado.exportar_geojson('isosistas_m65.geojson')

# Exportar a Shapefile
resultado.exportar_shapefile('isosistas_m65.shp')

# Exportar grilla a GeoTIFF
resultado.exportar_geotiff('intensidad_m65.tif')

# Convertir a GeoDataFrame para análisis SIG
gdf = resultado.to_geodataframe()
print(gdf.head())
```

### Modelo de Sitio (Efectos de Vs30)

```python
from seismex.analysis.isoseismal import ModeloSitio, GeneradorIsosistas
import numpy as np

# Crear modelo de sitio con raster de Vs30
vs30_raster = np.load('vs30_mexico.npy')  # Tu grilla de Vs30
bounds = (-118, 14, -86, 33)  # lon_min, lat_min, lon_max, lat_max

modelo_sitio = ModeloSitio(
    vs30_default=760.0,         # Valor por defecto donde no hay datos
    vs30_raster=vs30_raster,    # Grilla de valores
    bounds=bounds               # Límites del raster
)

# Crear generador con modelo de sitio
gen = GeneradorIsosistas(
    ipe='cenapred_2006',
    modelo_sitio=modelo_sitio
)
```

### Escenarios Múltiples

```python
# Calcular isosistas combinadas de múltiples eventos
eventos = [
    {'latitud': 19.32, 'longitud': -103.64, 'profundidad_km': 15, 'magnitud': 6.5},
    {'latitud': 19.50, 'longitud': -103.80, 'profundidad_km': 20, 'magnitud': 5.8},
]

resultado_escenario = gen.calcular_escenario(
    eventos=eventos,
    resolucion_km=5.0,
    metodo_combinacion='max'  # 'max', 'mean', o 'sum'
)
```

### Escala de Intensidad MMI

| MMI | Descripción | Color |
|-----|-------------|-------|
| I | No sentido | #FFFFFF |
| II | Muy débil | #ACD8E9 |
| III | Débil | #ACD8E9 |
| IV | Ligero | #83D0DA |
| V | Moderado | #7BC87F |
| VI | Fuerte | #F9F518 |
| VII | Muy fuerte | #FAC611 |
| VIII | Severo | #FA8A11 |
| IX | Violento | #F7100C |
| X | Extremo | #C80F0A |
| XI | Casi total destrucción | #800000 |
| XII | Total destrucción | #400000 |

### Conversión PGM a MMI

```python
from seismex.analysis.isoseismal import pga_a_mmi_wald, pgv_a_mmi_wald

# Convertir PGA (g) a MMI
mmi = pga_a_mmi_wald(0.15)  # 0.15g → ~VII MMI

# Convertir PGV (cm/s) a MMI
mmi = pgv_a_mmi_wald(20.0)  # 20 cm/s → ~VII MMI
```

### Listar Modelos Disponibles

```python
from seismex.analysis.isoseismal import GeneradorIsosistas

modelos = GeneradorIsosistas.listar_modelos()
print("IPEs:", modelos['ipes'])
print("GMPEs:", modelos['gmpes'])
```

---

## PSHA

Análisis Probabilístico de Peligro Sísmico basado en la metodología de Cornell-McGuire.

### Estado: 📋 Planificado

### Estructura Planificada

```python
from seismex.analysis.psha import (
    AnalizadorPSHA,
    ModeloFuentes,
    ArbolLogico
)

# Definir modelo de fuentes
fuentes = ModeloFuentes()
fuentes.agregar_zona_area(
    nombre='Fosa Mesoamericana',
    geometria='fosa_mesoamericana.geojson',
    a_value=4.5,
    b_value=0.95,
    mmax=8.2,
    profundidad_media=25
)

# Crear analizador
psha = AnalizadorPSHA(
    fuentes=fuentes,
    gmpe=['zhao_2006', 'garcia_2005'],  # Árbol lógico
    pesos_gmpe=[0.6, 0.4],
    periodos_retorno=[475, 975, 2475],   # años
    vs30=760                              # Roca
)

# Calcular curva de peligro
curva = psha.calcular_curva_peligro(
    sitio=(19.32, -103.64),
    intensidad='PGA'
)

# Calcular mapa de peligro
mapa = psha.calcular_mapa_peligro(
    region={'lat': (14, 33), 'lon': (-118, -86)},
    resolucion=0.1,
    periodo_retorno=475
)

# Desagregación
desag = psha.desagregar(
    sitio=(19.32, -103.64),
    nivel_peligro=0.1,  # g
    tipo='MRε'
)
```

---

## Ejemplos Integrados

### Pipeline Completo de Análisis

```python
from seismex.core import CatalogoSismico, Preprocesador
from seismex.analysis import (
    AnalizadorGutenbergRichter,
    CalculadoraESD,
    ConfiguracionESD
)
from seismex.analysis.isoseismal import GeneradorIsosistas
from seismex.visualization import VisualizadorESD

# 1. Cargar y preparar datos
catalogo = CatalogoSismico.desde_csv('ssn_colima.csv', formato='ssn')
catalogo.homogeneizar_magnitudes('Mw')

prep = Preprocesador()
catalogo = prep.declustering(catalogo)

# 2. Análisis Gutenberg-Richter
gr = AnalizadorGutenbergRichter()
resultado_gr = gr.analizar(catalogo)
mc = resultado_gr.mc

print(f"Mc = {mc:.2f}, b = {resultado_gr.b_value:.3f}")

# 3. Análisis ESD con Mc calculado
config = ConfiguracionESD(
    tamano_celda_km=10.0,
    magnitud_minima=mc
)

esd = CalculadoraESD(config)
resultado_esd = esd.calcular_esd(catalogo)

# 4. Generar isosistas para el evento más grande
evento_max = catalogo.obtener_evento_maximo()
gen = GeneradorIsosistas(ipe='cenapred_2006')
isosistas = gen.calcular(
    latitud=evento_max.latitud,
    longitud=evento_max.longitud,
    profundidad_km=evento_max.profundidad_km,
    magnitud=evento_max.magnitud
)

# 5. Visualizar y exportar
viz = VisualizadorESD(resultado_esd)
viz.graficar_secciones_horizontales([10, 30, 50])
viz.exportar_geotiff('esd_colima.tif', profundidad_km=30)

isosistas.graficar()
isosistas.exportar_geojson('isosistas_evento_max.geojson')
```

### Análisis de Evento Específico

```python
from seismex.analysis.isoseismal import (
    GeneradorIsosistas,
    TipoEvento
)

# Configurar para evento de subducción
gen = GeneradorIsosistas(
    ipe='allen_2012',
    gmpe='zhao_2006'
)

# Sismo del 19 de septiembre de 2017
resultado = gen.calcular(
    latitud=18.40,
    longitud=-98.72,
    profundidad_km=51,
    magnitud=7.1,
    tipo_evento=TipoEvento.SUBDUCCION_INTRAPLACA,
    resolucion_km=2.0,
    radio_max_km=400
)

# Visualizar
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(12, 10))
resultado.graficar(ax=ax, titulo="Isosistas - Sismo 19S 2017 (M7.1)")
plt.savefig('isosistas_19s_2017.png', dpi=300, bbox_inches='tight')
plt.show()
```

---

## Archivos del Módulo

```
seismex/analysis/
├── __init__.py               # Exportaciones
├── esd.py                    # Energy Space Density ✅
├── gutenberg_richter.py      # Análisis G-R ✅
├── isoseismal.py             # Isosistas (GMPEs/IPEs) ✅
├── psha.py                   # PSHA (planificado)
├── source_models.py          # Modelos de fuentes (planificado)
└── README.md                 # Este archivo
```

---

## Referencias

### ESD
- Del Pezzo, E., et al. (2024). "Energy Space Density: A new approach to seismic hazard assessment." *Geophysical Research Letters*.

### Gutenberg-Richter
- Aki, K. (1965). "Maximum likelihood estimate of b in the formula log N = a - bM." *BERI*, 43, 237-239.
- Woessner, J., & Wiemer, S. (2005). "Assessing the quality of earthquake catalogues." *BSSA*, 95(2), 684-698.
- Shi, Y., & Bolt, B. A. (1982). "The standard error of the magnitude-frequency b value." *BSSA*, 72(5), 1677-1687.

### Isosistas / GMPEs / IPEs
- Allen, T.I., et al. (2012). "Intensity attenuation for active crustal regions." *Journal of Seismology*, 16, 409-433.
- Atkinson, G.M. & Wald, D.J. (2007). "Did You Feel It? intensity data: A surprisingly good measure of earthquake ground motion." *SRL*, 78(3), 362-368.
- Zhao, J.X., et al. (2006). "Attenuation relations of strong ground motion in Japan." *BSSA*, 96(3), 898-913.
- García, D., et al. (2005). "A predictive ground motion model for Mexico." *GJI*, 162(3), 908-924.
- Atkinson, G.M. & Boore, D.M. (2003). "Empirical ground-motion relations for subduction-zone earthquakes." *BSSA*, 93(4), 1703-1729.
- CENAPRED (2006). "Guía básica para la elaboración de atlas estatales y municipales de peligros y riesgos."

### PSHA
- Cornell, C.A. (1968). "Engineering seismic risk analysis." *BSSA*, 58(5), 1583-1606.
- McGuire, R.K. (2004). "Seismic Hazard and Risk Analysis." *EERI*.

---

## Véase También

- [`seismex.core`](../core/README.md) - Manejo de catálogos
- [`seismex.visualization`](../visualization/README.md) - Visualización
- [`seismex.optimization`](../optimization/README.md) - Optimización multiobjetivo
- [`seismex.data`](../data/README.md) - Conectores de datos

---

**Versión:** 1.0.0  
**Estado:** ESD ✅ | G-R ✅ | Isosistas ✅ | PSHA 📋
