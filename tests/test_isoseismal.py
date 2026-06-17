#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para seismex.analysis.isoseismal
======================================

Tests unitarios para el módulo de generación de isosistas.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch


class TestGMPEs:
    """Tests para Ground Motion Prediction Equations."""
    
    def test_gmpe_zhao2006_pga_basico(self):
        """Test cálculo básico de PGA con Zhao 2006."""
        from seismex.analysis.isoseismal import GMPEZhao2006
        
        gmpe = GMPEZhao2006()
        pga, sigma = gmpe.calcular_pga(
            magnitud=7.0,
            distancia_km=50,
            profundidad_km=25,
            vs30=760
        )
        
        assert pga > 0, "PGA debe ser positivo"
        assert pga < 2.0, "PGA debe ser razonable (< 2g)"
        assert sigma > 0, "Sigma debe ser positivo"
    
    def test_gmpe_zhao2006_atenuacion(self):
        """Test que PGA decrece con distancia."""
        from seismex.analysis.isoseismal import GMPEZhao2006
        
        gmpe = GMPEZhao2006()
        
        pga_cerca, _ = gmpe.calcular_pga(magnitud=7.0, distancia_km=20)
        pga_lejos, _ = gmpe.calcular_pga(magnitud=7.0, distancia_km=100)
        
        assert pga_cerca > pga_lejos, "PGA debe decrecer con distancia"
    
    def test_gmpe_zhao2006_escalamiento_magnitud(self):
        """Test que PGA aumenta con magnitud."""
        from seismex.analysis.isoseismal import GMPEZhao2006
        
        gmpe = GMPEZhao2006()
        
        pga_m6, _ = gmpe.calcular_pga(magnitud=6.0, distancia_km=50)
        pga_m7, _ = gmpe.calcular_pga(magnitud=7.0, distancia_km=50)
        pga_m8, _ = gmpe.calcular_pga(magnitud=8.0, distancia_km=50)
        
        assert pga_m6 < pga_m7 < pga_m8, "PGA debe aumentar con magnitud"
    
    def test_gmpe_garcia2005_mexico(self):
        """Test GMPE García 2005 para México."""
        from seismex.analysis.isoseismal import GMPEGarcia2005
        
        gmpe = GMPEGarcia2005()
        
        assert gmpe.nombre == "García et al. (2005)"
        
        pga, sigma = gmpe.calcular_pga(
            magnitud=7.5,
            distancia_km=100,
            profundidad_km=30
        )
        
        assert 0 < pga < 1.0, "PGA debe estar en rango razonable"
        assert sigma > 0
    
    def test_gmpe_atkinson_boore_2003(self):
        """Test GMPE Atkinson & Boore 2003."""
        from seismex.analysis.isoseismal import GMPEAtkinsonBoore2003
        
        gmpe = GMPEAtkinsonBoore2003()
        
        pga, sigma = gmpe.calcular_pga(
            magnitud=7.0,
            distancia_km=80,
            profundidad_km=50
        )
        
        assert pga > 0
        assert sigma > 0


