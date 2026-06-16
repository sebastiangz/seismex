# 📊 seismex.analysis

Módulo de análisis sísmico de SEISMEX. Contiene implementaciones de metodologías para evaluación de peligro y riesgo sísmico.

---

## 📋 Contenido

- [Módulos Disponibles](#módulos-disponibles)
- [ESD - Energy Space Density](#esd---energy-space-density)
- [Gutenberg-Richter](#gutenberg-richter)
- [Isosistas](#isosistas)
- [Modelos de Fuentes](#modelos-de-fuentes)
- [PSHA](#psha)
- [Ejemplos Integrados](#ejemplos-integrados)

---

## Módulos Disponibles

| Módulo | Descripción | Estado |
|--------|-------------|--------|
| `esd` | Energy Space Density (Del Pezzo et al.) | ✅ Completo |
| `gutenberg_richter` | Análisis de valor-b y Mc | ✅ Completo |
| `isoseismal` | Mapas de isosistas (GMPEs/IPEs) | ✅ Completo |
| `source_models` | Modelos de fuentes sísmicas | ✅ Completo |
| `psha` | Probabilistic Seismic Hazard Analysis | ✅ Completo |

---

## ESD - Energy Space Density

Implementación de la metodología **Energy Space Density** basada en Del Pezzo et al. (2024).

```python
from seismex.analysis import CalculadoraESD, ConfiguracionESD

config = ConfiguracionESD(tamano_celda_km=10.0, magnitud_minima=2.4)
calculadora = CalculadoraESD(config)
resultado = calculadora.calcular_esd(catalogo)
```

---

## Gutenberg-Richter

Análisis de la relación frecuencia-magnitud para estimar Mc y valor-b.

```python
from seismex.analysis import AnalizadorGutenbergRichter

gr = AnalizadorGutenbergRichter(metodo_mc='maxc', metodo_b='mle')
resultado = gr.analizar(catalogo)
print(f"Mc = {resultado.mc:.2f}, b = {resultado.b_value:.3f}")
```

---

## Isosistas

Generación de mapas de intensidad sísmica con GMPEs e IPEs.

### Modelos Implementados

| GMPEs | IPEs |
|-------|------|
| Zhao et al. (2006) | Allen et al. (2012) |
| García et al. (2005) | Atkinson & Wald (2007) |
| Atkinson & Boore (2003) | CENAPRED (2006) |

```python
from seismex.analysis.isoseismal import GeneradorIsosistas

gen = GeneradorIsosistas(ipe='cenapred_2006', gmpe='garcia_2005')
resultado = gen.calcular(
    latitud=19.32, longitud=-103.64,
    profundidad_km=15, magnitud=6.5
)
resultado.graficar()
resultado.exportar_geojson('isosistas.geojson')
```

---

## Modelos de Fuentes

Modelos de fuentes sísmicas para análisis PSHA.

### Estado: ✅ Completo

### Tipos de Fuentes

| Clase | Descripción |
|-------|-------------|
| `FuenteArea` | Zonas sismogénicas de área |
| `FuenteFalla` | Fallas activas con geometría |
| `FuentePuntual` | Fuentes puntuales (volcanes, etc.) |

### Distribuciones de Magnitud

| Clase | Descripción |
|-------|-------------|
| `DistribucionGutenbergRichter` | G-R truncada |
| `DistribucionCaracteristica` | Youngs & Coppersmith (1985) |

### Uso Básico

```python
from seismex.analysis.source_models import (
    ModeloFuentes,
    FuenteArea,
    DistribucionGutenbergRichter,
    DistribucionProfundidad,
    TipoFalla,
    crear_modelo_mexico_simplificado
)

# Opción 1: Modelo preconfigurado para México
modelo = crear_modelo_mexico_simplificado()

# Opción 2: Crear modelo personalizado
modelo = ModeloFuentes(nombre="Mi Modelo", version="1.0")

# Agregar zona de área
modelo.agregar_zona_area(
    nombre="Subducción Pacífico",
    poligono=[
        (14.5, -98.0), (16.0, -95.0), (16.5, -93.0),
        (15.5, -92.0), (14.0, -94.0), (14.0, -97.0)
    ],
    a_value=5.0,
    b_value=0.9,
    mmin=5.0,
    mmax=8.2,
    profundidad_media=30
)

# Agregar falla
modelo.agregar_falla(
    nombre="Falla Acambay",
    traza=[(19.8, -99.8), (20.1, -99.5)],
    longitud_km=45,
    ancho_km=15,
    buzamiento=60,
    slip_rate_mm_yr=0.5,
    tipo_falla=TipoFalla.NORMAL
)

# Ver resumen
print(modelo.resumen())

# Generar catálogo sintético
catalogo = modelo.muestrear_catalogo(n_eventos=1000)

# Exportar
modelo.exportar_json('modelo_fuentes.json')
gdf = modelo.to_geodataframe()
```

### Fuente de Área Detallada

```python
from seismex.analysis.source_models import (
    FuenteArea,
    DistribucionGutenbergRichter,
    DistribucionProfundidad,
    TipoDistribucionProfundidad
)

# Distribución de magnitud G-R
dist_mag = DistribucionGutenbergRichter(
    mmin=4.5,
    mmax=7.8,
    a_value=4.2,
    b_value=0.95
)

# Distribución de profundidad
dist_prof = DistribucionProfundidad(
    tipo=TipoDistribucionProfundidad.TRIANGULAR,
    prof_min=5,
    prof_max=40,
    prof_media=20
)

# Crear fuente
fuente = FuenteArea(
    nombre="Zona Oaxaca",
    poligono=[
        (15.5, -98.5), (17.0, -96.0), (17.5, -95.0),
        (16.5, -94.5), (15.0, -96.0)
    ],
    distribucion_magnitud=dist_mag,
    distribucion_profundidad=dist_prof
)

# Propiedades
print(f"Área: {fuente.area_km2():.0f} km²")
print(f"Tasa total: {fuente.tasa_total():.2f} eventos/año")

# Muestrear eventos
eventos = fuente.muestrear_eventos(100)
```

### Fuente de Falla

```python
from seismex.analysis.source_models import FuenteFalla, TipoFalla

fuente = FuenteFalla(
    nombre="Falla San Andrés",
    traza=[(34.0, -118.5), (35.5, -117.0), (36.5, -116.0)],
    longitud_km=150,
    ancho_km=15,
    buzamiento=90,
    rake=180,
    tipo_falla=TipoFalla.LATERAL_DERECHA,
    slip_rate_mm_yr=25.0,
    distribucion_magnitud=DistribucionGutenbergRichter(mmin=5.0, mmax=8.0)
)

# Estimar Mmax con Wells & Coppersmith
mmax = fuente.magnitud_maxima_wells_coppersmith()
print(f"Mmax estimada: {mmax:.1f}")

# Momento sísmico anual
m0 = fuente.momento_sismico_anual()
print(f"M0 anual: {m0:.2e} dyn·cm/año")
```

---

## PSHA

Análisis Probabilístico de Peligro Sísmico basado en Cornell-McGuire.

### Estado: ✅ Completo

### Componentes

| Clase | Descripción |
|-------|-------------|
| `AnalizadorPSHA` | Motor principal de cálculo |
| `CurvaPeligro` | Curva de excedencia de intensidad |
| `MapaPeligro` | Mapa espacial de peligro |
| `Desagregacion` | Análisis de contribución M-R-ε |
| `ArbolLogico` | Manejo de incertidumbre epistémica |

### Uso Básico

```python
from seismex.analysis.psha import AnalizadorPSHA, crear_analizador_mexico
from seismex.analysis.source_models import crear_modelo_mexico_simplificado
from seismex.analysis.isoseismal import GMPEGarcia2005, GMPEZhao2006

# Opción 1: Analizador preconfigurado para México
psha = crear_analizador_mexico(vs30=400)

# Opción 2: Configuración manual
fuentes = crear_modelo_mexico_simplificado()
psha = AnalizadorPSHA(fuentes=fuentes, vs30=760)
psha.agregar_gmpe(GMPEGarcia2005(), peso=0.6)
psha.agregar_gmpe(GMPEZhao2006(), peso=0.4)

# Ver configuración
print(psha.resumen())
```

### Curva de Peligro

```python
# Calcular curva de peligro para un sitio
curva = psha.calcular_curva_peligro(
    sitio=(19.4, -99.1),  # Ciudad de México
    vs30=350,
    medida=MedidaIntensidad.PGA
)

# Obtener PGA para diferentes períodos de retorno
pga_475 = curva.intensidad_para_periodo_retorno(475)
pga_2475 = curva.intensidad_para_periodo_retorno(2475)
print(f"PGA 475 años: {pga_475:.3f} g")
print(f"PGA 2475 años: {pga_2475:.3f} g")

# Probabilidad de exceder 0.2g en 50 años
prob = curva.probabilidad_excedencia(0.2, tiempo_exposicion=50)
print(f"P(PGA > 0.2g en 50 años): {prob:.1%}")

# Graficar curva
curva.graficar()
```

### Mapa de Peligro

```python
# Calcular mapa para TR=475 años
mapa = psha.calcular_mapa_peligro(
    region={'lat': (14, 20), 'lon': (-105, -95)},
    periodo_retorno=475,
    resolucion=0.25,
    vs30=400,
    verbose=True
)

# Propiedades
print(f"PGA máxima: {mapa.intensidad_maxima:.3f} g")
print(f"PGA media: {mapa.intensidad_media:.3f} g")

# Obtener PGA en un punto
pga_cdmx = mapa.obtener_intensidad(19.4, -99.1)

# Graficar
mapa.graficar(contornos=True)

# Exportar
mapa.exportar_geotiff('peligro_475.tif')
gdf = mapa.to_geodataframe()
```

### Espectro de Peligro Uniforme (UHS)

```python
# Calcular UHS para TR=475 años
periodos, aceleraciones = psha.calcular_espectro_uniforme(
    sitio=(19.4, -99.1),
    periodo_retorno=475,
    periodos=[0.0, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0],
    vs30=350
)

# Graficar
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
plt.plot(periodos, aceleraciones, 'o-')
plt.xlabel('Período (s)')
plt.ylabel('Sa (g)')
plt.title('Espectro de Peligro Uniforme - TR=475 años')
plt.grid(True)
plt.show()
```

### Desagregación

```python
# Desagregar peligro para PGA=0.3g
desag = psha.desagregar(
    sitio=(19.4, -99.1),
    nivel_intensidad=0.3,
    vs30=350
)

# Escenarios dominantes
print(f"Magnitud modal: {desag.magnitud_modal:.1f}")
print(f"Distancia modal: {desag.distancia_modal:.0f} km")
print(f"Epsilon modal: {desag.epsilon_modal:.2f}")

print(f"Magnitud media: {desag.magnitud_media:.1f}")
print(f"Distancia media: {desag.distancia_media:.0f} km")

# Graficar
desag.graficar_MR()
```

### Árbol Lógico

```python
from seismex.analysis.psha import ArbolLogico

# Crear árbol lógico
arbol = ArbolLogico()
arbol.agregar_rama("García 2005", peso=0.5, gmpe=GMPEGarcia2005())
arbol.agregar_rama("Zhao 2006", peso=0.3, gmpe=GMPEZhao2006())
arbol.agregar_rama("AB 2003", peso=0.2, gmpe=GMPEAtkinsonBoore2003())

arbol.normalizar_pesos()
print(f"Pesos válidos: {arbol.validar()}")
```

### Utilidades

```python
from seismex.analysis.psha import (
    calcular_probabilidad_poisson,
    periodo_retorno_desde_probabilidad
)

# Probabilidad de al menos 1 evento en 50 años (tasa=0.01/año)
prob = calcular_probabilidad_poisson(tasa=0.01, tiempo=50, n_eventos=1)
print(f"P(N>=1 en 50 años): {prob:.1%}")

# Período de retorno para 10% en 50 años
tr = periodo_retorno_desde_probabilidad(probabilidad=0.10, tiempo=50)
print(f"TR para 10% en 50 años: {tr:.0f} años")
```

---

## Ejemplos Integrados

### Pipeline Completo de Análisis

```python
from seismex.core import CatalogoSismico
from seismex.analysis import AnalizadorGutenbergRichter, CalculadoraESD, ConfiguracionESD
from seismex.analysis.isoseismal import GeneradorIsosistas
from seismex.analysis.source_models import crear_modelo_mexico_simplificado
from seismex.analysis.psha import AnalizadorPSHA

# 1. Cargar catálogo
catalogo = CatalogoSismico.desde_csv('ssn_colima.csv', formato='ssn')

# 2. Análisis Gutenberg-Richter
gr = AnalizadorGutenbergRichter()
resultado_gr = gr.analizar(catalogo)
print(f"Mc = {resultado_gr.mc:.2f}, b = {resultado_gr.b_value:.3f}")

# 3. Análisis ESD
config = ConfiguracionESD(tamano_celda_km=10.0, magnitud_minima=resultado_gr.mc)
esd = CalculadoraESD(config)
resultado_esd = esd.calcular_esd(catalogo)

# 4. Crear modelo de fuentes calibrado
from seismex.analysis.source_models import ModeloFuentes
modelo = ModeloFuentes(nombre="Colima Calibrado")
modelo.agregar_zona_area(
    nombre="Zona Colima",
    poligono=[(18.5, -105.0), (20.0, -104.0), (20.0, -102.5), (18.5, -103.0)],
    a_value=resultado_gr.a_value,
    b_value=resultado_gr.b_value,
    mmin=resultado_gr.mc,
    mmax=8.0
)

# 5. Análisis PSHA
from seismex.analysis.isoseismal import GMPEGarcia2005
psha = AnalizadorPSHA(fuentes=modelo, vs30=400)
psha.agregar_gmpe(GMPEGarcia2005(), peso=1.0)

# Curva de peligro
curva = psha.calcular_curva_peligro(sitio=(19.3, -103.7))
print(f"PGA 475 años: {curva.intensidad_para_periodo_retorno(475):.3f} g")

# 6. Isosistas del evento más grande
evento_max = catalogo.obtener_evento_maximo()
gen = GeneradorIsosistas(ipe='cenapred_2006')
isosistas = gen.calcular(
    latitud=evento_max.latitud,
    longitud=evento_max.longitud,
    profundidad_km=evento_max.profundidad_km,
    magnitud=evento_max.magnitud
)

# 7. Exportar resultados
resultado_esd.exportar_geotiff('esd_colima.tif')
isosistas.exportar_geojson('isosistas_max.geojson')
curva.graficar()
```

### Análisis de Escenario Sísmico

```python
from seismex.analysis.isoseismal import GeneradorIsosistas, TipoEvento
from seismex.analysis.psha import AnalizadorPSHA

# Definir escenario: M8.0 en la brecha de Guerrero
escenario = {
    'latitud': 17.0,
    'longitud': -100.5,
    'profundidad_km': 20,
    'magnitud': 8.0
}

# Generar isosistas
gen = GeneradorIsosistas(ipe='allen_2012', gmpe='zhao_2006')
isosistas = gen.calcular(
    tipo_evento=TipoEvento.SUBDUCCION_INTERFAZ,
    resolucion_km=2.0,
    radio_max_km=500,
    **escenario
)

print(f"Intensidad máxima: {isosistas.intensidad_maxima:.1f} MMI")
isosistas.graficar(titulo="Escenario M8.0 Brecha de Guerrero")
isosistas.exportar_geojson('escenario_guerrero_m80.geojson')
```

---

## Archivos del Módulo

```
seismex/analysis/
├── __init__.py               # Exportaciones
├── esd.py                    # Energy Space Density ✅
├── gutenberg_richter.py      # Análisis G-R ✅
├── isoseismal.py             # Isosistas (GMPEs/IPEs) ✅
├── source_models.py          # Modelos de fuentes ✅
├── psha.py                   # PSHA Cornell-McGuire ✅
└── README.md                 # Este archivo
```

---

## Referencias

### ESD
- Del Pezzo, E., et al. (2024). "Energy Space Density: A new approach to seismic hazard assessment." *Geophysical Research Letters*.

### Gutenberg-Richter
- Aki, K. (1965). "Maximum likelihood estimate of b in the formula log N = a - bM." *BERI*, 43, 237-239.
- Woessner, J., & Wiemer, S. (2005). "Assessing the quality of earthquake catalogues." *BSSA*, 95(2), 684-698.

### Isosistas / GMPEs / IPEs
- Allen, T.I., et al. (2012). "Intensity attenuation for active crustal regions." *J. Seismology*, 16, 409-433.
- Zhao, J.X., et al. (2006). "Attenuation relations of strong ground motion in Japan." *BSSA*, 96(3), 898-913.
- García, D., et al. (2005). "A predictive ground motion model for Mexico." *GJI*, 162(3), 908-924.
- Atkinson, G.M. & Boore, D.M. (2003). "Empirical ground-motion relations for subduction-zone earthquakes." *BSSA*, 93(4), 1703-1729.
- CENAPRED (2006). "Guía básica para la elaboración de atlas estatales y municipales de peligros y riesgos."

### Modelos de Fuentes
- Youngs, R.R. & Coppersmith, K.J. (1985). "Implications of fault slip rates and earthquake recurrence models." *BSSA*, 75(4), 939-964.
- Wells, D.L. & Coppersmith, K.J. (1994). "New empirical relationships among magnitude, rupture length, rupture width, rupture area, and surface displacement." *BSSA*, 84(4), 974-1002.
- Gutenberg, B. & Richter, C.F. (1944). "Frequency of earthquakes in California." *BSSA*, 34(4), 185-188.

### PSHA
- Cornell, C.A. (1968). "Engineering seismic risk analysis." *BSSA*, 58(5), 1583-1606.
- McGuire, R.K. (2004). "Seismic Hazard and Risk Analysis." *EERI Monograph*.
- Bazzurro, P. & Cornell, C.A. (1999). "Disaggregation of seismic hazard." *BSSA*, 89(2), 501-520.

---

## Véase También

- [`seismex.core`](../core/README.md) - Manejo de catálogos
- [`seismex.visualization`](../visualization/README.md) - Visualización
- [`seismex.optimization`](../optimization/README.md) - Optimización multiobjetivo
- [`seismex.data`](../data/README.md) - Conectores de datos

---

**Versión:** 1.0.0  
**Estado:** ESD ✅ | G-R ✅ | Isosistas ✅ | Fuentes ✅ | PSHA ✅
