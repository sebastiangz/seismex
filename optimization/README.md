# SEISMEX Optimization

Módulo de optimización multiobjetivo para ubicación óptima de infraestructura considerando riesgo sísmico.

## Estado: 🚧 PLANIFICADO

Este módulo está en fase de planificación. La estructura y las interfaces están definidas, pero la implementación completa está pendiente.

## Descripción

El módulo `seismex.optimization` implementa el algoritmo **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) para resolver problemas de optimización multiobjetivo en el contexto de análisis de riesgo sísmico.

### Caso de uso principal

Encontrar ubicaciones óptimas para infraestructura crítica (hospitales, escuelas, plantas industriales) que minimicen el riesgo sísmico mientras optimizan otros objetivos como costo, accesibilidad e impacto ambiental.

## Estructura del módulo

```
seismex/optimization/
├── __init__.py       # Exportaciones y estado del módulo
├── genetic.py        # Motor NSGA-II
├── objectives.py     # Funciones objetivo predefinidas
├── constraints.py    # Restricciones predefinidas
└── README.md         # Esta documentación
```

## Componentes

### Motor NSGA-II (`genetic.py`)

| Clase | Descripción | Estado |
|-------|-------------|--------|
| `ConfiguracionNSGAII` | Parámetros del algoritmo | ✅ Definida |
| `Individuo` | Representación de solución candidata | ✅ Definida |
| `Poblacion` | Conjunto de individuos | ✅ Definida |
| `OptimizadorNSGAII` | Motor principal de optimización | 🚧 Estructura |

### Funciones objetivo (`objectives.py`)

| Función | Descripción | Estado |
|---------|-------------|--------|
| `objetivo_riesgo_esd()` | Minimizar riesgo sísmico (ESD) | 🚧 Estructura |
| `objetivo_costo_construccion()` | Minimizar costo de construcción | 🚧 Estructura |
| `objetivo_impacto_ambiental()` | Minimizar impacto ambiental | 🚧 Estructura |
| `objetivo_accesibilidad()` | Maximizar accesibilidad | 🚧 Estructura |
| `objetivo_distancia_fallas()` | Maximizar distancia a fallas | 🚧 Estructura |
| `objetivo_distancia_volcanes()` | Maximizar distancia a volcanes | 🚧 Estructura |
| `objetivo_pendiente()` | Minimizar pendiente del terreno | 🚧 Estructura |
| `crear_objetivo_personalizado()` | Factory para objetivos lambda | ✅ Definida |

### Restricciones (`constraints.py`)

| Función | Descripción | Estado |
|---------|-------------|--------|
| `restriccion_uso_suelo()` | Limitar a zonas permitidas | 🚧 Estructura |
| `restriccion_pendiente()` | Pendiente máxima | 🚧 Estructura |
| `restriccion_zona_inundable()` | Evitar zonas inundables | 🚧 Estructura |
| `restriccion_distancia_minima()` | Distancia entre sitios | ✅ Implementada |
| `restriccion_capacidad()` | Límites de capacidad | 🚧 Estructura |
| `restriccion_zona_protegida()` | Evitar ANPs | 🚧 Estructura |
| `restriccion_buffer_fallas()` | Distancia a fallas | 🚧 Estructura |
| `restriccion_elevacion()` | Rango de elevación | 🚧 Estructura |
| `crear_restriccion_personalizada()` | Factory para restricciones | ✅ Definida |

## Uso planificado

```python
from seismex.optimization import (
    OptimizadorNSGAII,
    ConfiguracionNSGAII,
    objetivo_riesgo_esd,
    objetivo_costo_construccion,
    restriccion_uso_suelo,
    restriccion_distancia_minima
)

# Configurar algoritmo
config = ConfiguracionNSGAII(
    n_generaciones=100,
    tamano_poblacion=200,
    prob_cruce=0.9,
    prob_mutacion=0.1,
    n_sitios=3  # Optimizar ubicación de 3 sitios
)

# Crear optimizador
optimizador = OptimizadorNSGAII(config)

# Agregar funciones objetivo (minimización)
optimizador.agregar_objetivo(objetivo_riesgo_esd(resultado_esd))
optimizador.agregar_objetivo(objetivo_costo_construccion(mapa_costos))

# Agregar restricciones
optimizador.agregar_restriccion(restriccion_uso_suelo(uso_suelo_permitido))
optimizador.agregar_restriccion(restriccion_distancia_minima(distancia_km=5))

# Definir región de estudio (lat_min, lat_max), (lon_min, lon_max)
region = [(18.0, 21.0), (-105.0, -102.0)]

# Ejecutar optimización
resultado = optimizador.optimizar(region)

# Analizar resultados
print(f"Soluciones en frente de Pareto: {len(resultado.frente_pareto)}")
resultado.graficar_pareto()
resultado.exportar_geojson('soluciones_optimas.geojson')
```

## Algoritmo NSGA-II

El algoritmo NSGA-II es un algoritmo evolutivo multiobjetivo que:

1. **Inicializa** una población aleatoria de soluciones
2. **Evalúa** cada solución en todas las funciones objetivo
3. **Ordena** por dominancia de Pareto (non-dominated sorting)
4. **Calcula** crowding distance para diversidad
5. **Selecciona** padres por torneo
6. **Cruza** (SBX - Simulated Binary Crossover)
7. **Muta** (Polynomial Mutation)
8. **Combina** población padre e hijos
9. **Selecciona** siguiente generación (elitismo)
10. **Repite** hasta convergencia o máximo de generaciones

### Referencia

> Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). 
> "A fast and elitist multiobjective genetic algorithm: NSGA-II."
> *IEEE Transactions on Evolutionary Computation*, 6(2), 182-197.

## Dependencias

### Requeridas
- `numpy` >= 1.20.0
- `scipy` >= 1.7.0

### Opcionales
- `deap` - Puede acelerar la optimización
- `geopandas` - Para restricciones geográficas
- `rasterio` - Para trabajar con DEMs y rasters

## Roadmap de implementación

### Fase 1: Core NSGA-II
- [ ] Implementar `_non_dominated_sorting()`
- [ ] Implementar `_calcular_crowding_distance()`
- [ ] Implementar `_seleccion_torneo()`
- [ ] Implementar `_cruce_sbx()`
- [ ] Implementar `_mutacion_polinomial()`
- [ ] Completar `optimizar()`

### Fase 2: Objetivos
- [ ] Implementar `objetivo_riesgo_esd()` con interpolación
- [ ] Implementar `objetivo_costo_construccion()`
- [ ] Implementar objetivos geográficos

### Fase 3: Restricciones
- [ ] Implementar verificación con GeoDataFrames
- [ ] Implementar interpolación de rasters (DEM)
- [ ] Manejo de restricciones con constraint-handling

### Fase 4: Resultados
- [ ] Crear clase `ResultadoOptimizacion`
- [ ] Visualización de frente de Pareto
- [ ] Exportación a GeoJSON/Shapefile
- [ ] Análisis de sensibilidad

## Contribuir

Para contribuir al desarrollo de este módulo:

1. Ver `CONTRIBUTING.md` en la raíz del proyecto
2. Revisar los issues etiquetados con `optimization`
3. Seguir el estilo de código existente
4. Incluir tests para nuevas funcionalidades

## Tests pendientes

```bash
# Cuando esté implementado:
pytest tests/test_optimization.py -v
```

---

**Nota:** Este módulo está en desarrollo activo. Las interfaces pueden cambiar antes de la versión 1.0.0.
