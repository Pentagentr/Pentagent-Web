"""
RAG Servis Modülü
CVE RAG sistemi ile entegrasyon için servis
Qdrant üzerinden CVE araması yapar
Gemini ile optimize query oluşturma
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import google.generativeai as genai
from config import config

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
        Gemini ile optimize query oluşturur.
        
        Args:
            scan_results: Tarama sonuçları (vulnerability bilgileri içeren)
            
        Returns:
            En alakalı CVE'lerin listesi
        """
        if not self.is_available():
            return []
        
        try:
            # Gemini ile optimize query oluştur
            query = self._generate_optimized_query_with_gemini(scan_results)
            
            if not query:
                # Fallback: basit query oluştur
                logger.warning("Gemini query oluşturamadı, basit query kullanılıyor")
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
    
    def _generate_optimized_query_with_gemini(self, scan_results: Dict[str, Any]) -> str:
        """
        Gemini ile optimize RAG query oluştur.
        Scan sonuçlarını analiz edip en iyi CVE arama sorgusunu üretir.
        
        Args:
            scan_results: Tarama sonuçları
            
        Returns:
            Optimize edilmiş RAG query string
        """
        try:
            # Gemini model başlat
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
            # Scan sonuçlarını özetle
            summary = self._summarize_scan_results(scan_results)
            
            # Gemini'ye prompt gönder
            prompt = f"""Based on the following penetration test results, generate an optimized search query for a CVE (Common Vulnerabilities and Exposures) database.

Scan Results:
{summary}

Requirements:
- Focus on the most critical vulnerabilities found
- Include specific technology/software names and versions if available
- Use terms that would match CVE descriptions
- Keep it concise (max 100 characters)
- Prioritize network-facing vulnerabilities

Generate ONLY the search query, nothing else. Example format: "Apache 2.4.49 path traversal remote code execution"

Search Query:"""
            
            # Gemini'den yanıt al
            response = model.generate_content(prompt)
            query = response.text.strip()
            
            # Query'yi temizle
            query = query.replace('"', '').replace("'", "").strip()
            
            logger.info(f"Gemini tarafından optimize edilmiş query: '{query}'")
            return query
            
        except Exception as e:
            logger.error(f"Gemini query oluşturma hatası: {e}")
            return ""
    
    def _summarize_scan_results(self, scan_results: Dict[str, Any]) -> str:
        """
        Scan sonuçlarını Gemini için özet haline getirir.
        
        Args:
            scan_results: Tarama sonuçları
            
        Returns:
            Özet string
        """
        summary_parts = []
        
        # Target
        target = scan_results.get("target", "")
        if target:
            summary_parts.append(f"Target: {target}")
        
        # Vulnerabilities
        vulnerabilities = scan_results.get("vulnerabilities", [])
        if vulnerabilities:
            vuln_list = [f"- {v.get('type', 'Unknown')}" for v in vulnerabilities[:5]]
            summary_parts.append(f"Vulnerabilities Found:\n" + "\n".join(vuln_list))
        
        # Technologies
        technologies = scan_results.get("technologies", [])
        if technologies:
            tech_list = ", ".join(technologies[:5])
            summary_parts.append(f"Technologies: {tech_list}")
        
        # Services
        services = scan_results.get("services", [])
        if services:
            service_list = [f"- {s.get('name', 'Unknown')} (Port {s.get('port', 'N/A')})" 
                          for s in services[:5]]
            summary_parts.append(f"Open Services:\n" + "\n".join(service_list))
        
        # Summary
        summary = scan_results.get("summary", "")
        if summary:
            summary_parts.append(f"Summary: {summary}")
        
        return "\n\n".join(summary_parts) if summary_parts else "No detailed information available"
    
    def _generate_query_from_scan(self, scan_results: Dict[str, Any]) -> str:
        """
        Basit query oluştur (Gemini fallback için).
        
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


# Production ready - test kodu yok
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("RAG Service Module - Production Ready")
    print("Use: from services.rag_service import get_rag_service")

