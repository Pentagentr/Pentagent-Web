"""
RAG Servis Modülü
CVE RAG sistemi ile entegrasyon için servis
Qdrant üzerinden CVE araması yapar
LLM ile optimize query oluşturma
mixedbread-ai/mxbai-rerank-xsmall-v1 ile sonuç reranking (hafif ve hızlı)
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
    Memory-efficient ve production-ready.
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
        self._session = None  # Shared aiohttp session
        self._token_validation_cache = None  # Token validation cache
        self._token_validation_time = None  # Last validation time
        self._initialize()
        self._initialized = True
    
    def _initialize(self):
        """RAG engine'i başlat"""
        try:
            if CVESearchEngine is None:
                logger.warning("CVE Search Engine modülü yüklenemedi. RAG özellikleri devre dışı.")
                return
            
            logger.info("RAG servis başlatılıyor...")
            

            qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
            

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
            

            is_cloud = search_config.qdrant_api_key is not None or search_config.qdrant_host.startswith('http')
            if is_cloud:
                logger.info(f"Qdrant Cloud'a bağlanılıyor: {search_config.qdrant_host}")
            else:
                logger.info(f"Local Qdrant'a bağlanılıyor: {search_config.qdrant_host}:{search_config.qdrant_port}")
            

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
    
    async def _get_or_create_session(self):
        """Shared aiohttp session - memory efficient"""
        if self._session is None or self._session.closed:

            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self._session
    
    async def _close_session(self):
        """Session cleanup - memory leak prevention"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _rerank_results(self, query: str, results: List[CVEResult], limit: int = 5) -> List[CVEResult]:
        """
        HuggingFace mixedbread-ai/mxbai-rerank-xsmall-v1 ile sonuçları yeniden sırala.
        Hata durumunda FALLBACK: Orijinal sıralama
        Memory-efficient ve production-ready.
        
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
        

        reranker_url = os.getenv('RERANKER_API_URL')
        if not reranker_url or reranker_url == 'https://your-space.hf.space/rerank':
            logger.warning("⚠️ RERANKER_API_URL ayarlanmamış, reranker atlanıyor")
            logger.warning("💡 Environment variable'da kendi Space URL'nizi ayarlayın")
            return results
        
        try:
            logger.info(f"🔄 Reranker başlatılıyor: {len(results)} sonuç sıralanacak")
            

            documents = []
            for r in results:

                doc_parts = [
                    f"CVE: {r.cve_id}",
                    f"Description: {r.description[:400]}",
                    f"Severity: {r.severity or 'Unknown'}",
                    f"CVSS: {r.base_score or 'N/A'}"
                ]
                if r.product:
                    doc_parts.append(f"Product: {r.product}")
                if r.vendor:
                    doc_parts.append(f"Vendor: {r.vendor}")
                
                documents.append(" | ".join(doc_parts))
            
            logger.info(f"📝 {len(documents)} document reranker formatında hazırlandı")
            

            reranker_url_raw = os.getenv('RERANKER_API_URL', 'https://meryemarpaci-pentagent-mxbai-rerank.hf.space/rerank')
            

            if reranker_url_raw and not reranker_url_raw.startswith('http'):

                if '/' in reranker_url_raw and not reranker_url_raw.startswith('http'):
                    space_name = reranker_url_raw.replace('/', '-')
                    reranker_url = f"https://{space_name}.hf.space/rerank"
                else:
                    reranker_url = reranker_url_raw
            elif reranker_url_raw and '/rerank' not in reranker_url_raw:

                reranker_url = reranker_url_raw.rstrip('/') + '/rerank'
            else:
                reranker_url = reranker_url_raw
            
            logger.info(f"🎯 Reranker endpoint: {reranker_url}")
            

            headers = {
                "Content-Type": "application/json"
            }
            

            payload = {
                "query": query,
                "documents": documents,
                "top_k": limit
            }
            logger.info(f"🎯 Kendi Reranker Space kullanılıyor")
            

            doc_count = len(documents)
            logger.info(f"📤 {doc_count} document reranker'a gönderiliyor")
            logger.info(f"🔗 POST {reranker_url}")
            logger.debug(f"📦 Payload: query='{query[:50]}...', documents={doc_count}, top_k={limit}")
            


            import requests
            try:
                response = requests.post(
                    reranker_url,
                    headers=headers,
                    json=payload,
                    timeout=(10, 90)  # (connect, read) timeout - 90s HuggingFace Space cold start için
                )
                    
                if response.status_code == 404:
                    logger.warning(f"⚠️ Reranker Space bulunamadı: {reranker_url}")
                    logger.warning("💡 Çözüm: RERANKER_API_URL environment variable'ını kontrol edin")
                    logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                    return results
                
                if response.status_code == 503:
                    logger.warning(f"⚠️ Reranker Space uyuyor (cold start)")
                    logger.warning("💡 Space uyanıyor, lütfen tekrar deneyin")
                    logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                    return results
                
                if response.status_code == 405:
                    error_text = response.text
                    logger.error(f"❌ Reranker API Method Not Allowed (405): {reranker_url}")
                    logger.error(f"💡 URL kontrolü: Space URL'i doğru formatta olmalı")
                    logger.error(f"💡 Doğru format: https://username-spacename.hf.space/rerank")
                    logger.error(f"💡 Örnek: https://meryemarpaci-pentagent-mxbai-rerank.hf.space/rerank")
                    logger.error(f"API yanıtı: {error_text[:200]}")
                    logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                    return results
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.warning(f"⚠️ Reranker API hatası: {response.status_code}")
                    logger.warning(f"💡 URL: {reranker_url}")
                    logger.warning(f"API yanıtı: {error_text[:200]}")
                    logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                    return results
                

                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > 1_000_000:
                    logger.warning(f"⚠️ Reranker response çok büyük: {content_length} bytes")
                    logger.warning("⚠️ Memory koruması - orijinal sıralama kullanılıyor")
                    return results
                
                rerank_response = response.json()
                logger.info(f"✅ Reranker yanıtı alındı: {type(rerank_response)}")
                

                if isinstance(rerank_response, dict) and 'scores' in rerank_response:
                    rerank_scores = rerank_response['scores']
                    logger.info(f"📊 {len(rerank_scores)} skor alındı")
                else:
                    logger.warning(f"⚠️ Beklenmeyen reranker response formatı: {type(rerank_response)}")
                    return results
                
                if len(rerank_scores) == len(results):

                    reranked = []
                    for idx, score in enumerate(rerank_scores):
                        cve = results[idx]
                        original_score = cve.score
                        

                        rerank_score = float(score) if isinstance(score, (int, float)) else 0.5
                        



                        boosted_score = min(1.0, rerank_score * 10.0)  # 10x boost, max 1.0
                        normalized_rerank = max(0.0, boosted_score)
                        


                        combined_score = (original_score * 0.15) + (normalized_rerank * 0.85)
                        

                        cve.score = combined_score
                        
                        reranked.append({
                            "cve": cve,
                            "original_score": original_score,
                            "rerank_score": rerank_score,
                            "normalized_rerank": normalized_rerank,
                            "combined_score": combined_score
                        })
                    

                    reranked.sort(key=lambda x: x['combined_score'], reverse=True)
                    

                    reranked_cves = [item['cve'] for item in reranked]
                    
                    logger.info(f"✅ RERANKING TAMAMLANDI: {len(reranked_cves)} sonuç")
                    

                    for i, item in enumerate(reranked[:3], 1):
                        logger.info(f"  🏆 #{i}: {item['cve'].cve_id} | Rerank: {item['rerank_score']:.3f} | Normalized: {item['normalized_rerank']:.3f} | Final: {item['combined_score']:.3f} ({item['combined_score']*100:.1f}%)")
                    
                    return reranked_cves
                else:
                    logger.error(f"❌ Beklenmeyen reranker yanıtı: {type(rerank_scores)}, len: {len(rerank_scores) if isinstance(rerank_scores, list) else 'N/A'}")
                    raise Exception("Reranker yanıtı işlenemedi")
            
            except requests.exceptions.Timeout:
                logger.error("❌ Reranker TIMEOUT (30s)")
                logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                return results
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Reranker bağlantı hatası: {e}")
                logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                return results
            except Exception as e:
                logger.warning(f"⚠️ RERANKER request hatası: {type(e).__name__} - {e}")
                logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                return results
        except Exception as e:
            logger.warning(f"⚠️ RERANKER BAŞARISIZ: {type(e).__name__} - {e}")
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
        use_reranker: Optional[bool] = None,
        query_info: Optional[Dict[str, Any]] = None
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

        if self._engine is None and not self._available:
            logger.info("🔄 RAG Engine ilk kullanımda başlatılıyor...")
            self._initialize()
        
        if not self.is_available():
            logger.warning("RAG servisi kullanılamıyor")
            return []
        
        try:
            logger.info(f"CVE araması yapılıyor: '{query}' (limit={limit}, severity={severity})")
            

            reranker_enabled = True if use_reranker is None else use_reranker

            fetch_limit = 20 if reranker_enabled else limit
            if reranker_enabled:
                logger.info(f"🎯 Reranker aktif - {fetch_limit} sonuç çekilecek, reranking sonrası {limit} döndürülecek")
            else:
                logger.info(f"🎯 Reranker devre dışı - {limit} sonuç döndürülecek")
            

            if severity:

                from qdrant_client.models import Filter, FieldCondition, MatchValue
                severity_filter = Filter(
                    must=[
                        FieldCondition(
                            key="severity",
                            match=MatchValue(value=severity.upper())
                        )
                    ]
                )
                results = self._engine.search(
                    query=query,
                    severity=severity,
                    limit=fetch_limit
                )
            else:
                results = self._engine.search(query, limit=fetch_limit)
            

            cve_results = []
            for r in results:

                metadata = r.metadata or {}
                references = metadata.get('references', [])
                

                logger.info(f"🔗 CVE {r.cve_id}: {len(references) if references else 0} referans bulundu")
                if references and len(references) > 0:
                    logger.info(f"   İlk referans: {references[0] if isinstance(references[0], str) else references[0].get('url', 'N/A')}")
                
                cve_results.append(CVEResult(
                    cve_id=r.cve_id,
                    score=r.score,
                    severity=r.severity,
                    base_score=r.base_score,
                    attack_vector=r.attack_vector,
                    description=r.description,
                    published_date=r.published_date,
                    modified_date=metadata.get('modified_date'),
                    references=references,
                    cwe_id=metadata.get('cwe_id'),
                    vendor=metadata.get('vendor'),
                    product=metadata.get('product'),
                    cvss_vector=metadata.get('cvss_vector'),
                    exploitability_score=metadata.get('exploitability_score'),
                    impact_score=metadata.get('impact_score')
                ))
            
            logger.info(f"✅ {len(cve_results)} CVE bulundu (vektör araması)")
            

            if reranker_enabled:
                if len(cve_results) <= 1:
                    logger.info(f"⚠️ Reranker atlanıyor: {len(cve_results)} sonuç var (en az 2 sonuç gerekli)")
                else:

                    reranker_url = os.getenv('RERANKER_API_URL')
                    if not reranker_url or reranker_url == 'https://your-space.hf.space/rerank':
                        logger.warning(f"⚠️ RERANKER_API_URL ayarlanmamış veya geçersiz: {reranker_url}")
                        logger.warning("⚠️ Reranker atlanıyor, orijinal sıralama kullanılıyor")
                    else:
                        logger.info(f"🔄 Reranker başlatılıyor ({len(cve_results)} sonuç) → {reranker_url}")
            
            if reranker_enabled and len(cve_results) > 1:
                logger.info(f"🔄 Reranker işleme başlıyor...")
                

                try:
                    import concurrent.futures
                    
                    def run_rerank_in_new_loop():
                        """Yeni event loop oluştur ve rerank çalıştır - Thread-safe"""

                        new_loop = asyncio.new_event_loop()
                        try:
                            asyncio.set_event_loop(new_loop)
                            return new_loop.run_until_complete(
                                self._rerank_results(query, cve_results, limit)
                            )
                        finally:

                            try:

                                pending = asyncio.all_tasks(new_loop)
                                for task in pending:
                                    task.cancel()

                                if pending:
                                    new_loop.run_until_complete(
                                        asyncio.gather(*pending, return_exceptions=True)
                                    )
                            except Exception:
                                pass  # Hata olsa bile devam et
                            finally:
                                new_loop.close()
                                asyncio.set_event_loop(None)  # Thread'den loop'u temizle
                    

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(run_rerank_in_new_loop)
                        try:
                            reranked_results = future.result(timeout=60)  # 60s timeout (HuggingFace Space cold start için)
                            

                            reranked_results = reranked_results[:limit]
                            logger.info(f"✅ Reranking tamamlandı, en iyi {len(reranked_results)} sonuç döndürülüyor")
                            return reranked_results
                            
                        except concurrent.futures.TimeoutError:

                            logger.warning("⏱️ Reranker thread pool TIMEOUT (60s) - orijinal sıralama kullanılıyor (normal durum)")
                            future.cancel()  # Cancel the future
                            return cve_results[:limit]
                        except RuntimeError as e:
                            if "Event loop is closed" in str(e):

                                logger.warning(f"⚠️ Event loop closed hatası yakalandı: {e}")
                                logger.info("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan) - normal fallback")
                                return cve_results[:limit]
                            raise  # Diğer RuntimeError'ları yukarı fırlat
                        except asyncio.TimeoutError:

                            logger.warning(f"⏱️ Reranker asyncio TIMEOUT - orijinal sonuçlar döndürülüyor (normal durum)")
                            return cve_results[:limit]
                        except Exception as e:

                            error_msg = str(e) if str(e) else f"{type(e).__name__} hatası"
                            logger.warning(f"⚠️ RERANKER request hatası: {error_msg}")
                            logger.info("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan) - normal fallback")
                            return cve_results[:limit]
                            
                except RuntimeError as e:
                    if "Event loop is closed" in str(e) or "cannot be called from a running event loop" in str(e).lower():
                        logger.error(f"❌ RERANKER Event loop hatası: {e}")
                        logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                        return cve_results[:limit]
                    raise  # Diğer RuntimeError'ları yukarı fırlat
                except asyncio.TimeoutError:
                    logger.error(f"⏱️ Reranker asyncio TIMEOUT - orijinal sonuçlar döndürülüyor")
                    return cve_results[:limit]
                except Exception as e:
                    logger.warning(f"⚠️ RERANKER request hatası: {type(e).__name__} - {e}")
                    logger.warning("⚠️ Orijinal sıralama kullanılıyor (Reranker olmadan)")
                    return cve_results[:limit]
            else:

                return cve_results[:limit]
            
        except Exception as e:
            logger.error(f"❌ CVE arama hatası: {type(e).__name__} - {e}")
            logger.warning("⚠️ Boş sonuç döndürülüyor (sistem çökmesi engellendi)")
            return []
    
    def get_cve_by_id(self, cve_id: str) -> Optional[CVEResult]:
        """
        CVE ID ile direkt CVE detayı getir.
        
        Args:
            cve_id: CVE ID (ör: CVE-2024-12345)
            
        Returns:
            CVEResult veya None
        """

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

        if self._engine is None and not self._available:
            logger.info("🔄 RAG Engine ilk kullanımda başlatılıyor...")
            self._initialize()
        
        if not self.is_available():
            return {'results': [], 'query': '', 'summary': ''}
        
        try:

            query = self._generate_optimized_query_with_llm(scan_results)
            summary = self._summarize_scan_results(scan_results)
            
            if not query:

                logger.warning("LLM query oluşturamadı, basit query kullanılıyor")
                query = self._generate_query_from_scan(scan_results)
            
            if not query:
                logger.warning("Scan sonuçlarından query oluşturulamadı")
                return {'results': [], 'query': '', 'summary': summary}
            
            logger.info(f"Scan analizi için oluşturulan query: '{query}'")
            

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

            model = UnifiedLLM()
            

            all_tool_outputs = self._prepare_all_tool_outputs_for_ai(scan_results)
            
            logger.info(f"🔍 RAG Query için hazırlanan tool outputs: {len(all_tool_outputs) if all_tool_outputs else 0} karakter")
            logger.info(f"📊 Scan results keys: {list(scan_results.keys())}")
            
            if not all_tool_outputs or all_tool_outputs == "No tool outputs":
                logger.warning("⚠️ Hiç tool çıktısı yok, generic query kullanılıyor")
                logger.warning(f"⚠️ Scan results içeriği: {scan_results}")
                return "web application security vulnerability exploitation"
            

            prompt = f"""Sen bir Kıdemli Siber Güvenlik Analistisin. Aşağıdaki penetrasyon testi sonuçlarını detaylı analiz et ve CVE veritabanı için SPESİFİK arama sorgusu oluştur.

🎯 HEDEF: {scan_results.get('target', 'Unknown')}

📊 TÜM TOOL ÇIKTILARI:
{all_tool_outputs[:5000]}

🔍 DETAYLI ANALİZ GÖREVİN:
1. **TEKNOLOJİ TESPİTİ**: Hangi yazılımlar, versiyonlar, servisler tespit edildi?
2. **GÜVENLİK AÇIKLARI**: Hangi zafiyetler, misconfigurations, vulnerabilities bulundu?
3. **KRİTİK BULGULAR**: En önemli güvenlik riskleri neler?

🎯 SPESİFİK QUERY OLUŞTURMA KURALLARI - TÜM DETAYLARI KORU:
- ✅ MUTLAKA tespit edilen teknoloji ve versiyonu kullan - VERSİYON NUMARALARINI ASLA ÇIKARMA
- ✅ Eğer versiyon yoksa, teknoloji adını + zafiyet türünü kullan
- ✅ Tespit edilen zafiyet türünü belirt (XSS, SQLi, LFI, RCE, vb.)
- ✅ CVE veritabanında bulunabilir format kullan
- ✅ YIL BİLGİSİ VARSA MUTLAKA QUERY'DE TUT (CVE-2021, 2024, vb.) - YILI ASLA KALDIRMA!
- ✅ KOD NUMARALARINI KORU: CVE ID'leri, bug numaraları, commit hash'leri koru
- ✅ PATH'LERİ VE DOSYA ADLARINI KORU: Spesifik path'ler ve dosya adları varsa koru
- ✅ TEKNİK DETAYLARI KORU: Ürün adları, vendor adları, protokol adları TAM OLARAK koru
- ❌ SADECE FİLLER KELİMELERİ KALDIR: "nasıl", "neden", "ne", "hakkında" gibi filler kelimeleri çıkar
- SADECE query string döndür, açıklama YAPMA
- Teknoloji adını tam olarak yaz (kısaltma kullanma)
- Uzun olsa bile önemli detayları koru - karakter limiti yok, detaylar öncelikli

💡 SPESİFİK QUERY ÖRNEKLERİ (İYİ):
- "Apache HTTP Server 2.4.49 path traversal directory listing CVE-2021"
- "WordPress 5.8.1 SQL injection authentication bypass vulnerability"
- "nginx 1.18.0 HTTP request smuggling remote code execution"
- "PHP 7.4.3 file upload arbitrary code execution CVE"
- "OpenSSH 8.2 authentication bypass privilege escalation"
- "MySQL 8.0.27 SQL injection remote authentication bypass"
- "Redis 6.2.0 unauthorized access remote code execution"
- "Node.js Express 4.17.1 prototype pollution denial of service"

❌ KÖTÜ QUERY ÖRNEKLERİ (KULLANMA):
- "web application vulnerability" (çok generic)
- "security issue" (belirsiz)
- "exploit" (spesifik değil)
- "server misconfiguration" (teknoloji belirtilmemiş)

⚠️ ÖNEMLİ: 
- Tool çıktılarından TESPİT EDİLEN GERÇEK bilgileri kullan
- Teknoloji + Version + Zafiyet Türü kombinasyonu ŞART
- Generic kelimeler kullanma, spesifik ol
- CVE formatında arama yapılacak, buna uygun query yaz

Şimdi SPESİFİK CVE query'i oluştur:"""
            

            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():

                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(
                            asyncio.run,
                            model.generate_content_async(prompt)
                        )
                        try:
                            response = future.result(timeout=20)  # 20s timeout
                        except concurrent.futures.TimeoutError:
                            logger.warning("LLM query generation TIMEOUT (20s)")
                            future.cancel()
                            return self._generate_query_from_scan(scan_results)
                else:

                    response = loop.run_until_complete(
                        model.generate_content_async(prompt)
                    )
            except RuntimeError as e:

                logger.warning(f"Event loop hatası: {e}, basit query kullanılıyor")
                return self._generate_query_from_scan(scan_results)
            except asyncio.TimeoutError:
                logger.warning("LLM query generation asyncio TIMEOUT")
                return self._generate_query_from_scan(scan_results)
            

            if isinstance(response, str):
                query = response.strip()
            elif hasattr(response, 'text'):
                query = response.text.strip()
            elif hasattr(response, 'get'):
                query = response.get('text', '').strip()
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                query = str(response).strip()
            

            if query and len(query) > 10:

                if query.startswith('"') and query.endswith('"'):
                    query = query[1:-1]
                
                logger.info(f"✅ LLM query oluşturuldu: '{query}'")
                return query
            else:

                logger.debug(f"LLM query oluşturulamadı veya kısa döndü, fallback kullanılıyor")
                fallback_query = self._generate_query_from_scan(scan_results)
                if fallback_query:
                    logger.info(f"✅ Fallback query oluşturuldu: '{fallback_query}'")
                return fallback_query
            
        except Exception as e:
            logger.error(f"LLM query oluşturma hatası: {e}")
            return ""
    
    def _prepare_all_tool_outputs_for_ai(self, scan_results: Dict[str, Any]) -> str:
        """
        TÜM TOOL ÇIKTILARINI AI'ya vermek için hazırla - JSON FORMATINDA.
        """
        try:
            import json
            

            tool_outputs = []
            target = scan_results.get("target", "target")
            

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
            

            if "execution_summary" in scan_results:
                exec_summary = scan_results["execution_summary"]
                tool_outputs.append({
                    "execution_info": exec_summary,
                    "tools_executed": exec_summary.get("tools_executed", []),
                    "successful_tools": exec_summary.get("successful_tools", [])
                })
            

            if "findings" in scan_results and scan_results["findings"]:
                tool_outputs.append({
                    "findings": scan_results["findings"],
                    "findings_count": len(scan_results["findings"])
                })
            

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
            

            if "findings" in scan_results and scan_results["findings"]:
                findings = scan_results["findings"]
                logger.info(f"📊 Mevcut {len(findings)} bulgu kullanılıyor")
                

                enriched_findings = []
                for finding in findings:
                    enriched_finding = finding.copy()
                    

                    if "context_summary" in scan_results:
                        context = scan_results["context_summary"]
                        if "technologies" in context:
                            enriched_finding["detected_technologies"] = context["technologies"]
                        if "open_ports" in context:
                            enriched_finding["open_ports"] = context["open_ports"]
                        if "parameters" in context:
                            enriched_finding["discovered_parameters"] = context["parameters"]
                    

                    if "execution_summary" in scan_results:
                        exec_summary = scan_results["execution_summary"]
                        enriched_finding["tools_executed"] = exec_summary.get("tools_executed", [])
                        enriched_finding["successful_tools"] = exec_summary.get("successful_tools", [])
                    
                    enriched_findings.append(enriched_finding)
                
                return json.dumps(enriched_findings, indent=2, ensure_ascii=False)
            

            findings = []
            target = scan_results.get("target", "target")
            

            for tool_name, tool_result in scan_results.items():
                if not isinstance(tool_result, dict):
                    continue
                

                if tool_name.startswith("tool_"):
                    tool_name = tool_name[5:]  # "tool_" prefix'ini kaldır
                

                if "web_crawler" in tool_name.lower():
                    forms = tool_result.get("forms", [])
                    endpoints = tool_result.get("endpoints", [])
                    parameters = tool_result.get("parameters", [])
                    pages = tool_result.get("pages", [])
                    technologies = tool_result.get("technologies", [])
                    

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
                

                else:

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
        

        for tool_name, tool_result in scan_results.items():
            if not isinstance(tool_result, dict):
                continue
            

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
            

            elif "api" in tool_name.lower():
                api_endpoints = tool_result.get("api_endpoints", [])
                if api_endpoints:
                    security_findings.append(f"{target} API endpoint security vulnerability")
            

            elif "directory" in tool_name.lower():
                directories = tool_result.get("directories", [])
                sensitive_dirs = []
                for dir_path in directories:
                    if any(word in dir_path.lower() for word in ['admin', 'backup', 'config', 'logs', 'test', 'dev']):
                        sensitive_dirs.append(dir_path)
                if sensitive_dirs:
                    security_findings.append(f"{target} sensitive directory exposure vulnerability")
            

            elif "header" in tool_name.lower():
                missing_headers = tool_result.get("missing_security_headers", [])
                if missing_headers:
                    if "X-Frame-Options" in missing_headers:
                        security_findings.append(f"{target} clickjacking vulnerability missing X-Frame-Options")
                    if "X-XSS-Protection" in missing_headers:
                        security_findings.append(f"{target} XSS protection vulnerability")
                    if "Content-Security-Policy" in missing_headers:
                        security_findings.append(f"{target} CSP injection vulnerability")
            

            elif "tech" in tool_name.lower():
                technologies = tool_result.get("technologies", []) or tool_result.get("detected_technologies", [])
                if technologies and isinstance(technologies, list):
                    for tech in technologies[:2]:
                        if isinstance(tech, dict):
                            tech_name = tech.get("name", "") or tech.get("technology", "")
                            version = tech.get("version", "")
                            if tech_name and version and version != "N/A":
                                security_findings.append(f"{target} {tech_name} {version} vulnerability")
            

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
        

        context = scan_results.get("context_summary", {})
        if isinstance(context, dict):

            forms = context.get("forms", [])
            if forms:
                security_findings.append(f"{target} web application form vulnerability")
            

            parameters = context.get("parameters", [])
            if parameters:
                security_findings.append(f"{target} parameter manipulation vulnerability")
        

        if security_findings:

            return " ".join(security_findings[:3])
        else:
            return f"{target} web application security vulnerability"
    
    def _summarize_scan_results(self, scan_results: Dict[str, Any]) -> str:
        """
        Scan sonuçlarını LLM için KAPSAMLI özet haline getirir.
        TÜM TOOL ÇIKTILARI, BULGULAR, TEKNOLOJİLER detaylı şekilde.
        """
        summary_parts = []
        

        target = scan_results.get("target", "")
        if target:
            summary_parts.append(f"🎯 HEDEF: {target}\n")
        

        context = scan_results.get("context_summary", {})
        if context:
            summary_parts.append("📊 TARAMA CONTEXT:")
            

            if context.get("technologies"):
                techs = context["technologies"]
                summary_parts.append(f"  • Tespit Edilen Teknolojiler ({len(techs)}): {', '.join(techs[:10])}")
            

            if context.get("open_ports"):
                ports = context["open_ports"]
                summary_parts.append(f"  • Açık Portlar ({len(ports)}): {', '.join(map(str, ports[:20]))}")
            

            if context.get("services"):
                services = context["services"]
                summary_parts.append(f"  • Aktif Servisler ({len(services)}): {', '.join(services[:10])}")
            

            if context.get("subdomains"):
                subs = context["subdomains"]
                summary_parts.append(f"  • Subdomain'ler ({len(subs)}): {', '.join(subs[:10])}")
            

            if context.get("forms"):
                forms = context["forms"]
                summary_parts.append(f"  • Keşfedilen Formlar: {len(forms)} adet")
            

            if context.get("parameters"):
                params = context["parameters"]
                summary_parts.append(f"  • URL Parametreleri ({len(params)}): {', '.join(params[:15])}")
            

            if context.get("endpoints"):
                eps = context["endpoints"]
                summary_parts.append(f"  • API Endpoint'ler ({len(eps)}): {', '.join(eps[:10])}")
            
            summary_parts.append("")  # Boş satır
        

        summary_parts.append("🔍 TOOL SONUÇLARI:")
        for tool_name, tool_result in scan_results.items():
            if tool_name in ["target", "context_summary", "execution_summary"] or not isinstance(tool_result, dict):
                continue
                
            tool_summary = []
            

            if "web_crawler" in tool_name or "enum_web_crawler" in tool_name:
                if tool_result.get("forms"):
                    tool_summary.append(f"{len(tool_result['forms'])} form")
                if tool_result.get("endpoints"):
                    tool_summary.append(f"{len(tool_result['endpoints'])} endpoint")
                if tool_result.get("parameters"):
                    tool_summary.append(f"{len(tool_result['parameters'])} parametre")
                if tool_result.get("pages"):
                    tool_summary.append(f"{len(tool_result['pages'])} sayfa")
            

            elif "port" in tool_name:
                if tool_result.get("open_ports"):
                    ports = tool_result["open_ports"]
                    tool_summary.append(f"{len(ports)} açık port: {', '.join(map(str, ports[:10]))}")
            

            elif "tech" in tool_name:
                if tool_result.get("technologies"):
                    techs = tool_result["technologies"]
                    tool_summary.append(f"{len(techs)} teknoloji: {', '.join(techs[:8])}")
            

            elif "ssl" in tool_name:
                if tool_result.get("vulnerabilities"):
                    tool_summary.append(f"{len(tool_result['vulnerabilities'])} SSL zafiyeti")
                if tool_result.get("certificate_info"):
                    tool_summary.append("SSL sertifika analizi")
            

            elif "subdomain" in tool_name:
                if tool_result.get("subdomains"):
                    subs = tool_result["subdomains"]
                    tool_summary.append(f"{len(subs)} subdomain: {', '.join(subs[:8])}")
            

            elif "directory" in tool_name or "bruteforce" in tool_name:
                if tool_result.get("directories"):
                    dirs = tool_result["directories"]
                    tool_summary.append(f"{len(dirs)} dizin: {', '.join(dirs[:8])}")
            

            elif "panel" in tool_name or "admin" in tool_name:
                if tool_result.get("discovered_panels"):
                    panels = tool_result["discovered_panels"]
                    tool_summary.append(f"{len(panels)} panel: {', '.join(panels[:5])}")
            

            elif any(v in tool_name for v in ["xss", "sqli", "lfi", "verify"]):
                if tool_result.get("vulnerabilities"):
                    vulns = tool_result["vulnerabilities"]
                    tool_summary.append(f"{len(vulns)} zafiyet tespit edildi")
            

            else:
                if tool_result.get("vulnerabilities"):
                    tool_summary.append(f"{len(tool_result['vulnerabilities'])} zafiyet")
                if tool_result.get("findings"):
                    tool_summary.append(f"{len(tool_result['findings'])} bulgu")
                if tool_result.get("success") and tool_result.get("data"):
                    data = tool_result["data"]
                    if isinstance(data, dict):
                        tool_summary.append(f"{len(data)} veri noktası")
            
            if tool_summary:
                summary_parts.append(f"  • {tool_name}: {', '.join(tool_summary)}")
        
        summary_parts.append("")  # Boş satır
        

        exec_summary = scan_results.get("execution_summary", {})
        if exec_summary:
            summary_parts.append("📈 TARAMA İSTATİSTİKLERİ:")
            if exec_summary.get("tools_executed"):
                tools = exec_summary["tools_executed"]
                summary_parts.append(f"  • Çalıştırılan Tool Sayısı: {len(tools)}")
            if exec_summary.get("successful_tools"):
                success = exec_summary["successful_tools"]
                summary_parts.append(f"  • Başarılı Tool Sayısı: {len(success)}")
            if exec_summary.get("total_findings"):
                summary_parts.append(f"  • Toplam Bulgu: {exec_summary['total_findings']}")
        
        result = "\n".join(summary_parts) if summary_parts else "Tarama sonuçları bulunamadı"
        logger.info(f"📋 KAPSAMLI Scan Summary oluşturuldu: {len(result)} karakter")
        return result
    
    def _generate_query_from_scan(self, scan_results: Dict[str, Any]) -> str:
        """
        Basit query oluştur (LLM fallback için).
        Scan results'tan teknoloji, zafiyet ve servis bilgilerini çıkararak optimize query oluşturur.
        
        Args:
            scan_results: Tarama sonuçları
            
        Returns:
            RAG query string
        """
        query_parts = []
        target = scan_results.get("target", "")
        

        for key, value in scan_results.items():
            if not isinstance(value, dict):
                continue
                

            tool_data = value.get("data", {}) if isinstance(value.get("data"), dict) else {}
            

            technologies = tool_data.get("technologies", [])
            if technologies and isinstance(technologies, list):
                tech_list = [str(t) for t in technologies[:3] if t]
                if tech_list:
                    query_parts.extend(tech_list)
            

            vulnerabilities = tool_data.get("vulnerabilities", [])
            if vulnerabilities and isinstance(vulnerabilities, list):
                vuln_types = [v.get("type", "") or v.get("title", "") for v in vulnerabilities[:3] if isinstance(v, dict)]
                vuln_types = [v for v in vuln_types if v and len(v) > 3]
                if vuln_types:
                    query_parts.extend(vuln_types)
            

            findings = tool_data.get("findings", {})
            if isinstance(findings, dict):

                critical = findings.get("critical", [])
                high = findings.get("high", [])
                if critical or high:
                    query_parts.append("security vulnerability")
            

            services = tool_data.get("services", [])
            if services and isinstance(services, list):
                service_names = [s.get("name", "") if isinstance(s, dict) else str(s) for s in services[:2]]
                service_names = [s for s in service_names if s and len(s) > 2]
                if service_names:
                    query_parts.extend(service_names)
        

        vulnerabilities = scan_results.get("vulnerabilities", [])
        if vulnerabilities and isinstance(vulnerabilities, list):
            vuln_types = [v.get("type", "") for v in vulnerabilities[:3] if isinstance(v, dict) and v.get("type")]
            if vuln_types:
                query_parts.extend(vuln_types)
        
        technologies = scan_results.get("technologies", [])
        if technologies and isinstance(technologies, list):
            tech_list = [str(t) for t in technologies[:2] if t]
            if tech_list:
                query_parts.extend(tech_list)
        

        if query_parts:

            seen = set()
            unique_parts = []
            for part in query_parts:
                part_lower = part.lower().strip()
                if part_lower and part_lower not in seen and len(part_lower) > 2:
                    seen.add(part_lower)
                    unique_parts.append(part.strip())
            
            if unique_parts:
                query = " ".join(unique_parts[:5])  # Max 5 kelime
                if target and target not in query:
                    query = f"{query} {target}"
                return query
        

        if target:
            return f"web application security vulnerability {target}"
        
        return "web application security vulnerability"
    
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
            

            scan_data = {
                "target": target,
                "scan_date": datetime.now().isoformat(),
                "findings": findings,
                "execution_summary": {
                    "total_tools_executed": len(execution_results) if isinstance(execution_results, (dict, list)) else 0,
                    "successful_tools": len([r for r in (execution_results.values() if isinstance(execution_results, dict) else execution_results) if isinstance(r, dict) and r.get("success", False)]),
                    "risk_level": self._calculate_overall_risk_level(findings)
                },
                "metadata": {
                    "scan_type": "comprehensive",
                    "methodology": "OWASP Top 10, PTES, NIST SP 800-115"
                }
            }
            

            try:

                try:
                    import firebase_admin
                    from firebase_admin import credentials, firestore
                    

                    if not firebase_admin._apps:

                        cred = credentials.ApplicationDefault()
                        firebase_admin.initialize_app(cred)
                    
                    db = firestore.client()
                    scan_ref = db.collection('scan_results').document()
                    scan_ref.set(scan_data)
                    logger.info(f"✅ Scan results Firebase'e kaydedildi: {target}")
                except ImportError:
                    logger.warning("⚠️ Firebase kütüphanesi yüklü değil, Firebase kayıt atlanıyor")
                except Exception as firebase_error:
                    logger.warning(f"⚠️ Firebase kayıt hatası: {firebase_error}")
            except Exception as e:
                logger.warning(f"⚠️ Firebase bağlantı hatası: {e}")
            

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

    def _is_token_valid_cached(self) -> bool:
        """
        HuggingFace token validation - CACHED (1 saat).
        Her request'te kontrol etme - memory ve network efficient.
        """
        import time
        

        current_time = time.time()
        if self._token_validation_cache is not None and self._token_validation_time is not None:
            if current_time - self._token_validation_time < 3600:

                return self._token_validation_cache
        

        is_valid = self._has_valid_hf_token()
        self._token_validation_cache = is_valid
        self._token_validation_time = current_time
        
        return is_valid
    
    def _has_valid_hf_token(self) -> bool:
        """HuggingFace token'ının geçerli olup olmadığını kontrol et"""
        try:
            hf_token = os.getenv('HUGGINGFACE_TOKEN')
            if not hf_token:
                logger.error("❌ HUGGINGFACE_TOKEN environment variable yok!")
                return False
            

            import requests
            headers = {"Authorization": f"Bearer {hf_token}"}
            response = requests.get("https://huggingface.co/api/whoami", headers=headers, timeout=5)
            
            if response.status_code == 200:
                user_data = response.json()
                user_name = user_data.get("name", "unknown")
                logger.info(f"✅ HuggingFace token geçerli - Kullanıcı: {user_name}")
                

                permissions = user_data.get("permissions", [])
                if isinstance(permissions, list):
                    if "inference" in permissions or "read" in permissions:
                        logger.info("✅ Inference API yetkisi mevcut")
                        return True
                    else:
                        logger.warning(f"⚠️ Inference API yetkisi belirsiz. Mevcut yetkiler: {permissions}")
                        logger.info("🔄 Inference API'yi deneyeceğiz...")
                        return True  # Deneme yapalım
                else:
                    logger.info("✅ Token geçerli, inference API'yi deneyeceğiz")
                    return True  # Deneme yapalım
            else:
                logger.warning(f"⚠️ HuggingFace token kontrol hatası: Status {response.status_code}")
                if response.status_code == 401:
                    logger.warning("💡 Token süresi dolmuş olabilir, ama deneyeceğiz")
                    return False  # 401 için cache'e False kaydet
                elif response.status_code == 403:
                    logger.warning("💡 Token yetkisi belirsiz, ama deneyeceğiz")
                    return True
                else:
                    logger.warning(f"⚠️ Beklenmeyen status: {response.status_code}")
                

                logger.info("🔄 Token kontrol hatası olmasına rağmen inference API'yi deneyeceğiz")
                return True
                
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



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("RAG Service Module - Production Ready")
    print("Use: from services.rag_service import get_rag_service")

