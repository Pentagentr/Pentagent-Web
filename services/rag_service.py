"""
RAG Servis Modülü
CVE RAG sistemi ile entegrasyon için servis
Qdrant üzerinden CVE araması yapar
LLM ile optimize query oluşturma
BAAI/bge-reranker-base ile sonuç reranking
"""

import logging
import sys
import os
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from model_wrapper import UnifiedLLM
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
    """CVE arama sonucu - Tüm detaylar"""
    cve_id: str
    score: float
    severity: Optional[str]
    base_score: Optional[float]
    attack_vector: Optional[str]
    description: str
    published_date: Optional[str]
    modified_date: Optional[str] = None
    references: Optional[List] = None
    cwe_id: Optional[str] = None
    vendor: Optional[str] = None
    product: Optional[str] = None
    cvss_vector: Optional[str] = None
    exploitability_score: Optional[float] = None
    impact_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict formatına dönüştür - Tüm detaylar"""
        return {
            "cve_id": self.cve_id,
            "score": self.score,
            "severity": self.severity,
            "base_score": self.base_score,
            "attack_vector": self.attack_vector,
            "description": self.description,
            "published_date": self.published_date,
            "modified_date": self.modified_date,
            "references": self.references or [],
            "cwe_id": self.cwe_id,
            "vendor": self.vendor,
            "product": self.product,
            "cvss_vector": self.cvss_vector,
            "exploitability_score": self.exploitability_score,
            "impact_score": self.impact_score
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
            qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
            
            # Port: HuggingFace Space için gereksiz, ignore et
            qdrant_port_str = os.getenv('QDRANT_PORT', '6333')
            if '.hf.space' in qdrant_host:
                qdrant_port = 443  # HuggingFace Space için HTTPS default port
                logger.info("🌐 HuggingFace Space detected - using default HTTPS port (443)")
            else:
                qdrant_port = int(qdrant_port_str)
            
            qdrant_api_key = os.getenv('QDRANT_API_KEY')
            hf_token = os.getenv('HUGGINGFACE_TOKEN')
            use_hf_api = os.getenv('USE_HF_INFERENCE_API', 'false').lower() == 'true'
            
            logger.info(f"🔧 Environment Config:")
            logger.info(f"  QDRANT_HOST: {qdrant_host}")
            logger.info(f"  QDRANT_PORT: {qdrant_port}")
            logger.info(f"  QDRANT_API_KEY: {'✅ Set' if qdrant_api_key else '❌ Not set'}")
            logger.info(f"  HUGGINGFACE_TOKEN: {'✅ Set' if hf_token else '❌ Not set'}")
            logger.info(f"  USE_HF_INFERENCE_API: {use_hf_api}")
            
            search_config = SearchConfig(
                qdrant_host=qdrant_host,
                qdrant_port=qdrant_port,
                qdrant_api_key=qdrant_api_key,
                huggingface_token=hf_token,
                timeout=30  # Startup için daha kısa timeout
            )
            
            # Cloud deployment için https kontrolü
            is_cloud = search_config.qdrant_api_key is not None or search_config.qdrant_host.startswith('http')
            if is_cloud:
                logger.info(f"Qdrant Cloud'a bağlanılıyor: {search_config.qdrant_host}")
            else:
                logger.info(f"Local Qdrant'a bağlanılıyor: {search_config.qdrant_host}:{search_config.qdrant_port}")
            
            # Retry mekanizması - 2 deneme (total: max 60 saniye)
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔄 RAG Engine başlatma denemesi {attempt + 1}/{max_retries}")
                    logger.info(f"  Qdrant Host: {search_config.qdrant_host}")
                    logger.info(f"  Qdrant Port: {search_config.qdrant_port}")
                    logger.info(f"  HF Token: {'✅ Var' if search_config.huggingface_token else '❌ Yok'}")
                    
                    self._engine = CVESearchEngine(search_config)
                    logger.info("✅ RAG Engine başarıyla oluşturuldu")
                    logger.info(f"✅ CVE koleksiyonu hazır: {search_config.collection_name}")
                    break
                except Exception as e:
                    logger.error(f"❌ Bağlantı denemesi {attempt + 1}/{max_retries} başarısız")
                    logger.error(f"   Hata: {str(e)}")
                    
                    if attempt < max_retries - 1:
                        logger.info("   ⏳ 3 saniye sonra tekrar denenecek...")
                        import time
                        time.sleep(3)
                    else:
                        logger.warning("⚠️ RAG servisi başlatılamadı (HuggingFace Space uyuyor olabilir)")
                        logger.warning("⚠️ İlk CVE arama isteğinde tekrar denenecek")
                        self._engine = None
                        self._available = False
                        return  # Exception raise etme, devam et
            
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
    
    async def _rerank_results(self, query: str, results: List[CVEResult]) -> List[CVEResult]:
        """
        HuggingFace BAAI/bge-reranker-base ile sonuçları yeniden sırala.
        
        Args:
            query: Orijinal arama sorgusu
            results: Qdrant'tan gelen ilk sonuçlar
            
        Returns:
            Rerank edilmiş CVE sonuçları
        """
        if not config.USE_RERANKER:
            logger.info("Reranker devre dışı, orijinal sıralama kullanılıyor")
            return results
        
        if not config.HUGGINGFACE_TOKEN:
            logger.warning("HuggingFace token yok, reranker atlanıyor")
            return results
        
        if not results or len(results) == 0:
            return results
        
        try:
            logger.info(f"🔄 Reranker başlatılıyor: {len(results)} sonuç sıralanacak")
            
            # HuggingFace Reranker API'ye istek hazırla
            headers = {
                "Authorization": f"Bearer {config.HUGGINGFACE_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Query ve documents hazırla
            # BAAI/bge-reranker formatı: source_sentence + sentences listesi
            documents = [f"{r.cve_id}: {r.description[:500]}" for r in results]
            
            payload = {
                "inputs": {
                    "source_sentence": query,
                    "sentences": documents
                }
            }
            
            # HuggingFace API'ye istek gönder
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config.RERANKER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Reranker API hatası: {response.status}")
                        logger.warning(f"API yanıtı: {error_text[:200]}")
                        return results
                    
                    rerank_scores = await response.json()
                    logger.info(f"Reranker yanıtı alındı: {type(rerank_scores)}")
                    
                    # Rerank skorlarını işle
                    if isinstance(rerank_scores, list):
                        # Sonuçları rerank skoruna göre sırala
                        reranked = []
                        for idx, score in enumerate(rerank_scores):
                            if idx < len(results):
                                # Orijinal CVE'yi kopyala ve rerank skorunu ekle
                                cve = results[idx]
                                # Score'u güncelle (rerank score daha önemli)
                                original_score = cve.score
                                rerank_score = score if isinstance(score, (int, float)) else score.get('score', 0)
                                
                                # Rerank score ile birleştir (ağırlıklı ortalama)
                                combined_score = (original_score * 0.3) + (rerank_score * 0.7)
                                
                                reranked.append({
                                    "cve": cve,
                                    "original_score": original_score,
                                    "rerank_score": rerank_score,
                                    "combined_score": combined_score
                                })
                        
                        # Combined score'a göre sırala
                        reranked.sort(key=lambda x: x['combined_score'], reverse=True)
                        
                        # Sadece CVE'leri döndür
                        reranked_cves = [item['cve'] for item in reranked]
                        
                        logger.info(f"✅ Reranking tamamlandı: {len(reranked_cves)} sonuç yeniden sıralandı")
                        
                        # Sıralama değişikliğini logla
                        for i, item in enumerate(reranked[:3], 1):
                            logger.info(f"  #{i}: {item['cve'].cve_id} (orijinal: {item['original_score']:.3f}, rerank: {item['rerank_score']:.3f}, combined: {item['combined_score']:.3f})")
                        
                        return reranked_cves
                    else:
                        logger.warning(f"Beklenmeyen reranker yanıtı: {type(rerank_scores)}")
                        return results
                        
        except asyncio.TimeoutError:
            logger.warning("Reranker timeout, orijinal sıralama kullanılıyor")
            return results
        except Exception as e:
            logger.error(f"Reranker hatası: {e}")
            logger.info("Reranker başarısız, orijinal sıralama kullanılıyor")
            return results
    
    def search_cve(
        self,
        query: str,
        limit: int = 5,
        severity: Optional[str] = None,
        use_reranker: Optional[bool] = None
    ) -> List[CVEResult]:
        """
        CVE araması yap ve reranker ile optimize et.
        
        Args:
            query: Arama sorgusu
            limit: Maksimum sonuç sayısı (default: 5)
            severity: Severity filtresi (CRITICAL, HIGH, MEDIUM, LOW)
            use_reranker: Reranker kullanılsın mı? (None: config'den al)
            
        Returns:
            Rerank edilmiş CVEResult listesi
        """
        # Lazy initialization: engine None ise tekrar başlat
        if self._engine is None and not self._available:
            logger.info("🔄 RAG Engine ilk kullanımda başlatılıyor...")
            self._initialize()
        
        if not self.is_available():
            logger.warning("RAG servisi kullanılamıyor")
            return []
        
        try:
            logger.info(f"CVE araması yapılıyor: '{query}' (limit={limit}, severity={severity})")
            
            # Reranker kullanılacaksa daha fazla sonuç al
            reranker_enabled = use_reranker if use_reranker is not None else config.USE_RERANKER
            fetch_limit = config.RERANKER_TOP_K if reranker_enabled else limit
            
            # Severity filtresi varsa
            if severity:
                results = self._engine.search_by_severity(
                    query=query,
                    severity=severity,
                    limit=fetch_limit
                )
            else:
                results = self._engine.search(query, limit=fetch_limit)
            
            # SearchResult'ları CVEResult'a dönüştür - TÜM DETAYLARLA
            cve_results = []
            for r in results:
                # Metadata'dan tüm bilgileri çıkar
                metadata = r.metadata or {}
                cve_results.append(CVEResult(
                    cve_id=r.cve_id,
                    score=r.score,
                    severity=r.severity,
                    base_score=r.base_score,
                    attack_vector=r.attack_vector,
                    description=r.description,
                    published_date=r.published_date,
                    modified_date=metadata.get('modified_date'),
                    references=metadata.get('references', []),
                    cwe_id=metadata.get('cwe_id'),
                    vendor=metadata.get('vendor'),
                    product=metadata.get('product'),
                    cvss_vector=metadata.get('cvss_vector'),
                    exploitability_score=metadata.get('exploitability_score'),
                    impact_score=metadata.get('impact_score')
                ))
            
            logger.info(f"✅ {len(cve_results)} CVE bulundu (vektör araması)")
            
            # Reranker ile optimize et
            if reranker_enabled and len(cve_results) > 1:
                logger.info(f"🔄 Reranker başlatılıyor ({len(cve_results)} sonuç)...")
                
                # Async reranker'ı sync context'te çalıştır
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Event loop zaten çalışıyorsa thread pool kullan
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            reranked_results = pool.submit(
                                asyncio.run, 
                                self._rerank_results(query, cve_results)
                            ).result(timeout=30)
                    else:
                        # Event loop çalışmıyorsa direkt çalıştır
                        reranked_results = loop.run_until_complete(
                            self._rerank_results(query, cve_results)
                        )
                    
                    # Limit'e göre kes
                    reranked_results = reranked_results[:limit]
                    logger.info(f"✅ Reranking tamamlandı, en iyi {len(reranked_results)} sonuç döndürülüyor")
                    return reranked_results
                    
                except Exception as e:
                    logger.error(f"Reranker çalıştırma hatası: {e}")
                    logger.info("Reranker başarısız, orijinal sonuçlar döndürülüyor")
                    return cve_results[:limit]
            else:
                # Reranker kullanılmıyor, direkt döndür
                return cve_results[:limit]
            
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
        # Lazy initialization
        if self._engine is None and not self._available:
            logger.info("🔄 RAG Engine ilk kullanımda başlatılıyor...")
            self._initialize()
        
        if not self.is_available():
            return None
        
        try:
            result = self._engine.get_cve_by_id(cve_id)
            if result:
                metadata = result.metadata or {}
                return CVEResult(
                    cve_id=result.cve_id,
                    score=result.score,
                    severity=result.severity,
                    base_score=result.base_score,
                    attack_vector=result.attack_vector,
                    description=result.description,
                    published_date=result.published_date,
                    modified_date=metadata.get('modified_date'),
                    references=metadata.get('references', []),
                    cwe_id=metadata.get('cwe_id'),
                    vendor=metadata.get('vendor'),
                    product=metadata.get('product'),
                    cvss_vector=metadata.get('cvss_vector'),
                    exploitability_score=metadata.get('exploitability_score'),
                    impact_score=metadata.get('impact_score')
                )
            return None
            
        except Exception as e:
            logger.error(f"CVE getirme hatası ({cve_id}): {e}")
            return None
    
    def analyze_scan_results(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tarama sonuçlarını analiz edip ilgili CVE'leri bul.
        Gemini ile optimize query oluşturur.
        
        Args:
            scan_results: Tarama sonuçları (vulnerability bilgileri içeren)
            
        Returns:
            Dict: {
                'results': List[CVEResult],
                'query': str,  # LLM'in ürettiği query
                'summary': str  # Scan özeti
            }
        """
        # Lazy initialization
        if self._engine is None and not self._available:
            logger.info("🔄 RAG Engine ilk kullanımda başlatılıyor...")
            self._initialize()
        
        if not self.is_available():
            return {'results': [], 'query': '', 'summary': ''}
        
        try:
            # LLM ile optimize query oluştur
            query = self._generate_optimized_query_with_llm(scan_results)
            summary = self._summarize_scan_results(scan_results)
            
            if not query:
                # Fallback: basit query oluştur
                logger.warning("LLM query oluşturamadı, basit query kullanılıyor")
                query = self._generate_query_from_scan(scan_results)
            
            if not query:
                logger.warning("Scan sonuçlarından query oluşturulamadı")
                return {'results': [], 'query': '', 'summary': summary}
            
            logger.info(f"Scan analizi için oluşturulan query: '{query}'")
            
            # CVE araması yap
            results = self.search_cve(query, limit=5)
            
            return {
                'results': results,
                'query': query,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Scan analizi hatası: {e}")
            return {'results': [], 'query': '', 'summary': ''}
    
    def _generate_optimized_query_with_llm(self, scan_results: Dict[str, Any]) -> str:
        """
        LLM ile optimize RAG query oluştur.
        Scan sonuçlarını analiz edip en iyi CVE arama sorgusunu üretir.
        """
        try:
            # Unified LLM (Groq default)
            model = UnifiedLLM()
            
            # Scan sonuçlarını özetle
            summary = self._summarize_scan_results(scan_results)
            
            # LLM'ye prompt gönder - KISA (token tasarrufu)
            prompt = f"""Penetration test sonuçları için CVE database query oluştur.

Scan Sonuçları:
{summary[:500]}

Query kuralları:
- En kritik zafiyet odaklı
- Teknoloji/versiyon ekle
- Max 100 karakter
- SADECE query döndür

Query:"""
            
            # Yanıt al - Event loop sorunu çözümü
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Event loop zaten çalışıyor - thread pool kullan
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        response = pool.submit(
                            asyncio.run,
                            model.generate_content_async(prompt)
                        ).result(timeout=30)
                else:
                    # Event loop çalışmıyor - direkt çalıştır
                    response = loop.run_until_complete(
                        model.generate_content_async(prompt)
                    )
            except RuntimeError as e:
                # Event loop hatasını yakala
                logger.warning(f"Event loop hatası: {e}, basit query kullanılıyor")
                return self._generate_query_from_scan(scan_results)
            
            # Response string veya object olabilir
            if isinstance(response, str):
                query = response.strip()
            elif hasattr(response, 'text'):
                query = response.text.strip()
            elif hasattr(response, 'get'):
                query = response.get('text', '').strip()
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                query = str(response).strip()
            
            # Query'yi temizle
            query = query.replace('"', '').replace("'", "").strip()
            
            logger.info(f"✅ LLM optimize query: '{query}'")
            return query
            
        except Exception as e:
            logger.error(f"LLM query oluşturma hatası: {e}")
            return ""
    
    def _summarize_scan_results(self, scan_results: Dict[str, Any]) -> str:
        """Scan sonuçlarını LLM için özet haline getirir - GERÇEK SCAN FORMATI."""
        summary_parts = []
        
        # Scan sonuçları genellikle tool_name: {result} formatında geliyor
        # Örnek: {"ssl_scan": {...}, "subdomain_enum": {...}, "port_scan": {...}}
        
        # Target
        target = scan_results.get("target", "")
        if target:
            summary_parts.append(f"Target: {target}")
        
        # Her tool sonucunu analiz et
        for tool_name, tool_result in scan_results.items():
            if tool_name == "target" or not isinstance(tool_result, dict):
                continue
                
            # Vulnerability/findings anahtarlarını ara
            findings = None
            if isinstance(tool_result, dict):
                findings = tool_result.get("vulnerabilities") or tool_result.get("findings") or tool_result.get("results")
            
            if findings and isinstance(findings, (list, dict)):
                if isinstance(findings, dict):
                    # Dict formatındaki findings'i listeye çevir
                    findings_text = f"{tool_name}: " + ", ".join([f"{k}={v}" for k, v in list(findings.items())[:3]])
                    summary_parts.append(findings_text)
                else:
                    # List formatındaki findings
                    findings_text = f"{tool_name}: " + ", ".join([str(f) for f in findings[:3]])
                    summary_parts.append(findings_text)
            elif tool_result:
                # Genel tool sonucu
                result_str = str(tool_result)[:100]  # İlk 100 karakter
                summary_parts.append(f"{tool_name}: {result_str}")
        
        # Technologies - tool sonuçlarından çıkar
        tech_result = scan_results.get("enum_tech_detector") or scan_results.get("tech_detection")
        if tech_result and isinstance(tech_result, dict):
            technologies = tech_result.get("technologies") or tech_result.get("detected_technologies")
            if technologies:
                if isinstance(technologies, list):
                    tech_list = ", ".join([str(t) for t in technologies[:3]])
                else:
                    tech_list = str(technologies)[:100]
                summary_parts.append(f"Technologies: {tech_list}")
        
        # Port scan sonuçları
        port_result = scan_results.get("port_scan") or scan_results.get("recon_port_scanner")
        if port_result and isinstance(port_result, dict):
            open_ports = port_result.get("open_ports") or port_result.get("ports")
            if open_ports:
                ports_str = str(open_ports)[:100]
                summary_parts.append(f"Open Ports: {ports_str}")
        
        result = "\n".join(summary_parts) if summary_parts else "No detailed scan results available"
        logger.info(f"📋 Scan Summary: {result[:200]}...")
        return result
    
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

