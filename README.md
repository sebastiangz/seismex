**SEISMEX**

Sistema de Análisis Sísmico para México

Propuesta Conceptual y Arquitectura de Sistema

Integración de:

*Energy Space Density (ESD) \| Mapas de Isosistas \| Análisis de Peligro
Sísmico (PGA)*

*Optimización Multi-objetivo con Algoritmos Genéticos*

Marzo 2026

1\. Resumen ejecutivo

SEISMEX es una propuesta de sistema integrado para el análisis sísmico a
escala nacional de México, diseñado para proporcionar herramientas
avanzadas de visualización, análisis y toma de decisiones en materia de
riesgo sísmico.

El sistema integra cuatro capacidades principales: generación
automatizada de mapas de isosistas (intensidades sísmicas en escala
Mercalli Modificada), cálculo de la Densidad Espacial de Energía Sísmica
(ESD) basado en la metodología de Del Pezzo et al. (2024), análisis
probabilístico de peligro sísmico (PSHA) para cálculo de PGA, y
optimización multi-objetivo mediante algoritmos genéticos (NSGA-II) para
la selección de sitios considerando restricciones sísmicas.

La arquitectura propuesta permite su aplicación en planificación urbana,
evaluación de riesgo para infraestructura crítica, y generación de
escenarios sísmicos para protección civil.

2\. Justificación y contexto

2.1 Contexto sismotectónico de México

México se encuentra en una de las zonas de mayor actividad sísmica del
mundo debido a la interacción de cinco placas tectónicas:
Norteamericana, Pacífico, Cocos, Rivera y Caribe. La zona de subducción
a lo largo de la Trinchera Mesoamericana genera sismos de gran magnitud
con periodos de recurrencia de 25-30 años para eventos Mw mayor a 7.5.

La región Occidente (Colima, Jalisco, Michoacán) presenta una tectónica
particularmente compleja con la interacción de las placas de Cocos y
Rivera, separadas por el graben El Gordo. Esta configuración ha generado
sismos destructivos como los de 1985 (Mw 8.1), 1995 (Mw 8.0), 2003 (Mw
7.6) y 2022 (Mw 7.7).

2.2 Necesidad del sistema

- Inexistencia de herramientas integradas que combinen análisis ESD con
  optimización espacial

- Necesidad de visualización moderna compatible con GIS y Google Earth
  Engine

- Requerimiento de metodologías reproducibles para evaluación de riesgo
  sísmico

- Demanda de herramientas para optimización de ubicación de
  infraestructura crítica

3\. Fundamentos metodológicos

3.1 Energy Space Density (ESD)

La técnica ESD, desarrollada por Del Pezzo (2023) y aplicada
exitosamente en ambientes volcánicos y tectónicos, proporciona una
representación de la distribución espacial de la energía sísmica
liberada. Se basa en la relación empírica entre magnitud momento y
energía:

*E(x) = 10\^(1.5\*Mw(x) + 11.8)*

La ESD se define como la energía acumulada dentro de celdas
tridimensionales relativa a la energía total de la región. El método
asume que la densidad de fracturas generadas por dislocaciones
cosísmicas es proporcional a la energía liberada.

3.2 Generación de isosistas

Los mapas de isosistas representan curvas de igual intensidad sísmica
(escala Mercalli Modificada). Se generan mediante ecuaciones de
atenuación específicas para México y técnicas de interpolación espacial
(IDW, Kriging). Las intensidades se calculan a partir de la magnitud,
distancia epicentral y condiciones del sitio.

3.3 Análisis probabilístico de peligro sísmico (PSHA)

El PSHA calcula la probabilidad de excedencia de un nivel dado de
movimiento del terreno (típicamente PGA) en un período de tiempo
determinado. Utiliza modelos de fuentes sísmicas, relaciones de
recurrencia Gutenberg-Richter, y ecuaciones de movimiento fuerte (GMPEs)
calibradas para México.

3.4 Optimización con algoritmos genéticos

Se implementa NSGA-II (Non-dominated Sorting Genetic Algorithm II) para
optimización multi-objetivo. Los objetivos típicos incluyen: minimizar
exposición al peligro sísmico, minimizar costos de
construcción/operación, y minimizar impacto ambiental. La biblioteca
DEAP (Distributed Evolutionary Algorithms in Python) proporciona la
infraestructura computacional.

4\. Arquitectura del sistema

4.1 Capa 1: Fuentes de datos

  ----------------- -------------------- ------------------- -------------------
     **Fuente**      **Tipo de datos**       **Formato**      **Actualización**

     SSN México       Catálogo sísmico      CSV/API REST         Tiempo real
                          nacional                           

       ISC-GEM        Catálogo global          ISF/CSV              Anual
                       homogeneizado                         

      USGS NEIC       Sismos globales        GeoJSON/API         Tiempo real
                           M\>4.5                            

      Catálogos            Sismos           Digitalizado          Estático
     históricos      pre-instrumentales                      

     Redes GNSS         Deformación       RINEX/Velocidades       Continuo
                        superficial                          
  ----------------- -------------------- ------------------- -------------------

