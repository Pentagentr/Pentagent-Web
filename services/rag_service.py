"""
RAG Servis Modülü
CVE RAG sistemi ile entegrasyon için servis
Qdrant üzerinden CVE araması yapar
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# RAG modülünü import et
rag_pent_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Rag-Pent')
sys.path.insert(0, rag_pent_path)

try:
    from Qdrant.cve_search import CVESearchEngine, SearchConfig, SearchResult
except ImportError as e:
    logging.error(f"RAG modülü import edilemedi: {e}")
    CVESearchEngine = None
    SearchConfig = None
    SearchResult = None

logger = logging.getLogger(__name__)


@dataclass
class CVEResult:
    """CVE arama sonucu"""
    cve_id: str
    score: float
    severity: Optional[str]
    base_score: Optional[float]
    attack_vector: Optional[str]
    description: str
    published_date: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict formatına dönüştür"""
        return {
            "cve_id": self.cve_id,
            "score": self.score,
            "severity": self.severity,
            "base_score": self.base_score,
            "attack_vector": self.attack_vector,
            "description": self.description,
            "published_date": self.published_date
        }


class RAGService:
    """
    CVE RAG sistemi ile etkileşim için servis sınıfı.
    Singleton pattern kullanır.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._engine = None
        self._available = False
        self._initialize()
        self._initialized = True
    
    def _initialize(self):
        """RAG engine'i başlat"""
        try:
            if CVESearchEngine is None:
                logger.warning("CVE Search Engine modülü yüklenemedi. RAG özellikleri devre dışı.")
                return
            
            logger.info("RAG servis başlatılıyor...")
            
            # Environment variables'dan config oluştur
            config = SearchConfig()
            
            # Cloud deployment için https kontrolü
            is_cloud = config.qdrant_api_key is not None
            if is_cloud:
                logger.info(f"Qdrant Cloud'a bağlanılıyor: {config.qdrant_host}")
            else:
                logger.info(f"Local Qdrant'a bağlanılıyor: {config.qdrant_host}:{config.qdrant_port}")
            
            self._engine = CVESearchEngine(config)
            
            # Health check
            if self._engine.health_check():
                self._available = True
                stats = self._engine.get_stats()
                logger.info(f"✅ RAG servisi başlatıldı: {stats.get('points_count', 0)} CVE yüklü")
            else:
                logger.warning("RAG servisi başlatılamadı: Qdrant sağlık kontrolü başarısız")
                
        except Exception as e:
            logger.warning(f"RAG servisi başlatılamadı: {e}")
            logger.info("RAG özellikleri devre dışı. Qdrant'ın çalıştığından emin olun.")
    
    def is_available(self) -> bool:
        """RAG servisinin kullanılabilir olup olmadığını kontrol et"""
        return self._available and self._engine is not None
    
    def search_cve(
        self,
        query: str,
        limit: int = 5,
        severity: Optional[str] = None
    ) -> List[CVEResult]:
        """
        CVE araması yap.
        
        Args:
            query: Arama sorgusu
            limit: Maksimum sonuç sayısı (default: 5)
            severity: Severity filtresi (CRITICAL, HIGH, MEDIUM, LOW)
            
        Returns:
            CVEResult listesi
        """
        if not self.is_available():
            logger.warning("RAG servisi kullanılamıyor")
            return []
        
        try:
            logger.info(f"CVE araması yapılıyor: '{query}' (limit={limit}, severity={severity})")
            
            # Severity filtresi varsa
            if severity:
                results = self._engine.search_by_severity(
                    query=query,
                    severity=severity,
                    limit=limit
                )
            else:
                results = self._engine.search(query, limit=limit)
            
            # SearchResult'ları CVEResult'a dönüştür
            cve_results = []
            for r in results:
                cve_results.append(CVEResult(
                    cve_id=r.cve_id,
                    score=r.score,
                    severity=r.severity,
                    base_score=r.base_score,
                    attack_vector=r.attack_vector,
                    description=r.description,
                    published_date=r.published_date
                ))
            
            logger.info(f"✅ {len(cve_results)} CVE bulundu")
            return cve_results
            
        except Exception as e:
            logger.error(f"CVE arama hatası: {e}")
            return []
    
    def get_cve_by_id(self, cve_id: str) -> Optional[CVEResult]:
        """
        CVE ID ile direkt CVE detayı getir.
        
        Args:
            cve_id: CVE ID (ör: CVE-2024-12345)
            
        Returns:
            CVEResult veya None
        """
        if not self.is_available():
            return None
        
        try:
            result = self._engine.get_cve_by_id(cve_id)
            if result:
                return CVEResult(
                    cve_id=result.cve_id,
                    score=result.score,
                    severity=result.severity,
                    base_score=result.base_score,
                    attack_vector=result.attack_vector,
                    description=result.description,
                    published_date=result.published_date
                )
            return None
            
        except Exception as e:
            logger.error(f"CVE getirme hatası ({cve_id}): {e}")
            return None
    
    def analyze_scan_results(self, scan_results: Dict[str, Any]) -> List[CVEResult]:
        """
        Tarama sonuçlarını analiz edip ilgili CVE'leri bul.
        
        Args:
            scan_results: Tarama sonuçları (vulnerability bilgileri içeren)
            
        Returns:
            En alakalı CVE'lerin listesi
        """
        if not self.is_available():
            return []
        
        try:
            # Scan sonuçlarından query oluştur
            query = self._generate_query_from_scan(scan_results)
            
            if not query:
                logger.warning("Scan sonuçlarından query oluşturulamadı")
                return []
            
            logger.info(f"Scan analizi için oluşturulan query: '{query}'")
            
            # CVE araması yap
            return self.search_cve(query, limit=5)
            
        except Exception as e:
            logger.error(f"Scan analizi hatası: {e}")
            return []
    
    def _generate_query_from_scan(self, scan_results: Dict[str, Any]) -> str:
        """
        Scan sonuçlarından RAG sorgusu oluştur.
        
        Args:
            scan_results: Tarama sonuçları
            
        Returns:
            RAG query string
        """
        query_parts = []
        
        # Vulnerability türlerini topla
        vulnerabilities = scan_results.get("vulnerabilities", [])
        if vulnerabilities:
            vuln_types = [v.get("type", "") for v in vulnerabilities if v.get("type")]
            if vuln_types:
                query_parts.extend(vuln_types[:3])  # İlk 3 vulnerability türü
        
        # Teknoloji ve servis bilgilerini ekle
        technologies = scan_results.get("technologies", [])
        if technologies:
            query_parts.extend(technologies[:2])  # İlk 2 teknoloji
        
        # Açık portlar ve servisler
        services = scan_results.get("services", [])
        if services:
            service_names = [s.get("name", "") for s in services if s.get("name")]
            query_parts.extend(service_names[:2])
        
        # Query'yi oluştur
        if query_parts:
            return " ".join(query_parts)
        
        # Fallback: target'ı kullan
        target = scan_results.get("target", "")
        if target:
            return f"web application vulnerability {target}"
        
        return "web security vulnerability"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        RAG servis istatistikleri.
        
        Returns:
            İstatistik bilgileri
        """
        if not self.is_available():
            return {
                "available": False,
                "message": "RAG servisi kullanılamıyor"
            }
        
        try:
            stats = self._engine.get_stats()
            return {
                "available": True,
                "total_cves": stats.get("points_count", 0),
                "collection": stats.get("collection_name", ""),
                "status": stats.get("status", "unknown")
            }
        except Exception as e:
            logger.error(f"Stats getirme hatası: {e}")
            return {
                "available": False,
                "error": str(e)
            }


# Global instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """
    Singleton RAG servis instance döner.
    
    Returns:
        RAGService instance
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("RAG Servis Test")
    print("=" * 50)
    
    service = get_rag_service()
    
    if service.is_available():
        print("✅ RAG servisi kullanılabilir")
        
        # Stats
        stats = service.get_stats()
        print(f"📊 İstatistikler: {stats}")
        
        # Test arama
        results = service.search_cve("SQL injection vulnerability", limit=3)
        print(f"\n🔍 Test Arama Sonuçları ({len(results)} CVE):")
        for r in results:
            print(f"  - {r.cve_id} ({r.severity}): Score={r.score:.4f}")
    else:
        print("❌ RAG servisi kullanılamıyor")
        print("  Qdrant'ın çalıştığından emin olun: docker-compose up -d")

