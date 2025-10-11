"""
CVE Arama Modülü - Production Ready
Bu modül Qdrant üzerinde CVE araması için hybrid search API sağlar.
Dense vektörlere öncelik verir (semantik search ağırlıklı).
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import uuid

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from FlagEmbedding import BGEM3FlagModel
import torch

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SearchConfig:
    """Arama yapılandırma ayarları"""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: Optional[str] = None  # Cloud deployment için
    qdrant_https: bool = False  # Cloud için True
    huggingface_token: Optional[str] = None  # Private HuggingFace Space için
    collection_name: str = "cve_collection_hybrid"
    model_name: str = "BAAI/bge-m3"
    # Dense vektör ağırlığı daha yüksek (semantik search öncelikli)
    default_dense_weight: float = 0.7
    default_sparse_weight: float = 0.3
    max_retries: int = 3
    timeout: int = 30


@dataclass
class SearchResult:
    """Arama sonucu veri yapısı"""
    cve_id: str
    score: float
    dense_score: float
    sparse_score: float
    severity: Optional[str]
    base_score: Optional[float]
    attack_vector: Optional[str]
    description: str
    published_date: Optional[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict formatına dönüştür"""
        return {
            "cve_id": self.cve_id,
            "score": self.score,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "severity": self.severity,
            "base_score": self.base_score,
            "attack_vector": self.attack_vector,
            "description": self.description,
            "published_date": self.published_date,
            "metadata": self.metadata
        }