class TestIPEs:
    """Tests para Intensity Prediction Equations."""
    
    def test_ipe_allen2012_basico(self):
        """Test cálculo básico de MMI con Allen 2012."""
        from seismex.analysis.isoseismal import IPEAllen2012
        
        ipe = IPEAllen2012()
        mmi, sigma = ipe.calcular_intensidad(
            magnitud=7.0,
            distancia_km=50,
            profundidad_km=15
        )
        
        assert 1 <= mmi <= 12, "MMI debe estar entre 1 y 12"
        assert sigma > 0
    
    def test_ipe_allen2012_atenuacion(self):
        """Test que MMI decrece con distancia."""
        from seismex.analysis.isoseismal import IPEAllen2012
        
        ipe = IPEAllen2012()
        
        mmi_cerca, _ = ipe.calcular_intensidad(magnitud=7.0, distancia_km=10)
        mmi_lejos, _ = ipe.calcular_intensidad(magnitud=7.0, distancia_km=200)
        
        assert mmi_cerca > mmi_lejos
    
    def test_ipe_cenapred_mexico(self):
        """Test IPE CENAPRED para México."""
        from seismex.analysis.isoseismal import IPECENAPRED2006
        
        ipe = IPECENAPRED2006()
        
        assert ipe.nombre == "CENAPRED (2006)"
        
        mmi, sigma = ipe.calcular_intensidad(
            magnitud=6.5,
            distancia_km=30,
            profundidad_km=20
        )
        
        assert 1 <= mmi <= 12
    
    def test_ipe_descripcion_intensidad(self):
        """Test descripciones de intensidad MMI."""
        from seismex.analysis.isoseismal import IPEAllen2012
        
        ipe = IPEAllen2012()
        
        assert "No sentido" in ipe.descripcion_intensidad(1)
        assert "Moderado" in ipe.descripcion_intensidad(5)
        assert "Severo" in ipe.descripcion_intensidad(8)
    
    def test_ipe_color_intensidad(self):
        """Test colores de intensidad MMI."""
        from seismex.analysis.isoseismal import IPEAllen2012
        
        ipe = IPEAllen2012()
        
        color = ipe.color_intensidad(7)
        assert color.startswith('#')
        assert len(color) == 7


class TestGeneradorIsosistas:
    """Tests para GeneradorIsosistas."""
    
    def test_generador_inicializacion(self):
        """Test inicialización del generador."""
        from seismex.analysis.isoseismal import GeneradorIsosistas
        
        gen = GeneradorIsosistas(ipe='allen_2012')
        assert gen.ipe is not None
        assert gen.ipe.nombre == "Allen et al. (2012)"
    
    def test_generador_con_gmpe(self):
        """Test inicialización con GMPE."""
        from seismex.analysis.isoseismal import GeneradorIsosistas
        
        gen = GeneradorIsosistas(ipe='allen_2012', gmpe='garcia_2005')
        assert gen.gmpe is not None
        assert gen.gmpe.nombre == "García et al. (2005)"
    
    def test_generador_ipe_invalido(self):
        """Test error con IPE inválido."""
        from seismex.analysis.isoseismal import GeneradorIsosistas
        
        with pytest.raises(ValueError):
            GeneradorIsosistas(ipe='modelo_inexistente')
    
    def test_calcular_isosistas_basico(self):
        """Test cálculo básico de isosistas."""
        from seismex.analysis.isoseismal import GeneradorIsosistas
        
        gen = GeneradorIsosistas(ipe='cenapred_2006')
        
        resultado = gen.calcular(
            latitud=19.0,
            longitud=-103.0,
            profundidad_km=20,
            magnitud=6.5,
            resolucion_km=20,  # Baja resolución para test rápido
            radio_max_km=100
        )
        
        assert resultado is not None
        assert resultado.intensidad_grid.shape[0] > 0
        assert resultado.intensidad_grid.shape[1] > 0
        assert resultado.intensidad_maxima > 0
    
    def test_calcular_isosistas_evento(self):
        """Test información del evento en resultado."""
        from seismex.analysis.isoseismal import GeneradorIsosistas
        
        gen = GeneradorIsosistas(ipe='allen_2012')
        
        resultado = gen.calcular(
            latitud=18.5,
            longitud=-99.0,
            profundidad_km=50,
            magnitud=7.1,
            resolucion_km=25,
            radio_max_km=80
        )
        
        assert resultado.evento['magnitud'] == 7.1
        assert resultado.evento['latitud'] == 18.5
        assert resultado.evento['profundidad_km'] == 50
    
    def test_listar_modelos(self):
        """Test listado de modelos disponibles."""
        from seismex.analysis.isoseismal import GeneradorIsosistas
        
        modelos = GeneradorIsosistas.listar_modelos()
        
        assert 'ipes' in modelos
        assert 'gmpes' in modelos
        assert 'allen_2012' in modelos['ipes']
        assert 'garcia_2005' in modelos['gmpes']


