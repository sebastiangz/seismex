# SEISMEX Optimization

Módulo de optimización multiobjetivo para ubicación óptima de infraestructura considerando riesgo sísmico.

## Estado: ✅ IMPLEMENTADO

Este módulo está completamente implementado y listo para usar.

## Descripción

El módulo `seismex.optimization` implementa el algoritmo **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) para resolver problemas de optimización multiobjetivo en el contexto de análisis de riesgo sísmico.

### Caso de uso principal

Encontrar ubicaciones óptimas para infraestructura crítica (hospitales, escuelas, plantas industriales) que minimicen el riesgo sísmico mientras optimizan otros objetivos como costo, accesibilidad e impacto ambiental.

## Instalación

El módulo se instala como parte de SEISMEX:

```bash
pip install seismex
```

### Dependencias

**Requeridas:**
- `numpy` >= 1.20.0

**Opcionales:**
- `scipy` >= 1.7.0 - Para operaciones avanzadas
- `matplotlib` >= 3.4.0 - Para visualización
- `geopandas` >= 0.10.0 - Para exportación geográfica
- `shapely` >= 1.8.0 - Para geometrías

## Estructura del módulo

```
seismex/optimization/
├── __init__.py       # Exportaciones y funciones de información
├── genetic.py        # Motor NSGA-II completo
├── objectives.py     # Funciones objetivo predefinidas
├── constraints.py    # Restricciones predefinidas
└── README.md         # Esta documentación
```

## Uso rápido

```python
from seismex.optimization import (
    OptimizadorNSGAII,
    ConfiguracionNSGAII,
    objetivo_riesgo_esd,
    objetivo_costo_construccion,
    restriccion_distancia_minima,
    restriccion_zona_protegida
)

# 1. Configurar algoritmo
config = ConfiguracionNSGAII(
    n_generaciones=100,
    tamano_poblacion=200,
    prob_cruce=0.9,
    prob_mutacion=0.1,
    n_sitios=3  # Optimizar ubicación de 3 sitios
)

# 2. Crear optimizador
optimizador = OptimizadorNSGAII(config)

# 3. Agregar funciones objetivo (minimización)
optimizador.agregar_objetivo(objetivo_riesgo_esd(esd_grid, bounds))
optimizador.agregar_objetivo(objetivo_costo_construccion(mapa_costos, bounds))

# 4. Agregar restricciones
optimizador.agregar_restriccion(restriccion_distancia_minima(distancia_km=5))
optimizador.agregar_restriccion(restriccion_zona_protegida(zonas_anp))

# 5. Definir región de estudio
region = [(18.0, 21.0), (-105.0, -102.0)]  # (lat_min, lat_max), (lon_min, lon_max)

# 6. Ejecutar optimización
resultado = optimizador.optimizar(region)

# 7. Analizar resultados
print(f"Soluciones en frente de Pareto: {len(resultado.frente_pareto)}")
resultado.graficar_pareto()

# 8. Obtener solución de compromiso
mejor = resultado.obtener_solucion_compromiso()
print("Ubicaciones óptimas:")
for i, (lat, lon) in enumerate(mejor.decodificar_coordenadas()):
    print(f"  Sitio {i+1}: ({lat:.4f}°N, {lon:.4f}°W)")

# 9. Exportar resultados
resultado.exportar_geojson('soluciones_optimas.geojson')
```

## Componentes

### Motor NSGA-II (`genetic.py`)

| Clase | Descripción |
|-------|-------------|
| `ConfiguracionNSGAII` | Parámetros del algoritmo (generaciones, población, probabilidades) |
| `Individuo` | Representación de una solución candidata |
| `Poblacion` | Conjunto de individuos con operaciones de población |
| `ResultadoOptimizacion` | Contenedor de resultados con visualización y exportación |
| `OptimizadorNSGAII` | Motor principal de optimización |

**Operadores implementados:**
- ✅ Fast Non-dominated Sorting
- ✅ Crowding Distance
- ✅ Selección por Torneo
- ✅ Simulated Binary Crossover (SBX)
- ✅ Mutación Polinomial

### Funciones objetivo (`objectives.py`)

| Función | Descripción |
|---------|-------------|
| `objetivo_riesgo_esd()` | Minimizar riesgo sísmico basado en ESD |
| `objetivo_costo_construccion()` | Minimizar costo de construcción |
| `objetivo_impacto_ambiental()` | Minimizar impacto ambiental |
| `objetivo_accesibilidad()` | Maximizar accesibilidad a servicios |
| `objetivo_distancia_fallas()` | Maximizar distancia a fallas geológicas |
| `objetivo_distancia_volcanes()` | Maximizar distancia a volcanes activos |
| `objetivo_pendiente()` | Minimizar pendiente del terreno |
| `crear_objetivo_personalizado()` | Crear objetivo con función lambda |
| `crear_objetivo_compuesto()` | Combinar múltiples objetivos |

### Restricciones (`constraints.py`)