class CVESearchEngine:
    """
    Production-ready CVE arama motoru.
    Qdrant üzerinde hybrid search (dense + sparse) yapar.
    """
    
    def __init__(self, config: Optional[SearchConfig] = None):
        """
        Args:
            config: Arama yapılandırma ayarları. None ise default kullanılır.
        """
        self.config = config or SearchConfig()
        self._client = None
        self._model = None
        self._initialize()
    
    def _initialize(self):
        """Qdrant client ve BGE-M3 modelini başlat"""
        try:
            # Qdrant bağlantısı (Cloud veya Local)
            logger.info(f"Qdrant'a bağlanılıyor: {self.config.qdrant_host}:{self.config.qdrant_port}")
            
            # HuggingFace Private Space için
            if self.config.huggingface_token:
                # HuggingFace Space'e Bearer token ile bağlan
                headers = {"Authorization": f"Bearer {self.config.huggingface_token}"}
                self._client = QdrantClient(
                    url=self.config.qdrant_host,
                    timeout=self.config.timeout,
                    https=True,
                    headers=headers
                )
            # Cloud deployment için API key kullan
            elif self.config.qdrant_api_key:
                self._client = QdrantClient(
                    url=self.config.qdrant_host,
                    api_key=self.config.qdrant_api_key,
                    timeout=self.config.timeout,
                    https=self.config.qdrant_https
                )
            else:
                # Local deployment için
                self._client = QdrantClient(
                    host=self.config.qdrant_host,
                    port=self.config.qdrant_port,
                    timeout=self.config.timeout
                )
            
            # Collection kontrolü
            collections = self._client.get_collections().collections
            collection_exists = any(c.name == self.config.collection_name for c in collections)
            if not collection_exists:
                raise ValueError(f"Collection '{self.config.collection_name}' bulunamadı!")
            
            logger.info(f"Collection '{self.config.collection_name}' bulundu")
            
            # BGE-M3 model yükleme
            logger.info(f"BGE-M3 modeli yükleniyor: {self.config.model_name}")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            use_fp16 = device == "cuda"
            self._model = BGEM3FlagModel(self.config.model_name, use_fp16=use_fp16)
            logger.info(f"Model yüklendi (Device: {device.upper()})")
            
        except Exception as e:
            logger.error(f"Başlatma hatası: {e}")
            raise
    
    def _encode_query(self, query: str) -> Tuple[List[float], models.SparseVector]:
        """
        Query'yi dense ve sparse vektörlere çevir.
        
        Args:
            query: Arama sorgusu
            
        Returns:
            (dense_vector, sparse_vector) tuple'ı
        """
        try:
            # Dense vektör
            dense_vec = self._model.encode([query], return_dense=True)['dense_vecs'][0]
            
            # Sparse vektör
            sparse_output = self._model.encode([query], return_sparse=True)['lexical_weights'][0]
            sparse_vec = models.SparseVector(
                indices=list(sparse_output.keys()),
                values=list(sparse_output.values())
            )
            
            return dense_vec.tolist(), sparse_vec
            
        except Exception as e:
            logger.error(f"Query encoding hatası: {e}")
            raise
    
    def search(
        self,
        query: str,
        limit: int = 10,
        dense_weight: Optional[float] = None,
        sparse_weight: Optional[float] = None,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        Hybrid search (dense + sparse) yapar.
        
        Args:
            query: Arama sorgusu
            limit: Maksimum sonuç sayısı
            dense_weight: Dense vektör ağırlığı (None ise config'den alınır)
            sparse_weight: Sparse vektör ağırlığı (None ise config'den alınır)
            min_score: Minimum skor eşiği
            
        Returns:
            SearchResult listesi
        """
        if not query or not query.strip():
            logger.warning("Boş query alındı")
            return []
        
        # Ağırlıkları ayarla
        d_weight = dense_weight if dense_weight is not None else self.config.default_dense_weight
        s_weight = sparse_weight if sparse_weight is not None else self.config.default_sparse_weight
        
        # Ağırlıkları normalize et
        total_weight = d_weight + s_weight
        d_weight = d_weight / total_weight
        s_weight = s_weight / total_weight
        
        logger.info(f"Arama başlatıldı: '{query}' (limit={limit}, dense={d_weight:.2f}, sparse={s_weight:.2f})")
        
        try:
            # Query'yi vektörlere çevir
            dense_vec, sparse_vec = self._encode_query(query)
            
            # Dense arama
            dense_results = self._search_dense(dense_vec, limit * 2)
            
            # Sparse arama
            sparse_results = self._search_sparse(sparse_vec, limit * 2)
            
            # Sonuçları birleştir
            combined_results = self._combine_results(
                dense_results, sparse_results, d_weight, s_weight
            )
            
            # Minimum skor filtresi uygula
            if min_score > 0:
                combined_results = [r for r in combined_results if r.score >= min_score]
            
            # Limit uygula
            final_results = combined_results[:limit]
            
            logger.info(f"Arama tamamlandı: {len(final_results)} sonuç bulundu")
            return final_results
            
        except Exception as e:
            logger.error(f"Arama hatası: {e}")
            raise
    
    def _search_dense(self, dense_vector: List[float], limit: int) -> List[Dict]:
        """Dense (semantik) arama yapar"""
        try:
            results = self._client.query_points(
                collection_name=self.config.collection_name,
                query=dense_vector,
                using="text-dense",
                limit=limit,
                with_payload=True
            )
            return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
        except Exception as e:
            logger.error(f"Dense search hatası: {e}")
            return []
    
    def _search_sparse(self, sparse_vector: models.SparseVector, limit: int) -> List[Dict]:
        """Sparse (keyword) arama yapar"""
        try:
            results = self._client.query_points(
                collection_name=self.config.collection_name,
                query=sparse_vector,
                using="text-sparse",
                limit=limit,
                with_payload=True
            )
            return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
        except Exception as e:
            logger.error(f"Sparse search hatası: {e}")
            return []
    
    def _combine_results(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict],
        dense_weight: float,
        sparse_weight: float
    ) -> List[SearchResult]:
        """Dense ve sparse sonuçları birleştirir"""
        combined = {}
        
        # Dense sonuçları ekle
        for result in dense_results:
            point_id = result["id"]
            combined[point_id] = {
                "payload": result["payload"],
                "dense_score": result["score"],
                "sparse_score": 0.0
            }
        
        # Sparse sonuçları ekle
        for result in sparse_results:
            point_id = result["id"]
            if point_id not in combined:
                combined[point_id] = {
                    "payload": result["payload"],
                    "dense_score": 0.0,
                    "sparse_score": result["score"]
                }
            else:
                combined[point_id]["sparse_score"] = result["score"]
        
        # Hybrid skor hesapla ve SearchResult objelerine çevir
        results = []
        for point_id, data in combined.items():
            payload = data["payload"]
            metadata = payload.get("metadata", {})
            
            # Hybrid skor
            hybrid_score = (dense_weight * data["dense_score"]) + (sparse_weight * data["sparse_score"])
            
            result = SearchResult(
                cve_id=payload.get("cve_id", str(point_id)),
                score=hybrid_score,
                dense_score=data["dense_score"],
                sparse_score=data["sparse_score"],
                severity=metadata.get("severity"),
                base_score=metadata.get("base_score"),
                attack_vector=metadata.get("attack_vector"),
                description=payload.get("content", "")[:500],  # İlk 500 karakter
                published_date=metadata.get("published_date"),
                metadata=metadata
            )
            results.append(result)
        
        # Skora göre sırala
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def search_by_severity(
        self,
        query: str,
        severity: str,
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """
        Severity filtresine göre arama yapar.
        
        Args:
            query: Arama sorgusu
            severity: Severity seviyesi (CRITICAL, HIGH, MEDIUM, LOW)
            limit: Maksimum sonuç sayısı
            **kwargs: search() metoduna iletilecek ek parametreler
            
        Returns:
            Filtrelenmiş SearchResult listesi
        """
        # Önce normal arama yap (daha fazla sonuç al)
        all_results = self.search(query, limit=limit * 3, **kwargs)
        
        # Severity'ye göre filtrele
        severity_upper = severity.upper()
        filtered = [r for r in all_results if r.severity and r.severity.upper() == severity_upper]
        
        logger.info(f"Severity filtreleme: {len(filtered)} sonuç (severity={severity})")
        return filtered[:limit]
    
    def get_cve_by_id(self, cve_id: str) -> Optional[SearchResult]:
        """
        CVE ID'ye göre doğrudan CVE detaylarını getirir.
        
        Args:
            cve_id: CVE ID (ör: CVE-2024-12345)
            
        Returns:
            SearchResult veya None
        """
        try:
            # CVE ID'den UUID oluştur
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, cve_id))
            
            results = self._client.retrieve(
                collection_name=self.config.collection_name,
                ids=[point_uuid],
                with_payload=True,
                with_vectors=False
            )
            
            if not results:
                logger.warning(f"CVE bulunamadı: {cve_id}")
                return None
            
            payload = results[0].payload
            metadata = payload.get("metadata", {})
            
            return SearchResult(
                cve_id=payload.get("cve_id", cve_id),
                score=1.0,  # Direct fetch, skor yok
                dense_score=0.0,
                sparse_score=0.0,
                severity=metadata.get("severity"),
                base_score=metadata.get("base_score"),
                attack_vector=metadata.get("attack_vector"),
                description=payload.get("content", ""),
                published_date=metadata.get("published_date"),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"CVE getirme hatası ({cve_id}): {e}")
            return None
    
    def health_check(self) -> bool:
        """
        Sistem sağlık kontrolü yapar.
        
        Returns:
            True: Sistem sağlıklı, False: Sorun var
        """
        try:
            # Qdrant bağlantısını kontrol et
            self._client.get_collections()
            
            # Collection'ı kontrol et
            info = self._client.get_collection(self.config.collection_name)
            logger.info(f"Health check OK - Collection: {info.points_count} points")
            return True
            
        except Exception as e:
            logger.error(f"Health check FAILED: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Collection istatistiklerini döner.
        
        Returns:
            İstatistik bilgileri
        """
        try:
            info = self._client.get_collection(self.config.collection_name)
            return {
                "collection_name": self.config.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.value if info.status else "unknown"
            }
        except Exception as e:
            logger.error(f"Stats getirme hatası: {e}")
            return {}


# Global engine instance (lazy initialization için)
_engine_instance: Optional[CVESearchEngine] = None


def get_search_engine(config: Optional[SearchConfig] = None) -> CVESearchEngine:
    """
    Singleton pattern ile search engine instance döner.
    
    Args:
        config: Yapılandırma (None ise default)
        
    Returns:
        CVESearchEngine instance
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = CVESearchEngine(config)
    return _engine_instance


if __name__ == "__main__":
    # Production ready module
    print("CVE Search Engine - Production Ready")
    print("Use: from Qdrant.cve_search import get_search_engine")

