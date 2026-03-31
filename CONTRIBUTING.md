# 🤝 Contribuir a SEISMEX

¡Gracias por tu interés en contribuir a SEISMEX! Este documento proporciona guías y mejores prácticas para contribuir al proyecto.

## Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Contribuir](#cómo-contribuir)
- [Configuración del Entorno de Desarrollo](#configuración-del-entorno-de-desarrollo)
- [Estilo de Código](#estilo-de-código)
- [Testing](#testing)
- [Documentación](#documentación)
- [Pull Requests](#pull-requests)
- [Reportar Bugs](#reportar-bugs)
- [Solicitar Funcionalidades](#solicitar-funcionalidades)

---

## Código de Conducta

Este proyecto sigue un código de conducta inclusivo y respetuoso. Se espera que todos los contribuidores:

- Sean respetuosos y considerados con otros contribuidores
- Acepten críticas constructivas de manera profesional
- Se enfoquen en lo mejor para la comunidad y el proyecto
- Muestren empatía hacia otros miembros de la comunidad

---

## Cómo Contribuir

### Tipos de Contribuciones

1. **🐛 Corrección de bugs**: Identificar y corregir errores
2. **✨ Nuevas funcionalidades**: Implementar características nuevas
3. **📚 Documentación**: Mejorar o agregar documentación
4. **🧪 Tests**: Agregar o mejorar cobertura de pruebas
5. **🎨 Mejoras de código**: Refactoring, optimización, limpieza

### Flujo de Trabajo

1. **Fork** el repositorio
2. **Crea una rama** desde `main` para tu contribución
3. **Desarrolla** tus cambios siguiendo las guías de estilo
4. **Escribe tests** para tu código
5. **Documenta** tus cambios
6. **Abre un Pull Request**

---

## Configuración del Entorno de Desarrollo

### Prerrequisitos

- Python 3.9+
- Git
- Conda (recomendado) o pip

### Instalación para Desarrollo

```bash
# Clonar tu fork
git clone https://github.com/sebastiangz/seismex.git
cd seismex

# Crear ambiente con conda
conda env create -f environment.yml
conda activate seismex

# O con pip
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Instalar en modo desarrollo
pip install -e ".[dev]"

# Instalar pre-commit hooks
pre-commit install
```

### Verificar Instalación

```bash
# Ejecutar tests
pytest

# Verificar estilo de código
black --check seismex/
isort --check-only seismex/
flake8 seismex/
```

---

## Estilo de Código

### Python

Seguimos [PEP 8](https://pep8.org/) con las siguientes herramientas:

- **Black**: Formateo automático (línea máxima: 88 caracteres)
- **isort**: Ordenamiento de imports
- **flake8**: Linting

```bash
# Formatear código
black seismex/
isort seismex/

# Verificar sin modificar
black --check seismex/
isort --check-only seismex/
flake8 seismex/
```

### Convenciones de Nombres

| Tipo | Convención | Ejemplo |
|------|------------|---------|
| Módulos | snake_case | `esd_calculator.py` |
| Clases | PascalCase | `CalculadoraESD` |
| Funciones | snake_case | `calcular_energia()` |
| Constantes | UPPER_CASE | `COEF_ENERGIA_A` |
| Variables | snake_case | `magnitud_momento` |

### Docstrings

Usar formato NumPy:

```python
def calcular_energia(magnitud: float) -> float:
    """
    Calcula la energía sísmica a partir de la magnitud.
    
    Usa la relación de Kanamori (1977):
    log₁₀(E) = 1.5 * Mw + 11.8
    
    Parameters
    ----------
    magnitud : float
        Magnitud momento (Mw) del evento sísmico.
        
    Returns
    -------
    float
        Energía en ergios.
        
    Raises
    ------
    ValueError
        Si la magnitud es negativa o mayor a 10.
        
    Examples
    --------
    >>> calcular_energia(5.0)
    1.9952623149688795e+19
    
    References
    ----------
    .. [1] Kanamori, H. (1977). The energy release in great earthquakes.
           J. Geophys. Res., 82, 2981-2987.
    """
    if magnitud < 0 or magnitud > 10:
        raise ValueError(f"Magnitud inválida: {magnitud}")
    return 10 ** (1.5 * magnitud + 11.8)
```

---

## Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con cobertura
pytest --cov=seismex --cov-report=html

# Tests específicos
pytest tests/test_esd.py
pytest tests/test_esd.py::test_calcular_energia

# Tests verbosos
pytest -v

# Detener en primer fallo
pytest -x
```

### Escribir Tests

Estructura de archivos de test:

```
tests/
├── unit/
│   ├── test_catalog.py
│   ├── test_esd.py
│   └── test_gutenberg_richter.py
├── integration/
│   ├── test_esd_workflow.py
│   └── test_visualization.py
├── conftest.py          # Fixtures compartidos
└── data/                # Datos de prueba
    └── test_catalog.csv
```

Ejemplo de test:

```python
import pytest
import numpy as np
from seismex.analysis.esd import CalculadoraESD, ConfiguracionESD

class TestCalculadoraESD:
    """Tests para CalculadoraESD."""
    
    @pytest.fixture
    def config_default(self):
        """Configuración por defecto para tests."""
        return ConfiguracionESD(
            tamano_celda=10.0,
            rango_profundidad=(0, 100)
        )
    
    def test_calcular_energia_magnitud_5(self):
        """Energía para Mw=5 debe ser ~2e19 ergios."""
        energia = CalculadoraESD.calcular_energia(5.0)
        assert np.isclose(energia, 1.995e19, rtol=0.01)
    
    def test_calcular_energia_magnitud_negativa(self):
        """Magnitud negativa debe lanzar ValueError."""
        with pytest.raises(ValueError, match="inválida"):
            CalculadoraESD.calcular_energia(-1.0)
    
    @pytest.mark.parametrize("magnitud,expected_log", [
        (3.0, 16.3),
        (5.0, 19.3),
        (7.0, 22.3),
    ])
    def test_calcular_energia_parametrizado(self, magnitud, expected_log):
        """Verificar relación log-lineal."""
        energia = CalculadoraESD.calcular_energia(magnitud)
        log_energia = np.log10(energia)
        assert np.isclose(log_energia, expected_log, atol=0.1)
```

---

## Documentación

### Estructura

```
docs/
├── api/           # Documentación generada automáticamente
├── tutorials/     # Tutoriales paso a paso
├── examples/      # Ejemplos de uso
└── index.rst      # Página principal
```

### Generar Documentación

```bash
cd docs
make html
# Abrir docs/_build/html/index.html
```

### Formato de Tutoriales

Los tutoriales deben incluir:

1. **Objetivo claro** al inicio
2. **Prerrequisitos** listados
3. **Pasos numerados** con código ejecutable
4. **Explicaciones** de cada paso
5. **Resultados esperados** (incluyendo figuras)
6. **Errores comunes** y soluciones

---

## Pull Requests

### Antes de Abrir un PR

- [ ] Código formateado con Black e isort
- [ ] Sin errores de flake8
- [ ] Tests pasan (`pytest`)
- [ ] Cobertura de tests para código nuevo
- [ ] Docstrings para funciones/clases públicas
- [ ] CHANGELOG actualizado (si aplica)

### Plantilla de PR

```markdown
## Descripción

Breve descripción de los cambios.

## Tipo de Cambio

- [ ] 🐛 Bug fix
- [ ] ✨ Nueva funcionalidad
- [ ] 📚 Documentación
- [ ] 🎨 Refactoring

## Cambios Realizados

- Cambio 1
- Cambio 2

## Tests

Describe cómo se probaron los cambios.

## Checklist

- [ ] Tests pasan
- [ ] Código formateado
- [ ] Documentación actualizada
```

### Convenciones de Commits

Usar [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: agregar cálculo de valor-b por máxima verosimilitud
fix: corregir error en conversión de magnitudes
docs: actualizar README con ejemplos de uso
test: agregar tests para módulo de isosistas
refactor: simplificar estructura de CatalogoSismico
```

---

## Reportar Bugs

### Información a Incluir

1. **Descripción** clara del problema
2. **Pasos para reproducir**
3. **Comportamiento esperado** vs **observado**
4. **Versión** de SEISMEX y Python
5. **Sistema operativo**
6. **Código de ejemplo** mínimo que reproduce el error
7. **Stack trace** completo (si aplica)

### Plantilla

```markdown
## Descripción del Bug

Una descripción clara y concisa del bug.

## Pasos para Reproducir

1. Cargar catálogo con `...`
2. Ejecutar `...`
3. Ver error

## Comportamiento Esperado

Qué esperabas que pasara.

## Comportamiento Observado

Qué pasó realmente.

## Entorno

- SEISMEX: 0.1.0
- Python: 3.10
- OS: Ubuntu 22.04

## Código de Ejemplo

```python
from seismex import ...
# Código mínimo que reproduce el error
```

## Stack Trace

```
Traceback (most recent call last):
  ...
```
```

---

## Solicitar Funcionalidades

### Información a Incluir

1. **Descripción** de la funcionalidad
2. **Caso de uso** (¿por qué es útil?)
3. **Ejemplo de API** propuesto
4. **Alternativas** consideradas

---

## Contacto

- **Issues**: Para bugs y solicitudes de funcionalidades
- **Discussions**: Para preguntas generales y discusiones
- **Email**: seismex@example.com

---

¡Gracias por contribuir a SEISMEX! 🌎🔬
