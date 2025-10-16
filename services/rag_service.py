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
from datetime import datetime
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
    
    def get(self, key: str, default=None):
        """Dict-like get method for compatibility"""
        return getattr(self, key, default)
    
    def __iter__(self):
        """Iterate over key-value pairs for JSON serialization"""
        return iter(self.to_dict().items())
    
    def keys(self):
        """Return keys for JSON serialization"""
        return self.to_dict().keys()
    
    def values(self):
        """Return values for JSON serialization"""
        return self.to_dict().values()


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
        403 hatası durumunda FALLBACK: Metin benzerliği ile sıralama
        
        Args:
            query: Orijinal arama sorgusu
            results: Qdrant'tan gelen ilk sonuçlar (sparse+dense birleşik)
            
        Returns:
            Rerank edilmiş CVE sonuçları
        """
        if not config.USE_RERANKER:
            logger.info("Reranker devre dışı, orijinal sıralama kullanılıyor")
            return results
        
        if not results or len(results) == 0:
            return results
        
        # HuggingFace token kontrolü - ZORUNLU
        if not config.HUGGINGFACE_TOKEN:
            logger.error("❌ HuggingFace token YOK! Reranker kullanılamıyor.")
            logger.warning("⚠️ Reranker olmadan orijinal sıralama kullanılıyor")
            return results
        
        try:
            logger.info(f"🔄 Reranker başlatılıyor: {len(results)} sonuç sıralanacak")
            
            # Query ve documents hazırla
            documents = [f"{r.cve_id}: {r.description[:500]}" for r in results]
            
            # SENTENCE-TRANSFORMERS RERANKER kullan (cross-encoder)
            # BAAI/bge-reranker-base yerine daha stabil bir model: cross-encoder/ms-marco-MiniLM-L-6-v2
            reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            inference_url = f"https://api-inference.huggingface.co/models/{reranker_model}"
            
            # Token kontrolü
            if not config.HUGGINGFACE_TOKEN:
                logger.error("❌ HUGGINGFACE_TOKEN environment variable tanımlı değil!")
                logger.error("💡 Render.com'da Environment Variables bölümünden HUGGINGFACE_TOKEN ekleyin")
                raise Exception("HUGGINGFACE_TOKEN tanımlı değil")
            
            logger.info(f"🔑 HuggingFace Token: {config.HUGGINGFACE_TOKEN[:10]}... (ilk 10 karakter)")
            
            headers = {
                "Authorization": f"Bearer {config.HUGGINGFACE_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Cross-encoder formatı: {"inputs": [["query", "doc1"], ["query", "doc2"], ...]}
            # Her query-document çifti için skor döndürür
            pairs = [[query, doc] for doc in documents]
            
            payload = {
                "inputs": pairs,
                "options": {
                    "wait_for_model": True
                }
            }
            
            # HuggingFace API'ye istek gönder
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    inference_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 403:
                        error_text = await response.text()
                        logger.error(f"❌ RERANKER API 403 (YETKİ HATASI): {error_text[:300]}")
                        logger.error("💡 Çözüm: HuggingFace token'ınızın 'Inference API' yetkisi olmalı")
                        raise Exception(f"Reranker API yetki hatası (403): {error_text[:100]}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Reranker API hatası: {response.status}")
                        logger.error(f"API yanıtı: {error_text[:300]}")
                        raise Exception(f"Reranker API başarısız ({response.status}): {error_text[:100]}")
                    
                    rerank_scores = await response.json()
                    logger.info(f"✅ Reranker yanıtı alındı: {type(rerank_scores)}")
                    
                    # Cross-encoder array of floats döndürür: [0.85, 0.72, 0.91, ...]
                    if isinstance(rerank_scores, list) and len(rerank_scores) == len(results):
                        # Sonuçları rerank skoruna göre sırala
                        reranked = []
                        for idx, score in enumerate(rerank_scores):
                            cve = results[idx]
                            original_score = cve.score
                            
                            # Rerank score normalize et (0-1 arası)
                            rerank_score = float(score) if isinstance(score, (int, float)) else 0.5
                            
                            # Rerank score DOMİNANT olmalı (sen fallback istemiyorsun!)
                            # %80 rerank, %20 orijinal skor
                            combined_score = (original_score * 0.2) + (rerank_score * 0.8)
                            
                            reranked.append({
                                "cve": cve,
                                "original_score": original_score,
                                "rerank_score": rerank_score,
                                "combined_score": combined_score
                            })
                        
                        # Combined score'a göre sırala (EN YÜKSEK ÖNCE)
                        reranked.sort(key=lambda x: x['combined_score'], reverse=True)
                        
                        # Sadece CVE'leri döndür
                        reranked_cves = [item['cve'] for item in reranked]
                        
                        logger.info(f"✅ RERANKING TAMAMLANDI: {len(reranked_cves)} sonuç")
                        
                        # Top 3'ü logla
                        for i, item in enumerate(reranked[:3], 1):
                            logger.info(f"  🏆 #{i}: {item['cve'].cve_id} | Rerank: {item['rerank_score']:.3f} | Combined: {item['combined_score']:.3f}")
                        
                        return reranked_cves
                    else:
                        logger.error(f"❌ Beklenmeyen reranker yanıtı: {type(rerank_scores)}, len: {len(rerank_scores) if isinstance(rerank_scores, list) else 'N/A'}")
                        raise Exception("Reranker yanıtı işlenemedi")
                        
        except asyncio.TimeoutError:
            logger.error("❌ Reranker TIMEOUT (30s)")
            logger.warning("⚠️ Orijinal sıralama kullanılıyor")
            return results
        except Exception as e:
            logger.error(f"❌ RERANKER BAŞARISIZ: {e}")
            logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
            return results
    
    async def search(self, query: str, limit: int = 5, severity: Optional[str] = None) -> List[CVEResult]:
        """
        Async search metodu - web_api.py için.
        Reranker MUTLAKA aktif.
        """
        return self.search_cve(query, limit, severity, use_reranker=True)
    
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
            use_reranker: Reranker kullanılsın mı? (None: ZORUNLU True)
            
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
            
            # Reranker MUTLAKA aktif - HuggingFace token kontrolü
            reranker_enabled = True if use_reranker is None else use_reranker
            
            # HuggingFace token kontrolü - yetki yoksa uyarı ver ama devam et
            if reranker_enabled and not self._has_valid_hf_token():
                logger.error("❌ HUGGINGFACE TOKEN YETKİSİ YOK!")
                logger.error("💡 Çözüm: HuggingFace hesabınızda 'Inference API' yetkisi olmalı")
                logger.error("🔗 https://huggingface.co/settings/tokens adresinden token oluşturun")
                # Reranker'ı devre dışı bırakma, sadece uyarı ver
            # 20 sparse vektör için fetch_limit = 20
            fetch_limit = 20 if reranker_enabled else limit
            if reranker_enabled:
                logger.info(f"🎯 Reranker aktif - {fetch_limit} sonuç çekilecek, reranking sonrası {limit} döndürülecek")
            else:
                logger.info(f"🎯 Reranker devre dışı - {limit} sonuç döndürülecek")
            
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
    
    async def generate_optimized_query(self, scan_results: Dict[str, Any]) -> str:
        """Public metod - LLM ile optimize RAG query oluştur"""
        return self._generate_optimized_query_with_llm(scan_results)
    
    def _generate_optimized_query_with_llm(self, scan_results: Dict[str, Any]) -> str:
        """
        LLM ile optimize RAG query oluştur - TÜM TOOL ÇIKTILARI İLE.
        Scan sonuçlarını analiz edip en iyi CVE arama sorgusunu üretir.
        """
        try:
            # Unified LLM (Groq default)
            model = UnifiedLLM()
            
            # TÜM TOOL ÇIKTILARINI HAZIRLA - JSON FORMATINDA
            all_tool_outputs = self._prepare_all_tool_outputs_for_ai(scan_results)
            
            if not all_tool_outputs or all_tool_outputs == "No tool outputs":
                logger.warning("⚠️ Hiç tool çıktısı yok, generic query kullanılıyor")
                return "web application security vulnerability exploitation"
            
            # LLM'ye TÜM TOOL ÇIKTILARINI ver - KRİTİK: JSON FORMATINDA
            prompt = f"""Sen bir pentest uzmanısın. Aşağıdaki JSON formatındaki TÜM TOOL ÇIKTILARINI analiz et ve CVE database query oluştur.

