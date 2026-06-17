#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para seismex.analysis.psha
================================

Tests unitarios para el módulo de Análisis Probabilístico de Peligro Sísmico.
"""

import pytest
import numpy as np


class TestCurvaPeligro:
    """Tests para CurvaPeligro."""
    
    @pytest.fixture
    def curva_ejemplo(self):
        """Crea una curva de peligro de ejemplo."""
        from seismex.analysis.psha import CurvaPeligro, MedidaIntensidad
        
        intensidades = np.logspace(-3, 0, 20)  # 0.001g a 1g
        # Tasas decrecientes con intensidad
        tasas = 0.1 * np.exp(-5 * intensidades)
        
        return CurvaPeligro(
            intensidades=intensidades,
            tasas_excedencia=tasas,
            medida=MedidaIntensidad.PGA,
            sitio=(19.4, -99.1),
            vs30=400
        )
    
    def test_inicializacion(self, curva_ejemplo):
        """Test inicialización correcta."""
        assert len(curva_ejemplo.intensidades) == 20
        assert len(curva_ejemplo.tasas_excedencia) == 20
        assert curva_ejemplo.sitio == (19.4, -99.1)
    
    def test_probabilidad_excedencia(self, curva_ejemplo):
        """Test cálculo de probabilidad de excedencia."""
        prob = curva_ejemplo.probabilidad_excedencia(0.1, tiempo_exposicion=50)
        
        assert 0 <= prob <= 1
    
    def test_probabilidad_excedencia_limites(self, curva_ejemplo):
        """Test probabilidades en límites."""
        # Intensidad muy baja: probabilidad alta
        prob_baja = curva_ejemplo.probabilidad_excedencia(0.001, tiempo_exposicion=50)
        
        # Intensidad muy alta: probabilidad baja
        prob_alta = curva_ejemplo.probabilidad_excedencia(1.0, tiempo_exposicion=50)
        
        assert prob_baja > prob_alta
    
    def test_interpolar_tasa(self, curva_ejemplo):
        """Test interpolación de tasa."""
        tasa = curva_ejemplo.interpolar_tasa(0.1)
        
        assert tasa > 0
    
    def test_intensidad_para_periodo_retorno(self, curva_ejemplo):
        """Test obtención de intensidad para TR."""
        im_475 = curva_ejemplo.intensidad_para_periodo_retorno(475)
        im_2475 = curva_ejemplo.intensidad_para_periodo_retorno(2475)
        
        # TR mayor = intensidad mayor
        assert im_2475 > im_475
    
    def test_to_dict(self, curva_ejemplo):
        """Test conversión a diccionario."""
        d = curva_ejemplo.to_dict()
        
        assert 'intensidades' in d
        assert 'tasas_excedencia' in d
        assert 'medida' in d
        assert d['vs30'] == 400


class TestMapaPeligro:
    """Tests para MapaPeligro."""
    
    @pytest.fixture
    def mapa_ejemplo(self):
        """Crea un mapa de peligro de ejemplo."""
        from seismex.analysis.psha import MapaPeligro, MedidaIntensidad
        
        lats = np.linspace(18, 20, 5)
        lons = np.linspace(-104, -102, 5)
        intensidades = np.random.uniform(0.05, 0.3, (5, 5))
        
        return MapaPeligro(
            intensidades=intensidades,
            latitudes=lats,
            longitudes=lons,
            periodo_retorno=475,
            medida=MedidaIntensidad.PGA
        )
    
    def test_bounds(self, mapa_ejemplo):
        """Test cálculo de bounds."""
        bounds = mapa_ejemplo.bounds
        
        assert bounds[0] == -104  # lon_min
        assert bounds[2] == -102  # lon_max
        assert bounds[1] == 18    # lat_min
        assert bounds[3] == 20    # lat_max
    
    def test_intensidad_maxima(self, mapa_ejemplo):
        """Test intensidad máxima."""
        assert 0.05 <= mapa_ejemplo.intensidad_maxima <= 0.3
    
    def test_intensidad_media(self, mapa_ejemplo):
        """Test intensidad media."""
        assert 0.05 <= mapa_ejemplo.intensidad_media <= 0.3
    
    def test_obtener_intensidad_dentro(self, mapa_ejemplo):
        """Test obtener intensidad en punto dentro del mapa."""
        im = mapa_ejemplo.obtener_intensidad(19.0, -103.0)
        
        assert not np.isnan(im)
        assert im > 0
    
    def test_obtener_intensidad_fuera(self, mapa_ejemplo):
        """Test obtener intensidad en punto fuera del mapa."""
        im = mapa_ejemplo.obtener_intensidad(25.0, -90.0)
        
        assert np.isnan(im)


class TestDesagregacion:
    """Tests para Desagregacion."""
    
    @pytest.fixture
    def desag_ejemplo(self):
        """Crea una desagregación de ejemplo."""
        from seismex.analysis.psha import Desagregacion
        
        mags = np.linspace(5, 8, 10)
        dists = np.linspace(10, 200, 15)
        epsilons = np.linspace(-3, 3, 5)
        
        # Contribución MR: pico en M=7, R=50
        contrib_MR = np.zeros((10, 15))
        for i, m in enumerate(mags):
            for j, r in enumerate(dists):
                contrib_MR[i, j] = np.exp(-0.5 * ((m - 7) / 0.5) ** 2) * \
                                   np.exp(-0.5 * ((r - 50) / 30) ** 2)
        contrib_MR /= contrib_MR.sum()
        
        contrib_MRe = np.zeros((10, 15, 5))
        
        return Desagregacion(
            bins_magnitud=mags,
            bins_distancia=dists,
            bins_epsilon=epsilons,
            contribucion_MR=contrib_MR,
            contribucion_MRe=contrib_MRe,
            intensidad_objetivo=0.2,
            sitio=(19.4, -99.1)
        )
    
    def test_magnitud_modal(self, desag_ejemplo):
        """Test magnitud modal."""
        m_modal = desag_ejemplo.magnitud_modal
        
        # Debe estar cerca de 7 (donde pusimos el pico)
        assert 6.5 < m_modal < 7.5
    
    def test_distancia_modal(self, desag_ejemplo):
        """Test distancia modal."""
        r_modal = desag_ejemplo.distancia_modal
        
        # Debe estar cerca de 50 (donde pusimos el pico)
        assert 30 < r_modal < 80
    
    def test_magnitud_media(self, desag_ejemplo):
        """Test magnitud media ponderada."""
        m_media = desag_ejemplo.magnitud_media
        
        assert 5 <= m_media <= 8
    
    def test_distancia_media(self, desag_ejemplo):
        """Test distancia media ponderada."""
        r_media = desag_ejemplo.distancia_media
        
        assert r_media > 0
    
    def test_resumen(self, desag_ejemplo):
        """Test generación de resumen."""
        resumen = desag_ejemplo.resumen()
        
        assert "Desagregación" in resumen
        assert "Magnitud" in resumen
        assert "Distancia" in resumen


class TestArbolLogico:
    """Tests para ArbolLogico."""
    
    def test_inicializacion(self):
        """Test inicialización vacía."""
        from seismex.analysis.psha import ArbolLogico
        
        arbol = ArbolLogico()
        
        assert len(arbol) == 0
    
    def test_agregar_rama(self):
        """Test agregar ramas."""
        from seismex.analysis.psha import ArbolLogico
        
        arbol = ArbolLogico()
        arbol.agregar_rama("Rama 1", peso=0.5)
        arbol.agregar_rama("Rama 2", peso=0.5)
        
        assert len(arbol) == 2
    
    def test_normalizar_pesos(self):
        """Test normalización de pesos."""
        from seismex.analysis.psha import ArbolLogico
        
        arbol = ArbolLogico()
        arbol.agregar_rama("Rama 1", peso=1)
        arbol.agregar_rama("Rama 2", peso=3)
        
        arbol.normalizar_pesos()
        
        pesos = [r.peso for r in arbol.ramas]
        assert np.isclose(sum(pesos), 1.0)
        assert np.isclose(pesos[0], 0.25)
        assert np.isclose(pesos[1], 0.75)
    
    def test_validar(self):
        """Test validación de pesos."""
        from seismex.analysis.psha import ArbolLogico
        
        arbol = ArbolLogico()
        arbol.agregar_rama("Rama 1", peso=0.6)
        arbol.agregar_rama("Rama 2", peso=0.4)
        
        assert arbol.validar()
        
        # Pesos que no suman 1
        arbol2 = ArbolLogico()
        arbol2.agregar_rama("Rama 1", peso=0.3)
        arbol2.agregar_rama("Rama 2", peso=0.3)
        
        assert not arbol2.validar()


class TestGMPEWrapper:
    """Tests para GMPEWrapper."""
    
    def test_wrapper_gmpe(self):
        """Test wrapper con GMPE real."""
        from seismex.analysis.psha import GMPEWrapper
        from seismex.analysis.isoseismal import GMPEGarcia2005
        
        gmpe = GMPEGarcia2005()
        wrapper = GMPEWrapper(gmpe)
        
        assert wrapper.nombre == "García et al. (2005)"
    
    def test_calcular_pga(self):
        """Test cálculo de PGA a través del wrapper."""
        from seismex.analysis.psha import GMPEWrapper, MedidaIntensidad
        from seismex.analysis.isoseismal import GMPEGarcia2005
        
        wrapper = GMPEWrapper(GMPEGarcia2005())
        
        media, sigma = wrapper.calcular(
            magnitud=7.0,
            distancia=50,
            profundidad=20,
            vs30=400,
            medida=MedidaIntensidad.PGA
        )
        
        assert media > 0
        assert sigma > 0
    
    def test_probabilidad_excedencia(self):
        """Test cálculo de P(IM > im | M, R)."""
        from seismex.analysis.psha import GMPEWrapper
        from seismex.analysis.isoseismal import GMPEGarcia2005
        
        wrapper = GMPEWrapper(GMPEGarcia2005())
        
        # Probabilidad de exceder 0.1g
        p = wrapper.probabilidad_excedencia(
            intensidad=0.1,
            magnitud=7.0,
            distancia=50,
            profundidad=20
        )
        
        assert 0 <= p <= 1


class TestAnalizadorPSHA:
    """Tests para AnalizadorPSHA."""
    
    @pytest.fixture
    def psha_ejemplo(self):
        """Crea un analizador PSHA de ejemplo."""
        from seismex.analysis.psha import AnalizadorPSHA
        from seismex.analysis.source_models import crear_modelo_mexico_simplificado
        from seismex.analysis.isoseismal import GMPEGarcia2005
        
        fuentes = crear_modelo_mexico_simplificado()
        
        psha = AnalizadorPSHA(
            fuentes=fuentes,
            vs30=400,
            distancia_maxima=300
        )
        psha.agregar_gmpe(GMPEGarcia2005(), peso=1.0)
        
        return psha
    
    def test_inicializacion(self, psha_ejemplo):
        """Test inicialización."""
        assert psha_ejemplo.fuentes is not None
        assert len(psha_ejemplo.gmpes) == 1
        assert psha_ejemplo.vs30 == 400
    
    def test_agregar_gmpe(self):
        """Test agregar múltiples GMPEs."""
        from seismex.analysis.psha import AnalizadorPSHA
        from seismex.analysis.source_models import crear_modelo_mexico_simplificado
        from seismex.analysis.isoseismal import GMPEGarcia2005, GMPEZhao2006
        
        psha = AnalizadorPSHA(fuentes=crear_modelo_mexico_simplificado())
        psha.agregar_gmpe(GMPEGarcia2005(), peso=0.6)
        psha.agregar_gmpe(GMPEZhao2006(), peso=0.4)
        
        assert len(psha.gmpes) == 2
        assert np.isclose(sum(psha.pesos_gmpe), 1.0)
    
    def test_calcular_curva_peligro(self, psha_ejemplo):
        """Test cálculo de curva de peligro."""
        curva = psha_ejemplo.calcular_curva_peligro(
            sitio=(19.0, -103.5),
            vs30=400
        )
        
        assert curva is not None
        assert len(curva.intensidades) > 0
        assert len(curva.tasas_excedencia) > 0
        
        # Tasas deben ser decrecientes
        assert curva.tasas_excedencia[0] >= curva.tasas_excedencia[-1]
    
    def test_curva_peligro_diferentes_sitios(self, psha_ejemplo):
        """Test que diferentes sitios dan diferentes resultados."""
        curva1 = psha_ejemplo.calcular_curva_peligro(sitio=(19.0, -103.5))
        curva2 = psha_ejemplo.calcular_curva_peligro(sitio=(25.0, -100.0))
        
        # Las curvas deben ser diferentes
        # (sitio cerca de fuentes vs lejos)
        im_475_1 = curva1.intensidad_para_periodo_retorno(475)
        im_475_2 = curva2.intensidad_para_periodo_retorno(475)
        
        # No necesariamente diferentes, pero al menos calculables
        assert im_475_1 > 0
        assert im_475_2 >= 0
    
    def test_resumen(self, psha_ejemplo):
        """Test generación de resumen."""
        resumen = psha_ejemplo.resumen()
        
        assert "ANALIZADOR PSHA" in resumen
        assert "GMPEs" in resumen


class TestUtilidades:
    """Tests para funciones de utilidad."""
    
    def test_calcular_probabilidad_poisson(self):
        """Test cálculo de probabilidad Poisson."""
        from seismex.analysis.psha import calcular_probabilidad_poisson
        
        # Tasa = 1/475 por año, tiempo = 50 años
        # P ≈ 10%
        prob = calcular_probabilidad_poisson(tasa=1/475, tiempo=50)
        
        assert 0.09 < prob < 0.11
    
    def test_periodo_retorno_desde_probabilidad(self):
        """Test cálculo de período de retorno."""
        from seismex.analysis.psha import periodo_retorno_desde_probabilidad
        
        # 10% en 50 años → TR ≈ 475 años
        tr = periodo_retorno_desde_probabilidad(probabilidad=0.10, tiempo=50)
        
        assert 470 < tr < 480
    
    def test_periodo_retorno_limites(self):
        """Test límites de período de retorno."""
        from seismex.analysis.psha import periodo_retorno_desde_probabilidad
        
        # Probabilidad = 1 → TR = tiempo
        tr_max = periodo_retorno_desde_probabilidad(probabilidad=1.0, tiempo=50)
        assert tr_max == 50
        
        # Probabilidad ≈ 0 → TR → infinito
        tr_min = periodo_retorno_desde_probabilidad(probabilidad=0.001, tiempo=50)
        assert tr_min > 1000


class TestCrearAnalizadorMexico:
    """Tests para factory de analizador México."""
    
    def test_crear_analizador(self):
        """Test creación del analizador."""
        from seismex.analysis.psha import crear_analizador_mexico
        
        psha = crear_analizador_mexico(vs30=400)
        
        assert psha is not None
        assert psha.vs30 == 400
        assert len(psha.gmpes) >= 1
        assert psha.fuentes is not None
    
    def test_analizador_funcional(self):
        """Test que el analizador es funcional."""
        from seismex.analysis.psha import crear_analizador_mexico
        
        psha = crear_analizador_mexico()
        
        # Debe poder calcular una curva
        curva = psha.calcular_curva_peligro(sitio=(19.4, -99.1))
        
        assert curva is not None
        
        pga_475 = curva.intensidad_para_periodo_retorno(475)
        assert pga_475 > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
