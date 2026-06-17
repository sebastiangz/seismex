#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para seismex.optimization
===============================

Tests unitarios para el módulo de optimización multiobjetivo NSGA-II.
"""

import pytest
import numpy as np


class TestConfiguracionNSGAII:
    """Tests para ConfiguracionNSGAII."""
    
    def test_inicializacion_default(self):
        """Test inicialización con valores default."""
        from seismex.optimization import ConfiguracionNSGAII
        
        config = ConfiguracionNSGAII()
        
        assert config.n_generaciones == 100
        assert config.tamano_poblacion == 100
        assert 0 < config.prob_cruce < 1
        assert 0 < config.prob_mutacion < 1
    
    def test_inicializacion_personalizada(self):
        """Test inicialización con valores personalizados."""
        from seismex.optimization import ConfiguracionNSGAII
        
        config = ConfiguracionNSGAII(
            n_generaciones=200,
            tamano_poblacion=150,
            prob_cruce=0.95,
            prob_mutacion=0.05,
            n_sitios=5
        )
        
        assert config.n_generaciones == 200
        assert config.tamano_poblacion == 150
        assert config.n_sitios == 5


class TestIndividuo:
    """Tests para Individuo."""
    
    def test_crear_individuo(self):
        """Test creación de individuo."""
        from seismex.optimization import Individuo
        
        genes = np.array([19.5, -103.2, 18.8, -102.5])
        ind = Individuo(genes=genes, n_sitios=2)
        
        assert len(ind.genes) == 4
        assert ind.n_sitios == 2
    
    def test_valores_objetivo(self):
        """Test asignación de valores objetivo."""
        from seismex.optimization import Individuo
        
        ind = Individuo(genes=np.array([19.5, -103.2]), n_sitios=1)
        ind.valores_objetivo = [0.5, 0.3, 0.8]
        
        assert len(ind.valores_objetivo) == 3
    
    def test_dominancia(self):
        """Test relación de dominancia."""
        from seismex.optimization import Individuo
        
        ind1 = Individuo(genes=np.array([1, 2]), n_sitios=1)
        ind2 = Individuo(genes=np.array([3, 4]), n_sitios=1)
        
        # ind1 domina a ind2 si es mejor en todos los objetivos
        ind1.valores_objetivo = [0.2, 0.3]  # Menores = mejores
        ind2.valores_objetivo = [0.5, 0.6]
        
        assert ind1.domina(ind2)
        assert not ind2.domina(ind1)
    
    def test_no_dominancia_pareto(self):
        """Test soluciones no dominadas (Pareto)."""
        from seismex.optimization import Individuo
        
        ind1 = Individuo(genes=np.array([1, 2]), n_sitios=1)
        ind2 = Individuo(genes=np.array([3, 4]), n_sitios=1)
        
        # Trade-off: ind1 mejor en obj1, ind2 mejor en obj2
        ind1.valores_objetivo = [0.2, 0.8]
        ind2.valores_objetivo = [0.8, 0.2]
        
        assert not ind1.domina(ind2)
        assert not ind2.domina(ind1)
    
    def test_decodificar_coordenadas(self):
        """Test decodificación de genes a coordenadas."""
        from seismex.optimization import Individuo
        
        genes = np.array([19.5, -103.2, 18.8, -102.5])
        ind = Individuo(genes=genes, n_sitios=2)
        
        coords = ind.decodificar_coordenadas()
        
        assert len(coords) == 2
        assert coords[0] == (19.5, -103.2)
        assert coords[1] == (18.8, -102.5)
    
    def test_copiar(self):
        """Test copia de individuo."""
        from seismex.optimization import Individuo
        
        ind1 = Individuo(genes=np.array([1, 2, 3, 4]), n_sitios=2)
        ind1.valores_objetivo = [0.5, 0.3]
        
        ind2 = ind1.copiar()
        
        assert np.array_equal(ind1.genes, ind2.genes)
        assert ind1 is not ind2


class TestPoblacion:
    """Tests para Poblacion."""
    
    def test_crear_poblacion(self):
        """Test creación de población."""
        from seismex.optimization import Poblacion, Individuo
        
        individuos = [
            Individuo(genes=np.random.rand(4), n_sitios=2)
            for _ in range(10)
        ]
        
        pob = Poblacion(individuos=individuos)
        
        assert len(pob) == 10
    
    def test_generar_aleatoria(self):
        """Test generación de población aleatoria."""
        from seismex.optimization import Poblacion
        
        bounds = [(18, 20), (-104, -102)]  # lat, lon
        
        pob = Poblacion.generar_aleatoria(
            tamano=50,
            n_sitios=2,
            bounds=bounds
        )
        
        assert len(pob) == 50
        
        # Verificar que los genes están dentro de los bounds
        for ind in pob:
            coords = ind.decodificar_coordenadas()
            for lat, lon in coords:
                assert 18 <= lat <= 20
                assert -104 <= lon <= -102
    
    def test_obtener_frente_pareto(self):
        """Test obtención del frente de Pareto."""
        from seismex.optimization import Poblacion, Individuo
        
        # Crear población con objetivos conocidos
        individuos = []
        for i in range(10):
            ind = Individuo(genes=np.array([i, i]), n_sitios=1)
            # Trade-off lineal: mejor en obj1 = peor en obj2
            ind.valores_objetivo = [i / 10, 1 - i / 10]
            individuos.append(ind)
        
        pob = Poblacion(individuos=individuos)
        frente = pob.obtener_frente_pareto()
        
        # Todos deberían estar en el frente (trade-off)
        assert len(frente) == 10
    
    def test_estadisticas(self):
        """Test cálculo de estadísticas."""
        from seismex.optimization import Poblacion, Individuo
        
        individuos = []
        for i in range(20):
            ind = Individuo(genes=np.random.rand(4), n_sitios=2)
            ind.valores_objetivo = [np.random.rand(), np.random.rand()]
            ind.factible = True
            individuos.append(ind)
        
        pob = Poblacion(individuos=individuos)
        stats = pob.estadisticas()
        
        assert 'n_individuos' in stats
        assert 'n_factibles' in stats
        assert stats['n_individuos'] == 20


class TestFuncionesObjetivo:
    """Tests para funciones objetivo."""
    
    def test_objetivo_riesgo_esd(self):
        """Test función objetivo de riesgo ESD."""
        from seismex.optimization import objetivo_riesgo_esd
        
        # Crear grid ESD de prueba
        esd_grid = np.random.rand(10, 10)
        bounds = (-104, 18, -102, 20)  # lon_min, lat_min, lon_max, lat_max
        
        obj = objetivo_riesgo_esd(esd_grid, bounds)
        
        # Evaluar para un sitio
        sitios = [(19.0, -103.0)]
        valor = obj.evaluar(sitios)
        
        assert valor is not None
    
    def test_objetivo_costo_construccion(self):
        """Test función objetivo de costo."""
        from seismex.optimization import objetivo_costo_construccion
        
        obj = objetivo_costo_construccion()
        
        sitios = [(19.0, -103.0), (19.5, -102.5)]
        valor = obj.evaluar(sitios)
        
        assert valor >= 0
    
    def test_objetivo_accesibilidad(self):
        """Test función objetivo de accesibilidad."""
        from seismex.optimization import objetivo_accesibilidad
        
        pois = [(19.2, -103.2), (19.8, -102.8)]  # Points of interest
        
        obj = objetivo_accesibilidad(pois)
        
        sitios = [(19.5, -103.0)]
        valor = obj.evaluar(sitios)
        
        # Accesibilidad se maximiza (retorna negativo para minimizar)
        assert valor <= 0
    
    def test_objetivo_distancia_fallas(self):
        """Test función objetivo de distancia a fallas."""
        from seismex.optimization import objetivo_distancia_fallas
        
        fallas = [
            [(19.0, -104.0), (20.0, -103.0)],
            [(18.5, -103.0), (19.5, -102.0)]
        ]
        
        obj = objetivo_distancia_fallas(fallas)
        
        sitios = [(19.5, -102.5)]
        valor = obj.evaluar(sitios)
        
        # Distancia a fallas se maximiza (retorna negativo)
        assert valor <= 0
    
    def test_objetivo_pendiente(self):
        """Test función objetivo de pendiente."""
        from seismex.optimization import objetivo_pendiente
        
        dem = np.random.rand(20, 20) * 1000  # Elevación en metros
        bounds = (-104, 18, -102, 20)
        
        obj = objetivo_pendiente(dem, bounds)
        
        sitios = [(19.0, -103.0)]
        valor = obj.evaluar(sitios)
        
        assert valor >= 0
    
    def test_crear_objetivo_personalizado(self):
        """Test creación de objetivo personalizado."""
        from seismex.optimization import crear_objetivo_personalizado
        
        def mi_funcion(sitios):
            return sum(lat + lon for lat, lon in sitios)
        
        obj = crear_objetivo_personalizado(
            nombre="Mi Objetivo",
            funcion=mi_funcion,
            minimizar=True
        )
        
        sitios = [(19.0, -103.0)]
        valor = obj.evaluar(sitios)
        
        assert valor == 19.0 + (-103.0)


class TestRestricciones:
    """Tests para restricciones."""
    
    def test_restriccion_uso_suelo(self):
        """Test restricción de uso de suelo."""
        from seismex.optimization import restriccion_uso_suelo
        
        # Crear raster de uso de suelo (1 = permitido, 0 = prohibido)
        uso_suelo = np.ones((10, 10))
        uso_suelo[5:, :] = 0  # Mitad inferior prohibida
        bounds = (-104, 18, -102, 20)
        
        rest = restriccion_uso_suelo(uso_suelo, bounds, usos_permitidos=[1])
        
        # Punto en zona permitida
        sitios_ok = [(19.5, -103.0)]
        assert rest.es_factible(sitios_ok)
        
        # Punto en zona prohibida
        sitios_bad = [(18.5, -103.0)]
        assert not rest.es_factible(sitios_bad)
    
    def test_restriccion_pendiente_maxima(self):
        """Test restricción de pendiente máxima."""
        from seismex.optimization import restriccion_pendiente
        
        # Crear DEM con pendiente variable
        dem = np.zeros((20, 20))
        dem[:, 10:] = 500  # Escalón abrupto
        bounds = (-104, 18, -102, 20)
        
        rest = restriccion_pendiente(dem, bounds, pendiente_maxima=10)
        
        # La factibilidad depende de dónde caiga el punto
        sitios = [(19.0, -103.0)]
        resultado = rest.evaluar(sitios)
        
        assert resultado is not None
    
    def test_restriccion_distancia_minima(self):
        """Test restricción de distancia mínima entre sitios."""
        from seismex.optimization import restriccion_distancia_minima
        
        rest = restriccion_distancia_minima(distancia_km=50)
        
        # Sitios muy cercanos (< 50 km)
        sitios_cercanos = [(19.0, -103.0), (19.1, -103.0)]
        assert not rest.es_factible(sitios_cercanos)
        
        # Sitios alejados (> 50 km)
        sitios_lejanos = [(19.0, -103.0), (20.0, -102.0)]
        assert rest.es_factible(sitios_lejanos)
    
    def test_restriccion_zona_protegida(self):
        """Test restricción de zona protegida."""
        from seismex.optimization import restriccion_zona_protegida
        
        # Polígono de ANP
        anp = [(19.0, -103.5), (19.5, -103.5), (19.5, -103.0), (19.0, -103.0)]
        
        rest = restriccion_zona_protegida(poligonos=[anp])
        
        # Punto dentro del ANP
        sitios_dentro = [(19.25, -103.25)]
        assert not rest.es_factible(sitios_dentro)
        
        # Punto fuera del ANP
        sitios_fuera = [(18.5, -102.5)]
        assert rest.es_factible(sitios_fuera)
    
    def test_restriccion_buffer_fallas(self):
        """Test restricción de buffer alrededor de fallas."""
        from seismex.optimization import restriccion_buffer_fallas
        
        fallas = [[(19.0, -103.0), (19.5, -102.5)]]
        
        rest = restriccion_buffer_fallas(fallas, buffer_km=20)
        
        # Evaluar cerca de la falla
        sitios = [(19.25, -102.75)]
        resultado = rest.evaluar(sitios)
        
        assert resultado is not None
    
    def test_crear_restriccion_personalizada(self):
        """Test creación de restricción personalizada."""
        from seismex.optimization import crear_restriccion_personalizada
        
        def mi_restriccion(sitios):
            # Todos los sitios deben estar al norte de lat 19
            for lat, lon in sitios:
                if lat < 19:
                    return 19 - lat  # Violación
            return 0
        
        rest = crear_restriccion_personalizada(
            nombre="Norte de 19",
            funcion=mi_restriccion
        )
        
        assert rest.es_factible([(19.5, -103.0)])
        assert not rest.es_factible([(18.5, -103.0)])


class TestOptimizadorNSGAII:
    """Tests para OptimizadorNSGAII."""
    
    def test_inicializacion(self):
        """Test inicialización del optimizador."""
        from seismex.optimization import OptimizadorNSGAII, ConfiguracionNSGAII
        
        config = ConfiguracionNSGAII(n_generaciones=10, tamano_poblacion=20)
        opt = OptimizadorNSGAII(config)
        
        assert opt.config.n_generaciones == 10
        assert len(opt.objetivos) == 0
        assert len(opt.restricciones) == 0
    
    def test_agregar_objetivo(self):
        """Test agregar funciones objetivo."""
        from seismex.optimization import (
            OptimizadorNSGAII, ConfiguracionNSGAII,
            objetivo_costo_construccion
        )
        
        opt = OptimizadorNSGAII(ConfiguracionNSGAII())
        opt.agregar_objetivo(objetivo_costo_construccion())
        
        assert len(opt.objetivos) == 1
    
    def test_agregar_restriccion(self):
        """Test agregar restricciones."""
        from seismex.optimization import (
            OptimizadorNSGAII, ConfiguracionNSGAII,
            restriccion_distancia_minima
        )
        
        opt = OptimizadorNSGAII(ConfiguracionNSGAII())
        opt.agregar_restriccion(restriccion_distancia_minima(50))
        
        assert len(opt.restricciones) == 1
    
    def test_optimizar_basico(self):
        """Test optimización básica."""
        from seismex.optimization import (
            OptimizadorNSGAII, ConfiguracionNSGAII,
            objetivo_costo_construccion,
            restriccion_distancia_minima
        )
        
        config = ConfiguracionNSGAII(
            n_generaciones=5,  # Pocas generaciones para test rápido
            tamano_poblacion=20,
            n_sitios=2
        )
        
        opt = OptimizadorNSGAII(config)
        opt.agregar_objetivo(objetivo_costo_construccion())
        opt.agregar_restriccion(restriccion_distancia_minima(10))
        
        resultado = opt.optimizar(
            bounds=[(18, 20), (-104, -102)]
        )
        
        assert resultado is not None
        assert len(resultado.frente_pareto) > 0


class TestResultadoOptimizacion:
    """Tests para ResultadoOptimizacion."""
    
    @pytest.fixture
    def resultado_ejemplo(self):
        """Crea un resultado de ejemplo."""
        from seismex.optimization import ResultadoOptimizacion, Individuo
        
        # Crear frente de Pareto de ejemplo
        frente = []
        for i in range(10):
            ind = Individuo(genes=np.array([19 + i/10, -103 + i/10]), n_sitios=1)
            ind.valores_objetivo = [i/10, 1 - i/10]
            frente.append(ind)
        
        return ResultadoOptimizacion(
            frente_pareto=frente,
            historial_convergencia=[0.5, 0.4, 0.3, 0.2, 0.15],
            tiempo_ejecucion=5.0,
            n_generaciones=5,
            n_evaluaciones=100
        )
    
    def test_resumen(self, resultado_ejemplo):
        """Test generación de resumen."""
        resumen = resultado_ejemplo.resumen()
        
        assert "Pareto" in resumen or "soluciones" in resumen.lower()
    
    def test_obtener_solucion_compromiso(self, resultado_ejemplo):
        """Test obtención de solución de compromiso."""
        solucion = resultado_ejemplo.obtener_solucion_compromiso()
        
        assert solucion is not None
    
    def test_to_dataframe(self, resultado_ejemplo):
        """Test conversión a DataFrame."""
        df = resultado_ejemplo.to_dataframe()
        
        assert df is not None
        assert len(df) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