📊 TÜM TOOL ÇIKTILARI:
{all_tool_outputs[:2000]}

🎯 QUERY KURALLARI:
- JSON'daki TÜM tool çıktılarına odaklan (tool_name, data, findings, vulnerabilities)
- Teknoloji adı ve versiyonu varsa ekle (örn: WordPress 5.0, Apache 2.4.49)
- Web teknolojileri tespit edilmişse: "web application vulnerability [technology]"
- API endpoint'ler varsa: "API security vulnerability [technology]"
- Form/parametre varsa: "web application input validation vulnerability [technology]"
- Admin panel varsa: "admin panel vulnerability [technology]"
- Missing headers varsa: "security headers vulnerability [technology]"
- Port taraması varsa: "network service vulnerability [service]"
- Directory bruteforce varsa: "directory traversal vulnerability"
- Max 120 karakter, ÖZLÜ ve SPESİFİK
- SADECE query string döndür, açıklama YAPMA

💡 ÖRNEK QUERY'LER:
- "WordPress 5.0 vulnerability CVE"
- "Apache 2.4.49 path traversal CVE"
- "web application SQL injection vulnerability"
- "API security authentication bypass CVE"
- "admin panel vulnerability CVE"
- "security headers vulnerability CVE"
- "network service vulnerability SSH"