4.2 Capa 2: Preprocesamiento

1.  **Homogenización de magnitudes:** Conversión Ml a Mw usando
    relaciones empíricas regionales.

2.  **Análisis Gutenberg-Richter:** Cálculo del valor-b y magnitud de
    completitud (Mc) mediante método de Monte Carlo.

3.  **Filtrado espacial y temporal:** Selección de eventos por región,
    profundidad y período de análisis.

4.  **Control de calidad:** Verificación de coordenadas, eliminación de
    duplicados, validación de magnitudes.

4.3 Capa 3: Módulos de análisis

4.3.1 Módulo de isosistas

- Ecuaciones de atenuación: Implementación de GMPEs para México (e.g.,
  Ordaz et al., García et al.)

- Interpolación espacial: IDW (Inverse Distance Weighting) y Kriging
  ordinario

- Conversión PGV/PGA a intensidad MM: Relaciones empíricas calibradas

- Generación de contornos: Algoritmo marching squares con suavizado

4.3.2 Módulo ESD

- Discretización 3D: Celdas cúbicas de 10x10x10 km con desplazamiento de
  2.5 km

- Cálculo de energía: E = 10\^(1.5\*Mw + 11.8) para cada evento

- Normalización: Por capa de profundidad y por energía total

- Visualización: Secciones horizontales y verticales con escala
  logarítmica

4.3.3 Módulo de peligro sísmico (PGA)

- Modelo de fuentes: Zonas sismogénicas basadas en CFE 2015

- Relaciones de recurrencia: Gutenberg-Richter con truncamiento

- GMPEs: Modelos específicos para subducción y fallas corticales

- Períodos de retorno: 100, 475, 2475 años (10%, 2%, 1% en 50 años)

4.3.4 Módulo de optimización AG

  ------------------ ------------------ ---------------------------------
    **Parámetro**         **Valor                **Descripción**
                       recomendado**    

   Tamaño población       100-200           Número de individuos por
                                                   generación

     Generaciones          50-100           Iteraciones del algoritmo

     Prob. cruce            0.85          Probabilidad de recombinación

    Prob. mutación          0.15            Probabilidad de mutación

    Tamaño torneo            3             Individuos en selección por
                                                     torneo

      Algoritmo           NSGA-II          Optimización multi-objetivo
                                                     Pareto
  ------------------ ------------------ ---------------------------------

4.4 Capa 4: Visualización y salidas

  --------------------- ------------------------------ -------------------
     **Herramienta**             **Función**              **Formatos de
                                                            salida**

   Google Earth Engine    Análisis geoespacial en la   Mapas interactivos,
                         nube, batimetría, topografía         tiles

          QGIS             Análisis espacial local,     SHP, GeoTIFF, PDF
                                 cartografía           

      Folium/Geemap         Mapas web interactivos        HTML, Leaflet

         Plotly          Visualización 3D, frentes de   HTML interactivo
                                    Pareto             

       Matplotlib            Gráficos estáticos,          PNG, SVG, PDF
                                publicaciones          
  --------------------- ------------------------------ -------------------

5\. Especificaciones técnicas

5.1 Requerimientos de software

  ---------------------- ------------------------------ -----------------
      **Componente**             **Tecnología**             **Versión
                                                            mínima**

    Lenguaje principal               Python                   3.10+

   Algoritmos genéticos               DEAP                    1.4+

   Análisis geoespacial   GeoPandas, Shapely, Rasterio  0.14+, 2.0+, 1.3+

   Google Earth Engine      earthengine-api, geemap      0.1.380+, 0.30+

      Visualización        Matplotlib, Plotly, Folium     3.7+, 5.18+,
                                                              0.15+

     Cálculo numérico             NumPy, SciPy            1.24+, 1.11+

      Interpolación          PyKrige, scikit-learn         1.7+, 1.3+
  ---------------------- ------------------------------ -----------------

5.2 Estructura de datos del catálogo sísmico

  ---------------- ----------- -------------------------- ---------------------
     **Campo**      **Tipo**        **Descripción**            **Ejemplo**

     fecha_utc      datetime      Fecha y hora UTC del     2022-09-19T18:05:06
                                         evento           

      latitud         float      Latitud del epicentro           18.2377
                                        (grados)          

      longitud        float      Longitud del epicentro         -103.269
                                        (grados)          

   profundidad_km     float     Profundidad focal en km           12.1

      magnitud        float       Magnitud del evento              7.7

   tipo_magnitud     string    Tipo de magnitud (Mw, Ml,           Mw
                                          mb)             

       fuente        string         Fuente del dato                SSN
  ---------------- ----------- -------------------------- ---------------------