| Función | Descripción |
|---------|-------------|
| `restriccion_uso_suelo()` | Limitar a zonas con uso permitido |
| `restriccion_pendiente()` | Pendiente máxima del terreno |
| `restriccion_zona_inundable()` | Evitar zonas inundables |
| `restriccion_distancia_minima()` | Distancia mínima entre sitios |
| `restriccion_capacidad()` | Verificar capacidad del terreno |
| `restriccion_zona_protegida()` | Evitar áreas naturales protegidas |
| `restriccion_buffer_fallas()` | Buffer de seguridad a fallas |
| `restriccion_elevacion()` | Rango de elevación permitido |
| `restriccion_region()` | Límites de la región de estudio |
| `crear_restriccion_personalizada()` | Crear restricción con función lambda |
| `crear_restriccion_compuesta()` | Combinar múltiples restricciones |

## Ejemplos avanzados

### Objetivo personalizado

```python
from seismex.optimization import crear_objetivo_personalizado
import numpy as np

# Objetivo: minimizar distancia promedio a una lista de hospitales
hospitales = [(19.4, -103.5), (19.6, -103.8), (19.3, -103.4)]

objetivo_hospitales = crear_objetivo_personalizado(
    nombre="Distancia a hospitales",
    funcion=lambda coords: np.mean([
        min(np.sqrt((lat - h[0])**2 + (lon - h[1])**2) for h in hospitales)
        for lat, lon in coords
    ]),
    unidad="grados",
    descripcion="Minimiza distancia promedio a hospitales existentes"
)

optimizador.agregar_objetivo(objetivo_hospitales)
```

### Restricción personalizada

```python
from seismex.optimization import crear_restriccion_personalizada

# Restricción: todos los sitios deben estar al norte de latitud 19
restriccion_norte = crear_restriccion_personalizada(
    nombre="Norte de lat 19",
    funcion=lambda coords: sum(max(0, 19 - lat) for lat, lon in coords),
    descripcion="Penaliza sitios al sur de latitud 19"
)

optimizador.agregar_restriccion(restriccion_norte)
```

### Análisis de resultados

```python
# Obtener DataFrame del frente de Pareto
df = resultado.to_dataframe()
print(df.head())

# Obtener GeoDataFrame para análisis espacial
gdf = resultado.to_geodataframe()
gdf.plot(column='Riesgo Sísmico (ESD)', cmap='RdYlGn_r', legend=True)

# Visualizar convergencia
resultado.graficar_convergencia()

# Solución con pesos personalizados (priorizar bajo riesgo)
mejor = resultado.obtener_solucion_compromiso(pesos=[0.7, 0.3])
```

## Algoritmo NSGA-II

El algoritmo NSGA-II es un algoritmo evolutivo multiobjetivo que:

1. **Inicializa** una población aleatoria de soluciones
2. **Evalúa** cada solución en todas las funciones objetivo
3. **Ordena** por dominancia de Pareto (non-dominated sorting)
4. **Calcula** crowding distance para mantener diversidad
5. **Selecciona** padres por torneo binario
6. **Cruza** usando SBX (Simulated Binary Crossover)
7. **Muta** usando mutación polinomial
8. **Combina** población padre e hijos
9. **Selecciona** siguiente generación con elitismo
10. **Repite** hasta convergencia o máximo de generaciones

### Referencia

> Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). 
> "A fast and elitist multiobjective genetic algorithm: NSGA-II."
> *IEEE Transactions on Evolutionary Computation*, 6(2), 182-197.

## Parámetros del algoritmo

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `n_generaciones` | 100 | Número máximo de generaciones |
| `tamano_poblacion` | 100 | Tamaño de la población (debe ser par) |
| `prob_cruce` | 0.9 | Probabilidad de cruce |
| `prob_mutacion` | 0.1 | Probabilidad de mutación |
| `eta_cruce` | 20.0 | Índice de distribución para SBX |
| `eta_mutacion` | 20.0 | Índice de distribución para mutación |
| `n_sitios` | 1 | Número de sitios a optimizar |
| `semilla` | None | Semilla para reproducibilidad |

## Funciones de información

```python
from seismex.optimization import info, listar_componentes, ejemplo_basico

# Mostrar información del módulo
info()

# Listar todos los componentes
componentes = listar_componentes()
print(componentes)

# Ejecutar ejemplo básico
resultado = ejemplo_basico()
```

## Tests

```bash
# Ejecutar tests del módulo
pytest tests/test_optimization.py -v

# Con cobertura
pytest tests/test_optimization.py --cov=seismex.optimization
```

## Contribuir

Para contribuir al desarrollo de este módulo:

1. Ver `CONTRIBUTING.md` en la raíz del proyecto
2. Revisar los issues etiquetados con `optimization`
3. Seguir el estilo de código existente (PEP 8)
4. Incluir tests para nuevas funcionalidades
5. Documentar con docstrings estilo NumPy

---

**Versión:** 1.0.0  
**Autor:** SEISMEX Team  
**Licencia:** MIT