🔍 ANALİZ ET:
1. Hangi teknolojiler tespit edildi?
2. Hangi güvenlik açıkları bulundu?
3. Hangi tool'lar çalıştırıldı?
4. En kritik bulgu nedir?
5. Hangi servisler açık?

CVE Query:"""
            
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
            if query and len(query) > 10:
                # JSON formatından çıkar
                if query.startswith('"') and query.endswith('"'):
                    query = query[1:-1]
                
                logger.info(f"✅ LLM query oluşturuldu: '{query}'")
                return query
            else:
                logger.warning("LLM boş veya kısa query döndürdü")
                return self._generate_query_from_scan(scan_results)
            
        except Exception as e:
            logger.error(f"LLM query oluşturma hatası: {e}")
            return ""
    
    def _prepare_all_tool_outputs_for_ai(self, scan_results: Dict[str, Any]) -> str:
        """
        TÜM TOOL ÇIKTILARINI AI'ya vermek için hazırla - JSON FORMATINDA.
        """
        try:
            import json
            
            # Tool çıktılarını topla
            tool_outputs = []
            target = scan_results.get("target", "target")
            
            # Scan results'tan tool çıktılarını çıkar
            for key, value in scan_results.items():
                if key.startswith("tool_") and isinstance(value, dict):
                    tool_name = key[5:]  # "tool_" prefix'ini kaldır
                    
                    tool_output = {
                        "tool_name": tool_name,
                        "target": target,
                        "data": value,
                        "data_keys": list(value.keys()) if isinstance(value, dict) else [],
                        "data_size": len(value) if isinstance(value, dict) else 0
                    }
                    tool_outputs.append(tool_output)
            
            # Context summary'den de tool bilgilerini ekle
            if "context_summary" in scan_results:
                context = scan_results["context_summary"]
                for key, value in context.items():
                    if key.startswith("tool_") and isinstance(value, dict):
                        tool_name = key[5:]
                        
                        tool_output = {
                            "tool_name": tool_name,
                            "target": target,
                            "data": value,
                            "data_keys": list(value.keys()) if isinstance(value, dict) else [],
                            "data_size": len(value) if isinstance(value, dict) else 0
                        }
                        tool_outputs.append(tool_output)
            
            # Execution summary'den tool bilgilerini ekle
            if "execution_summary" in scan_results:
                exec_summary = scan_results["execution_summary"]
                tool_outputs.append({
                    "execution_info": exec_summary,
                    "tools_executed": exec_summary.get("tools_executed", []),
                    "successful_tools": exec_summary.get("successful_tools", [])
                })
            
            # Bulguları da ekle
            if "findings" in scan_results and scan_results["findings"]:
                tool_outputs.append({
                    "findings": scan_results["findings"],
                    "findings_count": len(scan_results["findings"])
                })
            
            # JSON formatında döndür
            if tool_outputs:
                logger.info(f"📊 {len(tool_outputs)} tool çıktısı AI'ya hazırlandı")
                return json.dumps(tool_outputs, indent=2, ensure_ascii=False)
            else:
                logger.warning("⚠️ Hiç tool çıktısı bulunamadı")
                return "No tool outputs"
                
        except Exception as e:
            logger.error(f"Tool outputs hazırlama hatası: {e}")
            return "No tool outputs"
    
    def _prepare_json_findings_for_ai(self, scan_results: Dict[str, Any]) -> str:
        """
        JSON bulgularını AI'ya vermek için hazırla - GELİŞTİRİLMİŞ ANALİZ + TOOL ÇIKTILARI.
        """
        try:
            import json
            
            # Eğer scan_results'da zaten findings array'i varsa onu kullan
            if "findings" in scan_results and scan_results["findings"]:
                findings = scan_results["findings"]
                logger.info(f"📊 Mevcut {len(findings)} bulgu kullanılıyor")
                
                # Bulguları zenginleştir - context_summary ve execution_summary ekle
                enriched_findings = []
                for finding in findings:
                    enriched_finding = finding.copy()
                    
                    # Context summary'den ek bilgi ekle
                    if "context_summary" in scan_results:
                        context = scan_results["context_summary"]
                        if "technologies" in context:
                            enriched_finding["detected_technologies"] = context["technologies"]
                        if "open_ports" in context:
                            enriched_finding["open_ports"] = context["open_ports"]
                        if "parameters" in context:
                            enriched_finding["discovered_parameters"] = context["parameters"]
                    
                    # Execution summary'den ek bilgi ekle
                    if "execution_summary" in scan_results:
                        exec_summary = scan_results["execution_summary"]
                        enriched_finding["tools_executed"] = exec_summary.get("tools_executed", [])
                        enriched_finding["successful_tools"] = exec_summary.get("successful_tools", [])
                    
                    enriched_findings.append(enriched_finding)
                
                return json.dumps(enriched_findings, indent=2, ensure_ascii=False)
            
            # Tool sonuçlarından bulguları çıkar - GELİŞTİRİLMİŞ
            findings = []
            target = scan_results.get("target", "target")
            
            # Tool sonuçlarında bulguları ara
            for tool_name, tool_result in scan_results.items():
                if not isinstance(tool_result, dict):
                    continue
                
                # Tool_ prefix'li sonuçları da işle
                if tool_name.startswith("tool_"):
                    tool_name = tool_name[5:]  # "tool_" prefix'ini kaldır
                
                # Web crawler bulguları - DETAYLI ANALİZ
                if "web_crawler" in tool_name.lower():
                    forms = tool_result.get("forms", [])
                    endpoints = tool_result.get("endpoints", [])
                    parameters = tool_result.get("parameters", [])
                    pages = tool_result.get("pages", [])
                    technologies = tool_result.get("technologies", [])
                    
                    # Teknoloji tespiti varsa ayrı bulgu ekle
                    if technologies:
                        tech_str = ", ".join(technologies[:5])  # İlk 5 teknoloji
                        findings.append({
                            "title": f"Web Technologies Detected: {tech_str}",
                            "severity": "medium",
                            "description": f"Web uygulamasında {len(technologies)} teknoloji tespit edildi: {tech_str}",
                            "technology": tech_str,
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Technologies: {tech_str}"
                        })
                    
                    # Form ve parametre bulguları
                    if forms or parameters:
                        form_count = len(forms)
                        param_count = len(parameters)
                        param_list = ", ".join(parameters[:10])  # İlk 10 parametre
                        
                        findings.append({
                            "title": "Interactive Web Elements Discovered",
                            "severity": "medium", 
                            "description": f"Web uygulamasında {form_count} form ve {param_count} parametre tespit edildi. Parametreler: {param_list}",
                            "technology": "Web Application",
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Forms: {form_count}, Parameters: {param_list}"
                        })
                    
                    # Endpoint bulguları
                    if endpoints:
                        endpoint_list = ", ".join(endpoints[:10])  # İlk 10 endpoint
                        findings.append({
                            "title": f"API Endpoints Discovered ({len(endpoints)} total)",
                            "severity": "medium",
                            "description": f"Web uygulamasında {len(endpoints)} API endpoint tespit edildi: {endpoint_list}",
                            "technology": "Web API",
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Endpoints: {endpoint_list}"
                        })
                
                # Admin panel bulguları
                elif "exposed_panels" in tool_name.lower() or "infra" in tool_name.lower():
                    panels = tool_result.get("discovered_panels", [])
                    if panels:
                        findings.append({
                            "title": "Exposed Admin Panels",
                            "severity": "high",
                            "description": f"{len(panels)} admin panel ve management interface keşfedildi",
                            "technology": "Infrastructure",
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Panels: {panels[:5]}"
                        })
                
                # Teknoloji tespiti bulguları
                elif "technologies" in tool_name.lower():
                    technologies = tool_result if isinstance(tool_result, list) else tool_result.get("technologies", [])
                    if technologies:
                        tech_str = ", ".join(technologies[:5])
                        findings.append({
                            "title": f"Technology Stack Detected: {tech_str}",
                            "severity": "medium",
                            "description": f"Web uygulamasında {len(technologies)} teknoloji tespit edildi: {tech_str}",
                            "technology": tech_str,
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Technologies: {tech_str}"
                        })
                
                # Missing headers
                elif "header" in tool_name.lower():
                    missing_headers = tool_result.get("missing_security_headers", [])
                    if missing_headers:
                        findings.append({
                            "title": "Missing Security Headers",
                            "severity": "medium",
                            "description": f"Eksik güvenlik header'ları: {', '.join(missing_headers)}",
                            "technology": "HTTP",
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Missing headers: {missing_headers}"
                        })
                
                # Port scanner bulguları
                elif "port" in tool_name.lower():
                    open_ports = tool_result.get("open_ports", [])
                    services = tool_result.get("services", [])
                    if open_ports:
                        findings.append({
                            "title": f"Open Ports Discovered ({len(open_ports)} total)",
                            "severity": "medium",
                            "description": f"Hedefte {len(open_ports)} açık port tespit edildi: {', '.join(map(str, open_ports[:10]))}",
                            "technology": "Network",
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Open ports: {open_ports[:10]}"
                        })
                
                # Vulnerability test bulguları
                elif any(vuln_type in tool_name.lower() for vuln_type in ["xss", "sqli", "lfi", "verify"]):
                    vulnerabilities = tool_result.get("vulnerabilities", [])
                    findings_data = tool_result.get("findings", [])
                    if vulnerabilities or findings_data:
                        vuln_count = len(vulnerabilities) + len(findings_data)
                        findings.append({
                            "title": f"Security Vulnerabilities Detected ({vuln_count} total)",
                            "severity": "high",
                            "description": f"{tool_name} ile {vuln_count} güvenlik açığı tespit edildi",
                            "technology": "Web Application",
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Vulnerabilities: {vuln_count} found"
                        })
                
                # GENEL TOOL ÇIKTI - TÜM TOOL'LAR İÇİN
                else:
                    # Diğer tool'lar için genel bulgu oluştur
                    if tool_result and isinstance(tool_result, dict) and len(tool_result) > 0:
                        data_keys = list(tool_result.keys())
                        findings.append({
                            "title": f"{tool_name} Tool Results",
                            "severity": "info",
                            "description": f"{tool_name} tool'u çalıştırıldı ve {len(data_keys)} veri noktası toplandı",
                            "technology": "Tool Output",
                            "target": target,
                            "tool_source": tool_name,
                            "evidence": f"Data keys: {data_keys[:5]}"
                        })
            
            # Bulguları JSON'a çevir
            if findings:
                logger.info(f"📊 {len(findings)} bulgu JSON'a çevrildi")
                return json.dumps(findings, indent=2, ensure_ascii=False)
            else:
                logger.warning("⚠️ Hiç bulgu bulunamadı")
                return "No findings"
                
        except Exception as e:
            logger.error(f"JSON findings hazırlama hatası: {e}")
            return "No findings"
    
    def _extract_security_findings(self, scan_results: Dict[str, Any]) -> str:
        """
        Scan sonuçlarından SPESİFİK GÜVENLİK BULGULARINI çıkar - CVE query için.
        Tool bulgularına dayalı spesifik query oluşturur.
        """
        security_findings = []
        target = scan_results.get("target", "target")
        
        # 1. Tool sonuçlarında SPESİFİK bulguları ara
        for tool_name, tool_result in scan_results.items():
            if not isinstance(tool_result, dict):
                continue
            
            # a) Web crawler - Form ve endpoint bulguları
            if "web_crawler" in tool_name.lower():
                forms = tool_result.get("forms", [])
                endpoints = tool_result.get("endpoints", [])
                parameters = tool_result.get("parameters", [])
                
                if forms:
                    security_findings.append(f"{target} web application login forms vulnerability")
                if endpoints:
                    login_endpoints = [ep for ep in endpoints if any(word in ep.lower() for word in ['login', 'auth', 'signin'])]
                    if login_endpoints:
                        security_findings.append(f"{target} authentication endpoint security vulnerability")
                if parameters:
                    sensitive_params = [p for p in parameters if any(word in p.lower() for word in ['user', 'pass', 'id', 'token', 'key'])]
                    if sensitive_params:
                        security_findings.append(f"{target} parameter injection vulnerability")
            
            # b) Admin panel discovery
            elif "exposed_panels" in tool_name.lower() or "infra" in tool_name.lower():
                panels = tool_result.get("discovered_panels", [])
                if panels:
                    for panel in panels[:2]:
                        if "phpmyadmin" in panel.lower():
                            security_findings.append(f"{target} phpMyAdmin exposed panel vulnerability")
                        elif "cpanel" in panel.lower():
                            security_findings.append(f"{target} cPanel exposed management interface")
                        elif "jenkins" in panel.lower():
                            security_findings.append(f"{target} Jenkins CI/CD exposed vulnerability")
                        elif "admin" in panel.lower():
                            security_findings.append(f"{target} admin panel exposed authentication bypass")
            
            # c) API endpoint discovery
            elif "api" in tool_name.lower():
                api_endpoints = tool_result.get("api_endpoints", [])
                if api_endpoints:
                    security_findings.append(f"{target} API endpoint security vulnerability")
            
            # d) Directory bruteforce - Sensitive directories
            elif "directory" in tool_name.lower():
                directories = tool_result.get("directories", [])
                sensitive_dirs = []
                for dir_path in directories:
                    if any(word in dir_path.lower() for word in ['admin', 'backup', 'config', 'logs', 'test', 'dev']):
                        sensitive_dirs.append(dir_path)
                if sensitive_dirs:
                    security_findings.append(f"{target} sensitive directory exposure vulnerability")
            
            # e) Missing security headers
            elif "header" in tool_name.lower():
                missing_headers = tool_result.get("missing_security_headers", [])
                if missing_headers:
                    if "X-Frame-Options" in missing_headers:
                        security_findings.append(f"{target} clickjacking vulnerability missing X-Frame-Options")
                    if "X-XSS-Protection" in missing_headers:
                        security_findings.append(f"{target} XSS protection vulnerability")
                    if "Content-Security-Policy" in missing_headers:
                        security_findings.append(f"{target} CSP injection vulnerability")
            
            # f) Technology detection - Versiyon bilgisi varsa CVE için önemli
            elif "tech" in tool_name.lower():
                technologies = tool_result.get("technologies", []) or tool_result.get("detected_technologies", [])
                if technologies and isinstance(technologies, list):
                    for tech in technologies[:2]:
                        if isinstance(tech, dict):
                            tech_name = tech.get("name", "") or tech.get("technology", "")
                            version = tech.get("version", "")
                            if tech_name and version and version != "N/A":
                                security_findings.append(f"{target} {tech_name} {version} vulnerability")
            
            # g) Vulnerability scanners
            elif any(vuln_tool in tool_name.lower() for vuln_tool in ["verify_xss", "verify_sqli", "verify_lfi"]):
                vulnerabilities = tool_result.get("vulnerabilities", [])
                if vulnerabilities:
                    for vuln in vulnerabilities[:2]:
                        vuln_type = vuln.get("type", "").lower()
                        if "xss" in vuln_type:
                            security_findings.append(f"{target} cross-site scripting XSS vulnerability")
                        elif "sql" in vuln_type:
                            security_findings.append(f"{target} SQL injection vulnerability")
                        elif "lfi" in vuln_type:
                            security_findings.append(f"{target} local file inclusion vulnerability")
        
        # 2. Context'ten spesifik bulguları çıkar
        context = scan_results.get("context_summary", {})
        if isinstance(context, dict):
            # Forms bulundu mu?
            forms = context.get("forms", [])
            if forms:
                security_findings.append(f"{target} web application form vulnerability")
            
            # Parameters bulundu mu?
            parameters = context.get("parameters", [])
            if parameters:
                security_findings.append(f"{target} parameter manipulation vulnerability")
        
        # Sonuç - spesifik vulnerability queries
        if security_findings:
            # En spesifik 3 bulguyu al ve birleştir
            return " ".join(security_findings[:3])
        else:
            return f"{target} web application security vulnerability"
    
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
    
    def store_scan_results(self, target: str, findings: List[Dict[str, Any]], execution_results: Dict[str, Any]):
        """
        Tarama sonuçlarını RAG'a kaydet - Firebase entegrasyonu ile.
        
        Args:
            target: Hedef sistem
            findings: Bulgular listesi
            execution_results: Tool execution sonuçları
        """
        try:
            if not self.is_available():
                logger.warning("RAG servisi kullanılamıyor - scan results kaydedilemiyor")
                return False
            
            # Tarama sonuçlarını RAG formatına çevir
            scan_data = {
                "target": target,
                "scan_date": datetime.now().isoformat(),
                "findings": findings,
                "execution_summary": {
                    "total_tools_executed": len(execution_results),
                    "successful_tools": len([r for r in execution_results.values() if r.get("success", False)]),
                    "risk_level": self._calculate_overall_risk_level(findings)
                },
                "metadata": {
                    "scan_type": "comprehensive",
                    "methodology": "OWASP Top 10, PTES, NIST SP 800-115"
                }
            }
            
            # Firebase'e kaydet (mevcut Firebase bağlantısı kullan)
            try:
                from config import firebase_db
                if firebase_db:
                    scan_ref = firebase_db.collection('scan_results').document()
                    scan_ref.set(scan_data)
                    logger.info(f"✅ Scan results Firebase'e kaydedildi: {target}")
            except Exception as e:
                logger.error(f"Firebase kayıt hatası: {e}")
            
            # RAG engine'e de kaydet (opsiyonel)
            try:
                if hasattr(self._engine, 'store_document'):
                    self._engine.store_document(scan_data)
                    logger.info(f"✅ Scan results RAG'a kaydedildi: {target}")
            except Exception as e:
                logger.warning(f"RAG engine kayıt hatası: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store scan results: {e}")
            return False
    
    def _calculate_overall_risk_level(self, findings: List[Dict[str, Any]]) -> str:
        """Bulgulara göre genel risk seviyesini hesapla"""
        if not findings:
            return "LOW"
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in findings:
            severity = finding.get("severity", "low").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        if severity_counts["critical"] > 0:
            return "CRITICAL"
        elif severity_counts["high"] > 0:
            return "HIGH"
        elif severity_counts["medium"] > 0:
            return "MEDIUM"
        else:
            return "LOW"

    def _has_valid_hf_token(self) -> bool:
        """HuggingFace token'ının geçerli olup olmadığını kontrol et"""
        try:
            hf_token = os.getenv('HUGGINGFACE_TOKEN')
            if not hf_token:
                logger.error("❌ HUGGINGFACE_TOKEN environment variable yok!")
                return False
            
            # Token'ın Inference API yetkisi var mı kontrol et
            import requests
            headers = {"Authorization": f"Bearer {hf_token}"}
            response = requests.get("https://huggingface.co/api/whoami", headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                user_name = user_data.get("name", "unknown")
                logger.info(f"✅ HuggingFace token geçerli - Kullanıcı: {user_name}")
                
                # Inference API yetkisi kontrolü
                permissions = user_data.get("permissions", [])
                if "inference" in permissions:
                    logger.info("✅ Inference API yetkisi mevcut")
                    return True
                else:
                    logger.error(f"❌ Inference API yetkisi yok! Mevcut yetkiler: {permissions}")
                    logger.error("💡 HuggingFace token'ınızı 'Inference API' yetkisi ile yeniden oluşturun")
                    return False
            else:
                logger.error(f"❌ HuggingFace token geçersiz! Status: {response.status_code}")
                if response.status_code == 401:
                    logger.error("💡 Token süresi dolmuş veya geçersiz")
                elif response.status_code == 403:
                    logger.error("💡 Token yetkisi yetersiz")
                return False
                
        except Exception as e:
            logger.error(f"❌ HuggingFace token kontrol hatası: {e}")
            return False

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

