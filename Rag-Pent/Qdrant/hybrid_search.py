"""
CVE RAG Projesi - Hybrid Arama Arayüzü
Bu script hem dense (semantik) hem sparse (keyword) arama yapabilir
ve sonuçları birleştirerek en iyi sonuçları sunar.
"""

import orjson
import numpy as np
from qdrant_client import QdrantClient, models
from FlagEmbedding import BGEM3FlagModel
import torch
from typing import List, Dict, Any
import time
import uuid  # UUID işlemleri için

class CVEHybridSearcher:
    """CVE verilerinde hybrid arama yapan sınıf"""
    
    def __init__(self, qdrant_host="localhost", qdrant_port=6333, collection_name="cve_collection_hybrid"):
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = collection_name
        
        # BGE-M3 modelini yükle
        print("🔧 BGE-M3 modeli yükleniyor...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        use_fp16 = True if device == "cuda" else False
        self.model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=use_fp16)
        print(f"✅ Model yüklendi (Cihaz: {device.upper()})")
    
    def search_dense(self, query: str, limit: int = 10) -> List[Dict]:
        """Semantik (dense) arama yapar"""
        # Query'yi vektöre çevir
        query_vector = self.model.encode([query], return_dense=True)['dense_vecs'][0]
        
        # Qdrant'da dense arama (yeni API)
        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector.tolist(),
            using="text-dense",
            limit=limit,
            with_payload=True
        )
        
        return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
    
    def search_sparse(self, query: str, limit: int = 10) -> List[Dict]:
        """Keyword (sparse) arama yapar"""
        # Query'yi sparse vektöre çevir
        sparse_output = self.model.encode([query], return_sparse=True)['lexical_weights'][0]
        
        # Qdrant sparse vektör formatına çevir
        sparse_vector = models.SparseVector(
            indices=list(sparse_output.keys()),
            values=list(sparse_output.values())
        )
        
        # Qdrant'da sparse arama (yeni API)
        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=sparse_vector,
            using="text-sparse",
            limit=limit,
            with_payload=True
        )
        
        return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results.points]
    
    def hybrid_search(self, query: str, limit: int = 10, dense_weight: float = 0.7, sparse_weight: float = 0.3) -> List[Dict]:
        """Hybrid arama: dense ve sparse sonuçları birleştirir"""
        print(f"🔍 Hybrid arama başlatılıyor: '{query}'")
        
        # Her iki arama türünü paralel yap
        dense_results = self.search_dense(query, limit * 2)
        sparse_results = self.search_sparse(query, limit * 2)
        
        # Sonuçları birleştir ve skorları normalize et
        combined_scores = {}
        
        # Dense sonuçları ekle
        for result in dense_results:
            cve_id = result["id"]
            if cve_id not in combined_scores:
                combined_scores[cve_id] = {"payload": result["payload"], "dense_score": 0, "sparse_score": 0}
            combined_scores[cve_id]["dense_score"] = result["score"]
        
        # Sparse sonuçları ekle
        for result in sparse_results:
            cve_id = result["id"]
            if cve_id not in combined_scores:
                combined_scores[cve_id] = {"payload": result["payload"], "dense_score": 0, "sparse_score": 0}
            combined_scores[cve_id]["sparse_score"] = result["score"]
        
        # Hybrid skorları hesapla
        hybrid_results = []
        for cve_id, data in combined_scores.items():
            hybrid_score = (dense_weight * data["dense_score"]) + (sparse_weight * data["sparse_score"])
            hybrid_results.append({
                "id": cve_id,
                "hybrid_score": hybrid_score,
                "dense_score": data["dense_score"],
                "sparse_score": data["sparse_score"],
                "payload": data["payload"]
            })
        
        # Skora göre sırala ve limit uygula
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return hybrid_results[:limit]
    
    def search_by_severity(self, query: str, severity: str, limit: int = 10) -> List[Dict]:
        """Belirli severity'ye göre filtreli arama"""
        # Önce hybrid arama yap
        results = self.hybrid_search(query, limit * 2)
        
        # Severity'ye göre filtrele
        filtered_results = [
            r for r in results 
            if r["payload"].get("metadata", {}).get("severity", "").upper() == severity.upper()
        ]
        
        return filtered_results[:limit]
    
    def get_cve_details(self, cve_id: str) -> Dict:
        """Belirli bir CVE'nin detaylarını getirir (CVE ID string'inden UUID'ye çevirir)"""
        # CVE ID'sinden UUID oluştur
        point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, cve_id))
        
        results = self.qdrant_client.retrieve(
            collection_name=self.collection_name,
            ids=[point_uuid],
            with_payload=True,
            with_vectors=False
        )
        
        if results:
            return results[0].payload
        return None

def main():
    """Test ve demo fonksiyonu"""
    print("="*60)
    print("🚀 CVE Hybrid Arama Sistemi - Demo")
    print("="*60)
    
    try:
        # Searcher'ı başlat
        searcher = CVEHybridSearcher()
        
        # Test sorguları
        test_queries = [
            "SQL injection vulnerability",
            "buffer overflow in web server",
            "authentication bypass",
            "remote code execution",
            "cross-site scripting XSS"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Sorgu: '{query}'")
            print("-" * 50)
            
            # Hybrid arama yap
            results = searcher.hybrid_search(query, limit=3)
            
            for i, result in enumerate(results, 1):
                payload = result["payload"]
                metadata = payload.get("metadata", {})
                cve_id = payload.get("cve_id", result['id'])  # Payload'daki CVE ID'yi kullan
                
                print(f"{i}. CVE ID: {cve_id}")
                print(f"   Hybrid Score: {result['hybrid_score']:.4f} (Dense: {result['dense_score']:.4f}, Sparse: {result['sparse_score']:.4f})")
                print(f"   Severity: {metadata.get('severity', 'N/A')}")
                print(f"   Attack Vector: {metadata.get('attack_vector', 'N/A')}")
                print(f"   Base Score: {metadata.get('base_score', 'N/A')}")
                print(f"   Content Preview: {payload.get('content', '')[:100]}...")
                print()
            
            time.sleep(1)  # Rate limiting
        
        print("="*60)
        print("✅ Demo tamamlandı!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        print("💡 Çözüm: Qdrant'ın çalıştığından ve vektörlerin yüklendiğinden emin olun")

if __name__ == "__main__":
    main()