6\. Funciones objetivo para algoritmos genéticos

6.1 Objetivo 1: Minimizar exposición sísmica

Se define como la combinación de la distancia inversa a las zonas de
máxima liberación de energía (identificadas por ESD) y el PGA esperado
en el sitio:

*f₁(x,y) = w₁·(1/d_ESD) + w₂·PGA(x,y,T)*

Donde d_ESD es la distancia mínima a celdas con ESD normalizado mayor a
0.01, y T es el período de retorno seleccionado.

6.2 Objetivo 2: Minimizar costo operativo

Para aplicaciones de infraestructura, se considera la distancia a puntos
de interés (puertos, ciudades, redes de transporte):

*f₂(x,y) = Σᵢ wᵢ·dᵢ(x,y)*

6.3 Objetivo 3: Minimizar impacto ambiental

Basado en la proximidad a áreas protegidas, ecosistemas sensibles y
zonas de recarga acuífera:

*f₃(x,y) = max(0, r_buffer - d_ecosistema)*

6.4 Restricciones

- Restricciones geométricas: Límites del área de estudio, distancias
  mínimas a fallas activas

- Restricciones geotécnicas: Pendiente máxima, profundidad del nivel
  freático

- Restricciones normativas: Uso de suelo, zonas federales, áreas
  protegidas

- Restricciones de peligro: Intensidad máxima aceptable, PGA umbral

7\. Casos de uso

7.1 Planificación urbana

Identificación de zonas de menor peligro sísmico para expansión urbana
mediante la combinación de mapas ESD con análisis de PGA. Generación de
mapas de aptitud del territorio con escala de 1:50,000.

7.2 Evaluación de infraestructura crítica

Análisis de riesgo para hospitales, escuelas, puentes y líneas vitales.
Optimización de ubicación de nuevas instalaciones considerando
escenarios sísmicos de diseño.

7.3 Escenarios para protección civil

Generación rápida de mapas de isosistas post-evento para evaluación de
daños. Simulación de escenarios sísmicos basados en sismicidad histórica
e instrumental.

7.4 Proyectos de inversión

Evaluación de sitios para proyectos portuarios, industriales o
energéticos. Análisis costo-beneficio incorporando el riesgo sísmico en
la selección de alternativas.

8\. Plan de implementación propuesto

  ------------------ -------------- ----------------------------------------
       **Fase**       **Duración**              **Entregables**

      1\. Diseño        2 meses      Especificación técnica, diseño de base
      detallado                         de datos, prototipos de interfaz

    2\. Módulo de       2 meses             Conectores SSN/ISC/USGS,
        datos                           preprocesamiento, validación QC

    3\. Módulo ESD      2 meses        Algoritmo ESD 3D, visualización de
                                           secciones, integración GEE

      4\. Módulo        2 meses     Ecuaciones de atenuación, interpolación,
      isosistas                               generación de mapas

    5\. Módulo PGA      2 meses      PSHA probabilístico, mapas de peligro
                                             por período de retorno

    6\. Módulo AG       2 meses           NSGA-II, funciones objetivo,
                                        restricciones, frentes de Pareto

   7\. Integración      2 meses       API unificada, interfaz de usuario,
                                                 documentación

    8\. Validación      2 meses      Pruebas con casos reales, calibración,
                                                  publicación
  ------------------ -------------- ----------------------------------------

9\. Referencias

Del Pezzo, E. (2023). Space distribution of the seismic source energy at
Campi Flegrei caldera. Physics of the Earth and Planetary Interiors,
336, 106986.

Del Pezzo, E., & Bianco, F. (2024). Space and time distribution of
seismic source energy at Campi Flegrei. Physics of the Earth and
Planetary Interiors, 356, 107258.

Del Pezzo, E., Ibáñez, J.M., Stich, D., Prudencio, J., & Bianco, F.
(2025). Seismo-Genetic Structures of Southern Spain Revealed by Energy
Space Density Analysis. Geophysical Research Letters (en revisión).

Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T.A.M.T. (2002). A fast
and elitist multiobjective genetic algorithm: NSGA-II. IEEE Transactions
on Evolutionary Computation, 6(2), 182-197.

Ordaz, M., & Reyes, C. (1999). Earthquake hazard in Mexico City:
Observations versus computations. Bulletin of the Seismological Society
of America, 89(5), 1379-1383.

CFE (2015). Manual de diseño de obras civiles: Diseño por sismo.
Comisión Federal de Electricidad, México.

CENAPRED (2006). Guía básica para la elaboración de atlas estatales y
municipales de peligros y riesgos. Centro Nacional de Prevención de
Desastres, México.

*--- Fin del documento ---*
