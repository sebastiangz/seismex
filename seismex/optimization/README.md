# 🧬 seismex.optimization

Módulo de optimización multiobjetivo de SEISMEX. Implementa algoritmos genéticos (NSGA-II) para la toma de decisiones en evaluación de riesgo sísmico.

---

## 📋 Contenido

- [Descripción General](#descripción-general)
- [NSGA-II](#nsga-ii)
- [Funciones Objetivo](#funciones-objetivo)
- [Restricciones](#restricciones)
- [Ejemplos de Aplicación](#ejemplos-de-aplicación)
- [Integración con Análisis Sísmico](#integración-con-análisis-sísmico)

---

## Estado: 📋 Planificado

Este módulo está en fase de diseño. La implementación se basará en el código existente de `GA_VERTIMIENTOS_CUYUTLAN_v1.py` adaptado para análisis de riesgo sísmico.

---

## Descripción General

El módulo de optimización permite encontrar soluciones óptimas a problemas multiobjetivo relacionados con:

- **Ubicación de infraestructura crítica** considerando riesgo sísmico
- **Planificación de evacuación** optimizando rutas y refugios
- **Asignación de recursos** para mitigación de riesgo
- **Diseño de redes de monitoreo sísmico**
- **Evaluación de impacto ambiental** de proyectos en zonas sísmicas

### Arquitectura del Módulo

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPTIMIZADOR NSGA-II                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Población  │→ │  Selección  │→ │   Cruce y Mutación      │ │
│  │   Inicial   │  │  Torneo     │  │   SBX + Polynomial      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│         ↓                                      ↓                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Evaluación de Objetivos                     │   │
│  │  f₁: Costo  |  f₂: Riesgo  |  f₃: Impacto  |  f₄: Social │   │
│  └─────────────────────────────────────────────────────────┘   │
│         ↓                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         Non-Dominated Sorting + Crowding Distance        │   │
│  └─────────────────────────────────────────────────────────┘   │
│         ↓                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Frente de Pareto                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## NSGA-II

### Clase Principal

```python
from seismex.optimization import NSGAII, ConfiguracionNSGAII

# Configuración
config = ConfiguracionNSGAII(
    tamano_poblacion=100,
    generaciones=200,
    prob_cruce=0.9,
    prob_mutacion=0.1,
    eta_cruce=15,               # Índice de distribución SBX
    eta_mutacion=20,            # Índice de distribución mutación
    semilla=42                  # Reproducibilidad
)

# Crear optimizador
optimizer = NSGAII(config)
```

### Definición del Problema

```python
from seismex.optimization import ProblemaOptimizacion

class ProblemaUbicacionPlanta(ProblemaOptimizacion):
    """Optimización de ubicación de planta industrial considerando riesgo sísmico."""
    
    def __init__(self, resultado_esd, catalogo, region):
        super().__init__(
            n_variables=2,              # lat, lon
            n_objetivos=4,              # costo, riesgo, impacto, social
            n_restricciones=3           # área válida, distancia mín, etc.
        )
        self.resultado_esd = resultado_esd
        self.catalogo = catalogo
        self.region = region
        
        # Límites de variables
        self.limites_inf = [region['lat_min'], region['lon_min']]
        self.limites_sup = [region['lat_max'], region['lon_max']]
    
    def evaluar(self, x):
        """Evaluar solución x = [lat, lon]."""
        lat, lon = x
        
        # Objetivo 1: Costo de construcción
        f1 = self.calcular_costo(lat, lon)
        
        # Objetivo 2: Riesgo sísmico (de ESD)
        f2 = self.calcular_riesgo_sismico(lat, lon)
        
        # Objetivo 3: Impacto ambiental
        f3 = self.calcular_impacto_ambiental(lat, lon)
        
        # Objetivo 4: Impacto social
        f4 = self.calcular_impacto_social(lat, lon)
        
        # Restricciones (g ≤ 0 para factible)
        g1 = self.restriccion_area_valida(lat, lon)
        g2 = self.restriccion_distancia_poblacion(lat, lon)
        g3 = self.restriccion_acceso_vias(lat, lon)
        
        return [f1, f2, f3, f4], [g1, g2, g3]
    
    def calcular_riesgo_sismico(self, lat, lon):
        """Extraer valor ESD en ubicación."""
        esd = self.resultado_esd.obtener_valor(lat, lon, profundidad_km=30)
        return 10 ** esd  # Convertir de log a lineal
```

### Ejecución

```python
# Crear problema
problema = ProblemaUbicacionPlanta(resultado_esd, catalogo, region)

# Ejecutar optimización
resultado = optimizer.optimizar(
    problema,
    verbose=True,
    callback=lambda gen, pop: print(f"Gen {gen}: {len(pop.frente_pareto)} soluciones")
)

# Obtener frente de Pareto
pareto = resultado.frente_pareto

print(f"Soluciones no dominadas: {len(pareto)}")
for i, sol in enumerate(pareto[:5]):
    print(f"  {i+1}: Costo={sol.f[0]:.2f}, Riesgo={sol.f[1]:.4f}, "
          f"Impacto={sol.f[2]:.2f}, Social={sol.f[3]:.2f}")
```

---

## Funciones Objetivo

### Catálogo de Funciones Disponibles

| Función | Descripción | Minimizar |
|---------|-------------|-----------|
| `costo_construccion` | Costo estimado de construcción | ✅ |
| `riesgo_sismico_esd` | Riesgo basado en ESD | ✅ |
| `riesgo_sismico_pga` | Riesgo basado en PGA esperado | ✅ |
| `impacto_ambiental` | Índice de impacto ambiental | ✅ |
| `impacto_social` | Afectación a comunidades | ✅ |
| `distancia_recursos` | Distancia a recursos necesarios | ✅ |
| `conectividad_vial` | Acceso a red de carreteras | ❌ (maximizar) |
| `cobertura_monitoreo` | Cobertura de red sísmica | ❌ (maximizar) |

### Implementación de Funciones Objetivo

```python
from seismex.optimization.objectives import (
    ObjetivoCosto,
    ObjetivoRiesgoESD,
    ObjetivoImpactoAmbiental,
    ObjetivoImpactoSocial
)

# Función de costo
costo = ObjetivoCosto(
    costo_base_por_m2=1500,     # USD/m²
    factores_terreno={
        'plano': 1.0,
        'pendiente_moderada': 1.2,
        'pendiente_alta': 1.5,
        'inundable': 1.8
    }
)

# Función de riesgo sísmico
riesgo = ObjetivoRiesgoESD(
    resultado_esd=resultado_esd,
    profundidad_km=30,
    normalizar=True
)

# Función de impacto ambiental
impacto_amb = ObjetivoImpactoAmbiental(
    areas_protegidas='anp_mexico.geojson',
    cuerpos_agua='hidrografia.geojson',
    vegetacion='uso_suelo.tif',
    pesos={
        'anp': 10.0,
        'humedales': 8.0,
        'bosque': 5.0,
        'selva': 5.0,
        'agricola': 2.0,
        'urbano': 1.0
    }
)

# Función de impacto social
impacto_soc = ObjetivoImpactoSocial(
    poblaciones='localidades_inegi.csv',
    buffer_impacto_km=5.0,
    factor_poblacion=1.0,
    factor_marginacion=2.0
)
```

---

## Restricciones

### Tipos de Restricciones

```python
from seismex.optimization.constraints import (
    RestriccionGeografica,
    RestriccionDistancia,
    RestriccionAccesibilidad,
    RestriccionNormativa
)

# Restricción de área válida (solo en región permitida)
area = RestriccionGeografica(
    poligono='area_estudio.geojson',
    excluir=['anp.geojson', 'zonas_urbanas.geojson']
)

# Restricción de distancia mínima a poblaciones
distancia = RestriccionDistancia(
    puntos='localidades.csv',
    distancia_min_km=2.0,
    distancia_max_km=50.0
)

# Restricción de accesibilidad
acceso = RestriccionAccesibilidad(
    red_vial='carreteras.geojson',
    distancia_max_km=10.0
)

# Restricción normativa (e.g., NOM-001-SEMARNAT)
normativa = RestriccionNormativa(
    norma='NOM-001',
    parametros={
        'distancia_cuerpo_agua_m': 500,
        'distancia_anp_m': 1000
    }
)
```

### Manejo de Restricciones

```python
from seismex.optimization import ManejadorRestricciones

# Crear manejador
manejador = ManejadorRestricciones(
    restricciones=[area, distancia, acceso, normativa],
    metodo='penalizacion',      # 'penalizacion', 'reparacion', 'rechazo'
    factor_penalizacion=1e6
)

# Verificar factibilidad
es_factible, violaciones = manejador.verificar(x)

if not es_factible:
    for v in violaciones:
        print(f"Violación: {v.restriccion} = {v.valor:.2f}")
```

---

## Ejemplos de Aplicación

### Ejemplo 1: Ubicación de Planta Industrial

```python
from seismex.optimization import NSGAII, ProblemaOptimizacion
from seismex.optimization.objectives import *
from seismex.optimization.constraints import *

# Cargar datos previos
from seismex.core import CatalogoSismico
from seismex.analysis import CalculadoraESD, ConfiguracionESD

catalogo = CatalogoSismico.desde_csv('catalogo_colima.csv')
config = ConfiguracionESD(tamano_celda_km=10)
calc = CalculadoraESD(config)
resultado_esd = calc.calcular_esd(catalogo)

# Definir problema
problema = ProblemaUbicacionPlanta(
    resultado_esd=resultado_esd,
    region={'lat_min': 18.5, 'lat_max': 20.0, 
            'lon_min': -104.5, 'lon_max': -103.0},
    objetivos=[
        ObjetivoCosto(),
        ObjetivoRiesgoESD(resultado_esd),
        ObjetivoImpactoAmbiental('capas_ambientales/'),
        ObjetivoImpactoSocial('localidades.csv')
    ],
    restricciones=[
        RestriccionGeografica('area_permitida.geojson'),
        RestriccionDistancia('poblaciones.csv', min_km=2.0)
    ]
)

# Optimizar
config = ConfiguracionNSGAII(tamano_poblacion=100, generaciones=200)
optimizer = NSGAII(config)
resultado = optimizer.optimizar(problema)

# Visualizar frente de Pareto
from seismex.optimization.visualization import VisualizadorPareto

viz = VisualizadorPareto(resultado)
viz.graficar_frente_2d(objetivos=[0, 1], guardar='pareto_costo_riesgo.png')
viz.graficar_frente_3d(objetivos=[0, 1, 2], guardar='pareto_3d.html')
viz.graficar_mapa_soluciones(guardar='mapa_soluciones.html')
```

### Ejemplo 2: Red de Monitoreo Sísmico

```python
class ProblemaRedMonitoreo(ProblemaOptimizacion):
    """Optimizar ubicación de N estaciones sísmicas."""
    
    def __init__(self, n_estaciones, region, resultado_esd):
        super().__init__(
            n_variables=2 * n_estaciones,  # lat, lon para cada estación
            n_objetivos=3,
            n_restricciones=1
        )
        self.n_estaciones = n_estaciones
        self.region = region
        self.resultado_esd = resultado_esd
    
    def evaluar(self, x):
        # Decodificar posiciones
        posiciones = [(x[2*i], x[2*i+1]) for i in range(self.n_estaciones)]
        
        # Objetivo 1: Cobertura (maximizar → minimizar -cobertura)
        f1 = -self.calcular_cobertura(posiciones)
        
        # Objetivo 2: Costo (minimizar)
        f2 = self.calcular_costo_instalacion(posiciones)
        
        # Objetivo 3: Detectabilidad en zonas de alta ESD (maximizar)
        f3 = -self.calcular_detectabilidad_esd(posiciones)
        
        # Restricción: distancia mínima entre estaciones
        g1 = self.restriccion_distancia_minima(posiciones, min_km=10)
        
        return [f1, f2, f3], [g1]

# Ejecutar
problema = ProblemaRedMonitoreo(n_estaciones=10, region=region, resultado_esd=resultado_esd)
resultado = optimizer.optimizar(problema)
```

### Ejemplo 3: Rutas de Evacuación

```python
class ProblemaEvacuacion(ProblemaOptimizacion):
    """Optimizar rutas de evacuación y ubicación de refugios."""
    
    def __init__(self, poblaciones, red_vial, refugios_candidatos, zonas_riesgo):
        # ... implementación
        pass
    
    def evaluar(self, x):
        # x codifica: selección de refugios y asignación de poblaciones
        
        # Objetivo 1: Tiempo máximo de evacuación (minimizar)
        f1 = self.calcular_tiempo_max_evacuacion(x)
        
        # Objetivo 2: Distancia total recorrida (minimizar)
        f2 = self.calcular_distancia_total(x)
        
        # Objetivo 3: Costo de operación refugios (minimizar)
        f3 = self.calcular_costo_refugios(x)
        
        # Objetivo 4: Exposición a riesgo durante evacuación (minimizar)
        f4 = self.calcular_riesgo_rutas(x)
        
        return [f1, f2, f3, f4], []
```

---

## Integración con Análisis Sísmico

### Flujo de Trabajo Completo

```python
# 1. Análisis sísmico
from seismex.core import CatalogoSismico
from seismex.analysis import CalculadoraESD, AnalizadorGutenbergRichter

catalogo = CatalogoSismico.desde_csv('catalogo.csv')
gr = AnalizadorGutenbergRichter().analizar(catalogo)

config_esd = ConfiguracionESD(magnitud_minima=gr.mc)
resultado_esd = CalculadoraESD(config_esd).calcular_esd(catalogo)

# 2. Definir problema de optimización
problema = ProblemaUbicacionPlanta(
    resultado_esd=resultado_esd,
    # ... parámetros
)

# 3. Optimizar
resultado = NSGAII(config).optimizar(problema)

# 4. Análisis de resultados
from seismex.optimization.analysis import AnalizadorResultados

analisis = AnalizadorResultados(resultado)

# Análisis de sensibilidad
sensibilidad = analisis.analisis_sensibilidad()

# Selección de mejor compromiso (TOPSIS)
mejor = analisis.seleccionar_topsis(pesos=[0.3, 0.3, 0.2, 0.2])

# Reporte
analisis.generar_reporte('reporte_optimizacion.docx')
```

---

## Archivos del Módulo

```
seismex/optimization/
├── __init__.py               # Exportaciones
├── nsga2.py                  # Algoritmo NSGA-II
├── problem.py                # Clase base ProblemaOptimizacion
├── objectives/               # Funciones objetivo
│   ├── __init__.py
│   ├── cost.py
│   ├── seismic_risk.py
│   ├── environmental.py
│   └── social.py
├── constraints/              # Restricciones
│   ├── __init__.py
│   ├── geographic.py
│   ├── distance.py
│   └── normative.py
├── operators/                # Operadores genéticos
│   ├── __init__.py
│   ├── crossover.py
│   ├── mutation.py
│   └── selection.py
├── analysis/                 # Análisis de resultados
│   ├── __init__.py
│   ├── pareto.py
│   ├── sensitivity.py
│   └── decision.py
├── visualization/            # Visualización
│   ├── __init__.py
│   └── pareto_plots.py
└── README.md                 # Este archivo
```

---

## Dependencias

```python
# Core
numpy>=1.21.0
scipy>=1.7.0

# Optimización
pymoo>=0.6.0            # Framework NSGA-II (opcional)
deap>=1.3.0             # Alternativa

# Análisis espacial
geopandas>=0.10.0
shapely>=1.8.0
rasterio>=1.2.0

# Visualización
matplotlib>=3.5.0
plotly>=5.0.0           # Gráficos 3D interactivos
```

---

## Referencias

- Deb, K., et al. (2002). "A fast and elitist multiobjective genetic algorithm: NSGA-II." *IEEE Transactions on Evolutionary Computation*, 6(2), 182-197.
- Coello, C.A.C., et al. (2007). "Evolutionary Algorithms for Solving Multi-Objective Problems." *Springer*.

---

## Véase También

- [`seismex.analysis`](../analysis/README.md) - Análisis ESD y PSHA
- [`seismex.visualization`](../visualization/README.md) - Visualización de resultados