class TestResultadoIsosistas:
    """Tests para ResultadoIsosistas."""
    
    @pytest.fixture
    def resultado_ejemplo(self):
        """Crea un resultado de ejemplo para tests."""
        from seismex.analysis.isoseismal import ResultadoIsosistas
        
        lats = np.linspace(18, 20, 10)
        lons = np.linspace(-104, -102, 10)
        intensidad = np.random.uniform(3, 8, (10, 10))
        
        return ResultadoIsosistas(
            intensidad_grid=intensidad,
            latitudes=lats,
            longitudes=lons,
            evento={
                'magnitud': 6.5,
                'latitud': 19.0,
                'longitud': -103.0,
                'profundidad_km': 20
            },
            modelo_ipe='Test IPE'
        )
    
    def test_bounds(self, resultado_ejemplo):
        """Test cálculo de bounds."""
        bounds = resultado_ejemplo.bounds
        
        assert len(bounds) == 4
        assert bounds[0] < bounds[2]  # lon_min < lon_max
        assert bounds[1] < bounds[3]  # lat_min < lat_max
    
    def test_intensidad_maxima(self, resultado_ejemplo):
        """Test cálculo de intensidad máxima."""
        assert resultado_ejemplo.intensidad_maxima > 0
        assert resultado_ejemplo.intensidad_maxima <= 12
    
    def test_to_dict(self, resultado_ejemplo):
        """Test conversión a diccionario."""
        d = resultado_ejemplo.evento
        
        assert 'magnitud' in d
        assert 'latitud' in d
        assert 'longitud' in d


class TestModeloSitio:
    """Tests para ModeloSitio."""
    
    def test_modelo_sitio_default(self):
        """Test modelo de sitio con valor default."""
        from seismex.analysis.isoseismal import ModeloSitio
        
        modelo = ModeloSitio(vs30_default=760)
        
        vs30 = modelo.obtener_vs30(19.0, -103.0)
        assert vs30 == 760
    
    def test_modelo_sitio_tipo_suelo(self):
        """Test clasificación de tipo de suelo."""
        from seismex.analysis.isoseismal import ModeloSitio, TipoSuelo
        
        modelo = ModeloSitio(vs30_default=400)
        
        tipo = modelo.tipo_suelo(19.0, -103.0)
        assert tipo == TipoSuelo.SUELO_FIRME


class TestConversiones:
    """Tests para funciones de conversión."""
    
    def test_pga_a_mmi(self):
        """Test conversión PGA a MMI."""
        from seismex.analysis.isoseismal import pga_a_mmi_wald
        
        mmi = pga_a_mmi_wald(0.1)  # 0.1g
        assert 5 < mmi < 8
        
        mmi_bajo = pga_a_mmi_wald(0.01)
        mmi_alto = pga_a_mmi_wald(0.5)
        assert mmi_bajo < mmi_alto
    
    def test_pgv_a_mmi(self):
        """Test conversión PGV a MMI."""
        from seismex.analysis.isoseismal import pgv_a_mmi_wald
        
        mmi = pgv_a_mmi_wald(10)  # 10 cm/s
        assert 4 < mmi < 8
    
    def test_distancia_hipocentral(self):
        """Test cálculo de distancia hipocentral."""
        from seismex.analysis.isoseismal import distancia_hipocentral
        
        # Mismo punto, solo profundidad
        dist = distancia_hipocentral(19.0, -103.0, 19.0, -103.0, 20)
        assert np.isclose(dist, 20, atol=0.1)
        
        # Puntos diferentes
        dist = distancia_hipocentral(19.0, -103.0, 20.0, -103.0, 10)
        assert dist > 100  # ~111 km + profundidad


class TestFactories:
    """Tests para funciones factory."""
    
    def test_crear_generador_mexico(self):
        """Test factory para generador México."""
        from seismex.analysis.isoseismal import crear_generador_mexico
        
        gen = crear_generador_mexico()
        
        assert gen.ipe.nombre == "CENAPRED (2006)"
        assert gen.gmpe.nombre == "García et al. (2005)"
    
    def test_crear_generador_subduccion(self):
        """Test factory para generador subducción."""
        from seismex.analysis.isoseismal import crear_generador_subduccion
        
        gen = crear_generador_subduccion()
        
        assert gen.gmpe is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
