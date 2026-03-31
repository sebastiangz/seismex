"""
SEISMEX Data - Sistema de Caché
================================

Sistema de caché persistente para datos sísmicos descargados.
Características:
- Almacenamiento en disco con compresión opcional
- Expiración configurable
- Limpieza automática
- Estadísticas de uso
"""

import os
import json
import gzip
import pickle
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict, List, Union
import shutil

logger = logging.getLogger(__name__)


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CacheEntry:
    """Metadatos de una entrada de caché."""
    key: str
    created_at: datetime
    expires_at: Optional[datetime]
    size_bytes: int
    source: str
    query_params: Dict[str, Any]
    compressed: bool
    hits: int = 0
    last_accessed: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario serializable."""
        return {
            'key': self.key,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'size_bytes': self.size_bytes,
            'source': self.source,
            'query_params': self.query_params,
            'compressed': self.compressed,
            'hits': self.hits,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Crea instancia desde diccionario."""
        return cls(
            key=data['key'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            size_bytes=data['size_bytes'],
            source=data['source'],
            query_params=data.get('query_params', {}),
            compressed=data.get('compressed', False),
            hits=data.get('hits', 0),
            last_accessed=datetime.fromisoformat(data['last_accessed']) if data.get('last_accessed') else None,
        )


@dataclass
class CacheStats:
    """Estadísticas del caché."""
    total_entries: int
    total_size_bytes: int
    total_size_mb: float
    oldest_entry: Optional[datetime]
    newest_entry: Optional[datetime]
    total_hits: int
    expired_entries: int
    sources: Dict[str, int]
    
    def __str__(self) -> str:
        lines = [
            "=" * 50,
            "SEISMEX Cache - Estadísticas",
            "=" * 50,
            f"Entradas totales: {self.total_entries}",
            f"Tamaño total: {self.total_size_mb:.2f} MB",
            f"Hits totales: {self.total_hits}",
            f"Entradas expiradas: {self.expired_entries}",
            "",
            "Por fuente:",
        ]
        for source, count in self.sources.items():
            lines.append(f"  {source}: {count} entradas")
        
        if self.oldest_entry:
            lines.append(f"\nEntrada más antigua: {self.oldest_entry}")
        if self.newest_entry:
            lines.append(f"Entrada más reciente: {self.newest_entry}")
        
        lines.append("=" * 50)
        return "\n".join(lines)


# =============================================================================
# GESTOR DE CACHÉ
# =============================================================================

class CacheManager:
    """
    Gestor de caché para datos sísmicos.
    
    Almacena datos descargados en disco con:
    - Compresión gzip opcional
    - Expiración configurable
    - Índice de metadatos
    - Limpieza automática
    
    Ejemplo de uso:
    
        >>> cache = CacheManager()
        >>> cache.set('usgs_mexico_2024', dataframe, source='usgs', 
        ...           query_params={'region': 'mexico', 'year': 2024})
        >>> df = cache.get('usgs_mexico_2024')
        >>> print(cache.stats())
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        expiration_days: int = 30,
        max_size_mb: int = 1000,
        compression: bool = True
    ):
        """
        Inicializa el gestor de caché.
        
        Args:
            cache_dir: Directorio de caché (default: ~/.seismex/cache)
            expiration_days: Días hasta expiración (0 = sin expiración)
            max_size_mb: Tamaño máximo en MB (0 = sin límite)
            compression: Habilitar compresión gzip
        """
        from seismex.data.config import get_config
        
        config = get_config()
        
        self.cache_dir = Path(cache_dir) if cache_dir else config.general.cache_dir
        self.cache_dir = Path(str(self.cache_dir).replace("~", str(Path.home())))
        
        self.expiration_days = expiration_days or config.general.cache_expiration_days
        self.max_size_mb = max_size_mb or config.general.cache_max_size_mb
        self.compression = compression if compression is not None else config.general.cache_compression
        
        # Crear directorio si no existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de índice
        self._index_file = self.cache_dir / "cache_index.json"
        self._index: Dict[str, CacheEntry] = {}
        
        # Cargar índice existente
        self._load_index()
        
        logger.debug(f"CacheManager inicializado: {self.cache_dir}")
    
    # =========================================================================
    # GESTIÓN DE ÍNDICE
    # =========================================================================
    
    def _load_index(self) -> None:
        """Carga el índice de caché desde disco."""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._index = {
                    k: CacheEntry.from_dict(v) 
                    for k, v in data.items()
                }
                logger.debug(f"Índice cargado: {len(self._index)} entradas")
            except Exception as e:
                logger.warning(f"Error al cargar índice de caché: {e}")
                self._index = {}
        else:
            self._index = {}
    
    def _save_index(self) -> None:
        """Guarda el índice de caché a disco."""
        try:
            data = {k: v.to_dict() for k, v in self._index.items()}
            with open(self._index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error al guardar índice de caché: {e}")
    
    def _generate_key(self, source: str, query_params: Dict[str, Any]) -> str:
        """
        Genera una clave única basada en fuente y parámetros.
        
        Args:
            source: Fuente de datos (ssn, usgs, isc, etc.)
            query_params: Parámetros de la consulta
            
        Returns:
            Clave hash única
        """
        # Ordenar parámetros para consistencia
        sorted_params = json.dumps(query_params, sort_keys=True, default=str)
        content = f"{source}:{sorted_params}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"{source}_{hash_val}"
    
    def _get_data_path(self, key: str, compressed: bool = None) -> Path:
        """Obtiene la ruta del archivo de datos."""
        if compressed is None:
            compressed = self.compression
        ext = ".pkl.gz" if compressed else ".pkl"
        return self.cache_dir / f"{key}{ext}"
    
    # =========================================================================
    # OPERACIONES CRUD
    # =========================================================================
    
    def set(
        self,
        key: str,
        data: Any,
        source: str = "unknown",
        query_params: Optional[Dict[str, Any]] = None,
        expiration_days: Optional[int] = None
    ) -> bool:
        """
        Almacena datos en caché.
        
        Args:
            key: Clave única (o se genera automáticamente)
            data: Datos a almacenar (DataFrame, dict, etc.)
            source: Fuente de datos (ssn, usgs, isc)
            query_params: Parámetros de la consulta original
            expiration_days: Días hasta expiración (override)
            
        Returns:
            True si se almacenó correctamente
        """
        query_params = query_params or {}
        exp_days = expiration_days if expiration_days is not None else self.expiration_days
        
        # Calcular fecha de expiración
        expires_at = None
        if exp_days > 0:
            expires_at = datetime.now() + timedelta(days=exp_days)
        
        # Verificar espacio disponible
        if self.max_size_mb > 0:
            self._enforce_size_limit()
        
        # Guardar datos
        data_path = self._get_data_path(key, self.compression)
        try:
            if self.compression:
                with gzip.open(data_path, 'wb') as f:
                    pickle.dump(data, f)
            else:
                with open(data_path, 'wb') as f:
                    pickle.dump(data, f)
            
            size_bytes = data_path.stat().st_size
            
            # Crear entrada de índice
            entry = CacheEntry(
                key=key,
                created_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=size_bytes,
                source=source,
                query_params=query_params,
                compressed=self.compression,
                hits=0,
                last_accessed=None
            )
            
            self._index[key] = entry
            self._save_index()
            
            logger.info(f"Caché almacenado: {key} ({size_bytes / 1024:.1f} KB)")
            return True
            
        except Exception as e:
            logger.error(f"Error al almacenar en caché: {e}")
            if data_path.exists():
                data_path.unlink()
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Recupera datos del caché.
        
        Args:
            key: Clave de la entrada
            default: Valor por defecto si no existe o expiró
            
        Returns:
            Datos almacenados o default
        """
        # Verificar si existe en índice
        entry = self._index.get(key)
        if entry is None:
            return default
        
        # Verificar expiración
        if entry.is_expired():
            logger.debug(f"Entrada expirada: {key}")
            self.delete(key)
            return default
        
        # Obtener ruta del archivo
        data_path = self._get_data_path(key, entry.compressed)
        if not data_path.exists():
            logger.warning(f"Archivo de caché no encontrado: {data_path}")
            del self._index[key]
            self._save_index()
            return default
        
        # Cargar datos
        try:
            if entry.compressed:
                with gzip.open(data_path, 'rb') as f:
                    data = pickle.load(f)
            else:
                with open(data_path, 'rb') as f:
                    data = pickle.load(f)
            
            # Actualizar estadísticas
            entry.hits += 1
            entry.last_accessed = datetime.now()
            self._save_index()
            
            logger.debug(f"Caché hit: {key} (hits: {entry.hits})")
            return data
            
        except Exception as e:
            logger.error(f"Error al leer caché: {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """
        Elimina una entrada del caché.
        
        Args:
            key: Clave de la entrada
            
        Returns:
            True si se eliminó
        """
        entry = self._index.get(key)
        if entry is None:
            return False
        
        # Eliminar archivo
        data_path = self._get_data_path(key, entry.compressed)
        if data_path.exists():
            data_path.unlink()
        
        # Eliminar del índice
        del self._index[key]
        self._save_index()
        
        logger.info(f"Caché eliminado: {key}")
        return True
    
    def exists(self, key: str) -> bool:
        """Verifica si una clave existe y no ha expirado."""
        entry = self._index.get(key)
        if entry is None:
            return False
        if entry.is_expired():
            return False
        return self._get_data_path(key, entry.compressed).exists()
    
    def get_or_set(
        self,
        key: str,
        fetcher: callable,
        source: str = "unknown",
        query_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Obtiene del caché o ejecuta fetcher y almacena.
        
        Args:
            key: Clave de caché
            fetcher: Función que obtiene los datos si no están en caché
            source: Fuente de datos
            query_params: Parámetros de consulta
            **kwargs: Argumentos adicionales para fetcher
            
        Returns:
            Datos del caché o recién obtenidos
        """
        # Intentar obtener del caché
        data = self.get(key)
        if data is not None:
            return data
        
        # Ejecutar fetcher
        logger.info(f"Caché miss: {key}, ejecutando fetcher...")
        data = fetcher(**kwargs)
        
        # Almacenar en caché
        if data is not None:
            self.set(key, data, source=source, query_params=query_params)
        
        return data
    
    # =========================================================================
    # BÚSQUEDA Y LISTADO
    # =========================================================================
    
    def find(
        self,
        source: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        include_expired: bool = False
    ) -> List[CacheEntry]:
        """
        Busca entradas en el caché.
        
        Args:
            source: Filtrar por fuente
            created_after: Creadas después de esta fecha
            created_before: Creadas antes de esta fecha
            include_expired: Incluir entradas expiradas
            
        Returns:
            Lista de entradas que coinciden
        """
        results = []
        
        for entry in self._index.values():
            # Filtrar por expiración
            if not include_expired and entry.is_expired():
                continue
            
            # Filtrar por fuente
            if source and entry.source != source:
                continue
            
            # Filtrar por fecha
            if created_after and entry.created_at < created_after:
                continue
            if created_before and entry.created_at > created_before:
                continue
            
            results.append(entry)
        
        return sorted(results, key=lambda e: e.created_at, reverse=True)
    
    def list_sources(self) -> List[str]:
        """Lista todas las fuentes con datos en caché."""
        sources = set(e.source for e in self._index.values())
        return sorted(sources)
    
    # =========================================================================
    # LIMPIEZA Y MANTENIMIENTO
    # =========================================================================
    
    def clean_expired(self) -> int:
        """
        Elimina todas las entradas expiradas.
        
        Returns:
            Número de entradas eliminadas
        """
        expired_keys = [
            key for key, entry in self._index.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        logger.info(f"Limpieza: {len(expired_keys)} entradas expiradas eliminadas")
        return len(expired_keys)
    
    def clean_all(self) -> int:
        """
        Elimina todo el caché.
        
        Returns:
            Número de entradas eliminadas
        """
        count = len(self._index)
        
        # Eliminar archivos de datos
        for key, entry in list(self._index.items()):
            data_path = self._get_data_path(key, entry.compressed)
            if data_path.exists():
                data_path.unlink()
        
        # Limpiar índice
        self._index.clear()
        self._save_index()
        
        logger.info(f"Caché completamente limpiado: {count} entradas eliminadas")
        return count
    
    def clean_source(self, source: str) -> int:
        """
        Elimina todas las entradas de una fuente específica.
        
        Args:
            source: Fuente a limpiar (ssn, usgs, isc, etc.)
            
        Returns:
            Número de entradas eliminadas
        """
        keys_to_delete = [
            key for key, entry in self._index.items()
            if entry.source == source
        ]
        
        for key in keys_to_delete:
            self.delete(key)
        
        logger.info(f"Limpieza {source}: {len(keys_to_delete)} entradas eliminadas")
        return len(keys_to_delete)
    
    def _enforce_size_limit(self) -> None:
        """Asegura que el caché no exceda el límite de tamaño."""
        if self.max_size_mb <= 0:
            return
        
        max_bytes = self.max_size_mb * 1024 * 1024
        current_size = sum(e.size_bytes for e in self._index.values())
        
        if current_size <= max_bytes:
            return
        
        # Ordenar por último acceso (más antiguo primero)
        entries = sorted(
            self._index.items(),
            key=lambda x: x[1].last_accessed or x[1].created_at
        )
        
        # Eliminar hasta estar bajo el límite
        for key, entry in entries:
            if current_size <= max_bytes * 0.9:  # Dejar 10% de margen
                break
            self.delete(key)
            current_size -= entry.size_bytes
        
        logger.info(f"Límite de tamaño aplicado, tamaño actual: {current_size / 1024 / 1024:.1f} MB")
    
    # =========================================================================
    # ESTADÍSTICAS
    # =========================================================================
    
    def stats(self) -> CacheStats:
        """
        Obtiene estadísticas del caché.
        
        Returns:
            CacheStats con información del caché
        """
        entries = list(self._index.values())
        
        if not entries:
            return CacheStats(
                total_entries=0,
                total_size_bytes=0,
                total_size_mb=0.0,
                oldest_entry=None,
                newest_entry=None,
                total_hits=0,
                expired_entries=0,
                sources={}
            )
        
        total_size = sum(e.size_bytes for e in entries)
        dates = [e.created_at for e in entries]
        sources_count: Dict[str, int] = {}
        for e in entries:
            sources_count[e.source] = sources_count.get(e.source, 0) + 1
        
        return CacheStats(
            total_entries=len(entries),
            total_size_bytes=total_size,
            total_size_mb=total_size / 1024 / 1024,
            oldest_entry=min(dates),
            newest_entry=max(dates),
            total_hits=sum(e.hits for e in entries),
            expired_entries=sum(1 for e in entries if e.is_expired()),
            sources=sources_count
        )
    
    def __len__(self) -> int:
        return len(self._index)
    
    def __contains__(self, key: str) -> bool:
        return self.exists(key)
    
    def __repr__(self) -> str:
        stats = self.stats()
        return f"CacheManager(entries={stats.total_entries}, size={stats.total_size_mb:.1f}MB)"


# =============================================================================
# SINGLETON GLOBAL
# =============================================================================

_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """
    Obtiene la instancia global del gestor de caché.
    
    Returns:
        CacheManager singleton
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance


def clear_cache() -> int:
    """
    Limpia todo el caché global.
    
    Returns:
        Número de entradas eliminadas
    """
    return get_cache().clean_all()
