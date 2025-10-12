"""
CVE Arama Modülü - Production Ready
Bu modül Qdrant üzerinde CVE araması için hybrid search API sağlar.
Dense vektörlere öncelik verir (semantik search ağırlıklı).
HuggingFace Inference API ile embedding oluşturma desteği.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import uuid
import os
import requests

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
import httpx

try:
    from FlagEmbedding import BGEM3FlagModel
    import torch
    HAS_LOCAL_MODEL = True
except ImportError:
    HAS_LOCAL_MODEL = False
    logger = logging.getLogger(__name__)
    logger.warning("FlagEmbedding/torch not available - using HuggingFace Inference API")

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
            logger.info(f"Qdrant'a bağlanılıyor: {self.config.qdrant_host}")
            
            # URL format kontrolü (https:// ile başlıyorsa Cloud)
            is_cloud_url = self.config.qdrant_host.startswith('http://') or self.config.qdrant_host.startswith('https://')
            
            if is_cloud_url:
                # Cloud deployment (HuggingFace Space veya diğer)
                logger.info(f"Cloud Qdrant bağlantısı (URL-based): {self.config.qdrant_host}")
                
                # HuggingFace Space için port ekleme (sadece .hf.space değilse)
                full_url = self.config.qdrant_host
                if '.hf.space' not in full_url:
                    # HuggingFace Space DEĞİL - port ekle
                    if self.config.qdrant_port and self.config.qdrant_port != 443:
                        if ':' not in full_url.split('/')[-1]:
                            full_url = f"{self.config.qdrant_host}:{self.config.qdrant_port}"
                else:
                    # HuggingFace Space - port ekleme, direkt URL kullan
                    logger.info("HuggingFace Space detected - using httpx for fast connection")
                
                logger.info(f"Full Qdrant URL: {full_url}")
                self._base_url = full_url
                
                # Cloud için httpx kullan (QdrantClient çok yavaş)
                logger.info("Using httpx for Qdrant API calls (faster than QdrantClient)")
                self._use_httpx = True
                self._httpx_client = httpx.Client(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    follow_redirects=True
                )
                
                # Collection kontrolü (httpx ile)
                logger.info("Checking collections via httpx...")
                collections_response = self._httpx_client.get(f"{full_url}/collections")
                collections_response.raise_for_status()
                collections_data = collections_response.json()
                
                collection_names = [c['name'] for c in collections_data['result']['collections']]
                logger.info(f"Found collections: {collection_names}")
                
                if self.config.collection_name not in collection_names:
                    raise ValueError(f"Collection '{self.config.collection_name}' bulunamadı!")
                
                # QdrantClient'ı None yap, httpx kullanacağız
                self._client = None
                
            else:
                # Local deployment (host:port format) - QdrantClient kullan
                logger.info(f"Local Qdrant bağlantısı: {self.config.qdrant_host}:{self.config.qdrant_port}")
                self._use_httpx = False
                self._httpx_client = None
                self._base_url = f"http://{self.config.qdrant_host}:{self.config.qdrant_port}"
                
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
            
            # BGE-M3 model yükleme - HuggingFace Inference API veya local
            use_hf_api = os.getenv("USE_HF_INFERENCE_API", "true").lower() == "true"
            
            if use_hf_api:
                logger.info("HuggingFace Inference API kullanılacak (BGE-M3)")
                self._model = None  # API kullanacağız
                self._hf_token = self.config.huggingface_token
                self._hf_api_url = "https://api-inference.huggingface.co/models/BAAI/bge-m3"
            elif HAS_LOCAL_MODEL:
                logger.info(f"Local BGE-M3 modeli yükleniyor: {self.config.model_name}")
                device = "cuda" if torch.cuda.is_available() else "cpu"
                use_fp16 = device == "cuda"
                self._model = BGEM3FlagModel(self.config.model_name, use_fp16=use_fp16)
                logger.info(f"Model yüklendi (Device: {device.upper()})")
                self._hf_token = None
                self._hf_api_url = None
            else:
                logger.warning("BGE-M3 model yüklenemedi - text-based search kullanılacak")
                self._model = None
                self._hf_token = None
                self._hf_api_url = None
            
        except Exception as e:
            logger.error(f"Başlatma hatası: {e}")
            raise
    
    def _encode_query(self, query: str) -> Tuple[List[float], models.SparseVector]:
        """
        Query'yi dense ve sparse vektörlere çevir.
        HuggingFace Inference API veya local model kullanır.
        
        Args:
            query: Arama sorgusu
            
        Returns:
            (dense_vector, sparse_vector) tuple'ı
        """
        try:
            # HuggingFace Inference API kullan (production)
            if self._model is None and self._hf_api_url:
                return self._encode_with_hf_api(query)
            
            # Local model kullan
            if self._model is not None:
                # Dense vektör
                dense_vec = self._model.encode([query], return_dense=True)['dense_vecs'][0]
                
                # Sparse vektör
                sparse_output = self._model.encode([query], return_sparse=True)['lexical_weights'][0]
                sparse_vec = models.SparseVector(
                    indices=list(sparse_output.keys()),
                    values=list(sparse_output.values())
                )
                
                return dense_vec.tolist(), sparse_vec
            
            # Hiçbiri yoksa - FALLBACK: Query'yi text olarak kullan (embedding olmadan)
            logger.warning("⚠️ NE HF API NE LOCAL MODEL - Text-based fallback")
            # Basit text-based sparse vector oluştur
            words = query.lower().split()
            sparse_vec = models.SparseVector(
                indices=list(range(len(words))),
                values=[1.0] * len(words)
            )
            # Dense için dummy vector (sıfırlarla doldur)
            dense_vec = [0.0] * 1024  # BGE-M3 dimension
            return dense_vec, sparse_vec
            
        except Exception as e:
            logger.error(f"Query encoding hatası: {e}")
            raise
    
    def _encode_with_hf_api(self, query: str) -> Tuple[List[float], models.SparseVector]:
        """
        HuggingFace Inference API ile query'yi vektörleştirir.
        
        Args:
            query: Arama sorgusu
            
        Returns:
            (dense_vector, sparse_vector) tuple
        """
        try:
            headers = {}
            if self._hf_token:
                headers["Authorization"] = f"Bearer {self._hf_token}"
            
            # HuggingFace Inference API'ye istek
            response = requests.post(
                self._hf_api_url,
                headers=headers,
                json={"inputs": query, "options": {"wait_for_model": True}},
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"HF API error: {response.status_code} - {response.text}")
            
            # Dense vector al
            dense_vec = response.json()
            
            # Sparse için basit keyword extraction (approximate)
            # HF Inference API sparse desteklemediği için keyword-based sparse oluştur
            words = query.lower().split()
            sparse_indices = list(range(len(words)))
            sparse_values = [1.0] * len(words)
            
            sparse_vec = models.SparseVector(
                indices=sparse_indices,
                values=sparse_values
            )
            
            logger.info("HuggingFace Inference API ile encoding tamamlandı")
            return dense_vec, sparse_vec
            
        except Exception as e:
            logger.error(f"HuggingFace API encoding hatası: {e}")
            raise
    
    def _analyze_query_intelligence(self, query: str) -> dict:
        """
        🧠 AKILLI QUERY ANALİZİ - En optimal RAG stratejisini belirler
        
        Returns:
            {
                'has_cve_id': bool,
                'has_version': bool,
                'is_semantic': bool,
                'query_length': int,
                'dense_weight': float,
                'sparse_weight': float,
                'strategy': str,
                'reasoning': str
            }
        """
        # Pattern tespitleri
        has_cve_id = bool(re.search(r'CVE-\d{4}-\d{4,}', query, re.IGNORECASE))
        has_version = bool(re.search(r'\b(\d+\.)+\d+\b|version\s*\d+|v\d+\.\d+', query, re.IGNORECASE))
        
        # Semantic indicators
        words = query.split()
        query_length = len(words)
        
        # Semantic kelimeler (soru, açıklama, bağlaç vs)
        semantic_keywords = ['what', 'how', 'why', 'explain', 'describe', 'tell', 'about', 
                           'vulnerability', 'exploit', 'attack', 'impact', 'risk', 'security',
                           'nedir', 'nasıl', 'hakkında', 'anlat', 'açıkla']
        has_semantic_keywords = any(kw in query.lower() for kw in semantic_keywords)
        is_semantic = query_length >= 4 or has_semantic_keywords
        
        # 🎯 PROFESYONEL STRATEJI BELİRLEME
        if has_cve_id and has_version:
            # Senaryo: "CVE-2021-44228 Apache Log4j 2.14.1"
            # Hem exact match hem semantic context gerekli
            strategy = "balanced_hybrid"
            dense_weight = 0.50  # Semantic context
            sparse_weight = 0.50  # Exact matching (CVE ID + version)
            reasoning = "CVE ID + Version tespit edildi → Balanced hybrid (exact + context)"
            
        elif has_cve_id:
            # Senaryo: "CVE-2021-44228 nedir?"
            # CVE exact match + anlamsal açıklama
            strategy = "cve_semantic"
            dense_weight = 0.50  # Semantic açıklama için
            sparse_weight = 0.50  # CVE ID exact match
            reasoning = "CVE ID tespit edildi → Balanced (ID exact + semantic explanation)"
            
        elif has_version and not is_semantic:
            # Senaryo: "Apache 2.4.49"
            # Version exact ama semantic de önemli
            strategy = "version_aware"
            dense_weight = 0.60  # Semantic anlama
            sparse_weight = 0.40  # Version exact match
            reasoning = "Sürüm tespit edildi → Semantic öncelikli (anlam + version)"
            
        elif is_semantic and not has_version:
            # Senaryo: "SQL injection web application vulnerability"
            # Pure anlamsal arama
            strategy = "pure_semantic"
            dense_weight = 0.80  # Semantic dominant
            sparse_weight = 0.20  # Keyword minimal
            reasoning = "Anlamsal sorgu tespit edildi → Pure semantic (meaning-focused)"
            
        elif has_version and is_semantic:
            # Senaryo: "Apache 2.4.49 path traversal vulnerability"
            # Hem version hem semantic
            strategy = "semantic_version"
            dense_weight = 0.60  # Semantic biraz öncelikli
            sparse_weight = 0.40  # Version + keyword
            reasoning = "Sürüm + anlamsal sorgu → Semantic öncelikli hybrid"
            
        else:
            # Senaryo: Belirsiz/kısa query
            strategy = "balanced_default"
            dense_weight = 0.70  # Semantic default ağırlıklı
            sparse_weight = 0.30  # Keyword yardımcı
            reasoning = "Genel sorgu → Default balanced (semantic öncelikli)"
        
        logger.info(f"🧠 QUERY ANALİZİ: {strategy}")
        logger.info(f"   └─ {reasoning}")
        
        return {
            'has_cve_id': has_cve_id,
            'has_version': has_version,
            'is_semantic': is_semantic,
            'query_length': query_length,
            'dense_weight': dense_weight,
            'sparse_weight': sparse_weight,
            'strategy': strategy,
            'reasoning': reasoning
        }
    
    def search(
        self,
        query: str,
        limit: int = 10,
        dense_weight: Optional[float] = None,
        sparse_weight: Optional[float] = None,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        🚀 PROFESYONEL ADAPTIVE RAG SEARCH SYSTEM
        
        Akıllı query analizi ile optimal search stratejisi otomatik belirlenir:
        
        Stratejiler:
        ┌─────────────────────────────────────────────────────────────┐
        │ Pure Semantic      │ 80% dense | 20% sparse                 │
        │ CVE + Semantic     │ 50% dense | 50% sparse (exact+context) │
        │ Version + Semantic │ 60% dense | 40% sparse (meaning+exact) │
        │ CVE + Version      │ 50% dense | 50% sparse (balanced)      │
        │ Balanced Default   │ 70% dense | 30% sparse                 │
        └─────────────────────────────────────────────────────────────┘
        
        Args:
            query: Arama sorgusu
            limit: Maksimum sonuç sayısı
            dense_weight: Manuel dense ağırlığı (None = otomatik)
            sparse_weight: Manuel sparse ağırlığı (None = otomatik)
            min_score: Minimum skor threshold
            
        Returns:
            SearchResult listesi (en alakalı önce, tam metadata ile)
        """
        if not query or not query.strip():
            logger.warning("Boş query alındı")
            return []
        
        query = query.strip()
        logger.info(f"🔍 PROFESYONEL RAG SEARCH BAŞLATILDI")
        logger.info(f"   Query: '{query}' | Limit: {limit}")
        
        # 🧠 PHASE 1: AKILLI QUERY ANALİZİ
        analysis = self._analyze_query_intelligence(query)
        
        # Manuel weight yoksa analiz sonucunu kullan
        if dense_weight is None:
            dense_weight = analysis['dense_weight']
        if sparse_weight is None:
            sparse_weight = analysis['sparse_weight']
        
        logger.info(f"⚖️  AĞIRLIKLAR: Dense {dense_weight:.0%} | Sparse {sparse_weight:.0%}")
        
        # 🎯 PHASE 2: CVE ID DIRECT FETCH (varsa)
        if analysis['has_cve_id']:
            cve_id_result = self._detect_and_fetch_cve_id(query)
            if cve_id_result:
                logger.info(f"✅ CVE direkt getirildi: {cve_id_result.cve_id}")
                logger.info(f"🔄 Context search yapılıyor (hybrid)...")
                
                # Hybrid search ile ilgili CVE'leri de getir
                hybrid_results = self._hybrid_search_internal(
                    query, limit - 1, dense_weight, sparse_weight, min_score
                )
                # Duplicate temizle
                hybrid_results = [r for r in hybrid_results if r.cve_id != cve_id_result.cve_id]
                
                final_results = [cve_id_result] + hybrid_results[:limit-1]
                avg_score = sum(r.score for r in final_results) / len(final_results) if final_results else 0
                logger.info(f"✅ SEARCH TAMAMLANDI: {len(final_results)} sonuç (avg: {avg_score:.3f})")
                return final_results
        
        # 🔬 PHASE 3: HYBRID SEARCH (adaptive weights)
        results = self._hybrid_search_internal(query, limit, dense_weight, sparse_weight, min_score)
        
        # 📊 PHASE 4: RESULT ANALYSIS & LOGGING
        if results:
            avg_score = sum(r.score for r in results) / len(results)
            logger.info(f"✅ SEARCH TAMAMLANDI: {len(results)} sonuç (avg: {avg_score:.3f})")
            logger.info(f"   Top score: {results[0].score:.3f} | Strategy: {analysis['strategy']}")
        else:
            logger.warning(f"⚠️  Sonuç bulunamadı (query: '{query}')")
        
        return results
    
    def _detect_and_fetch_cve_id(self, query: str) -> Optional[SearchResult]:
        """
        Query'de CVE ID var mı kontrol eder ve varsa direkt getirir.
        CVE format: CVE-YYYY-NNNNN (ör: CVE-2024-12345)
        """
        import re
        # CVE pattern: CVE-YYYY-1234 veya CVE-YYYY-12345678
        cve_pattern = r'CVE-\d{4}-\d{4,}'
        match = re.search(cve_pattern, query, re.IGNORECASE)
        
        if match:
            cve_id = match.group(0).upper()
            logger.info(f"🎯 CVE ID tespit edildi: {cve_id}")
            return self.get_cve_by_id(cve_id)
        return None
    
    def _detect_version_in_query(self, query: str) -> bool:
        """
        Query'de sürüm numarası var mı kontrol eder.
        Format: 1.2.3, v1.2, 2.4.49, vb.
        """
        import re
        # Version patterns
        version_patterns = [
            r'\d+\.\d+\.\d+',  # 1.2.3
            r'\d+\.\d+',       # 1.2
            r'v\d+\.\d+',      # v1.2
            r'version\s+\d+',  # version 2
        ]
        
        for pattern in version_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.info(f"📌 Sürüm pattern tespit edildi: {pattern}")
                return True
        return False
    
    def _hybrid_search_internal(
        self,
        query: str,
        limit: int,
        dense_weight: Optional[float],
        sparse_weight: Optional[float],
        min_score: float
    ) -> List[SearchResult]:
        """Internal hybrid search implementation"""
        logger.info(f"🔬 Hybrid search yapılıyor: '{query}'")
        
        try:
            # Ağırlıkları ayarla ve optimize et
            d_weight = dense_weight if dense_weight is not None else self.config.default_dense_weight
            s_weight = sparse_weight if sparse_weight is not None else self.config.default_sparse_weight
            
            # Ağırlıkları normalize et
            total_weight = d_weight + s_weight
            d_weight = d_weight / total_weight
            s_weight = s_weight / total_weight
            
            logger.info(f"⚖️ Ağırlıklar: Dense={d_weight:.2f}, Sparse={s_weight:.2f}")
            
            # Query'yi vektörlere çevir
            dense_vec, sparse_vec = self._encode_query(query)
            
            # Dense arama (semantik) - daha fazla sonuç al sonra birleştir
            logger.info(f"🧠 Semantic search yapılıyor...")
            dense_results = self._search_dense(dense_vec, limit * 3)
            logger.info(f"  → {len(dense_results)} semantic sonuç bulundu")
            
            # Sparse arama (keyword) - daha fazla sonuç al
            logger.info(f"🔤 Keyword search yapılıyor...")
            sparse_results = self._search_sparse(sparse_vec, limit * 3)
            logger.info(f"  → {len(sparse_results)} keyword sonuç bulundu")
            
            # Sonuçları profesyonelce birleştir
            logger.info(f"🔗 Sonuçlar birleştiriliyor...")
            combined_results = self._combine_results(
                dense_results, sparse_results, d_weight, s_weight
            )
            
            # Minimum skor filtresi uygula
            if min_score > 0:
                combined_results = [r for r in combined_results if r.score >= min_score]
                logger.info(f"  → {len(combined_results)} sonuç min_score filtresini geçti (threshold={min_score})")
            
            # Limit uygula ve sırala (en yüksek skor önce)
            final_results = sorted(combined_results, key=lambda x: x.score, reverse=True)[:limit]
            
            logger.info(f"✅ Profesyonel arama tamamlandı: {len(final_results)} sonuç (avg score: {sum(r.score for r in final_results)/len(final_results) if final_results else 0:.3f})")
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Arama hatası: {e}")
            # Fallback: text-based search
            logger.info("⚠️ Fallback: text-based search kullanılıyor")
            return self._text_based_search(query, limit)
    
    def _search_dense(self, dense_vector: List[float], limit: int) -> List[Dict]:
        """Dense (semantik) arama yapar"""
        try:
            if self._use_httpx:
                # httpx ile REST API çağrısı
                url = f"{self._base_url}/collections/{self.config.collection_name}/points/query"
                payload = {
                    "query": dense_vector,
                    "using": "text-dense",
                    "limit": limit,
                    "with_payload": True
                }
                response = self._httpx_client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return [{"id": p["id"], "score": p["score"], "payload": p.get("payload", {})} 
                        for p in data["result"]["points"]]
            else:
                # QdrantClient ile
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
            if self._use_httpx:
                # httpx ile REST API çağrısı
                url = f"{self._base_url}/collections/{self.config.collection_name}/points/query"
                payload = {
                    "query": {
                        "indices": sparse_vector.indices,
                        "values": sparse_vector.values
                    },
                    "using": "text-sparse",
                    "limit": limit,
                    "with_payload": True
                }
                response = self._httpx_client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return [{"id": p["id"], "score": p["score"], "payload": p.get("payload", {})} 
                        for p in data["result"]["points"]]
            else:
                # QdrantClient ile
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
    
    def _text_based_search(self, query: str, limit: int) -> List[SearchResult]:
        """
        Text-based search (model olmadan).
        Qdrant scroll kullanarak payload'da text arama yapar.
        
        Args:
            query: Arama sorgusu
            limit: Maksimum sonuç sayısı
            
        Returns:
            SearchResult listesi
        """
        try:
            logger.info(f"Text-based search: '{query}'")
            
            # Query kelimelerini küçült
            query_terms = query.lower().split()
            
            # Scroll ile CVE'leri al (payload filtresi ile)
            results = []
            points = []
            
            if getattr(self, "_use_httpx", False):
                # Qdrant REST scroll
                url = f"{self._base_url}/collections/{self.config.collection_name}/points/scroll"
                payload = {
                    "with_payload": True,
                    "with_vectors": False,
                    "limit": 1000
                }
                response = self._httpx_client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                points = data.get("result", {}).get("points", [])
                # Adapt to payload format below
                for p in points:
                    payload = p.get("payload", {})
                    metadata = payload.get("metadata", {})
                    content = (payload.get("content", "") or "").lower()
                    cve_id = (payload.get("cve_id", "") or "").lower()
                    match_count = sum(1 for term in query_terms if term in content or term in cve_id)
                    score = match_count / len(query_terms) if query_terms else 0
                    if score > 0:
                        results.append(SearchResult(
                            cve_id=payload.get("cve_id", str(p.get("id", ""))),
                            score=score,
                            dense_score=0.0,
                            sparse_score=score,
                            severity=metadata.get("severity"),
                            base_score=metadata.get("base_score"),
                            attack_vector=metadata.get("attack_vector"),
                            description=payload.get("content", "")[:500],
                            published_date=metadata.get("published_date"),
                            metadata=metadata
                        ))
            else:
                # Qdrant client scroll
                scroll_result = self._client.scroll(
                    collection_name=self.config.collection_name,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False
                )
                for point in scroll_result[0]:
                    payload = point.payload
                    metadata = payload.get("metadata", {})
                    content = payload.get("content", "").lower()
                    cve_id = payload.get("cve_id", "").lower()
                    match_count = sum(1 for term in query_terms if term in content or term in cve_id)
                    score = match_count / len(query_terms) if query_terms else 0
                    if score > 0:
                        results.append(SearchResult(
                            cve_id=payload.get("cve_id", str(point.id)),
                            score=score,
                            dense_score=0.0,
                            sparse_score=score,
                            severity=metadata.get("severity"),
                            base_score=metadata.get("base_score"),
                            attack_vector=metadata.get("attack_vector"),
                            description=payload.get("content", "")[:500],
                            published_date=metadata.get("published_date"),
                            metadata=metadata
                        ))
            
            results.sort(key=lambda x: x.score, reverse=True)
            logger.info(f"Text-based search tamamlandı: {len(results[:limit])} sonuç")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Text-based search hatası: {e}")
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
        
        # Hybrid skor hesapla ve SearchResult objelerine çevir - TÜM METADATA İLE
        results = []
        for point_id, data in combined.items():
            payload = data["payload"]
            metadata = payload.get("metadata", {})
            
            # Hybrid skor
            hybrid_score = (dense_weight * data["dense_score"]) + (sparse_weight * data["sparse_score"])
            
            # TÜM METADATA EXTRACT ET - HER ŞEY GELMELİ
            full_metadata = {
                "severity": metadata.get("severity"),
                "base_score": metadata.get("base_score"),
                "attack_vector": metadata.get("attack_vector"),
                "published_date": metadata.get("published_date"),
                "modified_date": metadata.get("modified_date"),
                "references": metadata.get("references", []),
                "cwe_id": metadata.get("cwe_id"),
                "vendor": metadata.get("vendor"),
                "product": metadata.get("product"),
                "cvss_vector": metadata.get("cvss_vector"),
                "cvss_vector_string": metadata.get("cvss_vector_string"),
                "exploitability_score": metadata.get("exploitability_score"),
                "impact_score": metadata.get("impact_score"),
                "confidentiality_impact": metadata.get("confidentiality_impact"),
                "integrity_impact": metadata.get("integrity_impact"),
                "availability_impact": metadata.get("availability_impact"),
                "access_complexity": metadata.get("access_complexity"),
                "authentication": metadata.get("authentication"),
                "affected_versions": metadata.get("affected_versions", []),
            }
            
            result = SearchResult(
                cve_id=payload.get("cve_id", str(point_id)),
                score=hybrid_score,
                dense_score=data["dense_score"],
                sparse_score=data["sparse_score"],
                severity=metadata.get("severity"),
                base_score=metadata.get("base_score"),
                attack_vector=metadata.get("attack_vector"),
                description=payload.get("content", ""),  # TAM AÇIKLAMA - KISALTMA YOK
                published_date=metadata.get("published_date"),
                metadata=full_metadata  # TÜM METADATA
            )
            results.append(result)
        
        # Skora göre sırala (en yüksek önce)
        results.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"🔗 {len(results)} sonuç birleştirildi ve sıralandı")
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
            
            if self._use_httpx:
                # httpx ile REST API çağrısı
                url = f"{self._base_url}/collections/{self.config.collection_name}/points"
                payload_data = {
                    "ids": [point_uuid],
                    "with_payload": True,
                    "with_vector": False
                }
                response = self._httpx_client.post(url, json=payload_data)
                response.raise_for_status()
                data = response.json()
                
                if not data["result"]:
                    logger.warning(f"CVE bulunamadı: {cve_id}")
                    return None
                
                point = data["result"][0]
                payload = point["payload"]
            else:
                # QdrantClient ile
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
            
            # TÜM METADATA EXTRACT ET - REFERANSLAR, SKORLAR, HER ŞEY
            full_metadata = {
                "severity": metadata.get("severity"),
                "base_score": metadata.get("base_score"),
                "attack_vector": metadata.get("attack_vector"),
                "published_date": metadata.get("published_date"),
                "modified_date": metadata.get("modified_date"),
                "references": metadata.get("references", []),
                "cwe_id": metadata.get("cwe_id"),
                "vendor": metadata.get("vendor"),
                "product": metadata.get("product"),
                "cvss_vector": metadata.get("cvss_vector"),
                "cvss_vector_string": metadata.get("cvss_vector_string"),
                "exploitability_score": metadata.get("exploitability_score"),
                "impact_score": metadata.get("impact_score"),
                "confidentiality_impact": metadata.get("confidentiality_impact"),
                "integrity_impact": metadata.get("integrity_impact"),
                "availability_impact": metadata.get("availability_impact"),
                "access_complexity": metadata.get("access_complexity"),
                "authentication": metadata.get("authentication"),
                "affected_versions": metadata.get("affected_versions", []),
            }
            
            return SearchResult(
                cve_id=payload.get("cve_id", cve_id),
                score=1.0,  # Direct fetch, skor yok
                dense_score=0.0,
                sparse_score=0.0,
                severity=metadata.get("severity"),
                base_score=metadata.get("base_score"),
                attack_vector=metadata.get("attack_vector"),
                description=payload.get("content", ""),  # TAM AÇIKLAMA
                published_date=metadata.get("published_date"),
                metadata=full_metadata  # TÜM METADATA
            )
            
        except Exception as e:
            logger.error(f"CVE getirme hatası ({cve_id}): {e}")
            return None
    
    def health_check(self) -> bool:
        """
        Sistem sağlık kontrolü yapar.
        Qdrant'a bağlanıp collection'ı kontrol eder.
        
        Returns:
            True: Sistem sağlıklı, False: Sorun var
        """
        try:
            if self._use_httpx:
                # httpx ile health check
                collections_response = self._httpx_client.get(f"{self._base_url}/collections")
                collections_response.raise_for_status()
                collections_data = collections_response.json()
                
                collection_names = [c['name'] for c in collections_data['result']['collections']]
                logger.info(f"Qdrant bağlantısı OK - {len(collection_names)} collection bulundu")
                
                # Collection detay
                collection_response = self._httpx_client.get(
                    f"{self._base_url}/collections/{self.config.collection_name}"
                )
                collection_response.raise_for_status()
                info = collection_response.json()
                points_count = info['result']['points_count']
                logger.info(f"Health check OK - Collection: {points_count} points")
                return True
            else:
                # QdrantClient ile health check
                collections_response = self._client.get_collections()
                logger.info(f"Qdrant bağlantısı OK - {len(collections_response.collections)} collection bulundu")
                
                # Collection'ı kontrol et
                info = self._client.get_collection(self.config.collection_name)
                logger.info(f"Health check OK - Collection: {info.points_count} points")
                return True
            
        except Exception as e:
            logger.error(f"Health check FAILED: {e}")
            logger.error(f"Qdrant Host: {self.config.qdrant_host}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Collection istatistiklerini döner.
        
        Returns:
            İstatistik bilgileri
        """
        try:
            if self._use_httpx:
                # httpx ile stats
                response = self._httpx_client.get(
                    f"{self._base_url}/collections/{self.config.collection_name}"
                )
                response.raise_for_status()
                data = response.json()
                info = data['result']
                
                return {
                    "collection_name": self.config.collection_name,
                    "points_count": info.get('points_count', 0),
                    "vectors_count": info.get('vectors_count', 0),
                    "indexed_vectors_count": info.get('indexed_vectors_count', 0),
                    "status": info.get('status', 'unknown')
                }
            else:
                # QdrantClient ile stats
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

