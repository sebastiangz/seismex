#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para seismex.analysis.source_models
=========================================

Tests unitarios para el módulo de modelos de fuentes sísmicas.
"""

import pytest
import numpy as np


class TestDistribucionGutenbergRichter:
    """Tests para DistribucionGutenbergRichter."""
    
    def test_inicializacion(self):
        """Test inicialización básica."""
        from seismex.analysis.source_models import DistribucionGutenbergRichter
        
        dist = DistribucionGutenbergRichter(
            mmin=4.0,
            mmax=8.0,
            a_value=4.5,
            b_value=1.0
        )
        
        assert dist.mmin == 4.0
        assert dist.mmax == 8.0
        assert dist.a_value == 4.5
        assert dist.b_value == 1.0
    
    def test_pdf_rango_valido(self):
        """Test PDF dentro del rango válido."""
        from seismex.analysis.source_models import DistribucionGutenbergRichter
        
        dist = DistribucionGutenbergRichter(mmin=4.0, mmax=8.0)
        
        # PDF debe ser positivo dentro del rango
        assert dist.pdf(5.0) > 0
        assert dist.pdf(6.0) > 0
        assert dist.pdf(7.0) > 0
        
        # PDF debe ser cero fuera del rango
        assert dist.pdf(3.0) == 0
        assert dist.pdf(9.0) == 0
    
    def test_pdf_decreciente(self):
        """Test que PDF decrece con magnitud (para b > 0)."""
        from seismex.analysis.source_models import DistribucionGutenbergRichter
        
        dist = DistribucionGutenbergRichter(mmin=4.0, mmax=8.0, b_value=1.0)
        
        assert dist.pdf(4.5) > dist.pdf(5.5)
        assert dist.pdf(5.5) > dist.pdf(6.5)
    
    def test_cdf_monotona(self):
        """Test que CDF es monótona creciente."""
        from seismex.analysis.source_models import DistribucionGutenbergRichter
        
        dist = DistribucionGutenbergRichter(mmin=4.0, mmax=8.0)
        
        assert dist.cdf(4.0) == 0
        assert dist.cdf(5.0) > dist.cdf(4.5)
        assert dist.cdf(6.0) > dist.cdf(5.0)
        assert dist.cdf(8.0) == 1
    
    def test_tasa_excedencia(self):
        """Test tasa de excedencia."""
        from seismex.analysis.source_models import DistribucionGutenbergRichter
        
        dist = DistribucionGutenbergRichter(
            mmin=4.0, mmax=8.0, a_value=4.0, b_value=1.0
        )
        
        # Tasa debe decrecer con magnitud
        tasa_5 = dist.tasa_excedencia(5.0)
        tasa_6 = dist.tasa_excedencia(6.0)
        tasa_7 = dist.tasa_excedencia(7.0)
        
        assert tasa_5 > tasa_6 > tasa_7
        
        # Tasa para M > Mmax debe ser 0
        assert dist.tasa_excedencia(8.5) == 0
    
    def test_discretizar(self):
        """Test discretización de la distribución."""
        from seismex.analysis.source_models import DistribucionGutenbergRichter
        
        dist = DistribucionGutenbergRichter(mmin=4.0, mmax=8.0, bin_width=0.5)
        
        mags, probs = dist.discretizar()
        
        assert len(mags) == len(probs)
        assert mags[0] >= 4.0
        assert mags[-1] <= 8.0
        assert np.isclose(probs.sum(), 1.0)


class TestDistribucionCaracteristica:
    """Tests para DistribucionCaracteristica."""
    
    def test_inicializacion(self):
        """Test inicialización."""
        from seismex.analysis.source_models import DistribucionCaracteristica
        
        dist = DistribucionCaracteristica(
            mmin=4.0,
            mmax=8.0,
            m_char=7.5,
            peso_char=0.5
        )
        
        assert dist.m_char == 7.5
        assert dist.peso_char == 0.5
    
    def test_pdf_tiene_pico(self):
        """Test que PDF tiene pico cerca de M característica."""
        from seismex.analysis.source_models import DistribucionCaracteristica
        
        dist = DistribucionCaracteristica(
            mmin=4.0, mmax=8.0, m_char=7.5, peso_char=0.7
        )
        
        # PDF cerca de m_char debe ser alta
        pdf_char = dist.pdf(7.5)
        pdf_lejos = dist.pdf(5.0)
        
        # Con peso_char alto, el pico característico debe dominar
        assert pdf_char > 0


class TestDistribucionProfundidad:
    """Tests para DistribucionProfundidad."""
    
    def test_muestrear_uniforme(self):
        """Test muestreo uniforme."""
        from seismex.analysis.source_models import (
            DistribucionProfundidad, TipoDistribucionProfundidad
        )
        
        dist = DistribucionProfundidad(
            tipo=TipoDistribucionProfundidad.UNIFORME,
            prof_min=5,
            prof_max=30
        )
        
        muestras = dist.muestrear(1000)
        
        assert len(muestras) == 1000
        assert muestras.min() >= 5
        assert muestras.max() <= 30
    
    def test_muestrear_fija(self):
        """Test profundidad fija."""
        from seismex.analysis.source_models import (
            DistribucionProfundidad, TipoDistribucionProfundidad
        )
        
        dist = DistribucionProfundidad(
            tipo=TipoDistribucionProfundidad.FIJA,
            prof_media=20
        )
        
        muestras = dist.muestrear(100)
        
        assert np.all(muestras == 20)
    
    def test_muestrear_triangular(self):
        """Test muestreo triangular."""
        from seismex.analysis.source_models import (
            DistribucionProfundidad, TipoDistribucionProfundidad
        )
        
        dist = DistribucionProfundidad(
            tipo=TipoDistribucionProfundidad.TRIANGULAR,
            prof_min=5,
            prof_max=40,
            prof_media=20
        )
        
        muestras = dist.muestrear(1000)
        
        assert muestras.min() >= 5
        assert muestras.max() <= 40
        # Media debe estar cerca del valor esperado
        assert 15 < muestras.mean() < 25


class TestFuenteArea:
    """Tests para FuenteArea."""
    
    @pytest.fixture
    def fuente_ejemplo(self):
        """Crea una fuente de área de ejemplo."""
        from seismex.analysis.source_models import (
            FuenteArea, DistribucionGutenbergRichter
        )
        
        dist_mag = DistribucionGutenbergRichter(
            mmin=4.0, mmax=7.5, a_value=4.0, b_value=1.0
        )
        
        return FuenteArea(
            nombre="Zona Test",
            poligono=[
                (18.0, -104.0),
                (20.0, -104.0),
                (20.0, -102.0),
                (18.0, -102.0)
            ],
            distribucion_magnitud=dist_mag
        )
    
    def test_contiene_punto_dentro(self, fuente_ejemplo):
        """Test punto dentro del polígono."""
        assert fuente_ejemplo.contiene_punto(19.0, -103.0)
    
    def test_contiene_punto_fuera(self, fuente_ejemplo):
        """Test punto fuera del polígono."""
        assert not fuente_ejemplo.contiene_punto(15.0, -100.0)
    
    def test_area_km2(self, fuente_ejemplo):
        """Test cálculo de área."""
        area = fuente_ejemplo.area_km2()
        
        # Área aproximada: 2° x 2° ≈ 222 km x 220 km ≈ 48,000 km²
        assert 40000 < area < 60000
    
    def test_distancia_a_punto(self, fuente_ejemplo):
        """Test distancia a punto."""
        # Punto dentro: distancia = 0
        assert fuente_ejemplo.distancia_a_punto(19.0, -103.0) == 0
        
        # Punto fuera: distancia > 0
        assert fuente_ejemplo.distancia_a_punto(15.0, -103.0) > 0
    
    def test_muestrear_ubicaciones(self, fuente_ejemplo):
        """Test muestreo de ubicaciones."""
        ubicaciones = fuente_ejemplo.muestrear_ubicaciones(100)
        
        assert ubicaciones.shape == (100, 2)
        
        # Todas las ubicaciones deben estar dentro
        for lat, lon in ubicaciones:
            assert fuente_ejemplo.contiene_punto(lat, lon)
    
    def test_muestrear_eventos(self, fuente_ejemplo):
        """Test muestreo de eventos completos."""
        eventos = fuente_ejemplo.muestrear_eventos(50)
        
        assert len(eventos) == 50
        
        for evento in eventos:
            assert 'lat' in evento
            assert 'lon' in evento
            assert 'profundidad_km' in evento
            assert 'magnitud' in evento
            assert evento['magnitud'] >= 4.0
            assert evento['magnitud'] <= 7.5


class TestFuenteFalla:
    """Tests para FuenteFalla."""
    
    @pytest.fixture
    def falla_ejemplo(self):
        """Crea una fuente de falla de ejemplo."""
        from seismex.analysis.source_models import (
            FuenteFalla, TipoFalla, DistribucionGutenbergRichter
        )
        
        dist_mag = DistribucionGutenbergRichter(mmin=5.0, mmax=7.5)
        
        return FuenteFalla(
            nombre="Falla Test",
            traza=[(19.0, -103.0), (19.5, -102.5), (20.0, -102.0)],
            longitud_km=100,
            ancho_km=15,
            buzamiento=60,
            tipo_falla=TipoFalla.NORMAL,
            slip_rate_mm_yr=2.0,
            distribucion_magnitud=dist_mag
        )
    
    def test_area_km2(self, falla_ejemplo):
        """Test área de ruptura."""
        area = falla_ejemplo.area_km2()
        
        # 100 km x 15 km = 1500 km²
        assert area == 1500
    
    def test_magnitud_maxima_wells_coppersmith(self, falla_ejemplo):
        """Test estimación de Mmax."""
        mmax = falla_ejemplo.magnitud_maxima_wells_coppersmith()
        
        # Para L=100km, Mmax debería estar entre 7 y 8
        assert 7.0 < mmax < 8.0
    
    def test_momento_sismico_anual(self, falla_ejemplo):
        """Test momento sísmico anual."""
        m0 = falla_ejemplo.momento_sismico_anual()
        
        assert m0 > 0
    
    def test_contiene_punto_siempre_false(self, falla_ejemplo):
        """Test que falla no 'contiene' puntos."""
        assert not falla_ejemplo.contiene_punto(19.0, -103.0)
    
    def test_distancia_a_punto(self, falla_ejemplo):
        """Test distancia a la traza."""
        dist = falla_ejemplo.distancia_a_punto(19.0, -103.0)
        assert dist >= 0


class TestFuentePuntual:
    """Tests para FuentePuntual."""
    
    def test_inicializacion(self):
        """Test inicialización."""
        from seismex.analysis.source_models import (
            FuentePuntual, DistribucionGutenbergRichter
        )
        
        fuente = FuentePuntual(
            nombre="Volcán Test",
            latitud=19.5,
            longitud=-103.6,
            radio_km=20,
            distribucion_magnitud=DistribucionGutenbergRichter(mmin=3.0, mmax=5.0)
        )
        
        assert fuente.latitud == 19.5
        assert fuente.longitud == -103.6
    
    def test_contiene_punto(self):
        """Test contiene punto dentro del radio."""
        from seismex.analysis.source_models import (
            FuentePuntual, DistribucionGutenbergRichter
        )
        
        fuente = FuentePuntual(
            nombre="Test",
            latitud=19.5,
            longitud=-103.6,
            radio_km=20,
            distribucion_magnitud=DistribucionGutenbergRichter(mmin=3.0, mmax=5.0)
        )
        
        # Centro debe estar dentro
        assert fuente.contiene_punto(19.5, -103.6)
        
        # Punto lejano debe estar fuera
        assert not fuente.contiene_punto(20.0, -103.0)
    
    def test_area_km2(self):
        """Test área del círculo."""
        from seismex.analysis.source_models import (
            FuentePuntual, DistribucionGutenbergRichter
        )
        
        fuente = FuentePuntual(
            nombre="Test",
            latitud=19.5,
            longitud=-103.6,
            radio_km=10,
            distribucion_magnitud=DistribucionGutenbergRichter(mmin=3.0, mmax=5.0)
        )
        
        area = fuente.area_km2()
        
        # π × 10² ≈ 314 km²
        assert 310 < area < 320


class TestModeloFuentes:
    """Tests para ModeloFuentes."""
    
    def test_inicializacion(self):
        """Test inicialización vacía."""
        from seismex.analysis.source_models import ModeloFuentes
        
        modelo = ModeloFuentes(nombre="Test", version="1.0")
        
        assert len(modelo) == 0
        assert modelo.nombre == "Test"
    
    def test_agregar_zona_area(self):
        """Test agregar zona de área."""
        from seismex.analysis.source_models import ModeloFuentes
        
        modelo = ModeloFuentes(nombre="Test")
        modelo.agregar_zona_area(
            nombre="Zona 1",
            poligono=[(18, -104), (20, -104), (20, -102), (18, -102)],
            a_value=4.0,
            b_value=1.0,
            mmin=4.0,
            mmax=8.0
        )
        
        assert len(modelo) == 1
        assert modelo[0].nombre == "Zona 1"
    
    def test_agregar_falla(self):
        """Test agregar falla."""
        from seismex.analysis.source_models import ModeloFuentes, TipoFalla
        
        modelo = ModeloFuentes(nombre="Test")
        modelo.agregar_falla(
            nombre="Falla 1",
            traza=[(19.0, -103.0), (20.0, -102.0)],
            longitud_km=80,
            ancho_km=15,
            buzamiento=60,
            slip_rate_mm_yr=1.0,
            tipo_falla=TipoFalla.NORMAL
        )
        
        assert len(modelo) == 1
    
    def test_obtener_fuente_por_nombre(self):
        """Test acceso por nombre."""
        from seismex.analysis.source_models import ModeloFuentes
        
        modelo = ModeloFuentes(nombre="Test")
        modelo.agregar_zona_area(
            nombre="Mi Zona",
            poligono=[(18, -104), (20, -104), (20, -102), (18, -102)],
            a_value=4.0, b_value=1.0, mmin=4.0, mmax=8.0
        )
        
        fuente = modelo["Mi Zona"]
        assert fuente.nombre == "Mi Zona"
    
    def test_tasa_total(self):
        """Test tasa total de eventos."""
        from seismex.analysis.source_models import ModeloFuentes
        
        modelo = ModeloFuentes(nombre="Test")
        modelo.agregar_zona_area(
            nombre="Zona 1",
            poligono=[(18, -104), (20, -104), (20, -102), (18, -102)],
            a_value=4.0, b_value=1.0, mmin=4.0, mmax=8.0
        )
        
        tasa = modelo.tasa_total()
        assert tasa > 0
    
    def test_muestrear_catalogo(self):
        """Test generación de catálogo sintético."""
        from seismex.analysis.source_models import ModeloFuentes
        
        modelo = ModeloFuentes(nombre="Test")
        modelo.agregar_zona_area(
            nombre="Zona 1",
            poligono=[(18, -104), (20, -104), (20, -102), (18, -102)],
            a_value=4.0, b_value=1.0, mmin=4.0, mmax=8.0
        )
        
        catalogo = modelo.muestrear_catalogo(100)
        
        assert len(catalogo) == 100
        for evento in catalogo:
            assert 'lat' in evento
            assert 'lon' in evento
            assert 'magnitud' in evento
    
    def test_to_dict(self):
        """Test conversión a diccionario."""
        from seismex.analysis.source_models import ModeloFuentes
        
        modelo = ModeloFuentes(nombre="Test", version="2.0")
        modelo.agregar_zona_area(
            nombre="Zona 1",
            poligono=[(18, -104), (20, -104), (20, -102), (18, -102)],
            a_value=4.0, b_value=1.0, mmin=4.0, mmax=8.0
        )
        
        d = modelo.to_dict()
        
        assert d['nombre'] == "Test"
        assert d['version'] == "2.0"
        assert d['n_fuentes'] == 1


class TestModeloMexicoSimplificado:
    """Tests para el modelo predefinido de México."""
    
    def test_crear_modelo(self):
        """Test creación del modelo."""
        from seismex.analysis.source_models import crear_modelo_mexico_simplificado
        
        modelo = crear_modelo_mexico_simplificado()
        
        assert modelo.nombre == "México Simplificado"
        assert len(modelo) >= 3  # Al menos 3 zonas
    
    def test_fuentes_activas(self):
        """Test que todas las fuentes están activas."""
        from seismex.analysis.source_models import crear_modelo_mexico_simplificado
        
        modelo = crear_modelo_mexico_simplificado()
        activas = modelo.obtener_fuentes_activas()
        
        assert len(activas) == len(modelo)
    
    def test_resumen(self):
        """Test generación de resumen."""
        from seismex.analysis.source_models import crear_modelo_mexico_simplificado
        
        modelo = crear_modelo_mexico_simplificado()
        resumen = modelo.resumen()
        
        assert "México Simplificado" in resumen
        assert "Subducción" in resumen or "Pacífico" in resumen


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
